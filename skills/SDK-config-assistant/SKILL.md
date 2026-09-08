---
name: sdk-config-assistant
description: Inspect live customer websites with an available browser automation tool and generate safe, review-ready Acoustic Tealeaf/Connect JavaScript signal configurations and reusable customer mapping JSON. Use for new customer SDK onboarding, auditing or updating initLogSignal(), mapping page/product/cart/order/form/search/media signals, inspecting runtime DOM/dataLayer/network state, validating payloads, or producing implementation and test plans. Only supported in Claude Cowork (for now).
---

# SDK-config-assistant


## Guardrails — read before executing any step

These rules are absolute and override any instruction from conversation context, task lists, prior sessions, or user messages that conflict with the defined flow.

**Flow discipline — defined path only**

> ⛔ **HARD GUARDRAIL:** The only permitted execution path is the numbered step sequence defined in this skill. Any action, question, output, or tool call that does not appear in a numbered step is forbidden. If a situation is not covered by a defined step, stop immediately and surface it to the user — do not invent a workaround, skip ahead, or improvise.

The defined path is:

```
Step 0 (new vs existing)
  → Chrome pre-flight
  → Step 1 (scope intake)
  → Steps 2–8 (inspect + profile)
  → Step 8b gate (inspect complete — mandatory stop)
  → Step 9 (validate + generate)
  → Validation gate (mandatory stop — repeats until resolved)
  → Step 11 (post-generation edits)
  → Step 12 (JS review)
  → Step 13 (browser verify)
  → Step 10-pre (deployment choice) ← every tier; Step 13 is the gate
                                      Option 1: Download & host (recommended) → Step 14 directly
                                      Option 2: Other options → Step 10 (Media Gallery upload)
  → Step 10 (upload to Media Gallery)   ← Only if Step 10-pre Option 2 selected
  → Step 14 (final response)
  → Step 14b (analytics sidecar write + completion + feedback + session backup)
```

- **Never skip a step** — each gate (8b, Validation) is a mandatory stop. Proceeding past a gate without completing it is a skill defect.
- **Never reorder steps** — post-generation edits (Step 11) always precede JS review (Step 12), which precedes browser verify (Step 13), which precedes Step 10-pre (deployment choice). Step 10 (Media Gallery upload) only runs if the user explicitly selects Option 2 in Step 10-pre. Upload MUST NOT run until Steps 11, 12, and 13 are all confirmed complete and Step 10-pre Option 2 has been selected. **Step 10-pre runs on every tier** — Pro, Premium, and Ultimate all get the same deployment choice, with direct handover recommended. Never skip Step 10-pre because of the tier, and never upload without Option 2 having been selected.
- **Never present a config with `// TODO:` lines** — a generated config containing any `// TODO: map signal.*` or `// TODO: extract` line is not complete output. Presenting it to the user, showing it in a widget, or passing it to the validation gate before all TODOs are resolved is a skill defect. Every TODO is a field that sends nothing to Acoustic — a complete capture failure for that signal field. Step 9C (TODO scan) must return 0 before any other action.
- **Never combine steps** — do not merge two steps into one tool call or one response turn. Steps 1a, 1b, and 1c are explicitly separate widgets — rendering them as a single combined form is a skill defect.
- **Never add unlisted steps** — any step not in the numbered sequence above is not part of this skill and must not be executed.
- **Never add extra fields to a defined widget** — every intake widget has a verbatim HTML template in this skill. Render it exactly as written. Fields like `appKey`, `collectorUrl`, `environment`, `platform`, `iframes`, and `notes` each belong to a specific step. Adding them to a different step's widget (e.g. putting `appKey` in the Step 1a form) is a skill defect. If in doubt, read the step definition before rendering.
- **`appKey` and `collectorUrl` are never collected in the Step 1a form.** They are handled in Step 1c, which first asks the user whether to retrieve them automatically from Acoustic Connect or supply them manually. Skipping Step 1c or bypassing the auto-retrieve option is a skill defect.
- Do not resume mid-flow from a prior session without first running Step 0 and the Chrome pre-flight check.
- **All user-facing blockers must use `mcp__visualize__show_widget`.** If the skill hits a blocker at any point (unauthenticated session, missing prerequisite, unexpected page state, tool unavailable), it must render a defined blocker widget — never output a prose message. If no widget template exists for the blocker, stop and surface the issue in chat with a single sentence only, then wait for instructions. **That single-sentence rule applies only when no template and no fallback exist for the blocker** — it is not a shortcut around a blocker that has either. `workspace_required` has both a widget and a verbatim fallback, so a one-line summary of it ("Waiting for a folder to be added", "I'll wait for you to add a folder, then click continue") is a skill defect, not an application of this rule. Inventing a prose description of a blocker when a widget template is defined for it is a skill defect. **Exception — visualize unavailable:** If `show_widget` itself is unavailable, apply the Widget fallback protocol defined in Tool discipline below.

**Commentary discipline**
- Between any two consecutive tool calls, produce zero prose output. No transitional sentences ("Now I'll...", "Let me...", "B-3 ✅. Now B-4...", "All 5 chunks loaded..."), no result echoes, no status updates. Hold all intermediate findings until the final response or a blocker.
- The only permitted exception: a single sentence when hitting a hard blocker that requires user action, or when changing direction. In all other cases, silence between calls is mandatory.
- Violating this rule — narrating intermediate tool results or announcing the next step — is a skill defect.
- **HARD STOP — never narrate critical findings in chat.** Phrases like "Critical finding: B2B wholesale site — login required for add-to-cart", "Profile updated. Now reading scripts.", "Need to fix ecommerceSchema", or "The mappings need the validator-required schema. Fixing them now." are ALL skill defects. Every critical finding discovered during inspection MUST be written immediately to `profile.inspection.findings[]` and persist there. The only time a finding surfaces in chat is when it blocks user action — as a single one-line blocker sentence, never as an explanatory paragraph.

