globalThis.browserControlInput = ({
    all,
    target,
    prepare,
    showCursor,
    settleCursor,
    visible,
    point,
    checkCancelled = () => {},
}) => {
    let hovered;
    const active = () => {
        let element = document.activeElement;
        while (element?.shadowRoot?.activeElement) {
            element = element.shadowRoot.activeElement;
        }
        return element;
    };
    const get = (args) => target(args, true) ?? active();
    function editable(element) {
        if (element.isContentEditable) {
            return;
        }
        if (
            !(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) ||
            element.readOnly ||
            element.disabled ||
            ["file", "checkbox", "radio", "button", "submit", "reset", "range", "color"].includes(element.type)
        ) {
            throw new Error("Target is not an editable text field.");
        }
    }
    function changed(element, text, inputType = "insertText") {
        element.dispatchEvent(new InputEvent("input", { bubbles: true, composed: true, data: text, inputType }));
        element.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    }
    function before(element, text, inputType = "insertText") {
        return element.dispatchEvent(
            new InputEvent("beforeinput", { bubbles: true, composed: true, cancelable: true, data: text, inputType }),
        );
    }
    function contentSelection(element) {
        const selection = element.ownerDocument.getSelection();
        if (
            !selection.rangeCount ||
            !element.contains(selection.anchorNode) ||
            !element.contains(selection.focusNode)
        ) {
            const range = document.createRange();
            range.selectNodeContents(element);
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
        }
        return selection;
    }
    function write(element, text, append = true) {
        editable(element);
        prepare(element, append ? "Typing" : "Fill");
        if (!before(element, text, append ? "insertText" : "insertReplacementText")) {
            return;
        }
        if (element.isContentEditable) {
            const selection = contentSelection(element);
            if (!append) {
                selection.selectAllChildren(element);
            }
            // Browser editing commands preserve existing markup and the editor's undo stack where supported.
            if (!document.execCommand("insertText", false, text)) {
                const range = selection.getRangeAt(0);
                range.deleteContents();
                const node = document.createTextNode(text);
                range.insertNode(node);
                range.setStartAfter(node);
                range.collapse(true);
                selection.removeAllRanges();
                selection.addRange(range);
                changed(element, text);
            } else {
                element.dispatchEvent(new Event("change", { bubbles: true }));
            }
            return;
        }
        const start = append ? (element.selectionStart ?? element.value.length) : 0;
        const end = append ? (element.selectionEnd ?? element.value.length) : element.value.length;
        const value = element.value.slice(0, start) + text + element.value.slice(end);
        const prototype =
            element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(prototype, "value").set.call(element, value);
        try {
            element.setSelectionRange(start + text.length, start + text.length);
        } catch {
            /* No selection API on numeric inputs. */
        }
        changed(element, text);
    }
    function mouse(element, type, x, y, button = 0, buttons = 0, detail = 0) {
        const options = {
            bubbles: !type.endsWith("enter") && !type.endsWith("leave"),
            composed: true,
            cancelable: true,
            clientX: x,
            clientY: y,
            button,
            buttons,
            detail,
        };
        return element.dispatchEvent(
            type.startsWith("pointer")
                ? new PointerEvent(type, { ...options, pointerId: 1, pointerType: "mouse", isPrimary: true })
                : new MouseEvent(type, options),
        );
    }
    function move(x, y, label = "Move", buttons = 0) {
        const element = target({ x, y });
        if (hovered !== element) {
            if (hovered?.isConnected) {
                for (const type of ["pointerout", "pointerleave", "mouseout", "mouseleave"]) {
                    mouse(hovered, type, x, y);
                }
            }
            for (const type of ["pointerover", "pointerenter", "mouseover", "mouseenter"]) {
                mouse(element, type, x, y);
            }
            hovered = element;
        }
        mouse(element, "pointermove", x, y, -1, buttons);
        mouse(element, "mousemove", x, y, 0, buttons);
        showCursor(x, y, label);
        return element;
    }
    function selectText(element, args) {
        editable(element);
        prepare(element, "Select text");
        const text = element.isContentEditable ? element.textContent : element.value;
        const matches = [];
        if (!args.text) {
            throw new Error("Selection text must not be empty.");
        }
        for (let at = text.indexOf(args.text); at >= 0; at = text.indexOf(args.text, at + 1)) {
            if (args.prefix && !text.slice(0, at).endsWith(args.prefix)) {
                continue;
            }
            if (args.suffix && !text.slice(at + args.text.length).startsWith(args.suffix)) {
                continue;
            }
            matches.push(at);
        }
        if (matches.length !== 1) {
            throw new Error(`Selection matched ${matches.length} occurrences. Supply prefix/suffix to identify one.`);
        }
        let start = matches[0];
        let end = start + args.text.length;
        if (args.selectionType === "cursor_before") {
            end = start;
        }
        if (args.selectionType === "cursor_after") {
            start = end;
        }
        if (!element.isContentEditable) {
            element.setSelectionRange(start, end);
            return { start, end };
        }
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        let position = 0;
        const range = document.createRange();
        let hasStart = false;
        while (walker.nextNode()) {
            const node = walker.currentNode;
            const next = position + node.length;
            if (!hasStart && start <= next) {
                range.setStart(node, start - position);
                hasStart = true;
            }
            if (end <= next) {
                range.setEnd(node, end - position);
                break;
            }
            position = next;
        }
        const selection = document.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return { start, end };
    }
    function press(element, args) {
        const key = globalThis.browserControlKeys(args);
        prepare(element, `Key ${key.key}`);
        const event = {
            key: key.key,
            code: key.code,
            bubbles: true,
            composed: true,
            cancelable: true,
            ctrlKey: key.ctrl,
            altKey: key.alt,
            shiftKey: key.shift,
            metaKey: key.meta,
        };
        try {
            if (!element.dispatchEvent(new KeyboardEvent("keydown", event))) {
                return;
            }
            if (key.key === "Tab") {
                const fields = all("a[href],button,input,textarea,select,[contenteditable='true'],[tabindex]")
                    .filter((item) => visible(item) && !item.disabled && !item.closest("[inert]") && item.tabIndex >= 0)
                    .sort((a, b) => (a.tabIndex || Infinity) - (b.tabIndex || Infinity));
                const index = fields.indexOf(element);
                fields[(index + (key.shift ? -1 : 1) + fields.length) % fields.length]?.focus();
                return;
            }
            if (key.key === "Escape") {
                return;
            }
            if (key.key === "Enter" && element.matches("button,a[href],summary")) {
                element.click();
                return;
            }
            if (key.key === " " && element.matches("button,input[type=checkbox],input[type=radio]")) {
                element.click();
                return;
            }
            if (key.key === "Enter" && element.form && element.localName !== "textarea") {
                element.form.requestSubmit();
                return;
            }
            editable(element);
            if ((key.ctrl || key.meta) && key.key.toLowerCase() === "a") {
                if (element.isContentEditable) {
                    document.getSelection().selectAllChildren(element);
                } else {
                    element.select();
                }
                return;
            }
            if (key.key.length === 1 && !key.ctrl && !key.meta && !key.alt) {
                write(element, key.key);
                return;
            }
            if (key.key === "Enter" && !key.ctrl && !key.meta && !key.alt) {
                write(element, "\n");
                return;
            }
            const selection = element.isContentEditable ? contentSelection(element) : null;
            if (selection) {
                if (["Backspace", "Delete"].includes(key.key)) {
                    document.execCommand(key.key === "Backspace" ? "delete" : "forwardDelete");
                    return;
                }
                const directions = {
                    ArrowLeft: "backward",
                    ArrowRight: "forward",
                    ArrowUp: "backward",
                    ArrowDown: "forward",
                    Home: "backward",
                    End: "forward",
                };
                if (directions[key.key]) {
                    selection.modify(
                        key.shift ? "extend" : "move",
                        directions[key.key],
                        ["Home", "End"].includes(key.key)
                            ? "lineboundary"
                            : /Up|Down/.test(key.key)
                              ? "line"
                              : key.ctrl || key.meta
                                ? "word"
                                : "character",
                    );
                    return;
                }
            } else if (element.selectionStart !== null) {
                const start = element.selectionStart;
                const end = element.selectionEnd;
                const value = element.value;
                const head = element.selectionDirection === "backward" ? start : end;
                const word = (position, direction) =>
                    direction < 0
                        ? position - (value.slice(0, position).match(/\s*\S+\s*$/)?.[0].length ?? position)
                        : position + (value.slice(position).match(/^\s*\S+\s*/)?.[0].length ?? value.length - position);
                if (["Backspace", "Delete"].includes(key.key)) {
                    const backwards = key.key === "Backspace";
                    const edge = key.ctrl || key.meta ? word(head, backwards ? -1 : 1) : head + (backwards ? -1 : 1);
                    if (start === end) {
                        element.setSelectionRange(
                            backwards ? Math.max(0, edge) : start,
                            backwards ? end : Math.min(value.length, edge),
                        );
                    }
                    write(element, "");
                    return;
                }
                let next;
                if (key.key === "Home") {
                    next = key.ctrl || key.meta ? 0 : value.lastIndexOf("\n", head - 1) + 1;
                }
                if (key.key === "End") {
                    const at = value.indexOf("\n", head);
                    next = key.ctrl || key.meta || at < 0 ? value.length : at;
                }
                if (["ArrowLeft", "ArrowRight"].includes(key.key)) {
                    const direction = key.key === "ArrowLeft" ? -1 : 1;
                    next =
                        !key.shift && start !== end
                            ? direction < 0
                                ? start
                                : end
                            : key.ctrl || key.meta
                              ? word(head, direction)
                              : head + direction;
                }
                if (next !== undefined) {
                    next = Math.max(0, Math.min(value.length, next));
                    const anchor = key.shift ? (element.selectionDirection === "backward" ? end : start) : next;
                    element.setSelectionRange(
                        Math.min(anchor, next),
                        Math.max(anchor, next),
                        next < anchor ? "backward" : "forward",
                    );
                    return;
                }
            }
            throw new Error(`DOM input cannot perform ${args.key} here. Use trusted input when available.`);
        } finally {
            element.dispatchEvent(new KeyboardEvent("keyup", event));
        }
    }
    return async (action, args) => {
        const result = { ok: true, inputMode: "dom", trusted: false };
        if (action === "move" || action === "hover") {
            const position = action === "move" ? point(args) : point(args, "Hover");
            move(position.x, position.y, action === "move" ? "Move" : "Hover");
            return result;
        }
        if (action === "drag") {
            const from = point({ x: args.from[0], y: args.from[1] });
            const to = point({ x: args.to[0], y: args.to[1] });
            const source = move(from.x, from.y, "Drag");
            const dataTransfer = new DataTransfer();
            mouse(source, "pointerdown", from.x, from.y, 0, 1);
            mouse(source, "mousedown", from.x, from.y, 0, 1);
            const started = source.dispatchEvent(
                new DragEvent("dragstart", {
                    bubbles: true,
                    cancelable: true,
                    dataTransfer,
                    clientX: from.x,
                    clientY: from.y,
                }),
            );
            let destination = source;
            try {
                for (let step = 1; step <= 12; step++) {
                    checkCancelled();
                    const x = from.x + ((to.x - from.x) * step) / 12;
                    const y = from.y + ((to.y - from.y) * step) / 12;
                    destination = move(x, y, "Drag", 1);
                    if (started) {
                        destination.dispatchEvent(
                            new DragEvent("dragover", {
                                bubbles: true,
                                cancelable: true,
                                dataTransfer,
                                clientX: x,
                                clientY: y,
                            }),
                        );
                    }
                    await new Promise((resolve) => setTimeout(resolve, 8));
                }
                checkCancelled();
                if (started) {
                    destination.dispatchEvent(
                        new DragEvent("drop", {
                            bubbles: true,
                            cancelable: true,
                            dataTransfer,
                            clientX: to.x,
                            clientY: to.y,
                        }),
                    );
                }
            } finally {
                mouse(destination, "pointerup", to.x, to.y);
                mouse(destination, "mouseup", to.x, to.y);
                source.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer }));
            }
            return result;
        }
        if (action === "click") {
            const { x, y, element } = point(args, "Click");
            const identity = () =>
                JSON.stringify([
                    element.localName,
                    element.getAttribute("role"),
                    element.getAttribute("aria-label"),
                    element.textContent,
                    element.getAttribute("href"),
                    element.getAttribute("type"),
                ]);
            const beforeIdentity = identity();
            const beforeBounds = element.getBoundingClientRect();
            const button = { left: 0, middle: 1, right: 2 }[args.mouseButton ?? "left"];
            const buttons = [1, 4, 2][button];
            move(x, y, "Click");
            await settleCursor();
            const hit = target({ x, y });
            const afterBounds = element.getBoundingClientRect();
            if (
                beforeIdentity !== identity() ||
                ["x", "y", "width", "height"].some((key) => Math.abs(beforeBounds[key] - afterBounds[key]) > 1) ||
                !element.isConnected ||
                !visible(element) ||
                element.disabled ||
                element.getAttribute("aria-disabled") === "true" ||
                element.closest("[inert]") ||
                (hit !== element && !element.contains(hit) && hit.getRootNode().host !== element)
            ) {
                throw new Error(
                    "Target changed, moved, became disabled or was covered during cursor movement. Read a fresh snapshot; click was not dispatched.",
                );
            }
            for (let count = 1; count <= (args.clickCount ?? 1); count++) {
                showCursor(x, y, "Click", true);
                const pointerDown = mouse(element, "pointerdown", x, y, button, buttons, count);
                const mouseDown = pointerDown && mouse(element, "mousedown", x, y, button, buttons, count);
                if (mouseDown) {
                    element.focus();
                }
                mouse(element, "pointerup", x, y, button, 0, count);
                mouse(element, "mouseup", x, y, button, 0, count);
                mouse(
                    element,
                    button === 0 ? "click" : button === 2 ? "contextmenu" : "auxclick",
                    x,
                    y,
                    button,
                    0,
                    count,
                );
            }
            if (button === 0 && args.clickCount === 2) {
                mouse(element, "dblclick", x, y, 0, 0, 2);
            }
            return result;
        }
        const element = get(args);
        if (action === "input_target") {
            const operation = args.operation;
            if (["click", "hover"].includes(operation)) {
                const { x, y } = point(args, operation);
                return { x, y };
            }
            if (["fill", "type", "paste"].includes(operation)) {
                editable(element);
            }
            prepare(element, operation);
            if (operation === "fill") {
                if (element.isContentEditable) {
                    document.getSelection().selectAllChildren(element);
                } else {
                    element.select();
                }
            }
            return {
                editable: element.isContentEditable || element.matches("input,textarea"),
                contentEditable: element.isContentEditable,
            };
        }
        if (action === "fill" || action === "type") {
            write(element, args.text, action === "type");
            return result;
        }
        if (action === "press") {
            press(element, args);
            return result;
        }
        if (action === "select_text") {
            return { ...result, ...selectText(element, args) };
        }
        if (action === "paste") {
            editable(element);
            prepare(element, "Paste");
            const transfer = new DataTransfer();
            transfer.setData(args.format === "html" ? "text/html" : "text/plain", args.text);
            if (
                !element.dispatchEvent(
                    new ClipboardEvent("paste", {
                        bubbles: true,
                        composed: true,
                        cancelable: true,
                        clipboardData: transfer,
                    }),
                )
            ) {
                return result;
            }
            if (args.format !== "html") {
                write(element, args.text);
                return result;
            }
            if (!element.isContentEditable) {
                throw new Error("HTML paste needs a contenteditable element.");
            }
            contentSelection(element);
            if (!document.execCommand("insertHTML", false, args.text)) {
                throw new Error("The browser could not insert HTML at the selection.");
            }
            element.dispatchEvent(new Event("change", { bubbles: true }));
            return result;
        }
        return null;
    };
};
