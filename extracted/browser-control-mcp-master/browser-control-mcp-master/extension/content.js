/* global chrome */
(() => {
    if (globalThis.__localBrowserControl) {
        return;
    }
    const api = globalThis.browser ?? chrome;
    // Unlike randomUUID(), getRandomValues() also works on plain HTTP router/intranet pages.
    const documentId = Array.from(crypto.getRandomValues(new Uint32Array(2)), (value) =>
        value.toString(16).padStart(8, "0"),
    ).join("");
    const refs = new Map();
    const ids = new WeakMap();
    let revision = 0;
    const mutations = new MutationObserver((records) => {
        if (
            records.some(
                (record) =>
                    !record.target.closest?.("#local-browser-control-cursor,style[data-browser-control-scrollbars]") &&
                    !(
                        record.type === "childList" &&
                        [...record.addedNodes, ...record.removedNodes].every(
                            (node) =>
                                node.id === "local-browser-control-cursor" ||
                                node.matches?.("style[data-browser-control-scrollbars]"),
                        )
                    ),
            )
        )
            revision++;
    });
    mutations.observe(document, { childList: true, subtree: true, attributes: true, characterData: true });
    let sequence = 0;
    const interactive = "a[href],button,input,textarea,select,[role],[contenteditable='true'],[tabindex]";
    let cursor;
    let cursorHost;
    let cursorShadow;
    let zoomFactor = 1;
    function setZoom(value) {
        if (Number.isFinite(value) && value > 0) zoomFactor = value;
        cursorHost?.style.setProperty("--cursor-scale", String(1 / zoomFactor));
    }
    let userInteracted = false;
    let aborted = false;
    function checkCancelled() {
        if (userInteracted || aborted)
            throw new Error(
                "Action cancelled because you interacted with or paused the page. Earlier effects may already have happened.",
            );
    }
    const movementMs = 350;
    function hideCursor() {
        if (cursor) cursor.style.visibility = "hidden";
        cursorShadow?.querySelectorAll(".pulse").forEach((pulse) => pulse.remove());
    }
    for (const event of ["pointermove", "pointerdown", "wheel", "keydown", "touchstart", "input"]) {
        window.addEventListener(
            event,
            (event) => {
                if (!event.isTrusted) return;
                // Browsers can emit stationary pointer moves after layout/top-layer changes.
                if (event.type === "pointermove" && event.movementX === 0 && event.movementY === 0) return;
                userInteracted = true;
                hideCursor();
                // Native editing can produce trusted input events; physical pointer/key
                // events are the takeover signal, not the resulting input event.
                if (event.type !== "input" && !aborted) {
                    aborted = true;
                    void api.runtime.sendMessage?.({ type: "browser-control-takeover" })?.catch(() => {});
                }
            },
            { capture: true, passive: true },
        );
    }
    async function settleCursor() {
        await new Promise((resolve) =>
            setTimeout(resolve, matchMedia("(prefers-reduced-motion:reduce)").matches ? 0 : movementMs + 80),
        );
        checkCancelled();
    }

    function showCursor(x, y, label, clicked = false) {
        if (userInteracted) return;
        if (!cursor?.isConnected) {
            const host = document.createElement("div");
            cursorHost = host;
            host.id = "local-browser-control-cursor";
            host.setAttribute("aria-hidden", "true");
            host.setAttribute("popover", "manual");
            host.style.cssText =
                "all:initial!important;display:block!important;position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;margin:0!important;padding:0!important;border:0!important;overflow:visible!important;background:transparent!important;pointer-events:none!important;z-index:2147483647!important;";
            const shadow = host.attachShadow({ mode: "closed" });
            cursorShadow = shadow;
            const style = document.createElement("style");
            style.textContent = `
                :host::backdrop { background:transparent!important;pointer-events:none!important; }
                .cursor { position:absolute;left:0;top:0;pointer-events:none;transition:transform ${movementMs}ms cubic-bezier(.4,0,.2,1);will-change:transform; }
                .arrow { display:block;width:calc(18.75px * var(--cursor-scale));height:calc(24px * var(--cursor-scale));filter:drop-shadow(0 1px 2px #0008); }
                .pulse { position:absolute;width:calc(44px * var(--cursor-scale));height:calc(44px * var(--cursor-scale));margin:calc(-25px * var(--cursor-scale)) 0 0 calc(-25px * var(--cursor-scale));border:calc(3px * var(--cursor-scale)) solid #2563eb;border-radius:50%;background:#60a5fa77;box-shadow:0 0 0 calc(2px * var(--cursor-scale)) white;pointer-events:none;animation:click-pulse 950ms ease-out forwards; }
                @keyframes click-pulse { 0% { transform:scale(.35);opacity:1; } 30% { opacity:1; } 100% { transform:scale(1.8);opacity:0; } }
                @media (prefers-reduced-motion:reduce) { .cursor { transition:none; } }
                @media (prefers-reduced-motion:reduce) { .pulse { animation:click-still 950ms linear forwards; } }
                @keyframes click-still { from { opacity:1; } to { opacity:0; } }
            `;
            cursor = document.createElement("div");
            cursor.className = "cursor";
            const arrow = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            arrow.setAttribute("class", "arrow");
            arrow.setAttribute("viewBox", "0 0 25 32");
            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", "M2 2 L22 18 L13 19 L18 29 L13 31 L8 21 L2 27 Z");
            path.setAttribute("fill", "#2563eb");
            path.setAttribute("stroke", "white");
            path.setAttribute("stroke-width", "2");
            path.setAttribute("stroke-linejoin", "round");
            arrow.append(path);
            cursor.append(arrow);
            shadow.append(style, cursor);
            document.documentElement.append(host);
            setZoom(zoomFactor);
        }
        // Re-enter the top layer so newly opened modal dialogs cannot cover the cursor.
        if (cursorHost.showPopover) {
            if (cursorHost.matches(":popover-open")) cursorHost.hidePopover();
            cursorHost.showPopover();
        }
        x = Math.max(0, Math.min(innerWidth - 1, x));
        y = Math.max(0, Math.min(innerHeight - 1, y));
        cursor.style.transform = `translate(${x}px,${y}px)`;
        cursor.style.opacity = "1";
        cursor.style.visibility = "visible";
        if (clicked) {
            const pulse = document.createElement("div");
            pulse.className = "pulse";
            pulse.style.left = `${x}px`;
            pulse.style.top = `${y}px`;
            cursorShadow.prepend(pulse);
            setTimeout(() => pulse.remove(), 1000);
        }
    }

    function all(selector, root = document) {
        const matches = [...root.querySelectorAll(selector)];
        for (const element of root.querySelectorAll("*")) {
            if (element.shadowRoot) {
                matches.push(...all(selector, element.shadowRoot));
            }
        }
        return matches;
    }
    function visible(element) {
        const style = getComputedStyle(element);
        return element.getClientRects().length > 0 && style.visibility !== "hidden" && style.display !== "none";
    }
    function ref(element) {
        if (!ids.has(element)) {
            ids.set(element, `${documentId}-${++sequence}`);
        }
        const id = ids.get(element);
        refs.set(id, element);
        return id;
    }
    function target(args, optional = false) {
        let element;
        if (args.ref) {
            element = refs.get(args.ref);
        } else if (args.selector) {
            const matches = all(args.selector);
            if (matches.length !== 1) {
                throw new Error(`Selector matched ${matches.length} elements; expected one.`);
            }
            [element] = matches;
        } else if (Number.isFinite(args.x) && Number.isFinite(args.y)) {
            if (args.x < 0 || args.y < 0 || args.x >= innerWidth || args.y >= innerHeight) {
                throw new Error("Coordinates are outside this frame viewport.");
            }
            element = document.elementFromPoint(args.x, args.y);
            while (element?.shadowRoot) {
                const child = element.shadowRoot.elementFromPoint(args.x, args.y);
                if (!child || child === element) {
                    break;
                }
                element = child;
            }
        } else if (optional) {
            return null;
        }
        if (!element?.isConnected) {
            throw new Error("Element not found or ref is stale. Read a new snapshot.");
        }
        return element;
    }
    function prepare(element, label = "Working", focus = true) {
        if (
            !visible(element) ||
            element.disabled ||
            element.getAttribute("aria-disabled") === "true" ||
            element.closest("[inert]")
        ) {
            throw new Error("Element is hidden or disabled.");
        }
        element.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
        if (focus) {
            element.focus();
        }
        const rect = element.getBoundingClientRect();
        showCursor(rect.x + rect.width / 2, rect.y + rect.height / 2, label);
    }
    function point(args, label = "Move") {
        if (Number.isFinite(args.x) && Number.isFinite(args.y)) {
            const element = target({ x: args.x, y: args.y });
            if (element.disabled) {
                throw new Error("Element is disabled.");
            }
            showCursor(args.x, args.y, label);
            return { element, x: args.x, y: args.y };
        }
        const element = target(args);
        prepare(element, label, false);
        const rect = element.getBoundingClientRect();
        const x = Math.max(0, rect.left) + (Math.min(innerWidth, rect.right) - Math.max(0, rect.left)) / 2;
        const y = Math.max(0, rect.top) + (Math.min(innerHeight, rect.bottom) - Math.max(0, rect.top)) / 2;
        const hit = target({ x, y });
        if (hit !== element && !element.contains(hit) && hit.getRootNode().host !== element) {
            throw new Error("Another element covers the target. Read a new snapshot.");
        }
        return { element, x, y };
    }
    const input = globalThis.browserControlInput({
        all,
        target,
        prepare,
        showCursor,
        settleCursor,
        visible,
        point,
        checkCancelled,
    });
    const state = globalThis.browserControlState({ visible, ref });
    const verification = globalThis.browserControlVerification({
        target,
        state,
        visible,
        checkCancelled: () => {
            if (aborted)
                throw new Error("Verification cancelled by human takeover. Earlier effects may already have happened.");
        },
    });
    function showScrollbars(root = document) {
        if (!root.querySelector("style[data-browser-control-scrollbars]")) {
            const style = document.createElement("style");
            style.dataset.browserControlScrollbars = "";
            style.textContent = `
                * { scrollbar-width:auto!important;scrollbar-color:#64748b #e2e8f0!important; }
                *::-webkit-scrollbar { display:block!important;width:12px!important;height:12px!important; }
                *::-webkit-scrollbar-thumb { background:#64748b!important;border-radius:6px!important; }
                *::-webkit-scrollbar-track { background:#e2e8f0!important; }
            `;
            (root === document ? (document.head ?? document.documentElement) : root).append(style);
        }
        for (const element of root.querySelectorAll("*")) if (element.shadowRoot) showScrollbars(element.shadowRoot);
    }
    async function execute(action, args) {
        if (action === "verification_begin") return verification.begin(args);
        if (action === "verification_end") return verification.end(args.id);
        if (args.documentId !== undefined && args.documentId !== documentId)
            throw new Error("Document changed. Read a fresh snapshot before acting.");
        if (args.revision !== undefined && args.revision !== revision)
            throw new Error("Page revision changed. Read a fresh snapshot before acting.");
        setZoom(args.zoomFactor);
        if (action === "privacy_regions") {
            return {
                documentId,
                revision,
                width: innerWidth,
                height: innerHeight,
                x: scrollX,
                y: scrollY,
                rectangles: all("*")
                    .filter(
                        (element) => visible(element) && (state.sensitive(element) || element.matches("iframe,frame")),
                    )
                    .map((element) => {
                        const rect = element.getBoundingClientRect();
                        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
                    }),
            };
        }
        if (action === "collect") {
            const container = args.ref || args.selector ? target(args) : document.scrollingElement;
            const items = new Map();
            const maxSteps = Math.min(40, Math.max(1, args.maxSteps ?? 10));
            const maxItems = Math.min(1000, Math.max(1, args.maxItems ?? 200));
            let steps = 0;
            let reachedEnd = false;
            userInteracted = false;
            aborted = false;
            for (; steps < maxSteps; steps++) {
                checkCancelled();
                const snapshot = state.snapshot(10000);
                for (const node of snapshot.nodes) {
                    if (
                        !node.inViewport ||
                        !["row", "listitem"].includes(node.role) ||
                        !container.contains(refs.get(node.ref))
                    )
                        continue;
                    const key = `${node.role}:${node.name}`;
                    if (!items.has(key) && items.size < maxItems) items.set(key, { role: node.role, text: node.name });
                }
                if (items.size >= maxItems) break;
                const before = container.scrollTop;
                container.scrollBy({ top: Math.max(1, container.clientHeight * 0.8), behavior: "instant" });
                await new Promise((resolve) => setTimeout(resolve, 150));
                checkCancelled();
                if (container.scrollTop === before) {
                    reachedEnd = true;
                    break;
                }
            }
            return {
                items: [...items.values()],
                observedCount: items.size,
                steps: steps + 1,
                reachedEnd,
                complete: false,
                limitation:
                    "Deduplicated by role and rendered text: identical rows can collapse. Reaching the current scroll boundary does not prove all server or virtualized rows were loaded. Leaves the container at the last observed position.",
            };
        }
        if (!["snapshot", "wait"].includes(action)) {
            userInteracted = false;
            // Background control owns permission across commands. This flag cancels
            // an in-flight content action; each admitted command starts a new one.
            aborted = false;
        }
        if (action === "snapshot") {
            aborted = false;
            userInteracted = false;
            if (args.showScrollbars === true) showScrollbars();
            for (const [id, element] of refs) {
                if (!element.isConnected) {
                    refs.delete(id);
                }
            }
            return { ...state.snapshot(args.maxChars), documentId, revision, observedAt: Date.now() };
        }
        if (action === "cursor") {
            showCursor(args.x, args.y, args.label ?? "Working");
            return { ok: true };
        }
        if (action === "wait") {
            if (!args.ref && !args.selector && !args.text) {
                throw new Error("Supply a ref, selector or text to wait for.");
            }
            const deadline = Date.now() + args.timeoutMs;
            do {
                checkCancelled();
                let element = null;
                try {
                    element = target(args, true);
                } catch {
                    /* Element may not exist yet. */
                }
                const found = (!args.ref && !args.selector) || (element && visible(element));
                if (found && (!args.text || document.body?.innerText.includes(args.text))) {
                    return { found: true };
                }
                await new Promise((resolve) => setTimeout(resolve, 100));
            } while (Date.now() < deadline);
            throw new Error("Wait timed out.");
        }
        if (action === "scroll") {
            let element = args.ref || args.selector ? target(args) : null;
            const horizontal = args.direction === "left" || args.direction === "right" || (args.x && !args.y);
            if (args.origin) {
                element = target({ x: args.origin[0], y: args.origin[1] });
            }
            if (element) {
                while (
                    element &&
                    element !== document.documentElement &&
                    !(
                        (horizontal
                            ? element.scrollWidth > element.clientWidth
                            : element.scrollHeight > element.clientHeight) &&
                        /(auto|scroll)/.test(
                            horizontal ? getComputedStyle(element).overflowX : getComputedStyle(element).overflowY,
                        )
                    )
                ) {
                    element = element.parentElement ?? element.getRootNode().host;
                }
                if (element === document.documentElement) {
                    element = null;
                }
            }
            const distance =
                args.pages === undefined
                    ? null
                    : args.pages *
                      (horizontal ? (element?.clientWidth ?? innerWidth) : (element?.clientHeight ?? innerHeight));
            const sign = args.direction === "left" || args.direction === "up" ? -1 : 1;
            (element ?? window).scrollBy({
                left: distance === null ? (args.x ?? 0) : horizontal ? distance * sign : 0,
                top: distance === null ? (args.y ?? 600) : horizontal ? 0 : distance * sign,
                behavior: "instant",
            });
            showCursor(innerWidth / 2, innerHeight / 2, "Scroll");
            return { scrolled: true };
        }
        if (action === "select") {
            const element = target(args);
            prepare(element, "Select");
            if (!(element instanceof HTMLSelectElement)) {
                throw new Error("Element is not a select control.");
            }
            if (!element.multiple && args.values.length > 1) {
                throw new Error("Select allows one value only.");
            }
            for (const value of args.values) {
                if (![...element.options].some((option) => option.value === value && !option.disabled)) {
                    throw new Error("Option is absent or disabled: " + value);
                }
            }
            for (const option of element.options) {
                option.selected = args.values.includes(option.value);
            }
            element.dispatchEvent(new Event("input", { bubbles: true }));
            element.dispatchEvent(new Event("change", { bubbles: true }));
            return { ok: true };
        }
        if (action === "secondary") {
            const element = target(args);
            prepare(element, args.action);
            const details = element.matches("details")
                ? element
                : element.matches("summary")
                  ? element.parentElement
                  : null;
            if (["Expand", "Collapse"].includes(args.action)) {
                const expanded = args.action === "Expand";
                if (details?.matches("details")) {
                    details.open = expanded;
                    return { ok: true };
                }
                if (!element.hasAttribute("aria-expanded")) {
                    throw new Error("Element does not expose an expand/collapse action.");
                }
                if ((element.getAttribute("aria-expanded") === "true") !== expanded) {
                    return input("click", args);
                }
                return { ok: true };
            }
            if (
                ["Increment", "Decrement"].includes(args.action) &&
                element.matches("input[type=number],input[type=range]")
            ) {
                element[args.action === "Increment" ? "stepUp" : "stepDown"]();
                element.dispatchEvent(new Event("input", { bubbles: true }));
                element.dispatchEvent(new Event("change", { bubbles: true }));
                return { ok: true };
            }
            throw new Error("Action is not exposed by this element.");
        }
        const result = await input(action, args);
        if (result === null) {
            throw new Error("Unknown page action: " + action);
        }
        return result;
    }
    api.runtime.onMessage.addListener((message, sender, respond) => {
        if (
            sender.id === api.runtime.id &&
            ["browser-control-abort", "browser-control-resume"].includes(message.type)
        ) {
            aborted = message.type === "browser-control-abort";
            userInteracted = aborted;
            hideCursor();
            respond({ ok: true });
            return false;
        }
        if (sender.id === api.runtime.id && message.type === "browser-control-zoom") {
            setZoom(message.zoomFactor);
            respond({ ok: true });
            return false;
        }
        if (sender.id === api.runtime.id && message.type === "browser-control-hide-cursor") {
            if (cursor) {
                cursor.style.opacity = "0";
                cursor.style.visibility = "hidden";
            }
            respond({ ok: true });
            return false;
        }
        if (sender.id !== api.runtime.id || message.type !== "browser-control") {
            return false;
        }
        execute(message.action, message.args).then(
            (result) => respond({ result }),
            (error) => respond({ error: error.message }),
        );
        return true;
    });
    globalThis.__localBrowserControl = true;
})();
