import test from "node:test";
import assert from "node:assert/strict";
import { chromium } from "playwright";
import { resolve } from "node:path";
test("local screenshot masking covers sensitive rectangles at scaled pixel ratios", async (t) => {
    const browser = await chromium.launch({ headless: true });
    t.after(() => browser.close());
    const page = await browser.newPage();
    await page.addScriptTag({ path: resolve("extension/capture.js") });
    const pixels = await page.evaluate(async () => {
        const canvas = new OffscreenCanvas(200, 100);
        const context = canvas.getContext("2d");
        context.fillStyle = "white";
        context.fillRect(0, 0, 200, 100);
        const bytes = new Uint8Array(await (await canvas.convertToBlob()).arrayBuffer());
        const input = `data:image/png;base64,${btoa(String.fromCharCode(...bytes))}`;
        const output = await globalThis.browserControlMaskCapture(input, {
            width: 100,
            height: 50,
            rectangles: [{ x: 10, y: 10, width: 20, height: 10 }],
        });
        const result = await createImageBitmap(
            new Blob([Uint8Array.from(atob(output.split(",")[1]), (char) => char.charCodeAt(0))], {
                type: "image/png",
            }),
        );
        context.drawImage(result, 0, 0);
        return {
            masked: [...context.getImageData(30, 30, 1, 1).data],
            outside: [...context.getImageData(90, 70, 1, 1).data],
        };
    });
    assert.deepEqual(pixels.masked, [23, 23, 23, 255]);
    assert.deepEqual(pixels.outside, [255, 255, 255, 255]);
});
