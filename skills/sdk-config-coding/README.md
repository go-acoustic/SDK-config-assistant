# SDK Config Coding

A Claude Code skill that helps you build and test Acoustic Connect behavioral signals for a customer's web SDK, using Chrome DevTools to inspect and verify signals against a live site. It ships in the `sdk-config-assistant` plugin and includes its own one-time setup walkthrough.

## Prerequisites

- Claude Code (CLI, or the VS Code / JetBrains extension). The skill doesn't run in Claude Cowork or the Claude app. In Cowork, use [SDK-config-assistant](../SDK-config-assistant) instead.
- A configured SDK loader (`acoconnect-loader.js`) for your site, with the correct `appKey`, endpoint URL, and `initLogSignal` function present. The skill assumes you will be building the signal code within this framework.
- Google Chrome (macOS).

## Install

Install the **sdk-config-assistant** plugin. See the [README](../../README.md) for the steps. The skill needs nothing else installed.

The Chrome DevTools MCP isn't bundled with the plugin, so it doesn't start for other users of the plugin. Setup registers it for you as a user-level Claude Code MCP server named `sdk-chrome-devtools`.

## Set up a project

Signal work happens in your own project directory (wherever your customer's `sites/` folder should live), not inside the plugin. Pick or create a directory for that work, then:

```zsh
cd ~/dev/my-signal-work
claude
```

No setup is required before working on a site — Claude reads your `sites/<hostname>/acoconnect-loader.js` directly and starts implementing signals.

**Guided first-run setup.** The first time you work on a site on a machine, Claude offers a one-time walkthrough of the browser tooling below:
- choosing a dedicated Chrome profile or your default one
- registering the Chrome DevTools MCP and checking it connects
- making Chrome launches use that profile
- installing and configuring Tampermonkey
- ESLint (optional)

It detects anything already done and lets you **skip** it, and remembers your choices in `~/.claude/sdk-config-coding/`, so it only asks once. You can run it any time with `/sdk-config-assistant:sdk-config-coding setup`, or follow the manual steps below instead.

**Optional: linting.** If you'd like ESLint checking of your `acoconnect-loader.js` files, just ask Claude to set it up — it will copy over a `package.json` and `eslint.config.mjs` and walk you through running `npm install`. This is entirely optional and off by default; the skill doesn't require or assume any particular code style.

### Choose a Chrome profile (one-time, per machine)

The skill can use either a **dedicated Chrome profile** (recommended) or **your default Chrome profile**. Setup asks which you want and records it; re-run `/sdk-config-assistant:sdk-config-coding setup` any time to switch.

| | Dedicated profile | Default profile |
|---|---|---|
| Browser | A separate Chrome window | Your everyday Chrome |
| Isolation | Tampermonkey, client-site logins and DevTools settings kept apart from your personal browsing | The Chrome DevTools MCP can see your everyday tabs and logins; Tampermonkey is installed in your personal profile |
| Starting Chrome | Claude launches it for you (or use the alias) | Open Chrome as normal |
| Requirement | Any Chrome | Chrome 144 or later |

### Option A: dedicated Chrome profile

A dedicated Chrome profile keeps your Tampermonkey scripts and remote-debugging configuration isolated from your everyday browsing session. If you already created `~/.chrome-acoustic-profile` with an earlier version, setup detects and reuses it.

Create the profile directory:

```zsh
mkdir -p ~/.chrome-acoustic-profile
```

Then launch Chrome using that profile with remote debugging enabled on port 9222:

```zsh
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir="$HOME/.chrome-acoustic-profile" \
  --remote-debugging-port=9222
```

> **Note:** Only one Chrome instance can own port 9222. Your regular Chrome can stay open — it's a separate process on a separate profile — but quit any other Chrome you started with `--remote-debugging-port=9222`, and make sure remote debugging is **off** at `chrome://inspect/#remote-debugging` in your regular Chrome (turning it on for Option B makes your regular Chrome listen on 9222 too). Setup and the skill check which Chrome owns the port and warn you if it's the wrong one.

You can save this as a shell alias or a small script so you don't have to type it each time, or you can ask Claude Code to open Chrome for you and it will use this command.

#### Customise the Chrome profile (optional but recommended)

Because this profile will be open alongside your regular Chrome, it helps to make it visually distinct:

- **Change the theme** — open Chrome settings (`chrome://settings`) → Appearance → Themes, and pick something different from your default profile.
- **Add other extensions** as needed (e.g. the Analytics Debugger, and an extension to disable CSP headers).
- **Save passwords** — the profile maintains its own password store, so you can save credentials for client sites without mixing them into your personal keychain.
- **Tweak DevTools** — the profile will remember your chosen DevTools appearance, tabs, and settings.

This profile is persistent. Once set up, you only need to launch Chrome with the `--remote-debugging-port=9222` flag at the start of each working session.

### Option B: default Chrome profile

Uses your everyday Chrome, with no second window. Requires Chrome 144 or later (check with `chrome://version`). Chrome no longer allows `--remote-debugging-port` on the default profile, so the MCP attaches to your running Chrome instead (`chrome-devtools-mcp --autoConnect`):

1. In your normal Chrome, open `chrome://inspect/#remote-debugging` and enable remote debugging. This persists.
2. Keep Chrome open while working. When Claude connects, Chrome asks whether to allow the debugging connection — accept it.

After choosing or switching mode, reconnect the MCP (`/mcp` → `sdk-chrome-devtools` → reconnect) or start a new session — even if `/mcp` already shows it as connected, it's still using the previous mode until reconnected.

Switching back to Option A later is safe — an existing `~/.chrome-acoustic-profile` is never deleted. When you do, turn remote debugging back **off** at `chrome://inspect/#remote-debugging`, otherwise your regular Chrome keeps port 9222 and the dedicated profile can't use it.

### Install Tampermonkey in the chosen profile

With Chrome running on the profile you chose (setup detects an existing install and skips this):

1. Open the [Tampermonkey page on the Chrome Web Store](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo) and click **Add to Chrome**.
2. After installation, go to `chrome://extensions` → Tampermonkey → **Details**.
3. Enable **"Allow access to file URLs"** — this is required so Tampermonkey can load your local `acoconnect-loader.js` files directly from disk.

The per-site userscripts only match the customer hostnames you work on, so with Option B the rest of your browsing is unaffected.

### Add your site

Copy your configured `acoconnect-loader.js` into `sites/<hostname>/`:

```zsh
mkdir -p sites/<hostname>
cp /path/to/your/acoconnect-loader.js sites/<hostname>/
```

Use a new or recent SDK that uses the `initLogSignal` function to implement signals. You can also ask Claude Code to set up the directories for you rather than doing it from the terminal.

Then tell Claude which site to work on. It will read the loader, show you an implementation status summary for each signal, generate a Tampermonkey script for you to paste into the browser, and walk through signal implementation once injection is confirmed.

### Continuing from sdk-config-assistant

The `SDK-config-assistant` skill (Claude Cowork, same plugin) generates an SDK config by inspecting the site. It tests each signal up to three times and escalates any that still fail. At the end of its session it shows a **Use coding assistant** button next to Close session. If you choose it and confirm, it copies the SDK into `SDK-config-coding/sites/<hostname>/` inside the folder you added to Cowork. It renames the SDK to `acoconnect-loader.js` and puts its report, its signal config and `original-sdk.js` (the loader exactly as handed off) under `handoff/`. Signals it could not build at all (for example a sign-in on another host) are listed in the signal config's `blockers[]` and handed over too.

To continue, open a terminal in that `SDK-config-coding/` folder, run `claude`, and say "let's work on <hostname>". The first time, Claude reads the handoff files and writes `notes.md` with the status of each signal, what was already tried for the escalated ones, and the open questions. It then lists the escalated signals first.

- **One-way for code.** Once you've changed the SDK here, it can't go back into `sdk-config-assistant`. You can re-run that skill on the same site later, but that produces a new SDK. If you hand off again, it asks before replacing the folder and keeps the old one as a backup.
- **Test mode.** Handed-off SDKs arrive in test mode (`fakeSignals: true`), even if sdk-config-assistant had already switched its own copy to production. When you're done, ask Claude to prepare the SDK for production. It sets the logging flags, re-verifies the SDK, and gives a readiness label.
- **What goes back.** At the end of preparing for production, Claude asks whether to save a summary of what was fixed. If you agree, it writes `sites/<hostname>/coding-result.json` (signal names, change types, trigger attributes and one-sentence reasons, never code) and uploads it to Acoustic's operator content org, the same place sdk-config-assistant sends its session backups, so sdk-config-analysis can learn from it. The upload needs you to be signed in to app.goacoustic.com in the Chrome profile this skill uses; if it fails, the file is still saved locally. sdk-config-assistant also shows the result the next time you load that site's profile.

---

## Best Practices

- Help Claude by providing exact URLs to test against (product page, cart, checkout, etc). You will save time and tokens by providing as much context as possible. Use **Esc** to break Claude out of a loop if you can see it is stuck.

- Sonnet is usually sufficient. Switch to Opus as required.

- Follow Claude's lead and develop each signal in turn. Review the code it produces for each signal before moving on. If it isn't clear from the output, tell Claude explicitly to test and validate the new code.

- Test manually! Claude can read the console and verify that a signal fires with the expected payload, but you should also walk through the user journey yourself to confirm behaviour end-to-end.
