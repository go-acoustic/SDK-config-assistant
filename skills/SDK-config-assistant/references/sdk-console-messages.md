# SDK Console Message Reference

When the Acoustic SDK is running in test mode (`fakeSignals: true`, `eventLog: true`), it emits structured messages to the browser console. Reading these messages is the primary way to confirm signal firing, discover correct `triggers` triggers, and validate payload completeness.

## How to see messages

1. Install the Tampermonkey script on the customer site.
2. Open DevTools → **Console**.
3. Filter by `[ACO]` or `Acoustic Connect` to isolate SDK output.
4. Perform the journey actions (page load, click, form submit, search, checkout).

---

## Type 2 — Screenview (page load)

Fires on every page load. Use to confirm `pageView` trigger and discover the URL path pattern.

```json
{
  "type": 2,
  "offset": 2688,
  "screenviewOffset": 0,
  "count": 1,
  "fromWeb": true,
  "screenview": {
    "type": "LOAD",
    "name": "root",
    "originalUrl": "/01/details/NN31219",
    "url": "/01/details/NN31219",
    "host": "https://www.acmeretail.com",
    "referrer": "",
    "title": "Buy Example Brand Mens T-Shirt...",
    "queryParams": {}
  },
  "dcid": "dcid-1.1782147575044s"
}
```

### How to use Type 2 for signal configuration

| Field | Path | Use |
|---|---|---|
| Page load trigger | `screenview.type = "LOAD"` | `triggers: [{ attributes: { "screenview.type": "LOAD" } }]` |
| Current URL path | `screenview.url` | Page category rules, URL-based signal guards |
| Page title | `screenview.title` | `pageView.name` fallback |
| Referrer | `screenview.referrer` | Previous-page tracking |
| Query params | `screenview.queryParams` | Search term extraction |

**pageView onEvent (confirmed):**
```json
{ "attributes": { "screenview.type": "LOAD" } }
```

---

## Type 4 — Interaction (click, change, focus)

Fires on every user interaction captured by the SDK. Use to discover correct `triggers` triggers for `addToCart`, `formInteraction`, `formSubmit`, and `productConfiguration` signals.

```json
{
  "type": 4,
  "offset": 27553,
  "screenviewOffset": 24865,
  "count": 15,
  "fromWeb": true,
  "target": {
    "id": "buy_NN31219",
    "idType": -1,
    "name": "",
    "tlType": "button",
    "type": "button",
    "currState": {
      "value": "",
      "innerText": "Add To Bag"
    },
    "attributes": {
      "class": "item__atb buyButton",
      "id": "buy_NN31219",
      "innerText": "Add To Bag"
    },
    "subType": "submit"
  },
  "event": {
    "tlEvent": "click",
    "type": "click"
  },
  "dcid": "dcid-4.1782147599902"
}
```

### Key fields and their triggers dot-notation paths

| Console field | triggers attribute key | Example value |
|---|---|---|
| `event.type` | `"event.type"` | `"click"` |
| `target.id` | `"target.id"` | `"buy_NN31219"` |
| `target.tlType` | `"target.tlType"` | `"button"` |
| `target.attributes.class` | `"target.attributes.class"` | `"item__atb buyButton"` |
| `target.attributes.innerText` | `"target.attributes.innerText"` | `"Add To Bag"` |
| `target.attributes.id` | `"target.attributes.id"` | `"buy_NN31219"` |
| `target.subType` | `"target.subType"` | `"submit"` |

### Selector strategy for Type 4

Prefer in this order:

1. **`target.attributes.innerText`** — human-readable, stable across product variants. Good for buttons with fixed labels ("Add To Bag", "Add To Basket", "Subscribe").
2. **`target.id`** — exact match when ID is static (e.g. `"subscribe-btn"`). Avoid when ID is dynamic (e.g. `"buy_NN31219"` — changes per product).
3. **`target.attributes.class`** — use a stable class that uniquely identifies the element (e.g. `"item__atb buyButton"`). Avoid generated/utility classes.
4. **`target.tlType` + `event.type`** — broad fallback; combine with enhance function guard.

**Example — addToCart with confirmed Type 4:**
```json
{
  "attributes": {
    "event.type": "click",
    "target.attributes.innerText": "Add To Bag"
  },
  "label": "addToCart Button Clicked"
}
```

