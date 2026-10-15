/* global chrome, browser */
if (typeof importScripts === "function") {
    importScripts("keys.js", "trusted.js", "sessions.js", "control.js", "transport.js", "capture.js");
}
const api = globalThis.browser ?? chrome;
const sessions = globalThis.browserControlSessions(api);
const control = globalThis.browserControlControl(api);
const toolbar = api.action ?? api.browserAction;
let socket;
let connecting = false;
let heartbeat;
let retry;
let lastMessage = 0;
let state = "Disconnected";
let queue = Promise.resolve();
let lastCapture = 0;

async function connect() {
    if (connecting || (socket && socket.readyState <= WebSocket.OPEN)) {
        return;
    }
    connecting = true;
    try {
        const settings = await api.storage.local.get(["enabled", "id", "transport"]);
        if (settings.enabled === false) {
            state = "Disabled";
            return;
        }
        const config = await (await fetch(api.runtime.getURL("connection.json"))).json();
        if (!/^[a-f0-9]{64}$/.test(config.token ?? "")) {
            state = "Not paired. Run browser-control-mcp --pair-extension on this extension folder.";
            return;
        }
        const id = settings.id ?? crypto.randomUUID();
        await api.storage.local.set({ id });
        state = "Connecting";
        const current = globalThis.browserControlTransport(
            api,
            `ws://127.0.0.1:${config.port}/extension`,
            settings.transport ?? "auto",
        );
        socket = current;
        current.onopen = () => {
            lastMessage = Date.now();
            current.send(
                JSON.stringify({
                    type: "hello",
                    token: config.token,
                    browser: config.browser,
                    id,
                    name: `${config.browser} profile ${id.slice(0, 8)}`,
                }),
            );
            clearInterval(heartbeat);
            heartbeat = setInterval(() => {
                if (Date.now() - lastMessage > 40000) {
                    current.close();
                    return;
                }
                if (current.readyState === WebSocket.OPEN) {
                    current.send(JSON.stringify({ type: "ping" }));
                }
            }, 15000);
        };
        current.onmessage = (event) => {
            lastMessage = Date.now();
            const message = JSON.parse(event.data);
            if (message.type === "ready") {
                state = `Connected (${current.kind})`;
                void toolbar.setBadgeText({ text: "ON" });
                return;
            }
            if (!message.id) {
                return;
            }
            // Serialise browser actions so screenshots and navigation cannot race each other.
            const ticket = control.ticket(message.args?.tabId);
            queue = queue
                .then(async () => {
                    if (current !== socket || current.readyState !== WebSocket.OPEN) {
                        return;
                    }
                    let response;
                    let started = false;
                    try {
                        if (Date.now() >= message.expiresAt) {
                            throw new Error("Request expired before execution.");
                        }
                        const admitted = await ticket;
                        const guard = () => control.check(admitted, message.action);
                        guard();
                        started = true;
                        const result = await execute(message.action, message.args, guard);
                        if (message.action !== "close") guard();
                        if (message.action === "snapshot") await control.observed(admitted);
                        response = { id: message.id, result };
                    } catch (error) {
                        response = { id: message.id, error: error.message, phase: started ? "unknown" : "rejected" };
                    }
                    if (current.readyState === WebSocket.OPEN) {
                        current.send(JSON.stringify(response));
                    }
                })
                .catch((error) => {
                    console.error("[browser-control]", error);
                });
        };
        current.onerror = () => current.close();
        current.onclose = () => {
            if (current !== socket) {
                return;
            }
            clearInterval(heartbeat);
            void globalThis.browserControlTrusted.detachAll();
            state = "Disconnected";
            void toolbar.setBadgeText({ text: "" });
            clearTimeout(retry);
            retry = setTimeout(connect, 1500);
        };
    } catch (error) {
        state = error.message;
        clearTimeout(retry);
        retry = setTimeout(connect, 1500);
    } finally {
        connecting = false;
    }
}

