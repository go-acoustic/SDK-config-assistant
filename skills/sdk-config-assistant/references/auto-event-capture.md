# Automatic SDK Event Capture

This procedure injects a lightweight capture shim into the browser, navigates customer pages, simulates key interactions, and reads the resulting Type 2 and Type 4 events — without requiring the user to perform any manual actions or paste console output.

Run this before building the website profile. The captured events are the primary source for `triggers` trigger configuration.

---

## Step 1 — Inject the capture shim

Run this once per page via `javascript_tool` immediately after navigation. It installs a minimal observer that records Type 2 (page load) and Type 4 (interaction) events in `window.__acoCapture` using the same structure the Acoustic SDK produces.

```js
(() => {
  if (window.__acoCapture) return '__acoCapture already active';

  window.__acoCapture = { type2: [], type4: [], dataLayer: [] };

  // TYPE 2 — page load (fires immediately on injection)
  window.__acoCapture.type2.push({
    type: 2,
    screenview: {
      type: 'LOAD',
      url: location.pathname + location.search,
      originalUrl: location.pathname + location.search,
      host: location.origin,
      title: document.title,
      referrer: document.referrer,
      queryParams: Object.fromEntries(new URL(location.href).searchParams)
    }
  });

  // TYPE 4 — click and change interactions (passive listeners, do not interfere with handlers)
  const _acoRecord = function(el, eventType) {
    window.__acoCapture.type4.push({
      type: 4,
      target: {
        id: el.id || null,
        tlType: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || el.tagName.toLowerCase(),
        subType: el.getAttribute('type') || null,
        currState: {
          value: el.value || null,
          innerText: (el.innerText || el.textContent || '').trim().slice(0, 120)
        },
        attributes: {
          class: el.className || null,
          id: el.id || null,
          innerText: (el.innerText || el.textContent || '').trim().slice(0, 120),
          href: el.href || null,
          name: el.getAttribute('name') || null,
          'data-action': el.dataset.action || null,
          'data-testid': el.dataset.testid || null,
          'data-colour': el.dataset.colour || el.dataset.color || null,
          'data-size': el.dataset.size || null,
          'data-variant': el.dataset.variant || null,
          'data-value': el.dataset.value || null,
          'aria-label': el.getAttribute('aria-label') || null
        }
      },
      event: { tlEvent: eventType, type: eventType }
    });
  };

  document.addEventListener('click', function(e) {
    const el = e.target.closest('button, a, input[type="submit"], input[type="button"], [role="button"], [data-colour], [data-color], [data-size], [data-variant], label');
    if (!el) return;
    _acoRecord(el, 'click');
  }, true); // capture phase — fires before any stopPropagation

  // change — covers size/colour/qty: select, radio, checkbox, number, range
  document.addEventListener('change', function(e) {
    const el = e.target;
    const tag = el.tagName.toLowerCase();
    const itype = (el.getAttribute('type') || '').toLowerCase();
    const isConfigEl = tag === 'select' ||
      (tag === 'input' && (itype === 'radio' || itype === 'checkbox' || itype === 'number' || itype === 'range')) ||
      /qty|quantity|colour|color|size|variant/i.test(el.className + ' ' + (el.getAttribute('name') || ''));
    if (!isConfigEl) return;
    _acoRecord(el, 'change');
  }, true);

  // DATALAYER — track pushes
  if (Array.isArray(window.dataLayer) && !window.dataLayer.__acoShimmed) {
    const orig = window.dataLayer.push.bind(window.dataLayer);
    window.dataLayer.push = (...items) => {
      window.__acoCapture.dataLayer.push(...structuredClone(items));
      return orig(...items);
    };
    window.dataLayer.__acoShimmed = true;
  }

  return '__acoCapture initialized';
})()
```

---

## Step 2 — Read Type 2 (fires automatically on page load)

After injecting the shim on any page, read the auto-captured page load event immediately:

```js
window.__acoCapture?.type2 || []
```

**What to extract for profile configuration:**

| Captured field | Profile use |
|---|---|
| `screenview.url` | Page category rule path pattern |
| `screenview.title` | `pageView.name` fallback DOM selector |
| `screenview.queryParams` | Search term parameter name |
| `screenview.host` | Confirm production domain |

**pageView onEvent (universal — confirmed from Type 2):**
```json
{ "attributes": { "screenview.type": "LOAD" } }
```

---

## Step 3 — Auto-discover interactive elements

Run this to find the elements that should generate key Type 4 events. Returns candidates for addToCart, search, and form signals.

