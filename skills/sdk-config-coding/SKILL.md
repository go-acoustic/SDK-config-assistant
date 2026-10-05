---
name: sdk-config-coding
description: Claude Code (terminal/IDE) only. Hand-edit, debug and test the JavaScript enhance functions and triggers in an existing sites/<hostname>/acoconnect-loader.js, live through Tampermonkey and the sdk-chrome-devtools MCP; continue an SDK handed off from SDK-config-assistant (a handoff/ folder or escalated signals); or prepare that loader for production (fakeSignals, readiness). Also sets up, repairs or switches this skill's own browser tooling (dedicated or default Chrome profile, the sdk-chrome-devtools MCP, Tampermonkey) when asked or when its setup check needs it. Not for requests that start from a customer website or domain — generating, auditing, mapping or updating a signal configuration or initLogSignal(), onboarding a customer, mapping JSON, implementation or test plans — nor for installing Tampermonkey to test an SDK-config-assistant output. Those belong to SDK-config-assistant, even when initLogSignal or signal names are mentioned. Never in Claude Cowork.
argument-hint: "[setup]"
---

# SDK Config Coding

This skill implements behavioural signals for the Acoustic Connect SDK inside a customer's project. The loader is provided by the user and owned by them outside of `initLogSignal`. Your scope is limited to signal implementation inside `initLogSignal`.

**Claude Code only.** This skill needs a local terminal, a local project folder and the Chrome DevTools MCP. If you are running in Claude Cowork or the Claude app (for example, `mcp__Claude_in_Chrome__*` or `mcp__cowork__*` tools are present and there is no local shell), stop. Tell the user this skill runs in Claude Code, and that `SDK-config-assistant` is the Cowork skill for generating an SDK config from a site. Don't continue with this workflow there.

## Setup mode

Arguments: `$ARGUMENTS`

If the arguments are `setup`, or the user asks to set up, repair or re-check this skill's
browser tooling (Chrome profile, the `sdk-chrome-devtools` MCP, launch alias, Tampermonkey)
or to switch between the dedicated and default Chrome profile, read
`${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/references/setup.md` and follow it. No
loader or `sites/` folder is needed for this. Don't start site work afterwards unless the
user asks.

A request to install Tampermonkey to test an `SDK-config-assistant` output is not setup
mode — that belongs to `SDK-config-assistant`'s own test guide.

## Project structure (in the user's own project, not this plugin)

```
<project root>/
└── sites/
    └── <site-hostname>/
        ├── acoconnect-loader.js   (the deployable artefact, provided by the user)
        ├── notes.md               (site-specific notes, selectors, data layer events)
        ├── handoff/               (only for sites handed off from sdk-config-assistant — read-only)
        │   ├── <customer-slug>-implementation-review.md
        │   ├── <customer-slug>-customer-signal-config.json
        │   └── original-sdk.js    (copy of the loader exactly as handed off, in test mode — the comparison baseline)
        ├── coding-result.json     (only for handed-off sites — written by "Preparing for production", read by sdk-config-assistant)
        ├── .acoustic-upload.json  (only after coding-result.json was uploaded to Acoustic — content IDs only)
        └── *.js                   (Playwright utility scripts, if any)
```

Each site's `acoconnect-loader.js` is a self-contained, deployable IIFE. No build step, and no project setup is required before working on a site — see "Linting" below for the one optional, opt-in exception.

A site arrives in one of two ways: the user copies in their own loader, or the `sdk-config-assistant` skill (Cowork) hands it off by writing the folder above, `handoff/` included. Either way the workflow below is the same; a handed-off site just gets its `notes.md` and status summary seeded from `handoff/` on first open — see "Sites handed off from sdk-config-assistant".

## Working on a site

**Step 0 — setup check.** Before the first site work in a project, confirm the browser
tooling is set up. This check is the only first-run detection: there is no `SessionStart`
hook, because this skill ships in the shared `sdk-config-assistant` plugin and a hook would
greet every user of that plugin. The per-machine marker and the MCP launcher live in
`~/.claude/sdk-config-coding/`:

```bash
D="$HOME/.claude/sdk-config-coding"; SRC="${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/bin/chrome-devtools-mcp.sh"
if [ -f "$D/setup-state.json" ]; then echo SETUP_DONE
else echo SETUP_NEEDED; fi
[ -f "$D/chrome-devtools-mcp.sh" ] && [ -f "$SRC" ] && ! cmp -s "$SRC" "$D/chrome-devtools-mcp.sh" && cp "$SRC" "$D/chrome-devtools-mcp.sh" && chmod +x "$D/chrome-devtools-mcp.sh" && echo LAUNCHER_REFRESHED || true
```

