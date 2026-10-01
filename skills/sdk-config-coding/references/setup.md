# SDK Config Coding — setup walkthrough

This is the guided, one-time setup for the `sdk-config-coding` skill's browser tooling.
It is safe to re-run: every step first checks whether it is already done and offers to
skip it, and the whole flow can be skipped. Most steps are **per-machine** (done once
ever); ESLint is **per-project**.

This walkthrough runs in Claude Code only. If you are in Claude Cowork or the Claude app,
stop and tell the user to run it from Claude Code.

## When this file is read

- The skill's Step 0 setup check reads it on `SETUP_NEEDED` (after the user accepts the
  walkthrough). A declined walkthrough doesn't come here: Step 0 writes the all-`skipped`
  marker itself.
- "Setup mode" in the skill reads it when the user runs
  `/sdk-config-assistant:sdk-config-coding setup`, or asks to set up, repair or
  re-check the skill's browser tooling, or to switch Chrome mode.

## Step 0 — Locate the marker file

The per-machine marker records each step's status so finished/skipped steps aren't
re-asked, and the chosen Chrome mode. It lives at a fixed path, alongside the MCP
launcher:

```bash
STATE_FILE="$HOME/.claude/sdk-config-coding/setup-state.json"
mkdir -p "$(dirname "$STATE_FILE")"
[ -f "$STATE_FILE" ] && echo MARKER_FOUND || echo NO_MARKER
```

- `NO_MARKER` → first run on this machine.

Read the marker if it exists (`cat "$STATE_FILE"`). Use its contents to pre-mark steps as
already done and skip straight past them unless the user wants to redo one. A marker with
no `chromeMode` (written by an earlier version, `"version": 1`) means `dedicated` — that is
what those installs were set up as. You'll write the marker in Step 1 and again in the
final step.

