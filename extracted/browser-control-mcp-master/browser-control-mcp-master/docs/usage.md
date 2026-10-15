# Browser behaviour and API reference

[Installation and overview](../README.md)

New tabs open in a blue **MCP Automation** tab group in an existing normal window, without changing your selected tab by default. Named sessions reuse their group; new sessions prefer the focused normal window. A new window is created only when no normal, non-incognito window is available. Screenshots briefly select their target tab, then restore the previous selection unless you selected a different tab during capture. `browser_focus` intentionally brings the target forward.

A blue virtual cursor moves smoothly over 350 ms, pauses briefly before clicking, and shows a larger 950 ms click pulse without a text label. Real mouse, touch, keyboard or wheel input immediately hides the cursor and pulses; it returns on the next automation action, not passive snapshots. A click waiting for cursor arrival is cancelled if you interact. The injected viewport overlay uses a closed shadow root to isolate its styles and the browser's popover top layer to appear above dialogs. It is click-through and never moves your physical cursor. Reduced-motion settings disable movement animation and replace expanding pulses with a fade. Navigation removes the overlay until the next action; iframe actions display it within the targeted frame.

The cursor uses a nominal 24 px size. Cursor and pulse dimensions compensate for the tab's zoom factor, including live zoom changes. The blue arrow is not a pixel-for-pixel copy of the OS cursor theme or accessibility cursor size.

### Scroll visibility

Snapshots expose `viewport`, `textScope`, and `scrollRegions`: each region has a target ref, current offsets, maximum offsets and available scroll directions. Semantic nodes mark `inViewport:false` when outside the viewport or clipped by a scroll container. The JavaScript facade prints these as `off-screen` and scroll position/direction hints. Document text can still include off-screen content; this is explicitly labelled, and virtualized content may require scrolling to load.

With `showScrollbars:true`, a snapshot adds high-contrast scrollbar CSS to the document and open shadow roots, overriding common hidden-scrollbar styles without changing overflow behavior. Ordinary snapshots do not add styling. OS overlay-scrollbar auto-hiding and closed shadow roots cannot be guaranteed. Refreshing removes the injected styles.

### Idle tab cleanup

Automation tabs close after **four hours without use**, checked every five minutes. Change the timeout in the extension popup; `0` disables cleanup. Agent actions, navigation and selecting an owned tab refresh the session deadline. A selected or audible tab in a group keeps that group active. Pinned tabs and tabs marked as handoffs or deliverables are protected.

Only tabs created by this extension, or child tabs opened from them, are eligible. Manually added tabs and tabs outside their automation group are left alone. Closing the last tab removes the group automatically. Pin or mark tabs containing work you need to keep: unmarked idle tabs, including forms, may close.

Ownership and deadlines survive background-worker restarts, but not a full browser restart or extension reload. Older groups without recorded per-tab ownership are never adopted for automatic closure.

Call `browser_list`, then `browser_tabs`. Use the returned browser ID when more than one profile is connected.

## Tools

| Tools                                                                | Purpose                                                               |
| -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `browser_list`, `browser_windows`, `browser_tabs`, `browser_frames`  | Find browser profiles, windows, tabs and frames                       |
| `browser_open`, `browser_navigate`, `browser_close`, `browser_focus` | Manage tabs                                                           |
| `browser_back`, `browser_forward`, `browser_reload`                  | Navigate history and reload                                           |
| `browser_snapshot`                                                   | Read visible text and interactive element refs                        |
| `browser_screenshot`                                                 | Capture a locally masked viewport PNG                                 |
| `browser_observe`, `browser_collect`                                 | Combine page observations or collect visible rows while scrolling     |
| `browser_action_status`, `browser_events`                            | Inspect operation status and recent human takeover events             |
| `browser_click`, `browser_hover`, `browser_move`                     | Interact with an element or move the virtual cursor                   |
| `browser_fill`, `browser_type`, `browser_select`, `browser_press`    | Edit forms and send keys                                              |
| `browser_scroll`, `browser_wait`                                     | Scroll or wait for text/an element                                    |
| `browser_drag`, `browser_select_text`, `browser_paste`               | Drag, select a text range and paste text or HTML                      |
| `browser_secondary`, `browser_mark`                                  | Expand/collapse controls, change numeric values and mark tab handoffs |
| `browser_capabilities`, `browser_accessibility`                      | Check input support and read Chrome's native accessibility tree       |
| `browser_api`, `browser_run`, `browser_reset`                        | Read the JavaScript API, run persistent scripts and reset variables   |

Page tools use `tabId`. Targets use `ref` from a snapshot or a CSS `selector` that matches one element. Click also accepts viewport coordinates `x` and `y`. Use `frameId` for an iframe. Open shadow roots are included. Refs are scoped to a document and become stale after navigation.