```js
(() => {
  const PATTERNS = {
    addToCart: [
      'button[id^="buy_"]', 'button[id^="add"]',
      '[data-action="add-to-cart"]', '[data-testid*="add-to-cart"]',
      'button[class*="AddToCart"]', 'button[class*="addToCart"]',
      'button[class*="atb"]', 'button[class*="add-to-bag"]',
      'button[class*="AddToBag"]', 'input[value*="Add to"]',
      'form[action*="basket"] button[type="submit"]',
      'form[action*="cart"] button[type="submit"]'
    ],
    colourSwatch: [
      '[data-colour]', '[data-color]',
      'button[class*="colour"]', 'button[class*="color"]', 'button[class*="swatch"]',
      'input[type="radio"][name*="colour"]', 'input[type="radio"][name*="color"]',
      '[class*="ColourSwatch"]', '[class*="color-swatch"]',
      'li[class*="colour"]', 'li[class*="swatch"]',
      '[data-testid*="colour"]', '[data-testid*="color"]'
    ],
    sizeSelector: [
      'select[name*="size"]', 'select[id*="size"]',
      'input[type="radio"][name*="size"]',
      'button[class*="size"]', '[data-size]',
      '[class*="SizeOption"]', '[class*="size-option"]',
      'li[class*="size"]', '[data-testid*="size"]',
      'select[name*="variant"]', 'select[id*="variant"]'
    ],
    quantitySelector: [
      'input[type="number"][name*="qty"]', 'input[type="number"][name*="quantity"]',
      'input[type="number"][id*="qty"]', 'input[type="number"][id*="quantity"]',
      'select[name*="qty"]', 'select[name*="quantity"]',
      'input[class*="qty"]', 'input[class*="quantity"]',
      'button[class*="qty-plus"]', 'button[class*="qty-minus"]',
      'button[aria-label*="increase"]', 'button[aria-label*="decrease"]',
      'button[aria-label*="quantity"]'
    ],
    searchSubmit: [
      'button[type="submit"][class*="search"]',
      'button[aria-label*="earch"]',
      'form[role="search"] button[type="submit"]',
      'form .search-button', '.aa-SubmitButton'
    ],
    formSubmit: [
      'form:not([action*="login"]):not([action*="signin"]):not([action*="password"]):not([action*="checkout"]) button[type="submit"]',
      'form[action*="signup"] button[type="submit"]',
      'form[action*="subscribe"] button[type="submit"]',
      'input[type="submit"][id*="SignUp"]',
      'input[type="submit"][id*="subscribe"]'
    ]
  };

  const results = {};
  for (const [signal, selectors] of Object.entries(PATTERNS)) {
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el && el.offsetParent !== null) {
          results[signal] = {
            selector: sel,
            id: el.id || null,
            innerText: (el.innerText || el.textContent || el.value || '').trim().slice(0, 80),
            className: (el.className || '').slice(0, 120),
            type: el.getAttribute('type'),
            href: el.href || null,
            found: true
          };
          break;
        }
      } catch(e) {}
    }
    if (!results[signal]) results[signal] = { found: false };
  }
  return results;
})()
```

---

## Step 4 — Simulate interactions to capture Type 4

For each discovered element, fire a synthetic click. The capture shim's listener records the resulting Type 4 event before any page navigation or AJAX call completes.

**Important safety rules:**
- Only simulate clicks on elements that are confirmed present and visible (`offsetParent !== null`).
- Do NOT simulate clicks on: payment buttons, form submit buttons on checkout pages, login/sign-in forms, or any button labelled "Place Order", "Pay", "Confirm".
- Add-to-cart clicks on live sites add a real item to the basket — acceptable for test/staging. On production, navigate away immediately after capture.
- Read `window.__acoCapture.type4` within the same `javascript_tool` call or immediately after, before any navigation.

```js
(() => {
  // Simulate click on a known selector and capture the resulting Type 4 immediately
  const capture = (selector) => {
    const el = document.querySelector(selector);
    if (!el || el.offsetParent === null) return { found: false, selector };
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    // Give capture listener a tick to record
    const events = (window.__acoCapture?.type4 || []).slice(-3);
    return { found: true, selector, id: el.id, innerText: (el.innerText||'').trim().slice(0,80), capturedEvents: events };
  };

  return {
    addToCart: capture('button[id^="buy_"], button[class*="atb"], [data-action="add-to-cart"]'),
  };
})()
```

To capture search Type 4, navigate to the search results page — the URL load triggers Type 2 automatically. Then read `queryParams` from the Type 2 event to confirm the search parameter name.

---

## Step 5 — Read all captured events

After simulating interactions, read the full capture buffer:

```js
JSON.parse(JSON.stringify(window.__acoCapture || {}))
```

Returns:
```json
{
  "type2": [ { "type": 2, "screenview": { "type": "LOAD", "url": "/01/details/NN31219", ... } } ],
  "type4": [
    {
      "type": 4,
      "target": {
        "id": "buy_NN31219",
        "attributes": { "class": "item__atb buyButton", "innerText": "Add To Bag" }
      },
      "event": { "type": "click" }
    }
  ],
  "dataLayer": [ { "event": "add_to_cart", "ecommerce": { ... } } ]
}
```

---

## Step 6 — Map captured events to triggers config

Use this mapping logic to convert captured Type 4 data into `triggers` entries for the profile.

**Selector preference for triggers attributes (in order):**

1. `target.attributes.innerText` — if the button has a fixed human-readable label ("Add To Bag", "Subscribe"). Most stable across product variants.
2. `target.attributes.class` — if the label varies but the class is stable (e.g. `"item__atb buyButton"`).
3. `target.id` — only if the ID is static (not dynamic like `buy_NN31219`). Dynamic IDs should be used for entity ID extraction in the enhance function, not for triggers matching.
4. `target.tlType` + `event.type` — broadest fallback; add an enhance function guard.

