# Acoustic Connect — initLogSignal Configuration Guide

> Maintained by Acoustic Professional Services. Include this section in every implementation review.

---

## How it works

The Acoustic Connect SDK (`acoconnect.js`) automatically observes every user interaction on the page — page loads, clicks, form changes, Ajax calls, and any custom events your code fires — and produces a structured `webEvent` object for each one.

`initLogSignal` registers itself as a listener for these webEvents via `TLT.registerBridgeCallbacks`. Every time the SDK fires a webEvent, `initLogSignal` checks whether any of your configured signals have a matching trigger. If one matches, your `enhance` function is called to build and return the signal payload, which is then sent to Acoustic Connect via `TLT.logSignal`.

```
Browser interaction happens (click, load, form change, Ajax, etc.)
        │
        ▼
Acoustic Connect SDK (acoconnect.js) captures the interaction
and produces a structured webEvent object
        │
        ▼
initLogSignal receives the webEvent via registerBridgeCallbacks
        │
        ▼
For each signal in cfg.signals:
  Does this webEvent match a trigger? ──No──▶ ignore and move on
        │ Yes
        ▼
  Call enhance(signal, help)
    - help.webEvent ← the full raw webEvent from the SDK
    - Read data from the page or the webEvent
    - Populate signal fields
    - return signal ──▶ TLT.logSignal(signal) ──▶ Acoustic Connect API
    - return null   ──▶ signal is suppressed, nothing is sent
```

You configure two things per signal: **what event fires it** (triggers) and **what data to send** (enhance).

---

## Top-level configuration (`cfg`)

```js
const cfg = {
    errorLog: true,       // Print warnings to console when required fields are missing.
                          // Set false in production to avoid noise.

    eventLog: false,      // Print every raw webEvent to console before trigger matching.
                          // Turn on temporarily when debugging why a trigger is not firing.

    signalsLog: true,     // Print every sent signal to console so you can see what was sent.

    fakeSignals: false,   // true = wrap signals as a Type 5 custom event instead of
                          // calling TLT.logSignal. No data leaves the site. Use during QA.

    messageTypes: [       // Controls which webEvent types are forwarded to initLogSignal.
        "load",           // Type 2 — page load and SPA navigation events
        "click",          // Type 4 — mouse click events
        "change",         // Type 4 — input value change events
        // "mousedown",   // Type 4 — mousedown events (rarely needed)
        // "ajaxListener",// Type 5 — XHR and fetch responses (Ajax monitoring)
        // "dlListener",  // Type 5 — data layer push events (GA/Adobe Analytics)
    ],

    GAdataLayerName: "",  // The window variable name for the data layer.
                          // Typically "dataLayer" for GA4 or "adobeDataLayer" for Adobe.
                          // Required only when using dlListener.

    GAeventsAllowList: [],// List of data layer event names to forward.
                          // e.g. ["add_to_cart", "purchase"]. Use ["all"] to capture all.
                          // Required only when using dlListener.

    signals: { /* ... */ }
};
```

---

## Understanding webEvents — what the SDK actually sends

> **Tip:** Set `eventLog: true` in `cfg` during development, open the browser console, and interact with your page. Every webEvent will be printed so you can copy real values directly into your triggers.

### Type 2 — Page load (screenview)

Fired once per page load, and on every SPA route change. Most common trigger for `pageView` signals.

```js
{
    type: 2,
    screenview: {
        type: "LOAD",               // "LOAD" on entry, "UNLOAD" when leaving
        name: "/products/shoes",    // Screenview name — usually the URL path
        originalUrl: "/products/shoes?color=red", // Raw URL path including query string
        url: "/products/shoes",     // Normalised URL (query params stripped by default)
        host: "https://www.example.com",
        referrer: "/home",          // Previous screenview name (empty on first load)
        title: "Shoes | Example Store",
        queryParams: { color: "red" }
    }
}
```

**Useful triggers:**
```js
// Fire on every page load
{ attributes: { "screenview.type": "LOAD" } }

// Fire only on a specific page
{ attributes: { "screenview.type": "LOAD", "screenview.url": "/checkout/confirmation" } }
```

**Reading values in enhance:**
```js
enhance: function (signal, help) {
    const sv = help.webEvent.screenview;
    signal.url = sv.originalUrl;
    signal.pageCategory = sv.url.split("/")[1] || "home";
    return signal;
}
```

---

### Type 4 — Click

Fired when the user clicks any element the SDK is tracking.

```js
{
    type: 4,
    event: { type: "click", tlEvent: "click" },
    target: {
        id: "add-to-cart-btn",
        idType: "HTML_ID",
        name: "addToCart",
        tlType: "button",           // SDK element classification — see table below
        type: "BUTTON",
        subType: "submit",
        attributes: {
            "class": "btn btn-primary btn-cart",
            "data-product-id": "SKU-9981",
            "data-price": "49.99",
            "innerText": "Add to Cart"  // always captured
        },
        currState: {
            value: "",
            innerText: "Add to Cart",
            href: ""
        }
    }
}
```

