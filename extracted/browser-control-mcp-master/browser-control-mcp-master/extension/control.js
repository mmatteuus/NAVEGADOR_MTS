globalThis.browserControlControl = (api) => {
    let tabs = {};
    let writes = Promise.resolve();
    const ready = api.storage.session.get("tabControl").then(({ tabControl = {} }) => {
        tabs = tabControl;
        // Ignore removed popup pause/permission settings on upgrade.
        for (const state of Object.values(tabs)) {
            if (state.mode !== "finished") {
                state.mode = "agent";
                state.fresh = false;
            }
        }
    });
    const save = () => {
        const snapshot = structuredClone(tabs);
        writes = writes.catch(() => {}).then(() => api.storage.session.set({ tabControl: snapshot }));
        return writes;
    };
    const get = (id) => tabs[id] ?? { mode: "agent", epoch: 0, fresh: false };
    return {
        async ticket(id) {
            await ready;
            return id === undefined ? null : { id, epoch: get(id).epoch };
        },
        async status(id) {
            await ready;
            return { ...get(id) };
        },
        async change(id, mode) {
            await ready;
            if (get(id).mode === "finished") throw new Error("Tab is closed; it cannot be resumed.");
            tabs[id] = {
                mode: mode === "finished" ? "finished" : "agent",
                epoch: get(id).epoch + 1,
                fresh: mode !== "finished",
            };
            await save();
            return { ...tabs[id] };
        },
        check(ticket, action) {
            if (!ticket) return;
            const state = get(ticket.id);
            if (ticket.epoch !== state.epoch || state.mode !== "agent") {
                throw new Error(
                    `Tab control is ${state.mode}; action cancelled. Earlier effects may already have happened. Read a fresh snapshot before continuing.`,
                );
            }
            if (state.fresh && action !== "snapshot")
                throw new Error("Interaction requires a fresh snapshot before further actions.");
        },
        async observed(ticket) {
            if (!ticket) return;
            this.check(ticket, "snapshot");
            tabs[ticket.id] = { ...get(ticket.id), fresh: false };
            await save();
        },
    };
};