**Template:**
```json
{
  "triggers": [
    {
      "attributes": {
        "event.type": "click",
        "target.attributes.innerText": "<innerText from Type 4>"
      },
      "label": "<signal name> — auto-captured Type 4"
    }
  ]
}
```

**Entity ID extraction from `target.id`:**

When `target.id` encodes a product/entity ID with a prefix (e.g. `"buy_NN31219"`), document the strip transform in the enhance function:
```js
// In addToCart enhance:
const rawId = help.webEvent?.target?.id || help.cssGet("[id^='buy_']", "id") || '';
signal.productId = rawId.replace(/^buy_/, '') || (help.jsonLdGet('0.sku')||'').split('/')[0] || null;
```

---

## productConfiguration — capture on product display page (PDP)

`productConfiguration` fires when a customer interacts with product options: colour swatches, size selectors, quantity changes, or variant dropdowns. One signal definition uses a **triggers array** — one entry per interaction type — and the enhance function branches on `help.label`.

### Step A — Inject shim and passively read interaction events

After navigating to the product display page (PDP) and injecting the shim (Step 1), interact with the page or read events that were triggered by the user's own interactions:

```js
// Read all Type 4 events with event.type click or change — filter to config interactions
JSON.parse(JSON.stringify(window.__acoCapture?.type4 || []))
  .filter(e => e.event.type === 'click' || e.event.type === 'change')
  .map(e => ({
    eventType: e.event.type,
    tagName:   e.target.tlType,
    id:        e.target.id,
    name:      e.target.attributes?.name,
    innerText: (e.target.currState?.innerText || '').slice(0, 60),
    value:     e.target.currState?.value,
    dataColour: e.target.attributes?.['data-colour'],
    dataColor:  e.target.attributes?.['data-color'],
    dataSize:   e.target.attributes?.['data-size'],
    dataVariant: e.target.attributes?.['data-variant'],
    ariaLabel:  e.target.attributes?.['aria-label'],
    className:  (e.target.attributes?.class || '').slice(0, 80)
  }))
```

### Step B — Discover configuration elements on product display page (PDP)

Run the element discovery script (Step 3) — it now includes `colourSwatch`, `sizeSelector`, and `quantitySelector` patterns. If elements are found, their selector and captured attributes feed directly into the triggers array.

### Step C — Broad variant selector discovery + simulate interactions

Sites implement size/colour/variant selectors in many ways. Run the broad discovery first to identify what pattern the site uses, then simulate only what's safe.

#### Step C1 — Broad discovery (run on every product display page (PDP) before simulating anything)

This script tries every known selector pattern across all common implementations. Do not assume a pattern — always run discovery first.