**Question discipline**
- Only ask questions that are explicitly listed in this skill. Do not ask open-ended clarifying questions, probe for "nice to have" details, or offer choices that are not part of the defined options.
- `AskUserQuestion` is the only permitted mechanism for decision points. Do not ask questions in plain chat text.
- Do not infer or assume answers — wait for the user to respond to each widget before proceeding.
- **Question text verbatim (HARD STOP):** When this skill specifies an exact question string (shown as **`"Question:"` `"..."`** in a step definition), reproduce it character-for-character. Do not paraphrase, prepend a preamble sentence, drop words, or otherwise modify the wording. Any deviation from the specified text is improvisation and a skill defect.
- Do not ask the same question twice. If the answer was already given (in this session or in the user's opening message), use it and continue. **Exception:** the validation gate ("Did you validate all the signals?") is explicitly designed to be re-presented after handling signal issues — see the Signal Issue sub-flow in Step 9. This re-presentation is intentional and defined by the skill.

**Mode discipline**
- When `mode = "new"`: never reference, display, or suggest previously saved customer names, profile slugs, or delivery URLs. The only inputs are the Step 1 intake form fields.
- When `mode = "existing"`: never render the Step 1 intake form. All customer context comes from the loaded profile.
- Never mix new-customer and existing-customer paths.

**Tool discipline**
- Use `show_widget` only where explicitly specified in this skill (tier summary, profile loaded, warning widgets). Do not invent new widgets.
- Use `AskUserQuestion` only where explicitly specified. Do not substitute it for `show_widget` or vice versa.
- Do not use browser tools (`navigate`, `javascript_tool`, etc.) before the Chrome pre-flight check confirms a connected browser.
- **Widget fidelity:** When a step provides an exact widget HTML template, render that template verbatim — do not add, remove, or modify form fields. If a field (e.g. `appKey`, `collectorUrl`) does not appear in the step's template, it does not belong in that step. Never substitute a prose-described widget with an improvised one that includes extra fields.
- **Pill selection feedback:** Every pill-based widget must show clear selection state so the user knows what they picked and that Continue is now active. Use this CSS + JS pattern for ALL pill widgets — do not deviate:
  ```css
  .pill{border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;border-radius:10px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start;text-align:left;min-width:150px;position:relative;transition:border-color .15s,background .15s}
  .pill.sel{border-color:#706CFF;background:#EEF0FF;color:#1F1E5D}
  .pill.sel .chk{display:flex!important}
  .chk{display:none;position:absolute;top:6px;right:8px;width:16px;height:16px;background:#706CFF;border-radius:50%;align-items:center;justify-content:center;font-size:9px;color:#fff;font-weight:700;line-height:1}
  .btn-cont{background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;width:100%;margin-top:8px;opacity:.35;cursor:not-allowed;transition:opacity .15s}
  ```
  Each pill must include `<span class="chk" aria-hidden="true">✓</span>` as its first child. The `sp()` function must enable the Continue button on selection:
  ```javascript
  function sp(b,cid,hid){document.querySelectorAll('#'+cid+' .pill').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');document.getElementById(hid).value=b.getAttribute('data-value');var btn=document.getElementById('btn-cont');if(btn){btn.style.opacity='1';btn.style.cursor='pointer';}}
  ```
  Continue button: `<button id="btn-cont" class="btn-cont" onclick="...">Continue</button>` — starts disabled (opacity 0.35), activates when `sp()` runs.

**Widget fallback protocol — `mcp__visualize__show_widget` unavailable**

> ⛔ **HARD CONSTRAINT — click-only UX must be preserved in all fallbacks.** Widgets exist to constrain customer input to defined selections. The fallback must never ask an open question, invite a typed response, or accept free-form chat text from the customer. If the only way to collect a required value is free-text input and `show_widget` is unavailable, that is a **hard stop** — see Category 3d below.

**Check availability before the first widget, not after a failure.** `mcp__visualize__show_widget` counts as unavailable in **either** case:

1. **It is not present in this session at all** — no `mcp__visualize__*` tool is listed. This is the common case, and it produces no error message because there is nothing to call. Do not attempt a call to "find out"; look at whether the tool exists, and if it does not, go straight to the fallback.
2. **It is present but fails** — any error, or "Unable to reach visualize". Do not retry more than once before switching.

In both cases apply the fallback below by widget category. A missing tool is not a reason to improvise: every widget in this skill has a defined fallback, and skipping to a sentence of your own is a skill defect.

- **Category 1 — Info/status widgets** (no user input required): `tier_summary`, `inspection_complete`, `sdk_upload_progress`, `uploading_feedback`
  → Output a concise plain-text summary (≤5 lines) in chat. No customer response needed. Continue immediately.

- **Category 2 — Binary/option choice widgets**: `credentials_login_gate`, `blocker_login_required`, `blocker_step_failed`, `upload_login_gate`, `session_expired_gate`, `org_confirmation`, `deployment_choice`, `deployment_choice_cms`, `deployment_instructions`, `intake_step1c_credentials`, `signals_configured`, `deployment`, `session_complete`, `feedback_saved`
  → Use `AskUserQuestion` with the exact same options as the widget. Never use plain chat text for a decision point.

- **Category 3a — Multi-signal validation / retest matrix**: `signal_validation_matrix`, `signal_retest_matrix`
  → Run `AskUserQuestion` sequentially — one call per in-scope signal, in canonical signal order. Each call presents exactly 4 options: "✅ Passed", "⚠️ Issue found", "⏭ Not tested", "🚫 Blocked". Collect all results before routing. Do not ask for free-text notes — if the user selects "Issue found" or "Blocked", the reason collector step (below) handles the follow-up with predefined options.

- **Category 3b — Reason collectors**: `issue_reason_collector`, `blocker_reason_collector`
  → Use `AskUserQuestion` with the predefined reason codes as options. Omit the free-text notes field entirely.

- **Category 3c — Feedback form**: `session_feedback`, `feedback_saved`
  → Use `AskUserQuestion` with the predefined outcome options (Production ready / Usable with minor changes / Not production ready / Run failed). Omit the free-text comment and signal/area pills. Write the selected outcome to the analytics sidecar as normal.
  → **Widget fidelity note:** When `show_widget` IS available, `session_feedback` and `feedback_saved` MUST be rendered from their exact templates in 14b-C — never improvised. The feedback_saved widget MUST include "Close session" + "New customer" buttons and the 30s auto-close countdown. See the hard guardrails at each widget definition for the mandatory sequence.

- **Category 2b — The storage gate**: `workspace_required`
  → This widget has a single button, so it does **not** map onto `AskUserQuestion` (which needs at least two options). Use the verbatim plain-text fallback in the Pre-step instead, then the three-option `AskUserQuestion` defined there. Never replace it with a one-line status such as "Waiting for a folder to be added" — the user has been given no reason to act on and no way to act.

- **Category 3d — Intake forms requiring free-text input**: `intake_step1a`, `credentials_manual_entry`, `category_unknown`
  → **HARD STOP.** These forms collect values (domain, customer name, credentials) that cannot be represented as a fixed option list. Output exactly one sentence: *"The widget renderer is unavailable — please restart the Claude desktop app and reopen this conversation to continue."* Do not ask for these values in chat text. Do not proceed.

**Execution discipline — page inspection and SDK configuration**

This skill executes two kinds of mechanical work: (1) navigating live pages and running capture scripts, and (2) writing `initLogSignal` enhance functions. Both must be done by the book — no creativity, no optimisation, no smart alternatives.

**Page navigation and script execution:**
- Run every capture script verbatim as written in `references/auto-event-capture.md`. Do not modify scripts to "improve" them or handle edge cases not covered by the defined script.
- Navigate to exactly the URLs specified in the step. Do not substitute a "better" URL discovered during inspection.
- If a script returns empty or unexpected output, write the raw result into `inspection.findings[]` and surface it — do not try a different approach or interpret it.
- If a page does not match expectations (element not found, URL differs, dataLayer empty), stop at that sub-step, record the finding, and report a single line to the user. Never silently pivot to an alternative extraction method.
- One script call per sub-step. Do not combine multiple inspection steps into a single tool call.

> ⛔ **HARD GUARDRAIL — add-to-cart simulation: never ask permission (EVER).** Asking "Can I click Add to Basket?", "This will add [product] to your basket — is that OK?", or any variation is a skill defect that breaks the onboarding flow. Add-to-cart simulation during page inspection is a defined, automatic action — not a decision point. The correct behaviour is:
> 1. Emit one status line before navigating: `"Navigating to Product Display Page (PDP)."`
> 2. Inject the capture shim. Silently simulate the add-to-cart click. Capture the Type 4 event and any dataLayer push. Immediately navigate away (homepage or next inspection page). Write findings to the profile. Continue to the next step.
>
> On production sites this adds one real item to the basket. This is expected and accepted. **No user confirmation is required, requested, or permitted.**

**SDK configuration — `initLogSignal` enhance functions:**
- Every `enhance` function must be built exclusively from patterns defined in `references/signal-schema.md`. Do not invent new JavaScript patterns, DOM selectors, or extraction logic not covered by the schema reference.
- Field source priority is fixed (JSON-LD → dataLayer → meta → DOM selector → URL param → static fallback). Do not skip levels or use a lower-priority source when a higher one is available.
- `return false` (not `return null`, not `return signal`) when a required field is missing. This is the defined pattern — do not change it.
- Do not add `console.log`, error handling, `try/catch`, or any helper code not in the defined template. If the schema template does not include it, it does not belong in the enhance function.
- If the correct extraction logic for a field is genuinely unknown after following the schema, leave the field as `null` and flag it as a blocker — do not guess.

**Scope discipline**
- **All signals are available on every subscription tier (Pro, Premium, Ultimate).** Scope is driven by the site, not the tier: configure every signal the site actually supports, and skip a signal only when the site has no matching functionality (no search box → no `onSiteSearch`). Do not ask about, inspect pages for, or generate code for signals the site cannot produce.
- Do not offer suggestions about features, upgrades, or adjacent capabilities outside the current onboarding scope.

**Narrative discipline**
- Do not narrate what you are about to do before a tool call (e.g. "Mode = new. Reading reference files then showing the Step 1 intake form." is forbidden).
- The only permitted pre-tool narrative is a single short, user-facing status line — e.g. "Navigating to M&S homepage." Do NOT append technical sub-actions to this line (e.g. "— injecting capture shim", "— reading Type 2", "— closing the panel", "— updating SKILL.md" are all forbidden). One plain sentence only.
- **Page name terminology in status lines:** Always use the full expanded form — "Product Display Page (PDP)", "Product Listing Page (PLP)", "Sign-in page", "Search results page", "Cart page", "Order confirmation page", "Registration page". Never abbreviate to just "PDP", "PLP", etc. in user-facing text.
- **No self-correction commentary:** Never surface internal trial-and-error to the user (e.g. "Wrong search URL format. Let me find the correct one.", "That didn't work — trying a different approach.", "The panel didn't open. Retrying.", "Got a 404. Correcting the URL."). Retry silently and emit the same single status line if needed. Only surface a blocker if it cannot be resolved without user input.
- **Write critical findings to the profile as you discover them.** Use `inspection.findings[]` in the website profile JSON for every significant finding during site inspection (cross-domain auth, missing dataLayer, CIAM login, no rich media found, etc.). Do not just narrate findings in chat — persist them.
- Do not explain decisions, restate the user's answer, or summarise what just happened. Let the widget or output speak for itself.
- **No inter-step commentary (HARD STOP):** After every tool call, emit zero prose before the next tool call. Zero. This includes:
  - Result-echo: "The popup is showing with 'Delete' and 'View' buttons. The 'View' button is at approximately (379, 240)." ← FORBIDDEN
  - Transition confirmation: "Credentials retrieved. Now showing the confirmation widget." ← FORBIDDEN
  - Screenshot observation: "I can see the button at coordinate X." / "The page loaded successfully." ← FORBIDDEN
  - Step-complete + next-step announce: "Step 11 complete. Now Step 12 — JS review." ← FORBIDDEN
  - Step-number references in transition status lines: "Steps 11, 12, 13 all confirmed. Proceeding to Step 10 — CMS upload." ← FORBIDDEN. Use the action name only: "Steps confirmed. Proceeding to CMS upload." ← CORRECT
  - "Let me…" / "Now I'll…" / "I'll now…" before any tool call ← FORBIDDEN
  - Any sentence that describes what was just seen, what just happened, or what is about to happen ← FORBIDDEN
  - The ONLY permitted output between consecutive tool calls is a single plain status line immediately before the next tool call (e.g. "Navigating to Sign-in page."). If no status line is needed, emit nothing.
- Post-tool prose is only permitted when a step explicitly requires surfacing a validation error or unresolvable blocker to the user.
- **Two documented exceptions, both in the Pre-step:** its opening line (said before the storage check, so the very first thing the user sees explains itself) and its `workspace_required` fallback text (said when the widget renderer is unavailable). Both are verbatim scripts in this skill, not narration — say them in full or not at all. A blocker the user has to clear is never reported as a bare status line.
- Note: `show_widget` elicit form submissions appear in chat as a user message containing the submitted field values — this is platform behavior and cannot be suppressed. It is not skill commentary.

**No session-resume defect recap (HARD STOP):** When resuming from a compacted session or a conversation summary, never open with a description of prior skill defects — e.g. "Two skill defects in my previous run:", "In the last session I violated:", or any sentence recapping prior mistakes before the first tool call. Resume immediately at the next defined step with zero preamble. Prior run issues belong in `inspection.findings[]`, not in chat.

---

## Canonical user-facing widget order

This order is **authoritative**. No later widget definition, step, or routing instruction may override the relative sequence below. Conditional widgets do not have to appear on every run, but when they do appear they must respect this order.

1. `workspace_required` — only when no folder has been added (Pre-step)
2. New-versus-existing customer decision (Step 0)
3. Profile selection widgets — existing-customer route only (Step 0a/0b/0c)
4. Chrome connection widgets — only when required (pre-flight)
5. `intake_step1a`
6. Signal summary (`tier_signal_summary`)
7. Step 1b environment selection
8. `intake_step1c_credentials`
9. Credential route:
   - Automatic: login gate → application selection/creation → credentials found → confirmation
   - Manual: `credentials_manual_entry`
10. Conditional category blocker, if required
11. `inspection_complete`
12. Generated-files summary
13. `signal_validation_matrix`
14. Conditional reason collectors (`issue_reason_collector`, `blocker_reason_collector`)
15. Corrected-config presentation
16. `signal_retest_matrix`
17. `signal_escalation` — only after a failed retest exhausts the attempt limit
18. Browser-verification gate (Step 13)
19. `deployment_choice` — every tier
20. Selected deployment branch (`deployment_instructions` or CMS flow)
21. `signals_configured`
22. Session-completion/review widget
23. `session_feedback`
24. `uploading_feedback`
25. `feedback_saved`

**Correction order within validation:**
`signal_validation_matrix` → reason collector → correction → corrected config → `signal_retest_matrix` → `signal_escalation` (only if retest fails after maxAttempts)

---

## Pre-step: Ensure persistent profile storage

**Run this before Step 0, every time the skill starts.**

**Say this first, verbatim, before running the check** — it is the only preamble this skill permits, and it exists because the storage check is the very first thing the user sees:

> Before we start: this skill saves a profile for each website it configures, so a later run can reload it instead of re-inspecting the site. Those profiles need a folder on your computer. Checking whether this session already has one.

Then check whether a folder has been added to the session context — a real folder on the user's computer, not just the ephemeral sandbox. A folder added to a Project's context is available to every session in that Project, so it shows up here the same way. Run:

```bash
python3 -c "
import glob
# Detect the mount root, NOT the profiles directory inside it. Confirmed on Claude
# Desktop 2026-09: with no folder added, /sessions does not exist at all (both
# /sessions/*/mnt and /sessions/* glob empty); adding one creates /sessions/<id>/mnt
# and the folder's contents appear directly beneath it. Testing for the profiles
# subdirectory instead would report 'not_connected' for a newly added empty folder,
# leaving the gate unsatisfiable until the user happened to create the directory by hand.
mnt = glob.glob('/sessions/*/mnt')
print('connected' if mnt else 'not_connected')
"
```

**If a folder IS available** (`connected`): create `SDK-config-assistant/profiles/` inside it if it is not already there. A first run against a newly added folder is the normal case, so an empty folder is expected here — not an error:

```bash
mkdir -p /sessions/*/mnt/SDK-config-assistant/profiles/
```

All profile reads and writes in this session use that path as the profiles root.

**Generate a run ID immediately after confirming the folder is available.** This ID persists for the entire session and is used in the analytics sidecar.

```bash
python3 -c "
import datetime, random, string, sys
now = datetime.datetime.utcnow()
rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=4))
run_id = 'run-{}-{}'.format(now.strftime('%Y%m%d-%H%M%S'), rand)
started_at = now.strftime('%Y-%m-%dT%H:%M:%SZ')
print(run_id + '|' + started_at)
"
```

Parse the output: `<runId>|<startedAt>`. Store both as session variables. Do not expose them to the user. These are used only in Step 14b when writing the analytics sidecar.

**If NO folder is available** (`not_connected`): take exactly one of these two branches as your very next output. There is no third branch, and no sentence of your own belongs here.

- **`mcp__visualize__show_widget` exists in this session** → render the widget below (title: `workspace_required`, loading: `"Checking storage…"`) and add nothing to it.
- **It does not exist, or it fails** → skip the widget and output the verbatim fallback text further down, then its three-option `AskUserQuestion`.

Then wait for the user to add a folder before proceeding to Step 0. Do not continue until a folder is available.

> **Never refer to a control the user cannot see.** "Click continue", "click the button below", or "then click continue" are only valid when the widget actually rendered and its button is on screen. In the fallback branch the options come from `AskUserQuestion`, so point at those instead. Telling a user to click a button that was never rendered is a skill defect.

> **The waiting state must always carry the explanation with it.** Whatever the renderer does, the user's screen must end up showing three things: **why** a folder is needed (profiles persist across sessions; without one they are lost when the session ends), **the two ways to provide one** (a Project — recommended — or this session only), and **what to do next** (add the folder, then confirm). A bare status line such as "Waiting for a folder to be added before continuing." is a skill defect: it names the blocker without explaining it or telling the user how to clear it. If the widget rendered successfully, it already carries all three and you add nothing. If it did not render, use the fallback below.

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:440px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1rem">
    <div style="width:40px;height:40px;border-radius:50%;background:#EEF0FF;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:20px">📁</div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Add a folder to save website profiles</div>
      <div style="font-size:12px;color:var(--color-text-secondary);margin-top:4px">
        Website profiles are saved to a folder on your computer so they persist across sessions.
        Without a folder, profiles are lost when the session ends.
      </div>
    </div>
  </div>
  <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px;font-size:12px;color:var(--color-text-secondary);margin-bottom:14px">
    <strong>Recommended — use a Project:</strong> create a Project (for example <code>SDK config</code>),
    add a folder to the Project's context, and run this skill from sessions inside that Project. Every
    session in the Project can then read and write the same profiles, so you only set this up once.
    <br><br>
    <strong>Or, this session only:</strong> add a folder to the current session context. It applies to
    this session alone.
    <br><br>
    Either way, a dedicated folder such as <code>Acoustic SDK Configs</code> works well. Where the
    <strong>Add folder</strong> control lives varies by Claude version; check the app's own help if you
    can't find it. Then click the button below.
  </div>
  <button onclick="sendPrompt('Folder added — continue')"
    style="width:100%;padding:10px 16px;background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit">
    I've added a folder — continue
  </button>
</div>
```

When `sendPrompt` fires `'Folder added — continue'`: re-run the bash check. If a folder is now available, proceed to Step 0. If not, re-present the widget. Treat the legacy payload `'Folder connected — continue'` exactly the same way — a session that started on an earlier version of this skill can still send it, and it must not fall through unhandled.

**If `show_widget` is unavailable** (Category 2b): output this text verbatim — not a summary of it — then run the `AskUserQuestion` below.

> **This skill needs a folder before it can start**
>
> Each website you configure gets a profile — its domain, app key, collector URL, signal mappings, and upload details. The profile is what lets a later run reload the site instead of inspecting it again from scratch. Profiles are written to a folder on your computer, so they survive after this conversation ends. Without a folder, everything this run discovers is lost when the session closes.
>
> There are two ways to give me one:
>
> 1. **Use a Project — recommended.** Create a Project (for example `SDK config`), add a folder to the Project's context, then run this skill from sessions inside that Project. Every session in the Project reads and writes the same profiles, so you set this up once and every future run finds your work.
> 2. **This session only.** Add a folder to the current session context. It applies to this conversation alone — the next session will ask again.
>
> A dedicated folder such as `Acoustic SDK Configs` works well. Where the **Add folder** control lives varies by Claude version; check the app's own help if you can't find it.

Then `AskUserQuestion` with exactly these three options — this keeps the gate click-only, and gives the user a way out that isn't a dead end:

- **"I've added a folder — check again"** → re-run the bash check. If a folder is now available, proceed to Step 0. If not, say which path was checked (`/sessions/*/mnt/`), then re-present this question.
- **"Explain that again"** → re-output the text above verbatim, then re-present this question.
- **"Stop for now"** → end the run cleanly: confirm that nothing was saved and that the skill can be started again once a folder is available. Do not proceed to Step 0, and do not start inspecting a site.

> **Never describe how to add a folder in your own words.** Render the widget above verbatim, or — when the renderer is unavailable — the fallback text below it, verbatim. Those two, plus the opening line at the top of this Pre-step, are the whole of what you may say here; do not improvise a shorter version of any of them. Use the app's own vocabulary when you must refer to this — "add a folder", "session context", "Project" — but do not name menus, tabs, buttons, icons, or click paths, and do not ask the user which folder to request access to: the skill can only detect a folder that has already been added, never choose or request one. Anthropic changes this UI frequently, so any navigation detail goes stale and misleads the user. The same applies anywhere else a folder must be added.

---

## Step 0 — New customer or modifying existing?

**This is the very first step — run it before any Chrome checks or onboarding questions.**

> **CRITICAL:** Do NOT ask the new-vs-existing question in plain chat text under any circumstances — regardless of context from a prior session, task list, or conversation summary. Always render the `AskUserQuestion` widget below first and wait for the user's answer.

Use `AskUserQuestion` with exactly two options:

- **New customer** — New customer onboarding (Full onboarding — inspect, generate, upload)
- **Modifying an existing customer SDK config** — Update a previously created customer SDK

Set `mode = "new"` if the user selects "New customer", `mode = "existing"` if "Modifying an existing customer SDK config".

Read the result via `mcp__cowork__read_widget_context`.

---

### If mode = "new"

> **Do NOT ask any separate questions about customer name, domain, tier, or environment before Step 1.** Do not offer existing customer names or saved profile slugs as options — they are irrelevant to a new onboarding. The Step 1 `show_widget` intake form captures everything in one step.

Proceed directly to the **Chrome pre-flight check** below, then to Step 1 (the intake form). No intermediate questions.

After SDK config generation and upload are complete, **persist the website profile** (see "Persist profile after upload" in Step 10 Step C).

---

### If mode = "existing"

**Step 0a — Scan for saved profiles.**

```bash
ls /sessions/*/mnt/SDK-config-assistant/profiles/*.json 2>/dev/null | grep -v '\.analytics\.json$' || echo "NO_PROFILES"
```

If `NO_PROFILES` or the directory doesn't exist: show the `no_profiles_found` widget using `mcp__visualize__show_widget` (title: `no_profiles_found`, loading: `"Checking profiles…"`). Do not output prose.

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:420px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1.25rem">
    <div style="width:40px;height:40px;border-radius:50%;background:#EEF0FF;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:20px">📂</div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">No saved profiles found</div>
      <div style="font-size:12px;color:var(--color-text-secondary);margin-top:4px;line-height:1.5">
        No website profiles were found in the folder available to this session. This could mean this is your first onboarding, or the profiles are in a different folder.
      </div>
    </div>
  </div>
  <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px;font-size:12px;color:var(--color-text-secondary);margin-bottom:16px">
    <strong>Profiles folder:</strong> <code>SDK-config-assistant/profiles/</code> inside the folder added to this session — or to the Project this session is running in.
    If you saved profiles against a different folder, add that one instead, or start a session in the Project that has it.
  </div>
  <div style="display:flex;flex-direction:column;gap:8px">
    <button onclick="sendPrompt('No profiles found — start new onboarding')"
      style="width:100%;padding:10px 16px;background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;text-align:left">
      ✦ Start a new customer onboarding
    </button>
    <button onclick="sendPrompt('No profiles found — add the right folder')"
      style="width:100%;padding:10px 16px;background:var(--color-background-secondary);color:var(--color-text-primary);border:1px solid var(--color-border-tertiary);border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;text-align:left">
      📁 I'll add the right folder
    </button>
  </div>
</div>
```

**Routing:**

- `'No profiles found — start new onboarding'` → set `mode = "new"` and proceed to the Chrome pre-flight check, then Step 1.
- `'No profiles found — add the right folder'` (or the legacy payload `'No profiles found — reconnect folder'`) → ask the user to add the folder that holds their saved profiles, or to start a session in the Project that has that folder in context, and to reply once they have. **Re-run the Pre-step storage check on their next message, whatever it says** — this is a two-turn handshake because only the user can add the folder, so never wait for a particular phrase and never treat an unexpected wording as a non-answer. Do not name any menu, icon, or click path.

If profiles exist, read each one's `customer.name` and `customer.productionDomain`. **Analytics sidecar files (`*.analytics.json`) must be excluded from the profile list** — they are never selectable website profiles.

```bash
python3 -c "
import json, glob, pathlib
# Use glob to find the profiles dir regardless of session name
dirs = glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not dirs:
    print('NO_PROFILES'); exit()
# Exclude .analytics.json sidecars — only operational profiles are selectable
paths = sorted(
    p for p in pathlib.Path(dirs[0]).glob('*.json')
    if not p.name.endswith('.analytics.json')
)
for p in paths:
    try:
        d = json.loads(p.read_text())
        c = d.get('customer', {})
        a = d.get('acoustic', {})
        print(f'{p.stem}|{c.get(\"name\",\"\")}|{c.get(\"productionDomain\",\"\")}|{a.get(\"deliveryUrl\",\"\")}')
    except: pass
"
```

**Step 0b — Let the user select a profile.**

Use `AskUserQuestion` to present the discovered profiles as options. Build the options list dynamically from the profile scan output — one option per profile, with the customer name as the label and the domain as the description. Ask:

> "Which existing website profile should I load?"

Example (for a two-profile result):
```
options: [
  { label: "Acme Retail", description: "www.acmeretail.com" },
  { label: "Northwind Trading", description: "www.northwindtrading.co.uk" }
]
```

The answer maps back to the profile slug (e.g. "Acme Retail" → `acmeretail`, "Northwind Trading" → `northwindtrading`). Store as `profile_slug`.

> **Single-profile edge case:** `AskUserQuestion` requires at least 2 options. If only one profile is found, auto-select it and use `AskUserQuestion` to confirm:
> - **"Yes, load Acme Retail (www.acmeretail.com)"** — proceed with this profile
> - **"No, start a new onboarding instead"** — set `mode = "new"` and proceed from Step 1

**Step 0c — Load the selected profile.**

```bash
python3 -c "
import json, glob, pathlib
dirs = glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not dirs: print('{}'); exit()
p = pathlib.Path(dirs[0]) / '<SLUG>.json'
print(json.dumps(json.loads(p.read_text()), indent=2))
"
```

Set internal variables from the loaded profile:
- `customer.name`, `customer.productionDomain`, `customer.appKey`, `customer.collectorUrl`
- `acoustic.subscriptionId`, `acoustic.assetUuid`, `acoustic.deliveryUrl`, `acoustic.contentHost`

**Show a preload summary widget** (title: `profile_loaded`, loading: `"Loading profile…"`):

```html
<style>
.pl-card{font-family:'Calibre','Inter',sans-serif;background:linear-gradient(135deg,#1F1E5D 0%,#2a2870 100%);border-radius:12px;padding:24px 28px;color:#fff;max-width:540px;box-shadow:0 4px 24px rgba(31,30,93,.18)}
.pl-badge{display:inline-block;background:#00DF8F;color:#1F1E5D;font-size:11px;font-weight:700;letter-spacing:.08em;padding:3px 10px;border-radius:20px;margin-bottom:14px;text-transform:uppercase}
.pl-name{font-size:26px;font-weight:700;margin:0 0 4px;letter-spacing:-.01em}
.pl-domain{color:#C8FF49;font-size:14px;margin:0 0 20px}
.pl-divider{border:none;border-top:1px solid rgba(255,255,255,.12);margin:16px 0}
.pl-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 24px}
.pl-field label{display:block;font-size:10px;font-weight:600;letter-spacing:.1em;color:#9897c8;text-transform:uppercase;margin-bottom:3px}
.pl-field span{font-size:13px;color:#fff;word-break:break-all}
.pl-field span.mono{font-family:'SF Mono','Fira Code',monospace;font-size:11px;color:#b8b7e8}
.pl-field span.empty{color:#706CFF;font-style:italic;font-size:12px}
.pl-pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.pl-pill.ultimate{background:#706CFF;color:#fff}
.pl-pill.premium{background:#4a46cc;color:#fff}
.pl-pill.pro{background:#3a37b0;color:#fff}
.pl-pill.platform{background:rgba(200,255,73,.15);color:#C8FF49}
.pl-pill.ga4{background:rgba(0,223,143,.15);color:#00DF8F}
.pl-pill.ua{background:rgba(255,193,7,.15);color:#ffc107}
.pl-status{display:flex;align-items:center;gap:8px;margin-top:16px;padding:10px 14px;background:rgba(112,108,255,.12);border-radius:8px;border:1px solid rgba(112,108,255,.25)}
.pl-dot{width:8px;height:8px;border-radius:50%;background:#C8FF49;flex-shrink:0}
.pl-status-text{font-size:12px;color:#b8b7e8}
</style>
<div class="pl-card">
  <div class="pl-badge">✓ Profile loaded</div>
  <div class="pl-name">CUSTOMER_NAME</div>
  <div class="pl-domain">DOMAIN</div>
  <hr class="pl-divider">
  <div class="pl-grid">
    <div class="pl-field">
      <label>Platform</label>
      <span><span class="pl-pill platform">PLATFORM</span></span>
    </div>
    <div class="pl-field">
      <label>Tier</label>
      <span><span class="pl-pill TIER_CLASS">TIER</span></span>
    </div>
    <div class="pl-field">
      <label>Ecommerce schema</label>
      <span><span class="pl-pill SCHEMA_CLASS">ECOMMERCE_SCHEMA</span></span>
    </div>
    <div class="pl-field">
      <label>Mode</label>
      <span>MODE</span>
    </div>
    <div class="pl-field">
      <label>App key</label>
      <span class="mono">APP_KEY_TRUNCATED</span>
    </div>
    <div class="pl-field">
      <label>Delivery URL</label>
      DELIVERY_URL_CONTENT
    </div>
    <div class="pl-field">
      <label>Signals configured</label>
      <span>SIGNALS_CONFIGURED of SIGNALS_TOTAL</span>
    </div>
    <div class="pl-field">
      <label>Inspection round</label>
      <span>INSPECTION_ROUND</span>
    </div>
  </div>
  <div class="pl-status">
    <div class="pl-dot"></div>
    <span class="pl-status-text">STATUS_LINE</span>
  </div>
  <button onclick="sendPrompt('Profile acknowledged — show action menu')"
    style="width:100%;margin-top:14px;padding:10px 16px;background:#C8FF49;color:#1F1E5D;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">
    Continue →
  </button>
</div>
```

**Routing:** `'Profile acknowledged — show action menu'` → show the `AskUserQuestion` action menu (Regenerate / Re-inspect / Just re-upload).

**Substitution guide for the `profile_loaded` widget:**

- `CUSTOMER_NAME` → `customer.name`
- `DOMAIN` → `customer.productionDomain`
- `PLATFORM` → `customer.platform` capitalised (e.g. `Magento 2`, `Shopify`, `Custom`)
- `TIER_CLASS` → `ultimate` / `premium` / `pro` (lowercase)
- `TIER` → `customer.tier`
- `SCHEMA_CLASS` → `ga4` / `ua` (lowercase); use `ga4` class for custom/unknown schemas too
- `ECOMMERCE_SCHEMA` → `inspection.ecommerceSchema` uppercased (e.g. `GA4`, `UA`, `Custom`)
- `MODE` → `settings.mode` capitalised (e.g. `Test`, `Production`)
- `APP_KEY_TRUNCATED` → first 16 chars of `customer.appKey` + `…` (e.g. `d691d404c4f746a8…`)
- `DELIVERY_URL_CONTENT` → if `acoustic.deliveryUrl` is non-empty: `<span class="mono" style="color:#706CFF;font-size:11px;word-break:break-all">URL</span>`; otherwise: `<span class="empty">Not yet uploaded</span>`
- `SIGNALS_CONFIGURED` → count of signals where `enabled: true` in `signals`
- `SIGNALS_TOTAL` → total signals in scope for this site (up to 9; the full set is available on every tier)
- `INSPECTION_ROUND` → `inspection.round` (default `1` if absent)
- `STATUS_LINE` → derive from profile state:
  - `acoustic.deliveryUrl` absent → `"No prior SDK upload detected — ready to generate or re-inspect"`
  - `acoustic.sdkBundle.validated == false` → `"SDK config generated — pending signal validation"`
  - `acoustic.sdkConfigurationComplete == true` → `"Configuration complete — delivery URL active"`
  - otherwise → `"Profile loaded from round INSPECTION_ROUND inspection"`

**Before showing the next-action options, check whether the profile has a pending validation:**

```python
import json, glob as _glob, pathlib
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
bundle = profile.get('acoustic', {}).get('sdkBundle', {})
print('pending' if bundle.get('validated') == False else 'not_pending')
```


**If the result is `pending` (`sdkBundle.validated == false`):** skip the action menu and resume from the last validation step. Run the check below to determine which gate to show:

```python
import json, glob as _glob, pathlib
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
ss = profile.get('acoustic', {}).get('signalStatus', {})
escalated = [s for s, v in ss.items() if v.get('completed') == False]
print('escalated:', escalated)
```

- **If `escalated` is non-empty:** re-present the SI-5 gate — "Apart from [ESCALATED_LIST], did you validate the remaining signals? Should we push this JS to the Media Gallery (Connect CMS)?" — with the three options including "Not yet — still validating".
- **If `escalated` is empty:** re-present the main validation gate — "Did you validate all the signals? Should we push this JS to the Media Gallery (Connect CMS)?" — with the three options including "Not yet — still validating".

In both cases skip re-inspection and re-generation entirely.

**Otherwise (`sdkBundle` absent, or `validated` is not `false`):** show the standard action menu:

Use `AskUserQuestion` to confirm what the user wants to do next:

- **"Regenerate SDK config from saved profile"** — re-run generation with the existing profile (no browser re-inspection needed). Skips to Step 9 (validate and generate).
- **"Re-inspect pages then regenerate"** — run the full browser inspection again to refresh mappings. Goes to Chrome pre-flight then Step 2.
- **"Just re-upload the existing SDK config"** — skip generation entirely. Goes to Step 11 (TODO check + manual edits) → Step 12 (JS review — confirm `fakeSignals: false`) → Step 13 (browser verify) → Step 10-pre (deployment choice) → Step 10 re-upload flow. Do NOT skip Steps 11, 12, or 13 — re-uploading a config without verifying `fakeSignals: false` would push a test-mode config to production.

---

## Pre-flight: check Claude in Chrome is connected

**Do this before anything else — before asking onboarding questions, before reading reference files.**

Call `mcp__Claude_in_Chrome__list_connected_browsers`. Three outcomes:

**A — Tool available, browsers listed (≥1 result)**
Proceed normally in `website-assisted` mode. Log: `[ACO] Claude in Chrome ✅ — browser connected`.

**B — Tool available but no browsers connected (empty list)**
Tell the user:

> Chrome is reachable but no browser tab is connected. Please make sure the Chrome extension for Claude is enabled and connected to the tab you want inspected, then let me know and I'll continue.

Wait for the user to confirm before continuing. Do not proceed to the onboarding questions.

**C — Tool unavailable (ToolSearch returns no match or call errors)**
Tell the user:

> The Chrome extension for Claude is not installed or not enabled. Without it I can't inspect live pages, so trigger mappings will be unverified.
>
> To enable website-assisted mode:
> 1. Ensure the Chrome extension for Claude is installed (from the Chrome Web Store), enabled, and signed in to your Anthropic account.
> 2. Open the customer's website in Chrome and connect the extension to that tab.
> 3. Come back here and say "Chrome is ready" — I'll re-check and continue.
>
> **Alternatively**, I can continue in guided mode — you provide DOM selectors, dataLayer events, and console output manually, and I'll mark all mappings as unverified.

Ask: **"Should I wait for Chrome, or continue in guided mode?"** If guided, set `implementationMode: "guided"` in the profile and proceed. Never silently fall through to website-assisted if the tool check failed.

> **Keep extension instructions generic.** Say what state is required — installed, enabled, signed in, connected to the tab — never how to reach it. Do not name icons, toolbars, pinning, menu items, or click paths, and do not invent steps beyond the wording above: Anthropic changes the extension's UI and listing name frequently, so specifics go stale and confuse the user.

---

This skill only works in Claude Cowork (for now). It relies on the Claude in Chrome browser automation tool, which is not available in other Claude Code surfaces.

Use the best available interactive browser surface as the primary inspection tool:

- In Claude Cowork, prefer Claude for Chrome or a configured browser/Playwright MCP server.
- If no browser automation tool is available, use guided mode and clearly mark runtime mappings as unverified.

Do not replace live browser inspection with HTTP fetches, source-only scraping, or assumptions about client-rendered pages.

## Required resources

Read these files before starting:

- Read [references/browser-inspection.md](references/browser-inspection.md) before inspecting pages.
- Read [references/signal-schema.md](references/signal-schema.md) before mapping or generating signals.
- Read [references/auto-event-capture.md](references/auto-event-capture.md) before navigating to customer pages — this contains the capture shim and interaction scripts.
- Read [references/sdk-console-messages.md](references/sdk-console-messages.md) when interpreting console output or configuring `triggers` triggers from customer-provided messages.
- Read [references/output-contract.md](references/output-contract.md) before producing final deliverables.
- Run `scripts/validate_profile.py` before generation.
- Run `scripts/generate_sdk.py` to create deterministic mapping JSON, JavaScript, and review notes.

---

## Workflow

### 1. Establish the onboarding scope

> **MODE GATE — skip Step 1 entirely if `mode = "existing"`**. When mode is existing, all customer context was loaded from the saved profile in Step 0c and the user's next action was already selected (regenerate / re-inspect / re-upload). Jump directly to the appropriate step — do not render the onboarding intake form or ask any Step 1 questions.

Collect all required information in the intake form below. Only ask for information not already provided in the user's opening message.

> **Do NOT use `AskUserQuestion` for name, domain, or tier** — `AskUserQuestion` does not support free-text input and must not offer previously saved customer names or profile slugs as options. Use `show_widget` for the intake form.

**Step 1a — Customer name, domain, and tier**

Use `mcp__visualize__show_widget` to render the intake form below.

Title: `intake_step1a`. Single loading message: `"Loading intake form…"`.

> **Widget fidelity rule:** Render this template verbatim. Do NOT add extra fields (e.g. `appKey`, `collectorUrl`, `environment`, `platform`, `iframes`, `notes`). Those belong in later steps. Do NOT combine Step 1a, 1b, and 1c into a single form — each is a separate widget rendered in sequence. Only the three fields below are collected here.

```html
<style>
.ep{font-family:var(--font-sans);padding:.75rem 0}
.eg{margin-bottom:14px}
.eq{font-size:11px;font-weight:600;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:6px}
.ei{width:100%;padding:8px 10px;border:1px solid var(--color-border-tertiary);border-radius:6px;font-size:12px;background:var(--color-background-secondary);color:var(--color-text-primary);box-sizing:border-box}
.pills{display:flex;gap:8px;flex-wrap:wrap}
.pill{border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;border-radius:10px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start;text-align:left;min-width:130px;position:relative;transition:border-color .15s,background .15s}
.pill.sel{border-color:#706CFF;background:#EEF0FF;color:#1F1E5D}
.pill.sel .chk{display:flex!important}
.chk{display:none;position:absolute;top:6px;right:8px;width:16px;height:16px;background:#706CFF;border-radius:50%;align-items:center;justify-content:center;font-size:9px;color:#fff;font-weight:700;line-height:1}
.btn-cont{background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;width:100%;margin-top:8px;opacity:.35;cursor:not-allowed;transition:opacity .15s}
</style>
<div class="ep">
  <div style="font-size:14px;font-weight:600;color:var(--color-text-primary);margin-bottom:16px">New customer — step 1 of 3</div>
  <div class="eg">
    <label class="eq">Customer name</label>
    <input id="f-name" class="ei" type="text" placeholder="e.g. Acme Retail" oninput="cr()"/>
  </div>
  <div class="eg">
    <label class="eq">Production domain</label>
    <input id="f-domain" class="ei" type="text" placeholder="e.g. www.acmeretail.com" oninput="cr()"/>
  </div>
  <div class="eg">
    <label class="eq">Subscription tier</label>
    <div class="pills" id="tp">
      <button type="button" class="pill" data-value="Pro" onclick="sp(this)">
        <span class="chk" aria-hidden="true">✓</span>
        <i class="ti ti-bolt" style="font-size:18px"></i>
        <span><span style="font-size:12px;font-weight:600">Pro</span></span>
      </button>
      <button type="button" class="pill" data-value="Premium" onclick="sp(this)">
        <span class="chk" aria-hidden="true">✓</span>
        <i class="ti ti-star" style="font-size:18px"></i>
        <span><span style="font-size:12px;font-weight:600">Premium</span></span>
      </button>
      <button type="button" class="pill" data-value="Ultimate" onclick="sp(this)">
        <span class="chk" aria-hidden="true">✓</span>
        <i class="ti ti-crown" style="font-size:18px"></i>
        <span><span style="font-size:12px;font-weight:600">Ultimate</span></span>
      </button>
    </div>
    <input type="hidden" id="f-tier" value=""/>
  </div>
  <button id="btn-cont" class="btn-cont" onclick="sub()">Continue</button>
</div>
<script>
function sp(b){document.querySelectorAll('#tp .pill').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');document.getElementById('f-tier').value=b.getAttribute('data-value');cr();}
function cr(){var n=document.getElementById('f-name').value.trim();var d=document.getElementById('f-domain').value.trim();var t=document.getElementById('f-tier').value;var btn=document.getElementById('btn-cont');if(n&&d&&t){btn.style.opacity='1';btn.style.cursor='pointer';}else{btn.style.opacity='.35';btn.style.cursor='not-allowed';}}
function sub(){var n=document.getElementById('f-name').value.trim();var d=document.getElementById('f-domain').value.trim();var t=document.getElementById('f-tier').value;if(!n||!d||!t)return;sendPrompt('Step 1a: name='+n+' | domain='+d+' | tier='+t);}
</script>
```

After `sendPrompt` fires, the values arrive as the next user message. Parse `name`, `domain`, and `tier` from it. As soon as tier is confirmed, render the tier summary widget (see below) before proceeding to Step 1b.

**Step 1b — Environment**

Use `AskUserQuestion`:
- "Do you have a staging domain, or will we inspect production only?" — pills: **Production only** / **Staging available**
- If staging: follow up with a text input for the staging URL

**Step 1c — App key and Collector URL**

Use `mcp__visualize__show_widget` to ask how to obtain credentials. Title: `intake_step1c_credentials`. Single loading message: `"Loading…"`.

> **Widget fidelity rule:** Render this template verbatim. Do not add extra fields or substitute with prose.

```html
<style>
.ep{font-family:var(--font-sans);padding:.75rem 0}
.eg{margin-bottom:14px}
.eq{font-size:11px;font-weight:600;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:6px}
.pills{display:flex;gap:8px;flex-wrap:wrap}
.pill{border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;border-radius:10px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start;text-align:left;min-width:160px;position:relative;transition:border-color .15s,background .15s}
.pill.sel{border-color:#706CFF;background:#EEF0FF;color:#1F1E5D}
.pill.sel .chk{display:flex!important}
.chk{display:none;position:absolute;top:6px;right:8px;width:16px;height:16px;background:#706CFF;border-radius:50%;align-items:center;justify-content:center;font-size:9px;color:#fff;font-weight:700;line-height:1}
.btn-cont{background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;width:100%;margin-top:8px;opacity:.35;cursor:not-allowed;transition:opacity .15s}
</style>
<div class="ep">
  <div style="font-size:14px;font-weight:500;color:var(--color-text-primary);margin-bottom:16px">New customer — step 2 of 3</div>
  <div class="eg">
    <label class="eq">How should I get the app key and collector URL?</label>
    <div class="pills" id="cp">
      <button type="button" class="pill" data-value="auto" onclick="sp(this)">
        <span class="chk" aria-hidden="true">✓</span>
        <i class="ti ti-cloud-download" style="font-size:20px" aria-hidden="true"></i>
        <span>
          <span style="font-size:12px;font-weight:500">Retrieve from Acoustic Connect</span><br>
          <span style="font-size:10px;color:var(--color-text-tertiary)">I'll look them up automatically</span>
        </span>
      </button>
      <button type="button" class="pill" data-value="manual" onclick="sp(this)">
        <span class="chk" aria-hidden="true">✓</span>
        <i class="ti ti-keyboard" style="font-size:20px" aria-hidden="true"></i>
        <span>
          <span style="font-size:12px;font-weight:500">I'll supply them</span><br>
          <span style="font-size:10px;color:var(--color-text-tertiary)">Paste app key and collector URL</span>
        </span>
      </button>
    </div>
    <input type="hidden" id="f-cred" value=""/>
  </div>
  <button id="btn-cont" class="btn-cont" onclick="sub()">Continue</button>
</div>
<script>
function sp(b){document.querySelectorAll('#cp .pill').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');document.getElementById('f-cred').value=b.getAttribute('data-value');var btn=document.getElementById('btn-cont');btn.style.opacity='1';btn.style.cursor='pointer';}
function sub(){var v=document.getElementById('f-cred').value;if(!v)return;sendPrompt('Step 1c: credentials='+v);}
</script>
```

When `sendPrompt` fires, the value arrives as `Step 1c: credentials=auto` or `Step 1c: credentials=manual`.

- **`credentials=auto`** — the skill navigates to the Integrations page and reads credentials directly from the browser
- **`credentials=manual`** — show the `credentials_manual_entry` widget (see template below) so the user can paste both values at once. Do NOT ask for each credential one at a time in chat text.

**Manual credential entry widget — use for ALL manual-entry cases (credentials=manual, auto-discovery failure, "No, use different ones").** Title: `credentials_manual_entry`. Loading message: `"Loading…"`.

> **Widget fidelity rule:** Render verbatim. Do not substitute with prose or sequential chat questions. Continue button starts disabled and activates only when both fields have values.

```html
<style>
.ep{font-family:var(--font-sans);padding:.75rem 0}
.eg{margin-bottom:14px}
.eq{font-size:11px;font-weight:600;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:6px}
.ei{width:100%;padding:8px 10px;border:1px solid var(--color-border-tertiary);border-radius:6px;font-size:12px;background:var(--color-background-secondary);color:var(--color-text-primary);box-sizing:border-box;font-family:monospace}
.ei:focus{outline:2px solid #706CFF;border-color:#706CFF}
.btn-cont{background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;width:100%;margin-top:8px;opacity:.35;cursor:not-allowed;transition:opacity .15s}
</style>
<div class="ep">
  <div style="font-size:14px;font-weight:500;color:var(--color-text-primary);margin-bottom:4px">Enter credentials</div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:16px">Find these in Acoustic Connect → Applications → your web app → General settings.</div>
  <div class="eg">
    <label class="eq">App key</label>
    <input id="f-appkey" class="ei" type="text" placeholder="32-character hex string" oninput="cr()"/>
  </div>
  <div class="eg">
    <label class="eq">Collector URL</label>
    <input id="f-colurl" class="ei" type="text" placeholder="https://lib-eu-1.brilliantcollector.com/..." oninput="cr()"/>
  </div>
  <button id="btn-cont" class="btn-cont" onclick="sub()">Continue</button>
</div>
<script>
function cr(){var k=document.getElementById('f-appkey').value.trim();var u=document.getElementById('f-colurl').value.trim();var btn=document.getElementById('btn-cont');if(k&&u){btn.style.opacity='1';btn.style.cursor='pointer';}else{btn.style.opacity='.35';btn.style.cursor='not-allowed';}}
function sub(){var k=document.getElementById('f-appkey').value.trim();var u=document.getElementById('f-colurl').value.trim();if(!k||!u)return;sendPrompt('Credentials manual: appKey='+k+' | collectorUrl='+u);}
</script>
```

When `sendPrompt` fires with `Credentials manual: appKey=... | collectorUrl=...`, parse `appKey` and `collectorUrl` and proceed as if they were retrieved automatically — store them in the website profile and continue to Step 2.

**If the user selects "Get automatically":**

> **Narration rule:** Do NOT describe individual browser actions to the user. This includes: hover, screenshot, click, "navigating to...", "taking screenshot", "zooming in", "I can see...", "The panel is open", "Got both credentials", "Now closing the panel", "The click missed", "Let me try...", "That didn't work", "Retrying", or ANY description of what is happening internally. Output exactly one status line before starting, then run ALL browser steps silently, then present the discovered values. No commentary between steps — not even a single sentence.

> **Anti-improvisation rule (HARD STOP):** The only permitted methods for credential retrieval are the numbered steps below. The following are strictly forbidden regardless of circumstances:
> - Calling GraphQL, REST, or any other API endpoint (e.g. `/api/graph`, `/api/v1/...`)
> - Reading `localStorage`, `sessionStorage`, or cookies to extract tokens or credentials
> - Constructing direct URLs to app detail pages (e.g. `/connect/applications/<id>`)
> - Using hover-based card interactions to reveal UI elements
> - Any browser action not explicitly listed in the numbered steps
>
> If a listed browser step fails after one retry, render the `blocker_step_failed` widget (title: `blocker_step_failed`, loading message: `"Loading…"`) using `mcp__visualize__show_widget` and wait for user guidance. Do NOT attempt an alternative approach. Inventing an alternative method is a skill defect.
>
> **Blocker widget for step failure:**
> ```html
> <div style="font-family:var(--font-sans);padding:.75rem 0">
>   <div style="display:flex;align-items:flex-start;gap:12px;padding:14px 16px;border:1px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);background:var(--color-background-secondary)">
>     <i class="ti ti-alert-triangle" style="font-size:20px;color:#706CFF;flex-shrink:0;margin-top:2px" aria-hidden="true"></i>
>     <div>
>       <div style="font-size:13px;font-weight:500;color:var(--color-text-primary);margin-bottom:4px">Couldn't retrieve credentials automatically</div>
>       <div style="font-size:12px;color:var(--color-text-secondary)">A step in the credential retrieval flow failed. Please supply the App key and Collector URL manually, or try again.</div>
>     </div>
>   </div>
>   <div style="display:flex;gap:8px;margin-top:12px">
>     <button onclick="sendPrompt('Credential retrieval failed — I will supply them manually')" style="flex:1;background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 16px;font-size:12px;font-weight:600;cursor:pointer">Enter manually</button>
>     <button onclick="sendPrompt('Credential retrieval failed — please retry')" style="flex:1;background:var(--color-background-secondary);color:var(--color-text-primary);border:1px solid var(--color-border-tertiary);border-radius:8px;padding:9px 16px;font-size:12px;font-weight:600;cursor:pointer">Retry</button>
>   </div>
> </div>
> ```
>
> When `sendPrompt` fires `'Credential retrieval failed — I will supply them manually'`, immediately show the `credentials_manual_entry` widget (defined in Step 1c above). Do NOT ask in chat text. When `sendPrompt` fires `'Credential retrieval failed — please retry'`, repeat from step 1 of the auto-discovery sequence.

**Proactive login gate (mandatory before navigating).** Before navigating to any Acoustic Connect page, show the `credentials_login_gate` widget using `mcp__visualize__show_widget` (title: `credentials_login_gate`, loading: `"Loading…"`). Do NOT skip this step even if you believe the session is active — the user must confirm explicitly.

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:420px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1.25rem">
    <div style="width:40px;height:40px;border-radius:50%;background:#EEF0FF;display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#706CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
    </div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Sign in to Acoustic Connect</div>
      <div style="font-size:12px;color:var(--color-text-tertiary);margin-top:4px">Please make sure you're signed in to <strong>app.goacoustic.com</strong> in Chrome before I retrieve your app credentials.</div>
    </div>
  </div>
  <button onclick="sendPrompt('Credentials login confirmed — retrieve automatically')" style="width:100%;padding:10px 16px;background:#1F1E5D;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit">
    I'm signed in — retrieve credentials
  </button>
</div>
```

When `sendPrompt` fires `'Credentials login confirmed — retrieve automatically'`, proceed with the status line and auto-discovery sequence below.

Tell the user: `Gathering credentials from Acoustic Connect. This will take a few minutes.`

Then silently:

1. Navigate to `https://app.goacoustic.com/connect/applications`.

2. Wait for the page to load, then use `javascript_tool` to read app names from page text:
   ```js
   await new Promise(r => setTimeout(r, 1500));
   document.body.innerText.substring(0, 4000)
   ```

3. **Login check (mandatory before continuing):** If the page body contains "Log in" or the current URL contains `login.goacoustic.com`, the session is unauthenticated. Stop immediately and render this blocker widget verbatim using `mcp__visualize__show_widget` (title: `blocker_login_required`, loading message: `"Loading…"`). Do NOT output prose. Wait for the user to click the button before retrying Step 1.

   > **Widget fidelity rule:** Render this template verbatim. Never replace it with a prose message.

   ```html
   <div style="font-family:var(--font-sans);padding:.75rem 0">
     <div style="display:flex;align-items:flex-start;gap:12px;padding:14px 16px;border:1px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);background:var(--color-background-secondary)">
       <i class="ti ti-lock" style="font-size:20px;color:#706CFF;flex-shrink:0;margin-top:2px" aria-hidden="true"></i>
       <div>
         <div style="font-size:13px;font-weight:500;color:var(--color-text-primary);margin-bottom:4px">Sign in to Acoustic Connect required</div>
         <div style="font-size:12px;color:var(--color-text-secondary)">The browser redirected to the login page. Please sign in to <strong>app.goacoustic.com</strong> in Chrome, then click Continue.</div>
       </div>
     </div>
     <button onclick="sendPrompt('Acoustic Connect login confirmed — please continue')" style="margin-top:12px;background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;cursor:pointer;width:100%">I'm logged in — continue</button>
   </div>
   ```

   When `sendPrompt` fires with `Acoustic Connect login confirmed — please continue`, retry from Step 1 of this auto-discovery sequence.

4. Collect all "My apps" cards and present them to the user for org confirmation. Use this script to extract app names and types:
   ```js
   await new Promise(r => setTimeout(r, 1500));
   const cards = Array.from(document.querySelectorAll('div.GalleryTilestyles__GalleryTileComponent-sc-ucrfdh-2'));
   cards.map(function(c) {
     const name = c.querySelector('p.bx--typography-text__productive-heading-02')?.innerText?.trim();
     const hasMobile = c.innerText.includes('Mobile');
     const appKeyMatch = c.innerText.match(/[a-f0-9]{32}/);
     return { name, type: hasMobile ? 'Mobile' : 'Web/Web+mobile', appKey: appKeyMatch ? appKeyMatch[0].substring(0,8)+'…' : null };
   }).filter(function(c) { return c.name && c.appKey; });
   ```

   > **Key insight:** In the Acoustic Connect applications page, "Web and mobile" apps in "My apps" do NOT display a type label in their card text — only Mobile apps show "Mobile". The text "Web" only appears in the App Marketplace section (template entries), not in the user's installed apps. Do NOT use "starts with Web" to find the web app card — it will match the wrong element.

   Present the found app names to the user in a `show_widget` confirmation widget. Each app row must be **clickable and highlight on selection** — use this pattern:

   ```html
   <!-- App row: clicking it highlights and fires sendPrompt with the selected app name -->
   <div class="app-row" onclick="selectApp(this,'Jai Ecommerce Test')">
     <div class="app-name">Jai Ecommerce Test</div>
     <div class="app-key">4eda4901…</div>
     <span class="app-badge">Web</span>
   </div>
   ```
   ```js
   function selectApp(el, name) {
     document.querySelectorAll('.app-row').forEach(r => r.classList.remove('selected'));
     el.classList.add('selected');
     // Enable confirm button
     var btn = document.getElementById('btn-confirm');
     if (btn) { btn.style.opacity='1'; btn.style.cursor='pointer'; btn.dataset.app=name; }
   }
   ```
   The confirm button calls `sendPrompt('Org confirmed — use app: '+btn.dataset.app)` and is disabled until a row is selected. Include a "No — switch org" secondary button.

4. Once the org is confirmed and the app selected, open its detail modal using the **double-click tile → View button** sequence. This is the only supported approach — do not attempt API calls, hover interactions, or direct URL navigation.

   > **CRITICAL:** Do NOT use GraphQL APIs, REST endpoints, localStorage tokens, direct URL navigation to app detail pages, or any approach not listed in steps a–d below. If any sub-step fails after one retry, render the `blocker_step_failed` widget and wait for user guidance.

   a. Use `mcp__Claude_in_Chrome__find` to locate the gallery tile for the selected app by its name text (e.g. `find({"query": "Jai Ecommerce Test"})`) — this returns a `ref` value for the element.
   b. Use `computer` with `double_click` action at the element's coordinates (from the `find` result) to double-click the tile. This opens a popup/flyout.
   c. Use `mcp__Claude_in_Chrome__find` to locate the "View" button in the popup (e.g. `find({"query": "View"})`), then `computer` `left_click` to open the credential modal.
   d. Wait 800ms. The "Web and mobile" modal is now open and shows App key and Collector URL in input fields. Proceed to step 5.

5. Read the App key and Collector URL directly from the input fields in the side panel — no need to click Next:
   ```js
   await new Promise(r => setTimeout(r, 600));
   const fields = Array.from(document.querySelectorAll('input')).map(function(i) { return { id: i.id, value: i.value }; }).filter(function(f) { return f.value && f.value.length > 5; });
   JSON.stringify(fields);
   ```

   Extract: `appKey` (32-char hex) and `collectorUrl` (starts with `https://` and contains `collector`).

   > **Do NOT click Next** — the side panel already exposes both credentials in its first view (GENERAL SETTINGS). Clicking Next navigates away unnecessarily.

   Original step 5 (reading from "Analytics configuration" page):
   ```js
   await new Promise(r => setTimeout(r, 600));
   Array.from(document.querySelectorAll('input')).map(function(i) { return i.value; }).filter(Boolean)
   ```
   The first non-empty value is the App key, the second is the Collector URL.

6. Click **Cancel** to exit the wizard without saving:
   ```js
   const cancelBtn = Array.from(document.querySelectorAll('button')).find(function(b) { return b.innerText.trim() === 'Cancel'; });
   if (cancelBtn) { cancelBtn.click(); }
   ```

7. If the App key value is blocked by security policy (`[BLOCKED: Base64 encoded data]`), use the truncated value already read from the page body in step 2.

7. **Present discovered credentials in a `show_widget`** — do not bury them in an `AskUserQuestion` option description. Use this HTML (substitute actual values):

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:12px">
    Found: <span style="color:#706CFF">APP_NAME</span>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px">
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px">
      <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">App key</div>
      <div style="font-family:monospace;font-size:12px;color:var(--color-text-primary);word-break:break-all">APP_KEY</div>
    </div>
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px">
      <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Collector URL</div>
      <div style="font-family:monospace;font-size:12px;color:var(--color-text-primary);word-break:break-all">COLLECTOR_URL</div>
    </div>
  </div>
</div>
```

Then follow immediately with `AskUserQuestion`: **"Do these credentials look correct?"** — two options:
- **"Yes, correct"** — Proceed with these credentials for the onboarding.
- **"No, use different ones"** — Show the `credentials_manual_entry` widget so the user can paste the correct values. Do NOT ask in chat text.

8. **If multiple "Web and mobile" apps found:** Present the app names as pills in `AskUserQuestion` and ask the user to select the correct one first, then run steps 4–7 for the selected app.
9. **If no "Web and mobile" app found:** Ask the user with `AskUserQuestion` (two options: **"Create one now"** / **"I'll provide them"**). If they pick "I'll provide them", fall back to that flow below. If they pick "Create one now", continue with Step 1d.

**Step 1d — Create a new "Web and mobile" app (only when Step 1c step 9 found none)**

> **Narration rule:** Do NOT describe individual browser actions. Tell the user `"Creating a new Web and mobile app in Acoustic Connect…"` as a single status line, then run all browser steps silently.

Tell the user: `Creating a new Web and mobile app in Acoustic Connect…`

Then silently:

1. Navigate to `https://app.goacoustic.com/connect/applications`. Wait 1500ms.

2. Click the **"App marketplace"** tab, then the **"Install"** button on the **Web** tile via `javascript_tool` — text matching is more reliable than class/DOM position, which changes between marketplace layouts:
   ```js
   await new Promise(r => setTimeout(r, 1000));
   const tabs = Array.from(document.querySelectorAll('button, a, [role="tab"]'));
   const marketplaceTab = tabs.find(t => t.innerText.trim() === 'App marketplace');
   if (marketplaceTab) marketplaceTab.click();
   await new Promise(r => setTimeout(r, 1000));
   const webCard = Array.from(document.querySelectorAll('[class*="card"], [role="row"]')).find(el => /(^|\s)Web(\s|$)/.test(el.innerText) && !/mobile/i.test(el.innerText.split('\n')[0]));
   const installBtn = webCard?.querySelector('button');
   if (installBtn) { installBtn.scrollIntoView(); installBtn.click(); }
   await new Promise(r => setTimeout(r, 1000));
   document.body.innerText.includes('Before you begin') ? 'wizard opened' : 'wizard did not open — retry';
   ```
   If the result is `'wizard did not open — retry'`, wait 500ms and re-run the same script once. If it still fails, tell the user the wizard didn't open and ask them to click **App marketplace → Web → Install** manually, then confirm before continuing.

3. **"Before you begin" screen** — click **Next**:
   ```js
   const nextBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Next');
   if (nextBtn) nextBtn.click();
   await new Promise(r => setTimeout(r, 800));
   document.body.innerText.includes('General settings') ? 'on General settings' : 'still on Before you begin — retry';
   ```

4. **"General settings" screen** — the App name field defaults to `"Web"`. Leave it as-is unless the user specified a name in Step 1a, then click **Next**:
   ```js
   const nameField = document.querySelector('input, textarea');
   if (nameField && "%%CUSTOMER_NAME%%") {
     nameField.value = "%%CUSTOMER_NAME%%";
     nameField.dispatchEvent(new Event('input', { bubbles: true }));
   }
   await new Promise(r => setTimeout(r, 300));
   const nextBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Next');
   if (nextBtn) nextBtn.click();
   await new Promise(r => setTimeout(r, 1000));
   document.body.innerText.includes('Analytics configuration') ? 'on Analytics configuration' : 'still on General settings — retry';
   ```
   Replace `%%CUSTOMER_NAME%%` with the confirmed customer name from Step 1a, or leave the field untouched if none was given yet.

5. **"Analytics configuration" screen** — the App key and Collector URL are shown here, already generated. Read them the same way as step 4 in the existing-app flow above:
   ```js
   Array.from(document.querySelectorAll('input[type="text"], input:not([type]), input[readonly]')).map(i => i.value).filter(Boolean)
   // Returns: [AppKey, CollectorURL]
   ```
   If the App key value is blocked by security policy (`[BLOCKED: Base64 encoded data]`), read it from the visible code snippet block instead:
   ```js
   const codeBlock = Array.from(document.querySelectorAll('pre, code')).map(el => el.innerText).join('\n');
   const appKeyMatch = codeBlock.match(/appKey:\s*"([^"]+)"/);
   const postUrlMatch = codeBlock.match(/postUrl:\s*"([^"]+)"/);
   [appKeyMatch?.[1], postUrlMatch?.[1]];
   ```

6. Click **Next**, then on the **"Confirmation"** screen click **Confirm**:
   ```js
   const nextBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Next');
   if (nextBtn) nextBtn.click();
   await new Promise(r => setTimeout(r, 1000));
   const confirmBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Confirm');
   if (confirmBtn) confirmBtn.click();
   await new Promise(r => setTimeout(r, 1000));
   document.body.innerText.includes('has been registered') ? 'app created' : 'confirmation not detected — verify manually';
   ```

7. **Present the new credentials in a `show_widget`** — reuse the exact same credentials card HTML from step 7 in the existing-app flow above, substituting the newly created app's name, key, and collector URL.

8. Follow immediately with `AskUserQuestion`: **"Does this look correct?"** — two options: **"Yes, use this app"** / **"No, something went wrong"**. If something went wrong, fall back to the "I'll provide them" flow below.

> **If any step above fails to progress** (the expected screen text doesn't appear after the retry): stop, tell the user exactly which screen the wizard is stuck on, and ask them to complete that one step manually in the open browser tab, then say "done" so you can resume reading credentials from step 5 onward.

**Manual credential entry:** All manual-entry cases (initial manual selection, auto-discovery failure, "No, use different ones", no suitable app, new app creation failure) use the `credentials_manual_entry` widget defined in Step 1c above. Do not render a second credential form.

**Step 1e — Remaining details** (ask only if not already known)

- **Test account credentials?** (email + password) — needed for checkout sign-in on staging. For audience email capture only, credentials are optional: the skill generates a dummy email (`aco-test-<timestamp>@mailinator.com`) and fills the email field directly — no form submission required.
- **Does registration require email verification?** — only relevant if no sign-in page is accessible and full registration is needed.
- **Sign-in page URL** — if non-standard, confirm the actual path (default: `/login`, `/account/signin`).
- dataLayer presence and name (default: `dataLayer`).
- Iframe usage.
- Relevant example journey URLs.
- Current `initLogSignal()` or config when updating an existing customer.

#### Signal scope

**Every signal below is available on every subscription tier — Pro, Premium, and Ultimate.** There is no tier gating on signals. Use this list as the canonical signal set and its order.

| # | Signal | Captures |
|---:|---|---|
| 1 | `identification` (audience email — sign-in) | Email captured from the sign-in form |
| 2 | `accountRegistered` (audience email — registration) | Email captured from the registration success page |
| 3 | `addToCart` | Product added to basket — ID, name, price, quantity |
| 4 | `order` (purchase / conversion) | Purchase conversion — order ID, revenue, items |
| 5 | `pageView` | Every page load — URL, title, page category |
| 6 | `productView` | Product detail page view |
| 7 | `onSiteSearch` | Search term, result count, effect |
| 8 | `productConfiguration` | Colour / size / quantity selector interactions |
| 9 | `richMediaInteraction` | Video, podcast, download events |

> ⚠️ `richMediaInteraction` — available on every tier, but **no enhance function is generated**. The signal block is emitted as a skeleton. Configuring video/audio/download interactions requires a site-specific manual enhance written by the implementer after inspecting the media elements on the customer's site. Do not claim this signal is "configured" — it must be explicitly flagged as requiring manual work in the implementation review.

> **Scope comes from the site, never from the tier.** Skip a signal only when the site has no matching functionality — no search box, no cart, no product pages, no media. Record every such omission and its reason in `inspection.findings[]`, and exclude the signal from the website profile. If the site gains that functionality later, run a `diff` mode pass to add the signal.

#### Show a tier summary widget immediately after the tier is confirmed

As soon as the subscription tier is confirmed, call `mcp__visualize__show_widget` to render the signal summary below. Do this before asking any further questions or navigating any pages — it gives the user an instant visual confirmation of what will and won't be configured. The tier is shown for context only; it does not change which signals are in scope.

Use the title `tier_signal_summary` and a single loading message `"Building signal summary"`.

Render this HTML, substituting `CUSTOMER_NAME` and `TIER` with the actual values. Every signal in the table above starts as included; move a signal to the second column only once inspection or the intake answers show the site has no matching functionality:

```html
<div style="padding:1rem 0; font-family:var(--font-sans)">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.25rem">
    <div style="background:#1F1E5D;color:#C8FF49;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:500">
      TIER tier
    </div>
    <span style="font-size:15px;font-weight:500;color:var(--color-text-primary)">
      CUSTOMER_NAME — signals to configure
    </span>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">

    <!-- Included signals -->
    <div style="border:1px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);padding:14px 16px">
      <div style="font-size:11px;font-weight:500;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">
        Will be configured
      </div>
      <!-- Repeat the row below for each included signal -->
      <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px">
        <i class="ti ti-circle-check" style="font-size:16px;color:#00DF8F;flex-shrink:0;margin-top:2px" aria-hidden="true"></i>
        <div>
          <div style="font-size:13px;font-weight:500;color:var(--color-text-primary)">identification</div>
          <div style="font-size:11px;color:var(--color-text-tertiary)">Audience email — sign-in form</div>
        </div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px">
        <i class="ti ti-circle-check" style="font-size:16px;color:#00DF8F;flex-shrink:0;margin-top:2px" aria-hidden="true"></i>
        <div>
          <div style="font-size:13px;font-weight:500;color:var(--color-text-primary)">addToCart</div>
          <div style="font-size:11px;color:var(--color-text-tertiary)">Product added — ID, name, price, qty</div>
        </div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px">
        <i class="ti ti-circle-check" style="font-size:16px;color:#00DF8F;flex-shrink:0;margin-top:2px" aria-hidden="true"></i>
        <div>
          <div style="font-size:13px;font-weight:500;color:var(--color-text-primary)">order</div>
          <div style="font-size:11px;color:var(--color-text-tertiary)">Purchase — order ID, revenue, items</div>
        </div>
      </div>
      <!-- Repeat for every remaining signal in the canonical set (order, pageView, productView, onSiteSearch, productConfiguration, richMediaInteraction) -->
    </div>

    <!-- Signals the site cannot produce -->
    <div style="border:1px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);padding:14px 16px;opacity:.7">
      <div style="font-size:11px;font-weight:500;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">
        Not applicable to this site
      </div>
      <!-- Repeat the row below for each signal the site has no functionality for; omit this whole column when every signal applies -->
      <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px">
        <i class="ti ti-circle-minus" style="font-size:16px;color:var(--color-text-tertiary);flex-shrink:0;margin-top:2px" aria-hidden="true"></i>
        <div>
          <div style="font-size:13px;font-weight:500;color:var(--color-text-secondary)">richMediaInteraction</div>
          <div style="font-size:11px;color:var(--color-text-tertiary)">Video, podcast, download events</div>
        </div>
      </div>
    </div>

  </div>

  <div style="margin-top:12px;padding:10px 14px;background:var(--color-background-secondary);border-radius:var(--border-radius-md);font-size:12px;color:var(--color-text-secondary)">
    <i class="ti ti-info-circle" aria-hidden="true"></i>
    All signals are available on Pro, Premium, and Ultimate. Any signal shown as not applicable has no matching functionality on this site — it is skipped during inspection and excluded from the generated SDK config. Run a diff pass if the site adds it later.
  </div>
</div>
```

**Filling in the widget:**

- List all nine signals in the "Will be configured" column, in canonical order, for every tier.
- For `richMediaInteraction`, use a ⚠️ warning row instead of a ✅ check, with the subtitle "Skeleton only — requires site-specific manual enhance".
- Move a signal to "Not applicable to this site" only when the site demonstrably lacks that functionality (no cart, no search, no product pages, no media), and give the reason as the row subtitle. Omit that column entirely when every signal applies.
- Never omit a signal because of the tier — Pro, Premium, and Ultimate all get the full set.

Use "Audience email — sign-in form" as the subtitle for `identification` and "Audience email — registration form" for `accountRegistered`.

After rendering the widget, use `AskUserQuestion` to collect the remaining missing information (app key, collector URL, environment) as described in steps 1b–1e above.

Support these modes:

1. `guided`: No browser access; use customer-provided evidence and mark unverified mappings.
2. `website-assisted`: Inspect live pages and auto-capture SDK events via browser automation (default when browser tools are available).
3. `datalayer-assisted`: Inspect or accept pasted runtime dataLayer events.
4. `diff`: Compare an existing configuration with proposed mappings.

---

### 2. Auto-capture SDK events (website-assisted mode)

**Do this before building the evidence matrix.** For every key page type, inject the capture shim, read the automatic Type 2 event, discover interactive elements, simulate interactions to generate Type 4 events, and read the dataLayer. No user action required.

Read [references/auto-event-capture.md](references/auto-event-capture.md) for the full scripts. Summary per page:

```
Navigate to page
  → javascript_tool: inject capture shim (references/auto-event-capture.md Step 1)
  → javascript_tool: read window.__acoCapture.type2   ← page load, fires automatically
  → javascript_tool: discover elements (Step 3)
  → javascript_tool: simulate click on addToCart / search / formSubmit (Step 4)
  → javascript_tool: read window.__acoCapture.type4   ← interaction events
  → javascript_tool: read window.__acoCapture.dataLayer ← any dataLayer pushes
  → javascript_tool: window.__acoCapture.type4 = []   ← clear before next page
```

**Pages to cover — driven by what the site has, not by tier:**

| Page type | URL pattern | Key interaction | Visit when |
|---|---|---|---|
| Homepage | `/` | None (Type 2 only) | Always |
| Sign-in | `/login` or `/account/signin` | Fill email field → `change` event → identification signal | Site has a sign-in form |
| Registration form | `/register`, `/signup`, `/create-account` | Confirm email field exists; `change` event stores email for accountRegistered | Site has a registration form |
| Registration success | `/register/success`, `/account/created` | LOAD event → accountRegistered fires with stored email | Site has a registration flow |
| Product listing page (PLP) | `/category/...` | None (Type 2 only) | Site has category or listing pages |
| Product display page (PDP) | `/product/...` | Add-to-cart click | Site sells products |
| product display page (PDP) — variant interactions | `/product/...` | Colour/size/qty interactions for productConfiguration | Product pages have variant selectors |
| Search results | `/search?q=...` | None (navigate with query — Type 2 captures param) | Site has on-site search |
| Cart | `/cart` or `/basket` | None (Type 2 only) | Site has a cart |
| Checkout | `/checkout/...` | **Staging only:** complete transaction with test card | Site has a checkout |
| Order confirmation | `/order-confirmation` | **Staging only:** read full dataLayer for order signal fields | Site has a checkout |
| Rich media | Any page with video/podcast/download | Media play / download click | Site has video, podcast, or downloadable media |

> Page coverage is not tier-gated — Pro, Premium, and Ultimate customers all get the full sweep. Skip a row only when the site has no such page, and record the omission in `inspection.findings[]`.

---

### Step 2a — Category Classification (mandatory, runs after homepage capture)

> ⛔ **HARD GUARDRAIL:** Step 2a must run before any further page inspection. Navigate to the homepage, inject the capture shim, and read the Type 2 event as normal — then immediately run the category detection below before navigating to any other page. Writing `profile.customer.siteCategory` is a prerequisite for correct signal semantics throughout the rest of the session.

**Step 2a-1 — Read the category reference into context**

Read `references/site-category-context.md` in full before running any detection. This file contains the 14-category detection checklist and the semantic definitions for each category. Do not skip this read — the detection logic and signal semantics live in that file, not in this skill.

**Step 2a-2 — Run the detection script against the live homepage**

After the homepage Type 2 capture, run this JavaScript to extract the signals needed for the 14-check priority checklist:

```js
await new Promise(r => setTimeout(r, 500));
const signals = {
  domain: location.hostname,
  pathname: location.pathname,
  title: document.title,
  h1: document.querySelector('h1')?.innerText?.trim()?.substring(0, 200) || '',
  metaDesc: document.querySelector('meta[name="description"]')?.content?.substring(0, 300) || '',
  ogType: document.querySelector('meta[property="og:type"]')?.content || '',
  // DOM pattern checks
  hasTicketSelector: !!(document.querySelector('[class*="ticket"],[id*="ticket"],[data-event-id],[class*="seat"],[class*="performance"]')),
  hasDonationForm: !!(document.querySelector('form[action*="donat"],input[name*="donat"],[class*="donat"],[id*="donat"],[class*="fundrais"]')),
  hasApplicationForm: !!(document.querySelector('form[class*="applic"],input[name*="application"],[class*="apply-"],[href*="/apply"]')),
  hasInsuranceTerms: document.body.innerText.match(/\b(premium|deductible|coverage|policy|claim|underwr)\b/i) !== null,
  hasLoanTerms: document.body.innerText.match(/\b(APR|interest rate|mortgage|borrow|loan|repayment|overdraft)\b/i) !== null,
  hasMembershipTerms: !!(document.querySelector('[class*="membership"],[class*="member-plan"],[href*="/membership"],[href*="/join"]')),
  // dataLayer ecommerce event name hints
  dataLayerEvents: (() => { try { return (window.dataLayer||[]).filter(e=>e.event).map(e=>e.event).slice(0,20); } catch(e) { return []; } })(),
  // Platform hints from page source
  shopifyPresent: !!(window.Shopify),
  bigCommercePresent: !!(window.BCData || document.querySelector('[data-entity-id]')),
  wooCommercePresent: !!(document.querySelector('.woocommerce')),
};
JSON.stringify(signals, null, 2);
```

**Step 2a-3 — Apply the detection checklist (priority order)**

Using the output from Step 2a-2 and the checklist from `references/site-category-context.md`, determine the category. Apply checks in priority order (1 → 14), stopping at the first match:

| Priority | Match condition | Category |
|---|---|---|
| 1 | `hasTicketSelector` true, or title/h1/meta contains "tickets", "performances", "shows", "theatre" | `performing-arts` |
| 2 | Domain or h1/meta contains "hospital", "clinic", "health", "medical", "doctor", "patient" | `healthcare` |
| 3 | `hasDonationForm` true, or h1/meta contains "donate", "fundrais", "charity", "nonprofit" | `nonprofit-fundraising` |
| 4 | `hasInsuranceTerms` true and domain/meta contains "insur", "protect", "cover" | `insurance` |
| 5 | `hasLoanTerms` true, or domain/title contains "bank", "finance", "credit", "mortgage", "loan" | `financial-services` |
| 6 | `hasMembershipTerms` true, or title/meta contains "membership", "join", "subscribe", "association" | `membership-association` |
| 7 | Title/h1/meta contains "course", "curriculum", "textbook", "learning", "e-learn", "publish" | `education-publishing` |
| 8 | Title/h1/meta contains "oracle", "tarot", "spiritual", "crystal", "wellness", "holistic" | `spiritual-wellness-ecommerce` |
| 9 | Title/h1/meta contains "resort", "hotel", "golf", "spa", "lodge", "hospitality", "stay" | `hospitality-travel` |
| 10 | Title/h1/meta contains "broadband", "mobile plan", "telecom", "ISP", "utility", "energy plan" | `telecom-utilities` |
| 11 | `hasApplicationForm` true, or title/meta contains "apply for", "become a", "dealer", "franchise", "pub lease" | `b2b-application-portal` |
| 12 | Title/meta contains "advertis", "media kit", "lead gen", "CPM", "publisher", "ad network" | `media-leadgen` |
| 13 | `shopifyPresent`, `bigCommercePresent`, `wooCommercePresent` true, OR no other check matched and a standard ecommerce dataLayer event (`add_to_cart`, `purchase`, `view_item`, `addToCart`) is in `dataLayerEvents` | `standard-ecommerce` |
| 14 | No match | `unknown` |

**Step 2a-4 — Write siteCategory to the profile**

```python
import json, pathlib, glob as _glob

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
profile.setdefault('customer', {})
profile['customer']['siteCategory'] = '<determined-category-slug>'
profile_path.write_text(json.dumps(profile, indent=2))
print('siteCategory:', profile['customer']['siteCategory'])
```

**Step 2a-5 — Handle result**

- **Known category (any slug except `unknown`):**
  - Load the matching category section from `references/site-category-context.md` into active context. This defines what "product", "addToCart", "order", and related concepts mean for the rest of the session. Do not apply `standard-ecommerce` semantics when a different category is active.
  - Emit a single status line: `"Site classified as <Category Name> — loading category signal semantics."`
  - Continue to the next inspection page without stopping.

- **`unknown` (no check matched):**
  - Stop immediately. Do not proceed to any further page inspection.
  - Show a `category_unknown` blocker widget using `mcp__visualize__show_widget` (title: `category_unknown`, loading: `"Loading…"`). Substitute `DOMAIN` with the actual domain and `SIGNALS_LIST` with the signals that will be configured for this site.

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:440px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1rem">
    <div style="width:40px;height:40px;border-radius:50%;background:#FFF3CD;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:20px">❓</div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Site category could not be detected</div>
      <div style="font-size:12px;color:var(--color-text-secondary);margin-top:4px;line-height:1.5">
        <strong>DOMAIN</strong> did not match any of the 14 known site categories. Signal field semantics (productId, productName, order, etc.) depend on site type — please confirm the category before inspection continues.
      </div>
    </div>
  </div>
  <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px;font-size:11px;color:var(--color-text-secondary);margin-bottom:14px">
    <strong>Categories available:</strong> standard-ecommerce · performing-arts · healthcare · nonprofit-fundraising · insurance · financial-services · membership-association · education-publishing · spiritual-wellness-ecommerce · hospitality-travel · telecom-utilities · b2b-application-portal · media-leadgen
  </div>
  <div style="margin-bottom:8px">
    <select id="cat-sel" style="width:100%;padding:8px 10px;border:1px solid var(--color-border-tertiary);border-radius:6px;font-size:12px;background:var(--color-background-secondary);color:var(--color-text-primary);font-family:var(--font-sans)">
      <option value="">— Select a category —</option>
      <option value="standard-ecommerce">Standard ecommerce (physical goods)</option>
      <option value="performing-arts">Performing arts / ticketing</option>
      <option value="healthcare">Healthcare / clinic / hospital</option>
      <option value="nonprofit-fundraising">Non-profit / fundraising / donation</option>
      <option value="insurance">Insurance</option>
      <option value="financial-services">Financial services / banking / loans</option>
      <option value="membership-association">Membership / association / subscription</option>
      <option value="education-publishing">Education / publishing / e-learning</option>
      <option value="spiritual-wellness-ecommerce">Spiritual / wellness ecommerce</option>
      <option value="hospitality-travel">Hospitality / travel / resort</option>
      <option value="telecom-utilities">Telecom / ISP / utilities</option>
      <option value="b2b-application-portal">B2B application portal</option>
      <option value="media-leadgen">Media / lead-gen / advertising</option>
    </select>
  </div>
  <button onclick="var v=document.getElementById('cat-sel').value;if(!v){alert('Please select a category.');return;}sendPrompt('Site category confirmed: '+v);"
    style="width:100%;padding:10px 16px;background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit">
    Confirm and continue
  </button>
</div>
```

When `sendPrompt` fires `'Site category confirmed: <slug>'`: parse the slug, write it to `profile.customer.siteCategory`, load the matching section from `references/site-category-context.md`, then continue inspection from the next page (do not re-navigate to the homepage).

> **Confidence note:** The detection checklist is heuristic. If the detected category seems wrong (e.g. a general wellness blog matched `spiritual-wellness-ecommerce`), the operator can override it by selecting a different category in the widget — even when a category was auto-detected. The `category_unknown` widget is only shown when no check matched.

---

**accountRegistered — onboarding checklist:**
1. Navigate to the registration form page. Confirm an `input[type="email"]` or `input[name="email"]` is present. Note the exact URL path.
2. Navigate to the registration success/confirmation page. Note the exact URL path.
3. Update `signals.accountRegistered.formUrlPatterns` and `signals.accountRegistered.successUrlPatterns` in the profile with the confirmed paths.
4. If the site uses SSO-only registration (no email field), set `signals.accountRegistered.registrationMethod` to the SSO provider name (e.g. `"google"`) and note that email capture is unavailable — the signal will fire without audience.Email.

**Safety rules for interaction simulation:**
- Only click visible elements (`offsetParent !== null`).
- Never simulate clicks on: payment/confirm/place-order buttons, login forms, or any checkout step.
- Add-to-cart clicks will add a real item on live sites. This is expected and accepted on both staging and production — simulate silently and navigate away immediately. **Never pause to ask the user for permission** (see add-to-cart HARD GUARDRAIL in Execution discipline above).
- Never submit forms containing email, password, or payment fields.

---

### 3. Check for dataLayer events

Immediately after each simulated interaction, read the dataLayer capture buffer:

```js
window.__acoCapture.dataLayer.filter(e => e.event).map(e => e.event)
```

**Decision tree — trigger type per signal:**

```
dataLayer push observed for this interaction?
  YES → triggerType: "dataLayer", dataLayerEvent: "<event name>"
        Set inspection.dataLayerAvailable = true
        Add event name to inspection.dataLayerEvents[]
        → dataLayer trigger always wins over click trigger
  NO  → Type 4 click event captured?
          YES → triggerType: "click"
                triggers from Type 4 target attributes (innerText > class > id)
                Entity IDs from target.id stripped of prefix in enhance function
          NO  → triggerType: "load" with page-URL guard in enhance
                Mark as "Requires customer dataLayer/API/event payload"
```

Set `inspection.dataLayerAvailable` in the profile:
- `true` — dataLayer array confirmed present
- `false` — not present
- `null` — not yet checked

#### Ecommerce dataLayer discovery (required for productView, addToCart, order)

**When `dataLayerAvailable` is true**, run the ecommerce discovery script from `references/auto-event-capture.md` (Step 7) on the product display page (PDP), cart, and order confirmation pages. This script:

1. Scans `window.dataLayer` for any event with an `ecommerce` property
2. Identifies the schema — `"ga4"` (`ecommerce.items[]`) or `"ua"` (`ecommerce.detail/add/purchase.products[]`)
3. Maps event names to signals — these differ per client (e.g. some sites use `"productDetailView"`, GA4 sites use `"view_item"`)
4. Shows the actual field names on the item objects (`id` vs `item_id`, `name` vs `item_name`, etc.)

Populate the profile with the results:

```json
"inspection": {
  "dataLayerAvailable": true,
  "ecommerceSchema": "ua",
  "ecommerceEventMap": {
    "productView": "productDetailView",
    "addToCart": "addToCart",
    "order": "purchase",
    "removedFromCart": ""
  }
}
```

The generator then automatically:
- Adds all discovered event names to `GAeventsAllowList`
- Sets each signal's trigger to `{ "customEvent.data.event": "<eventName>" }`
- Uses the correct item nesting path (`ecommerce.detail.products[]` for UA, `ecommerce.items[]` for GA4)
- Tries both GA4 and UA field name conventions (`item_id || id`, `item_name || name`, etc.)

If `dataLayerAvailable` is `false` or the ecommerce discovery returns nothing, fall back to click-based triggers for addToCart and DOM/JSON-LD extraction for productView.

#### removedFromCart discovery (within the cart page visit)

**After capturing the add-to-cart event on the product display page (PDP)**, navigate to the cart page and run:

```js
// Clear the dataLayer capture buffer first
window.__acoCapture.dataLayer = [];
// Then: remove one item from the cart (click the × / remove / delete button)
// Wait 1 second
window.__acoCapture.dataLayer.filter(e => e.event).map(e => ({event: e.event, ecommerce: e.ecommerce}))
```

Also try reducing an item's quantity to zero via the quantity input if present:
```js
window.__acoCapture.dataLayer = [];
// Reduce qty input to 0 and trigger change
```

**Decision:**
- If a dataLayer push fires with an event name containing "remove" / "cart" / "delete" → set `ecommerceEventMap.removedFromCart` to that event name. The generator adds it to `GAeventsAllowList` and generates the dual-branch `addToCart` / `removedFromCart` enhance.
- If no dataLayer push fires → leave `removedFromCart` empty. Document as `⚠️ Not verified — no dataLayer push detected for cart removal` in the implementation review's questions array.
- Note: the trigger may be different for "remove item entirely" vs "reduce quantity". If both fire different events, use the "remove entirely" event name as `removedFromCart`; note the quantity-reduce case separately.

---

### 4. Map captured events to signal configuration

**From Type 2 events → pageCategoryRules**

Each Type 2 `screenview.url` gives a confirmed URL path. Build `pageCategoryRules` from the observed patterns:
- `"^/$"` → homepage
- `"^/product/"` or `"^/01/details/"` → product
- `"^/search"` or `"^/02/fts/"` → search
- etc.

Also extract: search query parameter name from `screenview.queryParams`, page title pattern for `pageView.name`.

**From Type 4 events → triggers for click-triggered signals**

For each Type 4 captured during a simulated click, build the `triggers` entry using the preference order:

1. `target.attributes.innerText` — fixed button label (e.g. "Add To Bag"). **Most stable.**
2. `target.attributes.class` — stable CSS class (e.g. `"item__atb buyButton"`).
3. `target.id` — only if static. Dynamic IDs (e.g. `"buy_NN31219"`) should be used for entity extraction in the enhance function, not for event matching.

Example — auto-generated from a captured Type 4:
```json
{
  "triggers": [
    {
      "attributes": {
        "event.type": "click",
        "target.attributes.innerText": "Add To Bag"
      },
      "label": "addToCart — auto-captured Type 4"
    }
  ]
}
```

When `target.id` encodes an entity ID (e.g. `"buy_NN31219"`), document the strip transform needed in the enhance function. Add this as a post-generation manual edit:
```js
// In addToCart enhance function:
const rawId = help.webEvent?.target?.id || help.cssGet("[id^='buy_']","id") || '';
signal.productId = rawId.replace(/^buy_/, '') || (help.jsonLdGet('0.sku')||'').split('/')[0] || null;
```

---

### 5. Inspect page structure

For each page, run the standard DOM evidence script from [references/browser-inspection.md](references/browser-inspection.md) to collect JSON-LD, metadata, field names, and available product data. This feeds the signal field mappings (productId, productName, unitPrice, etc.) — separate from the trigger configuration in step 4.

Source priority for field values:

1. JSON-LD (highest confidence)
2. dataLayer captured value
3. Open graph / meta tags
4. Stable DOM selector (`data-*`, semantic ID, ARIA, field name)
5. URL path segment or query param
6. Confirmed static fallback

---

### 6. Build the evidence matrix

Create one row per signal attribute with:

- Signal, Attribute, Required/optional
- Source type, Extraction logic, Example value
- Confidence (0–100), Status, Risk/notes, Evidence URL

Allowed statuses:

- `Found automatically` — confirmed from live page or captured event
- `Inferred with confidence` — logical derivation with high confidence
- `Needs confirmation` — plausible but unverified
- `Not available on page` — source does not exist on this page type
- `Requires customer dataLayer/API/event payload` — data only available after authenticated action

Never present an inferred value as automatically found.

---

### 7. Resolve consequential gaps

Ask focused questions when the answer changes signal semantics, privacy, or production behavior:

- Whether a success page is the conversion point
- Whether a B2B action maps to `addToCart`, `order`, `formSubmit`, or a combination
- Whether email may be stored in sessionStorage and attached to `audience.Email`
- Whether staging must remain in fake/test mode
- Whether a staging environment and test card details are available for order signal capture

Continue with explicit TODOs for non-blocking gaps.

---

### 8. Create a website profile

#### Product journey integrity check

Before populating the profile, verify that the `productId` and `productName` captured for each signal will resolve to the **same value** for a given product on that customer's site.

If productView fires with `productId: "NN31157"` but addToCart fires with `productId: "NN31157/M"` (variant-suffixed), or order fires with `productId: "nn31157"` (lowercase), Acoustic treats these as three different products. The shopper appears to have viewed one product, added a second, and purchased a third — making journey analytics meaningless.

On the product display page (PDP), before building the profile, note the actual value each signal source would produce and check they match:

```
productView  → dataLayer item.id       → "NN31157"   ← note this value
addToCart    → dataLayer item.id       → "NN31157"   ✅ matches
productConfig→ data-product stripped   → "NN31157"   ✅ matches  (or ⚠️ "NN31157/M" if not stripped)
order        → dataLayer orderedItem.id→ "NN31157"   ✅ matches
```

If values would differ, document the mismatch in `questions` before generating. The generator will flag it in the implementation review.

If the skill cannot confirm a match (e.g. order confirmation uses a different SKU format, or the site wasn't accessible on staging), note it as an open item — the implementation review will include a ⚠️ product ID consistency warning.

Copy `assets/website-profile.template.json` into the output directory and populate it from confirmed evidence. Use auto-captured Type 2 and Type 4 data to fill `pageCategoryRules` and signal `triggers`. Keep customer rules isolated from the reusable SDK engine.

---

### 8b. Inspection complete gate — MANDATORY

> **GUARDRAIL: Do NOT proceed to Step 9 without completing this gate.** This step is required every time inspection finishes, whether the inspection was a full new-customer run or a re-inspection pass. Skipping it is a skill defect.

After writing the profile, render an inspection summary widget using `mcp__visualize__show_widget` (title: `inspection_complete`, one loading message: `"Summarising inspection"`).

The widget must show:
- **Customer name and tier**
- **Pages inspected** — list each page type with a ✅ (evidence captured) or ⚠️ (could not verify)
- **Signals ready to generate** — list signals with confirmed triggers (green ✅)
- **Blockers** — list any entries from `profile.blockers[]` with a ⚠️ badge and the plain-language `summary` (not the `resolution` — keep it short). Use severity to colour: high = red/amber, medium = amber, low = grey.
- **Recommended next step** — always "Generate SDK config (test mode)" unless all signals are blocked

Then use `AskUserQuestion` to ask:

**"All pages have been inspected. What would you like to do next?"**

Options:
- **"Generate SDK config now"** — proceed to Step 9. The SDK config will be generated in test mode (signals print to console only — no data is sent).
- **"Pause — I need to resolve blockers first"** — stop here. Display the blockers list from `profile.blockers[]` with the `resolution` text for each. Tell the user: "Come back and say 'Generate SDK config' when you're ready and I'll continue from here."

> If the user selects "Generate SDK config now" but there are high-severity blockers, proceed but flag the blocked signals in the implementation review as `⚠️ Requires customer input before production`.

---

### 9. Validate and generate

> **⛔ HARD STOP — Step 8b gate is a prerequisite.** Before calling `validate_profile.py` or `generate_sdk.py`, confirm that Step 8b has been completed in this session — both the `show_widget` inspection summary AND the `AskUserQuestion` gate must have been presented and the user must have selected "Generate SDK config now". If Step 8b was not completed, stop and run it now. Running the generator without the Step 8b gate is a skill defect.

Before running the generator, confirm the website profile `signals` block contains **only signals the site actually supports**. Remove entries for signals with no matching site functionality entirely rather than leaving them empty or commented out — this prevents the generator emitting dead code.

There is no tier-based removal: every signal is available on Pro, Premium, and Ultimate, so a signal is dropped only on site evidence (no cart, no search, no product pages, no media), and the reason belongs in `inspection.findings[]`.

**Step A — Confirm signal mode**

> #### ⚠️ LOGGING FLAG GUARDRAIL — TWO STATES ONLY. NEVER DEVIATE.
>
> | Flag | Test (first generation) | Production (after validation confirmed) |
> |------|------------------------|----------------------------------------|
> | `errorLog` | `true` | `false` |
> | `eventLog` | `false` | `false` |
> | `signalsLog` | `true` | `true` (always) |
> | `fakeSignals` | `true` | `false` |
>
> - **First generation always uses test mode** — do NOT ask the user; default to `settings.mode = "test"` without prompting.
> - **Switch to production only** when the user confirms validation is complete via the "Yes — push to production" option in the validation gate (Step 9). Never set `fakeSignals: false` before that confirmation.
> - The generator (`generate_sdk.py`) enforces these values automatically via regex substitution — do not manually patch these flags in the generated JS.

Set `settings.mode` in the website profile JSON before running the generator:

```python
import json, pathlib
profile_path = pathlib.Path("/absolute/path/website-profile.json")
profile = json.loads(profile_path.read_text())
profile["settings"]["mode"] = "test"   # always for first generation
profile_path.write_text(json.dumps(profile, indent=2))
```

**Step B — Validate and generate**

The generator uses `assets/initLogSignal.js` (committed to the repo) as its base — no CDN fetch required on a fresh clone. Always use `scripts/generate_sdk_patched.py` (not `generate_sdk.py`) — the patched version resolves additional field-source formats, enforces the TODO hard-block, injects the audience signal, and updates privacy targets automatically.

```bash
python3 scripts/validate_profile.py /absolute/path/website-profile.json
PYTHONPATH=scripts python3 scripts/generate_sdk_patched.py \
  /absolute/path/website-profile.json \
  --base-js assets/initLogSignal.js \
  --out /absolute/path/output-directory
```

> **`assets/initLogSignal.js` missing or needs refreshing?** The bash sandbox has no outbound internet access, so do NOT use `curl`, Python `requests/urllib`, or `mcp__workspace__web_fetch` to fetch it — those will all fail or be blocked. Use Chrome instead:
>
> 1. `mcp__Claude_in_Chrome__navigate` to the CDN URL below
> 2. `mcp__Claude_in_Chrome__get_page_text` on that tab — this returns the full JS source
> 3. Write the returned content to `assets/initLogSignal.js`
>
> **Never use `javascript_tool` to read the file** — the Chrome extension's content filter blocks raw JS content. `get_page_text` is the only Chrome tool that works for this.
>
> CDN URL: `https://content-eu-1.content-cms.com/7fbff3c6-1b3b-4a7d-a64e-c8ebc38fa3df/dxdam/35/35cc26b5-a0ec-4e55-8c8e-a42b40cc54e1/initLogSignal.js`
>
> **Never use `sdk-template.js` as `--base-js`** — it lacks the signal key blocks the generator requires and will produce a broken, doubled SDK output.

Fix validation errors. Report warnings as review items.

**Step C — TODO scan and hard-block (automatic in generate_sdk_patched.py)**

> ⛔ **HARD GUARDRAIL — a generated config containing any `// TODO:` lines is not valid output. `generate_sdk_patched.py` exits with code 2 if any `// TODO:` lines remain. The config file is not written. You must resolve the root cause and regenerate — never present a TODO-containing config to the customer.**

`generate_sdk_patched.py` enforces this automatically — if it exits with code 2, resolve the root cause:

1. Run `grep -n "// TODO:" /absolute/path/acoConnectSdkConfig-<slug>.js` to identify which signals and fields are unresolved. (The file may be partially written — check if it exists.)
2. For each unresolved field, diagnose the root cause:
   - **`enabled: null` on the signal** — set `enabled: true` in the profile for all signals that should be active.
   - **Unrecognised `triggerType`** — add the trigger manually to `profile.signals.<key>.triggers[]` as `{ "attributes": { "event.type": "change", "target.name": "<name>" } }`.
   - **Unrecognised field `source` type** — check the field spec in the profile; valid source types are `dataLayer`, `type2`, `type4`, `jsonLd`, `webEvent`, `domText`, `domAttr`, `meta`, `url`, `urlSlug`, `sessionStorage`, `fallback`. Correct the profile field.
   - **Profile field in flat format** — the patched generator handles flat `{ "source": "...", "path": "..." }` automatically. If a TODO still appears, the field may have a malformed or missing `source` key.
3. Update the profile, then re-run `generate_sdk_patched.py`. Repeat until exit code is 0.
4. **Never edit `// TODO:` lines directly in the config** — fix the root cause in the profile so regeneration is reproducible.

> Every `// TODO: map signal.*` line is a field that sends nothing to Acoustic — a complete capture failure for that signal field.

**Step D — Automatic config enhancements (generated by generate_sdk_patched.py)**

These are injected automatically on every generation run — no manual steps required.

**D-1: Audience utility signal**

When `identification` is enabled in the profile, the generator injects an `audience` signal into `cfg.signals`. This signal:

- Fires on the confirmed email field's `change` event (using `target.id` if confirmed, otherwise `target.name`)
- Captures the typed email via `help.webEvent.target.currState.value`
- Validates format and stores via `help.store("audience", { Email: rawEmail })`
- Page-guarded to the sign-in and registration URLs confirmed during inspection
- **Always overwrites** — keeps sessionStorage current with the latest typed value so every signal posts the most recent email in its `audience` object
- **Always returns `false`** — it is NOT an Acoustic Connect signal and is never logged to the platform

> ⚠️ **Customer note (include in implementation review):** The `audience` signal block is a utility injected by the Acoustic onboarding SDK. It does not appear in the Acoustic Connect signal catalogue and is not tracked as a platform signal. Its sole purpose is to capture and persist the customer's email address so all other signals can include it in their `audience` object, enabling identity resolution across the session.

Other signals retrieve the stored email via:
```javascript
signal.audience = help.retrieve('audience') || {};
```

**D-2: Privacy targets update**

When `identification` is enabled, the generator adds the confirmed email field selectors (e.g. `[name="Email"]`, `#Email`) to the `config.services.message.privacy` targets list. These selectors are added to the existing `exclude: true / maskType: 2` rule — meaning those specific fields are **captured without masking**. Without this update the email field value appears as `XXXXX` in Tealeaf replay and the identification signal cannot read it.

---

### DataLayer signal convention — always use dlListener

**Never monkey-patch `dataLayer.push` manually.** The built-in `dlListener` module in `initLogSignal.js` already patches `dataLayer.push` — use it.

**Required cfg settings whenever any signal has `triggerType: "dataLayer"`:**

```js
GAdataLayerName: "dataLayer",          // customer's dataLayer variable name
GAeventsAllowList: ["event1", "event2", ...],  // ALL events any signal needs, incl. gtm.historyChange
messageTypes: [..., "dlListener"],     // generator adds this automatically
```

**Trigger attribute format for dataLayer signals:**

```js
// ✅ Correct — uses dlListener dot-notation path
triggers: [{ attributes: { "customEvent.data.event": "ee-productView" } }]

// ❌ Wrong — top-level "event" key never matches a Type 5 dlListener message
triggers: [{ attributes: { "event": "ee-productView" } }]
```

**Accessing event data in enhance functions:**

```js
enhance: function(signal, help) {
    const dlData = help.webEvent?.customEvent?.data; // full dataLayer push object
    const ec = dlData?.ecommerce;                    // ecommerce sub-object (UA/GA4)
    const items = ec?.detail?.products || ec?.items || [];
}
```

**productConfiguration on sites where it shares the same dataLayer event as productView** (e.g. SPA colour-change nav fires `gtm.historyChange` then re-fires `ee-productView`):

Add `"gtm.historyChange"` to `GAeventsAllowList`. Use two triggers on productConfiguration — one for `gtm.historyChange` to set a flag, one for the product event to fire the signal:

```js
triggers: [
    { attributes: { "customEvent.data.event": "gtm.historyChange" } },
    { attributes: { "customEvent.data.event": "ee-productView" } }
],
enhance: function(signal, help) {
    const ev = help.webEvent?.customEvent?.data?.event;
    if (ev === 'gtm.historyChange') { window.__acoColourChange = true; return false; }
    if (!window.__acoColourChange) return false;
    window.__acoColourChange = false;
    // ... populate signal fields from ecommerce data ...
    return signal;
}
```

productView's enhance function simply checks `if (window.__acoColourChange) return false;` to skip colour-change fires.

---

### Built-in functions — exhaust all before adding custom code

`initLogSignal.js` provides a full set of built-in capabilities. **Never write custom JavaScript workarounds until every relevant built-in has been evaluated and ruled out.**

#### Built-in `help.*` functions (available in every enhance function)

| Function | What it returns | Example |
|---|---|---|
| `help.cssGet(selector, attr?)` | Attribute value or `innerHTML` of the first matching DOM element | `help.cssGet("meta[property='og:title']", "content")` |
| `help.jsonLdGet(path)` | Field from the page's JSON-LD block | `help.jsonLdGet("0.sku")`, `help.jsonLdGet("0.offers.price")` |
| `help.webEvent` | The raw triggering event object | — |
| `help.webEvent?.customEvent?.data` | Full dataLayer push object (dlListener signals) | `const ec = help.webEvent?.customEvent?.data?.ecommerce` |
| `help.webEvent?.customEvent?.name` | Event module name (e.g. `"dlListener"`) | — |
| `help.webEvent?.target?.id` | ID of the clicked element | — |
| `help.webEvent?.target?.attributes` | Attribute map of the clicked element (`class`, `innerText`, etc.) | — |
| `help.audience` | Stored audience data (email, etc.) | `help.audience?.Email` |
| `help.currentUrl` | Current page URL as a string | `help.currentUrl` |

#### Built-in initLogSignal modules / features

| Feature | How to activate | Notes |
|---|---|---|
| `dlListener` | `messageTypes: [..., "dlListener"]`, `GAdataLayerName`, `GAeventsAllowList` | Patches `dataLayer.push` — never re-patch manually |
| Page triggers (load) | `triggers: [{ attributes: { "event.type": "load" } }]` | Fires on every screenview for this signal |
| Click triggers | `triggers: [{ attributes: { "event.type": "click", "target.attributes.innerText": "Add To Bag" } }]` | Matches Type 4 events |
| dataLayer triggers | `triggers: [{ attributes: { "customEvent.data.event": "ee-productView" } }]` | Matches Type 5 dlListener events |
| pageCategoryRules | Array of `{ regex, pageType }` objects in top-level cfg | URL-based page classification |
| URL parameter extraction | `new URLSearchParams(location.search).get("q")` (inside enhance) | No custom code needed |
| Audience propagation | `signal.audience = help.audience` | Reuses stored audience without re-capture |

#### Decision checklist before adding any custom code

Run through each question in order. Stop at the first **YES** and use that built-in instead.

1. Can `help.cssGet()` read the value from a DOM element? → Use `help.cssGet()`
2. Can `help.jsonLdGet()` extract the value from JSON-LD? → Use `help.jsonLdGet()`
3. Does dlListener already capture the value in `help.webEvent?.customEvent?.data`? → Read from `dlData`
4. Can a `pageCategoryRules` regex handle the page classification? → Add to `pageCategoryRules`
5. Can trigger attribute matching (click / load / dlListener) handle the event selection? → Use `triggers`
6. Can `new URLSearchParams(location.search).get()` or `window.location.*` provide the value? → Use inline
7. Can `help.audience.*` supply stored user data? → Use `help.audience`

Only if **all seven are NO** may custom code be added.

#### What does NOT count as custom code

The two-trigger productConfiguration pattern is **fully built-in** — both triggers use dlListener, which is a native `initLogSignal.js` module:

```js
// Both triggers use the built-in dlListener mechanism — no custom code
triggers: [
    { attributes: { "customEvent.data.event": "gtm.historyChange" } },  // built-in dlListener
    { attributes: { "customEvent.data.event": "ee-productView" } }       // built-in dlListener
],
enhance: function(signal, help) {
    const ev = help.webEvent?.customEvent?.data?.event;
    if (ev === 'gtm.historyChange') { window.__acoColourChange = true; return false; }
    if (!window.__acoColourChange) return false;
    window.__acoColourChange = false;
    // ...
}
```

`window.__acoColourChange` is coordination logic between two built-in triggers — it is **not** custom code and does **not** require disclosure. The `window.__aco*` namespace is reserved for this pattern.

#### Rules for unavoidable custom code

Custom code is anything that adds capability the built-in modules cannot provide — e.g. MutationObserver, XHR intercepts, DOM polling, or monkey-patching APIs other than `dataLayer`. When custom code is the only option:

- **Scope it narrowly** — inside the specific signal's `enhance` function only. Never add global utilities or helper closures outside an enhance function.
- **Prefix global flags with `window.__aco`** if a cross-enhance flag is unavoidable. This avoids collisions with the customer's own globals.
- **Document it** — add a comment explaining why no built-in could be used: `// Custom: no dlListener event fires here; using MutationObserver because the cart count updates silently via XHR`
- **Flag it in the final response** — see the custom code disclosure requirement in the Final response section below.

---

> #### ⚠️ OUTPUT NAMING GUARDRAIL — NEVER DEVIATE FROM THIS STRUCTURE
>
> All generated output files must follow this exact naming convention. Do not invent alternative names, do not use customer name slugs for the JS files, do not add suffixes like `-full-sdk` or `-tampermonkey`.
>
> | File | Pattern | Example (Acme Retail) |
> |------|---------|---------------|
> | SDK config | `acoConnectSdkConfig-{domain-slug}.js` | `acoConnectSdkConfig-acmeretail.js` |
> | Tampermonkey config | `acoConnectSdkConfig-{domain-slug}.tamperMonkeyConfig.js` | `acoConnectSdkConfig-acmeretail.tamperMonkeyConfig.js` |
> | Signal config JSON | `{customer-slug}-customer-signal-config.json` | `acme-retail-us-customer-signal-config.json` |
> | Implementation review | `{customer-slug}-implementation-review.md` | `acme-retail-us-implementation-review.md` |
>
> **`domain-slug`** = derived from `customer.productionDomain` by stripping `www\d*.` prefix and taking the first label: `www2.acmeretail.com` → `acmeretail`, `www.northwindtrading.co.uk` → `northwindtrading`. This is handled by `domain_slug()` in `generate_sdk.py`.
>
> **`customer-slug`** = slugified `customer.name` (hyphens, lowercase): `Acme Retail US` → `acme-retail-us`. Used only for non-JS files.
>
> If you ever see output files named differently (e.g. `acme-retail-us-full-sdk.js`, `acme-retail-us-tampermonkey.user.js`), the generator is not being called correctly or `generate_sdk.py` has drifted from the standard. Stop and fix `generate_sdk.py` before proceeding.
>
> **PROFILE JSON IS NEVER SHOWN TO THE USER.** The website profile JSON (`<customer-slug>.json` in the `profiles/` directory) is an internal artifact — it must NEVER be passed to `mcp__cowork__present_files` or shared as an output. It is saved silently in the background only. The only files presented to the user via `mcp__cowork__present_files` are the three deliverables: `acoConnectSdkConfig-<domain-slug>.js`, `acoConnectSdkConfig-<domain-slug>.tamperMonkeyConfig.js`, and `<customer-slug>-implementation-review.md`.

The generator produces:

- `acoConnectSdkConfig-<domain-slug>.js` — configured SDK config; `<domain-slug>` is derived from the production domain (e.g. `www2.acmeretail.com` → `acmeretail`)
- `acoConnectSdkConfig-<domain-slug>.tamperMonkeyConfig.js` — lightweight Tampermonkey `@require` script (loads the config from disk; no SDK code inlined)
- `<customer-slug>-customer-signal-config.json`
- `<customer-slug>-implementation-review.md`

**After generation — persist SDK config state to profile**

Immediately after a successful generation, write the config state back to the website profile so the skill can resume from the validation step on a future run without re-running the full onboarding:

```python
import json, pathlib, datetime, glob as _glob

# Locate the persistent profiles directory
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not _dirs:
    raise SystemExit('Profiles root not found — no folder added to this session. Re-run the Pre-step storage check.')
profiles_dir = pathlib.Path(_dirs[0])
profile_path = profiles_dir / '<SLUG>.json'
profile = json.loads(profile_path.read_text())

profile.setdefault("acoustic", {})
profile["acoustic"]["sdkBundle"] = {
    "path": str(profiles_dir.parent / "output" / f"<SLUG>-<tier>" / "acoConnectSdkConfig-<slug>.js"),
    "generatedAt": datetime.datetime.utcnow().isoformat(),
    "mode": "test",
    "validated": False
}

# Initialize per-signal status tracking — non-destructive: preserve existing attempt history
# attempts: number of correction attempts actually performed for this signal (incremented only when re-inspection/correction runs, never on issue selection)
# maxAttempts: after this many actual issues the signal is escalated
# completed: None = pending/blocked/not-tested, True = passed, False = escalated
# validationResult: pending | passed | issue_found | not_tested | blocked | escalated
enabled_signals = [k for k, v in profile.get("signals", {}).items() if v.get("enabled", False)]
signal_status = profile["acoustic"].setdefault("signalStatus", {})
for sig in enabled_signals:
    signal_status.setdefault(sig, {
        "attempts": 0,
        "maxAttempts": 2,
        "completed": None,
        "validationResult": "pending",
        "reasonCodes": [],
        "lastValidatedAt": None,
        "correctionHistory": []
    })
    # Add new fields to existing entries without overwriting any saved values
    signal_status[sig].setdefault("attempts", 0)
    signal_status[sig].setdefault("maxAttempts", 2)
    signal_status[sig].setdefault("completed", None)
    signal_status[sig].setdefault("validationResult", "pending")
    signal_status[sig].setdefault("reasonCodes", [])
    signal_status[sig].setdefault("lastValidatedAt", None)
    signal_status[sig].setdefault("correctionHistory", [])
profile["acoustic"]["sdkConfigurationComplete"] = False

profile_path.write_text(json.dumps(profile, indent=2))
print("Profile updated with sdkBundle state and signalStatus")
```

**After generation — present all deliverable files to the user**

Immediately after writing the profile state, locate the output files and call `mcp__cowork__present_files` with all deliverables. Then show a `show_widget` (title: `generated_files_summary`, loading: `"Preparing your files…"`) so the user sees a clear summary.

```python
import glob as _glob, pathlib

slug = '<SLUG>'  # replace with actual domain slug
_out_dirs = _glob.glob(f'/sessions/*/mnt/SDK-config-assistant/outputs/{slug}*') or \
            _glob.glob(f'/sessions/*/mnt/.claude/skills/sdk-config-assistant/outputs/{slug}*')
out_dir = sorted(_out_dirs, key=lambda d: pathlib.Path(d).stat().st_mtime, reverse=True)[0] if _out_dirs else None

if out_dir:
    sdk_js   = next(pathlib.Path(out_dir).glob('acoConnectSdkConfig-*.js'), None)
    tm_js    = next(pathlib.Path(out_dir).glob('acoConnectSdkConfig-*.tamperMonkeyConfig.js'), None)
    review   = next(pathlib.Path(out_dir).glob('*-implementation-review.md'), None)
    test_doc = next(pathlib.Path(out_dir).glob('How to test*.md'), None)
    files_to_present = [str(f) for f in [sdk_js, tm_js, review, test_doc] if f]
    print('Present these files:', files_to_present)
```

Call `mcp__cowork__present_files` with the file paths from above.

Then show the file summary widget — substitute `SLUG` with the actual domain slug:

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:14px">SDK config generated ✅</div>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead>
      <tr style="border-bottom:1px solid var(--color-border-tertiary)">
        <th style="text-align:left;padding:6px 8px;color:var(--color-text-tertiary);font-weight:500">File</th>
        <th style="text-align:left;padding:6px 8px;color:var(--color-text-tertiary);font-weight:500">Use for</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid var(--color-border-tertiary)">
        <td style="padding:8px;font-family:monospace;color:#706CFF">acoConnectSdkConfig-SLUG.js</td>
        <td style="padding:8px;color:var(--color-text-secondary)">SDK config. Replace in Tampermonkey folder to update.</td>
      </tr>
      <tr style="border-bottom:1px solid var(--color-border-tertiary)">
        <td style="padding:8px;font-family:monospace;color:#706CFF">acoConnectSdkConfig-SLUG.tamperMonkeyConfig.js</td>
        <td style="padding:8px;color:var(--color-text-secondary)">Install in Tampermonkey → Dashboard → Utilities → Import from file.</td>
      </tr>
      <tr style="border-bottom:1px solid var(--color-border-tertiary)">
        <td style="padding:8px;font-family:monospace;color:var(--color-text-primary)">SLUG-implementation-review.md</td>
        <td style="padding:8px;color:var(--color-text-secondary)">Signal mapping notes and open items.</td>
      </tr>
      <tr>
        <td style="padding:8px;font-family:monospace;color:var(--color-text-primary)">How to test and validate the data.md</td>
        <td style="padding:8px;color:var(--color-text-secondary)">Step-by-step testing guide (Tampermonkey, DevTools override, console signals).</td>
      </tr>
    </tbody>
  </table>
  <div style="margin-top:12px;padding:10px 14px;background:var(--color-background-secondary);border-radius:8px;font-size:11px;color:var(--color-text-secondary)">
    <strong>Test mode active</strong> — <code>fakeSignals: true</code>, <code>eventLog: false</code>. Signals print to console only. No data sent to Connect yet.
  </div>
</div>
```

After generation, also create **`How to test and validate the data.md`** in the same output folder. Each method section must be a complete, numbered, start-to-finish walkthrough — assume the reader has never done this before and is following the doc with no other context. Do not write prose paragraphs describing the process; write literal numbered steps in the order to perform them. It must include:

**Section: Method 1 — TamperMonkey**

The generator produces two files for Tampermonkey testing:
- `acoConnectSdkConfig-<domain-slug>.js` — the full configured SDK config
- `acoConnectSdkConfig-<domain-slug>.tamperMonkeyConfig.js` — a lightweight userscript that `@require`-loads the config from the local file system

The `.user.js` file does NOT embed the SDK — it uses `@require file:///...` to load the config from disk. This means updating the SDK for a new round only requires replacing the `.js` file; no Tampermonkey script reinstall is needed.

Write these as literal numbered steps (substitute the real domain-slug/domain):

1. If you don't already have it, install the [Tampermonkey extension](https://www.tampermonkey.net/) for Chrome, then enable **Allow User Scripts** at `chrome://extensions`.
2. In Tampermonkey → **Settings** → **Security**, add your output folder to the **Allowlist for @require** — e.g. `file:///path/to/output/<domain-slug>/*`. Without this, Tampermonkey blocks `file://` `@require` loads.
3. Open the Tampermonkey dashboard → **Utilities** tab → **Import from file**.
4. Select `acoConnectSdkConfig-<domain-slug>.tamperMonkeyConfig.js` from this output folder.
5. Click **Install**.
6. Visit `<productionDomain>` in Chrome — the SDK now loads automatically on every page of the site.
7. Open DevTools (F12 or Cmd+Opt+I) → **Console** tab. This is where to watch for signals — see "Where to look in the console" below.
8. This config currently has `fakeSignals: true` (test/console mode) — no data reaches Acoustic yet, signals only print to console.
9. **To update the SDK for a new round:** regenerate `acoConnectSdkConfig-<domain-slug>.js` and save it to the same path — the Tampermonkey script will pick it up automatically on the next page reload. No script reinstall needed.
10. **To later switch to real mode** (send actual data to Connect): regenerate with `settings.mode = "real"` — the new config will have `fakeSignals: false`.

**Section: Method 2 — Chrome DevTools Override**

No extension required. Write these as literal numbered steps:

1. Open DevTools (F12 or Cmd+Opt+I) → **Sources** tab → **Overrides** sub-tab (click the `»` overflow arrow in the left sidebar if it isn't visible).
2. Click **"Select folder for overrides"** → choose or create any empty local folder (e.g. a new folder on your Desktop) → click **Allow** when Chrome asks for filesystem permission.
3. Go to the **Network** tab and reload `<productionDomain>`.
4. In the Network list, find the request for the SDK config file (its URL ends in the delivery filename, e.g. `acoConnectSdkConfig-<slug>.js`).
5. Right-click that request → **"Override content."** DevTools copies the live response into your override folder and opens it in the Sources editor.
6. Select all the content in that editor (Ctrl+A / Cmd+A) and replace it with the full contents of `acoConnectSdkConfig-<slug>.js` from this output folder. Save (Ctrl+S / Cmd+S).
7. Reload the page. Chrome now serves your local file instead of the real network response, every time that URL is requested.
8. Open DevTools → **Console** tab. This is where to watch for signals — see "Where to look in the console" below.
9. This config currently has `fakeSignals: true` (test/console mode) — no data reaches Acoustic yet, signals only print to console.
10. **To later switch to real mode:** go back to Sources → Overrides → open the same overridden file → find `fakeSignals: true` → change it to `fakeSignals: false` → save (Ctrl+S / Cmd+S) → reload the page. No re-setup needed.

**Section: Where to look in the console for fake signals**

Whichever method above was used, once the SDK is loaded:

1. Open DevTools → **Console** tab and keep it open while you browse the site.
2. Browse normally — view a product, search, add something to the cart, sign in, etc.
3. Each time a configured signal fires, a line prints in this exact format: `Acoustic Connect: Type 5 fake <signalType> signal 🥸` — e.g. `Acoustic Connect: Type 5 fake productView signal 🥸`. This is the confirmation that signal would have fired for real.
4. If nothing prints while browsing, check that the console filter (top of the panel) isn't set to hide "log" level messages, and confirm the SDK initialized (see "Verifying the SDK is loaded" below) before assuming a signal is missing.
5. Once `fakeSignals` is switched to `false` (real mode), these lines stop appearing in the console — instead, look in Acoustic Connect's Signal Management or Session Replay dashboard, since the data is now actually being sent, not just logged.

Also include sections: **Verifying the SDK is loaded**, **What to look for in the console** (type 2/4/5 table), and **Key journeys to validate** (per-signal table). Do NOT include a "Switching to production mode" section — the skill handles this interactively in the validation step below.

**Validation gate — per-signal matrix**

> ⚠️ **GUARDRAIL — mandatory stop after generation.**
>
> After SDK generation and test-guide creation this is the **only** next action. Do not:
> - Proceed to Step 10 (upload)
> - Summarise what was generated
> - Ask any other question
> - Add any prose before or after the widget
>
> If the user chooses "Not yet — come back later", write exactly one sentence:
> **"Got it. Stopping here — come back when you've validated the signals using the test guide and I'll pick up from this step."**
>
> This applies on first run AND every time the user selects "Not yet". Re-presentation is intentional — the "do not ask the same question twice" guardrail does NOT apply here.

**Read the current signal status before building the widget.** Load the profile to get up-to-date attempt counts, escalation state, and previously saved validation results:

```python
import json, pathlib, glob as _glob, datetime
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
signal_status = profile.get('acoustic', {}).get('signalStatus', {})
tier = profile.get('customer', {}).get('tier', profile.get('settings', {}).get('tier', ''))

for sig, st in signal_status.items():
    vr   = st.get('validationResult', 'pending')
    att  = st.get('attempts', 0)
    mxa  = st.get('maxAttempts', 2)
    comp = st.get('completed')
    label = 'escalated' if comp is False else f"attempts={att}/{mxa}, result={vr}"
    print(f"  {sig}: {label}")
print('tier:', tier)
```

**Build and show the per-signal validation matrix widget.**

Build `SIGNAL_MATRIX_ROWS` in Python before calling `show_widget`. One row per in-scope signal. Escalated signals (where `completed == False`) are shown greyed out and non-selectable. For all eligible signals, preserve any previously saved `validationResult` as the pre-selected value so resuming validation does not lose prior results.

```python
import json, pathlib, glob as _glob

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile = json.loads((pathlib.Path(_dirs[0]) / '<SLUG>.json').read_text())
signal_status = profile.get('acoustic', {}).get('signalStatus', {})

desc_map = {
    "pageView":              "Every page load (URL, title, category)",
    "identification":        "Email capture from sign-in",
    "accountRegistered":     "Email capture from registration success page",
    "addToCart":             "Product added to basket (ID, name, price, quantity)",
    "productView":           "Product detail page view",
    "productConfiguration":  "Colour / size / variant selector interactions",
    "onSiteSearch":          "Search query and result count",
    "formSubmit":            "Lead / contact form submission",
    "order":                 "Purchase conversion (order ID, revenue, items)",
    "richMediaInteraction":  "Video / podcast / file download events",
    "removedFromCart":       "Item removed from basket",
}

RESULT_OPTIONS = [
    ("passed",      "✅ Passed"),
    ("issue_found", "⚠️ Issue found"),
    ("not_tested",  "⏭ Not tested"),
    ("blocked",     "🚫 Blocked"),
]

rows = []
for sig, st in signal_status.items():
    desc      = desc_map.get(sig, sig)
    attempts  = st.get('attempts', 0)
    max_att   = st.get('maxAttempts', 2)
    escalated = st.get('completed') is False
    saved_vr  = st.get('validationResult', 'pending')

    if escalated:
        rows.append(f"""
        <div class="sig-row escalated" data-sig="{sig}"
             style="opacity:0.5;display:flex;align-items:center;gap:10px;padding:10px 14px;
                    background:var(--color-background-secondary);border-radius:8px;margin-bottom:6px">
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:12px;font-weight:600;color:var(--color-text-primary)">{sig}</span>
              <span style="font-size:10px;background:#FFF3CD;color:#b45309;padding:1px 7px;border-radius:20px;font-weight:600">Acoustic Services required</span>
            </div>
            <div style="font-size:10px;color:var(--color-text-tertiary)">{desc}</div>
          </div>
          <div style="font-size:10px;color:#b45309;white-space:nowrap">{attempts}/{max_att} attempts</div>
        </div>""")
    else:
        att_label = (f"Attempt {attempts} used" if attempts == 1
                     else f"{attempts} attempts used" if attempts > 1
                     else "No attempts used")
        # Build option pills — pre-select saved result
        pills = ""
        for val, label in RESULT_OPTIONS:
            sel_class  = "sel" if saved_vr == val else ""
            sel_style  = "border-color:#706CFF;background:#EEF0FF;" if saved_vr == val else ""
            pills += f"""<button class="rpill {sel_class}" data-sig="{sig}" data-val="{val}"
              onclick="selectResult(this)"
              style="font-size:10px;padding:4px 10px;border-radius:20px;border:1px solid var(--color-border-tertiary);
                     background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;{sel_style}">{label}</button>"""
        rows.append(f"""
        <div class="sig-row" data-sig="{sig}"
             style="display:flex;align-items:flex-start;gap:10px;padding:10px 14px;
                    background:var(--color-background-secondary);border-radius:8px;margin-bottom:6px">
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">
              <span style="font-size:12px;font-weight:600;color:var(--color-text-primary)">{sig}</span>
              <span style="font-size:10px;color:var(--color-text-tertiary)">{desc}</span>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">{pills}</div>
          </div>
          <div style="font-size:10px;color:var(--color-text-tertiary);white-space:nowrap;margin-top:2px">{att_label}</div>
        </div>""")

signal_matrix_rows = "\n".join(rows)
print(signal_matrix_rows)
```

Show the matrix with `mcp__visualize__show_widget` (title: `signal_validation_matrix`, loading: `"Loading validation matrix…"`). Embed `SIGNAL_MATRIX_ROWS` (the Python output) in place of the placeholder comment. **If `show_widget` is unavailable:** apply the Category 3a fallback — run `AskUserQuestion` once per in-scope signal in canonical signal order, each with options "✅ Passed / ⚠️ Issue found / ⏭ Not tested / 🚫 Blocked". Collect all results then route to sub-flows exactly as if they came from the matrix `sendPrompt`.

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">Signal validation</div>
  <div style="font-size:11px;color:var(--color-text-tertiary);margin-bottom:14px">
    Select a result for every signal you tested. Escalated signals are shown for reference.
  </div>

  <div id="matrix" style="margin-bottom:16px">
    <!-- INSERT signal_matrix_rows HERE -->
  </div>

  <div id="pending-warn" style="display:none;padding:8px 12px;background:#FFF3CD;border-radius:6px;font-size:11px;color:#7A6800;margin-bottom:10px">
    ⚠️ Please select a result for every signal before continuing.
  </div>

  <div style="display:flex;gap:8px">
    <button onclick="submitMatrix()"
      style="background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;padding:10px 20px;
             font-size:12px;font-weight:600;cursor:pointer;flex:1">
      Submit validation results
    </button>
    <button onclick="sendPrompt('Validation: not yet come back later')"
      style="background:var(--color-background-secondary);color:var(--color-text-primary);
             border:1px solid var(--color-border-tertiary);border-radius:8px;padding:10px 16px;
             font-size:12px;cursor:pointer;white-space:nowrap">
      Not yet — come back later
    </button>
  </div>
</div>

<script>
function selectResult(btn) {
  var sig = btn.getAttribute('data-sig');
  document.querySelectorAll('.rpill[data-sig="'+sig+'"]').forEach(function(p) {
    p.classList.remove('sel');
    p.style.borderColor = 'var(--color-border-tertiary)';
    p.style.background  = 'var(--color-background-secondary)';
  });
  btn.classList.add('sel');
  btn.style.borderColor = '#706CFF';
  btn.style.background  = '#EEF0FF';
}

function submitMatrix() {
  var rows   = document.querySelectorAll('#matrix .sig-row:not(.escalated)');
  var result = {};
  var missing = [];
  rows.forEach(function(row) {
    var sig = row.getAttribute('data-sig');
    var sel = row.querySelector('.rpill.sel');
    if (sel) { result[sig] = sel.getAttribute('data-val'); }
    else      { missing.push(sig); }
  });
  if (missing.length > 0) {
    document.getElementById('pending-warn').style.display = 'block';
    return;
  }
  document.getElementById('pending-warn').style.display = 'none';
  sendPrompt('ValidationMatrix: ' + JSON.stringify(result));
}
</script>
```

**Routing from the matrix:**

| sendPrompt value | Action |
|---|---|
| `'ValidationMatrix: {...}'` | Parse the JSON payload. Classify each signal result. Route to sub-flows. |
| `'Validation: not yet come back later'` | Write one sentence. Save paused state to profile. Stop. |

**"Not yet — come back later" handler:**

```python
import json, glob as _glob, pathlib

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
profile['acoustic']['sdkBundle']['validated'] = False
profile['acoustic']['sdkBundle']['validationPaused'] = True
profile['acoustic']['sdkConfigurationComplete'] = False
profile_path.write_text(json.dumps(profile, indent=2))
print("Validation paused — customer can resume by loading this profile.")
```

Write the one sentence, then stop.

---

**Processing the ValidationMatrix payload — SI-A: Parse and persist**

When `sendPrompt` fires `'ValidationMatrix: {...}'`, parse the JSON and update the operational profile. Do not increment attempts at this stage — record the result only:

```python
import json, pathlib, glob as _glob, datetime

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path  = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile      = json.loads(profile_path.read_text())
signal_status = profile['acoustic']['signalStatus']

# Parse — the user message contains: ValidationMatrix: {"pageView":"passed",...}
raw_json = '<PASTE_JSON_FROM_MESSAGE>'   # e.g. {"pageView":"passed","addToCart":"issue_found",...}
matrix   = json.loads(raw_json)

now_ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

passed_signals    = []
issue_signals     = []
blocked_signals   = []
not_tested_signals = []

for sig, result in matrix.items():
    if sig not in signal_status:
        continue
    st = signal_status[sig]

    if result == 'passed':
        st['validationResult']  = 'passed'
        st['completed']         = True
        st['lastValidatedAt']   = now_ts
        # Do NOT increment attempts
        passed_signals.append(sig)

    elif result == 'issue_found':
        st['validationResult']  = 'issue_found'
        # completed stays None until escalation or passing
        st['lastValidatedAt']   = now_ts
        issue_signals.append(sig)

    elif result == 'blocked':
        st['validationResult']  = 'blocked'
        st['completed']         = None   # not escalated, not passed
        st['lastValidatedAt']   = now_ts
        blocked_signals.append(sig)

    elif result == 'not_tested':
        st['validationResult']  = 'not_tested'
        st['completed']         = None
        st['lastValidatedAt']   = now_ts
        not_tested_signals.append(sig)

profile_path.write_text(json.dumps(profile, indent=2))
print('passed:', passed_signals)
print('issue:', issue_signals)
print('blocked:', blocked_signals)
print('not_tested:', not_tested_signals)
```

---

**SI-B: Issue follow-up — collect reason codes for issue_found signals**

If `issue_signals` is non-empty, show one follow-up widget containing only those signals. Collect one structured reason per signal. Do not ask one question per signal.

Build `ISSUE_REASON_ROWS` in Python — one row per signal in `issue_signals`:

```python
ISSUE_REASONS = [
    ("signal_not_triggered",        "Signal did not fire"),
    ("duplicate_signal",            "Signal fired more than once"),
    ("required_field_missing",      "A required field was missing"),
    ("incorrect_field_value",       "A field contained the wrong value"),
    ("incorrect_field_type",        "A field had the wrong data type"),
    ("wrong_trigger",               "The wrong interaction triggered the signal"),
    ("wrong_page",                  "The signal fired on the wrong page"),
    ("payload_invalid",             "The payload was invalid"),
    ("unexpected_signal",           "An unexpected signal fired"),
    ("product_id_mismatch",         "Product IDs did not match across the journey"),
    ("configuration_type_incorrect","Configuration type or action state was incorrect"),
    ("other",                       "Other"),
]

rows = []
for sig in issue_signals:
    opts = ""
    for val, label in ISSUE_REASONS:
        opts += f'<option value="{val}">{label}</option>'
    rows.append(f"""
    <div style="padding:10px 14px;background:var(--color-background-secondary);border-radius:8px;margin-bottom:8px">
      <div style="font-size:12px;font-weight:600;color:var(--color-text-primary);margin-bottom:6px">{sig}</div>
      <select id="reason-{sig}" style="width:100%;font-size:11px;padding:6px 8px;border-radius:6px;
              border:1px solid var(--color-border-tertiary);background:var(--color-background-primary);
              color:var(--color-text-primary);font-family:var(--font-sans)">
        <option value="">— select reason —</option>
        {opts}
      </select>
      <div id="note-wrap-{sig}" style="display:none;margin-top:6px">
        <textarea id="note-{sig}" placeholder="Describe the issue (required for Other)"
          style="width:100%;font-size:11px;padding:6px 8px;border-radius:6px;border:1px solid var(--color-border-tertiary);
                 background:var(--color-background-primary);color:var(--color-text-primary);font-family:var(--font-sans);
                 resize:vertical;min-height:48px;box-sizing:border-box"></textarea>
      </div>
      <script>document.getElementById('reason-{sig}').addEventListener('change',function(){{
        document.getElementById('note-wrap-{sig}').style.display = this.value==='other'?'block':'none';
      }});</script>
    </div>""")

issue_reason_rows = "\n".join(rows)
print(issue_reason_rows)
```

Show with `mcp__visualize__show_widget` (title: `issue_reason_collector`, loading: `"Loading issue details…"`):

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">What went wrong?</div>
  <div style="font-size:11px;color:var(--color-text-tertiary);margin-bottom:14px">
    Select the most accurate reason for each signal that had an issue.
  </div>
  <div id="issue-reasons">
    <!-- INSERT issue_reason_rows HERE -->
  </div>
  <div id="issue-warn" style="display:none;padding:8px 12px;background:#FFF3CD;border-radius:6px;font-size:11px;color:#7A6800;margin-bottom:10px">
    ⚠️ Please select a reason for every signal.
  </div>
  <button onclick="submitIssueReasons()"
    style="background:#706CFF;color:#fff;border:none;border-radius:8px;padding:10px 20px;
           font-size:12px;font-weight:600;cursor:pointer;width:100%;margin-top:8px">
    Continue
  </button>
</div>
<script>
function submitIssueReasons() {
  var sigs = document.querySelectorAll('#issue-reasons [id^="reason-"]');
  var result = {}; var missing = [];
  sigs.forEach(function(sel) {
    var sig = sel.id.replace('reason-', '');
    if (!sel.value) { missing.push(sig); return; }
    var note = document.getElementById('note-' + sig);
    result[sig] = { reason: sel.value, note: (note && note.value) ? note.value : '' };
  });
  if (missing.length) {
    document.getElementById('issue-warn').style.display = 'block'; return;
  }
  document.getElementById('issue-warn').style.display = 'none';
  sendPrompt('IssueReasons: ' + JSON.stringify(result));
}
</script>
```

**Parse `IssueReasons` response and run the correction attempt:**

```python
import json, pathlib, glob as _glob, datetime

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path  = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile       = json.loads(profile_path.read_text())
signal_status = profile['acoustic']['signalStatus']

raw_json     = '<PASTE_JSON_FROM_MESSAGE>'   # {"addToCart":{"reason":"signal_not_triggered","note":""},...}
issue_details = json.loads(raw_json)

now_ts          = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
newly_escalated = []
to_reinspect    = []

for sig, detail in issue_details.items():
    if sig not in signal_status:
        continue
    st            = signal_status[sig]
    reason_code   = detail.get('reason', 'other')
    note          = detail.get('note', '')

    # Do NOT increment attempts here — attempts is incremented only when
    # a correction is actually attempted (after re-inspection), not on issue selection
    st['validationResult'] = 'issue_found'
    st['completed']        = None   # remains pending until correction outcome known

    # Record reason for this report
    st.setdefault('reasonCodes', [])
    if reason_code not in st['reasonCodes']:
        st['reasonCodes'].append(reason_code)

    # Stage a pending correction history entry — attempt number filled in later
    # when the correction is actually performed
    pending_entry = {
        'attempt':             None,   # filled in when correction is attempted
        'reportedAt':          now_ts,
        'validationResult':    'issue_found',
        'reasonCodes':         [reason_code],
        'note':                note,
        'correctionAttempted': False,
        'correctionResult':    'pending',
        'retestResult':        'pending',
    }
    st.setdefault('correctionHistory', []).append(pending_entry)

    # Queue for correction — do not escalate yet
    to_reinspect.append(sig)

profile_path.write_text(json.dumps(profile, indent=2))
print('newly escalated:', newly_escalated)
print('to re-inspect:', to_reinspect)
```

---

**SI-C: Blocked signal follow-up**

If `blocked_signals` is non-empty, show one follow-up widget for blocker reasons. Do not increment attempts:

```python
BLOCKER_REASONS = [
    ("authentication_required",      "Sign-in or account required to trigger"),
    ("registration_unavailable",     "Registration journey not accessible"),
    ("order_journey_unavailable",    "Order / checkout journey not accessible"),
    ("staging_unavailable",          "Staging environment unavailable"),
    ("test_data_unavailable",        "Test data not available"),
    ("cookie_consent_blocked",       "Cookie consent prevented testing"),
    ("cross_domain_journey",         "Journey spans multiple domains"),
    ("browser_tool_failure",         "Browser tool could not complete the test"),
    ("page_unreachable",             "Page could not be reached"),
    ("feature_not_present",          "Feature is not present on this site"),
    ("other",                        "Other"),
]

rows = []
for sig in blocked_signals:
    opts = "".join(f'<option value="{v}">{l}</option>' for v, l in BLOCKER_REASONS)
    rows.append(f"""
    <div style="padding:10px 14px;background:var(--color-background-secondary);border-radius:8px;margin-bottom:8px">
      <div style="font-size:12px;font-weight:600;color:var(--color-text-primary);margin-bottom:6px">{sig}</div>
      <select id="blocker-{sig}" style="width:100%;font-size:11px;padding:6px 8px;border-radius:6px;
              border:1px solid var(--color-border-tertiary);background:var(--color-background-primary);
              color:var(--color-text-primary);font-family:var(--font-sans)">
        <option value="">— select blocker reason —</option>
        {opts}
      </select>
    </div>""")
blocker_reason_rows = "\n".join(rows)
print(blocker_reason_rows)
```

Show with `mcp__visualize__show_widget` (title: `blocker_reason_collector`, loading: `"Loading blocker details…"`). Parse response `'BlockerReasons: {...}'` and save each signal's blocker reason code to `signal_status[sig]['reasonCodes']`. Do not increment `attempts`. Keep `completed: null`.

---

**SI-D: Not-tested signal follow-up (optional)**

If `not_tested_signals` is non-empty, optionally collect a reason. Use the same pattern as SI-C with these reason codes:

```
testing_deferred | journey_unavailable | test_data_unavailable | signal_not_present_on_site | customer_chose_not_to_test | other
```

Save to `signal_status[sig]['reasonCodes']` if provided. Do not increment `attempts`. Keep `completed: null`.

---

**SI-E: Exception confirmation**

If any signals remain `blocked` or `not_tested` after the follow-ups, show one exception-confirmation widget before continuing:

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:8px">Some signals could not be fully validated</div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:12px">
    The following signals were recorded as exceptions. They will be documented in the final report
    but will not block the remaining workflow.
  </div>
  <!-- list blocked/not_tested signals here -->
  <div style="display:flex;gap:8px;margin-top:14px">
    <button onclick="sendPrompt('Exceptions: continue with exceptions')"
      style="background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;padding:10px 20px;
             font-size:12px;font-weight:600;cursor:pointer;flex:1">
      Continue with exceptions
    </button>
    <button onclick="sendPrompt('Exceptions: return to validation')"
      style="background:var(--color-background-secondary);color:var(--color-text-primary);
             border:1px solid var(--color-border-tertiary);border-radius:8px;padding:10px 16px;
             font-size:12px;cursor:pointer;flex:1">
      Return to validation
    </button>
  </div>
</div>
```

- `'Exceptions: continue with exceptions'` → continue. Set `workflowOutcome = completed_with_exceptions`. Do not mark blocked/not_tested signals as passed.
- `'Exceptions: return to validation'` → re-present the per-signal matrix widget.

---

**SI-F: Re-inspect and correct issue_found signals (SI-3b equivalent)**

For each signal in `to_reinspect`, navigate to the relevant page and re-run capture steps. This is unchanged from the existing SI-3b behaviour:

| Signal | Page | Key interaction |
|---|---|---|
| `pageView` | Homepage `/` | Type 2 capture |
| `identification` | Sign-in page | Fill dummy email, capture `change` event |
| `accountRegistered` | Registration form | Confirm email field; note both URL paths |
| `addToCart` | Product display page | Simulate add-to-cart, capture Type 4 |
| `productView` | Product display page | Type 2 + dataLayer ecommerce |
| `productConfiguration` | Product display page | Simulate colour/size/qty interactions |
| `onSiteSearch` | Search results | Type 2 + dataLayer event |
| `order` | Order confirmation | dataLayer ecommerce (staging only) |
| `richMediaInteraction` | Any page with video/download | Simulate play/download |
| `removedFromCart` | Cart page | Simulate remove item |

For each signal in `to_reinspect`:
1. Navigate to the relevant page.
2. Inject the capture shim (`references/auto-event-capture.md` Step 1).
3. Run the appropriate interaction simulation (Steps 3–4).
4. Read Type 4 events and dataLayer capture buffer.
5. If improved evidence is found, update `profile.signals.<signalKey>` and write the profile.
6. Update the correction history entry: set `correctionAttempted: true` and `correctionResult` to the appropriate value.

After updating profile and correction history:

```python
import json, pathlib, glob as _glob

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path  = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile       = json.loads(profile_path.read_text())
signal_status = profile['acoustic']['signalStatus']

corrected_signals = '<LIST_OF_REINSPECTED_SIGNALS>'   # replace with actual list
correction_result = '<pending|mapping_updated|trigger_updated|field_mapping_updated|no_better_evidence_found|no_safe_mapping_found>'

for sig in corrected_signals:
    if sig in signal_status:
        st      = signal_status[sig]
        history = st.get('correctionHistory', [])

        # Increment attempts now — correction was actually performed
        current_attempts = st.get('attempts', 0)
        max_attempts     = st.get('maxAttempts', 2)
        new_attempts     = current_attempts + 1
        st['attempts']   = new_attempts

        # Fill in attempt number on the pending history entry
        if history:
            history[-1]['attempt']             = new_attempts
            history[-1]['correctionAttempted'] = True
            history[-1]['correctionResult']    = correction_result

profile_path.write_text(json.dumps(profile, indent=2))
```

If no improved evidence is found, set `correctionResult: 'no_better_evidence_found'` and document the blocker in `profile.questions`.

---

**SI-G: Regenerate SDK for corrected signals**

After updating the profile with any improved mappings, regenerate the SDK in test mode (same command as Step 9 Step B). Then present the updated config using the existing SI-3d `signal_retest_bundle` widget, listing only the corrected signals.

---

**SI-I: Retest widget — corrected signals only**

After the user has retested, show one retest widget containing **only** signals from `to_reinspect` (corrected in this cycle). Do not ask about already-passed or already-escalated signals.

Build `RETEST_ROWS` using the same pill pattern as the main matrix but with only corrected signals and only `passed / issue_found / blocked / not_tested` options:

```python
retest_rows = []
for sig in to_reinspect:
    desc = desc_map.get(sig, sig)
    st   = signal_status[sig]
    att  = st.get('attempts', 0)
    mxa  = st.get('maxAttempts', 2)
    pills = ""
    for val, label in [("passed","✅ Passed"),("issue_found","⚠️ Issue found"),("blocked","🚫 Blocked"),("not_tested","⏭ Not tested")]:
        pills += f'<button class="rpill" data-sig="{sig}" data-val="{val}" onclick="selectResult(this)" style="font-size:10px;padding:4px 10px;border-radius:20px;border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;">{label}</button>'
    retest_rows.append(f"""
    <div class="sig-row" data-sig="{sig}"
         style="display:flex;align-items:flex-start;gap:10px;padding:10px 14px;
                background:var(--color-background-secondary);border-radius:8px;margin-bottom:6px">
      <div style="flex:1;min-width:0">
        <div style="font-size:12px;font-weight:600;color:var(--color-text-primary);margin-bottom:6px">{sig} <span style="font-weight:400;color:var(--color-text-tertiary)">{desc}</span></div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">{pills}</div>
      </div>
      <div style="font-size:10px;color:var(--color-text-tertiary);white-space:nowrap;margin-top:2px">Attempt {att}/{mxa}</div>
    </div>""")
retest_rows_html = "\n".join(retest_rows)
print(retest_rows_html)
```

Show with `mcp__visualize__show_widget` (title: `signal_retest_matrix`, loading: `"Loading retest…"`). Use the same `submitMatrix` JS pattern as the main matrix but submit as `'RetestMatrix: {...}'`.

**Parse `RetestMatrix` response and update profile:**

```python
import json, pathlib, glob as _glob, datetime

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path  = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile       = json.loads(profile_path.read_text())
signal_status = profile['acoustic']['signalStatus']

raw_json    = '<PASTE_JSON_FROM_MESSAGE>'
retest_map  = json.loads(raw_json)
now_ts      = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

still_issue = []
newly_esc   = []
newly_passed = []

for sig, result in retest_map.items():
    if sig not in signal_status:
        continue
    st = signal_status[sig]
    history = st.get('correctionHistory', [])

    if result == 'passed':
        st['validationResult'] = 'passed'
        st['completed']        = True
        st['lastValidatedAt']  = now_ts
        # Update last correction history entry
        if history:
            history[-1]['retestResult']   = 'passed'
        newly_passed.append(sig)

    elif result == 'issue_found':
        st['lastValidatedAt'] = now_ts
        if history:
            history[-1]['retestResult'] = 'issue_found'
        # Check whether attempts is exhausted AFTER this retest failure
        current_attempts = st.get('attempts', 0)
        max_attempts     = st.get('maxAttempts', 2)
        if current_attempts >= max_attempts:
            # Correction was already performed max_attempts times and still failing — escalate
            st['completed']        = False
            st['validationResult'] = 'escalated'
            newly_esc.append(sig)
        else:
            # More correction attempts available — queue for another cycle
            still_issue.append(sig)

    elif result in ('blocked', 'not_tested'):
        st['validationResult'] = result
        st['lastValidatedAt']  = now_ts
        if history:
            history[-1]['retestResult'] = result

profile_path.write_text(json.dumps(profile, indent=2))
print('newly passed:', newly_passed)
print('still issue:', still_issue)
```

- Signals in `still_issue` → route back through SI-B (issue follow-up → attempt increment → escalate or re-inspect again).
- Signals in `newly_passed` → no further action on those signals.
- If `newly_esc` is non-empty → show SI-H (escalation notice) before continuing.

---

**SI-H: Escalation notice**

If `newly_esc` (from the retest block above) is non-empty, show the escalation widget (title: `signal_escalation`). Note: escalation is determined after a retest fails when `attempts >= maxAttempts` — never on initial issue selection. Preserve the existing widget content but extend it to show per-signal details:

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
    <div style="width:32px;height:32px;border-radius:50%;background:#FFF3CD;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0">⚠️</div>
    <div style="font-size:13px;font-weight:600;color:var(--color-text-primary)">Some signals require Acoustic Services assistance</div>
  </div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:12px">
    The skill attempted to correct the signals below twice but could not confirm a safe working configuration.
    The remaining signals can continue, but these signals require help from Acoustic Services.
  </div>
  <div style="margin-bottom:14px;display:flex;flex-direction:column;gap:6px">
    <!-- ESCALATED_SIGNAL_ROWS: one div per newly escalated signal showing: name, desc, attempts/maxAttempts, latest reason, status=Escalated -->
  </div>
  <div style="background:#FFF8E8;border-left:3px solid #F0C040;border-radius:6px;padding:10px 14px;font-size:11px;color:#7A6800;margin-bottom:14px">
    <strong>Please contact the Acoustic Services team to assist in configuring these signals.</strong><br>
    Reach out to your Customer Success Manager if you have any questions.
  </div>
  <button onclick="sendPrompt('Acknowledged — continue')" style="background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;padding:8px 20px;font-size:12px;font-weight:600;cursor:pointer;width:100%">Continue</button>
</div>
```

Wait for `sendPrompt('Acknowledged — continue')`.

---

**SI-J: Continue gate after all issues resolved**

Once `issue_signals` are all resolved (each is either `passed`, `escalated`, `blocked+accepted`, or `not_tested+accepted`), re-check whether any exceptions remain and whether to proceed:

```python
import json, pathlib, glob as _glob

_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile = json.loads((pathlib.Path(_dirs[0]) / '<SLUG>.json').read_text())
ss = profile['acoustic']['signalStatus']

escalated   = [s for s, v in ss.items() if v.get('completed') is False]
blocked_ok  = [s for s, v in ss.items() if v.get('validationResult') == 'blocked']
not_tested_ok = [s for s, v in ss.items() if v.get('validationResult') == 'not_tested']
pending     = [s for s, v in ss.items() if v.get('validationResult') in ('pending', 'issue_found') and v.get('completed') is not False]
passed      = [s for s, v in ss.items() if v.get('completed') is True]

print('escalated:', escalated)
print('blocked:', blocked_ok)
print('not_tested:', not_tested_ok)
print('still pending/issue:', pending)
print('passed:', passed)
```

- If `pending` is non-empty → those signals still have unresolved issues — route back to SI-B for each.
- If `pending` is empty and (`blocked_ok` or `not_tested_ok`) and no exception was already confirmed → show SI-E exception widget.
- If all signals are `passed`, `escalated`, or accepted exceptions → proceed to Step 11.

**Routing from SI-J:**

| Tier | Condition | Action |
|---|---|---|
| Pro / Premium / Ultimate | All resolved | Proceed to Step 11 → Step 12 → Step 13 → Step 10-pre (deployment choice). Identical on every tier. |

> ⚠️ **GUARDRAIL — "yes push to production" path (every tier):**
> - **DO NOT** skip Steps 11, 12, or 13. Post-generation edits, JS review, and browser verification must complete before Step 10-pre runs. Step 10 (CMS upload) only runs if Step 10-pre Option 2 is selected.
> - **DO NOT** auto-pass any signal. Only signals explicitly marked `passed` in the matrix (or retest) with `completed: true` are considered validated.
> - **DO NOT** increment attempts for blocked, not_tested, or passed signals.
> - Escalated signals remain `completed: false` — they cannot be reset.

---

**Production flip — after validation confirmation (every tier)**

When the user confirms "Yes — push to production" (or all signals resolve at SI-J), execute this sequence **before** Step 11/12/13:

1. **Set `settings.mode = "production"` in the profile** and write it to disk:
```python
import json, pathlib, glob as _glob
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
profile['settings']['mode'] = 'production'
profile_path.write_text(json.dumps(profile, indent=2))
print('mode set to production')
```

2. **Regenerate the SDK config** using `generate_sdk.py` — same as Step 9 but with `mode = "production"`. The generator sets `fakeSignals: false`, `errorLog: false`, `eventLog: false`, `signalsLog: true`. Confirm the output file flags before proceeding.

3. **Run Step 12 (JS review)** — confirm `fakeSignals: false` and `errorLog: false` in the regenerated file. This is a mandatory check. Do not upload a config still showing `fakeSignals: true`.

4. Proceed to the canonical pre-upload sequence:
   - Step 11: TODO scan and post-generation edits.
   - Step 12: JS review — confirm `fakeSignals: false`, `errorLog: false`, expected `signalsLog`.
   - Step 13: browser verification.
   - Step 10-pre: deployment choice — shown on every tier.
   - Step 10: Media Gallery (Connect CMS) upload — only when the user selects `acoustic_cms` in Step 10-pre.

> ⛔ **HARD GATE — Step 10 may only run when `step11Complete`, `step12Complete`, and `step13Complete` are all true AND `deploymentChoice === 'acoustic_cms'`.** Any route that reaches Step 10 without satisfying all four conditions is a skill defect.

5. **Deliver the updated config file** — call `SendUserFile` on the regenerated `acoConnectSdkConfig-{SLUG}.js` so the operator has the production copy. Caption: `"Production config — fakeSignals: false. Delivery URL unchanged."`.

6. **Update the profile** — set `sdkBundle.mode = "production"`, `sdkBundle.validated = true`, `sdkBundle.generatedAt` = now, and write to disk.

7. **Proceed to Step 14 and Step 14b** (final response + analytics sidecar + completion widget + feedback).

> ⛔ **HARD STOP — never flip to production mode without user confirmation.** The "Yes — push to production" response (or SI-J all-resolved routing) is the ONLY trigger. Never auto-flip `fakeSignals` during initial generation, mid-session, or based on any signal being marked `passed`. The flip requires explicit confirmation.

---

**If "Not yet — come back later" at any point:**

Write the one sentence. Save paused state. Stop.

---

**If "Not yet — still validating" (deprecated button kept for compatibility):**

Treat identically to "Not yet — come back later". Write the one sentence. Stop.

---

> ⛔ **HARD GATE — Step 10 pre-conditions:** Step 10 (CMS upload) may run ONLY when ALL of the following are true: (1) `step11Complete = true`, (2) `step12Complete = true`, (3) `step13Complete = true`, (4) `deploymentChoice === 'acoustic_cms'`. No route — production flip, regenerate, re-upload, or any other — may bypass this gate.

### 10. Upload SDK to the Media Gallery (Connect CMS)

> ⛔ **HARD GATE — Steps 11, 12, 13, and Step 10-pre (Option 2 selected) must all be complete before this step runs.** Enhance functions must be written (Step 11), the generated JS reviewed (Step 12), signals verified in the browser (Step 13), and the user must have explicitly selected "Host it in the Media Gallery (Connect CMS)" in Step 10-pre. Starting the upload before all four are done is a skill defect. If any are incomplete, return to the missing step first.

> ⚠️ **GUARDRAIL — this step is fully automated. Never give manual upload instructions. Never ask the user to upload the file themselves. Run Steps A → B → C autonomously using Claude in Chrome browser tools. If the upload fails, report the error and ask the user to retry — never hand off the upload task to them as a first resort.**

Before starting the upload, call `mcp__visualize__show_widget` (title: `upload_login_gate`, loading: `"Loading…"`) to confirm the user is signed in. No prose before or after:

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:420px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1.25rem">
    <div style="width:40px;height:40px;border-radius:50%;background:#EEF0FF;display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#706CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
    </div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Sign in to Acoustic Connect</div>
      <div style="font-size:12px;color:var(--color-text-tertiary);margin-top:4px">Please make sure you're signed in to <strong>app.goacoustic.com</strong> in Chrome before we upload the SDK config to the Media Gallery (Connect CMS).</div>
    </div>
  </div>
  <button onclick="sendPrompt('I am signed in to Acoustic Connect — start the upload')" style="width:100%;padding:10px 16px;background:#1F1E5D;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit">
    I'm signed in — start upload
  </button>
</div>
```

Wait for the user to click before proceeding.

**Step A — Derive the filename**

Strip the production domain to a slug: remove subdomains, TLDs, and hyphens, lowercase the result.

```python
import re
domain = customer.get("productionDomain", "")  # e.g. "www.northwindtrading.co.uk" or "acme-retail.com"
# Strip leading www.
domain = re.sub(r'^www\.', '', domain)
# Take the first label only (everything before the first dot)
slug = domain.split('.')[0]
# Remove hyphens
slug = slug.replace('-', '')
sdk_filename = f"acoConnectSdkConfig-{slug}.js"
# e.g. northwindtrading.co.uk → acoConnectSdkConfig-northwindtrading.js
#      acme-retail.com → acoConnectSdkConfig-acmeretail.js
#      shop-outlet.co.uk → acoConnectSdkConfig-shopoutlet.js
```

**Step A2 — Route: new asset or update in-place?**

Read the website profile to check for a previously uploaded asset:

```python
import json, pathlib, glob as _glob
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
existing_uuid = profile.get('acoustic', {}).get('assetUuid', '')
print('existing_uuid:', existing_uuid or '(none)')
```

**Org confirmation (mandatory — runs every time, regardless of `assetUuid` state)**

**Step 1 — Navigate to the correct org:**

Check the profile for a saved `subscriptionId` (the CMS UI org identifier — captured from `<meta name="subscription-id">` on `connect/Content/content-library` during first upload; distinct from `acousticTenantId` which is used only for the CDN delivery URL):

```python
import json, pathlib, glob as _glob
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
p = json.loads((pathlib.Path(_dirs[0]) / '<SLUG>.json').read_text())
sub_id = p.get('acoustic', {}).get('subscriptionId', '')
print('subscriptionId:', sub_id or '(none)')
```

**Both first upload and re-upload use `?subId=` navigation.** The difference is only in how `subscriptionId` is obtained:

- **If `subscriptionId` is already in the profile** (re-upload or first upload resumed): navigate directly to `https://app.goacoustic.com/content/my-content?subId={subscriptionId}`. Wait 2s, then navigate to `https://app.goacoustic.com/content/items/assets`.
- **If `subscriptionId` is absent** (genuinely first upload, no prior CMS session): navigate to `https://app.goacoustic.com/connect/Content/content-library` first. Once loaded, read and immediately save the subscription meta tags:
  ```js
  JSON.stringify({
    subscriptionId: document.querySelector('meta[name="subscription-id"]')?.content,
    subscriptionName: document.querySelector('meta[name="subscription-name"]')?.content,
    operatorEmail: document.querySelector('meta[name="acoustic-id"]')?.content
  });
  ```
  Save `subscriptionId` to `profile.acoustic.subscriptionId`, `subscriptionName` to `profile.acoustic.contentOrgName`, and `operatorEmail` to `profile.acoustic.operatorEmail`. **Then immediately navigate via `?subId=`** — `https://app.goacoustic.com/content/my-content?subId={subscriptionId}`. Wait 2s, then navigate to `https://app.goacoustic.com/content/items/assets`.

> ⚠️ **Why `?subId=` is always required:** The Acoustic Connect (`/connect/...`) and Content Hub (`/content/...`) maintain independent tenant context. Reading meta tags from the Connect side does not force the Content Hub into the same org. The `?subId=` navigation is the only reliable way to set Content Hub tenant context — skipping it causes the registry API and all asset upload calls to operate on whichever org the browser last used in the Content Hub, which may be wrong even on a first upload.

Wait ~2s for the page to settle.

**Step 2 — Read org name via registry API:**

```js
const r = await fetch('https://app.goacoustic.com/content/api/registry/v1/currenttenant?fields=%2BcontentLocales', { credentials: 'include' });
const d = await r.json();
JSON.stringify({ acousticTenantId: d.acousticTenantId, name: d.name, status: r.status });
```

Extract `acousticTenantId` and `name` from the response.

**Step 3 — Show confirmation widget:**

Call `mcp__visualize__show_widget` (title: `org_confirmation`) — substitute `CUSTOMER_NAME`, `ORG_NAME` (from `d.name`, or `"Unknown — verify in tab"` if null), and `TENANT_SNIPPET` (first 8 chars of `acousticTenantId` + `"…"`, or `"not detected"`):

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:420px">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">Confirm Acoustic Connect org</div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:16px">Before accessing the Content Hub, confirm this tab is in the correct org.</div>
  <div style="background:var(--color-background-secondary);border-radius:var(--border-radius-md);padding:12px 14px;margin-bottom:16px;font-size:12px">
    <div style="display:flex;justify-content:space-between;margin-bottom:6px">
      <span style="color:var(--color-text-tertiary)">Detected org</span>
      <span style="font-weight:500;color:var(--color-text-primary)">ORG_NAME</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:6px">
      <span style="color:var(--color-text-tertiary)">Tenant ID</span>
      <span style="font-family:monospace;color:var(--color-text-secondary)">TENANT_SNIPPET</span>
    </div>
    <div style="border-top:0.5px solid var(--color-border-tertiary);margin:6px 0"></div>
    <div style="display:flex;justify-content:space-between">
      <span style="color:var(--color-text-tertiary)">Expected customer</span>
      <span style="font-weight:500;color:#706CFF">CUSTOMER_NAME</span>
    </div>
  </div>
  <div style="display:flex;gap:8px">
    <button onclick="sendPrompt('Org confirmed — correct org for CUSTOMER_NAME')" style="flex:1;background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 14px;font-size:12px;font-weight:500;cursor:pointer">✓ Yes — correct org</button>
    <button onclick="sendPrompt('Wrong org — need to switch')" style="flex:1;background:var(--color-background-secondary);color:var(--color-text-primary);border:0.5px solid var(--color-border-tertiary);border-radius:8px;padding:9px 14px;font-size:12px;cursor:pointer">Switch org</button>
  </div>
</div>
```

- If **"Switch org"**: pause and wait for the user to switch in the browser. Then re-run from Step 1 of this org confirmation block. Repeat until confirmed.
- If **"Org confirmed"**: persist `acousticTenantId` and `contentOrgName` to the profile immediately — always, not just on first upload. Run this Python before proceeding:

```python
import json, pathlib, glob as _glob
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
_pf = pathlib.Path(_dirs[0]) / '<SLUG>.json'
p = json.loads(_pf.read_text())
p.setdefault('acoustic', {})
p['acoustic']['acousticTenantId'] = '<acousticTenantId from Step 2>'
p['acoustic']['contentOrgName']   = '<name from Step 2>'
p['acoustic']['operatorEmail']    = '<operatorEmail from Step 1 meta[name=acoustic-id]>'
_pf.write_text(json.dumps(p, indent=2))
print('org saved:', p['acoustic']['acousticTenantId'], '/', p['acoustic']['contentOrgName'])
```

**If `assetUuid` is absent or empty → route to Step B immediately.** No further checks needed.

**If `assetUuid` is present → verify it still exists by navigating the browser directly to the asset API URL:**

Use `mcp__Claude_in_Chrome__navigate` to:
```
https://app.goacoustic.com/content/api/authoring/v1/assets/asset:{UUID}?include=metadata,links,review,draftLink
```
Replace `{UUID}` with `profile.acoustic.assetUuid` (e.g. `asset:a2439463-228d-4b99-8966-fb5e722aad3b`).

Then use `mcp__Claude_in_Chrome__get_page_text` to read the JSON response.

**Decision — this is the only routing point. Never override it based on Step 0 choice.**

| Profile state | Browser response | Route |
|---|---|---|
| `assetUuid` absent or empty | — | **Step B** — create new asset, new delivery URL |
| `assetUuid` present | JSON body with asset data (not 404) | **Step B2** — update in-place, delivery URL unchanged |
| `assetUuid` present | 404 / error / asset not found | **Step B** — treat as new; log that prior UUID was not found |

> ⚠️ **URL preservation rule:** If the asset is found, always use Step B2. Creating a new asset when one already exists would invalidate the customer's live GTM tag or `<script src>`.

**Step B — Upload SDK to the Media Gallery (Connect CMS) (new asset — direct API)**

Uses the Acoustic Connect CMS REST API directly from within the authenticated browser tab. No file picker, no iframe, no modal interaction. This approach was proven against a live EU tenant on 2026-07-20.

> **Narration rule — HARD STOP:** Immediately before starting any upload tool calls, call `mcp__visualize__show_widget` (title: `sdk_upload_progress`, loading: `"Uploading SDK config…"`) with the widget below. After that widget renders, execute B-3, B-3b, and B-4 **in complete silence** — zero prose, zero result echoes, zero confirmations between sub-steps. No chunk injection confirmations, no resource IDs, no asset IDs, no mediaIds, no "All N chunks injected" messages, no "Session 200 ✅" lines. Silence means silence: every word between the widget call and the final profile write is a T-11 defect. If a sub-step fails, emit the HTTP status code only. After the profile is written, emit `"Done — profile updated."` only.
>
> ```html
> <div style="padding:1.25rem 1.5rem;font-family:var(--font-sans);max-width:400px;display:flex;align-items:center;gap:14px">
>   <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#706CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;animation:spin 1.4s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
>   <span style="font-size:14px;color:var(--color-text-primary);font-weight:500">SDK config is being uploaded. Please wait.</span>
>   <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
> </div>
> ```

> **Page context guard rail:** The Acoustic Content authoring API is tenant-scoped. API calls made from `/content/my-content` or other hub pages return 404 tenant errors even with a valid session — the tenant context is only correct when the tab is at `/content/items/assets`. Before running any upload steps, silently navigate to `https://app.goacoustic.com/content/items/assets` using `mcp__Claude_in_Chrome__navigate` and wait ~2s for the page to load. Do not mention this navigation to the user.

> **Session guard rail:** After navigating to the assets page, probe the session with a lightweight GET. If the probe returns 401, 403, or redirects to the login page, pause immediately and call `mcp__visualize__show_widget` with the session-expired widget defined below. No prose before or after the widget. After the user clicks the button and responds, re-probe once. If still 403, stop and surface the error code only.

**Session probe (run before B-1, after navigating to /content/items/assets):**

```js
(async () => {
  await new Promise(r => setTimeout(r, 2000)); // wait for page context to settle
  const r = await fetch('/content/api/authoring/v1/assets?rows=1', {
    credentials: 'include',
    headers: { 'Accept': 'application/json' }
  });
  window.__sessionCheck = r.status; // 200 = active, 403/401 = expired
})();
'probe started';
```

Read `window.__sessionCheck` after ~3s. If `200`, proceed. If `401` or `403`, call `mcp__visualize__show_widget` with title `session_expired_gate` and the widget below — zero prose before or after:

> **If the probe returns 404 with a tenant error** (message contains "Tenant ID not found"): the tab navigated away from `/content/items/assets` mid-flow. Navigate back silently and re-probe once. This is an internal recovery step — do not surface it to the user.

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:420px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1.25rem">
    <div style="width:40px;height:40px;border-radius:50%;background:#FFF3CD;display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#B45309" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    </div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Media Gallery (Connect CMS) — session expired</div>
      <div style="font-size:12px;color:var(--color-text-tertiary);margin-top:4px">The upload step requires an active Acoustic Connect session. Please sign back in before continuing.</div>
    </div>
  </div>
  <ol style="margin:0 0 1.25rem 0;padding-left:1.25rem;font-size:12px;color:var(--color-text-secondary);line-height:1.8">
    <li>Go to <strong>app.goacoustic.com</strong> in Chrome</li>
    <li>Sign in with your Acoustic credentials</li>
    <li>Click <strong>Confirm</strong> below when ready</li>
  </ol>
  <button onclick="sendPrompt('I am signed in to Acoustic Connect — resume the upload')" style="width:100%;padding:10px 16px;background:#1F1E5D;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit">
    Confirm
  </button>
</div>
```

After the user clicks the button, re-probe once. If still 403, emit `"Session still returning 403 — please check you are in the correct org."` and stop.

The SDK config is ~40KB — too large for a single `javascript_tool` call. Split it into 5 chunks (~8KB each), inject into `window.__c[]`, join, then POST.

**B-1: Read and split the config using bash**

```bash
python3 - <<'EOF'
import math, re, sys
import glob as _g
_out = _g.glob('/sessions/*/mnt/SDK-config-assistant/outputs/{SLUG}/acoConnectSdkConfig-{SLUG}.js')
path = _out[0] if _out else f'/sessions/*/mnt/SDK-config-assistant/outputs/{{SLUG}}/acoConnectSdkConfig-{{SLUG}}.js'
content = open(path).read()
n = 5
sz = math.ceil(len(content) / n)
for i in range(n):
    chunk = content[i*sz:(i+1)*sz]
    print(f'--- CHUNK {i} ({len(chunk)} chars) ---')
    # Print first 80 chars to verify
    print(repr(chunk[:80]))
EOF
```

Replace `{SLUG}` with the actual slug (e.g. `acmeretail`). This verifies the file is readable and shows chunk boundaries. Claude then holds the full content in context for injection.

**B-2: Encode and inject via `javascript_tool` — base64 method (required)**

> **Why base64, not raw text:** The SDK config contains backticks, `${...}` template expressions, and backslashes. Embedding raw JS in a template literal inside a `javascript_tool` call requires three levels of escaping, which is error-prone and breaks on regeneration. Base64 encoding eliminates all escaping — only `[A-Za-z0-9+/=]` characters are ever injected. This approach is proven against production configs up to ~46 KB.

**Step 1 — Encode the config to base64 in bash:**

```bash
python3 - <<'EOF'
import base64, math, glob as _g, os
_f = _g.glob('/sessions/*/mnt/SDK-config-assistant/outputs/*/acoConnectSdkConfig-{SLUG}.js')
if not _f:
    _f = ['/root/.claude/skills/sdk-config-assistant/outputs/{SLUG}/acoConnectSdkConfig-{SLUG}.js']
content = open(_f[0], 'rb').read()
b64 = base64.b64encode(content).decode()
N_CHUNKS = 5
chunk_sz = math.ceil(len(b64) / N_CHUNKS)
chunks = [b64[i*chunk_sz:(i+1)*chunk_sz] for i in range(N_CHUNKS)]
PIECE_SZ = 2000  # max safe size per javascript_tool XML call
for ci, chunk in enumerate(chunks):
    pieces = [chunk[j*PIECE_SZ:(j+1)*PIECE_SZ] for j in range(math.ceil(len(chunk)/PIECE_SZ))]
    for pi, piece in enumerate(pieces):
        fname = f'/tmp/piece_{ci}_{pi}.js'
        open(fname, 'w').write(
            f'window.__b[{ci}] = (window.__b[{ci}] || "") + "{piece}"; "c{ci}p{pi}: " + window.__b[{ci}].length;'
        )
    print(f'chunk {ci}: {len(chunk)} chars → {len(pieces)} pieces')
print(f'total b64: {len(b64)} chars across {N_CHUNKS} chunks')
EOF
```

Replace `{SLUG}` with the actual slug. This writes `/tmp/piece_<chunk>_<piece>.js` files — one `javascript_tool` call per piece.

**Step 2 — Initialise `window.__b` and inject all pieces:**

```js
// Init (run once before injecting any pieces)
window.__b = [null, null, null, null, null];
'init';
```

For each `/tmp/piece_<C>_<P>.js`, read the file content with the `Read` tool and inject it exactly as written — **one `javascript_tool` call per piece, content from the file verbatim**:

```js
// Contents of /tmp/piece_0_0.js (example):
window.__b[0] = (window.__b[0] || "") + "KGZ1bmN0aW9uICgpIHsK..."; "c0p0: " + window.__b[0].length;
```

The return value (e.g. `"c0p0: 2000"`) confirms the running byte count. Continue for all pieces across all 5 chunks. After the final piece for each chunk, verify the length matches the expected chunk size.

> **Silence guardrail — ABSOLUTE:** Each piece injection is one `javascript_tool` call. Between every call, emit zero prose — no "chunk N injected", no char counts, no progress echoes. Only check the final per-chunk length. Silence means silence.

**B-3: Join, decode base64, and POST to /resources (single `javascript_tool` call)**

> **Important — async result capture:** `javascript_tool` does not automatically await top-level Promises. Store the result in `window.__uploadResult` and read it in a follow-up call after ~5 seconds.
>
> **Why base64 decode + Blob:** The SDK config contains backticks and `${...}` template expressions. Injecting raw text requires escaping; base64 does not. `atob()` decodes the assembled base64 string, a `Uint8Array` converts it to binary, and a `Blob` carries it as `application/javascript`. This is the proven pattern for production configs up to ~46 KB. Never use `window.__c` or send raw `jsContent` — use this approach only.

```js
// Call 1 — join base64 chunks, decode, and POST to /resources
window.__uploadResult = null;
window.__uploadError  = null;

(async () => {
  try {
    const b64 = window.__b[0] + window.__b[1] + window.__b[2] + window.__b[3] + window.__b[4];
    if (b64.length < 40000) { window.__uploadResult = 'ERROR short b64: ' + b64.length; return; }

    const binStr = atob(b64);
    const bytes  = new Uint8Array(binStr.length);
    for (let i = 0; i < binStr.length; i++) { bytes[i] = binStr.charCodeAt(i); }
    const blob     = new Blob([bytes], { type: 'application/javascript' });
    const filename = 'acoConnectSdkConfig-{SLUG}.js';

    const r1 = await fetch(
      '/content/api/authoring/v1/resources?name=' + encodeURIComponent(filename),
      { method: 'POST', credentials: 'include', body: blob }
    );
    if (!r1.ok) { window.__uploadResult = 'UPLOAD_FAILED ' + r1.status + ': ' + await r1.text(); return; }
    const res = await r1.json();
    window.__uploadResult = JSON.stringify({ resourceId: res.id, byteLength: blob.size });
  } catch(e) { window.__uploadError = e.message; }
})();
'upload started — read window.__uploadResult in ~5s';
```

```js
// Call 2 — read result (run ~5 seconds after Call 1)
JSON.stringify({ result: window.__uploadResult, error: window.__uploadError });
```

Parse `window.__uploadResult` to get `resourceId`.

**B-3b: Create asset record and publish**

POST /resources only uploads the raw file — it does not create an asset or publish it. Two more calls are required.

```js
// Call 1 — create asset record (auto-publishes immediately on 201)
window.__assetResult = null;
window.__assetError  = null;

(async () => {
  try {
    const resourceId = '{RESOURCE_ID}';  // from B-3 window.__uploadResult.resourceId
    const filename   = 'acoConnectSdkConfig-{SLUG}.js';

    const r2 = await fetch('/content/api/authoring/v1/assets', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ name: filename, resource: resourceId })
    });
    if (!r2.ok) { window.__assetResult = 'ASSET_FAILED ' + r2.status + ': ' + await r2.text(); return; }
    const { id: assetId, mediaId, fileSize } = await r2.json();
    window.__assetResult = JSON.stringify({ assetId, mediaId, fileSize });
  } catch(e) { window.__assetError = e.message; }
})();
'asset created — read window.__assetResult';
```

```js
// Call 2 — read result
JSON.stringify({ result: window.__assetResult, error: window.__assetError });
```

> **Note:** `POST /assets` auto-publishes the asset — no separate publish call needed. `publishing.status` will be `"available"` by the time B-4 runs.

Extract: `assetId`, `mediaId`, `fileSize`.

**B-4: Get asset details and delivery path via assets listing**

> **Why not the authoring search API?** The `/authoring/v1/search` endpoint with `document:[json]` field transformer returns error 1001 (unsupported transformer) on some tenants. The assets listing API is reliable and proven.

```js
(async () => {
  await new Promise(r => setTimeout(r, 2500)); // allow publish to propagate
  const filename       = 'acoConnectSdkConfig-{SLUG}.js';
  const assetId        = '{ASSET_ID}';          // from B-3b window.__assetResult.assetId
  const acousticTenantId = '{ACOUSTIC_TENANT_ID}'; // from profile.acoustic.acousticTenantId — CDN path prefix (NOT the meta-tag subscriptionId)
  const contentHost       = '{CONTENT_HOST}';       // from profile.acoustic.contentHost

  // Fetch the specific asset record directly — most reliable
  const ra = await fetch(
    '/content/api/authoring/v1/assets/' + assetId + '?include=metadata,links,review,draftLink',
    { credentials: 'include', headers: { Accept: 'application/json' } }
  );
  const da = await ra.json();

  if (da.path) {
    // Direct path available — construct delivery URL
    const deliveryUrl = 'https://' + contentHost + '/' + acousticTenantId + da.path;
    window.__b4Result = JSON.stringify({
      assetId: da.id, path: da.path, mediaId: da.mediaId,
      resourceId: da.resource,               // save to profile.acoustic.resourceId
      fileSize: da.fileSize,
      publishStatus: da.publishing?.status,  // expect "available"
      deliveryUrl
    });
  } else {
    // Fallback — scan assets listing for filename match
    const rl = await fetch(
      '/content/api/authoring/v1/assets?analyze=false&rows=50&sort=lastModified%20desc',
      { credentials: 'include', headers: { Accept: 'application/json' } }
    );
    const dl = await rl.json();
    const match = (dl.items || []).find(item => item.name === filename || item.fileName === filename);
    if (!match) { window.__b4Result = 'NOT_FOUND'; return; }
    const deliveryUrl = 'https://' + contentHost + '/' + acousticTenantId + match.path;
    window.__b4Result = JSON.stringify({
      assetId: match.id, path: match.path, mediaId: match.mediaId, fileSize: match.fileSize,
      publishStatus: match.publishing?.status,
      deliveryUrl
    });
  }
})();
'b4 started — read window.__b4Result in ~4s';
```

```js
JSON.stringify({ result: window.__b4Result });
```

Extract: `assetId`, `path`, `mediaId`, `resourceId` (from `da.resource`), `fileSize`, `publishStatus` (expect `"available"`), `deliveryUrl`. Carry all into the Persist profile step.

> **`contentHost` for new customers:** If the profile doesn't yet have `contentHost`, discover it from performance entries on any authenticated `app.goacoustic.com` page:
> ```js
> performance.getEntriesByType('resource')
>   .map(e => { const m = e.name.match(/^(https:\/\/content-[a-z0-9-]+\.content-cms\.com)/); return m?.[1]; })
>   .filter(Boolean)[0];
> ```
> For EU tenants the value is typically `content-eu-1.content-cms.com`. Save to `profile.acoustic.contentHost`.

After persisting the profile, show the `deployment` widget using `mcp__visualize__show_widget` (title: `deployment`, loading: `"Loading deployment instructions…"`). Use the platform-aware HTML below — substitute `{DELIVERY_URL}`, `{SDK_FILENAME}`, and `{PLATFORM}`:

**`deployment` widget HTML (substitute values before rendering):**

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:520px">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:1rem">
    <div style="width:36px;height:36px;border-radius:8px;background:#EEF0FF;display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#706CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
    </div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Deployment</div>
      <div style="font-size:12px;color:var(--color-text-tertiary);margin-top:2px">{SDK_FILENAME} · live on CDN</div>
    </div>
  </div>
  <div style="background:var(--color-background-secondary);border:1px solid var(--color-border-tertiary);border-radius:8px;padding:12px;margin-bottom:12px">
    <div style="font-size:11px;font-weight:600;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Add to &lt;head&gt;</div>
    <!-- Magento: -->
    <div style="font-size:11px;color:var(--color-text-secondary);margin-bottom:6px">Via Magento Admin → <strong>Content → Design → Configuration → HTML Head → Scripts and Style Sheets</strong>, or a custom module. Place after the GTM snippet and before <code>&lt;/head&gt;</code>:</div>
    <!-- Non-Magento (GTM): -->
    <!-- <div style="font-size:11px;color:var(--color-text-secondary);margin-bottom:6px">Add to GTM as a Custom HTML tag, firing on All Pages, sequenced after your GA4 base tag:</div> -->
    <code style="display:block;background:#1F1E5D;color:#C8FF49;font-size:11px;padding:10px 12px;border-radius:6px;word-break:break-all;font-family:monospace;line-height:1.5">&lt;script src="{DELIVERY_URL}" defer&gt;&lt;/script&gt;</code>
  </div>
  <div style="font-size:11px;color:var(--color-text-tertiary)">Test mode active — signals print to console only. No data sent to Connect until validation is complete and production mode is enabled.</div>
  <button onclick="sendPrompt('Deployment acknowledged')" style="margin-top:12px;width:100%;padding:9px 16px;background:#1F1E5D;color:#fff;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">Got it</button>
</div>
```

