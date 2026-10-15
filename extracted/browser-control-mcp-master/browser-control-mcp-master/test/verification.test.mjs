import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const source = await readFile(new URL("../extension/verification.js", import.meta.url), "utf8");
function fixture({ delay = 200, rollback = false, rollbackAfter = 0, hidden = false } = {}) {
    let now = 0;
    const element = { value: "Before", isConnected: true };
    const context = vm.createContext({
        Date: { now: () => now },
        setTimeout(callback, ms) {
            if (ms === 60000) return 1;
            queueMicrotask(() => {
                now += delay;
                if (rollback && now >= rollbackAfter) element.value = "Before";
                callback();
            });
            return 2;
        },
        clearTimeout() {},
        document: { activeElement: element, hidden },
    });
    vm.runInContext(source, context);
    const verification = context.browserControlVerification({
        target: () => element,
        state: { snapshot: () => ({ nodes: [], text: "", url: "https://example.test" }) },
        visible: () => true,
    });
    const id = verification.begin({ operation: "fill", text: "After" });
    element.value = "After";
    return () => verification.end(id);
}

test("field verification samples immediately before background timer delays", async () => {
    const result = await fixture({ delay: 1300 })();
    assert.equal(result.status, "verified");
});

test("field verification still rejects a delayed rollback", async () => {
    const result = await fixture({ rollback: true })();
    assert.equal(result.status, "mismatch");
});

test("hidden-page verification allows throttled page rollback timers to run", async () => {
    const result = await fixture({ rollback: true, rollbackAfter: 1000, hidden: true })();
    assert.equal(result.status, "mismatch");
});
