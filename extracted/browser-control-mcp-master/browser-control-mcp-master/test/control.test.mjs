import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
const context = vm.createContext({ structuredClone });
vm.runInContext(await readFile(new URL("../extension/control.js", import.meta.url), "utf8"), context);
test("takeover cancels queued actions; fresh state continues without manual resume", async () => {
    const data = { tabControl: { 3: { mode: "paused", epoch: 2, fresh: true } } };
    const api = {
        storage: {
            session: {
                get: async () => structuredClone(data),
                set: async (value) => Object.assign(data, structuredClone(value)),
            },
        },
    };
    const control = context.browserControlControl(api);
    control.check(await control.ticket(3), "click");
    const old = await control.ticket(1);
    const other = await control.ticket(2);
    control.check(old, "click");
    await control.change(1, "human");
    assert.throws(() => control.check(old, "click"), /cancelled/);
    control.check(other, "click");
    assert.throws(() => control.check(old, "click"), /cancelled/);
    const resumed = await control.ticket(1);
    assert.throws(() => control.check(resumed, "click"), /fresh snapshot/);
    await control.observed(resumed);
    control.check(resumed, "click");
    await control.change(1, "finished");
    const restarted = context.browserControlControl(api);
    const closed = await restarted.ticket(1);
    assert.throws(() => restarted.check(closed, "snapshot"), /finished/);
    await assert.rejects(restarted.change(1, "agent"), /closed/);
});