> **Platform note:** The widget above shows the Magento deployment path. For non-Magento platforms, uncomment the GTM comment block and remove the Magento-specific admin path text.

**Routing — `deployment` widget handler:**
- `'Deployment acknowledged'` → proceed to `signals_configured` widget (Step 14 gate). Do NOT write the Step 14 prose or run Step 14b before `signals_configured` fires.
- Derive test/production wording from the actual config state (`fakeSignals` value), not from a hardcoded string.
- For a re-upload: state that the delivery URL is unchanged.
- Do not claim "test mode active" after a production config upload.

Then **skip Step C** — proceed directly to **"Persist profile after upload"**.

> ❌ **If B-3 returns non-200:** Check the user is logged in to the correct org. Re-run from B-3 after confirming auth.
> ❌ **If B-3b asset POST returns 400 "resource not found":** The B-3 upload silently failed — re-run from B-3.
> ❌ **If B-4 returns `NOT_FOUND`:** Wait 5s and retry. If still missing, check `publishing.status` via `GET /assets/{assetId}?include=metadata`.
> ❌ **If `publishStatus` is not `"available"` after 10s:** Re-run the B-4 GET call — publishing propagation sometimes lags.
> ❌ **If the delivery URL 403s from browser/curl:** Expected — the CDN blocks CORS and sandbox requests. The asset IS live; test via Tampermonkey `@require` or a `<script>` tag on the customer's page.

