import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const context = vm.createContext({ console });
vm.runInContext(await readFile(new URL("../extension/sessions.js", import.meta.url), "utf8"), context);
test("closing the last owned tab ends the named task instead of recreating it", async () => {
    const f = fixture();
    const tab = await f.manager.open({ url: "https://example.test", sessionName: "Finished task" });
    await f.api.tabs.remove(tab.id);
    await f.manager.removed(tab.id);
    await assert.rejects(f.manager.open({ url: "https://example.test", sessionName: "Finished task" }), /closed/);
    assert.equal(f.groups.length, 0);
});
function fixture() {
    let time = 1000;
    let next = 10;
    const tabs = [{ id: 1, windowId: 1, groupId: -1, active: true }];
    const groups = [];
    const data = { automationSessions: [], tabMarks: {} };
    const local = { idleHours: 4 };
    const api = {
        storage: {
            session: {
                get: async () => structuredClone(data),
                set: async (value) => Object.assign(data, structuredClone(value)),
            },
            local: { get: async () => local },
        },
        windows: { getAll: async () => [{ id: 1, type: "normal", focused: true }] },
        tabs: {
            query: async () => structuredClone(tabs),
            get: async (id) => {
                const tab = tabs.find((t) => t.id === id);
                if (!tab) throw Error("absent");
                return { ...tab };
            },
            create: async (args) => {
                const tab = { ...args, id: next++, groupId: -1 };
                tabs.push(tab);
                return { ...tab };
            },
            group: async (args) => {
                let group = groups.find((g) => g.id === args.groupId);
                if (!group) {
                    group = { id: next++, windowId: args.createProperties.windowId };
                    groups.push(group);
                }
                for (const tab of tabs) if (args.tabIds.includes(tab.id)) tab.groupId = group.id;
                return group.id;
            },
            remove: async (id) => {
                tabs.splice(
                    tabs.findIndex((t) => t.id === id),
                    1,
                );
                for (let index = groups.length - 1; index >= 0; index--)
                    if (!tabs.some((t) => t.groupId === groups[index].id)) groups.splice(index, 1);
            },
        },
        tabGroups: {
            get: async (id) => {
                const group = groups.find((g) => g.id === id);
                if (!group) throw Error("absent");
                return { ...group };
            },
            update: async (id, changes) =>
                Object.assign(
                    groups.find((g) => g.id === id),
                    changes,
                ),
        },
    };
    return {
        api,
        tabs,
        groups,
        data,
        local,
        advance: (hours) => (time += hours * 3600000),
        manager: context.browserControlSessions(api, () => time),
    };
}

test("sessions reuse existing windows and close only owned idle tabs at the boundary", async () => {
    const f = fixture();
    const first = await f.manager.open({ url: "https://example.com", sessionName: "One" });
    const second = await f.manager.open({ url: "https://example.com", sessionName: "Two" });
    assert.equal(first.windowId, 1);
    assert.equal(first.active, false);
    assert.notEqual(f.tabs.find((t) => t.id === first.id).groupId, f.tabs.find((t) => t.id === second.id).groupId);
    f.advance(3.99);
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 3);
    f.advance(0.01);
    await f.manager.cleanup();
    assert.deepEqual(
        f.tabs.map((t) => t.id),
        [1],
    );
    assert.equal(f.groups.length, 0);
    assert.equal(f.data.automationSessions.length, 0);
});

test("activity extends the deadline; disabling cleanup preserves tabs", async () => {
    const f = fixture();
    const tab = await f.manager.open({ url: "https://example.com" });
    f.advance(3);
    await f.manager.touch(tab.id);
    f.advance(2);
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 2);
    f.local.idleHours = 0;
    f.advance(10);
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 2);
    f.local.idleHours = 4;
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 1);
});

test("same-name sessions reuse their group and own child tabs", async () => {
    const f = fixture();
    const first = await f.manager.open({ url: "https://example.com" });
    const second = await f.manager.open({ url: "https://example.com/second" });
    assert.equal(f.groups.length, 1);
    const child = await f.api.tabs.create({ windowId: 1, openerTabId: first.id, active: false });
    await f.manager.child(child);
    assert.equal(f.tabs.find((t) => t.id === child.id).groupId, f.groups[0].id);
    assert.deepEqual(f.data.automationSessions[0].tabIds, [first.id, second.id, child.id]);
    f.advance(4);
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 1);
});

test("browser-recorded recent access protects an inactive group", async () => {
    const f = fixture();
    const tab = await f.manager.open({ url: "https://example.com" });
    f.advance(5);
    f.tabs.find((t) => t.id === tab.id).lastAccessed = 4 * 3600000 + 1000;
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 2);
    f.advance(3);
    await f.manager.cleanup();
    assert.equal(f.tabs.length, 1);
});

test("pinned, marked, selected and audible tabs are protected", async () => {
    for (const protection of ["pinned", "marked", "active", "audible"]) {
        const f = fixture();
        const tab = await f.manager.open({ url: "https://example.com" });
        if (protection === "marked") f.data.tabMarks[tab.id] = "handoff";
        else f.tabs.find((t) => t.id === tab.id)[protection] = true;
        f.advance(5);
        await f.manager.cleanup();
        assert.equal(f.tabs.length, 2, protection);
    }
});

test("manual additions and tabs moved out of an automation group are never closed", async () => {
    const f = fixture();
    const tab = await f.manager.open({ url: "https://example.com" });
    const owned = f.tabs.find((t) => t.id === tab.id);
    f.tabs.push({ id: 99, windowId: 1, groupId: owned.groupId, active: false });
    owned.groupId = -1;
    f.advance(5);
    await f.manager.cleanup();
    assert.deepEqual(
        f.tabs.map((t) => t.id),
        [1, tab.id, 99],
    );
});

test("worker restart preserves deadlines and legacy groups are not adopted for closure", async () => {
    const f = fixture();
    await f.manager.open({ url: "https://example.com" });
    f.advance(5);
    const restarted = context.browserControlSessions(f.api, () => 5 * 3600000 + 1000);
    await restarted.cleanup();
    assert.equal(f.tabs.length, 1);
    const legacy = await f.manager.open({ url: "https://example.com" });
    delete f.data.automationSessions[0].tabIds;
    f.advance(5);
    await f.manager.cleanup();
    assert.ok(f.tabs.some((t) => t.id === legacy.id));
});
