# Local Browser Control MCP

Control Chrome, Helium and Firefox from an MCP client using your existing browser session. The server runs locally. No remote relay, account or debugging port is required.

- Reuse existing windows and keep automation tabs in named groups.
- Read page state, scroll containers and frames; fill forms and verify actions.
- Show a smooth virtual cursor with click pulses. Human input hides it and cancels pending work.
- Mask sensitive screenshot regions locally, by default and without a switch.
- Close unused automation tabs after four hours. Preserve pinned and marked tabs.
- Use an authenticated local WebSocket, or an optional native messaging pipe.

This is an independent project. It does not use or reproduce OpenAI's private extension protocol.

## Install

Requires **Node.js 22+**, **Chrome/Helium 120+** or **Firefox 139+**.

### Release package

Download the server `.tgz` from [Releases](https://github.com/kierandrewett/browser-control-mcp/releases), then install it:

```sh
npm install -g ./browser-control-mcp-0.1.0.tgz
browser-control-mcp --setup
```

The setup command creates locally paired extension folders, starts the bridge and prints your MCP configuration. Add that configuration to your client, then reconnect it.

Load the extension folder printed by setup:

- **Chrome / Helium:** open `chrome://extensions`, enable **Developer mode**, select **Load unpacked**, then select the `chrome` folder.
- **Firefox:** open `about:debugging#/runtime/this-firefox`, select **Load Temporary Add-on**, then select `firefox/manifest.json`.

The popup shows **Connected** when the bridge is available. It contains only the connection toggle and idle cleanup timeout.

**Firefox releases are unsigned.** Temporary installation ends when Firefox closes. Permanent installation in standard Firefox requires Mozilla signing. The Chrome ZIP is for unpacked installation, not a signed Web Store release.

Registry publication is pending. Use the release package above until an npm package name is confirmed.

### Using a downloaded extension ZIP

Setup already creates extension folders. If you prefer the separate release ZIP, extract it to a permanent folder and pair it before loading:

```sh
browser-control-mcp --pair-extension /path/to/extracted-extension
```

Public ZIPs contain **no pairing secret**. After pairing, the local folder contains your secret: do not upload or share that folder.

### Build from source

```sh
git clone https://github.com/kierandrewett/browser-control-mcp.git
cd browser-control-mcp
yarn install
yarn build
yarn setup
```

Use the extension paths and MCP configuration printed by setup. Development builds are also available in `build/chrome` and `build/firefox`.

After an update, repeat the build and setup commands, reload the extension and reconnect the MCP client.

## Start using it

Ask your client to call `browser_list`, then `browser_tabs`. If multiple profiles are connected, use the returned browser ID.

```text
browser_list {}
browser_tabs {"browser":"chrome"}
browser_snapshot {"browser":"chrome","tabId":3}
```

The server also provides a persistent JavaScript API:

```js
let tab = await cua.createBrowserTab("chrome", "https://example.com", {
    sessionName: "Research",
});
await tab.getAXStateAndScreenshot();
```

Read [browser behaviour and tools](docs/usage.md), [JavaScript API compatibility](docs/compatibility.md), and [privacy and recovery limits](docs/hardening.md).

## Behaviour and safety

There are no per-site approvals, task controls or manual resume buttons. When enabled, the connection can control your browser tabs. Browser-enforced permissions still apply.

Real mouse, keyboard, touch or wheel input cancels pending work and hides the virtual cursor. The agent must read a fresh snapshot before further actions. Disable the connection for private activity such as password-manager login.

Screenshots are always masked locally. Masking is not a guarantee that all sensitive page content is detected. Page text can still contain private information. Screenshots briefly select their target tab, then restore the previous selection.

New tabs normally open in an existing window without changing its selected tab. Named sessions use tab groups. Closing the last task tab removes the group and ends that named session.

Only recorded automation tabs are eligible for four-hour idle cleanup. Pinned tabs and marked handoffs or deliverables are protected. Ordinary tabs are not adopted for cleanup. Unmarked idle forms can close, so mark work you need to keep.

Chrome supports trusted text insertion when its target is active in the focused window. Pointer and key actions use DOM events in both browsers. Sites that require trusted pointer or key events may reject them. Chrome can show a debugger attachment banner.

Actions are not automatically replayed after failure. A lost reply can mean an action already happened. Read current page state and use `browser_action_status` before retrying a write.

The JavaScript runtime has your local OS permissions. It is **not a security sandbox**.

## Local connection

The bridge listens on `127.0.0.1:18925`. It uses a random pairing token, rejects web-page origins, reconnects after connection loss and expires journal metadata after 24 hours. The journal stores no page content, screenshots, action arguments or results.

npm installations store configuration, journal data and generated extensions in `~/.local/share/browser-control-mcp`. Source checkouts keep their existing `.local` directory. Set `BROWSER_CONTROL_HOME` to use another directory; use the same value for setup and the MCP server.

To diagnose startup, run `browser-control-mcp --bridge` in a terminal. For a custom port, stop the existing bridge, change `port` in the data directory's `config.json`, repeat setup, then reload both the extension and MCP client.

Keep the bridge on loopback. The server and browser must run on the same computer. A remote agent must start the stdio server on that computer, for example through SSH.

### Optional native messaging on Linux

From a source checkout, install the native host with your browser's extension ID:

```sh
node scripts/install-native.mjs helium YOUR_EXTENSION_ID
```

Use `chrome` or `chromium` for those browsers. For Firefox, use `node scripts/install-native.mjs firefox`. Chromium-based browsers accept a custom user-data directory as the third argument.

Reload the extension. The popup reports native messaging or local WebSocket transport. The native host uses OS pipes to the browser and still connects to the authenticated local bridge.

## Development

```sh
yarn check
yarn build
yarn test
```

Browser tests use temporary profiles and isolated bridge ports. They do not control your normal browsing session. Install Chromium with `yarn playwright install chromium`. To test Firefox:

```sh
GECKODRIVER=/path/to/geckodriver yarn test
```

Firefox tests expect `/usr/bin/firefox`. The suite covers forms, shadow roots, frames, screenshots, cursor behaviour, human takeover, idle cleanup and connection recovery.

### Create release files

```sh
yarn release:extensions
npm pack
```

The extension command requires `zip`. It creates fresh, unpaired Chrome and Firefox ZIPs plus `SHA256SUMS` in `releases/v<VERSION>`. It refuses to overwrite existing release files. Never ZIP the paired `build` folders for distribution.

The npm package uses an explicit file allowlist. Local configuration, build folders, browser profiles and test captures are excluded.

After installing a tarball in a temporary directory, test the installed package with:

```sh
node scripts/test-installed.mjs /path/to/node_modules/browser-control-mcp
```

This checks setup, generated extensions, MCP requests and the script runtime using isolated configuration and a temporary bridge port.
