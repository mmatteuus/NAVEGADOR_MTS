import { randomBytes } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";
import { homedir } from "node:os";

export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
// Preserve checkout installations; npm/npx installs share stable user-owned state.
export const dataDirectory = process.env.BROWSER_CONTROL_HOME
    ? resolve(process.env.BROWSER_CONTROL_HOME)
    : existsSync(resolve(root, ".local")) || existsSync(resolve(root, "src"))
      ? resolve(root, ".local")
      : resolve(homedir(), ".local/share/browser-control-mcp");
export const configPath = resolve(dataDirectory, "config.json");
export interface Config {
    port: number;
    token: string;
}

export async function getConfig(): Promise<Config> {
    await mkdir(dirname(configPath), { recursive: true, mode: 0o700 });
    try {
        await writeFile(configPath, JSON.stringify({ port: 18925, token: randomBytes(32).toString("hex") }, null, 2), {
            flag: "wx",
            mode: 0o600,
        });
    } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "EEXIST") {
            throw error;
        }
    }
    const config = JSON.parse(await readFile(configPath, "utf8")) as Config;
    if (
        !Number.isInteger(config.port) ||
        config.port < 1024 ||
        config.port > 65535 ||
        !/^[a-f0-9]{64}$/.test(config.token)
    ) {
        throw new Error(`Invalid config: ${configPath}`);
    }
    return config;
}
