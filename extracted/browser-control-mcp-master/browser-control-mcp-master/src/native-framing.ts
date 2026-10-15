import { endianness } from "node:os";
const little = endianness() === "LE";
export function frame(value: unknown): Buffer {
    const body = Buffer.from(JSON.stringify(value));
    if (body.length > 1024 * 1024) throw new Error("Native host message exceeds 1 MB");
    const header = Buffer.alloc(4);
    if (little) header.writeUInt32LE(body.length);
    else header.writeUInt32BE(body.length);
    return Buffer.concat([header, body]);
}
export function decoder(receive: (value: unknown) => void) {
    let pending: Buffer = Buffer.alloc(0);
    return (chunk: Buffer) => {
        pending = Buffer.concat([pending, chunk]);
        while (pending.length >= 4) {
            const size = little ? pending.readUInt32LE() : pending.readUInt32BE();
            if (!size || size > 16 * 1024 * 1024) throw new Error("Invalid native message size");
            if (pending.length < size + 4) return;
            const body = pending.subarray(4, size + 4);
            pending = pending.subarray(size + 4);
            receive(JSON.parse(body.toString("utf8")));
        }
    };
}