**`tlType` values:**

| tlType | Element |
|---|---|
| `"button"` | `<button>`, `<input type="button">` |
| `"submitButton"` | `<input type="submit">` |
| `"link"` | `<a href="...">` |
| `"textBox"` | `<input type="text">`, `<input type="email">`, `<textarea>` |
| `"password"` | `<input type="password">` |
| `"checkBox"` | `<input type="checkbox">` |
| `"radioButton"` | `<input type="radio">` |
| `"selectList"` | `<select>` |

**Useful triggers:**
```js
// Click by element id
{ attributes: { "event.type": "click", "target.id": "checkout-btn" } }

// Click by visible button text (most stable)
{ attributes: { "event.type": "click", "target.attributes.innerText": "Add to Cart" } }

// Click by CSS class (use RegExp for partial match)
{ attributes: { "event.type": "click", "target.attributes.class": /btn-add-wishlist/ } }

// Click by data attribute
{ attributes: { "event.type": "click", "target.attributes.data-action": "open-modal" } }
```

---

### Type 4 — Value change (text input, select, checkbox)

Fired when the user changes the value of a form field and moves focus away.

```js
// Text/email input change
{
    type: 4,
    event: { type: "change", tlEvent: "textChange" },
    target: {
        id: "email-input", name: "email", tlType: "textBox", subType: "email",
        attributes: { "class": "form-control", "innerText": "" },
        currState: { value: "user@example.com" }
    },
    prevState: { value: "" }
}

// Select dropdown change
{
    type: 4,
    event: { type: "change", tlEvent: "valueChange" },
    target: {
        tlType: "selectList",
        currState: { value: "US", text: "United States", index: 12 }
    },
    prevState: { value: "CA", text: "Canada", index: 3 }
}

// Checkbox change
{
    type: 4,
    event: { type: "change", tlEvent: "stateChange" },
    target: {
        tlType: "checkBox",
        currState: { value: "agreed", checked: true }
    }
}
```

**Useful triggers:**
```js
{ attributes: { "event.type": "change", "target.tlType": "textBox" } }
{ attributes: { "event.type": "change", "target.id": "promo-code" } }
{ attributes: { "event.type": "change", "target.name": "email" } }
```

**Reading values in enhance:**
```js
enhance: function (signal, help) {
    const curr = help.webEvent.target.currState;
    const newValue = curr?.value || "";          // text input new value
    const selectedOption = curr?.text || "";     // select display text
    const isChecked = curr?.checked || false;    // checkbox state
    return signal;
}
```

---

### Type 5 — Ajax listener

Fired after every XHR or fetch call the SDK intercepts. Requires `"ajaxListener"` in `messageTypes` and `addAjaxListener: true` in `initLibAdv`.

```js
{
    type: 5,
    customEvent: {
        name: "ajaxListener",
        data: {
            interfaceType: "fetch",
            requestURL: "/checkout/confirm",
            method: "POST",
            status: 200,
            ajaxResponseTime: 342,
            response: {         // only if response logging enabled in SDK config
                orderId: "ORD-20251101-0042",
                total: 98.44,
                currency: "USD",
                items: [{ sku: "SKU-9981", name: "Blue Sneakers", price: 49.99, qty: 2 }]
            }
        }
    }
}
```

**Useful triggers:**
```js
{ attributes: { "customEvent.name": "ajaxListener", "customEvent.data.requestURL": /\/checkout\/confirm/ } }
{ attributes: { "customEvent.name": "ajaxListener", "customEvent.data.status": 200, "customEvent.data.method": "POST" } }
```

---

### Type 5 — Data layer listener (dlListener)

Fired when your website pushes an event to a data layer (GA4, Adobe, custom). Requires `"dlListener"` in `messageTypes`, `GAdataLayerName`, and `GAeventsAllowList`.

```js
{
    type: 5,
    customEvent: {
        name: "dlListener",
        data: {                             // this IS the raw dataLayer push object
            event: "add_to_cart",
            ecommerce: {
                currency: "USD",
                value: 49.99,
                items: [{ item_id: "SKU-9981", item_name: "Blue Sneakers", price: 49.99, quantity: 1 }]
            }
        }
    }
}
```

> `help.dlEvent` is a shortcut for `help.webEvent.customEvent.data`.

**Trigger:**
```js
{ attributes: { "customEvent.name": "dlListener", "customEvent.data.event": "purchase" } }
```

---

### Type 5 — Custom events (formSubmit and others)

