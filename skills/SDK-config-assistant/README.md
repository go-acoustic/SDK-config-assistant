# SDK Config Assistant — Quick Start Guide

> **⚠️ IMPORTANT**
>
> This skill does a best effort to create an SDK config that will work correctly on your website. It uses AI to do so and thus, can make mistakes. The results should be checked and tested before applying to your production website. The performance and stability of your website can be affected if you do not do this. If in doubt, reach out to Acoustic support for help and guidance.

## What is it?

A Cowork skill that inspects a live customer website and generates a review-ready Acoustic Connect/Tealeaf SDK JavaScript configuration (`initLogSignal` setup), plus a customer mapping file and test plan. Used for new customer SDK onboarding or auditing/updating an existing signal config.

## How to start

**Add the marketplace:**
1. Open Claude Desktop and go to Cowork
2. Click **Customize**
3. Click **Plugins > Add > Add marketplace**
4. Enter as a URL: `go-acoustic/SDK-config-assistant`

**Install the plugin:**
1. Still under **Customize** in Cowork
2. Click **Plugins > Search**
3. Enter the plugin name **sdk-config-assistant**
4. Install it
5. Restart Claude Desktop to activate

Then, in a Cowork conversation, start the skill by typing `/sdk-config-assistant`

Menu names occasionally change — if these steps look out of date, follow Anthropic's own guide instead: [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) (Claude Help Center). This skill only runs in the Cowork tab, not Claude Code or the Desktop Chat tab — it needs the Claude in Chrome extension for live site inspection.

## Need help?

If you get stuck or a signal won't validate, log in to the Acoustic Support Portal and submit a case — attach the `<slug>.json` and `<slug>.analytics.json` files the skill saves locally at session close.

## Setup

- **Cowork only.** The skill only works in Claude Cowork — it relies on the Claude in Chrome browser tool, which isn't available on other Claude surfaces.
- **Install the Chrome extension for Claude** from the Chrome Web Store, make sure it's enabled and signed in to your Anthropic account, and connect it to the tab you want inspected. Other browsers aren't supported.
- **Tampermonkey** (Chrome extension) is recommended but not required — it's the easiest way to inject and test the generated SDK. A no-extension alternative (Chrome DevTools Overrides) is also documented in the test guide the skill produces.
- **A folder must be added before the skill will start** — it's where website profiles are saved so they persist between sessions. Without one, the skill blocks at the storage step. Two ways to provide it:
  - **Recommended — a Project.** Create a Project (for example `SDK config`), add a folder to the Project's context, and run the skill from sessions inside it. Every session in the Project sees the same profiles, so you set this up once.
  - **This session only.** Add a folder to the current session context; the next session will ask again.

## Getting ready

At minimum, have the production URL of the site you're configuring.

If you have a staging domain, note it too — the skill uses it to safely trigger the `order` signal (test checkout) and can generate a dummy test account for you if needed. Staging isn't required; without it the skill inspects production only.

**Heads-up:** during inspection the skill adds a real item to the live production cart to capture the add-to-cart signal. This happens automatically, by design — it doesn't ask permission first.

## Using it

- Type `/sdk-config-assistant` in Claude Cowork to start.
- The flow is entirely click-driven — questions come as buttons, menus, and generated widgets. Don't type free-text answers, extra context, or try to redirect the process; the skill is built to ignore/reject open chat input mid-flow and this can derail the steps.
- The step sequence itself is fixed and won't skip or reorder, but the exact generated code varies run to run based on what the browser inspection finds on the live site each time.

## What it actually does, step by step

1. Collects customer name, production domain, and subscription tier (Pro / Premium / Ultimate). The tier is recorded on the profile but does not change how the skill runs.
2. Explores the site (page structure, dataLayer, category classification).
3. Generates code for every signal the site supports. A signal is skipped only when the site has no matching functionality — no search box, no cart, no product pages, no media — and the reason is recorded in the profile.
4. Has you inject the SDK via Tampermonkey (or DevTools Override) and validate each signal fires with correct data.
5. For any signal with an issue, applies a correction and has you retest — up to two correction attempts per signal (three test passes total).
6. Any signal still failing after that is escalated: greyed out, excluded from the final config, and flagged for Acoustic Services follow-up.
7. Outputs the final files, then offers a deployment choice on every tier — hand the config files over for the customer to host themselves (recommended), or upload to the Media Gallery (Connect CMS) for CDN delivery.

## Output

- `acoConnectSdkConfig-<domain>.js` — the configured SDK
- `acoConnectSdkConfig-<domain>.tamperMonkeyConfig.js` — Tampermonkey loader
- `<customer>-customer-signal-config.json` — reusable signal mapping, for future updates
- `<customer>-implementation-review.md` — field-by-field audit, confidence scores, open questions
- `How to test and validate the data.md` — step-by-step test walkthrough

## Resuming a session

If you close and come back, start the skill again and select **Modifying existing** — it loads your saved website profile and picks up where you left off.

## If widgets don't render ("Unable to reach visualize")

The skill uses an inline widget renderer for interactive forms and validation matrices. If that renderer is unavailable in your Cowork session, the skill falls back automatically — you always click, never type:

- **Info/status messages** (signal summary, inspection complete, session complete) — shown as plain text in chat; the flow continues without interruption.
- **Option/choice widgets** (login gates, deployment choice, reason collectors, feedback) — replaced with a standard multiple-choice question; click to select, same options.
- **The storage step** — the full explanation is shown as text, with options to re-check after adding a folder, hear it again, or stop.
- **Signal validation matrix** — the skill asks about each signal one at a time as a multiple-choice question (Passed / Issue found / Not tested / Blocked).
- **Intake forms** (customer domain, credentials) — these cannot fall back safely. The skill will stop and ask you to restart the Claude desktop app.

To restore inline widgets and avoid the per-signal one-at-a-time mode: quit and relaunch the Claude desktop app, then reopen the conversation.

## Signal scope

All signals are available on every subscription tier — Pro, Premium, and Ultimate get the same set:

| Signal | Every tier |
|---|:---:|
| identification, accountRegistered | ✅ |
| addToCart, order | ✅ |
| pageView, productView, onSiteSearch, productConfiguration | ✅ |
| richMediaInteraction | ⚠️ Skeleton only — needs a site-specific manual enhance |

Which of these get configured depends on the site, not the tier: a signal is skipped only when the site has no matching functionality (no search box, no cart, no product pages, no media).
