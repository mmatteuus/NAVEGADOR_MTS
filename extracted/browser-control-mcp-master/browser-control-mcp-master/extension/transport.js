globalThis.browserControlTransport = (api, url, preference = "auto") => {
    const adapter = { readyState: 0, kind: "connecting" };
    let connection;
    let timer;
    let closed = false;
    let opened = false;
    function disconnected() {
        clearTimeout(timer);
        if (closed) return;
        closed = true;
        adapter.readyState = 3;
        adapter.onclose?.();
    }
    function websocket() {
        if (closed) return;
        adapter.kind = "local WebSocket";
        const ws = new WebSocket(url);
        connection = ws;
        ws.onopen = () => {
            adapter.readyState = 1;
            adapter.onopen?.();
        };
        ws.onmessage = (event) => adapter.onmessage?.(event);
        ws.onerror = () => ws.close();
        ws.onclose = disconnected;
    }
    adapter.send = (text) => {
        if (adapter.readyState !== 1) throw new Error("Transport disconnected");
        if (adapter.kind === "native messaging") connection.postMessage(JSON.parse(text));
        else connection.send(text);
    };
    adapter.close = () => {
        closed = true;
        clearTimeout(timer);
        adapter.readyState = 3;
        if (connection?.disconnect) connection.disconnect();
        else connection?.close();
        adapter.onclose?.();
    };
    if (preference === "websocket") queueMicrotask(websocket);
    else {
        try {
            const port = api.runtime.connectNative("dev.local_browser_control");
            connection = port;
            adapter.kind = "native messaging";
            const unavailable = () => {
                // Read lastError to prevent an unchecked runtime warning.
                void api.runtime.lastError;
                clearTimeout(timer);
                if (connection !== port || closed) return;
                if (!opened && preference === "auto") websocket();
                else disconnected();
            };
            port.onDisconnect.addListener(unavailable);
            port.onMessage.addListener((message) => {
                if (connection !== port || closed) return;
                if (message.type === "native-open") {
                    opened = true;
                    clearTimeout(timer);
                    adapter.readyState = 1;
                    adapter.onopen?.();
                } else adapter.onmessage?.({ data: JSON.stringify(message) });
            });
            timer = setTimeout(() => {
                unavailable();
                port.disconnect();
            }, 5000);
        } catch {
            if (preference === "auto") queueMicrotask(websocket);
            else queueMicrotask(disconnected);
        }
    }
    return adapter;
};
