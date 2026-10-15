import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { resolve } from "node:path";
import { getConfig, root } from "./config.js";
import { operationId } from "./journal.js";

const config = await getConfig();
export async function request(path: string, body?: unknown): Promise<Record<string, unknown>> {
    const id = path === "/command" ? operationId() : undefined;
    if (id && body && typeof body === "object") body = { ...body, operationId: id };
    try {
        const response = await fetch(`http://127.0.0.1:${config.port}${path}`, {
            method: body ? "POST" : "GET",
            // Do not reuse a pooled HTTP socket across bridge restarts. Never replay browser commands.
            headers: {
                Authorization: `Bearer ${config.token}`,
                "Content-Type": "application/json",
                Connection: "close",
            },
            body: body ? JSON.stringify(body) : undefined,
            signal: AbortSignal.timeout(body ? 35_000 : 1500),
        });
        const data = (await response.json()) as Record<string, unknown>;
        if (!response.ok) {
            throw new Error(String(data.error ?? `HTTP ${response.status}`));
        }
        return data;
    } catch (error) {
        throw new Error(
            `${error instanceof Error ? error.message : String(error)}${id ? ` Operation ID: ${id}. Query browser_action_status; do not blindly repeat the action.` : ""}`,
        );
    }
}

export async function ensureBridge(): Promise<void> {
    try {
        const health = await request("/health");
        if (health.service !== "browser-control-mcp") {
            throw new Error("Unexpected service on bridge port");
        }
        return;
    } catch {
        /* Start a local process; a competing process may already be starting. */
    }
    const child = spawn(process.execPath, [resolve(root, "dist/server.js"), "--bridge"], {
        detached: true,
        stdio: "ignore",
    });
    child.unref();
    for (let attempt = 0; attempt < 30; attempt++) {
        await delay(100);
        try {
            if ((await request("/health")).service === "browser-control-mcp") {
                return;
            }
        } catch {
            /* Retry startup only. */
        }
    }
    throw new Error(`Cannot start local bridge on 127.0.0.1:${config.port}. Check for a port conflict.`);
}