async function waitLoaded(tabId) {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
        const tab = await api.tabs.get(tabId);
        if (tab.status === "complete") {
            return tab;
        }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Page load timed out. Navigation may still be in progress.");
}

async function focus(tabId) {
    const tab = await api.tabs.update(tabId, { active: true });
    await api.windows.update(tab.windowId, { focused: true });
    return tab;
}

async function openAutomationTab(args) {
    const tab = await sessions.open({ ...args, url: safeUrl(args.url) });
    return waitLoaded(tab.id);
}

async function navigate(tabId, operation, guard = () => {}) {
    await globalThis.browserControlTrusted.detach(tabId);
    guard();
    let finish;
    let fail;
    const completion = new Promise((resolve, reject) => {
        finish = resolve;
        fail = reject;
    });
    // Attach before navigation. tabs.get can still report the previous document as complete.
    const events = [
        api.webNavigation.onCompleted,
        api.webNavigation.onHistoryStateUpdated,
        api.webNavigation.onReferenceFragmentUpdated,
    ];
    const listener = (details) => {
        if (details.tabId === tabId && details.frameId === 0) {
            finish();
        }
    };
    const error = (details) => {
        if (
            details.tabId === tabId &&
            details.frameId === 0 &&
            !/ERR_ABORTED|NS_BINDING_ABORTED|2152398850/.test(details.error)
        ) {
            fail(new Error(details.error));
        }
    };
    for (const event of events) {
        event.addListener(listener);
    }
    api.webNavigation.onErrorOccurred.addListener(error);
    const timer = setTimeout(() => fail(new Error("Navigation timed out. The page may still be loading.")), 20000);
    try {
        await Promise.all([completion, operation()]);
        return api.tabs.get(tabId);
    } finally {
        clearTimeout(timer);
        for (const event of events) {
            event.removeListener(listener);
        }
        api.webNavigation.onErrorOccurred.removeListener(error);
    }
}

function safeUrl(value) {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) {
        throw new Error("Only HTTP and HTTPS navigation is supported.");
    }
    return url.href;
}

