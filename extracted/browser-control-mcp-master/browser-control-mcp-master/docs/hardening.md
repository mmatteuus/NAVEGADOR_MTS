# Hardening requirements

Source: user's request to implement all discussed improvements. Explicitly
excluded: task-control panel, sidebar or dashboard. Essential controls belong
in the existing popup.

1. Human takeover is per tab, cancels queued work and pending input, emits an
   event, and requires a fresh snapshot, not manual resume. Closing a task stops it.
2. Durable operation IDs prevent blind replay after failures. Keep outcome
   uncertainty explicit; never claim arbitrary website exactly-once semantics.
3. Document/revision preconditions, readiness and target identity rechecks,
   configurable outcome deadlines; DOM state is not server persistence.
4. Unified observations include document/revision, screenshot, scroll/frame
   mapping and consistency limits. Identify offscreen/clipped targets. Scrollbar
   styling is optional. Virtualized collection has bounded, deduplicated output
   and honest completeness limits.
5. No per-site permission system or task/pause UI (user-requested removal).
   Screenshots are always masked automatically. Keep only connection and cleanup controls.
6. Native messaging option and Linux Chrome/Chromium/Helium/Firefox installer.
   Keep fallback and safe recovery. Test native input and report differences
   honestly instead of claiming browser parity.
7. Local screenshot masks, redacted known-sensitive fields/private content,
   tabs available without approval, short-lived metadata-only
   diagnostics, and secret-free manual login handoff.
8. Hostile tests: moving/replaced/covered targets, human interruption, delayed
   value rollback, nested scrolling, disconnect/recovery, Chrome and Firefox.

## Explicit implementation limits

- No extension-level site approvals. Browser-enforced permissions and local
  pairing authentication remain; old site-grant settings are ignored.
- `browser_run` is full-trust local Node, not a security sandbox against a
  malicious same-user client rewriting local installation files.
- Journal stores keyed request fingerprints and lifecycle metadata, never
  arguments or results. A completed reply does not prove website persistence.
- Native messaging removes the browser-side WebSocket. The local host still
  uses an authenticated loopback bridge; there is no remote relay.
- Native Chrome foreground text insertion is supported; trusted pointer/keyboard
  delivery remains explicitly unsupported. DOM input is tested in both browsers.
- Screenshot masking covers password/OTP/payment fields, explicitly private
  elements and all iframe rectangles, not arbitrary secret recognition. Disable
  the connection for highly sensitive activity. DOM consistency does not prove atomic
  rendering, CSS animation/canvas stability or network completion.
- Row deduplication uses role/text; identical rows can collapse. Reaching the
  current scroll boundary never proves complete server-side data.
- Login handoff: disable the connection, use Bitwarden/passkey/2FA manually, re-enable, then obtain
  fresh state. No credential or automatic login-success assertion is returned.