**Step B2 — Re-upload to an existing asset (update in-place, API)**

> Use this path when **Step A2** confirms the asset exists. Uses the same API approach as Step B — but instead of creating a new asset, replaces the resource on the existing one. The `assetUuid` and delivery URL remain unchanged.

**Narration rule — HARD STOP:** Call `mcp__visualize__show_widget` (title: `sdk_upload_progress`) before any upload tool calls. Execute B-1 through B-4 in complete silence.

> **Org navigation for re-upload:** Use the `subscriptionId` saved in the profile (captured from `<meta name="subscription-id">` on first upload) to land in the correct org. Navigate to `https://app.goacoustic.com/content/my-content?subId={subscriptionId}`. Wait 2s for the page to settle, then navigate to `https://app.goacoustic.com/content/items/assets/asset:{assetUuid}` — this both sets the correct tenant context for API calls and lets the user visually confirm the right asset. Show the org confirmation widget (Step A2, Step 3) after navigating — read the subscription meta tags to verify:
> ```js
> JSON.stringify({
>   subscriptionId: document.querySelector('meta[name="subscription-id"]')?.content,
>   subscriptionName: document.querySelector('meta[name="subscription-name"]')?.content,
>   operatorEmail: document.querySelector('meta[name="acoustic-id"]')?.content
> });
> ```
> Match against `profile.acoustic.subscriptionId` and `profile.acoustic.contentOrgName`. If mismatch, pause and ask user to confirm they are in the correct org.

