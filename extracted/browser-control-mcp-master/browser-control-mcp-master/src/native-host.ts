import { WebSocket } from "ws";
import { getConfig } from "./config.js";
import { ensureBridge } from "./connection.js";
import { decoder, frame } from "./native-framing.js";
import type { Config } from "./config.js";
import { pathToFileURL } from "node:url";

// Browser-facing transport is an OS pipe. The host retains the existing local
// authenticated bridge behind it; it never uses a remote socket or replays work.
export function runNativeHost(config: Config) {
    const socket = new WebSocket(`ws://127.0.0.1:${config.port}/extension`, {
        origin: "chrome-extension://native-host",
    });
    const stop = () => {
        socket.terminate();
        process.exit(0);
    };
    const send = (value: unknown) => {
        try {
            if (!process.stdout.write(frame(value))) socket.pause();
        } catch {
            stop();
        }
    };
    process.stdout.on("drain", () => socket.resume());
    process.stdout.on("error", stop);
    socket.on("open", () => {
        send({ type: "native-open" });
        process.stdin.resume();
    });
    socket.on("message", (data) => {
        try {
            send(JSON.parse(data.toString()));
        } catch {
            stop();
        }
    });
    socket.on("close", stop);
    socket.on("error", stop);
    const consume = decoder((value) => {
        if (socket.readyState !== WebSocket.OPEN) throw new Error("Bridge not connected");
        socket.send(JSON.stringify(value));
    });
    process.stdin.on("data", (chunk: Buffer) => {
        try {
            consume(chunk);
        } catch {
            stop();
        }
    });
    process.stdin.on("end", stop);
    process.stdin.on("error", stop);
    process.stdin.pause();
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    await ensureBridge();
    runNativeHost(await getConfig());
}
