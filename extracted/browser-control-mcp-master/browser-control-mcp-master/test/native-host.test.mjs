import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { once } from "node:events";
import { startBridge } from "../dist/bridge.js";
import { decoder, frame } from "../dist/native-framing.js";
import { operationId } from "../dist/journal.js";

test("native pipe routes authenticated commands and recovery refuses duplicate dispatch", async (t) => {
    const config = { port: 19829, token: randomBytes(32).toString("hex") };
    const directory = await mkdtemp(join(tmpdir(), "native-bridge-"));
    let bridge = await startBridge(config, directory);
    t.after(() => bridge.close());
    let dispatched = 0;
    const host = spawn(
        process.execPath,
        [
            "--input-type=module",
            "-e",
            `import {runNativeHost} from './dist/native-host.js';runNativeHost(${JSON.stringify(config)});`,
        ],
        { stdio: ["pipe", "pipe", "pipe"] },
    );
    t.after(() => host.kill());
    let ready;
    const connected = new Promise((resolve) => {
        ready = resolve;
    });
    const consume = decoder((message) => {
        if (message.type === "native-open")
            host.stdin.write(frame({ type: "hello", id: "native-test", browser: "chrome", token: config.token }));
        else if (message.type === "ready") ready();
        else if (message.id) {
            dispatched++;
            if (message.action === "drop-reply") {
                host.stdin.end();
                return;
            }
            host.stdin.write(frame({ id: message.id, result: { clicked: true } }));
        }
    });
    host.stdout.on("data", consume);
    await Promise.race([
        connected,
        new Promise((_, reject) => {
            const timer = setTimeout(() => reject(Error("Native handshake timed out")), 5000);
            timer.unref();
        }),
    ]);
    const headers = {
        Authorization: `Bearer ${config.token}`,
        "Content-Type": "application/json",
        Connection: "close",
    };
    const id = operationId();
    const command = () =>
        fetch(`http://127.0.0.1:${config.port}/command`, {
            method: "POST",
            headers,
            body: JSON.stringify({ operationId: id, browser: "native-test", action: "click", args: { tabId: 1 } }),
        }).then((res) => res.json());
    assert.deepEqual((await command()).result, { clicked: true });
    assert.match((await command()).error, /already recorded/);
    assert.equal(dispatched, 1);
    const status = () => fetch(`http://127.0.0.1:${config.port}/actions/${id}`, { headers }).then((res) => res.json());
    assert.equal((await status()).result.phase, "completed");
    const exited = once(host, "exit");
    const lost = operationId();
    const dropped = await fetch(`http://127.0.0.1:${config.port}/command`, {
        method: "POST",
        headers,
        body: JSON.stringify({ operationId: lost, browser: "native-test", action: "drop-reply" }),
    }).then((res) => res.json());
    assert.match(dropped.error, /unknown/);
    await bridge.close();
    await exited;
    bridge = await startBridge(config, directory);
    assert.equal(
        (await status()).result.phase,
        "completed",
        "Recovery metadata survives bridge and native host restart",
    );
    const recovered = await fetch(`http://127.0.0.1:${config.port}/actions/${lost}`, { headers }).then((res) =>
        res.json(),
    );
    assert.equal(recovered.result.phase, "unknown", "Lost reply remains unknown after restart, never replayed");
});