async function execute(action, args, guard = () => {}) {
    const { tabId } = args;
    if (tabId !== undefined) await sessions.touch(tabId);
    guard();
    if (action === "capabilities") {
        return {
            trustedInput: globalThis.browserControlTrusted.available,
            trustedKeyboard: false,
            trustedPointer: false,
            trustedInputRequiresFocus: true,
            nativeAccessibility: globalThis.browserControlTrusted.available,
            domInput: true,
            textSelection: true,
            htmlPaste: true,
            taskSessions: true,
            trustedFrames: "top-frame-only",
            browserChromeKeys: false,
        };
    }
    if (action === "accessibility") {
        return globalThis.browserControlTrusted.accessibility(tabId);
    }
    if (action === "mark") {
        await api.tabs.get(tabId);
        const { tabMarks = {} } = await api.storage.session.get("tabMarks");
        tabMarks[tabId] = args.mark;
        await api.storage.session.set({ tabMarks });
        return { tabId, mark: args.mark };
    }
    if (action === "windows") {
        const { automationSessions = [] } = await api.storage.session.get("automationSessions");
        return (await api.windows.getAll()).map(({ id, focused, state, type }) => {
            const names = automationSessions.filter((item) => item.windowId === id).map((item) => item.name);
            return { id, focused, state, type, automation: false, sessionNames: names };
        });
    }
    if (action === "tabs") {
        const { automationSessions = [], tabMarks = {} } = await api.storage.session.get([
            "automationSessions",
            "tabMarks",
        ]);
        const tabs = await api.tabs.query({});
        return tabs.map(({ id, windowId, groupId, url, title, active, status }) => {
            const session = automationSessions.find((item) => sessions.belongs(item, { id, groupId }));
            return {
                id,
                windowId,
                groupId,
                url,
                title,
                active,
                status,
                automation: !!session,
                sessionName: session?.name,
                mark: tabMarks[id],
            };
        });
    }
    if (action === "open") {
        return openAutomationTab(args);
    }
    if (action === "navigate") {
        return navigate(tabId, () => api.tabs.update(tabId, { url: safeUrl(args.url) }), guard);
    }
    if (action === "close") {
        guard();
        await api.tabs.remove(tabId);
        return { closed: tabId };
    }
    if (action === "focus") {
        guard();
        await focus(tabId);
        return { id: tabId, active: true };
    }
    if (["back", "forward", "reload"].includes(action)) {
        if (action === "reload") {
            return navigate(tabId, () => api.tabs.reload(tabId), guard);
        }
        // Native Back can skip entries without physical user activation. History traversal must not skip them.
        return navigate(
            tabId,
            () =>
                api.scripting.executeScript({
                    target: { tabId },
                    func: (delta) => {
                        history.go(delta);
                    },
                    args: [action === "back" ? -1 : 1],
                }),
            guard,
        );
    }
    if (action === "frames") {
        return api.webNavigation.getAllFrames({ tabId });
    }
    if (action === "observe") {
        const before = await execute("snapshot", args, guard);
        const frames = await execute("frames", args, guard);
        const screenshot = await execute("screenshot", args, guard);
        const after = await execute("snapshot", args, guard);
        const consistent =
            before.documentId === after.documentId &&
            before.revision === after.revision &&
            JSON.stringify(before.scrollRegions) === JSON.stringify(after.scrollRegions) &&
            JSON.stringify(before.viewport) === JSON.stringify(after.viewport);
        return {
            snapshot: after,
            screenshot,
            frames,
            consistent,
            consistencyScope:
                "DOM revision, viewport and scroll positions across capture; not an atomic render or animation guarantee.",
            startedAt: before.observedAt,
            endedAt: after.observedAt,
        };
    }
    if (action === "screenshot") {
        const target = await api.tabs.get(tabId);
        const [previous] = await api.tabs.query({ windowId: target.windowId, active: true });
        guard();
        await api.tabs.update(tabId, { active: true });
        try {
            await waitLoaded(tabId);
            guard();
            // Chrome permits two captures per second per extension. The shared
            // command queue plus spacing also covers combined observations.
            const pause = Math.max(0, 600 - (Date.now() - lastCapture));
            if (pause) await new Promise((resolve) => setTimeout(resolve, pause));
            guard();
            const before = await execute("privacy_regions", { tabId }, guard);
            lastCapture = Date.now();
            const capture = await api.tabs.captureVisibleTab(target.windowId, { format: "png" });
            guard();
            const after = await execute("privacy_regions", { tabId }, guard);
            guard();
            if (JSON.stringify(before) !== JSON.stringify(after))
                throw new Error(
                    "Page changed during screenshot privacy checks; capture withheld. Read fresh state and try again.",
                );
            const masked = await globalThis.browserControlMaskCapture(capture, after);
            guard();
            return masked;
        } finally {
            const current = await api.tabs.get(tabId).catch(() => null);
            let mayRestore = true;
            try {
                guard();
            } catch {
                mayRestore = false;
            }
            if (mayRestore && previous && previous.id !== tabId && current?.active) {
                await api.tabs.update(previous.id, { active: true }).catch(() => {});
            }
        }
    }
    const frameId = args.frameId ?? 0;
    try {
        await api.scripting.executeScript({
            target: { tabId, frameIds: [frameId] },
            files: ["keys.js", "input.js", "state.js", "verification.js", "content.js"],
        });
        if (!["snapshot", "wait"].includes(action)) {
            await api.tabs.sendMessage(tabId, { type: "browser-control-hide-cursor" }).catch(() => {});
        }
        const page = async (pageAction, pageArgs) => {
            const zoomFactor = await api.tabs.getZoom(tabId);
            guard();
            const response = await api.tabs.sendMessage(
                tabId,
                { type: "browser-control", action: pageAction, args: { ...pageArgs, zoomFactor } },
                { frameId },
            );
            if (response.error) {
                throw new Error(response.error);
            }
            return response.result;
        };
        const verificationId = await page("verification_begin", { ...args, operation: action });
        const result =
            (await globalThis.browserControlTrusted.mode(action, args)) === "trusted"
                ? await globalThis.browserControlTrusted.execute(action, args, page, guard)
                : await page(action, args);
        if (verificationId !== null) {
            let verification;
            try {
                verification = await page("verification_end", { id: verificationId });
            } catch {
                verification = {
                    status: "unconfirmed",
                    reason: "Page changed or verification became unavailable. Inspect current state before retrying.",
                };
            }
            return { ...result, ok: result.ok !== false && verification.status !== "mismatch", verification };
        }
        return result;
    } catch (error) {
        throw new Error(
            `Page action failed: ${error.message}. Browser settings pages, extension stores and some built-in viewers block extensions.`,
        );
    }
}

