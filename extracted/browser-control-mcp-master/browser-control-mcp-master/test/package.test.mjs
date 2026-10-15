import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, stat, symlink, cp } from "node:fs/promises";
import { tmpdir, homedir } from "node:os";
import { resolve } from "node:path";
import { buildExtensions } from "../scripts/extensions.mjs";
import { root } from "../dist/config.js";

test("release extensions contain no secret; CLI pairs locally and refuses a different installation", async () => {
    const directory = await mkdtemp(resolve(tmpdir(), "browser-control-package-"));
    await buildExtensions(directory);
    const env = { ...process.env, BROWSER_CONTROL_HOME: resolve(directory, "state") };
    const cli = resolve(root, "bin/browser-control-mcp.mjs");
    assert.match(execFileSync(process.execPath, [cli, "--help"], { env, encoding: "utf8" }), /--pair-extension/);
    for (const browser of ["chrome", "firefox"]) {
        const extension = resolve(directory, browser);
        const path = resolve(extension, "connection.json");
        assert.equal(JSON.parse(await readFile(path, "utf8")).token, null);
        const manifest = JSON.parse(await readFile(resolve(extension, "manifest.json"), "utf8"));
        assert.equal(manifest.version, JSON.parse(await readFile(resolve(root, "package.json"), "utf8")).version);
        for (const script of manifest.background.scripts ?? [manifest.background.service_worker]) {
            await stat(resolve(extension, script));
        }
        execFileSync(process.execPath, [cli, "--pair-extension", extension], { env });
        const config = JSON.parse(await readFile(path, "utf8"));
        assert.match(config.token, /^[a-f0-9]{64}$/);
        assert.equal(config.browser, browser);
        assert.equal(
            config.token,
            JSON.parse(await readFile(resolve(env.BROWSER_CONTROL_HOME, "config.json"), "utf8")).token,
        );
        execFileSync(process.execPath, [cli, "--pair-extension", extension], { env });
        assert.throws(
            () =>
                execFileSync(process.execPath, [cli, "--pair-extension", extension], {
                    env: { ...env, BROWSER_CONTROL_HOME: resolve(directory, "other-state") },
                    stdio: "pipe",
                }),
            /another installation/,
        );
        assert.equal(JSON.parse(await readFile(path, "utf8")).token, config.token);
    }
    assert.throws(() => execFileSync(process.execPath, [cli, "--unknown"], { env, stdio: "pipe" }), /Unknown argument/);
});

test("npm-style installs keep state outside the package and honour explicit overrides", async () => {
    const directory = await mkdtemp(resolve(tmpdir(), "browser-control-installed-"));
    await cp(resolve(root, "dist"), resolve(directory, "dist"), { recursive: true });
    await writeFile(resolve(directory, "package.json"), '{"type":"module"}');
    await symlink(resolve(root, "node_modules"), resolve(directory, "node_modules"));
    const run = (env) =>
        JSON.parse(
            execFileSync(
                process.execPath,
                [
                    "--input-type=module",
                    "-e",
                    'const {dataDirectory}=await import("./dist/config.js"); console.log(JSON.stringify(dataDirectory));',
                ],
                { cwd: directory, env, encoding: "utf8" },
            ),
        );
    const env = { ...process.env };
    delete env.BROWSER_CONTROL_HOME;
    assert.equal(run(env), resolve(homedir(), ".local/share/browser-control-mcp"));
    const override = resolve(directory, "override");
    assert.equal(run({ ...env, BROWSER_CONTROL_HOME: override }), override);
});
