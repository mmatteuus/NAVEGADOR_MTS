import { request, ensureBridge } from "./connection.js";

export type Content = { type: "text"; text: string } | { type: "image"; data: string; mimeType: string };
type Observation = { emit?: boolean; disableDiffing?: boolean };
type Vec2 = [number, number];
type Target = number | Vec2;
interface Peer {
    id: string;
    browser: string;
    name: string;
}
interface TabInfo {
    id: number;
    title?: string;
    url?: string;
    sessionName?: string;
    mark?: string;
}
interface SemanticNode {
    ref: string;
    parentRef: string | null;
    depth: number;
    role: string;
    name: string;
    value?: string;
    disabled?: boolean;
    checked?: boolean | string;
    expanded?: boolean | string;
    focused?: boolean;
    readonly?: boolean;
    selected?: boolean | string;
    level?: number | string;
    actions?: string[];
    inViewport?: boolean;
    scroll?: { x: number; y: number; maxX: number; maxY: number; directions: string[] };
    bounds: { x: number; y: number; width: number; height: number };
}
interface Snapshot {
    url: string;
    title: string;
    source: string;
    text: string;
    nodes: SemanticNode[];
    truncated: boolean;
}

export const documentation = `Local browser-control JavaScript API. Variables and top-level await persist between browser_run calls.
Snapshots include off-screen document content. Inspect off-screen flags and scroll positions/directions; scroll the region's index to reveal clipped or virtualized content.
Page actions emit verification summaries: observed-change is not proof of success, unconfirmed requires inspection, and mismatches throw without undoing the action. Direct action tools also accept expect:{text,selector,urlIncludes}. Never blindly retry a potentially applied action.
cua.getState(), cua.listBrowsers(), cua.listTabs({browser}), cua.getBrowser({id}), cua.getTab(id,{browser}),
cua.createBrowserTab(browserId,url,{sessionName,visible}). Opening a tab reuses an existing window with a named group and preserves the selected tab.
Tab: getAXState({emit,disableDiffing}), getScreenshot({emit}), getAXStateAndScreenshot({emit,disableDiffing}), observe(), collect({selector,maxSteps,maxItems}),
click(index|[x,y],{mouseButton,clickCount}), drag([x,y],[x,y]), pressKey('ctrl+a'), typeText(text),
setValue(index,value), paste(text,{format:'text'|'md'|'html'}), selectText(index,text,{prefix,suffix,selectionType}),
scroll(index|[x,y],direction,pages), performSecondaryAction(index,action), goto(url), back(), forward(), reload(), close(),
markDeliverable(), markHandoff(). Browser: browserId, documentation().
Read a state first; numeric indices identify the observed document, not CSS selectors. Actions must use current observations.
No site approvals are required. Human interaction cancels pending work; read a fresh getAXState before continuing. For private login, disable the connection globally while using your password manager.
observe() returns masked screenshot plus state and frame metadata with a DOM-consistency flag; getAXStateAndScreenshot is a legacy pair of separate captures. collect() scrolls and deduplicates visible rows, without claiming complete server data.
getAXState returns a DOM-derived semantic hierarchy with changes since the previous call; it is not a native AX tree.
Chrome browser_accessibility returns native AX separately. Chrome supports trusted text insertion only in an active foreground tab; background work uses DOM input. Pointer actions and keys use DOM input in both browsers.
Observations emit automatically unless emit:false. nodeRepl.write(value) emits text, nodeRepl.emitImage(bytes) emits an image.
This is a local Node runtime with the same OS permissions as the MCP process, not a security sandbox.
Native apps, arbitrary browser provider ids, and invisible in-app browser tabs are not supported.
Full reference: README.md and docs/compatibility.md in the server checkout.`;

