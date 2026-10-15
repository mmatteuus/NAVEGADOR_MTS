import { createServer, type IncomingMessage } from "node:http";
import { timingSafeEqual } from "node:crypto";
import { resolve } from "node:path";
import { WebSocketServer, WebSocket } from "ws";
import type { Config } from "./config.js";
import { dataDirectory } from "./config.js";
import { createJournal, operationId } from "./journal.js";

interface Peer {
    id: string;
    browser: string;
    name: string;
    socket: WebSocket;
    seen: number;
}
interface Pending {
    peer: Peer;
    resolve: (value: unknown) => void;
    reject: (error: Error) => void;
    timer: NodeJS.Timeout;
}

export async function startBridge(config: Config, journalDirectory = resolve(dataDirectory, `actions-${config.port}`)) {
    const journal = createJournal(journalDirectory, config.token);
    await journal.cleanup();
    const peers = new Map<string, Peer>();
    const pending = new Map<string, Pending>();
    const events: { type: string; browser: string; tabId: number; at: number }[] = [];
    const validToken = (token: string): boolean => {
        const actual = Buffer.from(token);
        const expected = Buffer.from(config.token);
        return actual.length === expected.length && timingSafeEqual(actual, expected);
    };
    const authorised = (req: IncomingMessage): boolean =>
        validToken((req.headers.authorization ?? "").replace(/^Bearer /, ""));
    const failPeer = (peer: Peer): void => {
        if (peers.get(peer.id) === peer) {
            peers.delete(peer.id);
        }
        for (const [id, item] of pending) {
            if (item.peer !== peer) {
                continue;
            }
            clearTimeout(item.timer);
            pending.delete(id);
            item.reject(
                new Error("Browser disconnected. Action outcome is unknown; inspect the page before retrying."),
            );
        }
    };
    const server = createServer(async (req, res) => {
        res.setHeader("Content-Type", "application/json");
        // Browser pages cannot call this API, even if they learn its address.
        if (req.headers.origin || !authorised(req)) {
            res.writeHead(403).end(JSON.stringify({ error: "Forbidden" }));
            return;
        }
        if (req.url === "/health" && req.method === "GET") {
            res.end(
                JSON.stringify({
                    service: "browser-control-mcp",
                    browsers: [...peers.values()].map(({ id, browser, name }) => ({ id, browser, name })),
                }),
            );
            return;
        }
        if (req.url === "/events" && req.method === "GET") {
            res.end(JSON.stringify({ result: events.filter((event) => Date.now() - event.at < 600_000) }));
            return;
        }
        if (req.url?.startsWith("/actions/") && req.method === "GET") {
            try {
                const entry = await journal.status(req.url.slice("/actions/".length));
                res.end(
                    JSON.stringify({
                        result: entry
                            ? {
                                  operationId: entry.id,
                                  phase: entry.phase,
                                  pending: pending.has(entry.id),
                                  updatedAt: entry.updatedAt,
                                  guidance:
                                      "Never replay this ID. Completed means a reply arrived, not that a website saved the change. Inspect the page if the result was lost.",
                              }
                            : {
                                  phase: "not-found",
                                  guidance:
                                      "No durable record found; inspect the page before starting a new operation.",
                              },
                    }),
                );
            } catch {
                res.writeHead(400).end(
                    JSON.stringify({
                        error: "Invalid, expired or unreadable operation record; inspect before retrying.",
                    }),
                );
            }
            return;
        }
        if (req.url !== "/command" || req.method !== "POST") {
            res.writeHead(404).end("{}");
            return;
        }
        let trackedId: string | undefined;
        let claimed = false;
        try {
            let body = "";
            for await (const chunk of req) {
                body += chunk.toString();
                if (Buffer.byteLength(body) > 1024 * 1024) {
                    throw new Error("Request exceeds 1 MB");
                }
            }
            const { browser, action, args = {}, operationId: suppliedId } = JSON.parse(body);
            if (typeof action !== "string" || !args || typeof args !== "object" || Array.isArray(args)) {
                throw new Error("Invalid command");
            }
            const matches = [...peers.values()].filter(
                (peer) => !browser || peer.id === browser || peer.browser === browser,
            );
            if (matches.length !== 1) {
                throw new Error(
                    matches.length
                        ? "Multiple browsers match. Use the browser id from browser_list."
                        : "No connected browser. Load the extension and enable its connection.",
                );
            }
            const peer = matches[0];
            const id = suppliedId ?? operationId();
            if (typeof id !== "string") throw new Error("Invalid operation ID");
            trackedId = id;
            if (!(await journal.claim(id, { browser: peer.id, action, args }))) {
                throw new Error(
                    "Operation already recorded and will not be dispatched again. Query browser_action_status and inspect the page.",
                );
            }
            claimed = true;
            await journal.phase(id, "dispatched");
            const result = await new Promise<unknown>((resolve, reject) => {
                const timer = setTimeout(() => {
                    pending.delete(id);
                    reject(
                        new Error(
                            "Browser request timed out. Action outcome is unknown; inspect the page before retrying.",
                        ),
                    );
                }, 30_000);
                pending.set(id, { peer, resolve, reject, timer });
                peer.socket.send(JSON.stringify({ id, action, args, expiresAt: Date.now() + 29_000 }), (error) => {
                    if (error) {
                        clearTimeout(timer);
                        pending.delete(id);
                        reject(error);
                    }
                });
            });
            await journal.phase(id, "completed");
            res.end(JSON.stringify({ result }));
        } catch (error) {
            if (claimed && trackedId) {
                const phase = (error as { phase?: string }).phase === "rejected" ? "rejected" : "unknown";
                try {
                    await journal.phase(trackedId, phase);
                } catch {
                    /* Preserve the original error; stale dispatched means unknown, never retry. */
                }
            }
            res.writeHead(400).end(
                JSON.stringify({
                    error: `${error instanceof Error ? error.message : String(error)}${trackedId ? ` Operation ID: ${trackedId}` : ""}`,
                }),
            );
        }
    });
    const wss = new WebSocketServer({ noServer: true, maxPayload: 16 * 1024 * 1024 });
    server.on("upgrade", (req, socket, head) => {
        const origin = req.headers.origin ?? "";
        if (process.env.BROWSER_CONTROL_DEBUG) {
            console.error("[bridge] WebSocket origin:", origin);
        }
        if (req.url !== "/extension" || !/^(chrome|moz)-extension:\/\/[^/]+$/.test(origin)) {
            socket.end("HTTP/1.1 403 Forbidden\r\n\r\n");
            return;
        }
        wss.handleUpgrade(req, socket, head, (ws) => wss.emit("connection", ws));
    });
    wss.on("connection", (socket) => {
        let peer: Peer | undefined;
        const authTimer = setTimeout(() => socket.close(1008, "Authentication required"), 5000);
        socket.on("error", () => socket.terminate());
        socket.on("message", (raw) => {
            try {
                const data = JSON.parse(raw.toString());
                if (!peer) {
                    if (
                        data.type !== "hello" ||
                        typeof data.token !== "string" ||
                        !validToken(data.token) ||
                        typeof data.id !== "string" ||
                        data.id.length > 128 ||
                        !["chrome", "firefox"].includes(data.browser)
                    ) {
                        socket.close(1008, "Invalid authentication");
                        return;
                    }
                    clearTimeout(authTimer);
                    const old = peers.get(data.id);
                    if (old) {
                        failPeer(old);
                        old.socket.close(1000, "Replaced");
                    }
                    peer = {
                        id: data.id,
                        browser: data.browser,
                        name: String(data.name ?? data.browser).slice(0, 100),
                        socket,
                        seen: Date.now(),
                    };
                    peers.set(peer.id, peer);
                    socket.send(JSON.stringify({ type: "ready" }));
                    return;
                }
                peer.seen = Date.now();
                if (data.type === "ping") {
                    socket.send(JSON.stringify({ type: "pong" }));
                    return;
                }
                if (data.type === "takeover" && Number.isInteger(data.tabId)) {
                    events.push({ type: "human-takeover", browser: peer.id, tabId: data.tabId, at: Date.now() });
                    if (events.length > 100) events.shift();
                    return;
                }
                const item = pending.get(data.id);
                if (!item || item.peer !== peer) {
                    return;
                }
                clearTimeout(item.timer);
                pending.delete(data.id);
                if (typeof data.error === "string") {
                    item.reject(
                        Object.assign(new Error(data.error), {
                            phase: data.phase === "rejected" ? "rejected" : "unknown",
                        }),
                    );
                } else {
                    item.resolve(data.result ?? null);
                }
            } catch {
                socket.close(1008, "Invalid message");
            }
        });
        socket.on("close", () => {
            clearTimeout(authTimer);
            if (peer) {
                failPeer(peer);
            }
        });
    });
    const heartbeat = setInterval(() => {
        for (const peer of peers.values()) {
            if (Date.now() - peer.seen > 45_000) {
                failPeer(peer);
                peer.socket.terminate();
            }
        }
    }, 15_000);
    const journalCleanup = setInterval(() => {
        void journal.cleanup().catch(() => {});
    }, 600_000);
    try {
        await new Promise<void>((resolve, reject) => {
            server.once("error", reject);
            server.listen(config.port, "127.0.0.1", resolve);
        });
    } catch (error) {
        clearInterval(heartbeat);
        clearInterval(journalCleanup);
        wss.close();
        throw error;
    }
    return {
        close: async (): Promise<void> => {
            clearInterval(heartbeat);
            clearInterval(journalCleanup);
            for (const socket of wss.clients) {
                socket.terminate();
            }
            wss.close();
            await new Promise<void>((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
        },
    };
}
