# Signal Mapping Reference

## Status and source values

Allowed statuses:

- Found automatically
- Inferred with confidence
- Needs confirmation
- Not available on page
- Requires customer dataLayer/API/event payload

Allowed source types:

- URL
- Meta tag
- JSON-LD
- DOM selector
- dataLayer
- sessionStorage
- localStorage
- AJAX response
- customer-provided value
- fallback/default

## Common fields

All enabled signals may include:

- `effect`: `positive`, `negative`, or `neutral`
- `audience.Email`: validated and consented email only
- `signalCustomAttributes`: no unapproved PII

Return `null` or do not emit when required data is unavailable.

## pageView

Required:

- signalType
- name
- category
- url
- pageCategory
- effect

Optional:

- audience.Email
- signalCustomAttributes

Recommended categories:

`homepage`, `product`, `collection`, `cart`, `checkout`, `thank-you`, `demo`, `demo-success`, `event`, `event-success`, `resource`, `report`, `search`, `blog`, `unknown`.

Track current and previous URL in session storage. Prefer the prior in-session URL over `document.referrer`. Never set previous URL equal to current URL.

## productView

Required:

- productId
- productName
- unitPrice as number
- currency
- productUrls as array
- imageUrls as array
- effect

Optional:

- productDescription
- discount as number
- productCategory
- availability
- inventoryQuantity as number
- brandName
- sku
- productStatus
- audience.Email
- signalCustomAttributes

Extraction priority: Product JSON-LD, dataLayer product, metadata, stable DOM, URL fallback, confirmed default.

### help.jsonLdGet(path)

Reads all `<script type="application/ld+json">` tags on the page, parses them, and traverses a dot-notation path. Handles both single-nested `[{...}]` and double-nested `[[{...}]]` structures by flattening one level before traversal — so the path `'0.name'` works regardless of nesting.

```js
help.jsonLdGet('0.name')                  // → product name
help.jsonLdGet('0.sku')                   // → SKU
help.jsonLdGet('0.offers.0.price')        // → price (offer is array)
help.jsonLdGet('0.offers.price')          // → price (offer is object)
help.jsonLdGet('0.offers.0.priceCurrency')// → currency code
help.jsonLdGet(null)                      // → entire flattened array (for inspection)
```

If a site's JSON-LD is structured as `[[{name:"...",sku:"..."}]]` (double array), it gets flattened to `[{name:"...",sku:"..."}]` internally, so the path `'0.name'` still resolves correctly. Always inspect the raw JSON-LD during onboarding to confirm the nesting depth.

For non-commerce B2B pages, `unitPrice: 1` and a confirmed currency may be used only as clearly marked placeholders.

## addToCart

Required:

- productId
- productName
- itemQuantity as number
- unitPrice as number
- currency
- effect

Optional:

- productDescription
- discount
- productCategory
- productUrls as array
- imageUrls as array
- shoppingCartUrl
- audience.Email
- signalCustomAttributes

Valid triggers include click, form interaction, form submit, CTA click, successful AJAX response, dataLayer event, or checkout start.

For B2B, explicitly confirm whether this represents demo request, form start, registration start, report download start, contact sales, or pricing CTA.

Deduplicate using signal + entity ID + journey state. Use a short TTL for click duplication and a durable session key for completed transitions.

## order

Required:

- orderId
- orderValue as number
- currency
- orderedItems as array
- effect

Optional numeric fields:

- orderSubtotal
- orderShippingHandling
- orderTax
- orderDiscount

Optional:

- audience.Email
- signalCustomAttributes

Prefer real confirmation ID and payload data. For behavioural B2B conversions, a synthetic ID such as `demo-<timestamp>` is permitted only when labelled non-financial and deduplicated.

## identification

**Trigger:** `event.type: "change"` on the email input field (Type 4 `valueChange` event). Fires when the user enters or changes their email address on a sign-in or registration page.

**Email source:** `help.webEvent.target.currState.value` — read directly from the Type 4 event. No DOM scanning required.

**triggers (Option A — stable target.name):**
```json
{ "event.type": "change", "target.name": "email" }
```

**triggers (Option B — generated/unstable name, use tlType + URL guard in enhance):**
```json
{ "event.type": "change", "target.tlType": "textBox" }
```

**Enhance function rules:**
- Read email from `help.webEvent?.target?.currState?.value`
- Validate with `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`
- Guard on page URL — only fire on sign-in/registration paths
- Deduplicate: if `sessionStorage.getItem('aco_email_value') === rawEmail`, return false
- Store to `sessionStorage` only — never `localStorage`
- Attach to `signal.audience = { Email: rawEmail }`

**Auto-capture:** fill the email field with a dummy email (`aco-test-<timestamp>@mailinator.com`) and dispatch a `change` event. The resulting Type 4 `capturedChangeEvents` entry reveals `target.name`, `target.id`, `target.tlType`, and `target.currState.value` — use these to configure the triggers trigger. No test account or form submission required.

**Scope:** sign-in and registration pages only. Excludes newsletter forms, checkout guest email, contact forms, password reset, and profile update pages.

## Forms

Support:

- formInteraction
- formSubmit
- lead, demo, event, newsletter, contact sales, and resource forms

Ignore by default:

- login
- password/reset
- payment
- shipping
- search
- add-to-cart utility forms

Do not capture field values for general form telemetry.

## onSiteSearch

Required:

- searchTerm
- numberOfResults as number
- effect

Use `positive` when results are present and `negative` for zero results. Confirm the query parameter and result count source.

## productConfiguration