The SDK does not automatically detect form submissions. Add a `document.addEventListener("submit", ...)` listener inside `initLogSignal` that calls `TLT.logCustomEvent("formSubmit", ...)`.

**Step 1 — Add listener inside `initLogSignal`, before `cfg`:**
```js
document.addEventListener("submit", function (event) {
    const form = event.target instanceof HTMLFormElement
        ? event.target
        : event.target?.closest?.("form");
    if (!form) return;

    const formName =
        form.querySelector('input[name="form_name"]')?.value ||
        form.getAttribute("name") || form.id || "unknown_form";

    const email =
        form.querySelector('input[type="email"]')?.value?.trim() ||
        form.querySelector('input[name*="email" i]')?.value?.trim() || "";

    if (formName === "unknown_form") return;
    TLT.logCustomEvent("formSubmit", { formName, email });
}, true); // true = capture phase — fires before page navigates away
```

**Step 2 — Add to `messageTypes`:**
```js
messageTypes: ["load", "click", "change", "formSubmit"]
```

---

## Signal configuration reference

```js
cfg.signals = {
    mySignalName: {
        // 1. signal — template for what gets sent
        signal: {
            signalType: "mySignalName",     // must match Connect signal type exactly
            // signal-specific fields...
            effect: "positive",             // required: "positive" or "negative"
            audience: {},                   // identity: { "Email": "..." }
            signalCustomAttributes: []
        },

        // 2. triggers — which webEvents activate this signal
        // Multiple triggers = OR logic. Multiple attributes = AND logic.
        triggers: [
            {
                attributes: {
                    "screenview.type": "LOAD",
                    "customEvent.data.requestURL": /\/checkout/  // RegExp supported
                },
                label: "optional name — available as help.label in enhance",
                delay: 0    // ms to wait before calling enhance
            }
        ],

        // 3. enhance — populate signal fields; return signal to send, null to suppress
        enhance: function (signal, help) {
            return signal;
        }
    }
};
```

---

## `help` utility reference

| Function / property | Description | Example |
|---|---|---|
| `help.webEvent` | Full raw webEvent from the SDK | `help.webEvent.target.id` |
| `help.dlEvent` | Raw dataLayer push object (dlListener only) | `help.dlEvent.ecommerce.items[0]` |
| `help.label` | Matched trigger label | `"Add to Wishlist"` |
| `help.cssGet(sel, attr, flag?, root?)` | Read a DOM value | See below |
| `help.getQueryParam(str, param, flag?)` | Parse a URL or query string | `help.getQueryParam(location.href, "q")` |
| `help.stripHtml(html)` | Remove HTML tags | `help.stripHtml("<b>Hi</b>") → "Hi"` |
| `help.store(key, value)` | Save to sessionStorage | `help.store("userEmail", "a@b.com")` |
| `help.retrieve(key)` | Read from sessionStorage | `help.retrieve("userEmail")` |
| `help.validateEmailFormat(str)` | Returns true if valid email | `help.validateEmailFormat("a@b.com")` |

**`help.cssGet` examples:**
```js
help.cssGet('h1.product-title', 'innerText')           // element text
help.cssGet('#quantity', 'value')                       // input value
help.cssGet('meta[name="product-id"]', 'content')      // meta tag attribute
help.cssGet('[data-sku]', 'dataset.sku')               // data-* attribute
help.cssGet('.price', 'innerText', 'n')                // number: "$49.99" → 49.99
help.cssGet('.price', 'innerText', 'ne')               // European: "49,99 €" → 49.99
```

---

## Signals by subscription tier

**Every signal is available on every tier — Connect Pro, Premium, and Ultimate are identical in signal scope:** add-to-cart, remove-from-cart, order, identification, error, page view, product view, product configuration, on-site search, and rich media interaction.

Whether a signal is configured for a given site depends on that site's functionality, never on the subscription tier.

---

## Worked examples

### 1. Page view — fire on every page load
```js
pageView: {
    signal: { signalType: "pageView", url: null, pageCategory: null, effect: "positive", audience: {} },
    triggers: [{ attributes: { "screenview.type": "LOAD" } }],
    enhance: function (signal, help) {
        signal.url = location.href.split("?")[0];
        signal.pageCategory = location.pathname.split("/")[1] || "home";
        signal.audience = { "Email": help.retrieve("userEmail") || "" };
        return signal;
    }
}
```

### 2. Capture email on field change (store only — no signal sent)
```js
identification: {
    signal: { signalType: "identification" },
    triggers: [{ attributes: { "event.type": "change", "target.tlType": "textBox" } }],
    enhance: function (signal, help) {
        const value = help.webEvent.target.currState?.value || "";
        if (help.validateEmailFormat(value)) { help.store("userEmail", value); }
        return null; // suppress — storage only
    }
}
```

