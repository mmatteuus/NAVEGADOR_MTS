/* global chrome */
globalThis.browserControlTrusted = (() => {
    const api = globalThis.browser ?? chrome;
    const attached = new Set();
    const available = !!api.debugger;
    const supported = ["fill", "type", "paste"];
    if (available) {
        api.debugger.onDetach.addListener(({ tabId }) => attached.delete(tabId));
    }
    async function send(tabId, method, params = {}, guard = () => {}) {
        if (!attached.has(tabId)) {
            try {
                await api.debugger.attach({ tabId }, "1.3");
            } catch (error) {
                throw new Error(
                    "Cannot attach trusted input. Close DevTools for this tab or explicitly use inputMode:dom. " +
                        error.message,
                );
            }
            attached.add(tabId);
        }
        guard();
        return api.debugger.sendCommand({ tabId }, method, params);
    }
    async function detachAll() {
        for (const tabId of attached) {
            await detach(tabId);
        }
        attached.clear();
    }
    async function detach(tabId) {
        if (attached.has(tabId)) {
            await api.debugger.detach({ tabId }).catch(() => {});
            attached.delete(tabId);
        }
    }
    async function mode(action, args) {
        const canUse =
            available &&
            (args.frameId ?? 0) === 0 &&
            supported.includes(action) &&
            !(action === "paste" && args.format === "html");
        if (args.inputMode === "trusted" && !canUse) {
            throw new Error(
                "Trusted input supports Chrome top-frame text insertion only. Pointer actions, keys, HTML paste and Firefox use DOM input.",
            );
        }
        if (args.inputMode === "dom" || !canUse) {
            return "dom";
        }
        const tab = await api.tabs.get(args.tabId);
        const window = await api.windows.get(tab.windowId);
        if (!tab.active || !window.focused) {
            if (args.inputMode === "trusted") {
                throw new Error(
                    "Trusted input requires the target tab in the focused window. Use DOM input for background work or explicitly focus the tab first.",
                );
            }
            return "dom";
        }
        return "trusted";
    }
    async function execute(action, args, page, guard = () => {}) {
        const { tabId } = args;
        const result = { ok: true, inputMode: "trusted", trusted: true };
        if (["fill", "type", "paste"].includes(action)) {
            await page("input_target", { ...args, operation: action });
            await send(tabId, "Input.insertText", { text: args.text }, guard);
            return result;
        }
        throw new Error("Unsupported trusted action: " + action);
    }
    async function accessibility(tabId) {
        if (!available) {
            throw new Error(
                "Native accessibility capture is available in Chrome only. Use browser_snapshot for semantic DOM state in either browser.",
            );
        }
        const { nodes } = await send(tabId, "Accessibility.getFullAXTree");
        return {
            source: "chrome-accessibility",
            nodes: nodes
                .filter((node) => !node.ignored)
                .map((node) => ({
                    nodeId: node.nodeId,
                    parentId: node.parentId,
                    childIds: node.childIds,
                    role: node.role?.value,
                    name: node.name?.value,
                    // Omit AX values because the native tree can include protected fields.
                    properties: node.properties?.filter((property) => property.name !== "value"),
                })),
        };
    }
    return { available, mode, execute, detachAll, detach, accessibility };
})();
