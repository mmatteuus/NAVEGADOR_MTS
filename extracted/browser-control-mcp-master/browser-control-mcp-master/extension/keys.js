// One key vocabulary for both input backends and the JavaScript compatibility API.
globalThis.browserControlKeys = (args) => {
    const parts = args.key.split("+");
    let key = parts.pop();
    const flags = { ctrl: !!args.ctrl, alt: !!args.alt, shift: !!args.shift, meta: !!args.meta };
    for (const part of parts) {
        const flag = {
            ctrl: "ctrl",
            control: "ctrl",
            alt: "alt",
            shift: "shift",
            meta: "meta",
            super: "meta",
            command: "meta",
        }[part.toLowerCase()];
        if (!flag) {
            throw new Error(`Unknown key modifier: ${part}`);
        }
        flags[flag] = true;
    }
    const aliases = {
        Return: "Enter",
        Esc: "Escape",
        space: " ",
        Space: " ",
        Left: "ArrowLeft",
        Right: "ArrowRight",
        Up: "ArrowUp",
        Down: "ArrowDown",
        Prior: "PageUp",
        Next: "PageDown",
    };
    key = aliases[key] ?? key;
    if (/^KP_\d$/.test(key)) {
        key = key.slice(-1);
    }
    if (
        !key ||
        (key.length > 1 &&
            ![
                "Enter",
                "Tab",
                "Escape",
                "Backspace",
                "Delete",
                "ArrowLeft",
                "ArrowRight",
                "ArrowUp",
                "ArrowDown",
                "Home",
                "End",
                "PageUp",
                "PageDown",
                "Insert",
            ].includes(key) &&
            !/^F([1-9]|1[0-2])$/.test(key))
    ) {
        throw new Error(`Unsupported key: ${key}`);
    }
    if (flags.shift && /^[a-z]$/.test(key)) {
        key = key.toUpperCase();
    }
    const virtual = {
        Enter: 13,
        Tab: 9,
        Escape: 27,
        Backspace: 8,
        Delete: 46,
        ArrowLeft: 37,
        ArrowUp: 38,
        ArrowRight: 39,
        ArrowDown: 40,
        Home: 36,
        End: 35,
        PageUp: 33,
        PageDown: 34,
        Insert: 45,
        " ": 32,
    };
    const code = /^[a-z]$/i.test(key)
        ? `Key${key.toUpperCase()}`
        : /^\d$/.test(key)
          ? `Digit${key}`
          : key === " "
            ? "Space"
            : key;
    return {
        key,
        code,
        ...flags,
        modifiers: (flags.alt ? 1 : 0) | (flags.ctrl ? 2 : 0) | (flags.meta ? 4 : 0) | (flags.shift ? 8 : 0),
        windowsVirtualKeyCode:
            virtual[key] ?? (/^F\d+$/.test(key) ? 111 + Number(key.slice(1)) : key.toUpperCase().charCodeAt(0)),
    };
};