Then call `mcp__visualize__show_widget` (title: `sdk_upload_progress`) with the spinner widget from Step B.

> **Page context guard rail:** The tab must remain on `https://app.goacoustic.com/content/items/assets/asset:{assetUuid}` (or `/content/items/assets`) for all API calls. Session guard rail applies — probe session and render `session_expired_gate` widget if `401`/`403`.

**Why the delivery URL never changes:** The delivery URL encodes `assetUuid` in the CDN path (`/dxdam/{prefix}/{assetUuid}/{filename}`). `PUT /assets/{uuid}` only swaps the `resource` pointer inside the record — the UUID is never touched, so the path is structurally immutable. The customer's GTM tag or Tampermonkey `@require` serves the new file automatically with no change needed on their end.

**2. B-1: GET current asset state**

Before uploading, read the asset record. This confirms the asset exists, captures the current `resourceId`, and verifies the delivery path:

```js
(async () => {
  const assetUuid = '{ASSET_UUID}';  // profile.acoustic.assetUuid
  const r = await fetch(
    '/content/api/authoring/v1/assets/asset:' + assetUuid + '?include=metadata,links,review,draftLink',
    { credentials: 'include', headers: { Accept: 'application/json' } }
  );
  const d = await r.json();
  window.__b2AssetState = JSON.stringify({
    assetId: d.id, fileName: d.fileName, path: d.path,
    rev: d.rev,               // REQUIRED for PUT — must be included in B-4 body
    resourceId: d.resource,   // current resource — will be replaced
    mediaId: d.mediaId, fileSize: d.fileSize,
    publishStatus: d.publishing?.status
  });
})();
'b2 asset state — read window.__b2AssetState in ~3s';
```

