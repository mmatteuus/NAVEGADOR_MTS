import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { mkdtemp, mkdir, cp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { chromium } from "playwright";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { getConfig, root } from "../dist/config.js";
import { startBridge } from "../dist/bridge.js";
import { additionalCases, extraFixture } from "./additional-cases.mjs";
import { cuaCases } from "./cua-cases.mjs";

const fixture = `<!doctype html><title>Browser control test</title>
<form onsubmit="event.preventDefault(); document.querySelector('#result').textContent='Submitted: '+document.querySelector('#name').value">
<label>Name <input id="name"></label><label>Password <input type="password" value="secret"></label>
<select id="colour"><option value="red">Red</option><option value="blue">Blue</option></select>
<input id="check" type="checkbox"><button>Submit</button></form>
<button id="delayed" onclick="setTimeout(()=>document.querySelector('#result').textContent='Ready',150)">Delayed</button>
<p id="result">Initial</p><div id="shadow"></div><iframe src="/frame"></iframe><div style="height:2000px">Long page</div>
<script>
const shadow = document.querySelector('#shadow').attachShadow({mode:'open'});
shadow.innerHTML='<button id="shadow-button">Shadow action</button>';
shadow.querySelector('button').onclick = (event) => { event.target.textContent='Shadow clicked'; };
</script>${extraFixture}`;

test("real extensions: MCP page actions, screenshots and bridge restart", { timeout: 180000 }, async (t) => {
    const config = await getConfig();
    // Use an isolated copy so the test cannot replace a user's running bridge or extensions.
    const directory = await mkdtemp(resolve(tmpdir(), "browser-control-test-"));
    for (const folder of ["dist", "build"]) {
        await cp(resolve(root, folder), resolve(directory, folder), { recursive: true });
    }
    await mkdir(resolve(directory, ".local"));
    const testConfig = { ...config, port: 19827 };
    await writeFile(resolve(directory, "package.json"), '{"type":"module"}');
    // Resolve dependencies from the original install without copying them.
    const { symlink } = await import("node:fs/promises");
    await symlink(resolve(root, "node_modules"), resolve(directory, "node_modules"), "dir");
    await writeFile(resolve(directory, ".local/config.json"), JSON.stringify(testConfig));
    for (const browser of ["chrome", "firefox"]) {
        await writeFile(
            resolve(directory, "build", browser, "connection.json"),
            JSON.stringify({ ...testConfig, browser }),
        );
    }
    let bridge = await startBridge(testConfig);
    t.after(() => bridge.close());
    const fixtureServer = createServer((req, res) => {
        res.setHeader("Content-Type", "text/html");
        res.end(req.url === "/frame" ? '<label>Frame input <input id="frame-input"></label>' : fixture);
    });
    await new Promise((resolve) => fixtureServer.listen(0, "127.0.0.1", resolve));
    t.after(() => {
        fixtureServer.closeAllConnections();
        return new Promise((resolve) => fixtureServer.close(resolve));
    });
    const url = `http://127.0.0.1:${fixtureServer.address().port}/`;
    for (const browser of ["chrome", "firefox"]) {
        await writeFile(
            resolve(directory, "build", browser, "connection.json"),
            JSON.stringify({
                ...testConfig,
                browser,
            }),
        );
    }
    const client = new Client({ name: "test", version: "1" });
    await client.connect(
        new StdioClientTransport({ command: process.execPath, args: [resolve(directory, "dist/server.js")] }),
    );
    t.after(() => client.close());
    const call = async (name, args = {}) => {
        const result = await client.callTool({ name: `browser_${name}`, arguments: args });
        assert.ok(!result.isError, JSON.stringify(result));
        return result.content[0].type === "image" ? result.content[0] : JSON.parse(result.content[0].text);
    };
    let firefoxDiagnostics = async () => {};
    const waitForBrowser = async (browser) => {
        for (let attempt = 0; attempt < 100; attempt++) {
            const { browsers } = await call("list");
            if (browsers.some((peer) => peer.browser === browser)) {
                return;
            }
            await delay(100);
        }
        if (browser === "firefox") {
            await firefoxDiagnostics();
        }
        throw new Error(`${browser} did not connect`);
    };
    const extension = resolve(directory, "build/chrome");
    const context = await chromium.launchPersistentContext("", {
        channel: "chromium",
        headless: true,
        args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
    });
    t.after(() => context.close());
    const browsers = ["chrome"];
    if (process.env.GECKODRIVER) {
        const driver = spawn(process.env.GECKODRIVER, ["--port", "19828", "--allow-system-access"], {
            stdio: "ignore",
        });
        t.after(() => {
            driver.kill();
        });
        const webdriver = async (path, body, method = "POST") => {
            const response = await fetch(`http://127.0.0.1:19828${path}`, {
                method,
                headers: { "Content-Type": "application/json" },
                body: body ? JSON.stringify(body) : undefined,
                signal: AbortSignal.timeout(20000),
            });
            const { value } = await response.json();
            if (!response.ok) {
                throw new Error(JSON.stringify(value));
            }
            return value;
        };
        for (let attempt = 0; attempt < 50; attempt++) {
            try {
                await webdriver("/status", undefined, "GET");
                break;
            } catch {
                await delay(100);
            }
        }
        const session = await webdriver("/session", {
            capabilities: {
                alwaysMatch: {
                    browserName: "firefox",
                    "moz:firefoxOptions": { binary: "/usr/bin/firefox", args: ["-headless"] },
                },
            },
        });
        t.after(() => webdriver(`/session/${session.sessionId}`, undefined, "DELETE").catch(() => {}));
        await webdriver(`/session/${session.sessionId}/moz/addon/install`, {
            path: resolve(directory, "build/firefox"),
            temporary: true,
        });
        firefoxDiagnostics = async () => {
            await webdriver(`/session/${session.sessionId}/moz/context`, { context: "chrome" });
            console.log(
                await webdriver(`/session/${session.sessionId}/execute/sync`, {
                    script: "return Services.console.getMessageArray().map(m => m.message).filter(m => /browser-control|background.js|connection.json|WebSocket/i.test(m));",
                    args: [],
                }),
            );
        };
        browsers.push("firefox");
    }
    for (const browser of browsers) {
        await t.test(browser, async () => {
            await waitForBrowser(browser);
            const originalTabs = await call("tabs", { browser, includeAll: true });
            const originalFocus = (await call("windows", { browser })).find((window) => window.focused)?.id;
            const tab = await call("open", { browser, url });
            assert.equal((await call("windows", { browser })).find((window) => window.focused)?.id, originalFocus);
            const args = { browser, tabId: tab.id };
            const owned = (await call("tabs", { browser })).find((item) => item.id === tab.id);
            assert.equal(owned.automation, true);
            assert.ok(owned.groupId >= 0, "Automation tab belongs to a group");
            assert.ok(
                originalTabs.some((item) => item.windowId === tab.windowId),
                "Automation reuses an existing window",
            );
            assert.equal(owned.active, false);
            for (const original of originalTabs)
                assert.equal(
                    (await call("tabs", { browser, includeAll: true })).find((item) => item.id === original.id)
                        .automation,
                    false,
                );
            let snapshot = await call("snapshot", args);
            assert.match(snapshot.text, /Initial/);
            assert.equal(snapshot.elements.find((element) => element.type === "password").value, "[redacted]");
            const input = snapshot.elements.find((element) => element.name === "Name");
            assert.ok(input?.ref);
            await call("fill", { ...args, ref: input.ref, text: "Test" });
            await call("type", { ...args, ref: input.ref, text: " user" });
            await call("select", { ...args, selector: "#colour", values: ["blue"] });
            await call("click", { ...args, selector: "#check" });
            await call("press", { ...args, ref: input.ref, key: "Enter" });
            snapshot = await call("snapshot", args);
            assert.match(snapshot.text, /Submitted: Test user/);
            assert.equal(snapshot.elements.find((element) => element.tag === "select").value, "blue");
            assert.equal(snapshot.elements.find((element) => element.type === "checkbox").checked, true);
            await call("click", { ...args, selector: "#shadow-button" });
            assert.match((await call("snapshot", args)).text, /Shadow clicked/);
            await call("click", { ...args, selector: "#delayed" });
            await call("wait", { ...args, text: "Ready" });
            const frames = await call("frames", args);
            const frame = frames.find((item) => item.url.endsWith("/frame"));
            await call("fill", { ...args, frameId: frame.frameId, selector: "#frame-input", text: "Frame filled" });
            assert.equal(
                (await call("snapshot", { ...args, frameId: frame.frameId })).elements[0].value,
                "Frame filled",
            );
            const screenshot = await call("screenshot", args);
            assert.equal(screenshot.mimeType, "image/png");
            assert.equal(Buffer.from(screenshot.data, "base64").subarray(1, 4).toString(), "PNG");
            const observation = await client.callTool({ name: "browser_observe", arguments: args });
            assert.ok(!observation.isError, JSON.stringify(observation));
            const metadata = JSON.parse(observation.content[0].text);
            assert.equal(typeof metadata.consistent, "boolean");
            assert.ok(metadata.snapshot.documentId);
            assert.equal(observation.content[1].type, "image");
            assert.equal(
                (await call("windows", { browser })).find((window) => window.focused)?.id,
                originalFocus,
                "Opening and capturing must preserve the focused window",
            );
            const after = await call("tabs", { browser, includeAll: true });
            for (const original of originalTabs) {
                assert.equal(
                    after.find((item) => item.id === original.id)?.active,
                    original.active,
                    "Normal selected tabs stay unchanged",
                );
            }
            await call("move", { ...args, x: 150, y: 100 });
            if (browser === "chrome") {
                const page = context.pages().find((item) => item.url() === url);
                assert.equal(await page.locator("#local-browser-control-cursor").count(), 1);
                const cursorScreenshot = await call("screenshot", args);
                await writeFile(resolve(root, ".local/cursor-test.png"), Buffer.from(cursorScreenshot.data, "base64"));
            }
            await call("scroll", { ...args, y: 400 });
            await call("navigate", { ...args, url: `${url}?next` });
            const stale = await client.callTool({ name: "browser_click", arguments: { ...args, ref: input.ref } });
            assert.equal(stale.isError, true);
            assert.equal((await call("back", args)).url, url);
            assert.equal((await call("forward", args)).url, `${url}?next`);
            await call("reload", args);
            await additionalCases(call, args);
            const originalActive = originalTabs.find((item) => item.windowId === originalFocus && item.active);
            if (originalActive) {
                await call("focus", { browser, tabId: originalActive.id });
            }
            const other = await call("open", { browser, url, sessionName: "Second task" });
            await call("focus", { browser, tabId: other.id });
            const trustedKey = await client.callTool({
                name: "browser_press",
                arguments: { ...args, key: "a", inputMode: "trusted" },
            });
            assert.equal(trustedKey.isError, true, "Unsupported trusted keys must fail explicitly");
            const trustedPointer = await client.callTool({
                name: "browser_click",
                arguments: { ...args, selector: "#pad", inputMode: "trusted" },
            });
            assert.equal(trustedPointer.isError, true, "Unsupported trusted pointers must fail explicitly");
            await cuaCases(client, browser, tab.id, url);
            assert.equal((await call("windows", { browser })).find((window) => window.focused)?.id, originalFocus);
            await call("mark", { ...args, mark: "deliverable" });
            assert.equal((await call("tabs", { browser })).find((item) => item.id === tab.id).mark, "deliverable");
            assert.equal(other.windowId, tab.windowId);
            assert.notEqual(other.groupId, tab.groupId);
            assert.equal(
                (await call("tabs", { browser })).find((item) => item.id === other.id).sessionName,
                "Second task",
            );
            await call("close", { browser, tabId: other.id });
            await call("close", args);
        });
    }
    await t.test("human takeover cancels queued work; fresh state continues without approval", async () => {
        const tab = await call("open", { browser: "chrome", url, sessionName: "Takeover test" });
        const args = { browser: "chrome", tabId: tab.id };
        await call("focus", args);
        await call("snapshot", args);
        const page = context.pages().at(-1);
        assert.equal(page.url(), url);
        const clicking = client.callTool({ name: "browser_click", arguments: { ...args, selector: "form button" } });
        await page.waitForSelector("#local-browser-control-cursor", { state: "attached" });
        const queued = client.callTool({
            name: "browser_fill",
            arguments: { ...args, selector: "#name", text: "must-not-be-written" },
        });
        await page.mouse.click(500, 500);
        assert.equal((await clicking).isError, true);
        assert.equal((await queued).isError, true);
        assert.equal(
            (
                await client.callTool({
                    name: "browser_fill",
                    arguments: { ...args, selector: "#name", text: "too-early" },
                })
            ).isError,
            true,
        );
        await call("snapshot", args);
        await call("fill", { ...args, selector: "#name", text: "resumed" });
        const events = await call("events");
        assert.ok(events.result.some((event) => event.tabId === tab.id && event.type === "human-takeover"));
        await call("close", args);
    });
    await t.test("idle cleanup closes real owned tabs and preserves marked tabs", async () => {
        const before = await call("tabs", { browser: "chrome" });
        const idle = await call("open", { browser: "chrome", url, sessionName: "Idle cleanup test" });
        const kept = await call("open", { browser: "chrome", url, sessionName: "Idle cleanup test" });
        await call("mark", { browser: "chrome", tabId: kept.id, mark: "handoff" });
        await context.serviceWorkers()[0].evaluate(async () => {
            const manager = globalThis.browserControlSessions(chrome, () => Date.now() + 5 * 3600000);
            await manager.cleanup();
        });
        const after = await call("tabs", { browser: "chrome" });
        assert.ok(!after.some((tab) => tab.id === idle.id));
        assert.ok(after.some((tab) => tab.id === kept.id));
        for (const tab of before) assert.ok(after.some((item) => item.id === tab.id));
        await call("close", { browser: "chrome", tabId: kept.id });
    });
    await t.test("cursor tracks actual browser zoom changes", async () => {
        const tab = await call("open", { browser: "chrome", url, sessionName: "Zoom test" });
        const worker = context.serviceWorkers()[0];
        await worker.evaluate((id) => chrome.tabs.setZoom(id, 1.25), tab.id);
        await call("move", { browser: "chrome", tabId: tab.id, x: 100, y: 100 });
        const scale = () =>
            worker.evaluate(async (id) => {
                const [result] = await chrome.scripting.executeScript({
                    target: { tabId: id },
                    func: () =>
                        document
                            .querySelector("#local-browser-control-cursor")
                            .style.getPropertyValue("--cursor-scale"),
                });
                return Number(result.result);
            }, tab.id);
        assert.equal(await scale(), 0.8);
        await worker.evaluate((id) => chrome.tabs.setZoom(id, 2), tab.id);
        for (let i = 0; i < 20 && (await scale()) !== 0.5; i++) await delay(50);
        assert.equal(await scale(), 0.5, "Existing cursor resizes without another action");
        await worker.evaluate((id) => chrome.tabs.setZoom(id, 1), tab.id);
        await call("close", { browser: "chrome", tabId: tab.id });
    });
    await bridge.close();
    bridge = await startBridge(testConfig);
    for (const browser of browsers) {
        await waitForBrowser(browser);
        assert.ok(Array.isArray(await call("tabs", { browser })));
    }
    await t.test("idle heartbeat", { skip: !!process.env.SKIP_IDLE_CHECK }, async () => {
        await delay(35000);
        for (const browser of browsers) {
            assert.ok(Array.isArray(await call("tabs", { browser })));
        }
    });
});