```js
(() => {
  const found = {};
  const vis = el => el && el.offsetParent !== null;

  // --- SIZE patterns ---
  const sizePatterns = [
    // Standard HTML selects
    'select[name*="size" i]', 'select[id*="size" i]', 'select[class*="size" i]',
    'select[name*="variant" i]', 'select[id*="variant" i]',
    // Radio inputs
    'input[type="radio"][name*="size" i]', 'input[type="radio"][value]',
    // MUI / custom radiogroup
    '[role="radiogroup"] [role="radio"]', '[role="radiogroup"] button',
    // Data-attribute buttons (e.g. MandM: button[data-product="SKU/S"])
    'button[data-size]', '[data-size]',
    'button[data-gtm*="size" i]', 'button[data-testid*="size" i]',
    // Class-based buttons / list items
    'button[class*="size" i]', 'li[class*="size" i] button', 'li[class*="attributes"] button',
    'button.attributes__select', '[class*="SizeOption" i]', '[class*="size-option" i]',
    '[class*="SizeSelector" i] button', '[class*="size-selector" i] button',
    // Aria-label fallback
    'button[aria-label*="size" i]', '[aria-label*="select size" i]',
  ];
  for (const sel of sizePatterns) {
    try {
      const els = [...document.querySelectorAll(sel)].filter(vis);
      if (els.length) {
        const el = els.find(e => !e.disabled) || els[0];
        found.size = { selector: sel, count: els.length, tag: el.tagName,
          text: (el.innerText||el.value||'').trim().slice(0,30),
          dataProduct: el.dataset.product||'', dataSize: el.dataset.size||'',
          dataGtm: el.dataset.gtm||'', name: el.name||'', value: el.value||'' };
        break;
      }
    } catch(e) {}
  }

  // --- COLOUR patterns ---
  const colourPatterns = [
    // Data attributes (most explicit)
    '[data-colour]', '[data-color]',
    'button[data-colour]', 'button[data-color]',
    'button[data-gtm*="colour" i]', 'button[data-gtm*="color" i]',
    'button[data-testid*="colour" i]', 'button[data-testid*="color" i]',
    // Radio inputs
    'input[type="radio"][name*="colour" i]', 'input[type="radio"][name*="color" i]',
    // Swatch elements
    'button[class*="swatch" i]', 'li[class*="swatch" i]',
    '[class*="ColourSwatch" i]', '[class*="color-swatch" i]',
    'button[class*="colour" i]', 'li[class*="colour" i] button',
    '[class*="ColorOption" i]', '[class*="colour-option" i]',
    // Select dropdown
    'select[name*="colour" i]', 'select[name*="color" i]', 'select[id*="color" i]',
    // Aria-label fallback
    '[aria-label*="colour" i]', '[aria-label*="color" i]',
  ];
  for (const sel of colourPatterns) {
    try {
      const els = [...document.querySelectorAll(sel)].filter(vis);
      if (els.length) {
        const el = els[0];
        found.colour = { selector: sel, count: els.length, tag: el.tagName,
          text: (el.innerText||'').trim().slice(0,30),
          dataColour: el.dataset.colour || el.dataset.color || '',
          ariaLabel: el.getAttribute('aria-label')||'' };
        break;
      }
    } catch(e) {}
  }

  // --- QUANTITY patterns ---
  const qtyPatterns = [
    'input[type="number"][name*="qty" i]', 'input[type="number"][name*="quantity" i]',
    'input[type="number"][id*="qty" i]', 'input[type="number"][id*="quantity" i]',
    'input[class*="qty" i]', 'input[class*="quantity" i]',
    'select[name*="qty" i]', 'select[name*="quantity" i]',
    '[aria-label*="quantity" i]',
  ];
  for (const sel of qtyPatterns) {
    try {
      const el = document.querySelector(sel);
      if (el && vis(el)) {
        found.quantity = { selector: sel, tag: el.tagName, name: el.name||'', id: el.id, currentValue: el.value };
        break;
      }
    } catch(e) {}
  }

  // --- GENERIC VARIANT patterns (fallback when size/colour patterns miss) ---
  // Catches custom listbox UIs, role=option dropdowns, and bespoke variant grids
  if (!found.size && !found.colour) {
    const variantPatterns = [
      '[role="listbox"] [role="option"]',
      '[role="option"]',
      'button[data-variant]', '[data-variant]',
      'button[data-value]',
      'ul[class*="option" i] button', 'ul[class*="variant" i] button',
      'ul[class*="selector" i] button', 'ol[class*="option" i] button',
    ];
    for (const sel of variantPatterns) {
      try {
        const els = [...document.querySelectorAll(sel)].filter(vis);
        if (els.length) {
          const el = els[0];
          found.variant = { selector: sel, count: els.length, tag: el.tagName,
            text: (el.innerText||'').trim().slice(0,30),
            dataVariant: el.dataset.variant||el.dataset.value||'' };
          break;
        }
      } catch(e) {}
    }
  }

  // --- SUMMARY of what was found ---
  found._summary = {
    sizeFound: !!found.size,
    colourFound: !!found.colour,
    quantityFound: !!found.quantity,
    variantFallbackFound: !!found.variant,
    recommendedTriggerType: found.size?.tag === 'SELECT' || found.colour?.tag === 'SELECT'
      ? 'change (select dropdown)'
      : found.size?.tag === 'INPUT' || found.colour?.tag === 'INPUT'
        ? 'change (radio/input)'
        : 'click (button/swatch)'
  };

  return found;
})()
```

#### Step C2 — Simulate interactions (only after discovery confirms elements)

Run only for the element types discovered in Step C1. **Do not guess selectors** — use the exact `selector` value from the discovery output.

```js
(() => {
  const results = {};
  const vis = el => el && el.offsetParent !== null;

  // SIZE — dispatch change (select/radio) or click (button)
  // Replace <SIZE_SELECTOR> with the selector from Step C1
  const sizeSel = '<SIZE_SELECTOR_FROM_DISCOVERY>';
  const sizeEls = [...document.querySelectorAll(sizeSel)].filter(vis);
  if (sizeEls.length > 1) {
    const target = sizeEls.find(e => !e.disabled && !e.classList.contains('selected')) || sizeEls[1];
    const tag = target.tagName.toLowerCase();
    const itype = (target.getAttribute('type')||'').toLowerCase();
    if (tag === 'select') {
      target.selectedIndex = Math.min(1, target.options.length - 1);
      target.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (tag === 'input' && (itype === 'radio' || itype === 'checkbox')) {
      target.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    }
    results.size = { selector: sizeSel, text: (target.innerText||target.value||'').trim().slice(0,30),
      dataProduct: target.dataset.product||'', dataSize: target.dataset.size||'' };
  }

  // COLOUR — always click (swatches are never selects)
  // Replace <COLOUR_SELECTOR> with the selector from Step C1
  const colourSel = '<COLOUR_SELECTOR_FROM_DISCOVERY>';
  const colourEls = [...document.querySelectorAll(colourSel)].filter(vis);
  if (colourEls.length > 0) {
    const target = colourEls[0];
    target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    results.colour = { selector: colourSel, dataColour: target.dataset.colour || target.dataset.color || '',
      text: (target.innerText||'').trim().slice(0,30) };
  }

  // QUANTITY — read current value only; do NOT simulate changes (may update basket)
  const qtySel = '<QTY_SELECTOR_FROM_DISCOVERY>';
  const qtyEl = document.querySelector(qtySel);
  if (qtyEl && vis(qtyEl)) {
    results.quantity = { selector: qtySel, name: qtyEl.name||'', id: qtyEl.id, value: qtyEl.value };
  }

  // Wait for dataLayer push, then read capture buffer
  await new Promise(r => setTimeout(r, 800));
  results.type4Captured = (window.__acoCapture?.type4 || []).slice(-6);
  results.dataLayerPushes = (window.__acoCapture?.dataLayer || []).slice(-4);

  return results;
})()
```