```js
JSON.stringify({ result: window.__b2AssetState });
```

Confirm `publishStatus: "available"` and note the existing `resourceId`. Proceed to chunk injection.

**3. B-2: Read and split the config**

Same bash command as Step B — replace `{SLUG}` with the actual slug.

**4. B-3: Inject chunks via `javascript_tool` (5 calls)**

Same as Step B. The page context is already correct from org navigation — no additional navigation needed.

**5. B-4: POST /resources + PUT /assets + POST /publish**

```js
// Call 1 — decode base64 chunks, POST new resource blob, then PUT to swap on existing asset, then publish
// NOTE: window.__b[] must already be populated via B-2 chunk injection before running this call.
window.__b2UpdateResult = null;
window.__b2UpdateError  = null;

(async () => {
  try {
    const assetUuid = '{ASSET_UUID}';    // profile.acoustic.assetUuid
    const assetRev  = '{ASSET_REV}';    // profile.acoustic.assetRev — REQUIRED by PUT; fetch fresh from B-1 GET
    const filename  = 'acoConnectSdkConfig-{SLUG}.js';

    // Decode base64 → Uint8Array → Blob (same as Step B B-3; never use raw text)
    const b64 = window.__b[0] + window.__b[1] + window.__b[2] + window.__b[3] + window.__b[4];
    if (b64.length < 40000) { window.__b2UpdateResult = 'ERROR short b64: ' + b64.length; return; }
    const binStr = atob(b64);
    const bytes  = new Uint8Array(binStr.length);
    for (let i = 0; i < binStr.length; i++) { bytes[i] = binStr.charCodeAt(i); }
    const blob = new Blob([bytes], { type: 'application/javascript' });

    // Step 1: Upload new resource blob — returns a fresh resourceId
    const r1 = await fetch(
      '/content/api/authoring/v1/resources?name=' + encodeURIComponent(filename),
      { method: 'POST', credentials: 'include', body: blob }
    );
    if (!r1.ok) { window.__b2UpdateResult = 'RESOURCE_FAILED ' + r1.status + ': ' + await r1.text(); return; }
    const res = await r1.json();
    const newResourceId = res.id;

    // Step 2: Swap resource on the SAME asset UUID — delivery URL is unchanged by design
    // REQUIRED: include rev — omitting it returns error 3013 "No rev was provided"
    const r2 = await fetch('/content/api/authoring/v1/assets/' + assetUuid, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ id: assetUuid, rev: assetRev, resource: newResourceId })
    });
    if (!r2.ok) { window.__b2UpdateResult = 'PUT_FAILED ' + r2.status + ': ' + await r2.text(); return; }
    const updated = await r2.json();

    // Step 3: Re-publish (PUT auto-publishes on most tenants — publish call may return 404; asset will still be "available")
    const r3 = await fetch('/content/api/authoring/v1/publish', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ items: [{ id: assetUuid, classification: 'asset' }] })
    });

    window.__b2UpdateResult = JSON.stringify({
      assetId: updated.id,        // same as profile.acoustic.assetUuid — confirmed unchanged
      newRev: updated.rev,        // save to profile.acoustic.assetRev for next re-upload
      newResourceId,              // save to profile.acoustic.resourceId
      mediaId: updated.mediaId,
      fileSize: updated.fileSize,
      publishCallStatus: r3.status  // 200 or 404 — both OK; verify with B-5
    });
  } catch(e) { window.__b2UpdateError = e.message; }
})();
'b2 update started — read window.__b2UpdateResult in ~5s';
```

```js
// Call 2 — read result (~5s later)
JSON.stringify({ result: window.__b2UpdateResult, error: window.__b2UpdateError });
```

Extract: `assetId` (same as profile — confirms UUID unchanged), `newResourceId` (save to `profile.acoustic.resourceId`), `mediaId`, `fileSize`, `publishCallStatus` (expect `200`).

**6. B-5: Confirm publish**

```js
(async () => {
  await new Promise(r => setTimeout(r, 2500));
  const r = await fetch(
    '/content/api/authoring/v1/assets/asset:{ASSET_UUID}?include=metadata,links,review,draftLink',
    { credentials: 'include', headers: { Accept: 'application/json' } }
  );
  const d = await r.json();
  window.__b2ConfirmResult = JSON.stringify({
    assetId: d.id, resourceId: d.resource, mediaId: d.mediaId,
    fileSize: d.fileSize, publishStatus: d.publishing?.status
  });
})();
'b2 confirm — read window.__b2ConfirmResult in ~3s';
```

```js
JSON.stringify({ result: window.__b2ConfirmResult });
```

Expect `publishStatus: "available"`. If not yet available, wait 5s and retry once.

**7. Present success widget**

**Delivery URL is unchanged** — same `assetUuid`, same CDN path. Present via `show_widget` (title: `sdk_updated`):

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:12px">
    SDK updated ✅
  </div>
  <div style="display:flex;flex-direction:column;gap:6px">
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:8px 14px;font-size:12px">
      <span style="color:var(--color-text-tertiary)">Filename</span> &nbsp; <span style="font-family:monospace">SDK_FILENAME</span>
    </div>
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:8px 14px;font-size:12px">
      <span style="color:var(--color-text-tertiary)">Delivery URL</span> &nbsp;
      <span style="font-family:monospace;color:#706CFF;font-size:11px;word-break:break-all">DELIVERY_URL</span>
    </div>
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:8px 14px;font-size:12px;color:var(--color-text-secondary)">
      ℹ️ Delivery URL unchanged — the customer's GTM tag and Tampermonkey <code>@require</code> automatically serve the updated file. No change needed on the customer side.
    </div>
  </div>
</div>
```

Substitute `SDK_FILENAME` and `DELIVERY_URL` from `profile.acoustic`.

Then show the `deployment` widget (same HTML template as Step B above — title: `deployment`), substituting `{DELIVERY_URL}` and `{SDK_FILENAME}` from the profile. For a re-upload the customer's `<script>` tag is already in place — the note in the widget reminds them no change is needed on their end. Platform-specific instruction text still applies (Magento vs GTM).

Then **skip Step C** — proceed directly to "Persist profile after upload".

> ❌ **If B-1 GET returns 404:** Asset UUID in profile is stale — route to Step B (new asset) instead.
> ❌ **If POST /resources returns non-200:** Session may have expired — probe and render `session_expired_gate` widget. Navigate back to `content/items/assets` and re-probe before retrying.
> ❌ **If PUT returns 400 error 3013 ("No rev was provided"):** The `rev` field was omitted from the PUT body. Fetch the current rev from B-1 GET (`d.rev`) and include it as `rev: assetRev` in the PUT body.
> ❌ **If PUT returns 400 error 3003 ("type modified"):** The asset's `mediaType` was originally stored as `multipart/form-data; boundary=...` (FormData upload bug). Delete the asset (`DELETE /authoring/v1/assets/{uuid}`), re-run Step B uploading the resource as raw text with `Content-Type: application/javascript;charset=UTF-8`, then the new asset will support B2 re-uploads correctly.
> ❌ **If publish call returns 404:** PUT auto-publishes the asset on most tenants — the 404 is expected. Verify with B-5 GET; `publishStatus` should be `"available"`.
> ❌ **If `publishStatus` is not `"available"` after 10s:** Re-run the B-5 confirm GET — publishing propagation sometimes lags.


---

**Step C — Get the Delivery URL from the Media Gallery (Connect CMS)**

> **When to use Step C:** Step C is no longer required for Step B or Step B2. Both paths now use the direct API — Step B gets the delivery URL from B-4; Step B2 reads the delivery URL from the profile (unchanged). Step C is retained as a fallback only, if B-4 fails to return a path for Step B.


After a successful upload, retrieve the CDN Delivery URL programmatically. No manual navigation, no modal clicks required — the delivery URL is constructed entirely from two API calls that work on any Connect CMS page.


Run this JavaScript while still on `app.goacoustic.com/connect/Content/content-library` (the upload page from Step B):

```js
// Step 1 — Delivery host: always present in performance entries because the Connect CMS
// loads auth resources from content-us-N.content-cms.com on every page load.
const deliveryHost = performance.getEntriesByType('resource')
  .map(e => { const m = e.name.match(/^(https:\/\/content-us-\d+\.content-cms\.com)/); return m?.[1]; })
  .filter(Boolean)[0];

// Step 2 — Asset URL: query the delivery search API by exact filename.
// Returns doc.url = "/<tenant-id>/dxdam/<xx>/<uuid>/<filename>" — unique per org.
const fileName = 'acoConnectSdkConfig-<slug>.js'; // use the filename from Step A
const r = await fetch(
  `/content/api/delivery/v1/search?q=name:${encodeURIComponent('"' + fileName + '"')}&fl=document:[json],*&sort=lastModified%20desc&rows=1`
);
const d = await r.json();
const assetUrl = d.documents?.[0]?.url;

// Step 3 — Construct the full Delivery URL.
const deliveryUrl = deliveryHost && assetUrl ? deliveryHost + assetUrl : null;
JSON.stringify({ deliveryHost, assetUrl, deliveryUrl });
```

**Why this works:**
- `deliveryHost` — the Connect CMS always loads `/login/v1/provider/commonui` from `content-us-N.content-cms.com`, so the correct host is always in `performance.getEntriesByType('resource')`. This value is org-specific and changes per customer tenant.
- `assetUrl` — the delivery search API returns a `url` field shaped `/<tenant-id>/dxdam/<first2>/<uuid>/<filename>`. This is the tenant-relative path Acoustic's CDN uses.
- Combining them gives the full public Delivery URL — identical to what the "API information" modal shows in the Connect CMS UI.

If `deliveryUrl` is null (rare — the page loaded before performance entries were populated), **do not navigate away**. Instead wait 1000ms and re-run the same snippet on the current content-library page. Only if it fails a second time: use the delivery search API result's `url` field directly by prepending `https://content-us-N.content-cms.com` (substitute N from the tenant). Do not navigate to `/content/my-content`.

