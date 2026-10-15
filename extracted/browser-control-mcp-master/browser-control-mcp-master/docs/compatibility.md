# Browser API compatibility

The API matches the browser-facing method names exposed by the ChatGPT/Codex browser runtime. It is not the private extension wire protocol. The transport stays local: MCP stdio to an authenticated loopback bridge to the extension.

## Runtime

Use `browser_run({code, timeoutMs})`. The timeout defaults to 30 seconds and has a 60-second maximum. Top-level `await`, `let` and `const` declarations persist within one MCP client. Separate clients have separate variables but share browser state. Use dynamic `await import(...)` for Node modules.

`nodeRepl.write(value)` returns text. `nodeRepl.emitImage(bytes)` returns PNG bytes; `{bytes, mimeType}` and base64 image data URLs also work. `console.log` returns text. Successful expressions are not printed automatically. Page observations print automatically unless `emit:false` is supplied.

`browser_reset` terminates that client's worker. A timeout also terminates the worker, including a synchronous infinite loop. Previously sent browser actions can still finish. Inspect the page before retrying. Ordinary script errors preserve variables. Do not start unawaited browser actions: they are not cancelled when a cell returns.

The runtime has full local Node permissions. Do not treat it as a sandbox for untrusted code.

## Entry points

| Method                                                       | Behaviour                                                                                                                            |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `cua.getState()`                                             | Lists connected browsers and their tabs; native apps are empty.                                                                      |
| `cua.listBrowsers()`                                         | Lists connected profile IDs and browser families.                                                                                    |
| `cua.listTabs({browser})`                                    | Lists tabs; includes session names and handoff/deliverable marks.                                                                    |
| `cua.getBrowser({id})`                                       | Returns `{browserId, documentation()}` and emits API documentation.                                                                  |
| `cua.getTab(id, {browser})`                                  | Binds an existing tab and emits its initial semantic state.                                                                          |
| `cua.createBrowserTab(browser, url, {sessionName, visible})` | Opens a background tab in a named group, reusing an existing normal window, and emits initial state. `visible:false` is unsupported. |
| `cua.listApps()` / `cua.getApp(name)`                        | Empty list / explicit unsupported error.                                                                                             |

Use the profile ID from observations, or `chrome`/`firefox` if exactly one profile matches. Ambiguous browser and tab IDs produce errors. There is no in-app browser provider, native application control or provider-selection interface.

## Tab methods

| Method                                                     | Arguments and result                                                                                                         |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `getAXState({emit, disableDiffing})`                       | Returns a DOM semantic hierarchy with numeric indices and visible text. Later calls report added, changed and removed nodes. |
| `getScreenshot({emit})`                                    | Returns PNG bytes for the visible viewport.                                                                                  |
| `getAXStateAndScreenshot(options)`                         | Returns `{state, screenshot}` and emits both by default.                                                                     |
| `click(indexOrPoint, {mouseButton, clickCount})`           | Index or `[x,y]` in viewport CSS pixels. Buttons: `left/right/middle` or `l/r/m`. Count: 1 or 2.                             |
| `drag(from, to)`                                           | Two `[x,y]` points. Synthetic pointer, mouse and drag events in both browsers.                                               |
| `pressKey(key)`                                            | Chords such as `ctrl+a`, `shift+Left`, `Return` and `Tab`; page input only.                                                  |
| `typeText(text)`                                           | Inserts at the current selection/caret.                                                                                      |
| `setValue(index, value)`                                   | Replaces a text field's value. Use the direct `browser_select` tool for select options.                                      |
| `paste(text, {format})`                                    | `text` (default), literal `md`, or DOM-edited `html`.                                                                        |
| `selectText(index, text, {prefix, suffix, selectionType})` | Requires one matching occurrence. Selection type: `text`, `cursor_before` or `cursor_after`.                                 |
| `scroll(indexOrPoint, direction, pages)`                   | Scrolls the nearest scroll container by viewport/container pages. Direction accepts full names or `u/d/l/r`.                 |
| `performSecondaryAction(index, action)`                    | Only actions listed in the observation: Expand, Collapse, Increment, Decrement.                                              |
| `goto(url)`, `back()`, `forward()`, `reload()`, `close()`  | Navigates or closes; invalidates observed indices.                                                                           |
| `markDeliverable()`, `markHandoff()`                       | Records local metadata on the tab. Does not bring it forward.                                                                |

Read state before using an index. Indices are local to the bound tab object and must not be copied between tab objects. Reload and navigation invalidate them. The compatibility API targets the top frame. Use direct tools with `frameId` for iframe controls.

## Important differences

- `getAXState` is an approximate DOM tree, not OpenAI's or the browser's full accessibility tree. Open shadow roots work; closed roots do not. Native Chrome accessibility is a separate read-only direct tool.
- Chrome supports trusted top-frame text insertion through `chrome.debugger` in an active foreground tab. Background automation uses DOM input. Explicit trusted input rejects an unfocused target; it never brings your window forward. The API reports `trustedInputRequiresFocus:true`. The browser can display a debugging banner. Do not switch away during a native text action.
- Pointer actions and keyboard chords use DOM events in both browsers. Native Chrome pointer/key delivery did not pass validation, including navigation and background-window cases. This implementation reports `trustedPointer:false` and `trustedKeyboard:false` and rejects explicit trusted pointer/key requests. Sites that require those trusted events remain unsupported.
- Firefox has no equivalent standard `chrome.debugger` extension API. Its DOM events have `isTrusted:false`. Browser-native actions and some site controls will not accept them. Requesting trusted input explicitly on Firefox produces an error.
- Screenshots briefly select the requested tab inside its window, then restore the previous selection unless the user selected another tab. They preserve the focused window in the tested browsers. Explicitly controlling a normal tab can still disturb that tab.
- Named task groups share existing normal windows. Owned automation tabs close after four idle hours by default, with a five-minute sweep. The popup can change or disable this timeout. Selected/audible groups and pinned or marked tabs are protected. Ownership and marks last for the browser session, not across browser restarts or extension reloads; legacy groups are not adopted for closure. The virtual cursor is a non-interactive page overlay, not an OS cursor.
- No file transfer API, permission-dialog handling, OS key input, invisible tabs or private OpenAI transport compatibility is supplied.