export function createCua(emit: (content: Content) => void) {
    const output = (value: unknown, options?: Observation): void => {
        if (options?.emit !== false) {
            emit({ type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) });
        }
    };
    async function peers(): Promise<Peer[]> {
        await ensureBridge();
        return (await request("/health")).browsers as Peer[];
    }
    async function peer(id?: string): Promise<Peer> {
        const matches = (await peers()).filter((item) => !id || item.id === id || item.browser === id);
        if (matches.length !== 1) {
            throw new Error(
                matches.length
                    ? "Multiple browser profiles match; use an id from cua.listBrowsers()."
                    : "No browser connected. Load the local extension.",
            );
        }
        return matches[0];
    }
    async function command<T>(browser: string, action: string, args: object = {}): Promise<T> {
        const data = await request("/command", { browser, action, args });
        return data.result as T;
    }
    function bindTab(tabId: number, browserId: string) {
        let sequence = 0;
        let indices = new Map<number, SemanticNode>();
        const refIndices = new Map<string, number>();
        let previous = new Map<number, string>();
        let documentUrl: string | undefined;
        let previousText: string | undefined;
        const action = async <T = unknown>(name: string, args: object = {}): Promise<T> => {
            const result = await command<T>(browserId, name, { tabId, ...args });
            const verification = (result as { verification?: { status: string; reason: string } })?.verification;
            if (verification) {
                emit({ type: "text", text: `${name}: ${verification.status}. ${verification.reason}` });
                if (verification.status === "mismatch") throw new Error(verification.reason);
            }
            return result;
        };
        const target = (value: Target): object => {
            if (Array.isArray(value) && value.length === 2 && value.every(Number.isFinite)) {
                return { x: value[0], y: value[1] };
            }
            const node = indices.get(value as number);
            if (!node) {
                throw new Error("Unknown or stale element index. Call getAXState() first.");
            }
            return { ref: node.ref };
        };
        async function getAXState(options?: Observation): Promise<string> {
            const snapshot = await action<Snapshot>("snapshot", { maxChars: 30000 });
            const current = new Map<number, string>();
            const currentNodes = new Map<number, SemanticNode>();
            for (const node of snapshot.nodes) {
                let index = refIndices.get(node.ref);
                if (index === undefined) {
                    index = ++sequence;
                    refIndices.set(node.ref, index);
                }
                currentNodes.set(index, node);
                const flags = [
                    node.disabled ? "disabled" : "",
                    node.inViewport === false ? "off-screen" : "",
                    node.scroll
                        ? `scroll=(${node.scroll.x},${node.scroll.y})/(${node.scroll.maxX},${node.scroll.maxY}) available=${node.scroll.directions.join(",") || "none"}`
                        : "",
                    node.focused ? "focused" : "",
                    node.readonly ? "readonly" : "",
                    node.selected !== undefined ? "selected=" + node.selected : "",
                    node.level !== undefined ? "level=" + node.level : "",
                    node.checked !== undefined ? "checked=" + node.checked : "",
                    node.expanded !== undefined ? "expanded=" + node.expanded : "",
                    node.value !== undefined ? "value=" + JSON.stringify(node.value) : "",
                    node.actions?.length ? "actions=" + node.actions.join(",") : "",
                ]
                    .filter(Boolean)
                    .join(" ");
                current.set(
                    index,
                    `${"  ".repeat(node.depth)}[${index}] ${node.role} ${JSON.stringify(node.name)} ${flags}`.trimEnd(),
                );
            }
            const full = options?.disableDiffing || !previous.size || documentUrl !== snapshot.url;
            let lines: string[];
            if (full) {
                lines = [...current.values()];
            } else {
                lines = [];
                for (const [id, line] of current) {
                    if (previous.get(id) !== line) {
                        lines.push(`${previous.has(id) ? "Changed" : "Added"}: ${line}`);
                    }
                }
                for (const id of previous.keys()) {
                    if (!current.has(id)) {
                        lines.push(`Removed: [${id}]`);
                    }
                }
                if (!lines.length) {
                    lines.push("No semantic state changes.");
                }
            }
            indices = currentNodes;
            previous = current;
            documentUrl = snapshot.url;
            if (full || previousText !== snapshot.text) {
                lines.push(
                    "Page text (includes off-screen content; scroll regions expose available directions):\n" +
                        snapshot.text,
                );
            }
            previousText = snapshot.text;
            for (const [ref, id] of refIndices) {
                if (!indices.has(id)) {
                    refIndices.delete(ref);
                }
            }
            const text = `${snapshot.title}\n${snapshot.url}\nSource: ${snapshot.source}${snapshot.truncated ? " (truncated)" : ""}\n${lines.join("\n")}`;
            output(text, options);
            return text;
        }
        async function getScreenshot(options?: Observation): Promise<Uint8Array> {
            const data = await action<string>("screenshot");
            const bytes = Buffer.from(data.split(",")[1], "base64");
            if (options?.emit !== false) {
                emit({ type: "image", data: bytes.toString("base64"), mimeType: "image/png" });
            }
            return bytes;
        }
        const invalidate = (): void => {
            indices.clear();
            previous.clear();
            refIndices.clear();
            documentUrl = undefined;
            previousText = undefined;
        };
        return {
            id: String(tabId),
            getAXState,
            getScreenshot,
            async observe() {
                const observation = await action<{ screenshot: string; [key: string]: unknown }>("observe", {
                    maxChars: 30000,
                });
                const { screenshot, ...metadata } = observation;
                output(metadata);
                emit({ type: "image", data: screenshot.split(",")[1], mimeType: "image/png" });
                return observation;
            },
            async collect(options: { selector?: string; maxSteps?: number; maxItems?: number } = {}) {
                const result = await action("collect", options);
                output(result);
                return result;
            },
            async getAXStateAndScreenshot(options?: Observation) {
                const state = await getAXState(options);
                const screenshot = await getScreenshot(options);
                return { state, screenshot };
            },
            async click(value: Target, options: { mouseButton?: string; clickCount?: number } = {}) {
                const aliases: Record<string, string> = { l: "left", r: "right", m: "middle" };
                const mouseButton = aliases[options.mouseButton ?? ""] ?? options.mouseButton ?? "left";
                if (!["left", "right", "middle"].includes(mouseButton) || ![1, 2].includes(options.clickCount ?? 1)) {
                    throw new Error("Unsupported mouse button or click count.");
                }
                await action("click", { ...target(value), ...options, mouseButton });
            },
            async drag(from: Vec2, to: Vec2) {
                target(from);
                target(to);
                await action("drag", { from, to });
            },
            async pressKey(key: string) {
                await action("press", { key });
            },
            async typeText(text: string) {
                await action("type", { text });
            },
            async setValue(index: number, value: string) {
                await action("fill", { ...target(index), text: value });
            },
            async paste(text: string, options: { format?: "text" | "md" | "html" } = {}) {
                await action("paste", { text, format: options.format ?? "text" });
            },
            async selectText(
                index: number,
                text: string,
                options: {
                    prefix?: string;
                    suffix?: string;
                    selectionType?: "text" | "cursor_before" | "cursor_after";
                } = {},
            ) {
                await action("select_text", { ...target(index), text, ...options });
            },
            async scroll(value: Target, direction: string, pages = 1) {
                const vector: Record<string, Vec2> = {
                    up: [0, -1],
                    u: [0, -1],
                    down: [0, 1],
                    d: [0, 1],
                    left: [-1, 0],
                    l: [-1, 0],
                    right: [1, 0],
                    r: [1, 0],
                };
                if (!vector[direction] || !Number.isFinite(pages) || pages < 0) {
                    throw new Error("Invalid scroll direction or distance.");
                }
                // Coordinate scroll uses the element under the point; deltas must not overwrite its target.
                await action("scroll", {
                    ...(Array.isArray(value) ? { origin: value } : target(value)),
                    pages,
                    direction:
                        vector[direction][0] < 0
                            ? "left"
                            : vector[direction][0] > 0
                              ? "right"
                              : vector[direction][1] < 0
                                ? "up"
                                : "down",
                });
            },
            async performSecondaryAction(index: number, secondary: string) {
                const node = indices.get(index);
                if (!node?.actions?.includes(secondary)) {
                    throw new Error("Action is not present in this element's observed actions.");
                }
                await action("secondary", { ...target(index), action: secondary });
            },
            async goto(url: string) {
                await action("navigate", { url });
                invalidate();
            },
            async back() {
                await action("back");
                invalidate();
            },
            async forward() {
                await action("forward");
                invalidate();
            },
            async reload() {
                await action("reload");
                invalidate();
            },
            async close() {
                await action("close");
                invalidate();
            },
            async markDeliverable() {
                await action("mark", { mark: "deliverable" });
            },
            async markHandoff() {
                await action("mark", { mark: "handoff" });
            },
        };
    }
    async function listTabs(options: { browser?: string; emit?: boolean } = {}) {
        const selected = options.browser ? [await peer(options.browser)] : await peers();
        const tabs = (
            await Promise.all(
                selected.map(async (item) =>
                    (await command<TabInfo[]>(item.id, "tabs")).map((tab) => ({
                        ...tab,
                        id: String(tab.id),
                        providerTabId: String(tab.id),
                        browserId: item.id,
                    })),
                ),
            )
        ).flat();
        output(tabs, options);
        return tabs;
    }
    return {
        async getState(options?: Observation) {
            const browsers = await peers();
            const state = {
                apps: [],
                browsers: await Promise.all(
                    browsers.map(async (item) => ({
                        id: item.id,
                        name: item.browser,
                        family: item.browser,
                        type: "extension",
                        profileName: item.name,
                        tabs: await listTabs({ browser: item.id, emit: false }),
                    })),
                ),
            };
            output(state, options);
            return state;
        },
        async listBrowsers(options?: Observation) {
            const browsers = (await peers()).map((item) => ({
                id: item.id,
                name: item.browser,
                family: item.browser,
                type: "extension",
                profileName: item.name,
            }));
            output(browsers, options);
            return browsers;
        },
        listTabs,
        async getBrowser(options: { id?: string; url?: string } = {}) {
            const selected = await peer(options.id);
            output(documentation);
            return { browserId: selected.id, documentation: async () => documentation };
        },
        async getTab(id: string | number, options: { browser?: string } = {}) {
            const candidates = (await listTabs({ ...options, emit: false })).filter((tab) => tab.id === String(id));
            if (candidates.length !== 1) {
                throw new Error("Tab id is absent or ambiguous; specify its browser id.");
            }
            const tab = bindTab(Number(id), candidates[0].browserId);
            await tab.getAXState();
            return tab;
        },
        async createBrowserTab(
            browserId: string,
            url = "https://example.com",
            options: { sessionName?: string; visible?: boolean } = {},
        ) {
            if (options.visible === false) {
                throw new Error(
                    "Invisible in-app tabs are not supported. Automation tabs open without selecting them.",
                );
            }
            const selected = await peer(browserId);
            const opened = await command<TabInfo>(selected.id, "open", {
                url,
                sessionName: options.sessionName,
                active: false,
            });
            const tab = bindTab(opened.id, selected.id);
            await tab.getAXState();
            return tab;
        },
        async listApps(options?: Observation) {
            const apps: never[] = [];
            output(apps, options);
            return apps;
        },
        async getApp(_name: string): Promise<never> {
            throw new Error("Native application control is not supported by this browser server.");
        },
    };
}