Then confirm the plan with the user in one line ("I'll walk through Chrome profile →
MCP → launch alias → Tampermonkey → optional ESLint, skipping anything already done")
and proceed. If the user only wants specific steps, jump to those.

## Step 1 — Choose the Chrome profile (per-machine)

The plugin can drive Chrome in one of two modes. Detect what's already there first, so
an earlier setup is recognised rather than recreated:

```bash
P="$HOME/.chrome-acoustic-profile"
if [ -f "$P/Local State" ]; then echo PROFILE_IN_USE
elif [ -d "$P" ]; then echo PROFILE_EMPTY
else echo PROFILE_MISSING; fi
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version 2>/dev/null || echo NO_CHROME
```

`PROFILE_IN_USE` means a dedicated profile from an earlier setup (by this wizard, an older
version of it, or the README's manual steps) — Chrome has run on it and it may already
hold Tampermonkey and scripts. `PROFILE_EMPTY` means the directory was created but Chrome
never launched on it.

Present the choice. If the marker already has a `chromeMode`, say which is current and
ask whether to keep it; if `PROFILE_IN_USE` and there's no marker, open with "Found an
existing dedicated Chrome profile at `~/.chrome-acoustic-profile`" and recommend keeping it.

| | **Dedicated profile** (recommended) | **Default profile** |
|---|---|---|
| Browser | A separate Chrome window on `~/.chrome-acoustic-profile` | Your everyday Chrome |
| Isolation | Tampermonkey, client-site logins and DevTools settings stay out of your personal profile | The MCP can see your everyday tabs and logins; Tampermonkey is installed in your personal profile |
| Starting Chrome | The plugin launches it for you | You open Chrome as normal; the plugin never relaunches it |
| Requirement | Any Chrome | Chrome 144 or later |

- **Dedicated** → go to Step 1a.
- **Default** → check the version printed above. If the major version is below 144, explain
  that Chrome 136+ blocks remote debugging of the default profile via command-line flags and
  only 144+ supports attaching to it, then offer dedicated instead (or updating Chrome
  first). Otherwise go to Step 1b.
- `NO_CHROME` → Chrome isn't installed at the standard path; stop and ask the user to
  install Google Chrome before continuing.

**Write `chromeMode` to the marker immediately** (not just in the final step): the MCP
launcher (`~/.claude/sdk-config-coding/chrome-devtools-mcp.sh`) reads it at startup to
decide how to connect. Merge into any existing marker rather than overwriting other steps, e.g.:

```bash
STATE_FILE="$HOME/.claude/sdk-config-coding/setup-state.json"
MODE="dedicated"   # or "default"
mkdir -p "$(dirname "$STATE_FILE")"
if [ -f "$STATE_FILE" ] && grep -q '"chromeMode"' "$STATE_FILE"; then
  sed -i '' "s/\"chromeMode\"[[:space:]]*:[[:space:]]*\"[a-z]*\"/\"chromeMode\": \"$MODE\"/" "$STATE_FILE"
elif [ -f "$STATE_FILE" ]; then
  sed -i '' "s/^{/{\\
  \"chromeMode\": \"$MODE\",/" "$STATE_FILE"
else
  printf '{\n  "version": 2,\n  "chromeMode": "%s"\n}\n' "$MODE" > "$STATE_FILE"
fi
cat "$STATE_FILE"
```

**Switching mode** on a re-run: never delete `~/.chrome-acoustic-profile` when moving to
default — tell the user it's kept, so switching back is instant. After the marker changes,
the MCP must reconnect to pick up the new mode (see Step 2).

**Switching from default back to dedicated:** remind the user to turn remote debugging
**off** at `chrome://inspect/#remote-debugging` in their everyday Chrome. While it's on, that
Chrome listens on `127.0.0.1:9222` — the same port the dedicated profile needs — so the
dedicated Chrome can't take the port and the MCP would attach to the everyday browser
instead. Step 2's ownership check catches this if they forget.

### Step 1a — Dedicated profile

- `PROFILE_IN_USE` → tell the user the existing profile will be reused as-is (nothing is
  overwritten) and mark `chromeProfile: "done"`.
- `PROFILE_EMPTY` → tell them the directory exists but hasn't been used yet; it will be used
  as-is. Mark `chromeProfile: "done"`.
- `PROFILE_MISSING` → create it:
  ```bash
  mkdir -p "$HOME/.chrome-acoustic-profile"
  ```
  Mark `chromeProfile: "done"`, or `"skipped"` if the user declines.

### Step 1b — Default profile

Remote debugging has to be switched on once inside the user's everyday Chrome:

1. Ask the user to open Chrome as they normally do (if it isn't already running).
2. Have them open `chrome://inspect/#remote-debugging` and enable remote debugging there.
   This is a manual step in the browser — it can't be automated. The setting persists.
3. Confirm with the user that it's on.

Mark `chromeProfile: "done"` (the "profile" here is the default one), or `"skipped"` if
the user declines.

## Step 2 — Register and verify the MCP (per-machine)

The Chrome DevTools MCP is not bundled with the plugin (a plugin-level server would start
for every `sdk-config-assistant` user). This step registers it for this user only, as the
user-scoped server `sdk-chrome-devtools`.

### Register

Copy the launcher to its fixed location (always, so a re-run picks up plugin updates) and
check whether the server is registered:

```bash
D="$HOME/.claude/sdk-config-coding"; mkdir -p "$D"
cp "${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/bin/chrome-devtools-mcp.sh" "$D/" && chmod +x "$D/chrome-devtools-mcp.sh" && echo LAUNCHER_OK
claude mcp get sdk-chrome-devtools >/dev/null 2>&1 && echo MCP_REGISTERED || echo MCP_MISSING
```

- `LAUNCHER_OK` missing → the copy failed (check that the source path exists); stop and
  tell the user.
- `MCP_REGISTERED` → carry on to "Verify".
- `MCP_MISSING` → explain that this adds a user-level MCP server to their Claude Code
  config (`~/.claude.json`), available in all their Claude Code sessions, and ask before
  running:
  ```bash
  claude mcp add --scope user sdk-chrome-devtools -- "$HOME/.claude/sdk-config-coding/chrome-devtools-mcp.sh"
  ```
  A newly added server isn't loaded into the current session. Ask the user to exit and run
  `claude --continue` to resume here, then carry on to "Verify". If they decline to
  register it, mark `mcp: "skipped"` and move to Step 3.

### Verify

The MCP starts through `~/.claude/sdk-config-coding/chrome-devtools-mcp.sh`, which picks
the connection from `chromeMode`: `--browser-url=http://127.0.0.1:9222` for dedicated,
`--autoConnect` for default. If `chromeMode` was just written or changed in Step 1, the
running MCP is still on the old setting — **stop and ask the user to reconnect it** (`/mcp`
→ select `sdk-chrome-devtools` → reconnect), or restart the session, and wait for them to
confirm before testing. Warn them that `/mcp` will probably already show it as connected: that's the
old connection, and it may even work (e.g. an everyday Chrome with remote debugging on is
reachable on 9222), but it isn't the mode they chose. Reconnect anyway.

Confirm the MCP is running with the chosen mode's flag before calling `list_pages`:

```bash
pgrep -fl "^npm exec chrome-devtools-mcp@latest" | grep -o -e "--autoConnect" -e "--browser-url=[^ ]*" | sort -u
```

Expect `--autoConnect` for default or `--browser-url=http://127.0.0.1:9222` for dedicated.
Other Claude sessions or plugins may run their own `chrome-devtools-mcp`, so both can appear.
If the expected flag is missing, the reconnect hasn't happened yet.

### Dedicated

1. Check whether port 9222 is free, and if not, **which Chrome owns it** — a listener
   alone doesn't mean it's the dedicated profile:
   ```bash
   PID=$(lsof -nP -iTCP:9222 -sTCP:LISTEN -t 2>/dev/null | head -n 1)
   if [ -z "$PID" ]; then echo PORT_FREE
   else
     CMD=$(ps -ww -p "$PID" -o command=)
     case "$CMD" in
       *"--user-data-dir=$HOME/.chrome-acoustic-profile"*) echo DEDICATED_UP ;;
       *"Google Chrome"*--remote-debugging-port*) echo OTHER_DEBUG_CHROME; echo "$CMD" ;;
       *"Google Chrome"*) echo DEFAULT_CHROME_TOGGLE ;;
       *) echo OTHER_PROCESS; echo "$CMD" ;;
     esac
   fi
   ```
   - `DEDICATED_UP` → the dedicated Chrome is already running; skip to sub-step 3.
   - `PORT_FREE` → launch it (sub-step 2).
   - `DEFAULT_CHROME_TOGGLE` → the user's everyday Chrome holds the port because remote
     debugging is on at `chrome://inspect/#remote-debugging` (typically left over from
     trying default mode). **Don't connect** — the MCP would drive the wrong browser. Ask
     them to turn that toggle off (or switch to default mode instead), re-run the check,
     then continue.
   - `OTHER_DEBUG_CHROME` / `OTHER_PROCESS` → something else owns the port; show the user the
     printed command and ask them to quit it, then re-run the check.
2. If the port is free, launch Chrome **by invoking the binary directly** (never
   `open -a "Google Chrome"`, which hands off to an existing Chrome and silently drops
   the flags). This is a separate process on a separate profile, so the user's normal
   Chrome does not need to be closed:
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --user-data-dir="$HOME/.chrome-acoustic-profile" \
     --remote-debugging-port=9222 \
     > /tmp/chrome-acoustic.log 2>&1 &
   disown
   ```
   Re-run the check above and confirm `DEDICATED_UP`.
3. Call the `list_pages` MCP tool (or `navigate_page` to `about:blank`). If it returns the
   browser's pages, the MCP ↔ profile link works.
   - If it fails, the most common cause is Chrome not running on 9222 or another Chrome
     owning the port — check `/tmp/chrome-acoustic.log` and re-run the ownership check,
     relaunch if needed, and retry once.

### Default

Do **not** launch Chrome with any flags in this mode — it would start a second, blank
instance instead of attaching to the user's own.

1. Make sure the user's Chrome is open.
2. Call `list_pages`. If it returns their open tabs, the MCP is attached.
   - When the MCP attaches, Chrome shows a prompt asking to allow the debugging connection.
     Tell the user to expect it and accept it. `list_pages` waits until they do.
   - If it fails: confirm Chrome is running, that remote debugging is still enabled at
     `chrome://inspect/#remote-debugging`, and that the MCP was reconnected after
     `chromeMode` changed. Retry once.

Mark `mcp: "done"` once `list_pages` succeeds, else `"skipped"`.

## Step 3 — Make Chrome launches use this profile (per-machine)

**Default mode:** not applicable — the user opens their own Chrome as usual. Mark
`launchAlias: "skipped"` without asking and move on.

**Dedicated mode:** ensure that whenever Chrome is opened for this work — by the user or
by the plugin — it's the dedicated profile on port 9222, not their everyday browser.

- The plugin itself always launches via the command in Step 2, so plugin-driven
  testing is already covered — confirm this to the user.
- For the user's own convenience, offer to add a shell alias so they can start it in
  one word. Check first:
  ```bash
  grep -q "chrome-acoustic-profile" "$HOME/.zshrc" 2>/dev/null && echo HAVE_ALIAS || echo NO_ALIAS
  ```
  If `NO_ALIAS` and the user wants it, append (ask before editing their `~/.zshrc`):
  ```bash
  cat >> "$HOME/.zshrc" <<'ALIAS'

  # sdk-config-coding: launch the dedicated Chrome profile with remote debugging
  alias chrome-acoustic='/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --user-data-dir="$HOME/.chrome-acoustic-profile" --remote-debugging-port=9222 > /tmp/chrome-acoustic.log 2>&1 & disown'
  ALIAS
  ```
  Tell them to `source ~/.zshrc` or open a new terminal, then `chrome-acoustic` starts it.

Mark `launchAlias: "done"` if added or already present (`HAVE_ALIAS`), `"skipped"` if
they declined.

## Step 4 — Install & configure Tampermonkey (per-machine)

Tampermonkey injects each site's `acoconnect-loader.js`. It can't be detected via CDP, but
its install folder can be checked on disk (extension ID `dhdgffkkebhmkfjojejmpbldmpobfkfo`)
in the profile chosen in Step 1:

```bash
# Dedicated
find "$HOME/.chrome-acoustic-profile" -maxdepth 3 -type d -path '*/Extensions/dhdgffkkebhmkfjojejmpbldmpobfkfo' 2>/dev/null
# Default
find "$HOME/Library/Application Support/Google/Chrome" -maxdepth 3 -type d -path '*/Extensions/dhdgffkkebhmkfjojejmpbldmpobfkfo' 2>/dev/null
```

A printed path means it's installed. The folder above `Extensions` is the Chrome profile folder
(`Default`, `Profile 1`, …); no output means not found. In default mode, a match
under a folder other than `Default` may be a different Chrome profile from the one the user
browses in — mention which folder matched and confirm with them.

- **Found** → tell the user Tampermonkey is already installed in this profile. The
  **"Allow access to file URLs"** toggle can't be checked from disk, so ask whether it's on;
  if not, have them enable it (sub-step 3 below). Then mark `tampermonkey: "done"`.
- **Not found** → with Chrome running on the chosen profile (Step 2), guide the install:
  1. `navigate_page` the MCP to the Web Store listing:
     `https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo`
  2. Ask the user to click **Add to Chrome** and confirm the install (this is a manual
     click in the browser — it can't be automated).
  3. Have them open `chrome://extensions` → Tampermonkey → **Details** and enable
     **"Allow access to file URLs"** (required so Tampermonkey can load local
     `acoconnect-loader.js` files via `file://` `@require`).
  4. Confirm with the user that it's installed and the toggle is on.

In default mode, reassure the user that the per-site userscripts only `@match` the
customer hostnames they work on, so the rest of their browsing is unaffected.

Mark `tampermonkey: "done"` when confirmed, else `"skipped"`.

Note: the per-site Tampermonkey **userscript** (filled from
`${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/tools/tampermonkey-template.js`) is generated per site by the
skill's "Session start" steps, not here — this step only covers installing the extension.

## Step 5 — ESLint (per-project, optional)

ESLint is a personal code-style preference, off by default, and **per-project** — so it
is not tracked in the per-machine marker. Only offer it if the user wants linting.

Check the current project:
```bash
[ -f eslint.config.mjs ] && echo HAVE_ESLINT || echo NO_ESLINT
```

- `HAVE_ESLINT` → already set up here; nothing to do.
- `NO_ESLINT` and the user wants it → follow "Linting (optional)" in the skill.

Do not record ESLint in the marker — it's re-checked per project by file presence.

## Final step — Write the marker

Write the per-machine marker so finished/skipped steps aren't re-asked and the
`sdk-config-coding` setup check stops offering the walkthrough. Include only the
per-machine steps (not ESLint). Set each step to `"done"` or `"skipped"`, and
`chromeMode` to the mode chosen in Step 1:

```bash
STATE_FILE="$HOME/.claude/sdk-config-coding/setup-state.json"
mkdir -p "$(dirname "$STATE_FILE")"
cat > "$STATE_FILE" <<EOF
{
  "version": 2,
  "chromeMode": "dedicated",
  "chromeProfile": "done",
  "mcp": "done",
  "launchAlias": "skipped",
  "tampermonkey": "done",
  "completedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

Substitute the real values based on what happened. **Always write this file, even when
the user skips everything** — an all-`"skipped"` marker is what stops the setup offer
from reappearing. If they skipped Step 1 too, write `"chromeMode": "dedicated"` (the
default the MCP launcher assumes anyway). Then confirm to the user which Chrome mode is
set, what was set up and what was skipped, and that they can re-run
`/sdk-config-assistant:sdk-config-coding setup` any time to change it — including
switching Chrome mode.

If setup was entered from Step 0 for site work, return to "Working on a site" in the skill.
If it was entered through setup mode, stop here.