Typical sequence:

```text
browser_list {}
browser_tabs {"browser":"firefox"}
browser_snapshot {"browser":"firefox","tabId":3}
browser_fill {"browser":"firefox","tabId":3,"ref":"<ref from snapshot>","text":"Example"}
browser_click {"browser":"firefox","tabId":3,"selector":"button[type=submit]"}
```

## Action verification

Page clicks, edits, selections, keys, scrolling, dragging and secondary actions include `verification`. Field edits and selections are compared against the requested DOM value; other actions compare semantic page state. Checks default to 1.2 seconds on visible pages and 3 seconds on hidden pages; `expect.timeoutMs` allows up to 10 seconds. Exact matches must settle for 400 ms on visible pages and 1.2 seconds on hidden pages, where browser timers can delay application updates. Status is `verified`, `already-satisfied`, `observed-change`, `unconfirmed`, or `mismatch`. An observed change is not proof of the intended outcome. Focus movement and the cursor overlay do not count as semantic success.

Direct action tools accept an optional `expect` object containing `text`, `selector`, and/or `urlIncludes` (all supplied conditions must match). For example, `browser_click` can include `"expect":{"text":"Settings saved"}`. Mismatches return a tool error without undoing or replaying the action. The JavaScript facade emits verification summaries and throws on mismatches. After a navigation destroys the observation context, verification may be unavailable; inspect the current page before retrying.

Verification never returns field contents and does not prove server-side persistence. Unconfirmed actions are never automatically retried. For slow applications, follow with `browser_wait` and a fresh observation.

## Persistent browser scripts

Call `browser_api` for the reference. `browser_run` accepts JavaScript with top-level await. Variables remain available in the next call from the same MCP client:

```js
let tab = await cua.createBrowserTab("chrome", "https://example.com", {
    sessionName: "Research",
});
```

In a later call:

```js
await tab.getAXStateAndScreenshot();
await tab.markDeliverable();
```

State output contains numeric element indices. Use a current index with `tab.click(index)` or `tab.setValue(index, text)`. Use `nodeRepl.write(value)` to return other values. Observations emit automatically unless `emit:false` is set. Each named session has its own tab group; groups can share a window with normal tabs. Handoff and deliverable marks protect tabs from idle cleanup; they do not send messages or publish tabs.

Scripts run in a separate local Node process, **not a security sandbox**. They have the MCP process's OS permissions. Await all browser actions. A script timeout resets its variables but does not undo or cancel browser actions already sent. `browser_reset` clears variables without closing tabs. See [API compatibility](compatibility.md) for exact signatures and differences.

## Limits

This is an independent implementation with a browser-facing `cua` compatibility API. It does not implement OpenAI's private extension protocol or all of its runtime features.

- Chrome supports trusted **text insertion only**, when the target tab is active in the focused window. Background automation uses DOM input. Explicit `inputMode:"trusted"` requests fail if the target is not in front; they never focus it automatically. `inputMode:"dom"` always requests synthetic input. Close DevTools for the target tab if they conflict with attachment.
- Pointer actions and keyboard chords use DOM events in both browsers. Native Chrome pointer and key delivery did not pass validation, so `trustedPointer` and `trustedKeyboard` are false. Explicit trusted pointer/key requests return an error. Sites that require these trusted events are not supported.
- Firefox and explicit iframe actions use synthetic DOM input. Sites can reject these events. Synthetic hover does not guarantee CSS `:hover`, and synthetic drag does not reproduce every browser drag behaviour. Neither backend moves your physical pointer.
- HTML paste uses DOM editing in both browsers. Text and Markdown paste insert literal text, not rendered Markdown. Native clipboard contents are not changed.
- Browser settings pages, extension stores and some built-in viewers block content scripts.
- Screenshots cover the visible viewport and briefly activate the requested tab within its window before restoring the previous selection. They can briefly interrupt what you see. Explicitly targeting one of your normal tabs can still affect that tab.
- It does not support file upload/download management, browser permission dialogs, native dialogs, closed shadow roots or browser-toolbar keyboard shortcuts. The JavaScript API controls page input, not the address bar.
- Semantic snapshots approximate accessible names and hierarchy from the DOM; they are not complete native accessibility trees. Chrome's native tree is available separately through `browser_accessibility`. Firefox does not provide that tool.
- Password input values are redacted in snapshots. Page text and screenshots can still contain sensitive data and are returned to the MCP client.
- Browser navigation can finish before a single-page application has rendered its content. Use `browser_wait` for the required element or text.
- The MCP process and browser must run on the same computer. A remote agent needs to launch this stdio server on the browser's computer, for example through SSH. Do not expose the loopback bridge publicly.
