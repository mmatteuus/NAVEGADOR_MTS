import { mkdir, readFile, writeFile, chmod } from "node:fs/promises";
import { homedir } from "node:os";
import { resolve } from "node:path";
import { root, dataDirectory } from "../dist/config.js";

const [browser, extensionId, customDirectory] = process.argv.slice(2);
if (
    process.platform !== "linux" ||
    !["chrome", "chromium", "helium", "firefox"].includes(browser) ||
    (browser !== "firefox" && !/^[a-p]{32}$/.test(extensionId ?? ""))
) {
    throw new Error(
        "Usage (Linux): node scripts/install-native.mjs chrome|chromium|helium EXTENSION_ID [USER_DATA_DIRECTORY]; or firefox",
    );
}
const directory =
    browser === "firefox"
        ? resolve(homedir(), ".mozilla/native-messaging-hosts")
        : resolve(
              customDirectory ?? resolve(homedir(), ".config", browser === "chrome" ? "google-chrome" : browser),
              "NativeMessagingHosts",
          );
const launcher = resolve(dataDirectory, "native-host");
const manifestPath = resolve(directory, "dev.local_browser_control.json");
try {
    const existing = JSON.parse(await readFile(manifestPath, "utf8"));
    if (existing.path !== launcher)
        throw new Error("A different native host is installed here; refusing to overwrite it.");
} catch (error) {
    if (error.code !== "ENOENT") throw error;
}
await mkdir(dataDirectory, { recursive: true, mode: 0o700 });
const quote = (value) => `'${value.replaceAll("'", "'\\''")}'`;
await writeFile(
    launcher,
    `#!/bin/sh\nexport BROWSER_CONTROL_HOME=${quote(dataDirectory)}\nexec ${quote(process.execPath)} ${quote(resolve(root, "dist/native-host.js"))} "$@"\n`,
    { mode: 0o700 },
);
await chmod(launcher, 0o700);
await mkdir(directory, { recursive: true, mode: 0o700 });
await writeFile(
    manifestPath,
    JSON.stringify(
        {
            name: "dev.local_browser_control",
            description: "Local browser-control MCP pipe transport",
            path: launcher,
            type: "stdio",
            ...(browser === "firefox"
                ? { allowed_extensions: ["browser-control@local.invalid"] }
                : { allowed_origins: [`chrome-extension://${extensionId}/`] }),
        },
        null,
        2,
    ),
    { mode: 0o600 },
);
console.log(`Installed ${manifestPath}. Reload the extension; its popup reports the selected transport.`);
