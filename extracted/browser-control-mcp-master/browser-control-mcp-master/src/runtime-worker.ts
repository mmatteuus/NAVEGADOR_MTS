import { start } from "node:repl";
import { PassThrough } from "node:stream";
import { inspect } from "node:util";
import { AsyncLocalStorage } from "node:async_hooks";
import { createCua, type Content } from "./cua.js";

const input = new PassThrough();
const output = new PassThrough();
output.resume();
const cell = new AsyncLocalStorage<string>();
let currentId: string | undefined;
let finish: ((error?: unknown) => void) | undefined;
const repl = start({
    prompt: "",
    input,
    output,
    terminal: false,
    useGlobal: false,
    // The default REPL evaluator sends uncaught throws to its writer, not its callback.
    // Direct eval calls do not send successful return values to this writer.
    writer(value) {
        if (cell.getStore() === currentId) {
            finish?.(value instanceof Error ? value : new Error(String(value)));
        }
        return "";
    },
});
let items: Content[] = [];
let active = false;
let bytes = 0;
const emit = (content: Content): void => {
    if (!active || cell.getStore() !== currentId) {
        return;
    }
    bytes += Buffer.byteLength(JSON.stringify(content));
    if (bytes > 16 * 1024 * 1024) {
        throw new Error("Script output exceeds 16 MB.");
    }
    items.push(content);
};
const write = (value: unknown): void =>
    emit({
        type: "text",
        text:
            typeof value === "string"
                ? value
                : inspect(value, { depth: 8, maxArrayLength: 100, maxStringLength: 100000 }),
    });
repl.context.cua = createCua(emit);
repl.context.nodeRepl = {
    write,
    async emitImage(value: Uint8Array | { bytes: Uint8Array; mimeType?: string } | string) {
        if (typeof value === "string") {
            const match = /^data:(image\/[\w+.-]+);base64,([A-Za-z0-9+/=]+)$/.exec(value);
            if (!match) {
                throw new Error("emitImage accepts image bytes or a base64 data URL.");
            }
            emit({ type: "image", mimeType: match[1], data: match[2] });
            return;
        }
        const wrapped = "bytes" in value ? value : { bytes: value, mimeType: "image/png" };
        emit({
            type: "image",
            mimeType: wrapped.mimeType ?? "image/png",
            data: Buffer.from(wrapped.bytes).toString("base64"),
        });
    },
};
repl.context.console = {
    log: (...args: unknown[]) =>
        write(args.map((value) => (typeof value === "string" ? value : inspect(value))).join(" ")),
    error: write,
    warn: write,
    info: write,
};
process.on("message", (message: { id: string; code: string }) => {
    if (active) {
        process.send?.({ id: message.id, error: "A script is already running." });
        return;
    }
    active = true;
    currentId = message.id;
    items = [];
    bytes = 0;
    const complete = (error?: unknown) => {
        if (!active || currentId !== message.id) {
            return;
        }
        active = false;
        process.send?.({ id: message.id, content: items, error: error == null ? undefined : String(error) });
        items = [];
        finish = undefined;
    };
    finish = complete;
    cell.run(message.id, () => {
        repl.eval(message.code + "\n", repl.context, "browser-run", complete);
    });
});
process.on("disconnect", () => process.exit(0));