> **Safety:** Never simulate quantity changes — a +/- click may trigger a cart update or navigate away. Capture quantity `change` events passively (the shim records them on real user interaction), or use the discovered `name`/`id` from Step C1 to hardcode the trigger attribute directly in the profile.

#### Step C3 — Determine actionState source from captured Type 4

After simulation, inspect the captured Type 4 events to find the most reliable attribute for `actionState`:

```js
(window.__acoCapture?.type4 || []).slice(-6).map(e => ({
  eventType: e.event?.type,
  tag: e.target?.tlType,
  // Ranked attribute sources — use the first non-null one as actionState
  dataColour: e.target?.attributes?.['data-colour'] || e.target?.attributes?.['data-color'],
  dataSize:   e.target?.attributes?.['data-size'],
  dataVariant: e.target?.attributes?.['data-variant'],
  dataProduct: e.target?.attributes?.['data-product'], // e.g. MandM "NN31157/M" — strip SKU prefix
  dataGtm:    e.target?.attributes?.['data-gtm'],
  ariaLabel:  e.target?.attributes?.['aria-label'],
  value:      e.target?.currState?.value,
  innerText:  (e.target?.currState?.innerText||'').trim().slice(0,40),
  className:  (e.target?.attributes?.class||'').slice(0,80),
}))
```

**actionState resolution priority:**
1. `data-colour` / `data-color` / `data-size` / `data-variant` — explicit semantic value, most stable
2. `data-product` — when SKU+size are combined (e.g. `"NN31157/M"`), strip the product prefix: `data-product.split('/').pop()`
3. `aria-label` — accessible name on icon-only buttons
4. `currState.value` — select option value or input value
5. `currState.innerText` — visible label text (split on newline, take first line only)

### Step D — Build the triggers array from captured events

After capturing, read the buffer:

```js
const events = window.__acoCapture?.type4 || [];
const configEvents = events.filter(e => e.event.type === 'click' || e.event.type === 'change');
configEvents.map(e => ({
  eventType: e.event.type,
  best_attribute: e.target.attributes?.['data-colour'] ? 'data-colour'
    : e.target.attributes?.['data-size'] ? 'data-size'
    : e.target.attributes?.name ? 'name'
    : e.target.currState?.innerText ? 'innerText'
    : 'class',
  value: e.target.attributes?.['data-colour'] || e.target.attributes?.['data-size'] || e.target.attributes?.name || (e.target.currState?.innerText || '').slice(0,40) || e.target.attributes?.class
}))
```

**Attribute preference for triggers (in order):**

1. `target.attributes.data-colour` / `target.attributes.data-size` / `target.attributes.data-variant` — explicit semantic data attribute; most stable
2. `target.name` (for `change` events on form controls — `name="size"`, `name="qty"`)
3. `target.attributes.aria-label` — accessible name on icon buttons
4. `target.attributes.innerText` — visible label on click events
5. `target.attributes.class` — last resort; avoid utility class noise

**Example triggers array output:**

```json
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
```

> When `target.attributes.data-colour` is set, the value in the onEvent attribute should be a literal string that was captured (e.g. `"Red"`) or a wildcard match pattern if the SDK supports it. If the SDK requires exact match, document each colour as a separate trigger — or use `target.attributes.class` with a swatch-specific class as a broader catch-all.

---

## Step 7 — Ecommerce dataLayer discovery

Run this script on the product display page (PDP), cart, and confirmation pages (before and after key interactions like Add to Cart). It scans the full `window.dataLayer` for ecommerce events, identifies the schema (GA4 vs UA Enhanced Ecommerce), and maps event names to signals.