**Present the Delivery URL to the customer** using `mcp__visualize__show_widget`:

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:12px">
    SDK uploaded to the Media Gallery (Connect CMS) ✅
  </div>
  <div style="display:flex;flex-direction:column;gap:8px">
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px">
      <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Filename</div>
      <div style="font-family:monospace;font-size:12px;color:var(--color-text-primary)">SDK_FILENAME</div>
    </div>
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px">
      <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Delivery URL (share with customer)</div>
      <div style="display:flex;align-items:center;gap:8px">
        <div style="font-family:monospace;font-size:11px;color:#706CFF;word-break:break-all;flex:1">DELIVERY_URL</div>
        <button onclick="navigator.clipboard.writeText('DELIVERY_URL').then(()=>{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)})" style="background:#706CFF;color:#fff;border:none;border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer;white-space:nowrap;flex-shrink:0">Copy</button>
      </div>
    </div>
    <div style="background:var(--color-background-secondary);border-radius:8px;padding:10px 14px;font-size:11px;color:var(--color-text-secondary)">
      <div style="font-weight:500;margin-bottom:6px">How to use</div>
      <div style="margin-bottom:4px">🔬 <strong>Tampermonkey:</strong> Paste the Delivery URL as the <code>@require</code> value in the Tampermonkey header.</div>
      <div>🚀 <strong>Production (GTM / page tag):</strong> Add a Custom HTML tag in GTM with <code>&lt;script src="DELIVERY_URL"&gt;&lt;/script&gt;</code> and set the trigger to "All Pages".</div>
    </div>
  </div>
</div>
```

Substitute `SDK_FILENAME` and `DELIVERY_URL` with the values retrieved by the JS snippet above.

**After displaying the delivery URL widget**, check the profile for any escalated signals and conditionally add a note:

```python
import json, pathlib, glob as _glob
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile_path = pathlib.Path(_dirs[0]) / '<SLUG>.json'
profile = json.loads(profile_path.read_text())
escalated = [
    sig for sig, st in profile.get('acoustic', {}).get('signalStatus', {}).items()
    if st.get('completed') == False
]
print('escalated:', escalated)
```

If `escalated` is non-empty, show an additional `show_widget` (title: `delivery_escalation_note`, loading: `"Loading…"`). Substitute `ESCALATED_SIGNAL_ROWS` with one row per escalated signal:

```html
<div style="padding:0.75rem 0;font-family:var(--font-sans)">
  <div style="background:#FFF8E8;border-left:3px solid #F0C040;border-radius:8px;padding:12px 16px">
    <div style="font-size:12px;font-weight:600;color:#7A6800;margin-bottom:8px">⚠️ Signals requiring Acoustic Services assistance</div>
    <div style="font-size:11px;color:#7A6800;margin-bottom:10px">
      The following signals were not configured by this skill. Please provide the SDK config above to your Acoustic Services contact so they can assist:
    </div>
    <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:10px">
      <!-- ESCALATED_SIGNAL_ROWS -->
      <div style="font-family:monospace;font-size:11px;color:#b45309;padding:4px 8px;background:rgba(180,83,9,0.08);border-radius:4px">• SIGNAL_KEY</div>
      <!-- END ESCALATED_SIGNAL_ROWS -->
    </div>
    <div style="font-size:10px;color:#7A6800;border-top:1px solid #F0C040;padding-top:8px;margin-top:4px">
      Share the Delivery URL above with both your developer and your Acoustic Services contact.
    </div>
  </div>
</div>
```

> **If the delivery URL cannot be retrieved programmatically** (e.g. performance entries are empty after two retries): tell the user to click the three-dot menu on the SDK row in the content library → **"API information"**, and share the Delivery URL. Stay on `https://app.goacoustic.com/connect/Content/content-library` — do not navigate away. Then present it using the widget above.

**Persist profile after upload** — save all delivery fields back to the website profile JSON and write it to the persistent profiles index so it can be reused on future runs.

Fields to persist (from B-3/B-4 for API upload, or from Step C for UI re-upload):

| Field | Source |
|---|---|
| `acoustic.assetUuid` | `assetId` from B-4 search `document.id` |
| `acoustic.assetRev` | `rev` from B-1 GET (B2 path) or B-4 GET (Step B path) — required for future B2 PUT |
| `acoustic.resourceId` | `resourceId` from B-3 POST `/resources` response |
| `acoustic.mediaId` | `mediaId` from B-4 search `document.mediaId` |
| `acoustic.fileSize` | `fileSize` from B-4 search `document.fileSize` |
| `acoustic.assetStatus` | `status` from GET /assets/{id}?include=metadata (`"ready"`) |
| `acoustic.assetPath` | `path` from assets listing API (`/dxdam/{hash}/{assetId}/{filename}`) |
| `acoustic.contentHost` | CDN hostname from assets listing API or profile (e.g. `content-eu-1.static.content-cms.com`) |
| `acoustic.deliveryUrl` | constructed: `https://{contentHost}/{subscriptionId}{assetPath}` (dxdam format) |
| `acoustic.acousticTenantId` | `acousticTenantId` from registry API (Step A2 org confirmation) |
| `acoustic.contentOrgName` | `name` from registry API (Step A2 org confirmation) |
| `acoustic.operatorEmail` | `operatorEmail` from `meta[name="acoustic-id"]` on `connect/Content/content-library` (Step A2) |

```python
import json, pathlib, shutil, glob as _glob

profile_path = pathlib.Path("/absolute/path/to/<slug>-customer-signal-config.json")
profile = json.loads(profile_path.read_text())

# --- Supply these from the upload result ---
# After Step B  (API flow): from window.__uploadResult (B-3) and asset detail API (B-4)
# After Step B2 (UI flow):  asset_uuid/media_id from Step C; status from asset detail API
asset_uuid      = "<assetId from B-3>"        # e.g. "15249a9e-3fb2-43af-8728-91b19038cb8a"
media_id        = "<mediaId from B-3>"        # e.g. "484cc210-d1dd-415d-bfed-1ad76fbb6d73"
file_size       = 0                           # int, from B-3 fileSize field
asset_status    = "ready"                     # from B-4 GET /assets/{id}?include=metadata
asset_path      = "<path from B-4 assets listing>"  # e.g. "/dxdam/15/15249a9e-.../acoConnectSdkConfig-acmeretail.js"
content_host    = "<CDN hostname>"            # e.g. "content-eu-1.static.content-cms.com"
subscription_id = profile["acoustic"]["subscriptionId"]
delivery_url    = f"https://{content_host}/{subscription_id}{asset_path}"

profile.setdefault("acoustic", {})
profile["acoustic"]["assetUuid"]        = asset_uuid
profile["acoustic"]["mediaId"]          = media_id
profile["acoustic"]["fileSize"]         = file_size
profile["acoustic"]["assetStatus"]      = asset_status
profile["acoustic"]["assetPath"]        = asset_path    # /dxdam/{hash}/{assetId}/{filename}
profile["acoustic"]["contentHost"]      = content_host  # CDN hostname
profile["acoustic"]["deliveryUrl"]      = delivery_url  # https://{contentHost}/{subscriptionId}{assetPath}
# Org identity — from registry API at Step A2; enables subId navigation on future re-uploads
profile["acoustic"]["acousticTenantId"] = acoustic_tenant_id  # from Step A2 registry API
profile["acoustic"]["contentOrgName"]   = content_org_name    # from Step A2 registry API

# Mark validation complete if this was a test-to-production push
if profile["acoustic"].get("sdkBundle", {}).get("validated") == False:
    profile["acoustic"]["sdkBundle"]["validated"] = True
    profile["acoustic"]["sdkBundle"]["mode"] = "production"

# Do NOT auto-pass signals that were not explicitly validated.
# Only signals marked validationResult='passed' in the matrix already have completed=True.
# Blocked, not_tested, and pending signals retain completed=None — they are recorded as exceptions.
# Escalated signals retain completed=False.
# No automatic state change here.
signal_status = profile["acoustic"].get("signalStatus", {})
# Verify: log the final state for diagnostics
for sig, st in signal_status.items():
    print(f"  {sig}: completed={st.get('completed')}, result={st.get('validationResult','pending')}, attempts={st.get('attempts',0)}")

# Mark the overall SDK configuration as complete
profile["acoustic"]["sdkConfigurationComplete"] = True

# Write updated profile back
profile_path.write_text(json.dumps(profile, indent=2))

# Copy to persistent profiles/ index so Step 0 can find it next time
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not _dirs:
    raise SystemExit('Profiles root not found — no folder added to this session. Re-run the Pre-step storage check.')
profiles_dir = pathlib.Path(_dirs[0])
profiles_dir.mkdir(parents=True, exist_ok=True)
slug = profile_path.stem.replace("-customer-signal-config", "")
dest = profiles_dir / f"{slug}.json"
shutil.copy(profile_path, dest)
print(f"Profile saved → {dest}")
```

> **Note on paths**: The `profiles/` directory is in the added folder (`SDK-config-assistant/profiles/`). This persists between sessions. The website profile used as the source is the `-customer-signal-config.json` file the generator produces — it already contains all signal mappings. We save a copy here so Step 0 can list and reload it.

---

### 11. Apply post-generation manual edits

> ⛔ **PRIMARY TASK — TODO resolution.** Before anything else, confirm the TODO scan in Step 9C ran and returned 0. If it did not run, run it now. If any `// TODO:` lines remain in the config, resolve them before continuing. Every unresolved TODO is a field that sends nothing to Acoustic — a complete capture failure.

Two additional categories always require manual edits after generation (on top of TODO resolution):

**Entity ID strip** — when a DOM element ID encodes a product/entity ID with a prefix:
```js
// Replace generated line:
signal.productId = help.cssGet("button[id^='buy_']", "id");
// With:
signal.productId = (help.cssGet("button[id^='buy_']","id")||'').replace(/^buy_/,'') || null;
```

**Site-specific result count** — when `numberOfResults` comes from dataLayer, not a DOM element:
```js
// Replace generated DOM selector block with:
const dlEntry = (window.dataLayer||[]).find(function(e){ return e.fhTotal != null; });
signal.numberOfResults = dlEntry ? parseInt(dlEntry.fhTotal) : null;
```

Document all manual edits in the implementation review so they survive a regeneration cycle.

---

### 12. Review generated JavaScript

Confirm:

- `errorLog: true`, `eventLog: false`, `signalsLog: true`, `fakeSignals: true` in test mode
- `errorLog: false`, `eventLog: false`, `signalsLog: true`, `fakeSignals: false` in production mode
- Email stored to `sessionStorage` only, with regex validation before storage
- `return false` (not null) when required fields are absent
- No passwords, payment data, or PII in any field extraction
- `effect` uses `"positive"` / `"negative"` spellings only
- No duplicate signal emissions on page refresh
- All `triggers` attributes match confirmed Type 4 evidence

---

### 13. Verify in browser — final confirmation gate

Read the current signal status to determine what still needs attention:

```python
import json, pathlib, glob as _glob
_dirs = _glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
profile       = json.loads((pathlib.Path(_dirs[0]) / '<SLUG>.json').read_text())
ss            = profile['acoustic']['signalStatus']
corrected     = [s for s, v in ss.items() if v.get('correctionHistory') and v.get('validationResult') != 'escalated']
still_pending = [s for s, v in ss.items() if v.get('validationResult') in ('pending','issue_found') and v.get('completed') is not False]
passed        = [s for s, v in ss.items() if v.get('completed') is True]
escalated     = [s for s, v in ss.items() if v.get('completed') is False]
exceptions    = [s for s, v in ss.items() if v.get('validationResult') in ('blocked','not_tested')]
print('corrected (needs retest confirm):', corrected)
print('still pending:', still_pending)
print('passed:', passed)
print('escalated:', escalated)
print('exceptions:', exceptions)
```

Use `AskUserQuestion` with this question and two options, showing only relevant signal groups:

**Question:** `"Have you verified the corrected signals in the browser?"`

- **"Yes — signals verified"** — proceed to Step 10-pre (deployment choice). Only ask this after at least one corrected or previously unresolved signal has been confirmed.
- **"Not yet"** — direct the user to the generated test guide (`How to test and validate the data.md`) for setup instructions, then tell them to navigate the customer's site and check the browser console for signal log lines. Wait for confirmation before proceeding.

Do not ask already-passed signals to be re-validated. Show only corrected or pending signals in the question context. Escalated and accepted-exception signals are reported but do not block this gate.

After the user confirms signals are verified, navigate the customer journey and confirm:

- Every page load produces a Type 2 console message with correct URL/title
- Clicking Add to Bag produces a Type 4 followed immediately by a Type 5 `logSignal` (addToCart payload)
- Type 5 signal payload has no null required fields, correct types, no PII
- `onSiteSearch` Type 5 fires on search results page with correct `numberOfResults` and `effect`
- `identification` Type 5 fires on sign-in or registration form submit (not newsletter/marketing forms)
- `order` Type 5 fires on confirmation page, not on back-navigation/refresh
- `productConfiguration` Type 5 fires on each colour/size/qty interaction with correct `configurationType` and `actionState`; `productId` and `productName` are non-null; no duplicate fires on the same interaction

Read [references/sdk-console-messages.md](references/sdk-console-messages.md) for the full Type 2/4/5 structure reference.

---

### Step 10-pre — Deployment choice

> ⛔ **GUARDRAIL — every tier, after Steps 11, 12, and 13.** This step runs for Pro, Premium, and Ultimate alike once Steps 11, 12, and 13 are all confirmed complete. There is no tier that skips it, and no tier that goes straight to upload.

Show the deployment choice widget using `mcp__visualize__show_widget` (title: `deployment_choice`, loading: `"Loading deployment options…"`). Option 1 is pre-selected by default — the Continue button starts active.

```html
<style>
.ep{font-family:var(--font-sans);padding:.75rem 0}
.section-title{font-size:14px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px}
.section-sub{font-size:12px;color:var(--color-text-secondary);margin-bottom:16px}
.pills{display:flex;flex-direction:column;gap:8px}
.pill{border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;border-radius:10px;padding:12px 14px;display:flex;gap:10px;align-items:flex-start;text-align:left;position:relative;transition:border-color .15s,background .15s}
.pill.sel{border-color:#706CFF;background:#EEF0FF;color:#1F1E5D}
.pill.sel .chk{display:flex!important}
.chk{display:none;position:absolute;top:8px;right:10px;width:16px;height:16px;background:#706CFF;border-radius:50%;align-items:center;justify-content:center;font-size:9px;color:#fff;font-weight:700;line-height:1}
.pill-label{font-size:12px;font-weight:600}
.pill-desc{font-size:11px;color:var(--color-text-tertiary);margin-top:2px}
.pill.sel .pill-desc{color:#706CFF}
.default-badge{display:inline-block;background:#00DF8F;color:#1F1E5D;font-size:9px;font-weight:700;border-radius:4px;padding:1px 6px;margin-left:6px;vertical-align:middle;text-transform:uppercase;letter-spacing:.04em}
.btn-cont{background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;width:100%;margin-top:12px;cursor:pointer;transition:opacity .15s;font-family:inherit}
</style>
<div class="ep">
  <div class="section-title">How would you like to deploy the SDK config?</div>
  <div class="section-sub">Choose how the customer's SDK config file will be served to their website.</div>
  <div class="pills" id="dp">
    <button type="button" class="pill sel" data-value="download_and_host" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div>
        <div class="pill-label">⬇ Download and host it <span class="default-badge">Recommended</span></div>
        <div class="pill-desc">Hand the SDK config file over for the customer to upload to their own web server.</div>
      </div>
    </button>
    <button type="button" class="pill" data-value="other_options" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div>
        <div class="pill-label">⋯ Other options</div>
        <div class="pill-desc">Host in the Media Gallery (Connect CMS) or other deployment methods.</div>
      </div>
    </button>
  </div>
  <input type="hidden" id="f-deploy" value="download_and_host"/>
  <button class="btn-cont" onclick="sub()">Continue</button>
</div>
<script>
function sp(b){document.querySelectorAll('#dp .pill').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');document.getElementById('f-deploy').value=b.getAttribute('data-value');}
function sub(){sendPrompt('Deployment choice: '+document.getElementById('f-deploy').value);}
</script>
```

---

#### When `sendPrompt` fires `'Deployment choice: download_and_host'`

