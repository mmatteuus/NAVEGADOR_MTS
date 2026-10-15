import { mkdir, copyFile, writeFile, unlink, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { root } from "../dist/config.js";

export async function buildExtensions(output, config = null) {
    const { version } = JSON.parse(await readFile(resolve(root, "package.json"), "utf8"));
    for (const browser of ["chrome", "firefox"]) {
        const directory = resolve(output, browser);
        await mkdir(directory, { recursive: true });
        await unlink(resolve(directory, "policy.js")).catch((error) => {
            if (error.code !== "ENOENT") throw error;
        });
        const manifest = {
            manifest_version: browser === "chrome" ? 3 : 2,
            name: "Local Browser Control",
            version,
            description: "Connect this browser to your local browser-control MCP server.",
            permissions: [
                "tabs",
                "activeTab",
                "tabGroups",
                "scripting",
                "storage",
                "alarms",
                "webNavigation",
                "nativeMessaging",
                ...(browser === "firefox" ? ["<all_urls>"] : ["debugger"]),
            ],
            ...(browser === "chrome" ? { host_permissions: ["<all_urls>"] } : {}),
            background:
                browser === "chrome"
                    ? { service_worker: "background.js" }
                    : {
                          scripts: [
                              "keys.js",
                              "trusted.js",
                              "sessions.js",
                              "control.js",
                              "transport.js",
                              "capture.js",
                              "background.js",
                          ],
                      },
            [browser === "chrome" ? "action" : "browser_action"]: { default_popup: "popup.html" },
            content_security_policy:
                browser === "chrome"
                    ? { extension_pages: "script-src 'self'; object-src 'self'; connect-src 'self' ws://127.0.0.1:*" }
                    : "script-src 'self'; object-src 'self'; connect-src 'self' ws://127.0.0.1:*",
            ...(browser === "chrome"
                ? { minimum_chrome_version: "120" }
                : {
                      browser_specific_settings: {
                          gecko: {
                              id: "browser-control@local.invalid",
                              strict_min_version: "139.0",
                              data_collection_permissions: { required: ["none"] },
                          },
                      },
                  }),
        };
        await writeFile(resolve(directory, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
        // This installation-specific file stays in ignored build output.
        await writeFile(
            resolve(directory, "connection.json"),
            JSON.stringify(config ? { ...config, browser } : { browser, port: 18925, token: null }),
            { mode: 0o600 },
        );
        for (const file of [
            "background.js",
            "sessions.js",
            "control.js",
            "transport.js",
            "capture.js",
            "keys.js",
            "trusted.js",
            "input.js",
            "state.js",
            "verification.js",
            "content.js",
            "popup.html",
            "popup.js",
        ]) {
            await copyFile(resolve(root, "extension", file), resolve(directory, file));
        }
    }
}
