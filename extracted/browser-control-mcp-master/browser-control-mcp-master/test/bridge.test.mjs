import test from "node:test";
import assert from "node:assert/strict";
import { once } from "node:events";
import { randomBytes } from "node:crypto";
import { WebSocket } from "ws";
import { startBridge } from "../dist/bridge.js";

test("bridge authentication, routing, disconnect failure and reconnection", async (t) => {
    const config = { port: 19826, token: randomBytes(32).toString("hex") };
    const bridge = await startBridge(config);
    t.after(() => bridge.close());
    await assert.rejects(startBridge(config), /EADDRINUSE/);
    const base = `http://127.0.0.1:${config.port}`;
    const headers = { Authorization: `Bearer ${config.token}`, "Content-Type": "application/json" };
    assert.equal((await fetch(`${base}/health`)).status, 403);
    assert.equal(
        (await fetch(`${base}/health`, { headers: { ...headers, Origin: "https://evil.example" } })).status,
        403,
    );
    async function peer(id, browser = "chrome") {
        const ws = new WebSocket(`ws://127.0.0.1:${config.port}/extension`, { origin: "chrome-extension://test" });
        await once(ws, "open");
        const ready = once(ws, "message");
        ws.send(JSON.stringify({ type: "hello", id, browser, token: config.token }));
        await ready;
        return ws;
    }
    const invalid = new WebSocket(`ws://127.0.0.1:${config.port}/extension`, { origin: "chrome-extension://test" });
    await once(invalid, "open");
    invalid.send(JSON.stringify({ type: "hello", token: "wrong" }));
    const [code] = await once(invalid, "close");
    assert.equal(code, 1008);
    const ws = await peer("one");
    const send = async (browser) =>
        (
            await fetch(`${base}/command`, {
                method: "POST",
                headers,
                body: JSON.stringify({ browser, action: "tabs" }),
            })
        ).json();
    ws.on("message", (raw) => {
        const message = JSON.parse(raw);
        ws.send(JSON.stringify({ id: message.id, result: ["tab"] }));
    });
    assert.deepEqual(await send("one"), { result: ["tab"] });
    const second = await peer("two");
    assert.match((await send()).error, /Multiple browsers/);
    second.on("message", () => second.close());
    assert.match((await send("two")).error, /disconnected/);
    const replacement = await peer("two");
    replacement.on("message", (raw) => {
        const message = JSON.parse(raw);
        replacement.send(JSON.stringify({ id: message.id, result: "reconnected" }));
    });
    assert.equal((await send("two")).result, "reconnected");
});