api.runtime.onMessage.addListener((message, sender, respond) => {
    if (sender.id === api.runtime.id && sender.tab && message.type === "browser-control-takeover") {
        void sessions.touch(sender.tab.id).catch(() => {});
        void control
            .change(sender.tab.id, "human")
            .then(() => {
                void api.tabs.sendMessage(sender.tab.id, { type: "browser-control-abort" }).catch(() => {});
                if (socket?.readyState === WebSocket.OPEN)
                    socket.send(JSON.stringify({ type: "takeover", tabId: sender.tab.id }));
            })
            .catch(() => {});
        return false;
    }
    if (sender.id !== api.runtime.id || sender.tab) {
        return false;
    }
    if (message.type === "status") {
        api.storage.local
            .get(["enabled", "idleHours"])
            .then(({ enabled, idleHours = 4 }) => respond({ state, enabled: enabled !== false, idleHours }));
        return true;
    }
    if (message.type === "cleanup-settings") {
        const hours = message.idleHours;
        if (!Number.isFinite(hours) || hours < 0 || hours > 720) {
            respond({ error: "Use a timeout between 0 and 720 hours." });
            return false;
        }
        api.storage.local.set({ idleHours: hours }).then(() => respond({ ok: true }));
        return true;
    }
    if (message.type === "toggle") {
        api.storage.local.set({ enabled: message.enabled }).then(() => {
            if (!message.enabled) {
                socket?.close();
                state = "Disabled";
            } else {
                void connect();
            }
            respond({ ok: true });
        });
        return true;
    }
    return false;
});
api.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "cleanup") {
        queue = queue
            .then(() => sessions.cleanup())
            .catch((error) => console.error("[browser-control] Cleanup failed", error));
    } else {
        void connect();
    }
});
api.runtime.onStartup.addListener(() => {
    void connect();
});
api.runtime.onInstalled.addListener(() => {
    void connect();
});
api.tabs.onCreated.addListener((tab) => {
    void sessions.child(tab).catch(console.error);
});
api.tabs.onRemoved.addListener((tabId) => {
    void control.change(tabId, "finished").catch(() => {});
    void sessions.removed(tabId).catch(() => {});
});
api.tabs.onActivated.addListener(({ tabId }) => {
    void sessions.touch(tabId).catch(console.error);
});
api.tabs.onZoomChange.addListener(({ tabId, newZoomFactor }) => {
    void api.tabs.sendMessage(tabId, { type: "browser-control-zoom", zoomFactor: newZoomFactor }).catch(() => {});
});
api.tabs.onUpdated.addListener((tabId, change) => {
    if (change.url || change.status === "loading") void sessions.touch(tabId).catch(console.error);
});
void api.alarms.create("reconnect", { periodInMinutes: 0.5 });
void api.alarms.create("cleanup", { periodInMinutes: 5 });
void connect();