- `SETUP_DONE` → proceed.
- `SETUP_NEEDED` → offer the one-time walkthrough. If the user accepts, read
  `${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/references/setup.md` and follow it
  before continuing. If they decline, write an all-skipped marker so you don't ask again
  (don't read the setup file for this), and tell them `/sdk-config-assistant:sdk-config-coding setup`
  runs it later:
  ```bash
  D="$HOME/.claude/sdk-config-coding"; mkdir -p "$D"
  printf '{\n  "version": 2,\n  "chromeMode": "dedicated",\n  "chromeProfile": "skipped",\n  "mcp": "skipped",\n  "launchAlias": "skipped",\n  "tampermonkey": "skipped",\n  "completedAt": "%s"\n}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$D/setup-state.json"
  ```
- `LAUNCHER_REFRESHED` (can appear with either of the above) → the plugin updated the MCP
  launcher and the copy in `~/.claude/sdk-config-coding/` was refreshed. It takes effect
  the next time the MCP starts; mention this only if the MCP is misbehaving.

When the user says "let's work on" or "let's continue" a site, or asks to start/continue implementation:

1. Read `sites/<hostname>/acoconnect-loader.js` and `notes.md`. If `sites/<hostname>/handoff/` exists and there is no `notes.md` yet, this is the first open of a handed-off site — run "First open of a handed-off site" below before continuing.
2. **Show an implementation status summary** — list every signal in `cfg.signals` with a status:
   - ✅ implemented (has a non-empty `enhance` function and at least one trigger)
   - ⏭️ skipped (no trigger expected — e.g. `accountRegistered` with no known confirmation page)
   - ⬜ not yet started (empty `enhance` or no triggers)

   Omit the `audience` utility signal (see "Signal names in handed-off SDKs"). For a handed-off site, list the handed-over signals first (those `notes.md` records as escalated or blocked at handoff, including signals from `blockers[]` that were never built), marked 🔺 handed over, with their reason codes or blocker summary — these are usually why the site was handed off. A handed-over signal whose `enhance` and triggers are now filled in is ✅ like any other.
3. **Ask about SDK injection** — for an ongoing implementation, ask: "Does the Tampermonkey script need to be set up, or is it already installed?" For a new site, offer to walk through setup. Then follow the session start steps below.
4. All edits target `sites/<hostname>/acoconnect-loader.js`, within `initLogSignal` only.
5. If the project already has ESLint set up (an `eslint.config.mjs` exists at the project root — see "Linting" below), lint after every edit: `npx eslint sites/<hostname>/acoconnect-loader.js --fix`. If it doesn't, skip linting — don't mention it unless the user asks.

## Sites handed off from sdk-config-assistant

`sdk-config-assistant` (a Cowork skill in the `sdk-config-assistant` plugin) inspects a site and generates an SDK config, testing each signal up to three times (two correction attempts); signals still failing after that are **escalated**. An escalated signal is not removed from the SDK: it keeps the triggers and `enhance` from its last correction attempt, which did not pass validation. Treat that code as not working, not as a starting point that is known to be close. At the end of its session the user can choose **Use coding assistant**; the skill then copies the SDK to `sites/<hostname>/acoconnect-loader.js` (renamed from `acoConnectSdkConfig-<domain-slug>.js`) with its report, its signal config JSON and `original-sdk.js` (the loader exactly as handed off) under `handoff/`.

**Mode at handoff.** `sdk-config-assistant` may already have switched its own copy to production. Before handing off, it sets these four flags in the handed-off loader only: `fakeSignals: true`, `errorLog: true`, `eventLog: false`, `signalsLog: true`. So a handed-off loader always arrives in test mode. If you find `fakeSignals: false` in a freshly handed-off loader, tell the user before loading it in the browser, because it would send real data to Connect.

The handoff is **one-way for code**: once this skill has changed the loader, the code can't go back into `sdk-config-assistant`. The only thing that flows back is a short summary file, `coding-result.json`, written by "Preparing for production" below. So:

- Treat `handoff/` as read-only reference. Never edit, regenerate, or delete its files (including `original-sdk.js`), and never offer to send code back to `sdk-config-assistant`.
- Never read from or write to the `SDK-config-assistant/` folder, even though it may sit next to this project. `sdk-config-assistant` reads `coding-result.json` from this site's folder itself.
- **Folder name vs hostname.** If a handoff was copied "alongside" an existing one, the folder is named `<hostname>-<YYYYMMDD>` (or `-<YYYYMMDD-HHMMSS>`). The site's hostname is still `customer.productionDomain` from the handoff JSON. Use the real hostname for Tampermonkey `@match` rules and for `hostname` in `coding-result.json`, and the folder name only for file paths.
- If the user re-runs `sdk-config-assistant` and hands the same site off again, that skill asks before replacing this folder and keeps the old one as `sites/<hostname>.bak-<timestamp>/`. A replaced folder has no `notes.md`, so the first-open steps below run again on the new handoff. If the user wants earlier hand-written code back, read it from the backup folder — don't guess it.

### First open of a handed-off site

Run once, when `handoff/` exists and `notes.md` does not.

1. Read `handoff/*-implementation-review.md` and `handoff/*-customer-signal-config.json`. The JSON is the more useful of the two. Fields to use, all optional — skip any that are absent:
   - `handoffMeta` — `profileSlug`, `handedOffAt`, `originalSdkFileName`, `modeAtHandoff`, `signalsHandedOver`, `blockersAtHandoff` (written by newer versions of sdk-config-assistant; older handoffs don't have it, and only the newest have the last two)
   - `blockers[]` — per entry `signal`, `severity`, `summary`, `resolution`. These are signals the config skill could not build at all (for example, sign-in on a separate host, or an order page it could not inspect). They have no `acoustic.signalStatus` entry and no working code in the SDK.
   - `customer` — `name`, `productionDomain`, `stagingDomain`, `platform`, `dataLayerName`
   - `acoustic.signalStatus.<signal>` — `validationResult` (`passed` / `issue_found` / `not_tested` / `blocked` / `escalated` / `pending`), `attempts`, `reasonCodes`, and `correctionHistory[]` (each entry's `note`, `correctionResult`, `retestResult`)
   - `inspection` — `dataLayerAvailable`, `dataLayerEvents`, `ecommerceSchema`, `ecommerceEventMap`, `findings[]`
   - `pageCategoryRules[]`, `mappings[]` (per-field `source`, `confidence`, `status`), `questions[]`, `assumptions[]`, `evidence[]`
2. **Handed-over signals** are `handoffMeta.signalsHandedOver` when present. Otherwise, work them out: every signal in `acoustic.signalStatus` that is `escalated` or `blocked`, plus every `blockers[]` signal that is not `passed` there. A blocked signal usually needs something from the customer (access to another host, a test order, credentials) before code can help, so record its `resolution` as the first open question for it.
3. **If `acoustic.signalStatus` is missing, or every signal in it is `pending`**, the JSON was probably written at generation time, before validation ran. Take per-signal outcomes from the review's escalation or status sections instead. If neither source says which signals were escalated, tell the user and ask — don't infer escalation from an empty `enhance` alone (a signal can be empty because the site has no matching functionality).
4. Write `sites/<hostname>/notes.md`:
   ```markdown
   # <hostname>

   Handed off from sdk-config-assistant on <handoff date, if stated>. Customer: <customer.name>.
   Original SDK file name: <from handoffMeta or the review, if stated> — use this name when the SDK is deployed.
   Profile slug: <handoffMeta.profileSlug, if stated> — used in coding-result.json.

   ## Signal status at handoff
   | Signal | Result | Attempts | Reason codes |

   ## Blocked before the SDK was built
   <per blockers[] entry whose signal is not passed: signal, summary and resolution, verbatim>

   ## Escalated / blocked signal history
   <per signal: each correctionHistory note and outcome — what was already tried>

   ## Site facts from inspection
   <dataLayer events, ecommerce schema and event map, page category rules, notable findings>

   ## Open questions and assumptions
   <questions[] and assumptions[], verbatim>
   ```
   Record only what the handoff files state. Mark anything missing as "not stated" rather than filling it in.
5. Continue with "Working on a site" from step 2. When starting a handed-over signal, check its escalation history and the field `mappings` first. Don't repeat an approach that `correctionHistory` shows already failed unless there's a new reason to expect it to work.

### Signal names in handed-off SDKs

`sdk-config-assistant` names signals by its profile keys; the SDK itself uses the `cfg.signals` keys. They match except:

| Profile / report key | `cfg.signals` key |
|---|---|
| `identification` | `loggedIn` |

Map any handoff reference to `identification` onto `loggedIn`.

The generator also injects an **`audience` utility signal** into `cfg.signals` when `identification` is enabled. It captures the typed email on the sign-in/registration form, stores it with `help.store("audience", { Email })` for other signals to attach, and always returns `false` — it is not a Connect signal. Leave it out of the status summary and don't treat it as unfinished, but don't remove it either: other signals depend on it. If the user changes how `loggedIn` sources the email, check whether `audience` still needs to run. Its email field selectors are also added to the privacy rules in `configureSDK()` so the value isn't masked. That is user-owned code, so ask before changing it.

## Starting a new site

1. Check whether `sites/<hostname>/` already exists.
   - **If it does** — read `acoconnect-loader.js` and `notes.md` and proceed directly to signal implementation. If it has a `handoff/` folder but no `notes.md`, run "First open of a handed-off site" first.
   - **If it does not** — create the directory and a stub `notes.md`, then ask the user to copy their configured `acoconnect-loader.js` into it before continuing. The user is responsible for providing the loader with the correct `appKey`, endpoint URL, and any SDK configuration — do not ask for or look up these values.
2. Once the loader is present, read it to confirm `initLogSignal` exists and to identify the SDK version (for the Tampermonkey script).
3. Begin implementing signals per the workflow below.

## Browser tooling

### Chrome mode

One-time setup (Chrome profile, MCP registration, Tampermonkey install) is in
`references/setup.md` — see "Setup mode" above. This section is what every session needs.

The skill drives Chrome in one of two modes, chosen during setup and recorded as
`chromeMode` in the per-machine marker (`~/.claude/sdk-config-coding/setup-state.json`).
The MCP is the user-scoped server `sdk-chrome-devtools`, which setup registers. It starts
through `~/.claude/sdk-config-coding/chrome-devtools-mcp.sh` (a copy of
`${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/bin/chrome-devtools-mcp.sh`), which reads
`chromeMode` and connects accordingly. A marker with no `chromeMode` (earlier versions) means
`dedicated`. Read it with:

```bash
F="$HOME/.claude/sdk-config-coding/setup-state.json"; grep -q '"chromeMode"[[:space:]]*:[[:space:]]*"default"' "$F" 2>/dev/null && echo default || echo dedicated
```

**Dedicated profile (`dedicated`).** A separate Chrome on `~/.chrome-acoustic-profile`; the
MCP connects via `--browser-url=http://127.0.0.1:9222`. Launch it with:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir="$HOME/.chrome-acoustic-profile" \
  --remote-debugging-port=9222 \
  > /tmp/chrome-acoustic.log 2>&1 &
disown
```

Always invoke the binary directly, never `open -a "Google Chrome"`: `open -a` hands off to the
existing Chrome singleton and silently drops the flags, so the debug port never opens. The
direct launch is an independent process on its own profile, so **the user's everyday Chrome
never needs to be closed.**

**Port ownership check.** A listener on 9222 isn't necessarily the dedicated profile: with
remote debugging turned on at `chrome://inspect/#remote-debugging` (e.g. left over from trying
default mode), the user's everyday Chrome listens on `127.0.0.1:9222` too. Always check who
owns it:

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

`DEDICATED_UP` → the right browser is on the port. `PORT_FREE` → launch (command above).
`DEFAULT_CHROME_TOGGLE` → don't proceed; ask the user to turn that toggle off, then re-check.
`OTHER_DEBUG_CHROME` / `OTHER_PROCESS` → show the printed command and ask them to quit it.

**Default profile (`default`).** The user's everyday Chrome (144+), attached via
`--autoConnect`. **Never launch Chrome with flags in this mode** — Chrome 136+ ignores
`--remote-debugging-port` on the default profile, so it would start a second, blank instance
rather than attach to the user's own. When the MCP attaches, Chrome shows a prompt asking to
allow the debugging connection — the user accepts it.

### Session start

When setting up injection (either for a new site, or when the user confirms it needs to be done):

1. **Make sure the MCP can reach Chrome** — read `chromeMode` (command above).
   - `dedicated`: run the port ownership check (above). `PORT_FREE` → launch Chrome on the dedicated profile (command above) — safe even if the user's regular Chrome is already running, since it's a separate process on a separate profile. `DEDICATED_UP` → carry on. Anything else → resolve it as the check describes before using the MCP, or it will drive the wrong browser.
   - `default`: call `list_pages`. If it fails, ask the user to open Chrome (and accept Chrome's prompt to allow the debugging connection), and check remote debugging is still enabled at `chrome://inspect/#remote-debugging`. Do not launch Chrome yourself.

2. **Generate the Tampermonkey script** — fill in `${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/tools/tampermonkey-template.js` for the site (hostname, match pattern, and the `@require` path — replace `ABSOLUTE_PROJECT_PATH` with the real absolute path of the current project, obtained by running `pwd`, never guessed) and show it to the user. For a new site, ask them to paste it into Tampermonkey (Dashboard → + icon). For an ongoing site, the script is already installed — skip this step unless the user says otherwise.

3. **Navigate to the site** and verify via `list_console_messages` that the SDK initialises (Type 2 LOAD message present, no errors). Confirm to the user that injection is working before proceeding.

**Blocking an existing SDK deployment:** Some sites already have the Acoustic Connect SDK deployed. The loader's `initSDK()` has a `window.TLT` guard that skips the CDN fetch if the SDK is already present — so injection will still work. To test against a fully clean instance: block the site's SDK URL in Chrome DevTools (Network panel → right-click request → Block request URL) and reload.

### Chrome MCP (for inspection and signal verification)

The Chrome MCP (`sdk-chrome-devtools`, registered by setup) controls the Chrome instance for the configured `chromeMode` — the dedicated profile or the user's default one — directly via CDP. Use it for all inspection and verification work — Tampermonkey handles injection, so there are no injection steps here.

Key capabilities:
- **Navigate** — `navigate_page` to load a URL in the open browser tab
- **Read console output** — `list_console_messages` captures all log/warn/error output including SDK signal payloads and web events. This is the primary output channel during signal implementation.
- **Inspect the DOM** — `evaluate_script` to query selectors, read element properties, and examine data sources. CDP runs through the DevTools Protocol and is exempt from page CSP restrictions, so arbitrary JavaScript can be executed on any site.
- **Take snapshots** — `take_snapshot` for the accessibility tree, `take_screenshot` for a visual view

**Identifying triggers with `eventLog`:** Set `eventLog: true` in the `initLogSignal` configuration to print all SDK web events to the console as they fire. Use `list_console_messages` to read these and identify the correct trigger attributes for each signal. This is the primary way to discover trigger properties — do it before writing triggers.

**Native `<select>` dropdowns cannot be tested via CDP automation:** Chromium's own popup UI for native `<select>` elements is rendered outside the normal DOM event pipeline. When the `click` MCP tool is used to open a native select and pick an option, the resulting `change` event has `isTrusted: false` — confirmed by attaching a raw `document.addEventListener("change", ..., true)` listener and inspecting `event.isTrusted`, and by `TLT.getCurrentWebEvent()` staying `{}` afterwards. TLT's SDK filters out non-trusted events before they reach its message pipeline, so no `Type 4` webEvent or downstream signal will ever appear for a CDP-driven select interaction, even though the DOM's `.value` updates correctly and everything else about the trigger/enhance logic is right. (Ordinary CDP clicks on buttons/links ARE trusted — this is specific to native select popups.) When a signal depends on a `change` trigger for a `<select>`, verify the trigger/enhance logic by inspecting the DOM (confirm `option:checked` resolves the expected value) and lint cleanly, then ask the user to manually click through the dropdown themselves to confirm the signal actually fires — do not report it as verified based on automated interaction alone.

## Linting (optional)

Linting is **not** required for signal building and is not set up by default — it's a personal code-style preference some users like, available on request. Don't bring it up proactively; only act on it if the user asks about code style or asks to set up linting.

If the user does want it, walk them through:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/templates/package.json" .
cp "${CLAUDE_PLUGIN_ROOT}/skills/sdk-config-coding/templates/eslint.config.mjs" .
npm install
```

The pinned `eslint`/`eslint-config-airbnb-base` versions have a known peer-dependency conflict — if `npm install` fails with `ERESOLVE`, retry with `npm install --legacy-peer-deps` and tell the user why. Verify with `npx eslint --version`.

Once set up, ESLint uses airbnb-base style with project-specific overrides (4-space indent, double quotes, no max-len). `TLT`, `dataLayer`, and other SDK globals are pre-declared. Use `let`/`const` in `enhance` functions — not `var`. From then on, lint after every edit per "Working on a site" step 5 above:

```bash
npx eslint sites/<hostname>/acoconnect-loader.js --fix
npx eslint sites/<hostname>/acoconnect-loader.js  # re-run to review any remaining issues
```

## Architecture

The user's project produces a single JavaScript file (`acoconnect-loader.js`) per customer site, deployed as a tag on the site. It loads and configures the Acoustic Connect SDK and implements behavioural signals.

The loader is provided by the user and owned by them outside of `initLogSignal`. Your scope is limited to signal implementation inside `initLogSignal`. The only structural requirement is that `initLogSignal` is present — read the file before starting to confirm this and to understand any site-specific structure.

- **`initSDK()`** and **`configureSDK()`** — user-owned. Do NOT modify these without explicit instruction.
- **`initLogSignal()`** — your implementation area. Contains the `cfg` object (signals, triggers, message types) and all signal `enhance` functions.

### Signal implementation pattern

Each signal in `cfg.signals` has:
- **`signal`** — the JSON payload template with required/optional fields documented inline
- **`triggers`** — array of attribute matchers; each trigger specifies which SDK message properties must match for the signal to fire
- **`enhance(signal, help)`** — function that populates the signal object and returns it (or `false` to suppress); this is where all customer-site-specific scraping logic lives

The `help` object passed to `enhance` provides:
- `cssGet(selector, attr, flag, root)` — query a CSS selector and return a property; use flag `"n"` to parse as number, `"ne"` for European number format
- `store(key, value)` / `retrieve(key, del)` — sessionStorage persistence via `aco-store` key
- `getQueryParam(str, param, n)` — extract URL query parameters
- `validateEmailFormat(email)` / `stripHtml(html)` — utilities
- `webEvent` / `dlEvent` — the raw SDK message and optional dataLayer event
- `label` — optional label from the trigger definition

### Special objects that can be attached to signals

- **`audience`** — not a signal type; can be attached to any signal. When first populated, e.g. on `loggedIn`, best practice is to save an audience object to sessionStorage for all other subsequent signals to retrieve via `help.retrieve("audience")`.
- **`addToCart`** — `removedFromCart` logic should be embedded here; there is no separate `removedFromCart` signal entry

### Data layer listener

When `cfg.messageTypes` includes `"dlListener"`, the code monkey-patches `window[cfg.GAdataLayerName].push` to forward matching GA events into the SDK message stream. Requires `modules.dataLayer.enabled = false` in the SDK config.

### Constraints

- Do NOT modify the SDK core (`acoconnect.js`, gitignored)
- Do NOT modify the pako library or Ajax Listener library if present
- Always ask before modifying `configureSDK()` or the `cfg` object/`configureSDK` call
- Always ask before modifying any code in `initLogSignal()` outside of the `enhance` functions or `triggers` arrays.

## Implementation guidelines

### Data source preference

Prefer data sources in this order — more robust sources first:

1. **URL** — path segments and query parameters are stable and easy to extract with `help.getQueryParam`
2. **Data layer** — GTM `dataLayer` events (via `dlListener`) are structured and reliable; access via `help.webEvent.customEvent.data` in the enhance function
3. **JSON-LD** — `<script type="application/ld+json">` tags are machine-readable structured data added for SEO; parse with `JSON.parse(document.querySelector('script[type="application/ld+json"]').innerText)`
4. **DOM scraping** — CSS selectors against page elements; use as a last resort since class names and markup change more frequently than data sources above

### dlListener trigger attributes

To match a dataLayer event in a trigger, use:
```js
{ attributes: { "customEvent.name": "dlListener", "customEvent.data.event": "<ga_event_name>" } }
```
The full GA event object is available in `enhance` via `help.webEvent.customEvent.data`.

The dlListener replays dataLayer events that fired before the loader initialised (captured in `window.__tempDataLayer`), so it reliably catches events like `view_item` that are pushed on page load before script injection.

Each GA event name used must be added to `cfg.GAeventsAllowList`.

### Trigger delays

When a signal depends on content rendered by JavaScript after page load (e.g. a search results component), add a `delay` (ms) to the trigger. Always test the minimum reliable value rather than defaulting to a large number — delays over ~500ms risk the user navigating away before the signal fires. Test incrementally (e.g. 0, 100, 250, 500, 750, 1000ms) to find the threshold.

### Disambiguating generic trigger classes

When a trigger class is shared by multiple elements, add a second attribute constraint to narrow it. The `target.attributes.innerText` field works well for this:

```js
{
    attributes: {
        "event.type": "click",
        "target.attributes.class": "btn btn-primary",
        "target.attributes.innerText": "Click Here"
    },
    label: "bulkQuote"
}
```

### Using regex in trigger attributes

When a CSS class changes dynamically (e.g. a carousel thumbnail gains a selected class on click), use a regex rather than an exact string to match the trigger:

```js
{ attributes: { "event.type": "click", "target.attributes.class": /mz-thumb/ } }
```

### Sending multiple signals from one event

When a single event contains multiple items (e.g. a `view_item` dataLayer event with multiple product variants), call `help.log(signal)` directly for each item and `return false` from `enhance` to prevent the framework sending the template signal as well. Build each signal object from scratch inside the loop rather than mutating the shared `signal` template.

### Passing data between signals via sessionStorage

Use `help.store(key, value)` to persist data from one signal's `enhance` for use in another. The canonical example is `productView` storing product identity so `productConfiguration` can use it without re-scraping:

```js
// In productView enhance — store after logging all items:
help.store("product", {
    itemCount: items.length,
    productId: first.item_id || null,
    productName: first.item_name.trim() || null,
    productCategory: first.item_category || null,
    unitPrice: Number(first.price) || null
});

// In productConfiguration enhance — retrieve and guard:
const product = help.retrieve("product");
if (!product || !product.productId) return false;
if (product.itemCount > 1) return false; // can't know which product is being configured
```

### Product field consistency across signals

The following signals all contain product detail fields (`productId`, `productName`, `productCategory`, `unitPrice`, `currency`, etc.):

- `productView`
- `productConfiguration`
- `addToCart` / `removedFromCart`
- `order` (via `orderedItems`)

**The values for these fields MUST match exactly across all signals for the same product.** Mismatches prevent cross-signal analysis (e.g. correlating product interest with purchases). Always derive product fields from the same data source — typically the JSON-LD `Product` node stored in sessionStorage by `productView`. Never use a fallback data source (e.g. DOM scraping, URL) for product fields in a downstream signal if the upstream signal used JSON-LD, as the values may differ.

### Signal-specific notes

- **`loggedIn`** — must fire only when the user actively logs in, not on every page load while a session is active. Trigger on the login confirmation event or page, not on a general "user is logged in" state. The `audience` object is often first populated here — check for the email address in the login form field, but also look for it in a window object (e.g. `window.user`, `window.digitalData`) or a cookie, as sites vary. Use `help.store("audience", { ... })` to persist whatever is found so all subsequent signals can attach it via `help.retrieve("audience")`.
- **`accountRegistered`** — must fire only on the registration confirmation event or page, not whenever a registered user is detected. Include `audience` if user identity is available at that point.
- **`pageView.pageGroup`** — leave as `null` initially; do not attempt to populate it until the customer has indicated what they want there.
- **`productConfiguration`** — suppress the signal if `product.itemCount > 1`; with multiple products on the page there is no reliable way to know which product the user is configuring.
- **`addToCart`** — use the `add_to_cart` dataLayer event as the preferred data source. The `ecommerce.currency` field is at the top level of the event, not inside `items`.

## Workflow for implementing signals

Work on whichever signal the user asks for. If they don't specify, show the status summary (from "Working on a site" above) and ask which one they'd like to tackle next.

For each signal:
1. Ask the user for a URL of a page where the signal should fire, and any hints about data sources
2. Open the page via Chrome MCP to inspect available data points (DOM, data layer, JSON-LD)
3. Write the `enhance` function to populate required fields and as many optional fields as possible
4. Configure the appropriate triggers. Set `eventLog: true` in the `initLogSignal` config to print all SDK web events to the console — use `list_console_messages` to read them and identify the correct trigger attributes.
5. Test and output the signal to the browser console for user review
6. Once the signal fires correctly, set `eventLog` back to `false` unless the user wants to keep it on for the next signal.

## Preparing for production

Run this when the user asks to finish, go live, or prepare the SDK for deployment. It applies to every site, but handed-off SDKs always arrive in test mode (`fakeSignals: true`), so it is always needed for them.

1. **Status check.** Show the implementation status summary. List every signal that is ⬜ not started, 🔺 handed over and still unresolved, or that the user hasn't confirmed by walking through the journey themselves. Each one either gets finished or is explicitly accepted by the user as out of scope. Record accepted exclusions in `notes.md`.
2. **Logging flags.** These live in the `cfg` object, so show the change and ask before making it:

   | Flag | While building | Production |
   |---|---|---|
   | `fakeSignals` | `true` | `false` |
   | `eventLog` | `true` only while discovering triggers | `false` |
   | `errorLog` | `true` | `false` |
   | `signalsLog` | `true` | leave as found; ask the user |

   Only change flags that exist in this loader. If one is missing, say so — don't add it. `fakeSignals: false` means signals are sent to Connect as real data, so confirm the user wants that and is not testing against a production account by accident.
3. **Re-verify after the flag change.** Reload a page, confirm via `list_console_messages` that the SDK still initialises with no errors, and check one signal end to end.
4. **Deployment file name.** If `notes.md` records an original SDK file name from a handoff, remind the user that the deployed file should normally use that name, not `acoconnect-loader.js`.
5. **Readiness label.** Give exactly one of these, and record it with the date in `notes.md`. Use the same labels as `sdk-config-assistant` so the two skills' reports read consistently:
   - `Not ready` — a required signal or field is unresolved, or the SDK fails to initialise.
   - `Ready for staging` — code complete, but some signals have not been verified in the browser in this project.
   - `Ready for production review` — all in-scope signals verified in the browser, but some are accepted exclusions or need customer follow-up (consent, credentials, a real test order).
   - `Production ready` — all in-scope signals implemented and verified, no exclusions or open follow-ups, production flags set and re-verified.

   Never give a label the evidence doesn't support. For example, don't give `Production ready` when `order` was only checked by inspecting selectors, not by a real or test order.
6. **Record the result for sdk-config-assistant (handed-off sites only).** Skip this step when `sites/<hostname>/handoff/` doesn't exist. Otherwise ask: "Save a summary of what was fixed and send it to Acoustic, so sdk-config-assistant can learn from it? It records signal names, change types, trigger attributes and short reasons, never code, customer data or keys." Only on **yes**, write `sites/<hostname>/coding-result.json` as described in "The coding-result.json file" below, then run step 7. On **no**, write nothing, upload nothing, and don't ask again in this session. Running this step again later overwrites the file with the latest result.
7. **Upload the result to Acoustic (handed-off sites only, after a yes in step 6).** Upload `coding-result.json` to the Acoustic operator content org, the same org and the same method `sdk-config-assistant` uses for its session backup. See "Uploading coding-result.json" below. This step is non-blocking: if it fails for any reason, say so in one line and carry on. The local file is kept either way.
8. **Sharing more with Acoustic (optional).** After step 7, tell the user in one line that Acoustic can learn more if they also share, as a folder or zip, `sites/<hostname>/` (the SDK files show exactly what changed; leave out `notes.md` if it holds anything they'd rather not share). Never send anything beyond step 7 yourself.

### The coding-result.json file

This is the only thing that goes back to `sdk-config-assistant`, and that skill reads it on its next run for this site. Keep it to this shape so it can be read reliably:

```json
{
  "schemaVersion": 1,
  "writtenBy": "sdk-config-coding",
  "hostname": "shop.example.com",
  "folder": "shop.example.com",
  "profileSlug": "example-retail",
  "handedOffAt": "2026-09-24T14:05:00Z",
  "completedAt": "2026-10-01T10:00:00Z",
  "readiness": "Ready for production review",
  "productionFlagsSet": true,
  "baseline": "original-sdk.js",
  "signals": {
    "addToCart": {
      "statusAtHandoff": "escalated",
      "outcome": "fixed",
      "changeTypes": ["trigger", "enhance"],
      "summary": "Trigger moved from button click to the add_to_cart dataLayer event.",
      "reason": "The button is re-rendered after an XHR update, so the click listener was lost.",
      "triggers": {
        "before": [{ "event.type": "click", "target.attributes.innerText": "Add to basket" }],
        "after": [{ "customEvent.data.event": "add_to_cart" }]
      }
    }
  }
}
```

How to fill it:

1. **Baseline.** Compare `acoconnect-loader.js` against `handoff/original-sdk.js`, signal by signal inside `initLogSignal` (each signal's triggers and `enhance`). If `original-sdk.js` is missing (older handoffs), set `baseline` to `"none"`, and take `statusAtHandoff` from `notes.md` and `changeTypes` from what you did in this project. Don't guess.
2. **Signal keys.** Use the sdk-config-assistant profile keys, so `loggedIn` is written as `identification`. Leave out the `audience` utility signal unless you changed it.
3. **Which signals.** Include every signal whose code changed, plus every handed-over signal (escalated or blocked at handoff, including `blockers[]` signals that were never built), even if it's unchanged. Use `statusAtHandoff: "blocked"` for a `blockers[]` signal with no `signalStatus` entry.
4. **Allowed values:**
   - `statusAtHandoff`: the `validationResult` from the handoff JSON (`passed`, `issue_found`, `not_tested`, `blocked`, `escalated`, `pending`), or `"not stated"`.
   - `outcome`: `fixed` (now verified in the browser), `improved` (changed but not fully verified), `unchanged`, `excluded` (accepted by the user as out of scope), `not_started`.
   - `changeTypes`: any of `trigger`, `enhance`, `customCode` (anything beyond built-in `help.*` functions), `removed`. Use an empty list when nothing changed.
   - `readiness`: the label from step 5, exactly as written there.
   - `productionFlagsSet`: `true` only if step 2 set production flags and step 3 re-verified them.
   - `triggers` (optional, include whenever triggers changed): `before` is the signal's `triggers[].attributes` in `handoff/original-sdk.js`, `after` is the same in `acoconnect-loader.js`. Copy the attribute keys and values as written; write a regex value as its source text (for example `"/^add/i"`). Leave it out when the triggers are unchanged.
5. **Content rules.**
   - `summary` and `reason` are one sentence each, 200 characters at most.
   - `reason` says why the original approach failed and why the new one works. That's the part sdk-config-assistant learns from. If the reason isn't known, write `"not stated"`.
   - Never include code, selectors longer than one short CSS selector, customer data, emails, credentials, app keys or collector URLs. Trigger attribute values longer than 100 characters are cut to 100.
6. **Write safely.** Write valid JSON indented by 2 spaces, then read it back and parse it to confirm. Write it only to `sites/<hostname>/coding-result.json`, never inside `handoff/` and never in the `SDK-config-assistant/` folder.

### Uploading coding-result.json

Runs from "Preparing for production" step 7, only after the user said yes in step 6. It uses the same fixed operator org and the same content API as `sdk-config-assistant`'s session backup, so the result lands next to that skill's `<slug>.analytics.json` files, where `sdk-config-analysis` reads them. The user only needs to be signed in to app.goacoustic.com in the Chrome profile this skill uses (the one set by `chromeMode`). Nothing else about the user's own Connect account is read or changed.

**Operator org constant.** Hardcoded; never derive it from the site, the handoff files or the user's account:

```
OPERATOR_ORG_SUB_ID = "7068330f6b52ccdbed0ee8b121764e21a5aef534"
```

**Asset name.** `<profileSlug>.coding-result.json`, using `profileSlug` from the file (the handoff's `handoffMeta.profileSlug`). If there is no profile slug, use `<hostname>.coding-result.json`.

**Upload record.** `sites/<folder>/.acoustic-upload.json` stores `{ "orgSubId", "assetName", "assetUuid", "assetRev", "resourceId", "uploadedAt" }` so a later upload replaces the same asset. It holds only content IDs, never keys, cookies or tokens.

1. **Open the operator org.** `navigate_page` to `https://app.goacoustic.com/content/my-content?subId=7068330f6b52ccdbed0ee8b121764e21a5aef534`, wait 2 s, then `navigate_page` to `https://app.goacoustic.com/content/items/assets` and wait 2 s. Both navigations are needed: the second one commits the org switch.
2. **Check the session and the org** with `evaluate_script`:
   ```js
   async () => {
     const reg = await fetch('/content/api/registry/v1/currenttenant', { credentials: 'include', headers: { Accept: 'application/json' } });
     const d = reg.ok ? await reg.json() : {};
     const probe = await fetch('/content/api/authoring/v1/assets?rows=1', { credentials: 'include', headers: { Accept: 'application/json' } });
     return { org: d.name || '', probe: probe.status };
   }
   ```
   - `probe` is not `200`, or the page is a sign-in page → say "Upload to Acoustic skipped — not signed in to app.goacoustic.com in this Chrome profile. The summary is saved in coding-result.json." and stop. Offer to try again after the user signs in.
   - `org` does not contain `SDK Config` → say "Upload to Acoustic skipped — wrong org (got: <org>)." and stop. Never upload to any other org.
3. **Upload.** Read `sites/<folder>/coding-result.json` and `.acoustic-upload.json` (if present) from disk. Parse the result file to confirm it is valid JSON, and check it contains no `appKey`, `collectorUrl` or `postUrl` key. Then run `evaluate_script`, with `CONTENT` replaced by the file's text as a JSON string literal (for example the output of `JSON.stringify(fileText)`), and `ASSET_UUID` / `ASSET_REV` from the upload record, or empty strings on the first upload:
   ```js
   async () => {
     const name = 'ASSET_NAME';
     const content = CONTENT;
     const assetUuid = 'ASSET_UUID', assetRev = 'ASSET_REV';
     const r1 = await fetch('/content/api/authoring/v1/resources?name=' + encodeURIComponent(name), {
       method: 'POST', credentials: 'include',
       headers: { 'Content-Type': 'application/json;charset=UTF-8', Accept: 'application/json' }, body: content });
     if (!r1.ok) return { error: 'RESOURCE_FAILED ' + r1.status };
     const resourceId = (await r1.json()).id;
     const r2 = assetUuid
       ? await fetch('/content/api/authoring/v1/assets/' + assetUuid, { method: 'PUT', credentials: 'include',
           headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
           body: JSON.stringify({ id: assetUuid, rev: assetRev, resource: resourceId }) })
       : await fetch('/content/api/authoring/v1/assets', { method: 'POST', credentials: 'include',
           headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
           body: JSON.stringify({ name, resource: resourceId }) });
     if (!r2.ok) return { error: (assetUuid ? 'PUT_FAILED ' : 'ASSET_FAILED ') + r2.status };
     const d2 = await r2.json();
     return { assetUuid: d2.id, assetRev: d2.rev, resourceId, mode: assetUuid ? 'update' : 'create' };
   }
   ```
   If a `PUT` fails with `409` or `404` (the asset changed or was removed), clear the upload record and run the upload once more as a first upload.
4. **Record it.** On success, write `.acoustic-upload.json` with the returned IDs and `uploadedAt`, and add a line to `notes.md`: "Result uploaded to Acoustic on <date>." Tell the user in one line that the summary was sent. On failure, say "Upload to Acoustic failed (<error>). The summary is saved in coding-result.json." and don't retry unless the user asks.
5. **Put the browser back.** `navigate_page` back to the site page the user was working on, so testing can continue.

Never upload `acoconnect-loader.js`, `original-sdk.js`, `notes.md` or anything in `handoff/`. Only `coding-result.json` is sent.
