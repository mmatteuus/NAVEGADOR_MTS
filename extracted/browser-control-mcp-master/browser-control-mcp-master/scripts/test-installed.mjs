import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { createServer } from "node:net";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const directory = process.argv[2];
if (!directory) throw new Error("Usage: node scripts/test-installed.mjs INSTALLED_PACKAGE_DIRECTORY");
process.env.BROWSER_CONTROL_HOME = await mkdtemp(resolve(tmpdir(), "browser-control-smoke-"));
const load = (name) => import(pathToFileURL(resolve(directory, "dist", name)).href);
const { getConfig, configPath, dataDirectory } = await load("config.js");
const config = await getConfig();
const probe = createServer();
await new Promise((done) => probe.listen(0, "127.0.0.1", done));
config.port = probe.address().port;
await new Promise((done) => probe.close(done));
await writeFile(configPath, JSON.stringify(config));
const { startBridge } = await load("bridge.js");
const bridge = await startBridge(config);
const client = new Client({ name: "installed-package-smoke", version: "1" });
try {
    const cli = resolve(directory, "bin/browser-control-mcp.mjs");
    const { stdout } = await promisify(execFile)(process.execPath, [cli, "--setup"]);
    assert.match(stdout, /mcpServers/);
    assert.ok(stdout.includes(dataDirectory));
    for (const browser of ["chrome", "firefox"]) {
        const generated = JSON.parse(
            await readFile(resolve(dataDirectory, "extensions", browser, "connection.json"), "utf8"),
        );
        assert.equal(generated.token, config.token);
        assert.equal(generated.port, config.port);
    }
    await client.connect(
        new StdioClientTransport({
            command: process.execPath,
            args: [cli],
            env: { BROWSER_CONTROL_HOME: dataDirectory },
        }),
    );
    const { tools } = await client.listTools();
    assert.ok(tools.some((tool) => tool.name === "browser_snapshot"));
    const result = await client.callTool({ name: "browser_list", arguments: {} });
    assert.notEqual(result.isError, true, JSON.stringify(result.content));
    const runtime = await client.callTool({ name: "browser_run", arguments: { code: "nodeRepl.write(2 + 2)" } });
    assert.notEqual(runtime.isError, true);
    assert.ok(JSON.stringify(runtime.content).includes("4"));
    console.log(
        "Installed package: setup, paired extensions, MCP discovery, bridge request and script runtime passed.",
    );
} finally {
    await client.close();
    await bridge.close();
}
