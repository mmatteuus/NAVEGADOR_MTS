globalThis.browserControlState = ({ visible, ref }) => {
    const normal = (text) => (text ?? "").replace(/\s+/g, " ").trim();
    function privateElement(element) {
        for (let current = element; current; current = current.getRootNode().host) {
            if (current.closest?.("[data-browser-control-private]")) return true;
        }
        return false;
    }
    const sensitive = (element) =>
        privateElement(element) ||
        element.matches?.("input[type=password]") ||
        (element.getAttribute?.("autocomplete") ?? "")
            .split(/\s+/)
            .some((token) => token === "one-time-code" || token.startsWith("cc-"));
    // Walk rendered content rather than shadowRoot.textContent, which includes
    // extension styles/scripts. Redaction applies to ancestor names as well.
    function renderedText(element, includeHidden = false) {
        if (element.nodeType === Node.TEXT_NODE) return element.textContent ?? "";
        if (element.nodeType !== Node.ELEMENT_NODE) return "";
        if (
            element.id === "local-browser-control-cursor" ||
            element.matches("script,style,noscript,template") ||
            (!includeHidden && (element.matches("[aria-hidden=true],[inert]") || !visible(element)))
        )
            return "";
        if (sensitive(element)) return "[redacted]";
        if (element.matches("input,textarea,select")) return "";
        const children = element.matches("details:not([open])")
            ? [...element.children].filter((child) => child.localName === "summary").slice(0, 1)
            : element.localName === "slot" && element.assignedNodes().length
              ? element.assignedNodes()
              : (element.shadowRoot ?? element).childNodes;
        return [...children].map((child) => renderedText(child, includeHidden)).join(" ");
    }
    function role(element) {
        const explicit = element.getAttribute("role")?.split(/\s+/)[0];
        if (explicit) {
            return ["none", "presentation"].includes(explicit) ? null : explicit;
        }
        if (/^h[1-6]$/.test(element.localName)) {
            return "heading";
        }
        if (element.localName === "input") {
            return (
                {
                    checkbox: "checkbox",
                    radio: "radio",
                    range: "slider",
                    number: "spinbutton",
                    button: "button",
                    submit: "button",
                    reset: "button",
                    hidden: null,
                    search: "searchbox",
                }[element.type] ?? (element.type === "hidden" ? null : "textbox")
            );
        }
        if (element.localName === "select") {
            return element.multiple || element.size > 1 ? "listbox" : "combobox";
        }
        if (element.localName === "a") {
            return element.hasAttribute("href") ? "link" : null;
        }
        if (element.isContentEditable && !element.parentElement?.isContentEditable) {
            return "textbox";
        }
        return (
            {
                button: "button",
                textarea: "textbox",
                summary: "button",
                details: "group",
                main: "main",
                nav: "navigation",
                header: "banner",
                footer: "contentinfo",
                aside: "complementary",
                section: "region",
                article: "article",
                form: "form",
                ul: "list",
                ol: "list",
                li: "listitem",
                table: "table",
                tr: "row",
                th: "columnheader",
                td: "cell",
                img: "img",
                progress: "progressbar",
                dialog: "dialog",
                iframe: "iframe",
                p: "paragraph",
                output: "status",
            }[element.localName] ?? (element.tabIndex >= 0 ? "generic" : null)
        );
    }
    function name(element, seen = new Set()) {
        if (privateElement(element)) return "[redacted]";
        if (seen.has(element)) {
            return "";
        }
        seen.add(element);
        const labelledBy = element.getAttribute("aria-labelledby");
        if (labelledBy) {
            const labels = labelledBy
                .split(/\s+/)
                .map((id) => element.getRootNode().getElementById?.(id))
                .filter(Boolean);
            if (labels.length) {
                return normal(labels.map((label) => name(label, seen) || renderedText(label, true)).join(" "));
            }
        }
        if (element.hasAttribute("aria-label")) {
            return normal(element.getAttribute("aria-label"));
        }
        if (element.labels?.length) {
            return normal([...element.labels].map((label) => renderedText(label, true)).join(" "));
        }
        if (element.localName === "img") {
            return normal(element.getAttribute("alt"));
        }
        if (element.matches("input[type=button],input[type=submit],input[type=reset]")) {
            return element.value || (element.type === "submit" ? "Submit" : "Reset");
        }
        if (element.matches("input,textarea,select") || element.isContentEditable) {
            return normal(element.getAttribute("title") || element.getAttribute("placeholder"));
        }
        return normal(renderedText(element) || element.getAttribute("title"));
    }
    function snapshot(maxChars = 20000) {
        const nodes = [];
        const elements = [];
        const scrollRegions = [];
        function inViewport(element, rect) {
            let left = Math.max(0, rect.left),
                top = Math.max(0, rect.top);
            let right = Math.min(innerWidth, rect.right),
                bottom = Math.min(innerHeight, rect.bottom);
            for (
                let parent = element.parentElement ?? element.getRootNode().host;
                parent;
                parent = parent.parentElement ?? parent.getRootNode().host
            ) {
                const style = getComputedStyle(parent);
                const bounds = parent.getBoundingClientRect();
                if (/auto|scroll|hidden|clip/.test(style.overflowX)) {
                    left = Math.max(left, bounds.left);
                    right = Math.min(right, bounds.right);
                }
                if (/auto|scroll|hidden|clip/.test(style.overflowY)) {
                    top = Math.max(top, bounds.top);
                    bottom = Math.min(bottom, bounds.bottom);
                }
            }
            return right > left && bottom > top;
        }
        function scrollInfo(element) {
            const page = element === document.scrollingElement;
            const style = getComputedStyle(element);
            const maxX = Math.max(0, element.scrollWidth - element.clientWidth);
            const maxY = Math.max(0, element.scrollHeight - element.clientHeight);
            const horizontal = maxX > 1 && (page || /auto|scroll/.test(style.overflowX));
            const vertical = maxY > 1 && (page || /auto|scroll/.test(style.overflowY));
            if (!horizontal && !vertical) return;
            return {
                page,
                x: element.scrollLeft,
                y: element.scrollTop,
                maxX,
                maxY,
                directions: [
                    vertical && element.scrollTop > 1 && "up",
                    vertical && element.scrollTop < maxY - 1 && "down",
                    horizontal && element.scrollLeft > 1 && "left",
                    horizontal && element.scrollLeft < maxX - 1 && "right",
                ].filter(Boolean),
            };
        }
        const visited = new Set();
        let limited = false;
        function walk(element, parentRef = null, depth = 0) {
            if (
                visited.has(element) ||
                element.id === "local-browser-control-cursor" ||
                ["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(element.tagName)
            ) {
                return;
            }
            visited.add(element);
            if (nodes.length >= 2000) {
                limited = true;
                return;
            }
            if (
                element.getAttribute("aria-hidden") === "true" ||
                element.hasAttribute("inert") ||
                getComputedStyle(element).display === "none"
            ) {
                return;
            }
            const scroll = visible(element) ? scrollInfo(element) : undefined;
            const nodeRole = visible(element) ? (role(element) ?? (scroll ? "region" : null)) : null;
            if (nodeRole) {
                const id = ref(element);
                const rect = element.getBoundingClientRect();
                const actions = [];
                if (scroll) actions.push(...scroll.directions.map((direction) => "Scroll " + direction));
                if (element.matches("details,summary") || element.hasAttribute("aria-expanded")) {
                    actions.push("Expand", "Collapse");
                }
                if (element.matches("input[type=number],input[type=range]")) {
                    actions.push("Increment", "Decrement");
                }
                const node = {
                    ref: id,
                    parentRef,
                    depth,
                    tag: element.localName,
                    role: nodeRole,
                    name: scroll?.page
                        ? "Page scroll area"
                        : sensitive(element) && !element.matches("input")
                          ? "[redacted]"
                          : name(element).slice(0, 500),
                    value: sensitive(element) ? "[redacted]" : element.value,
                    type: element.type,
                    focused: element === element.getRootNode().activeElement,
                    selectionStart: element.selectionStart,
                    selectionEnd: element.selectionEnd,
                    href: element.href,
                    checked: element.checked ?? element.getAttribute("aria-checked") ?? undefined,
                    disabled: !!element.disabled || element.getAttribute("aria-disabled") === "true",
                    readonly: !!element.readOnly || element.getAttribute("aria-readonly") === "true",
                    expanded:
                        element.localName === "details"
                            ? element.open
                            : (element.getAttribute("aria-expanded") ?? undefined),
                    selected: element.getAttribute("aria-selected") ?? undefined,
                    level: /^h[1-6]$/.test(element.localName)
                        ? Number(element.localName[1])
                        : (element.getAttribute("aria-level") ?? undefined),
                    actions,
                    inViewport: inViewport(element, rect),
                    visibility: inViewport(element, rect) ? "in-viewport" : "offscreen-or-clipped",
                    scroll,
                    bounds: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                };
                nodes.push(node);
                if (scroll)
                    scrollRegions.push({
                        ref: id,
                        name: node.name,
                        inViewport: node.inViewport,
                        bounds: node.bounds,
                        ...scroll,
                    });
                if (
                    scroll ||
                    element.matches(
                        "a[href],button,input,textarea,select,[role],[contenteditable='true'],[tabindex],summary",
                    )
                ) {
                    elements.push(node);
                }
                parentRef = id;
                depth++;
            }
            if (sensitive(element)) return;
            if (element.shadowRoot) {
                for (const child of element.shadowRoot.children) {
                    walk(child, parentRef, depth);
                }
            } else if (element.localName === "slot" && element.assignedElements().length) {
                for (const child of element.assignedElements()) {
                    walk(child, parentRef, depth);
                }
            } else {
                for (const child of element.children) {
                    walk(child, parentRef, depth);
                }
            }
        }
        if (document.documentElement) {
            walk(document.documentElement);
        }
        const text = document.body ? normal(renderedText(document.body)) : "";
        return {
            url: location.href,
            title: document.title,
            source: "dom-semantic",
            textScope:
                "Rendered document text, including off-screen content. Use inViewport and scrollRegions to plan scrolling.",
            viewport: { width: innerWidth, height: innerHeight },
            scrollRegions,
            text: text.slice(0, maxChars),
            truncated: text.length > maxChars || limited,
            nodes,
            elements,
        };
    }
    return { snapshot, name, role, sensitive };
};
