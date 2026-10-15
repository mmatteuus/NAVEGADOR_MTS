globalThis.browserControlSessions = (api, now = Date.now) => {
    let pending = Promise.resolve();
    const serial = (work) => {
        const result = pending.then(work);
        pending = result.catch(() => {});
        return result;
    };
    const read = async () => (await api.storage.session.get("automationSessions")).automationSessions ?? [];
    const save = (sessions) => api.storage.session.set({ automationSessions: sessions });
    const belongs = (session, tab) => session.tabIds?.includes(tab.id) && session.groupId === tab.groupId;
    async function touch(tabId) {
        return serial(async () => {
            const sessions = await read();
            const tab = await api.tabs.get(tabId).catch(() => null);
            const session = tab && sessions.find((item) => belongs(item, tab));
            if (session) {
                session.lastUsed = now();
                await save(sessions);
            }
        });
    }
    async function open(args) {
        return serial(async () => {
            const sessions = await read();
            const name = args.sessionName ?? "MCP Automation";
            const { finishedSessions = [] } = await api.storage.session.get("finishedSessions");
            if (finishedSessions.includes(name))
                throw new Error(
                    "This automation session was closed. Start a new task with a new sessionName; closed tasks are not recreated automatically.",
                );
            let session = sessions.find((item) => item.name === name);
            if (!session) {
                session = { name, tabIds: [] };
                sessions.push(session);
            }
            // Legacy records have no per-tab ownership. Never adopt their tabs for automatic closure.
            session.tabIds ??= [];
            const windows = (await api.windows.getAll()).filter((item) => item.type === "normal" && !item.incognito);
            let group =
                session.groupId === undefined ? null : await api.tabGroups.get(session.groupId).catch(() => null);
            let window = group && windows.find((item) => item.id === group.windowId);
            if (!window) {
                group = null;
                window = windows.find((item) => item.focused) ?? windows[0];
            }
            let tab;
            if (window) {
                tab = await api.tabs.create({ windowId: window.id, url: args.url, active: args.active ?? false });
            } else {
                const previous = (await api.windows.getAll()).find((item) => item.focused);
                window = await api.windows.create({ url: args.url, focused: false, type: "normal" });
                tab = window.tabs[0];
                if (previous && (await api.windows.get(window.id)).focused) {
                    await api.windows.update(previous.id, { focused: true }).catch(() => {});
                }
            }
            session.windowId = window.id;
            session.groupId = await api.tabs.group({
                tabIds: [tab.id],
                ...(group ? { groupId: group.id } : { createProperties: { windowId: window.id } }),
            });
            await api.tabGroups.update(session.groupId, { title: name, color: "blue", collapsed: false });
            session.tabIds.push(tab.id);
            session.lastUsed = now();
            await save(sessions);
            return tab;
        });
    }
    async function child(tab) {
        return serial(async () => {
            if (!tab.openerTabId) return;
            const sessions = await read();
            const opener = await api.tabs.get(tab.openerTabId).catch(() => null);
            const session = opener && sessions.find((item) => belongs(item, opener));
            if (!session || tab.windowId !== opener.windowId) return;
            await api.tabs.group({ tabIds: [tab.id], groupId: session.groupId });
            session.tabIds.push(tab.id);
            session.lastUsed = now();
            await save(sessions);
        });
    }
    async function cleanup() {
        return serial(async () => {
            const { idleHours = 4, enabled = true } = await api.storage.local.get(["idleHours", "enabled"]);
            if (!enabled || !Number.isFinite(idleHours) || idleHours <= 0) return;
            const sessions = await read();
            const { tabMarks = {} } = await api.storage.session.get("tabMarks");
            const tabs = await api.tabs.query({});
            const remaining = [];
            for (const session of sessions) {
                const owned = tabs.filter((tab) => belongs(session, tab));
                // Moving a tab out of its group relinquishes automation ownership.
                session.tabIds = owned.map((tab) => tab.id);
                const group = await api.tabGroups.get(session.groupId).catch(() => null);
                if (!group) continue;
                session.windowId = group.windowId;
                session.lastUsed ??= now();
                session.lastUsed = Math.max(session.lastUsed, ...owned.map((tab) => tab.lastAccessed ?? 0));
                const groupTabs = tabs.filter((tab) => tab.groupId === session.groupId);
                if (groupTabs.some((tab) => tab.active || tab.audible)) session.lastUsed = now();
                if (now() - session.lastUsed >= idleHours * 3600000) {
                    for (const tab of owned) {
                        // Recheck immediately before closure. Never close unowned, pinned, selected or marked tabs.
                        const current = await api.tabs.get(tab.id).catch(() => null);
                        if (
                            !current ||
                            !belongs(session, current) ||
                            current.active ||
                            current.audible ||
                            current.pinned ||
                            tabMarks[tab.id] ||
                            now() - (current.lastAccessed ?? 0) < idleHours * 3600000
                        )
                            continue;
                        await api.tabs.remove(tab.id);
                        session.tabIds = session.tabIds.filter((id) => id !== tab.id);
                        console.info("[browser-control] Closed idle automation tab", tab.id);
                    }
                }
                if (await api.tabGroups.get(session.groupId).catch(() => null)) remaining.push(session);
            }
            const liveIds = new Set((await api.tabs.query({})).map((tab) => String(tab.id)));
            for (const id of Object.keys(tabMarks)) if (!liveIds.has(id)) delete tabMarks[id];
            await api.storage.session.set({ automationSessions: remaining, tabMarks });
        });
    }
    async function removed(tabId) {
        return serial(async () => {
            const sessions = await read();
            const { finishedSessions = [] } = await api.storage.session.get("finishedSessions");
            for (const session of sessions) {
                if (!session.tabIds?.includes(tabId)) continue;
                session.tabIds = session.tabIds.filter((id) => id !== tabId);
                if (!session.tabIds.length && !finishedSessions.includes(session.name))
                    finishedSessions.push(session.name);
            }
            await api.storage.session.set({ automationSessions: sessions, finishedSessions });
        });
    }
    return { open, touch, child, cleanup, belongs, removed };
};
