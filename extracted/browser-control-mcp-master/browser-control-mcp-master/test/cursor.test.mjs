import test from "node:test";
import assert from "node:assert/strict";
import { chromium } from "playwright";
import { resolve } from "node:path";

test("cursor stays visible, isolates page CSS, animates and pulses above dialogs", async (t) => {
    const browser = await chromium.launch({ headless: true });
    t.after(() => browser.close());
    const page = await browser.newPage();
    // Intercept a non-loopback HTTP origin: localhost is treated as a secure context.
    await page.route("http://192.0.2.1/**", (route) =>
        route.fulfill({ body: "<html></html>", contentType: "text/html" }),
    );
    await page.goto("http://192.0.2.1/ssl-warning");
    assert.deepEqual(await page.evaluate(() => [isSecureContext, typeof crypto.randomUUID]), [false, "undefined"]);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setContent(
        `<style>div { visibility:hidden!important; opacity:0!important; pointer-events:auto!important; } .cursor { display:none!important; }</style><button id="target">Target</button><dialog><button>Modal</button></dialog>`,
    );
    await page.evaluate(() => {
        const original = Element.prototype.attachShadow;
        Element.prototype.attachShadow = function (options) {
            const root = original.call(this, options);
            if (this.id === "local-browser-control-cursor") window.cursorRoot = root;
            return root;
        };
        window.chrome = {
            runtime: {
                id: "test",
                onMessage: {
                    addListener(listener) {
                        window.action = (action, args) =>
                            new Promise((resolve, reject) =>
                                listener({ type: "browser-control", action, args }, { id: "test" }, (value) =>
                                    value.error ? reject(Error(value.error)) : resolve(value.result),
                                ),
                            );
                    },
                },
            },
        };
    });
    for (const file of ["keys.js", "input.js", "state.js", "verification.js", "content.js"]) {
        await page.addScriptTag({ path: resolve("extension", file) });
    }
    assert.deepEqual(errors, [], "Content scripts must initialize on plain HTTP pages");
    await page.evaluate(() => {
        window.firstAction = window.action;
    });
    await page.addScriptTag({ path: resolve("extension/content.js") });
    assert.equal(
        await page.evaluate(() => window.action === window.firstAction),
        true,
        "Reinjection must not duplicate listeners",
    );
    await page.evaluate(() => window.action("move", { x: 100, y: 100 }));
    await page.waitForTimeout(2800);
    const visible = await page.evaluate(() => {
        const cursor = window.cursorRoot.querySelector(".cursor");
        return { opacity: getComputedStyle(cursor).opacity, visibility: getComputedStyle(cursor).visibility };
    });
    assert.equal(visible.opacity, "1", "Cursor must not disappear between actions");
    assert.equal(visible.visibility, "visible");
    for (const zoomFactor of [0.8, 1, 1.25, 1.5, 2]) {
        await page.evaluate((zoomFactor) => window.action("move", { x: 100, y: 100, zoomFactor }), zoomFactor);
        const height = await page.evaluate(
            () => window.cursorRoot.querySelector(".arrow").getBoundingClientRect().height,
        );
        assert.ok(Math.abs(height * zoomFactor - 24) < 0.1, `24 px cursor at zoom ${zoomFactor}`);
    }
    await page.evaluate(() => window.action("move", { x: 100, y: 100, zoomFactor: 1 }));
    await page.evaluate(() => document.querySelector("dialog").showModal());
    await page.evaluate(() => window.action("move", { x: 250, y: 180 }));
    const layer = await page.evaluate(() => {
        const host = document.querySelector("#local-browser-control-cursor");
        return {
            top: host.matches(":popover-open"),
            pointer: getComputedStyle(host).pointerEvents,
            width: host.getBoundingClientRect().width,
            animated: window.cursorRoot.querySelector(".cursor").getAnimations().length > 0,
        };
    });
    assert.equal(layer.top, true);
    assert.equal(layer.pointer, "none");
    assert.equal(layer.width, 1280);
    assert.equal(layer.animated, true);
    await page.evaluate(() => document.querySelector("dialog").close());
    const clickStarted = Date.now();
    await page.evaluate(() => window.action("click", { selector: "#target" }));
    assert.ok(Date.now() - clickStarted >= 400, "Click waits for cursor arrival");
    assert.equal(await page.evaluate(() => window.cursorRoot.querySelector(".label")), null);
    assert.equal(await page.evaluate(() => window.cursorRoot.querySelectorAll(".pulse").length), 1);
    assert.equal(await page.evaluate(() => document.elementFromPoint(10, 10).id), "target");
    await page.screenshot({ path: "/tmp/browser-control-cursor.png" });
    for (const interact of [
        () => page.mouse.move(400, 400),
        () => page.mouse.click(410, 410),
        () => page.mouse.wheel(0, 30),
        () => page.keyboard.press("Shift"),
    ]) {
        await page.evaluate(() => window.action("move", { x: 100, y: 100 }));
        await interact();
        await page.waitForFunction(
            () => getComputedStyle(window.cursorRoot.querySelector(".cursor")).visibility === "hidden",
        );
        assert.equal(await page.evaluate(() => window.cursorRoot.querySelectorAll(".pulse").length), 0);
        await page.evaluate(() => window.action("snapshot", {}));
        assert.equal(
            await page.evaluate(() => getComputedStyle(window.cursorRoot.querySelector(".cursor")).visibility),
            "hidden",
        );
    }
    await page.evaluate(() => {
        window.pendingClick = window.action("click", { selector: "#target" }).then(
            () => "clicked",
            (error) => error.message,
        );
    });
    await page.mouse.move(450, 450);
    assert.match(await page.evaluate(() => window.pendingClick), /cancelled/);
    await page.evaluate(() => window.action("move", { x: 100, y: 100 }));
    assert.equal(
        await page.evaluate(() => getComputedStyle(window.cursorRoot.querySelector(".cursor")).visibility),
        "visible",
    );
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.evaluate(() => window.action("move", { x: 500, y: 300 }));
    assert.equal(
        await page.evaluate(() => getComputedStyle(window.cursorRoot.querySelector(".cursor")).transitionDuration),
        "0s",
    );
    await page.evaluate(() => window.action("click", { selector: "#target" }));
    assert.equal(
        await page.evaluate(() => getComputedStyle(window.cursorRoot.querySelector(".pulse")).animationName),
        "click-still",
    );
    await page.evaluate(() => {
        const area = document.createElement("section");
        area.id = "scroll-test";
        area.style.cssText = "overflow:auto;height:100px;width:200px;scrollbar-width:none";
        area.innerHTML =
            '<section style="height:600px;width:600px"><button style="margin-top:500px">Below fold</button></section>';
        document.body.append(area);
        document.body.style.minHeight = "2000px";
    });
    assert.equal(await page.evaluate(() => document.querySelector("style[data-browser-control-scrollbars]")), null);
    const scrolling = await page.evaluate(() => window.action("snapshot", { showScrollbars: true }));
    assert.equal(
        scrolling.nodes.find((node) => node.name === "Below fold" && node.role === "button").inViewport,
        false,
    );
    assert.ok(scrolling.scrollRegions.some((region) => region.page && region.directions.includes("down")));
    const nested = scrolling.scrollRegions.find((region) => !region.page && region.maxX > 0 && region.maxY > 0);
    assert.ok(nested);
    assert.deepEqual(nested.directions, ["down", "right"]);
    assert.equal(
        await page.evaluate(() => getComputedStyle(document.querySelector("#scroll-test")).scrollbarWidth),
        "auto",
    );
    await page.evaluate((ref) => window.action("scroll", { ref, direction: "down", pages: 20 }), nested.ref);
    const scrolled = await page.evaluate(() => window.action("snapshot", {}));
    const updated = scrolled.scrollRegions.find((region) => region.ref === nested.ref);
    assert.equal(updated.y, updated.maxY);
    assert.ok(updated.directions.includes("up"));
    assert.ok(!updated.directions.includes("down"));
    const outcomes = await page.evaluate(async () => {
        const field = document.createElement("input");
        field.id = "verify-field";
        field.type = "password";
        document.body.prepend(field);
        async function act(operation, args) {
            const id = await window.action("verification_begin", { operation, ...args });
            await window.action(operation, args);
            return window.action("verification_end", { id });
        }
        const success = await act("fill", { selector: "#verify-field", text: "private-test-value" });
        field.addEventListener("beforeinput", (event) => event.preventDefault());
        const blocked = await act("fill", { selector: "#verify-field", text: "different-private-value" });
        const noop = await act("click", { selector: "#target" });
        document.querySelector("#target").addEventListener("click", () =>
            setTimeout(() => {
                document.querySelector("#target").textContent = "Confirmed change";
            }, 300),
        );
        const expected = await act("click", { selector: "#target", expect: { text: "Confirmed change" } });
        return { success, blocked, noop, expected };
    });
    assert.equal(outcomes.success.status, "verified");
    assert.equal(outcomes.blocked.status, "mismatch");
    assert.equal(outcomes.noop.status, "unconfirmed");
    assert.equal(outcomes.expected.status, "verified");
    assert.ok(!JSON.stringify(outcomes).includes("private"), "Verification must not expose field values");
    await page.evaluate(() => {
        const host = document.createElement("section");
        host.attachShadow({ mode: "open" }).innerHTML =
            '<style>.secret-css {color:red}</style><p>Shadow content</p><section data-browser-control-private><p id="private-label">hidden-secret</p></section><button aria-labelledby="private-label">Public</button>';
        document.body.append(host);
    });
    const privacy = await page.evaluate(() => window.action("snapshot", {}));
    assert.match(privacy.text, /Shadow content/);
    assert.doesNotMatch(JSON.stringify(privacy), /secret-css|hidden-secret/);
    await assert.rejects(
        page.evaluate(() => window.action("click", { selector: "#target", documentId: "old-document" })),
        /Document changed/,
    );
    await page.emulateMedia({ reducedMotion: "no-preference" });
    const replaced = await page.evaluate(async () => {
        const button = document.querySelector("#target");
        window.accidentalClicks = 0;
        button.addEventListener("click", () => window.accidentalClicks++);
        const attempt = window.action("click", { selector: "#target" }).catch((error) => error.message);
        setTimeout(() => button.replaceWith(button.cloneNode(true)), 100);
        return { error: await attempt, clicks: window.accidentalClicks };
    });
    assert.match(replaced.error, /Target changed/);
    assert.equal(replaced.clicks, 0);
    await page.evaluate(() => {
        const list = document.createElement("ul");
        list.id = "virtual-list";
        list.style.cssText = "overflow:auto;height:60px;width:200px;margin:0;padding:0";
        for (let index = 0; index < 12; index++) {
            const item = document.createElement("li");
            item.style.height = "20px";
            item.textContent = `Row ${index}`;
            list.append(item);
        }
        document.body.prepend(list);
        list.scrollIntoView();
    });
    const collection = await page.evaluate(() => window.action("collect", { selector: "#virtual-list", maxSteps: 10 }));
    assert.ok(collection.observedCount > 3);
    assert.equal(collection.items.length, new Set(collection.items.map((item) => item.text)).size);
    assert.equal(collection.complete, false);
});