```js
(() => {
  const dl = window.dataLayer || [];
  const ecEvents = dl.filter(e => e.ecommerce);

  if (!ecEvents.length) {
    return { status: 'No ecommerce events found in dataLayer', total: dl.length };
  }

  // Identify schema from first ecommerce event
  const firstEc = ecEvents[0].ecommerce;
  let schema = 'unknown';
  if (firstEc.items) schema = 'ga4';
  else if (firstEc.detail || firstEc.add || firstEc.purchase || firstEc.checkout || firstEc.impressions) schema = 'ua';

  // Extract items array based on schema
  function getItems(ec) {
    if (schema === 'ga4') return ec.items || [];
    return ec.detail?.products || ec.add?.products || ec.remove?.products
        || ec.purchase?.products || ec.checkout?.products || ec.items || [];
  }

  // Build signal → event name map
  const signalEventMap = {
    productView: null,
    addToCart: null,
    order: null
  };

  // Common GA4 event names
  const GA4_MAP = { view_item: 'productView', add_to_cart: 'addToCart', purchase: 'order', begin_checkout: null };
  // Common UA event names
  const UA_MAP  = { productDetailView: 'productView', addToCart: 'addToCart', purchase: 'order',
                    checkout: null, productClick: null, impressions: null };

  ecEvents.forEach(e => {
    const signal = GA4_MAP[e.event] || UA_MAP[e.event];
    if (signal && !signalEventMap[signal]) signalEventMap[signal] = e.event;
  });

  // Sample the first item from the first event to show field names
  const sampleEc = ecEvents[0].ecommerce;
  const sampleItems = getItems(sampleEc);
  const sampleItem = sampleItems[0] || {};

  return {
    schema,
    signalEventMap,       // → copy this into inspection.ecommerceEventMap
    ecommerceEvents: ecEvents.map(e => ({
      event: e.event,
      itemCount: getItems(e.ecommerce).length,
      sampleFields: Object.keys(getItems(e.ecommerce)[0] || {})
    })),
    sampleItem,           // → shows actual field names (id vs item_id, name vs item_name, etc.)
    actionField: sampleEc?.purchase?.actionField || sampleEc?.checkout?.actionField || null
  };
})()
```

**Reading the output:**

- `schema` — use this to set `inspection.ecommerceSchema` in the profile (`"ga4"` or `"ua"`)
- `signalEventMap` — copy directly to `inspection.ecommerceEventMap` (e.g. `{ productView: "productDetailView", addToCart: "addToCart", order: "purchase" }`)
- `sampleItem` — shows the actual field names on this site: GA4 uses `item_id`/`item_name`, UA uses `id`/`name`. The generator handles both automatically.
- `actionField` — for UA order signals: contains `id` (orderId), `revenue`, `tax`, `shipping`

**If no ecommerce events appear in the buffer yet** — navigate to a product display page (PDP), wait for the page to fully load, then re-run. If the capture shim was injected before the page fired its own dataLayer push it will appear; if not, read `window.dataLayer` directly (not the capture buffer):

```js
(window.dataLayer || []).filter(e => e.ecommerce).map(e => ({
  event: e.event,
  keys: Object.keys(e.ecommerce),
  sample: e.ecommerce
}))
```

**Updating the profile after discovery:**

```json
"inspection": {
  "dataLayerAvailable": true,
  "ecommerceSchema": "ua",
  "ecommerceEventMap": {
    "productView": "productDetailView",
    "addToCart": "addToCart",
    "order": "purchase"
  }
}
```

This causes the generator to:
1. Add all three event names to `GAeventsAllowList`
2. Set each signal's trigger to `{ "customEvent.data.event": "<eventName>" }`
3. Use the correct item nesting path when building the enhance function

For any event names **not** in the common GA4/UA maps above (fully custom naming), add them manually to `ecommerceEventMap`.

---

## Full auto-capture workflow (summary)

```
For each page type (homepage, product display page (PDP), product listing page (PLP), search, cart, confirmation):
  1. Navigate to page
  2. Inject capture shim (or confirm it persists from previous page)
  3. Read type2 → record pageCategory, URL pattern, title
  4. Run element discovery → identify addToCart / search / formSubmit elements
  5. Simulate interaction on each discovered element
  6. Read type4 events → extract triggers attributes
  7. Check dataLayer buffer → check for ecommerce event names
  8. Clear type4 buffer before next page: window.__acoCapture.type4 = []

After all pages:
  9. Build pageCategoryRules from type2 URL patterns
  10. Build triggers for each signal from type4 attributes (prefer innerText > class > id)
  11. If dataLayer events found: switch triggerType to "dataLayer"
  12. Write to website profile and regenerate
```

---

## Checkout simulation (staging only — order signal configuration)

This step completes a real transaction on a staging or test site to capture the order confirmation dataLayer and fully configure the `order` signal. **Never run on production.**

### Pre-flight checks

Before starting, confirm all of the following:

1. **Environment confirmed as staging/test** — ask the user explicitly if not already established. Do not proceed if production.
2. **Test card details provided** — ask the user for: card number, expiry, CVV, billing name. Do not store or log these beyond the transaction. Never paste them into non-checkout fields.
3. **Test account credentials available** — ask for sign-in email and password if the checkout requires authentication.
4. **Cart has an item** — if not, first simulate an add-to-cart on the product display page (PDP) (Step 4 above).

Ask these questions before proceeding:
- "Is this a staging or test environment?"
- "Do you have test card details I can use to complete a transaction?" (If yes: "Please share card number, expiry, CVV, and billing name.")
- "Is a test account login required to check out?"

### Checkout flow

Navigate step by step. After each navigation, inject the capture shim and read Type 2 + dataLayer.

```
1. Navigate to cart → inject shim → read Type 2 (pageType: ViewBasket/Cart)
2. Proceed to checkout → inject shim → read Type 2 (pageType: Checkout)
3. Fill shipping details (address, phone) if required — use generic test data
4. Fill payment details using provided test card — enter into payment fields only
5. Click confirm/place order button
6. Wait for redirect to confirmation page
7. Inject shim on confirmation page → read Type 2 → read full dataLayer
```

