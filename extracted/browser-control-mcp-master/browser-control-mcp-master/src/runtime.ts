import { fork, type ChildProcess } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { root } from "./config.js";
import type { Content } from "./cua.js";

export function createRuntime() {
    let child: ChildProcess | undefined;
    let busy = false;
    function reset(): void {
        child?.kill("SIGKILL");
        child = undefined;
    }
    async function run(code: string, timeoutMs: number): Promise<{ content: Content[]; isError?: boolean }> {
        if (busy) {
            throw new Error("A browser script is already running in this MCP session.");
        }
        busy = true;
        if (!child) {
            child = fork(resolve(root, "dist/runtime-worker.js"), [], {
                stdio: ["ignore", "ignore", "ignore", "ipc"],
                execArgv: [],
            });
        }
        const process = child;
        try {
            return await new Promise((resolveResult, reject) => {
                const id = randomUUID();
                const cleanup = (): void => {
                    clearTimeout(timer);
                    process.off("message", message);
                    process.off("exit", exit);
                    process.off("error", error);
                };
                const message = (response: { id: string; content?: Content[]; error?: string }): void => {
                    if (response.id !== id) {
                        return;
                    }
                    cleanup();
                    const content = response.content ?? [];
                    if (response.error) {
                        content.push({ type: "text", text: response.error });
                    }
                    if (!content.length) {
                        content.push({
                            type: "text",
                            text: "Script completed. Use nodeRepl.write(value) to return values.",
                        });
                    }
                    resolveResult({ content, ...(response.error ? { isError: true } : {}) });
                };
                const exit = (): void => {
                    cleanup();
                    if (child === process) {
                        child = undefined;
                    }
                    reject(
                        new Error(
                            "Browser script runtime stopped. Variables were reset; inspect any in-progress action before retrying.",
                        ),
                    );
                };
                const error = (cause: Error): void => {
                    cleanup();
                    reset();
                    reject(cause);
                };
                const timer = setTimeout(() => {
                    cleanup();
                    reset();
                    reject(
                        new Error(
                            "Browser script timed out and its runtime was reset. Browser actions already sent may still finish; inspect the page before retrying.",
                        ),
                    );
                }, timeoutMs);
                process.on("message", message);
                process.once("exit", exit);
                process.once("error", error);
                process.send({ id, code }, (cause) => {
                    if (cause) {
                        error(cause);
                    }
                });
            });
        } finally {
            busy = false;
        }
    }
    return { run, reset };
}
