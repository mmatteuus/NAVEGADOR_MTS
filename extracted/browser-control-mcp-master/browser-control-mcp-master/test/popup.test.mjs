import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

test("popup contains only connection and cleanup controls", async (t) => {
    const browser = await chromium.launch({ headless: true });
    t.after(() => browser.close());
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setContent(
        (await readFile(resolve("extension/popup.html"), "utf8")).replace('<script src="popup.js"></script>', ""),
    );
    await page.evaluate(() => {
        window.messages = [];
        window.chrome = {
            runtime: {
                sendMessage: async (message) => {
                    window.messages.push(message);
                    if (message.type === "status") return { enabled: true, idleHours: 4, state: "Connected" };
                    return { ok: true };
                },
            },
        };
    });
    await page.addScriptTag({ path: resolve("extension/popup.js") });
    await page.waitForFunction(() => document.querySelector("#status").textContent === "Connected");
    assert.equal(await page.locator("#tab-status,#tab-control,#site-permission,select").count(), 0);
    assert.equal(await page.locator("button").count(), 2);
    await page.getByRole("button", { name: "Save timeout" }).click();
    const messages = await page.evaluate(() => window.messages);
    assert.ok(messages.some((message) => message.type === "cleanup-settings"));
    assert.ok(messages.every((message) => ["status", "toggle", "cleanup-settings"].includes(message.type)));
    assert.deepEqual(errors, []);
});