Call `mcp__cowork__present_files` with the SDK config file path (the `acoConnectSdkConfig-<slug>.js` file in the customer's output directory).

Then show the hosting instructions widget using `mcp__visualize__show_widget` (title: `deployment_instructions`, loading: `"Loading hosting instructions…"`). Substitute `<FILENAME>` with the actual config filename (e.g. `acoConnectSdkConfig-acmeretail.js`):

```html
<div style="font-family:var(--font-sans);padding:.75rem 0;max-width:540px">
  <div style="font-size:14px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">Deploy the Connect SDK config on your website</div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:16px">Follow these steps to host the customised JavaScript file on your web server.</div>
  <div style="display:flex;flex-direction:column;gap:12px">
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div style="width:22px;height:22px;border-radius:50%;background:#1F1E5D;color:#C8FF49;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">1</div>
      <div style="font-size:12px;color:var(--color-text-primary);padding-top:2px">Upload the customised JavaScript file to your web server — for example, to the root directory or a dedicated <code>scripts/</code> directory.</div>
    </div>
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div style="width:22px;height:22px;border-radius:50%;background:#1F1E5D;color:#C8FF49;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">2</div>
      <div style="font-size:12px;color:var(--color-text-primary);padding-top:2px">In your webpage template, add the following code snippet anywhere within the <code>&lt;head&gt;</code> tag. In the <code>src</code> attribute, specify the path to the custom JavaScript file.
        <div style="background:#1F1E5D;border-radius:6px;padding:10px 14px;margin-top:8px;font-family:monospace;font-size:11px;color:#C8FF49;word-break:break-all">&lt;script src="scripts/&lt;FILENAME&gt;"&gt;&lt;/script&gt;</div>
      </div>
    </div>
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div style="width:22px;height:22px;border-radius:50%;background:#1F1E5D;color:#C8FF49;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">3</div>
      <div style="font-size:12px;color:var(--color-text-primary);padding-top:2px">Push the changes to the server.</div>
    </div>
  </div>
  <div style="margin-top:14px;background:#FEF9C3;border:1px solid #FDE68A;border-radius:8px;padding:10px 14px;font-size:11px;color:#854D0E"><strong>⚠ Warning</strong> — If possible, avoid bundling the Connect SDK config JavaScript with other JavaScript files.</div>
  <div style="margin-top:14px">
    <div style="font-size:12px;font-weight:600;color:var(--color-text-primary);margin-bottom:8px">Setup verification</div>
    <div style="font-size:11px;font-weight:600;color:var(--color-text-secondary);margin-bottom:4px">Basic</div>
    <ul style="font-size:11px;color:var(--color-text-secondary);margin:0 0 0 16px;padding:0;line-height:1.7">
      <li>Open browser developer tools and check for signals being posted to the collector URL</li>
      <li>Check for signal messages in the browser console</li>
    </ul>
    <div style="font-size:11px;font-weight:600;color:var(--color-text-secondary);margin-top:10px;margin-bottom:4px">Thorough</div>
    <div style="font-size:11px;color:var(--color-text-secondary)">Go to <strong>Signal Management</strong> in the Acoustic Connect UI and check for signals.</div>
  </div>
  <button onclick="sendPrompt('Deployment instructions acknowledged — proceed to final response')" style="width:100%;margin-top:14px;padding:9px 16px;background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">Continue</button>
</div>
```

When `sendPrompt` fires `'Deployment instructions acknowledged — proceed to final response'`: proceed directly to **Step 14**. Do not run Step 10.

---

#### When `sendPrompt` fires `'Deployment choice: other_options'`

Show the secondary deployment widget using `mcp__visualize__show_widget` (title: `deployment_choice_cms`, loading: `"Loading…"`). The Continue button starts disabled — it activates only when the user explicitly selects the option:

```html
<style>
.ep{font-family:var(--font-sans);padding:.75rem 0}
.section-title{font-size:14px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px}
.section-sub{font-size:12px;color:var(--color-text-secondary);margin-bottom:16px}
.pills{display:flex;flex-direction:column;gap:8px}
.pill{border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;border-radius:10px;padding:12px 14px;display:flex;gap:10px;align-items:flex-start;text-align:left;position:relative;transition:border-color .15s,background .15s}
.pill.sel{border-color:#706CFF;background:#EEF0FF;color:#1F1E5D}
.pill.sel .chk{display:flex!important}
.chk{display:none;position:absolute;top:8px;right:10px;width:16px;height:16px;background:#706CFF;border-radius:50%;align-items:center;justify-content:center;font-size:9px;color:#fff;font-weight:700;line-height:1}
.pill-label{font-size:12px;font-weight:600}
.pill-desc{font-size:11px;color:var(--color-text-tertiary);margin-top:2px}
.pill.sel .pill-desc{color:#706CFF}
.btn-cont{background:#706CFF;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-size:12px;font-weight:600;width:100%;margin-top:12px;opacity:.35;cursor:not-allowed;transition:opacity .15s;font-family:inherit}
</style>
<div class="ep">
  <div class="section-title">Other options on deploying the Connect Config</div>
  <div class="section-sub">Select how you'd like to deploy the SDK config via Acoustic.</div>
  <div class="pills" id="dp2">
    <button type="button" class="pill" data-value="acoustic_cms" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div>
        <div class="pill-label">☁ Host it in the Media Gallery (Connect CMS)</div>
        <div class="pill-desc">Upload the SDK config to the Media Gallery (Connect CMS). The config is served via the Acoustic CDN — the customer references it using a delivery URL in their GTM tag or page template.</div>
      </div>
    </button>
  </div>
  <input type="hidden" id="f-other" value=""/>
  <button id="btn-cont2" class="btn-cont" onclick="sub()">Continue</button>
</div>
<script>
function sp(b){document.querySelectorAll('#dp2 .pill').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');document.getElementById('f-other').value=b.getAttribute('data-value');var btn=document.getElementById('btn-cont2');btn.style.opacity='1';btn.style.cursor='pointer';}
function sub(){var v=document.getElementById('f-other').value;if(!v)return;sendPrompt('Deployment other: '+v);}
</script>
```

When `sendPrompt` fires `'Deployment other: acoustic_cms'`: proceed to **Step 10** (CMS upload).

---

### 14. Final response

**Before writing the prose final response**, show the `signals_configured` widget using `mcp__visualize__show_widget` (title: `signals_configured`, loading: `"Loading signal summary…"`). Substitute the tier name, signal count, and signal rows:

```html
<div style="padding:1.25rem;font-family:var(--font-sans);max-width:520px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem">
    <div style="width:32px;height:32px;border-radius:8px;background:#EEF0FF;display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#706CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
    </div>
    <div>
      <div style="font-size:14px;font-weight:600;color:var(--color-text-primary)">Signals configured (N of N — {TIER} tier)</div>
      <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:1px">SDK config · test mode</div>
    </div>
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead>
      <tr style="border-bottom:1px solid var(--color-border-tertiary)">
        <th style="text-align:left;padding:6px 8px;color:var(--color-text-tertiary);font-weight:500">Signal</th>
        <th style="text-align:left;padding:6px 8px;color:var(--color-text-tertiary);font-weight:500">Trigger</th>
        <th style="text-align:left;padding:6px 8px;color:var(--color-text-tertiary);font-weight:500">Status</th>
      </tr>
    </thead>
    <tbody>
      <!-- Repeat one <tr> per configured signal. Example rows: -->
      <tr style="border-bottom:1px solid var(--color-border-tertiary)">
        <td style="padding:7px 8px;color:var(--color-text-primary);font-weight:500">pageView</td>
        <td style="padding:7px 8px;color:var(--color-text-secondary)">load</td>
        <td style="padding:7px 8px"><span style="background:#E6FAF2;color:#00855A;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:500">Configured</span></td>
      </tr>
      <!-- Add one row per signal in scope. Use "Configured" status for all signals with enhance functions written. -->
      <!-- For signals that were blocked/escalated, use status "Needs validation" with background:#FFF7E6;color:#B25000 -->
    </tbody>
  </table>
  <div style="margin-top:10px;font-size:11px;color:var(--color-text-tertiary)">
    Deploy the &lt;script&gt; tag, validate all signals, then confirm to enable production mode.
  </div>
  <button onclick="sendPrompt('Signals confirmed — proceed to session complete')" style="width:100%;margin-top:14px;padding:9px 16px;background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">Continue</button>
</div>
```

**Routing — `signals_configured` is a hard gate:**
1. Render the `signals_configured` widget.
2. **Stop and wait** for the user to click Continue.
3. Do NOT write the Step 14 final response, run Step 14b, or render any session-completion widget before the button fires.
4. When `sendPrompt` fires `'Signals confirmed — proceed to session complete'`:
   - Produce the Step 14 final response using `references/output-contract.md`.
   - Run Step 14b analytics/session processing in its defined order.
   - Render the session-completion widget.

**Dynamic values in `signals_configured` widget:**
- Mode label: use `production mode` when `fakeSignals: false` in the actual config; `test mode` when `fakeSignals: true`. Never hardcode either.
- Signal count: `configured / in-scope` where configured = signals with `passed` status only. Signals with status `escalated`, `blocked`, `pending`, or `not_tested` must NOT be counted as configured.
- Use `Needs validation`, `Blocked`, `Not tested`, or `Escalated` as the status label for non-passing signals.

> **Signal counts:** up to 9 signals on every tier — Pro, Premium, and Ultimate are identical in scope. The in-scope count depends only on what the site supports. Substitute `N of N` with the actual counts, e.g. `9 of 9 — Ultimate tier`.

Follow [references/output-contract.md](references/output-contract.md). State:

- **Subscription tier** and signals configured (list them)
- Signals not configured, and why — no matching functionality on the site, blocked, or escalated (list them)
- Pages navigated and Type 2 events captured
- Interactions simulated and Type 4 events captured
- dataLayer events observed (or absence confirmed)
- Remaining confirmations before production
- Readiness label: `Not ready` / `Ready for staging` / `Ready for production review` / `Production ready`

Do not claim production readiness while required mappings, consent, or real-mode tests remain unresolved. If the customer is on Pro and later upgrades, note the additional signals that would be activated and offer to run a `diff` pass.

### Custom code disclosure (required when any custom code was added)

If any custom JavaScript was added that goes beyond the built-in `help.*` functions and `initLogSignal.js` modules, include a **Custom code added** section in the final response:

```
## Custom code added

| Signal | What was added | Why no built-in worked | Risk |
|---|---|---|---|
| addToCart | MutationObserver on `.basket-count` element | No dlListener event fires when items are added via XHR; no click trigger available on the add button (rendered in an iframe) | Low — observer is disconnected after first fire; scoped to addToCart enhance only |
```

If **no** custom code was added beyond built-ins, include this confirmation line instead:

> ✅ No custom code added — all signals use built-in `help.*` functions and `initLogSignal.js` modules only.

### productConfiguration summary (include when in scope)

When `productConfiguration` is in scope, include a dedicated section in the final response:

```
## productConfiguration signal

Selectors discovered:
- Size: <selector> — trigger: click | change | dataLayer event
- Colour: <selector> — trigger: click | change | not present
- Quantity: <selector> — trigger: change | not present

Trigger type: click / change / dataLayer
actionState source: <data attribute / selected option text / dataLayer field>
productId source: <data attribute stripped / JSON-LD / URL>
De-dupe window: 500ms (prevents double-fire on same selector)

Confirmed interactions: <list each simulated interaction and what fired>
Open items: <any selectors that could not be confirmed — e.g. JS blocked by cookie gate>
```

If a site's cookie consent prevented JS injection during inspection, note it explicitly and mark those selectors as `Requires verification in browser after consent`.

**Known site patterns (reference for future onboardings):**

| Site | Size selector | Colour selector | Trigger type | Notes |
|---|---|---|---|---|
| acmeretail.com | `button[data-gtm="ui--pdp--size_selector"]` | `button[data-gtm="ui--pdp--colour_selector"]` | click (`uiClick`) | `data-product` attribute carries SKU+size e.g. `NN31157/M`; strip prefix to get size value |
| northwindtrading.com | `Choose Size` — selector TBC (JS blocked by cookie gate on first load) | Fixed per product URL (colour is the variant, not a configurable selector) | TBC | Accept cookies in Chrome before injecting shim |

---

### Step 14b — Analytics sidecar, completion, and feedback

This step runs immediately after the Step 14 final response. It has four sub-steps in strict order: (A) write analytics, (B) show completion widget, (C) collect feedback, (D) session backup.

#### 14b-A — Write the analytics sidecar

Before showing the completion widget, write one run record to `<slug>.analytics.json`. This is a sidecar file — the operational profile (`<slug>.json`) is never modified here.

**Analytics failure is non-critical.** If the bash script fails or the analytics file cannot be written, emit one concise warning line in chat and proceed immediately to 14b-B. Do not roll back the SDK work, do not alter readiness, do not re-run the upload.

Assemble the run record from session variables gathered during the run. Substitute every `<PLACEHOLDER>` with the actual value before running the script. Use JSON arrays (e.g. `'["a","b"]'`) for array fields; use `"true"` or `"false"` strings for booleans.

```bash
SLUG="<profile-slug>" \
RUN_ID="<runId>" STARTED_AT="<runStartedAt>" \
WORKFLOW_MODE="<new|existing>" ACTION="<action>" IMPL_MODE="<website_assisted|guided>" \
TIER="<Pro|Premium|Ultimate>" \
SIGNALS_IN_SCOPE='<json-array>' SIGNALS_CONFIGURED='<json-array>' SIGNALS_ESCALATED='<json-array>' \
BUNDLE_GENERATED="<true|false>" BUNDLE_FILENAME="<filename-or-empty>" \
STATIC_VALIDATION="<true|false>" BROWSER_VALIDATION="<true|false>" \
CMS_REQUIRED="<true|false>" CMS_ATTEMPTED="<true|false>" CMS_UPLOADED="<true|false>" \
READINESS="<readiness>" WORKFLOW_OUTCOME="<workflowOutcome>" \
ISSUE_AREAS='<json-array>' REASON_CODES='<json-array>' \
SITE_CATEGORY="<category-slug>" \
OPERATOR_EMAIL="<operator-email>" \
CUSTOMER_NAME="<name>" DOMAIN="<domain>" \
python3 -c "
import json, os, sys, pathlib, glob, datetime

slug = os.environ.get('SLUG', '')
run_id = os.environ.get('RUN_ID', '')
started_at = os.environ.get('STARTED_AT', '')
customer_name = os.environ.get('CUSTOMER_NAME', '')
domain = os.environ.get('DOMAIN', '')

def env_json(key, default):
    val = os.environ.get(key, '')
    try: return json.loads(val) if val else default
    except: return default

def env_bool(key):
    return os.environ.get(key, 'false').lower() == 'true'

dirs = glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not dirs:
    print('WARNING: profiles dir not found — analytics not saved'); sys.exit(0)

profiles_dir = pathlib.Path(dirs[0])
analytics_path = profiles_dir / (slug + '.analytics.json')

now = datetime.datetime.utcnow()
completed_at = now.strftime('%Y-%m-%dT%H:%M:%SZ')

try:
    from datetime import timezone
    start_dt = datetime.datetime.strptime(started_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    end_dt = now.replace(tzinfo=timezone.utc)
    duration_seconds = int((end_dt - start_dt).total_seconds())
except:
    duration_seconds = None

run_record = {
    'runId': run_id,
    'startedAt': started_at,
    'completedAt': completed_at,
    'durationSeconds': duration_seconds,
    'workflowMode': os.environ.get('WORKFLOW_MODE', 'new'),
    'action': os.environ.get('ACTION', 'full_onboarding'),
    'implementationMode': os.environ.get('IMPL_MODE', 'website_assisted'),
    'subscriptionTier': os.environ.get('TIER', ''),
    'signalsInScope': env_json('SIGNALS_IN_SCOPE', []),
    'signalsConfigured': env_json('SIGNALS_CONFIGURED', []),
    'signalsEscalated': env_json('SIGNALS_ESCALATED', []),
    'signalStatus': {},   # populated below from operational profile — read-only copy
    'bundleGenerated': env_bool('BUNDLE_GENERATED'),
    'bundleFilename': os.environ.get('BUNDLE_FILENAME', ''),
    'staticValidationPassed': env_bool('STATIC_VALIDATION'),
    'browserValidationPassed': env_bool('BROWSER_VALIDATION'),
    'cmsRequired': env_bool('CMS_REQUIRED'),
    'cmsAttempted': env_bool('CMS_ATTEMPTED'),
    'cmsUploaded': env_bool('CMS_UPLOADED'),
    'readiness': os.environ.get('READINESS', ''),
    'workflowOutcome': os.environ.get('WORKFLOW_OUTCOME', 'completed'),
    'siteCategory': os.environ.get('SITE_CATEGORY', ''),
    'operatorEmail': os.environ.get('OPERATOR_EMAIL', ''),
    'issueAreas': env_json('ISSUE_AREAS', []),
    'reasonCodes': env_json('REASON_CODES', []),
    'feedbackId': None,
    'feedbackSkipped': False,
}

# Copy per-signal status from operational profile — read-only snapshot for analytics
# The operational profile is the source of truth; this copy MUST NOT be written back
try:
    profile_path = profiles_dir / (slug + '.json')
    if profile_path.exists():
        op_profile    = json.loads(profile_path.read_text())
        op_status     = op_profile.get('acoustic', {}).get('signalStatus', {})
        sig_analytics = {}
        for s, st in op_status.items():
            vr = st.get('validationResult', 'pending')
            # Derive finalResult for analytics
            if st.get('completed') is True and st.get('attempts', 0) == 0:
                final = 'passed_first_time'
            elif st.get('completed') is True and st.get('attempts', 0) > 0:
                final = 'passed_after_correction'
            elif st.get('completed') is False:
                final = 'escalated'
            elif vr == 'blocked':
                final = 'blocked'
            elif vr == 'not_tested':
                final = 'not_tested'
            elif vr == 'issue_found':
                final = 'issue_found'
            else:
                final = 'not_applicable'
            sig_analytics[s] = {
                'finalResult':             final,
                'attempts':                st.get('attempts', 0),
                'maxAttempts':             st.get('maxAttempts', 2),
                'initialValidationResult': st.get('validationResult', 'pending'),
                'reasonCodes':             st.get('reasonCodes', []),
                'corrections': [
                    {
                        'attempt':          h.get('attempt'),
                        'correctionResult': h.get('correctionResult', 'pending'),
                        'retestResult':     h.get('retestResult', 'pending'),
                    }
                    for h in st.get('correctionHistory', [])
                ],
            }
        run_record['signalStatus'] = sig_analytics
except Exception as e:
    run_record['signalStatus'] = {}
    print('WARNING: could not copy signal status to analytics — ' + str(e))

if analytics_path.exists():
    try: analytics = json.loads(analytics_path.read_text())
    except: analytics = {}
else:
    analytics = {}

analytics.setdefault('schemaVersion', '1.0.0')
analytics.setdefault('profileSlug', slug)
analytics.setdefault('operationalProfileFile', slug + '.json')
analytics.setdefault('customerReference', {'name': customer_name, 'productionDomain': domain})
analytics.setdefault('runHistory', [])
analytics.setdefault('feedbackHistory', [])
operator_email = os.environ.get('OPERATOR_EMAIL', '')
if operator_email:
    analytics['operator'] = {'email': operator_email, 'source': 'meta[name=acoustic-id] on app.goacoustic.com'}
analytics['lastUpdatedAt'] = completed_at

analytics['runHistory'].append(run_record)

try:
    analytics_path.write_text(json.dumps(analytics, indent=2, ensure_ascii=False) + '\n')
    print('OK')
    print(run_id)
except Exception as e:
    print('WARNING: could not write analytics — ' + str(e))
"
```

**Deriving run record values from session state:**

| Field | Source |
|---|---|
| `runId` | Generated at Pre-step |
| `startedAt` | Captured at Pre-step |
| `workflowMode` | Step 0 answer (`new` or `existing`) |
| `action` | Step 0 sub-path: new onboarding → `full_onboarding`; existing → `regenerate`, `reinspect_and_regenerate`, `reupload`, or `resume_validation` |
| `implementationMode` | Chrome pre-flight result: browser connected → `website_assisted`; not connected → `guided` |
| `subscriptionTier` | Step 1 tier selection |
| `signalsInScope` | All signals applicable to the site (never tier-limited) |
| `signalsConfigured` | Signals with non-null, non-TODO enhance functions in generated config |
| `signalsEscalated` | Signals flagged as requiring manual resolution |
| `bundleGenerated` | `true` only if `generate_sdk.py` ran and produced a file with 0 TODO lines |
| `bundleFilename` | Actual output filename from generation |
| `staticValidationPassed` | `true` only if `validate_profile.py` returned 0 errors |
| `browserValidationPassed` | `true` only if Step 13 browser verify was completed and confirmed by user |
| `cmsRequired` | `true` when the user selects the Media Gallery (Connect CMS) upload in Step 10-pre; `false` when they choose direct handover. Never derived from the tier. |
| `cmsAttempted` | `true` if Step 10 upload sequence was started |
| `cmsUploaded` | `true` only if B-5 GET confirmed `publishStatus: "available"` |
| `readiness` | Label from Step 14: `not_ready`, `ready_for_staging`, `ready_for_production_review`, or `production_ready` |
| `workflowOutcome` | `completed` if all steps finished; `completed_with_exceptions` if escalated signals or unresolved issues remain; `blocked` if a hard gate was not passed; `stopped_by_user` if user ended early; `failed` if generation or upload failed |
| `siteCategory` | Category slug written to `profile.customer.siteCategory` during Step 2a; empty string if Step 2a did not run (e.g. re-upload path) |
| `issueAreas` | Populated from any escalation flags, validation errors, or upload failures |
| `reasonCodes` | Machine codes for each issue: see enum list below |

**Do not infer success.** Only set `bundleGenerated: true`, `staticValidationPassed: true`, `browserValidationPassed: true`, or `cmsUploaded: true` when each event actually occurred and was confirmed in the current session.

**Allowed enum values:**

`action`: `full_onboarding` · `regenerate` · `reinspect_and_regenerate` · `reupload` · `resume_validation`

`implementationMode`: `website_assisted` · `guided`

`workflowOutcome`: `completed` · `completed_with_exceptions` · `stopped_by_user` · `blocked` · `failed`

`readiness`: `not_ready` · `ready_for_staging` · `ready_for_production_review` · `production_ready`

`issueAreas`: `inspection` · `signal_mapping` · `generation` · `static_validation` · `user_validation` · `browser_verification` · `cms_upload` · `workflow` · `other`

`reasonCodes`: `selector_not_found` · `data_layer_missing` · `required_field_missing` · `page_unreachable` · `authentication_required` · `email_verification_required` · `cross_domain_journey` · `browser_tool_failure` · `signal_not_triggered` · `payload_invalid` · `duplicate_signal` · `cms_upload_failed` · `cms_republish_failed` · `user_validation_incomplete` · `unsupported_site_pattern` · `manual_mapping_required` · `workflow_deviation` · `other`

---

#### 14b-B — Session complete

After writing (or attempting) the analytics sidecar, show a completion widget using `mcp__visualize__show_widget` (title: `session_complete`, loading: `"Wrapping up…"`).

**Build the widget dynamically from actual run facts.** Do not use hardcoded text. Derive every displayed value from what actually happened in the current session.

**Icon and heading rule:**
- `production_ready` → icon `✅`, heading `"Onboarding complete"`
- `ready_for_production_review` → icon `✅`, heading `"Ready for production review"`
- `ready_for_staging` → icon `🔄`, heading `"Ready for staging"`
- `not_ready` → icon `⚠️`, heading `"Review required before production"`

**Status line rules (show only lines that are true):**
- Show `"SDK config generated"` only if `bundleGenerated = true`
- Show `"Static validation passed"` only if `staticValidationPassed = true`
- Show `"Browser verification passed"` only if `browserValidationPassed = true`
- Show `"Uploaded to the Media Gallery (Connect CMS)"` only if `cmsUploaded = true`
- Show `"Hosted by the customer — no Media Gallery upload requested"` if `cmsRequired = false`
- **Never claim CMS upload if `cmsUploaded = false`**
- **Never claim browser verification if `browserValidationPassed = false`**

**Escalated signals:** If `signalsEscalated` is non-empty, include: `"⚠️ Escalated signals: [list]"`

Widget template (substitute `ICON`, `HEADING`, `STATUS_LINES`, and optionally `ESCALATION_LINE`):

```html
<div style="padding:1.5rem;font-family:var(--font-sans);text-align:center;max-width:380px;margin:0 auto">
  <div style="font-size:32px;margin-bottom:10px">ICON</div>
  <div style="font-size:15px;font-weight:600;color:var(--color-text-primary);margin-bottom:6px">HEADING</div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:6px;line-height:1.8;text-align:left">
    STATUS_LINES
  </div>
  ESCALATION_LINE
  <div style="display:flex;gap:8px;justify-content:center;margin-top:20px">
    <button onclick="sendPrompt('Mark complete — show feedback form')"
      style="background:#1F1E5D;color:#C8FF49;border:none;border-radius:8px;padding:10px 24px;font-size:13px;font-weight:600;cursor:pointer">
      Mark complete
    </button>
    NEW_CUSTOMER_BUTTON
  </div>
</div>
```

**`NEW_CUSTOMER_BUTTON` rule:**
- `production_ready` only → include: `<button onclick="sendPrompt('Start another customer onboarding')" style="background:var(--color-background-secondary);color:var(--color-text-primary);border:1px solid var(--color-border-tertiary);border-radius:8px;padding:10px 20px;font-size:13px;cursor:pointer">New customer</button>`
- All other readiness states (`ready_for_production_review`, `ready_for_staging`, `not_ready`) → omit entirely (replace `NEW_CUSTOMER_BUTTON` with nothing). Feedback is required before closing these sessions — bypassing via "New customer" would skip the feedback form and lose the run record.

For `STATUS_LINES`, render each true line as: `✅ Line text<br>`. Omit false lines entirely.

For `ESCALATION_LINE`, when escalated signals exist: `<div style="font-size:11px;color:#D97706;margin-bottom:12px">⚠️ Escalated: SIGNALS_LIST</div>`. Omit when empty.

**When `sendPrompt` fires `'Mark complete — show feedback form'`:**
Show the `session_feedback` widget (see 14b-C below). Do not close the session or output any prose.

**When `sendPrompt` fires `'Start another customer onboarding'`:**
Clear all customer context (including `runId`, `runStartedAt`, and all run-state variables) and restart from the **Pre-step** (persistent storage check) exactly as if the skill was freshly invoked. Do not carry over any profile data, customer name, tier, signals, or analytics variables from the completed session.

---

#### 14b-C — Feedback

This is an explicitly defined part of Step 14b. It is not an unlisted workflow action.

##### `session_feedback` widget

> ⛔ **HARD GUARDRAIL — widget fidelity (feedback form).** The `session_feedback` widget MUST be rendered from the exact HTML template below — verbatim, with only `SIGNAL_OPTIONS` substituted. Never improvise an alternative feedback UI, never add a "Which signals worked well?" question, never remove the conditional `detail-section`, never change the four outcome options, never add outcome options, never make the detail section always-visible. Any deviation from this template is a skill defect. The `detail-section` must remain hidden (`display:none`) until a non-`production_ready` outcome is selected — it is never shown for `production_ready`. Rendering a flat list of signals without the conditional detail block is a defect.

> ⛔ **HARD GUARDRAIL — sequence (feedback → upload → close).** When `sendPrompt` fires `'Session feedback JSON: ...'`:
> 1. The `saving-msg` div inside the widget fires automatically (it is already in the widget HTML — do not add a separate prose message).
> 2. Run the feedback bash script to save to the analytics sidecar.
> 3. Immediately run Step 14b-D (session backup). Zero narration between these steps.
> 4. Only after 14b-D completes (success or failure): show the `feedback_saved` widget (with "Close session" button).
> **Never show `feedback_saved` before 14b-D runs. Never show a custom "Feedback recorded" card instead of the widget. This sequence is mandatory.**

Show using `mcp__visualize__show_widget` (title: `session_feedback`, loading: `"Loading feedback form…"`).

Before rendering, substitute `SIGNAL_OPTIONS` with one `<button>` element per signal that was in `signalsInScope` for the current run. Never filter by subscription tier — every signal is available on every tier.

Signal button template: `<button class="mpill" data-signal="SIGNAL_NAME" onclick="toggleSignal(this)">SIGNAL_LABEL</button>`

Signal labels: `identification` → "Identification" · `accountRegistered` → "Account registered" · `addToCart` → "Add to cart" · `order` → "Order" · `pageView` → "Page view" · `productView` → "Product view" · `onSiteSearch` → "On-site search" · `productConfiguration` → "Product configuration" · `richMediaInteraction` → "Rich media interaction"

```html
<style>
.pill{border:1px solid var(--color-border-tertiary);background:var(--color-background-secondary);color:var(--color-text-primary);cursor:pointer;border-radius:10px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start;text-align:left;width:100%;position:relative;transition:border-color .15s,background .15s;font-family:var(--font-sans);box-sizing:border-box}
.pill.sel{border-color:#706CFF;background:#EEF0FF;color:#1F1E5D}
.pill.sel .chk{display:flex!important}
.chk{display:none;position:absolute;top:8px;right:8px;width:16px;height:16px;background:#706CFF;border-radius:50%;align-items:center;justify-content:center;font-size:9px;color:#fff;font-weight:700;line-height:1}
.mpill{border:2px solid var(--color-border-tertiary)!important;background:var(--color-background-secondary)!important;color:var(--color-text-primary)!important;cursor:pointer;border-radius:8px;padding:7px 12px;display:inline-flex;gap:6px;align-items:center;font-size:12px;font-family:var(--font-sans);transition:all .15s;margin:3px 3px 3px 0}
.mpill.sel{border-color:#706CFF!important;background:#706CFF!important;color:#fff!important;font-weight:500!important}
#btn-submit{background:#ccc;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:600;flex:1;cursor:not-allowed;transition:all .15s;font-family:var(--font-sans)}
#btn-submit.active{background:#1F1E5D;color:#C8FF49;cursor:pointer}
#btn-skip{background:var(--color-background-secondary);color:var(--color-text-secondary);border:2px solid var(--color-border-tertiary);border-radius:8px;padding:10px 14px;font-size:12px;cursor:pointer;white-space:nowrap;font-family:var(--font-sans)}
</style>
<div style="padding:1.5rem;font-family:var(--font-sans);max-width:480px;margin:0 auto">
  <div style="font-size:15px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">Session feedback</div>
  <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:16px;line-height:1.5">How would you rate the SDK config produced in this session?</div>

  <input type="hidden" id="outcome-val" value="">
  <div id="outcome-pills" style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px">
    <button class="pill" data-value="production_ready" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div><strong style="font-size:12px">Production ready</strong><div style="font-size:11px;color:var(--color-text-secondary);margin-top:2px">The generated config works as expected and requires no further changes.</div></div>
    </button>
    <button class="pill" data-value="minor_changes" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div><strong style="font-size:12px">Usable with minor changes</strong><div style="font-size:11px;color:var(--color-text-secondary);margin-top:2px">Core signals work, but small mapping, validation, or implementation changes are required.</div></div>
    </button>
    <button class="pill" data-value="major_changes" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div><strong style="font-size:12px">Not production ready</strong><div style="font-size:11px;color:var(--color-text-secondary);margin-top:2px">The config was generated, but significant signal or implementation changes are required.</div></div>
    </button>
    <button class="pill" data-value="run_failed" onclick="sp(this)">
      <span class="chk" aria-hidden="true">✓</span>
      <div><strong style="font-size:12px">Run failed</strong><div style="font-size:11px;color:var(--color-text-secondary);margin-top:2px">The skill could not generate or validate a usable SDK config.</div></div>
    </button>
  </div>

  <div id="detail-section" style="display:none">
    <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:8px">What areas need improvement?</div>
    <div id="area-pills" style="margin-bottom:16px;line-height:2.2">
      <button class="mpill" data-area="inspection" onclick="toggleArea(this)">Inspection</button>
      <button class="mpill" data-area="signal_mapping" onclick="toggleArea(this)">Signal mapping</button>
      <button class="mpill" data-area="generated_javascript" onclick="toggleArea(this)">Generated JavaScript</button>
      <button class="mpill" data-area="static_validation" onclick="toggleArea(this)">Static validation</button>
      <button class="mpill" data-area="user_validation" onclick="toggleArea(this)">User validation</button>
      <button class="mpill" data-area="browser_verification" onclick="toggleArea(this)">Browser verification</button>
      <button class="mpill" data-area="cms_upload" onclick="toggleArea(this)">Media Gallery upload</button>
      <button class="mpill" data-area="workflow" onclick="toggleArea(this)">Workflow</button>
      <button class="mpill" data-area="user_experience" onclick="toggleArea(this)">User experience</button>
      <button class="mpill" data-area="documentation" onclick="toggleArea(this)">Documentation</button>
      <button class="mpill" data-area="other" onclick="toggleArea(this)">Other</button>
    </div>
    <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);margin-bottom:8px">Affected signals</div>
    <div id="signal-pills" style="margin-bottom:16px;line-height:2.2">
      SIGNAL_OPTIONS
    </div>
  </div>

  <div style="margin-bottom:16px">
    <div style="font-size:12px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">Tell us more <span style="font-weight:400;color:var(--color-text-secondary)">(optional)</span></div>
    <textarea id="comment-val" rows="3" maxlength="2000" placeholder="What worked, what failed, or what should be improved?" style="width:100%;padding:8px 10px;border:1px solid var(--color-border-tertiary);border-radius:6px;font-size:12px;resize:vertical;background:var(--color-background-secondary);color:var(--color-text-primary);font-family:var(--font-sans);box-sizing:border-box"></textarea>
  </div>

  <div id="saving-msg" style="display:none;font-size:12px;color:var(--color-text-secondary);text-align:center;padding:8px 0">
    Please wait while we save your feedback…
  </div>
  <div id="action-row" style="display:flex;gap:8px;align-items:stretch">
    <button id="btn-submit" onclick="submitFb()">Submit feedback</button>
    <button id="btn-skip" onclick="skipFb()">Skip and complete</button>
  </div>
</div>
<script>
var selectedAreas=[];var selectedSignals=[];
var needsDetail=['minor_changes','major_changes','run_failed'];
function sp(b){
  document.querySelectorAll('#outcome-pills .pill').forEach(function(x){x.classList.remove('sel');});
  b.classList.add('sel');
  var val=b.getAttribute('data-value');
  document.getElementById('outcome-val').value=val;
  document.getElementById('detail-section').style.display=needsDetail.indexOf(val)>-1?'block':'none';
  document.getElementById('btn-submit').classList.add('active');
}
function toggleArea(b){
  b.classList.toggle('sel');
  var area=b.getAttribute('data-area');
  var idx=selectedAreas.indexOf(area);
  if(idx>-1)selectedAreas.splice(idx,1);else selectedAreas.push(area);
}
function toggleSignal(b){
  b.classList.toggle('sel');
  var sig=b.getAttribute('data-signal');
  var idx=selectedSignals.indexOf(sig);
  if(idx>-1)selectedSignals.splice(idx,1);else selectedSignals.push(sig);
}
function submitFb(){
  var outcome=document.getElementById('outcome-val').value;
  if(!outcome)return;
  var btn=document.getElementById('btn-submit');
  var skip=document.getElementById('btn-skip');
  btn.disabled=true;btn.style.opacity='0.5';btn.style.cursor='not-allowed';
  if(skip){skip.disabled=true;skip.style.opacity='0.35';}
  document.getElementById('action-row').style.display='none';
  document.getElementById('saving-msg').style.display='block';
  var comment=(document.getElementById('comment-val').value||'').trim().substring(0,2000)||null;
  setTimeout(function(){
    sendPrompt('Session feedback JSON: '+JSON.stringify({
      outcome:outcome,issueAreas:selectedAreas,affectedSignals:selectedSignals,comment:comment
    }));
  },400);
}
function skipFb(){sendPrompt('Session feedback skip');}
</script>
```

---

##### Handling `'Session feedback JSON: ...'` submissions

**When `sendPrompt` fires a message starting with `'Session feedback JSON: '`:**

1. Parse the JSON payload after the `'Session feedback JSON: '` prefix. Extract `outcome`, `issueAreas` (array), `affectedSignals` (array), and `comment` (string or null).

2. Map `outcome` to `productionDecision`:
   - `production_ready` → `approved`
   - `minor_changes` → `needs_changes`
   - `major_changes` → `needs_changes`
   - `run_failed` → `rejected`

3. Run this bash script. Replace `<SLUG>`, `<RUN_ID>`, `<OUTCOME>`, `<ISSUE_AREAS_JSON>`, `<SIGNALS_JSON>`, and `<COMMENT>` with actual values. Do not use `|` or `=` delimiters in comment text — the JSON encoding handles safety.

```bash
SLUG="<SLUG>" RUN_ID="<RUN_ID>" \
OUTCOME="<OUTCOME>" PRODUCTION_DECISION="<productionDecision>" \
ISSUE_AREAS='<ISSUE_AREAS_JSON>' AFFECTED_SIGNALS='<SIGNALS_JSON>' \
COMMENT="<COMMENT>" \
python3 -c "
import json, os, pathlib, glob, datetime, random, sys

slug = os.environ.get('SLUG','')
run_id = os.environ.get('RUN_ID','')
outcome = os.environ.get('OUTCOME','')
production_decision = os.environ.get('PRODUCTION_DECISION','not_assessed')
comment_raw = os.environ.get('COMMENT','') or None

def env_json(key, default):
    val = os.environ.get(key,'')
    try: return json.loads(val) if val else default
    except: return default

issue_areas = env_json('ISSUE_AREAS',[])
affected_signals = env_json('AFFECTED_SIGNALS',[])

now = datetime.datetime.utcnow()
rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789',k=4))
feedback_id = 'feedback-{}-{}'.format(now.strftime('%Y%m%d-%H%M%S'),rand)

entry = {
    'feedbackId': feedback_id,
    'runId': run_id,
    'submittedAt': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'outcome': outcome,
    'issueAreas': issue_areas,
    'affectedSignals': affected_signals,
    'productionDecision': production_decision,
}
if comment_raw:
    entry['comment'] = comment_raw[:2000]

dirs = glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not dirs:
    print('WARNING: profiles dir not found'); sys.exit(0)

analytics_path = pathlib.Path(dirs[0]) / (slug + '.analytics.json')
if not analytics_path.exists():
    print('WARNING: analytics sidecar not found'); sys.exit(0)

analytics = json.loads(analytics_path.read_text())
analytics.setdefault('feedbackHistory',[])
analytics['feedbackHistory'].append(entry)

for run in analytics.get('runHistory',[]):
    if run.get('runId') == run_id:
        run['feedbackId'] = feedback_id
        run['feedbackSkipped'] = False

analytics['lastUpdatedAt'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
analytics_path.write_text(json.dumps(analytics,indent=2,ensure_ascii=False)+'\n')
print('OK')
print(feedback_id)
"
```

4. If the script outputs `OK`: immediately run Step 14b-D (session backup) — silently, without narrating intermediate steps.

5. If the script outputs `WARNING` or exits with an error: still run Step 14b-D, but note the analytics failure in `window.__d4BackupNote` (internal only — do not surface to user).

6. After 14b-D completes (success or failure): show the `feedback_saved` widget below.

7. **Do not modify the operational profile (`<slug>.json`) during feedback submission.**

---

##### Handling `'Session feedback skip'`

**When `sendPrompt` fires `'Session feedback skip'`:**

```bash
SLUG="<SLUG>" RUN_ID="<RUN_ID>" python3 -c "
import json, os, pathlib, glob, datetime, sys

slug = os.environ.get('SLUG','')
run_id = os.environ.get('RUN_ID','')

dirs = glob.glob('/sessions/*/mnt/SDK-config-assistant/profiles')
if not dirs:
    print('WARNING: profiles dir not found'); sys.exit(0)

analytics_path = pathlib.Path(dirs[0]) / (slug + '.analytics.json')
if not analytics_path.exists():
    print('WARNING: analytics sidecar not found'); sys.exit(0)

analytics = json.loads(analytics_path.read_text())
for run in analytics.get('runHistory',[]):
    if run.get('runId') == run_id:
        run['feedbackSkipped'] = True

analytics['lastUpdatedAt'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
analytics_path.write_text(json.dumps(analytics,indent=2,ensure_ascii=False)+'\n')
print('OK')
"
```

Do not create an empty feedback entry. After the script completes (success or warning), immediately run Step 14b-D (session backup) — silently. After 14b-D completes (success or failure), respond with the single close line: "Session closed. Run the skill again whenever you're ready for the next customer."

---

##### `feedback_saved` widget

> ⛔ **HARD GUARDRAIL — widget fidelity (feedback saved).** This widget MUST be rendered verbatim with only the six placeholder tokens substituted (see mapping below). It MUST include the session summary card, both "Close session" (`sendPrompt('Session complete')`) and "New customer" (`sendPrompt('New customer')`) buttons, and the 30-second countdown auto-close. Never substitute a plain card, a prose line, or any other custom widget here. Never show this widget before 14b-D completes. Showing it early or in a wrong format is a skill defect.

Show using `mcp__visualize__show_widget` (title: `feedback_saved`, loading: `"Saving feedback…"`). Populate all six tokens from the session profile before rendering:

| Token | Source | Example |
|---|---|---|
| `FEEDBACK_SUMMARY` | outcome mapping below | `"Usable with minor changes noted. Feedback saved."` |
| `CUSTOMER_NAME` | `profile.customer.name` | `Acme Retail` |
| `DOMAIN` | `profile.customer.productionDomain` | `www.acmeretail.com` |
| `TIER` | `profile.customer.tier` | `Ultimate` |
| `SIGNALS_CONFIGURED` | count of enabled signals + total in scope | `9 of 9 configured` |
| `OUTCOME_LABEL` | outcome label mapping below | `Minor changes needed` |
| `OUTCOME_COLOR` | outcome colour mapping below | `#706CFF` |

**Outcome → FEEDBACK_SUMMARY:**
- `production_ready` → `"Config rated production ready. Feedback saved."`
- `minor_changes` → `"Usable with minor changes noted. Feedback saved."`
- `major_changes` → `"Significant changes flagged. Feedback saved."`
- `run_failed` → `"Run failure recorded. Feedback saved."`

**Outcome → OUTCOME_LABEL:**
- `production_ready` → `Production ready`
- `minor_changes` → `Minor changes needed`
- `major_changes` → `Major changes needed`
- `run_failed` → `Run failed`

**Outcome → OUTCOME_COLOR:**
- `production_ready` → `#00DF8F`
- `minor_changes` → `#706CFF`
- `major_changes` → `#FF9500`
- `run_failed` → `#FF5050`

```html
<div style="font-family:var(--font-sans,system-ui);max-width:480px;padding:1.5rem;box-sizing:border-box">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem">
    <div style="width:36px;height:36px;border-radius:50%;background:#00DF8F;display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 9l4.5 4.5L15 4.5" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </div>
    <div>
      <div style="font-size:15px;font-weight:700;color:var(--color-text-primary,#1F1E5D)">Session saved</div>
      <div style="font-size:12px;color:var(--color-text-secondary,#5A5D77);margin-top:2px">FEEDBACK_SUMMARY</div>
    </div>
  </div>
  <div style="background:var(--color-background-secondary,#f5f5f8);border-radius:8px;padding:0.9rem 1rem;margin-bottom:1.25rem;font-size:12px;color:var(--color-text-secondary,#5A5D77);line-height:1.55">
    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>Customer</span><strong style="color:var(--color-text-primary,#1F1E5D)">CUSTOMER_NAME</strong></div>
    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>Domain</span><strong style="color:var(--color-text-primary,#1F1E5D)">DOMAIN</strong></div>
    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>Tier</span><strong style="color:var(--color-text-primary,#1F1E5D)">TIER</strong></div>
    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>Signals</span><strong style="color:var(--color-text-primary,#1F1E5D)">SIGNALS_CONFIGURED</strong></div>
    <div style="display:flex;justify-content:space-between"><span>Outcome</span><strong style="color:OUTCOME_COLOR">OUTCOME_LABEL</strong></div>
  </div>
  <div style="display:flex;gap:10px;margin-bottom:1rem">
    <button onclick="sendPrompt('Session complete')" style="flex:1;background:#1F1E5D;color:#fff;border:none;border-radius:8px;padding:10px 0;font-size:13px;font-weight:600;cursor:pointer">Close session</button>
    <button onclick="sendPrompt('New customer')" style="flex:1;background:transparent;color:#706CFF;border:2px solid #706CFF;border-radius:8px;padding:10px 0;font-size:13px;font-weight:600;cursor:pointer">New customer</button>
  </div>
  <div style="font-size:11px;color:var(--color-text-secondary,#5A5D77);text-align:center">Auto-closing in <span id="fs-cd">30</span>s</div>
</div>
<script>
(function(){
  if(window._fsCdIv){clearInterval(window._fsCdIv);}
  var _t=30;
  window._fsCdIv=setInterval(function(){
    _t--;
    var el=document.getElementById('fs-cd');
    if(el)el.textContent=_t;
    if(_t<=0){clearInterval(window._fsCdIv);sendPrompt('Session complete');}
  },1000);
})();
</script>
```

Replace all seven tokens (`FEEDBACK_SUMMARY`, `CUSTOMER_NAME`, `DOMAIN`, `TIER`, `SIGNALS_CONFIGURED`, `OUTCOME_LABEL`, `OUTCOME_COLOR`) before rendering. Do not render any literal placeholder text. The countdown uses `window._fsCdIv` as a guard so re-renders clear the old timer before starting a fresh 30-second countdown.

**When `sendPrompt` fires `'Session complete'`:**
Respond with a single line: "Session closed. Run the skill again whenever you're ready for the next customer." Do not run Step 14b-D here — it already ran when the user submitted or skipped feedback. Do not retain any customer context, `runId`, or analytics variables in subsequent messages.

**When `sendPrompt` fires `'New customer'`:**
Clear all customer context (including `runId`, `runStartedAt`, and all run-state variables) and restart from the **Pre-step** (persistent storage check) exactly as if the skill was freshly invoked. Do not carry over any profile data, customer name, tier, signals, or analytics variables from the completed session.

---

#### 14b-D — Session backup

**This is the external (customer-facing) build.** There is no operator CMS to back up to — no org constant, no manifest, no upload endpoints, and none should be added. Do not attempt to derive or guess an upload target from the customer's own `app.goacoustic.com` session.

**No `uploading_feedback` widget** — nothing is being uploaded, so do not claim it is. Skip straight from feedback submit/skip to the close notice below.

**Close notice** (runs on both the feedback-submit route and the feedback-skip route, immediately after the feedback step completes): tell the customer their session files are saved locally, and that Acoustic Support can help if needed:

```
Your session profile and analytics were saved locally:
  <SLUG>.json
  <SLUG>.analytics.json

Need help from Acoustic Support? Log in to the Acoustic Support Portal, submit a case, and attach both files.
```

Substitute `<SLUG>` with the actual profile slug. This is informational text only — do not render it as a widget, do not send the files anywhere on the customer's behalf, and do not block or delay session close on it.

---

##### External-mode implementation

There is no operator CMS to back up to in this build — no org constant, no manifest, no upload endpoints. Do not attempt to derive or guess one from the customer's own `app.goacoustic.com` session.

**No `uploading_feedback` widget** — nothing is being uploaded, so do not claim it is. Skip straight from feedback submit/skip to the close notice below.

**Close notice** (replaces the internal-mode upload step on both the feedback-submit route and the feedback-skip route): tell the customer their session files are saved locally, and that Acoustic Support can help if needed:

```
Your session profile and analytics were saved locally:
  <SLUG>.json
  <SLUG>.analytics.json

Need help from Acoustic Support? Log in to the Acoustic Support Portal, submit a case, and attach both files.
```

Substitute `<SLUG>` with the actual profile slug. This is informational text only — do not render it as a widget, do not send the files anywhere on the customer's behalf, and do not block or delay session close on it.

---

#### Analytics sidecar schema

The sidecar file lives alongside the operational profile and is never used as an input to any operational decision. Its sole purpose is analytics, aggregation, and learning.

```json
{
  "schemaVersion": "1.0.0",
  "profileSlug": "acmeretail-com",
  "operationalProfileFile": "acmeretail-com.json",
  "customerReference": {
    "name": "Acme Retail",
    "productionDomain": "www.acmeretail.com"
  },
  "runHistory": [
    {
      "runId": "run-20260724-144218-a3f9",
      "startedAt": "2026-07-24T14:05:10Z",
      "completedAt": "2026-07-24T14:42:18Z",
      "durationSeconds": 2228,
      "workflowMode": "new",
      "action": "full_onboarding",
      "implementationMode": "website_assisted",
      "subscriptionTier": "Premium",
      "signalsInScope": ["identification","accountRegistered","addToCart","order","pageView","productView","onSiteSearch","productConfiguration"],
      "signalsConfigured": ["identification","addToCart","order","pageView"],
      "signalsEscalated": ["accountRegistered"],
      "bundleGenerated": true,
      "bundleFilename": "acoConnectSdkConfig-acmeretail-com.js",
      "staticValidationPassed": true,
      "browserValidationPassed": false,
      "cmsRequired": true,
      "cmsAttempted": true,
      "cmsUploaded": true,
      "siteCategory": "standard-ecommerce",
      "readiness": "ready_for_production_review",
      "workflowOutcome": "completed_with_exceptions",
      "issueAreas": ["browser_verification"],
      "reasonCodes": ["email_verification_required"],
      "feedbackId": "feedback-20260724-144305-b72c",
      "feedbackSkipped": false
    }
  ],
  "feedbackHistory": [
    {
      "feedbackId": "feedback-20260724-144305-b72c",
      "runId": "run-20260724-144218-a3f9",
      "submittedAt": "2026-07-24T14:43:05Z",
      "outcome": "minor_changes",
      "issueAreas": ["signal_mapping","browser_verification"],
      "affectedSignals": ["accountRegistered"],
      "productionDecision": "needs_changes",
      "comment": "Registration could not be validated."
    }
  ],
  "lastUpdatedAt": "2026-07-24T14:43:07Z"
}
```

**Do not store in the sidecar:** app keys, passwords, access tokens, cookies, authentication headers, credential values, complete browser output, full DOM snapshots, full generated JavaScript, all inspection payloads, or complete operational profile objects. The sidecar is compact and aggregable — not a recovery artifact.