Read the full dataLayer on the confirmation page:

```js
JSON.parse(JSON.stringify(window.__acoCapture?.dataLayer || window.dataLayer || []))
```

### What to extract from confirmation page

| dataLayer key | Profile field | Signal attribute |
|---|---|---|
| `transactionId` or `transaction_id` or `orderId` | `order.fields.orderId.sources[0].path` | `orderId` (required) |
| `transactionTotal` or `value` or `revenue` | `order.fields.orderValue.sources[0].path` | `orderValue` (required) |
| `transactionProducts` or `items` or `products` | `order.fields.orderedItems.sources[0].path` | `orderedItems` |
| `transactionTax` or `tax` | `order.fields.orderTax.sources[0].path` | `orderTax` |
| `transactionShipping` or `shipping` | `order.fields.orderShippingHandling` | `orderShippingHandling` |
| `currency` | `order.fields.currency` | `currency` |

Also check for a GA4-style `purchase` event:
```js
window.__acoCapture.dataLayer.find(e => e.event === 'purchase')
```

If a `purchase` event exists, switch `order` to `triggerType: "dataLayer"` with `dataLayerEvent: "purchase"` and extract fields from `ecommerce.*`.

### After transaction

- Update `inspection.dataLayerEvents` with any confirmed event names.
- Update `order.fields` with the confirmed key names.
- If no dataLayer event fires on confirmation: use `triggerType: "load"` with URL path guard (`/order-confirmation`, `/thankyou`, etc.) and confirmed dataLayer key names.
- Update the order mapping rows to `"Found automatically"` status.
- Increment `inspection.round` and regenerate.

---

## Identification — sign-in and registration only

The identification signal captures the user's email at the authentication boundary (sign-in or account registration). It does **not** fire on newsletter/marketing signup forms.

**Trigger:** `event.type: "change"` on the email input field — fires when the user enters or changes their email address. Email is read directly from `help.webEvent.target.currState.value` in the enhance function.

**Consent basis:** The user voluntarily identifies themselves by logging in or registering. No separate marketing consent check is required — the act of authentication is the consent boundary.

---

### Pre-flight checks

Before running the capture procedure, confirm:

1. **Test account available?** — Ask: "Do you have a test account (email + password) for this site?" If gathered during checkout simulation, reuse those credentials. If **not available**, the skill generates a dummy email automatically — no credentials needed.
2. **Email verification required for registration?** — Ask only if registering a new account. Determines whether full registration is viable.
3. **Sign-in page URL** — Confirm the URL (e.g. `/Secure/Account/SignIn`, `/login`, `/account/signin`).

---

### Auto-capture procedure — email field fill (works with or without test credentials)

The identification signal trigger is a `change`/`valueChange` Type 4 event on the email input field. This fires when the user types their email and leaves the field. The skill replicates this by programmatically filling the field with a dummy email and dispatching a `change` event — no form submission, no account creation, no redirect.

**If test credentials are available:** use the real test account email (e.g. `test@example.com`).
**If no credentials available:** generate a disposable dummy email automatically — `aco-test-<timestamp>@mailinator.com`. This is sufficient to configure the signal; the field is never actually submitted.

```
1. Navigate to sign-in page (or registration page if sign-in page has no email field visible without password)
2. Inject capture shim (Step 1)
3. Read Type 2 → confirm page URL/title
4. Run form discovery script (below) → confirm email field selector, name, id, tlType
5. Fill email field with dummy or test email → dispatch change → Type 4 valueChange fires
6. Read captured Type 4 → extract target.name, target.id, target.tlType, target.currState.value
7. Use captured attributes to configure triggers trigger
```

**Step 1 — Discover sign-in form structure:**

```js
(() => {
  const emailSelectors = [
    'input[type="email"]',
    'input[name="email"]', 'input[name="Email"]',
    'input[id*="email"]', 'input[id*="Email"]',
    'input[autocomplete="email"]', 'input[autocomplete="username"]',
    'input[type="text"][name*="email"]', 'input[type="text"][id*="email"]'
  ];
  const results = [];
  for (const sel of emailSelectors) {
    const el = document.querySelector(sel);
    if (el) results.push({ selector: sel, id: el.id, name: el.name, type: el.type, subType: el.type, autocomplete: el.autocomplete, visible: el.offsetParent !== null });
  }
  const emailEl = results.find(r => r.visible) || results[0];
  return {
    emailFields: results,
    bestEmailSelector: emailEl?.selector || null,
    bestName: emailEl?.name || null,
    bestId: emailEl?.id || null
  };
})()
```

**Step 2 — Fill email field and capture the Type 4 valueChange event:**