### 3. Add to cart by button text
```js
addToCart: {
    signal: { signalType: "addToCart", productId: null, productName: null,
              itemQuantity: null, unitPrice: null, currency: "USD", effect: "positive", audience: {} },
    triggers: [{ attributes: { "event.type": "click", "target.attributes.innerText": "Add to Cart" } }],
    enhance: function (signal, help) {
        signal.productId   = help.cssGet('[data-product-id]', 'dataset.productId') || "";
        signal.productName = help.cssGet('h1.product-title', 'innerText') || "";
        signal.itemQuantity = help.cssGet('#quantity', 'value', 'n') || 1;
        signal.unitPrice   = help.cssGet('[data-price]', 'dataset.price', 'n') || 0;
        signal.audience    = { "Email": help.retrieve("userEmail") || "" };
        return signal;
    }
}
```

### 4. Multiple triggers with label (rich media play/pause/stop)
```js
triggers: [
    { attributes: { "event.type": "click", "target.id": "video-play" },  label: "play" },
    { attributes: { "event.type": "click", "target.id": "video-pause" }, label: "pause" },
    { attributes: { "event.type": "click", "target.id": "video-stop" },  label: "stop" }
],
enhance: function (signal, help) {
    signal.interactionType = help.label; // "play", "pause", or "stop"
    return signal;
}
```

### 5. Product configuration — dropdown change
```js
triggers: [
    { attributes: { "event.type": "change", "target.id": "size-select" },   label: "Size" },
    { attributes: { "event.type": "change", "target.id": "colour-select" }, label: "Colour" }
],
enhance: function (signal, help) {
    const curr = help.webEvent.target.currState;
    signal.configurationType = help.label + ": " + (curr?.text || curr?.value || "");
    return signal;
}
```

### 6. Ajax — order signal from checkout API response
```js
triggers: [{
    attributes: {
        "customEvent.name": "ajaxListener",
        "customEvent.data.requestURL": /\/api\/checkout\/confirm/,
        "customEvent.data.status": 200
    }
}],
enhance: function (signal, help) {
    const data = help.webEvent.customEvent.data.response || {};
    signal.orderId    = data.orderId || "";
    signal.orderValue = data.total || 0;
    signal.currency   = data.currency || "USD";
    signal.orderedItems = (data.items || []).map(function (item) {
        return { productId: item.sku, productName: item.name, unitPrice: item.price, itemQuantity: item.qty };
    });
    return signal;
}
```

### 7. DataLayer — GA4 purchase event
```js
// cfg: messageTypes includes "dlListener", GAdataLayerName: "dataLayer", GAeventsAllowList: ["purchase"]
triggers: [{ attributes: { "customEvent.name": "dlListener", "customEvent.data.event": "purchase" } }],
enhance: function (signal, help) {
    const ecom = help.dlEvent.ecommerce || {};
    signal.orderId    = ecom.transaction_id || "";
    signal.orderValue = ecom.value || 0;
    signal.currency   = ecom.currency || "USD";
    signal.orderedItems = (ecom.items || []).map(function (item) {
        return { productId: item.item_id, productName: item.item_name, unitPrice: item.price, itemQuantity: item.quantity };
    });
    return signal;
}
```

---

## Consent

Include a `consent` object on any signal that records channel opt-in:

```js
signal.consent = {
    enableOverrideExistingOptOut: false,
    email: [{ status: "OPT_IN", consentGroupIds: ["72d01db0-..."] }]
    // Also available: "sms", "whatsapp"
};
```

---

## Regex matching in triggers

Any trigger attribute value can be a `RegExp` instead of a string:

```js
{ "customEvent.data.requestURL": /\/api\/cart/ }        // URL contains this pattern
{ "screenview.url": /\/(checkout|basket|cart)/ }        // any of these pages
{ "target.attributes.class": /btn-primary/ }            // class contains this string
```

---

## Debugging

| Symptom | What to check |
|---|---|
| No signals appear in console | Is `signalsLog: true`? Is the signal type in `cfg.signals`? |
| A trigger is not firing | Set `eventLog: true`. Find the webEvent. Check exact attribute path and value. |
| Trigger fires but signal not sent | `enhance` is returning `null`/`false`. Add `console.log` at start of enhance. Check required fields are non-empty. |
| Signal in console but not in Connect | Check `fakeSignals: false`. Verify `appKey`. Check Network tab for collector POST. |
| Audience / email is empty | Identification must fire before this signal. Check `help.retrieve("userEmail")`. |
| Ajax trigger never matches | Confirm `addAjaxListener: true` in `initLibAdv` and `"ajaxListener"` in `messageTypes`. Use `eventLog: true`. |
| `response` is undefined in ajax enhance | Response body logging must be enabled: `log.responseData: true` in SDK ajaxListener config. |
