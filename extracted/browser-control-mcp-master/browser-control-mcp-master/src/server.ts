import { resolve } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { getConfig, root, dataDirectory } from "./config.js";
import { startBridge } from "./bridge.js";
import { request, ensureBridge } from "./connection.js";
import { createRuntime } from "./runtime.js";
import { documentation } from "./cua.js";

const config = await getConfig();

if (process.argv.includes("--bridge")) {
    const bridge = await startBridge(config);
    for (const signal of ["SIGINT", "SIGTERM"] as const) {
        process.once(signal, () => {
            void bridge.close().then(() => process.exit(0));
        });
    }
} else if (process.argv.includes("--setup")) {
    await ensureBridge();
    console.log(
        JSON.stringify(
            {
                mcpServers: {
                    "browser-control": {
                        command: process.execPath,
                        args: [resolve(root, "dist/server.js")],
                        ...(process.env.BROWSER_CONTROL_HOME ? { env: { BROWSER_CONTROL_HOME: dataDirectory } } : {}),
                    },
                },
            },
            null,
            2,
        ),
    );
    console.log(
        `\nExtension folders: ${resolve(dataDirectory, "extensions/chrome")} and ${resolve(dataDirectory, "extensions/firefox")}.`,
    );
} else {
    const server = new McpServer({ name: "browser-control", version: "0.1.0" });
    const runtime = createRuntime();
    server.server.onclose = () => runtime.reset();
    server.registerTool(
        "browser_run",
        {
            description:
                "Run JavaScript in a persistent local Node runtime with cua browser methods and nodeRepl output helpers. Top-level await and variables persist. Full local OS permissions; not a security sandbox. Read browser_api first.",
            inputSchema: {
                code: z.string().min(1).max(100000),
                timeoutMs: z.number().int().min(500).max(60000).default(30000),
            },
        },
        async ({ code, timeoutMs }) => {
            try {
                await ensureBridge();
                return await runtime.run(code, timeoutMs);
            } catch (error) {
                return { isError: true, content: [{ type: "text", text: String(error) }] };
            }
        },
    );
    server.registerTool(
        "browser_api",
        { description: "Read the local cua compatibility API and its limitations.", inputSchema: {} },
        async () => ({ content: [{ type: "text", text: documentation }] }),
    );
    server.registerTool(
        "browser_reset",
        {
            description:
                "Reset this MCP client's JavaScript runtime and variables. Does not close tabs. In-progress browser actions may still finish.",
            inputSchema: {},
        },
        async () => {
            runtime.reset();
            return { content: [{ type: "text", text: "Browser runtime reset. Tabs remain open." }] };
        },
    );
    const browser = z
        .string()
        .optional()
        .describe("Browser id from browser_list, or chrome/firefox when only one instance matches.");
    const tabId = z.number().int().describe("Tab id from browser_tabs.");
    const target = {
        documentId: z.string().optional().describe("Reject the action if this snapshot document has changed."),
        revision: z
            .number()
            .int()
            .nonnegative()
            .optional()
            .describe("Reject if the DOM revision differs from the snapshot."),
        ref: z.string().optional().describe("Element ref from the latest snapshot in this document."),
        selector: z.string().optional().describe("CSS selector. Must identify exactly one element."),
        frameId: z.number().int().optional().describe("Frame id from browser_frames; defaults to top frame."),
    };
    const text = (value: unknown) => ({ content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }] });
    server.registerTool(
        "browser_events",
        {
            description:
                "Read recent human-takeover events (last ten minutes, up to 100). No page contents are recorded.",
            inputSchema: {},
        },
        async () => {
            try {
                await ensureBridge();
                return text(await request("/events"));
            } catch (error) {
                return { ...text({ error: String(error) }), isError: true };
            }
        },
    );
    server.registerTool(
        "browser_action_status",
        {
            description:
                "Recover metadata for an operation ID from a failed command without replaying it. A completed reply does not prove website persistence; inspect the page before any retry.",
            inputSchema: { operationId: z.string().regex(/^\d{13}_[a-f0-9-]{36}$/) },
        },
        async ({ operationId }) => {
            try {
                await ensureBridge();
                return text(await request(`/actions/${operationId}`));
            } catch (error) {
                return { ...text({ error: String(error) }), isError: true };
            }
        },
    );
    server.registerTool(
        "browser_list",
        {
            description: "List connected Chrome and Firefox profiles. The local bridge starts automatically.",
            inputSchema: {},
        },
        async () => {
            try {
                await ensureBridge();
                return text(await request("/health"));
            } catch (error) {
                return { ...text({ error: String(error) }), isError: true };
            }
        },
    );
    function tool(name: string, description: string, schema: z.ZodRawShape): void {
        const inputSchema = {
            browser,
            ...schema,
            ...(["click", "fill", "type", "paste", "press", "select", "scroll", "drag", "secondary"].includes(name)
                ? {
                      expect: z
                          .object({
                              text: z.string().min(1).optional(),
                              selector: z.string().min(1).optional(),
                              urlIncludes: z.string().min(1).optional(),
                              timeoutMs: z.number().int().min(600).max(10000).optional(),
                          })
                          .refine(
                              (value) => Object.keys(value).length > 0,
                              "Provide an expected text, selector or URL substring",
                          )
                          .optional()
                          .describe(
                              "Post-action condition. Default timeout is 1.2 seconds in visible pages and 3 seconds in hidden pages. A mismatch does not undo the action; inspect before retrying.",
                          ),
                  }
                : {}),
            ...(["click", "move", "hover", "drag", "fill", "type", "press", "paste"].includes(name)
                ? {
                      inputMode: z
                          .enum(["auto", "dom", "trusted"])
                          .default("auto")
                          .describe(
                              "Auto uses trusted Chrome text insertion only in the active foreground tab; DOM otherwise. Pointer actions and keys always use DOM.",
                          ),
                  }
                : {}),
        };
        server.registerTool(`browser_${name}`, { description, inputSchema }, async (input) => {
            try {
                await ensureBridge();
                const { browser: selected, ...args } = input;
                const { result } = await request("/command", { browser: selected, action: name, args });
                if (name === "screenshot" && typeof result === "string") {
                    return { content: [{ type: "image" as const, data: result.split(",")[1], mimeType: "image/png" }] };
                }
                if (name === "observe") {
                    const { screenshot, ...observation } = result as { screenshot: string; [key: string]: unknown };
                    return {
                        content: [
                            ...text(observation).content,
                            { type: "image" as const, data: screenshot.split(",")[1], mimeType: "image/png" },
                        ],
                    };
                }
                return {
                    ...text(result),
                    ...((result as { verification?: { status?: string } })?.verification?.status === "mismatch"
                        ? { isError: true }
                        : {}),
                };
            } catch (error) {
                return { ...text({ error: String(error) }), isError: true };
            }
        });
    }
    tool("tabs", "List tabs in the connected browser without per-site approval.", {});
    tool("capabilities", "Report the input and observation capabilities of this browser.", {});
    tool(
        "accessibility",
        "Read Chrome's native accessibility tree. Snapshot provides semantic DOM state on both browsers.",
        { tabId },
    );
    tool("windows", "List browser windows, focus state and automation session names in each window.", {});
    tool("open", "Open a URL in a named group in an existing window. Does not select the new tab by default.", {
        url: z.string().url(),
        active: z.boolean().default(false),
        sessionName: z.string().min(1).max(100).optional().describe("Named task group. Defaults to MCP Automation."),
    });
    tool("mark", "Mark a tab as a deliverable or handoff without changing focus or closing it.", {
        tabId,
        mark: z.enum(["deliverable", "handoff"]),
    });
    tool("navigate", "Navigate a tab to an HTTP or HTTPS URL; wait for document load.", {
        tabId,
        url: z.string().url(),
    });
    tool("close", "Close a tab.", { tabId });
    tool("focus", "Activate a tab and focus its window.", { tabId });
    tool("back", "Go back in a tab's history.", { tabId });
    tool("forward", "Go forward in a tab's history.", { tabId });
    tool("reload", "Reload a tab and wait for document load.", { tabId });
    tool("frames", "List frame ids and URLs for use in page tools.", { tabId });
    tool(
        "snapshot",
        "Read rendered document text (including off-screen content), viewport flags and scroll regions with target refs, positions and available directions. Includes open shadow roots. Refs expire on navigation.",
        {
            tabId,
            frameId: target.frameId,
            maxChars: z.number().int().min(100).max(100000).default(20000),
            showScrollbars: z
                .boolean()
                .default(false)
                .describe(
                    "Optional visual assistance: inject visible scrollbar styling. Ordinary snapshots do not change page styling.",
                ),
        },
    );
    tool(
        "screenshot",
        "Capture the viewport as PNG. Temporarily selects the tab and restores the previous selection without focusing the window.",
        { tabId },
    );
    tool(
        "observe",
        "Capture semantic state, frame mapping and a locally masked screenshot with a DOM consistency flag. Not an atomic render guarantee; animated or changing pages may be inconsistent.",
        { tabId, maxChars: z.number().int().min(100).max(100000).default(20000) },
    );
    tool(
        "collect",
        "Scroll a list/table and accumulate visible rows with text-based deduplication. Bounded and interruptible; never claims full server-side completeness. Leaves scroll position changed.",
        {
            tabId,
            ...target,
            maxSteps: z.number().int().min(1).max(40).default(10),
            maxItems: z.number().int().min(1).max(1000).default(200),
        },
    );
    tool(
        "click",
        "Click an element or exact viewport coordinates with DOM events. Supports left/right/middle buttons and double-click.",
        {
            tabId,
            ...target,
            x: z.number().optional(),
            y: z.number().optional(),
            mouseButton: z.enum(["left", "right", "middle"]).default("left"),
            clickCount: z.number().int().min(1).max(2).default(1),
        },
    );
    tool("fill", "Replace a text field or contenteditable value and dispatch input/change events.", {
        tabId,
        ...target,
        text: z.string(),
    });
    tool("type", "Insert text at the cursor in a text field or contenteditable.", {
        tabId,
        ...target,
        text: z.string(),
    });
    tool("select", "Select options by their values and dispatch input/change events.", {
        tabId,
        ...target,
        values: z.array(z.string()).min(1),
    });
    tool(
        "press",
        "Press a key or chord such as ctrl+a, Return or shift+Left. Uses DOM editing in both browsers to preserve background operation. Trusted keyboard input is unsupported.",
        {
            tabId,
            ...target,
            key: z.string(),
            ctrl: z.boolean().default(false),
            alt: z.boolean().default(false),
            shift: z.boolean().default(false),
            meta: z.boolean().default(false),
        },
    );
    tool("scroll", "Scroll the page or an element by CSS pixels.", {
        tabId,
        ...target,
        x: z.number().default(0),
        y: z.number().default(600),
        origin: z.tuple([z.number(), z.number()]).optional(),
        pages: z.number().min(0).max(100).optional(),
        direction: z.enum(["up", "down", "left", "right"]).optional(),
    });
    tool("hover", "Dispatch pointer and mouse hover events on an element. Does not move the physical cursor.", {
        tabId,
        ...target,
    });
    tool("move", "Move the visible virtual cursor to viewport CSS coordinates. Does not move your physical mouse.", {
        tabId,
        frameId: target.frameId,
        x: z.number(),
        y: z.number(),
    });
    tool("wait", "Wait until an element is visible, or until page text contains a string.", {
        tabId,
        ...target,
        text: z.string().optional(),
        timeoutMs: z.number().int().min(1).max(25000).default(10000),
    });
    tool("drag", "Drag between exact viewport coordinates. DOM mode dispatches pointer and drag events.", {
        tabId,
        frameId: target.frameId,
        from: z.tuple([z.number(), z.number()]),
        to: z.tuple([z.number(), z.number()]),
    });
    tool("select_text", "Select one occurrence in an editable element. Use prefix/suffix to disambiguate.", {
        tabId,
        ...target,
        text: z.string().min(1),
        prefix: z.string().optional(),
        suffix: z.string().optional(),
        selectionType: z.enum(["text", "cursor_before", "cursor_after"]).default("text"),
    });
    tool(
        "paste",
        "Paste text, Markdown source or HTML into the target or focused editor. Does not use the system clipboard.",
        {
            tabId,
            ...target,
            text: z.string(),
            format: z.enum(["text", "md", "html"]).default("text"),
        },
    );
    tool("secondary", "Invoke an action listed in the element's snapshot actions field.", {
        tabId,
        ...target,
        action: z.enum(["Expand", "Collapse", "Increment", "Decrement"]),
    });
    await server.connect(new StdioServerTransport());
}