```js
(() => {
  // Use test account email if available; otherwise generate a disposable dummy
  const testEmail = typeof TEST_ACCOUNT_EMAIL !== 'undefined' && TEST_ACCOUNT_EMAIL
    ? TEST_ACCOUNT_EMAIL
    : 'aco-test-' + Date.now() + '@mailinator.com';

  const emailSelector = '<EMAIL_SELECTOR>'; // from Step 1 bestEmailSelector

  const emailEl = document.querySelector(emailSelector);
  if (!emailEl) return { error: 'Email field not found', selector: emailSelector };

  // Use native setter so React/Vue/Angular frameworks see the value change
  const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
  if (nativeSetter) nativeSetter.call(emailEl, testEmail); else emailEl.value = testEmail;

  // fire input first (React synthetic onChange depends on this)
  emailEl.dispatchEvent(new Event('input', { bubbles: true }));
  // fire change — this is the event the Acoustic SDK captures as Type 4 valueChange
  emailEl.dispatchEvent(new Event('change', { bubbles: true }));
  // fire blur — some forms trigger validation on blur
  emailEl.dispatchEvent(new Event('blur', { bubbles: true }));

  // Read capture buffer — the change event should appear as Type 4
  const captured = (window.__acoCapture?.type4 || []).filter(e => e.event?.type === 'change');
  return {
    emailUsed: testEmail,
    generatedDummy: !testEmail.includes('@mailinator') === false,
    capturedChangeEvents: captured.slice(-3).map(e => ({
      eventType: e.event?.type,
      tlEvent:   e.event?.tlEvent,
      targetName: e.target?.name,
      targetId:   e.target?.id,
      tlType:     e.target?.tlType,
      subType:    e.target?.subType,
      currValue:  e.target?.currState?.value,
      prevValue:  e.target?.prevState?.value
    }))
  };
})()
```

**Step 3 — Read the captured Type 4 and build the triggers trigger:**

From the `capturedChangeEvents` result, identify the email field entry (look for `currValue` matching the email you set). Then:

| If `targetName` is semantic (e.g. `"email"`, `"Email"`, `"emailAddress"`) | Use `target.name` in triggers |
|---|---|
| If `targetName` is generated/numeric (e.g. `"959062_249990pi_959062_249990"`) | Use `target.tlType: "textBox"` + URL guard in enhance |
| If `tlType: "textBox"` is present | Use it as a broad type guard, combined with URL guard |

---

### Auto-capture — full registration (fallback, when sign-in page not accessible)

Use only when: no sign-in page is accessible, and the site requires registration to see an email field. The field fill approach still applies — submit is optional.

```
1. Navigate to the registration page URL (/register, /account/register, /Secure/Account/Register)
2. Inject capture shim
3. Run form discovery
4. Fill email field with dummy email → dispatch change → capture Type 4
5. Optionally fill other required fields and dispatch submit to test the full flow
   - First name: Test, Last name: User
   - Password: generate dummy (e.g. Aco-Test-<timestamp>!)
   - Do NOT reuse real passwords
6. If email verification IS required: stop after field fill capture — signal is configured, end-to-end test requires manual verification
```

---

### triggers for identification (email field change)

Configure using the `target.name` or `target.tlType` confirmed from the captured Type 4:

**Option A — stable `target.name` (e.g. `"email"`):**
```json
{
  "triggerType": "valueChange",
  "triggers": [
    {
      "attributes": {
        "event.type": "change",
        "target.name": "email"
      },
      "label": "Email field changed on sign-in / registration"
    }
  ]
}
```

**Option B — `target.tlType` with URL guard in enhance (when name is generated/unstable):**
```json
{
  "triggerType": "valueChange",
  "triggers": [
    {
      "attributes": {
        "event.type": "change",
        "target.tlType": "textBox"
      },
      "label": "Text field changed on auth page"
    }
  ]
}
```
> When using Option B, the enhance function must guard on page URL to avoid firing on every text field on every page.

---

### Enhance function

Email is read directly from `help.webEvent.target.currState.value` — no DOM scanning needed. Includes URL guard (auth pages only) and deduplication (won't re-fire if email already stored in sessionStorage):

```js
// In identification enhance function:

// 1. Read email from the Type 4 valueChange event
const rawEmail = (help.webEvent?.target?.currState?.value || '').trim();

// 2. Validate format
if (!rawEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(rawEmail)) return false;

// 3. URL guard — only fire on sign-in or registration pages
const path = location.pathname.toLowerCase();
const isAuthPage = /signin|sign-in|login|log-in|register|account\/create|account\/register|secure\/account/i.test(path);
if (!isAuthPage) return false;

// 4. Deduplicate — don't re-fire if same email already captured this session
const existing = sessionStorage.getItem('aco_email_value');
if (existing === rawEmail) return false;

// 5. Store and attach
sessionStorage.setItem('aco_email_value', rawEmail);
help.store('audience', { Email: rawEmail });
signal.audience = { Email: rawEmail };
signal.loginMethod = 'email';
return signal;
```

> **Note on `target.currState.value` vs `prevState.value`:** `currState.value` is the new value after the change. `prevState.value` is what was there before. Always use `currState.value`.

---

### Forms and pages to EXCLUDE from identification

The URL guard in enhance handles most of these automatically. Explicitly exclude:

- Newsletter / marketing signup forms (footer, modal, overlay)
- Contact / enquiry forms
- Password reset forms
- Checkout guest email entry
- Search forms
- Profile update / account settings pages (email change, not authentication)

Identification fires only when the user enters their email on a genuine sign-in or registration page.