Captures a customer's intent to configure a product — selecting a colour, size, variant, or changing quantity. One signal definition can have **multiple triggers** (one per interaction type). Each trigger fires the same signal with a different `configurationType` set via the `label`.

### Required fields

- `configurationType` — set in enhance from `help.label` (the matched trigger's label). Use canonical values below.
- `productId` — same source as `productView` (JSON-LD sku, URL, or DOM)
- `productName` — same source as `productView`
- `effect` — always `"positive"` unless the selection is unavailable/out of stock

### Optional fields (populate when available)

- `unitPrice` — current displayed price (number)
- `currency` — ISO 4217 string
- `discount` — number
- `inventoryQuantity` — number (quantity selected or remaining stock)
- `productCategory` — string
- `productDescription` — string
- `productUrls` — array
- `imageUrls` — array (update when variant image changes)
- `actionState` — the selected value string: colour name, size label, qty value, variant name
- `audience.Email` — from sessionStorage if available
- `signalCustomAttributes` — additional attributes

### Canonical `configurationType` values (retail)

| Value | Interaction |
|---|---|
| `"colour"` | Colour swatch or colour radio button click |
| `"size"` | Size button, radio, or dropdown change |
| `"quantity"` | Qty input change or +/- button click |
| `"variant"` | Generic variant select / dropdown change |
| `"subscription-frequency"` | Subscription cadence selector (one-time / monthly / yearly) |
| `"amount"` | Price/amount field change (donations, flexible pricing) |
| Custom label | Use `help.label` directly for any other interaction |

### Multiple triggers pattern

Unlike most signals, `productConfiguration` uses a **triggers array** — one entry per distinct interaction element. The enhance function uses `help.label` to branch:

```json
{
  "signalType": "productConfiguration",
  "triggers": [
    {
      "attributes": { "event.type": "click", "target.attributes.data-colour": "<any>" },
      "label": "colour"
    },
    {
      "attributes": { "event.type": "change", "target.name": "size" },
      "label": "size"
    },
    {
      "attributes": { "event.type": "change", "target.name": "qty" },
      "label": "quantity"
    }
  ]
}
```

> **Note on `target.attributes.data-colour`:** The shim now captures `data-colour`, `data-color`, `data-size`, `data-variant`, and `aria-label` on click targets. If the swatch element has `data-colour="Red"`, use `"target.attributes.data-colour"` as the triggers key. If it uses `innerText`, use `"target.attributes.innerText"`.

### Enhance function template (retail)

```js
enhance: function(signal, help) {
  // Attach email from session if available
  const audience = help.retrieve('audience') || {};
  if (audience.Email) signal.audience = { Email: audience.Email };

  // Set configurationType from trigger label
  signal.configurationType = help.label;

  // Populate product identity (same sources as productView)
  signal.productId   = (help.jsonLdGet('0.sku') || '').split('/')[0]
                     || help.cssGet('[data-product-id]', 'data-product-id')
                     || null;
  signal.productName = help.jsonLdGet('0.name') || help.cssGet('h1', 'innerText') || null;
  signal.unitPrice   = parseFloat(help.jsonLdGet('0.offers.0.price')) || null;
  signal.currency    = help.jsonLdGet('0.offers.0.priceCurrency') || 'GBP';

  if (help.label === 'colour') {
    // actionState: the colour selected — from data-colour attr or innerText of clicked swatch
    signal.actionState = help.webEvent?.target?.attributes?.['data-colour']
                      || help.webEvent?.target?.attributes?.['data-color']
                      || help.webEvent?.target?.currState?.innerText
                      || null;

  } else if (help.label === 'size') {
    // actionState: selected size label — from select value or radio innerText
    signal.actionState = help.webEvent?.target?.currState?.value
                      || help.webEvent?.target?.currState?.innerText
                      || null;

  } else if (help.label === 'quantity') {
    // actionState: new qty value; inventoryQuantity mirrors it
    const qty = parseInt(help.webEvent?.target?.currState?.value, 10);
    signal.actionState = isNaN(qty) ? null : String(qty);
    signal.inventoryQuantity = isNaN(qty) ? null : qty;
  }

  return signal;
}
```

### Interaction discovery on product display page (PDP) (auto-capture)

On the product detail page, after injecting the shim, simulate one interaction of each type and read the resulting Type 4 event to confirm the correct `triggers` attributes:

```js
// Read all Type 4 events captured so far on this page
JSON.parse(JSON.stringify(window.__acoCapture?.type4 || []))
  .filter(e => e.event.type === 'click' || e.event.type === 'change')
  .map(e => ({ eventType: e.event.type, id: e.target.id, name: e.target.attributes.name, innerText: e.target.currState?.innerText, dataColour: e.target.attributes?.['data-colour'], dataSize: e.target.attributes?.['data-size'], className: e.target.attributes?.class }))
```

Use the output to choose the most stable `triggers` attribute for each trigger. Prefer:
1. `data-colour` / `data-size` / `data-variant` (explicit semantic attribute — most stable)
2. `target.name` for `change` events (form field name — stable)
3. `target.attributes.innerText` for click events (human-readable label)
4. `target.attributes.class` as a fallback

### Safety rule

Never simulate a click on a quantity `+` or `-` button that would trigger an add-to-cart or checkout flow. Only capture the `change` event on the qty `input` and read the resulting Type 4 passively.

Prefer data attributes, semantic IDs, ARIA, field names, stable hrefs, then visible text.

## richMediaInteraction

Fields:

- mediaId
- url
- mediaCategory
- mediaName
- interactionType
- effect
- audience
- signalCustomAttributes

Detect YouTube, Vimeo, video embeds, podcast links, webinar links, and downloadable assets.
