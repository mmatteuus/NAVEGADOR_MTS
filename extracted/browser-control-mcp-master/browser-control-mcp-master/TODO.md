- [x] Build the authenticated local bridge and MCP tools.
- [x] Build Chrome and Firefox extensions from shared source.
- [x] Test browser actions and connection recovery.
- [x] Document installation and known browser limits.
- [x] Reuse existing windows with background automation tab groups and a virtual cursor.
- [x] Close owned idle tabs after four hours with configurable cleanup and protected tabs.

## Browser API parity

- [x] Preserve click coordinates; add mouse buttons, double-click and DOM drag.
- [x] Add native Chrome text insertion and accessibility with explicit capability reporting.
- [x] Add text selection, formatted paste and keyboard editing.
- [x] Return semantic page hierarchy, accessible names and state changes.
- [x] Add a persistent JavaScript tool with the documented browser-facing cua methods.
- [x] Support named task sessions and tab handoff metadata.
- [x] Test the new actions, runtime persistence, failure cases and browsing isolation in both browsers.
- [ ] Reliable trusted pointer and keyboard input. Current implementation explicitly rejects these modes.

## Distribution

- [x] Package the CLI and keep npm installation data outside the package directory.
- [x] Build secret-free Chrome and Firefox release ZIPs with local pairing.
- [x] Test the packed package and document release installation.
- [x] Publish GitHub release files and verify their checksums.
- [ ] Publish to npm after the owner confirms the available package scope and logs in.
