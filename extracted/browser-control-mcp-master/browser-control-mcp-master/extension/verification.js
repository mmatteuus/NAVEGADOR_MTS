globalThis.browserControlVerification = ({ target, state, visible, checkCancelled = () => {} }) => {
    const pending = new Map();
    let sequence = 0;
    const watched = new Set(["click", "fill", "type", "paste", "press", "select", "scroll", "drag", "secondary"]);
    const value = (element) => (element?.isContentEditable ? element.innerText : element?.value);
    function fingerprint() {
        const snapshot = state.snapshot(30000);
        return JSON.stringify({
            url: snapshot.url,
            text: snapshot.text,
            nodes: snapshot.nodes.map(({ ref, role, name, value, checked, expanded, selected, scroll }) => ({
                ref,
                role,
                name,
                value,
                checked,
                expanded,
                selected,
                scroll,
            })),
        });
    }
    function expected(expect) {
        if (!expect) return false;
        if (expect.urlIncludes !== undefined && !location.href.includes(expect.urlIncludes)) return false;
        if (expect.text !== undefined && !document.body.innerText.includes(expect.text)) return false;
        if (expect.selector !== undefined) {
            const element = document.querySelector(expect.selector);
            if (!element || !visible(element)) return false;
        }
        return true;
    }
    function begin(args) {
        if (!watched.has(args.operation)) return null;
        let element;
        try {
            element = target(args.ref || args.selector ? args : { ...args, ref: undefined, selector: undefined }, true);
        } catch {
            /* A coordinate action may have no editable target. */
        }
        element ??= document.activeElement;
        const beforeValue = value(element);
        let desired;
        if (args.operation === "fill") desired = args.text;
        if (
            ["type", "paste"].includes(args.operation) &&
            args.format !== "html" &&
            typeof beforeValue === "string" &&
            !element.isContentEditable
        ) {
            const start = element.selectionStart ?? beforeValue.length;
            const end = element.selectionEnd ?? beforeValue.length;
            desired = beforeValue.slice(0, start) + args.text + beforeValue.slice(end);
        }
        const id = ++sequence;
        const timer = setTimeout(() => pending.delete(id), 60000);
        pending.set(id, { args, element, desired, before: fingerprint(), already: expected(args.expect), timer });
        return id;
    }
    async function end(id) {
        const record = pending.get(id);
        if (!record)
            return {
                status: "unconfirmed",
                reason: "Verification context expired or unavailable. Inspect the page before retrying.",
            };
        pending.delete(id);
        clearTimeout(record.timer);
        const { args, element, desired, before, already } = record;
        let matched = false;
        let changed = false;
        const exact = desired !== undefined || args.operation === "select" || !!args.expect;
        // Page timers in background tabs may run at one-second intervals even
        // while extension timers continue. Allow page rollback handlers to run.
        const settleMs = document.hidden ? 1200 : 400;
        const timeoutMs = Math.max(200, Math.min(10000, args.expect?.timeoutMs ?? (document.hidden ? 3000 : 1200)));
        const deadline = Date.now() + timeoutMs;
        let matchedSince = null;
        let firstSample = true;
        do {
            // Sample before yielding: background tabs can throttle even a 200 ms
            // timer beyond the verification budget. Keep later settling checks.
            if (!firstSample) await new Promise((resolve) => setTimeout(resolve, 200));
            firstSample = false;
            checkCancelled();
            if (args.expect) matched = expected(args.expect);
            else if (desired !== undefined) matched = !!element?.isConnected && value(element) === desired;
            else if (args.operation === "select")
                matched =
                    !!element?.isConnected &&
                    JSON.stringify([...element.selectedOptions].map((option) => option.value).sort()) ===
                        JSON.stringify([...args.values].sort());
            changed = fingerprint() !== before;
            if (matched) matchedSince ??= Date.now();
            else matchedSince = null;
            // Require a settling interval so a framework's delayed value rollback
            // does not get reported as a successful fill on the first sample.
            if ((matched && Date.now() - matchedSince >= settleMs) || (!exact && changed)) break;
        } while (Date.now() < deadline);
        if (matched && matchedSince !== null && Date.now() - matchedSince >= settleMs)
            return {
                status: already ? "already-satisfied" : "verified",
                scope: args.expect ? "requested postcondition" : "DOM field value",
                reason: "Post-action state matches. This does not verify server-side persistence.",
            };
        if (exact)
            return {
                status: "mismatch",
                reason: `Expected post-action state was not observed within ${timeoutMs} ms. Inspect before retrying; the action may have been applied.`,
            };
        return {
            status: changed ? "observed-change" : "unconfirmed",
            reason: changed
                ? "Page state changed; intended outcome is not proven. Use expect for a specific postcondition."
                : `No observable semantic change within ${timeoutMs} ms. Do not assume success or automatically retry.`,
        };
    }
    return { begin, end };
};
