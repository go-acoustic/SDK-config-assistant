# Final Deliverable Contract

Return these sections in order:

1. Customer summary
2. Pages inspected and discovered patterns
3. Signal mapping table
4. Questions needing confirmation
5. Generated files
6. Test checklist and results
7. Assumptions and readiness

## Mapping table

Include:

| Signal | Attribute | Requirement | Source | Extraction | Example | Confidence | Status | Risk | Evidence |
|---|---|---|---|---|---|---:|---|---|---|

Use an integer confidence score from 0–100.

## Generated files

Produce:

- Website profile/mapping JSON
- Customer-specific `initLogSignal()` JavaScript
- Implementation review Markdown

Link files using absolute local paths.

## Testing

Separate:

- Tests completed in the browser
- Tests not completed
- Tests requiring customer credentials/data/action

Do not say a signal was tested when only its selector was inspected.

## initLogSignal function reference

Include the following note block in the implementation review, after the signal mapping table and before the deployment instructions. This helps the customer's developer understand what each function and configuration option does.

> **For the developer implementing this SDK:** The `initLogSignal` configuration guide below explains every option you will see in the generated JavaScript. Read it if you are unsure what a trigger, enhance function, or help utility does.
>
> Full reference: `references/initLogSignal-guide.md` (included alongside your implementation files).

Summarise the following in the implementation review (do not reproduce the full guide — link it):

- What `cfg.fakeSignals` does and when to flip it to `false`
- What `cfg.eventLog` does and when to turn it on for debugging
- The meaning of `enhance` return values: `signal` = send it, `null` = suppress
- Where `help.retrieve("userEmail")` gets its value from (the `identification` signal stores it)
- A one-sentence description for each signal type configured for this customer

## Readiness labels

Use exactly one label. Derive it from the actual state of the current run — never guess or promote a label without evidence.

- `Not ready`: required data, consent, or trigger behaviour is unresolved. Use when one or more required fields are missing, a signal could not be mapped, static validation failed, or a required gate was not passed.
- `Ready for staging`: config generated and statically validated; browser or user validation has not been completed. Use when Step 13 browser verification was not performed or was inconclusive.
- `Ready for production review`: browser verification passed and all in-scope signals are configured; one or more signals are escalated or require manual follow-up before production.
- `Production ready`: all in-scope signals configured, static validation passed, browser verification completed and confirmed, no escalated signals, and the config has been reviewed. Only use when every gate has been cleared.

**Accuracy rules (mandatory):**
- Do not claim `Production ready` while any signal is escalated or unresolved.
- Do not claim `Ready for production review` if browser verification (Step 13) was not completed in this session.
- Do not state "Uploaded to the Media Gallery (Connect CMS)" unless `cmsUploaded = true` for this run.
- Do not state "Browser verification passed" unless Step 13 ran and the user confirmed signals in the browser.
- The Media Gallery upload is optional on every tier. When the user chose direct handover in Step 10-pre (`cmsRequired = false`), say the customer hosts the file themselves rather than reporting an upload status.
- The readiness label written to the Step 14 final response must match the `readiness` value recorded in the analytics sidecar run record.
