import test from "node:test";
import assert from "node:assert/strict";
import { decoder, frame } from "../dist/native-framing.js";
test("native framing handles fragmented UTF-8, multiple messages and size limits", () => {
    const received = [];
    const decode = decoder((value) => received.push(value));
    const bytes = Buffer.concat([frame({ text: "🔒 héllo" }), frame({ result: true })]);
    for (const byte of bytes) decode(Buffer.from([byte]));
    assert.deepEqual(received, [{ text: "🔒 héllo" }, { result: true }]);
    assert.throws(() => frame({ text: "x".repeat(1024 * 1024) }), /exceeds/);
    assert.throws(() => decoder(() => {})(Buffer.from([255, 255, 255, 255])), /Invalid/);
});