### Extracting data from Type 4 in the enhance function

When a signal fires on a Type 4 click, `help.webEvent` contains the SDK message. Access target fields via:

```js
// In enhance function (click-triggered signal):
const targetId = help.webEvent?.target?.id || '';          // "buy_NN31219"
const baseId   = targetId.replace(/^buy_/, '');            // "NN31219"
const btnText  = help.webEvent?.target?.currState?.innerText; // "Add To Bag"
```

Use `target.id` stripped of any prefix to derive productId, formId, or other entity identifiers when the element ID encodes them.

---

## Type 5 — Custom event (signal fired)

Fires when a configured signal emits. In test mode this is a fake `logSignal` call visible in the console. Use to confirm the signal fired, inspect the payload, and identify null/missing required fields.

```json
{
  "type": 5,
  "customEvent": {
    "name": "logSignal",
    "data": {
      "signalType": "productView",
      "productId": "NN31219",
      "productName": "Example Brand Mens T-Shirt",
      "unitPrice": 19.99,
      "currency": "GBP",
      "effect": "positive",
      "audience": {}
    }
  }
}
```

### What to check in Type 5

- All required fields are non-null (see signal-schema.md for per-signal requirements).
- `unitPrice`, `orderValue`, `numberOfResults` are numbers, not strings.
- `productUrls` and `imageUrls` are arrays.
- `effect` is `"positive"` or `"negative"` (not `"neutral"` for commerce signals).
- `audience.Email` only present after confirmed consent.
- No password, payment, or PII fields appear.

### Type 5 — dlListener (dataLayer push captured)

When `GAdataLayerName` is set and a dataLayer push occurs, the SDK emits a Type 5 `dlListener` event. Use this to discover event names for dataLayer-triggered signals.

```json
{
  "type": 5,
  "customEvent": {
    "name": "dlListener",
    "data": {
      "event": "add_to_cart",
      "ecommerce": {
        "currency": "GBP",
        "items": [{ "item_id": "NN31219", "item_name": "...", "price": 19.99 }]
      }
    }
  }
}
```

When you see a `dlListener` event with a relevant `data.event` name, update the profile:
```json
{
  "signals": {
    "addToCart": {
      "triggerType": "dataLayer",
      "dataLayerEvent": "add_to_cart"
    }
  }
}
```

---

## dataLayer-first configuration rule

**Always check for dataLayer events before falling back to DOM/click triggers.**

When generating or updating a signal configuration, follow this decision tree:

```
1. Is window.dataLayer present and non-empty?
   YES → Instrument it and observe pushes during key interactions.
         Did a relevant event fire (add_to_cart, purchase, view_item, etc.)?
         YES → Use triggerType: "dataLayer", set dataLayerEvent to the event name.
               Extract fields from help.webEvent.customEvent.data.ecommerce.*
         NO  → Fall through to step 2.
   NO  → inspection.dataLayerAvailable = false. Fall through to step 2.

2. Is there a stable DOM element or click event (Type 4) for this interaction?
   YES → Use triggerType: "click" with triggers targeting Type 4 attributes.
         Extract fields from JSON-LD, meta, or DOM selectors in enhance function.
   NO  → Mark signal as "Requires customer dataLayer/API/event payload".
```

Set `inspection.dataLayerAvailable` in the profile:
- `true` — dataLayer array found in window
- `false` — not present
- `null` — not yet checked

Set `inspection.dataLayerEvents` to the list of confirmed event names once observed (e.g. `["add_to_cart", "purchase", "view_item"]`).

---

## Iterative round workflow

| Round | Goal | Console focus |
|---|---|---|
| 0 | Generate initial script, instrument dataLayer | Confirm Type 2 fires on load; note Type 4 IDs/classes for key CTAs |
| 1 | Refine triggers from observed Type 4; confirm dataLayer events | Check Type 5 dlListener for event names; update `dataLayerEvents` |
| 2 | Fix null payload fields; validate all Type 5 signal payloads | Every required field non-null; types correct; no PII |
| 3+ | Edge cases, consent, deduplication, zero-result search | Confirm `effect: "negative"` for zero results; no duplicate signals on refresh |
