#!/usr/bin/env python3
"""
Generate a configured Acoustic SDK package for a customer.

Outputs per run:
  acoConnectSdkConfig-<domain-slug>.js                    — SDK bundle (paste into DevTools or GTM)
  acoConnectSdkConfig-<domain-slug>.tamperMonkeyConfig.js — lightweight Tampermonkey @require script
  <customer-slug>-customer-signal-config.json
  <customer-slug>-implementation-review.md

Domain slug is derived from productionDomain (e.g. www2.acmeretail.com → acmeretail).
The .user.js file @require-loads the bundle from a local file:// URL so the tester
only needs to swap the .js file between rounds — no script reinstall needed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from textwrap import indent, dedent
from typing import Any

from validate_profile import load_json, validate

BASE_INIT_LOG_SIGNAL_URL = (
    "https://content-eu-1.content-cms.com/7fbff3c6-1b3b-4a7d-a64e-c8ebc38fa3df"
    "/dxdam/35/35cc26b5-a0ec-4e55-8c8e-a42b40cc54e1/initLogSignal.js"
)
# initLogSignal.js is fetched automatically from BASE_INIT_LOG_SIGNAL_URL on every
# run when --base-js is not supplied. Pass --base-js only if the CDN is unreachable
# from the current Python environment (e.g. a sandboxed shell). No persistent copy
# is stored in assets/.
ASSETS_DIR = Path(__file__).parent.parent / "assets"
SDK_TEMPLATE_PATH = ASSETS_DIR / "sdk-template.js"
SDK_INSERT_MARKER = "// InitLogsignsal here - do not remove this comment"

# Maps profile signal keys → cfg.signals key in the base initLogSignal.js
SIGNAL_KEY_MAP: dict[str, str] = {
    "pageView": "pageView",
    "productView": "productView",
    "productConfiguration": "productConfiguration",
    "addToCart": "addToCart",
    "order": "order",
    "onSiteSearch": "onSiteSearch",
    "identification": "loggedIn",
    "richMediaInteraction": "richMediaInteraction",
    "formSubmit": "formSubmit",
}


# ---------------------------------------------------------------------------
# Base JS loading + helper injection
# ---------------------------------------------------------------------------

# Source for the jsonLdGet helper — injected into the CDN initLogSignal at load time.
# Handles both single-nested [{...}] and double-nested [[{...}]] JSON-LD structures
# by flattening one level before path traversal, so '0.name' works for both.
_JSONLD_GET_SRC = """\
    function jsonLdGet(path, scope) {
        var root = scope || document;
        var scripts = root.querySelectorAll('script[type="application/ld+json"]');
        var data = [];
        for (var s = 0; s < scripts.length; s++) {
            try {
                var parsed = JSON.parse(scripts[s].textContent);
                if (Array.isArray(parsed)) {
                    for (var a = 0; a < parsed.length; a++) {
                        if (Array.isArray(parsed[a])) {
                            for (var b = 0; b < parsed[a].length; b++) {
                                data.push(parsed[a][b]);
                            }
                        } else {
                            data.push(parsed[a]);
                        }
                    }
                } else {
                    data.push(parsed);
                }
            } catch (e) {}
        }
        if (!path) return data;
        var parts = path.split(".");
        var result = data;
        for (var p = 0; p < parts.length; p++) {
            if (result === null || result === undefined) return null;
            var key = isNaN(parts[p]) ? parts[p] : parseInt(parts[p], 10);
            result = result[key];
        }
        return (result !== undefined && result !== null) ? result : null;
    }
"""


def _inject_helpers(js: str) -> str:
    """Inject jsonLdGet into the CDN JS and wire it into the help object."""
    # 1. Insert jsonLdGet function immediately before logEnhanced
    marker = "function logEnhanced("
    if marker in js:
        js = js.replace(marker, _JSONLD_GET_SRC + "\n    " + marker, 1)
    else:
        print("[ACO] WARNING: logEnhanced not found — jsonLdGet not injected", file=sys.stderr)

    # 2. Add jsonLdGet to the help object (after cssGet: cssGet,)
    help_anchor = "cssGet: cssGet,"
    if help_anchor in js:
        js = js.replace(
            help_anchor,
            "cssGet: cssGet,\n                jsonLdGet: jsonLdGet,",
            1,
        )
    else:
        print("[ACO] WARNING: cssGet not found in help object — jsonLdGet not wired", file=sys.stderr)

    return js


def fetch_base_from_cdn() -> str:
    """Fetch initLogSignal.js directly from CDN. Called when --base-js is omitted."""
    print(f"[ACO] --base-js not supplied; fetching from CDN: {BASE_INIT_LOG_SIGNAL_URL}", file=sys.stderr)
    try:
        req = urllib.request.Request(
            BASE_INIT_LOG_SIGNAL_URL,
            headers={"User-Agent": "AcousticSDKGenerator/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            js = resp.read().decode("utf-8")
        if "function initLogSignal" not in js:
            raise ValueError("CDN response does not contain initLogSignal — check the URL.")
        print(f"[ACO] Fetched initLogSignal.js from CDN ({len(js):,} chars)", file=sys.stderr)
        return js
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Could not fetch initLogSignal.js from CDN ({exc}).\n"
            "Fetch it manually and pass it via --base-js /path/to/initLogSignal.js"
        ) from exc


_LOCAL_BASE_JS = ASSETS_DIR / "initLogSignal.js"


def load_base(base_js_path: "Path | None") -> str:
    """Load initLogSignal.js — from disk if path given, otherwise fetched from CDN.

    Lookup order:
      1. --base-js argument (explicit path)
      2. assets/initLogSignal.js (local cache, avoids CDN in restricted envs)
      3. CDN fetch
    """
    if base_js_path is None:
        if _LOCAL_BASE_JS.exists():
            js = _LOCAL_BASE_JS.read_text(encoding="utf-8")
            print(f"[ACO] Loaded base JS from local cache {_LOCAL_BASE_JS} ({len(js):,} chars)", file=sys.stderr)
            return js
        js = fetch_base_from_cdn()
    else:
        js = base_js_path.read_text(encoding="utf-8")
        print(f"[ACO] Loaded base JS from {base_js_path} ({len(js):,} chars)", file=sys.stderr)
    js = _inject_helpers(js)
    return js


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "customer"


def domain_slug(domain: str) -> str:
    """Extract a short slug from a production domain for use in bundle filenames.

    Examples:
      www2.acmeretail.com   → acmeretail
      www.northwindtrading.co.uk → northwindtrading
      www.shopoutlet.co.uk  → shopoutlet
    """
    d = domain.lower().strip()
    # Strip leading www / www2 / www3 etc.
    d = re.sub(r"^www\d*\.", "", d)
    # Take only the first label (before the first dot)
    d = d.split(".")[0]
    # Sanitise to alphanumeric only
    return re.sub(r"[^a-z0-9]", "", d) or "customer"


# ---------------------------------------------------------------------------
# Enhance function code generation
# ---------------------------------------------------------------------------

def _source_expr(source: dict[str, Any]) -> str | None:
    t = source.get("source", "")
    path = str(source.get("path", ""))
    sel = str(source.get("selector", ""))
    attr = str(source.get("attr", source.get("attribute", "content")))
    key = str(source.get("key", path))
    val = source.get("value", "")
    if t == "jsonLd":         return f"help.jsonLdGet({path!r})"
    if t == "dataLayer":      return f"help.dlGet({path!r})"
    if t == "webEvent":       return f"help.webEvent?.customEvent?.data?.{path}"
    if t == "type2":
        # Type 2 screenview — path relative to webEvent.screenview (e.g. "screenview.url")
        sub = path.replace("screenview.", "")
        return f"help.webEvent?.screenview?.{sub} || location.pathname + location.search"
    if t == "type4":
        # Type 4 interaction — path relative to webEvent.target (e.g. "target.currState.value")
        sub = path.replace("target.", "")
        return f"help.webEvent?.target?.{sub} || null"
    if t == "domText":        return f"help.cssGet({sel!r}, 'innerText')"
    if t == "domAttr":        return f"help.cssGet({sel!r}, {attr!r})"
    if t == "meta":
        s = sel or path
        return f"(document.querySelector('meta[property=\"{s}\"],meta[name=\"{s}\"]')||{{}}).content||null"
    if t == "url":            return f"(new URLSearchParams(location.search)).get({key!r})"
    if t == "urlSlug":        return "location.pathname.split('/').filter(Boolean).pop()||null"
    if t == "sessionStorage": return f"sessionStorage.getItem({key!r})"
    if t == "localStorage":   return f"localStorage.getItem({key!r})"
    if t == "fallback":       return repr(str(val))
    return None


def _field_lines(field_specs: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for field, spec in field_specs.items():
        # Support both flat {"source":…} and wrapped {"sources":[…]} profile formats
        raw_sources = spec.get("sources")
        if not raw_sources and spec.get("source"):
            raw_sources = [spec]  # treat flat dict as single-source
        exprs = [e for s in (raw_sources or []) if (e := _source_expr(s))]
        if not exprs:
            lines.append(f"    // TODO: map signal.{field}")
            continue
        chain = " || ".join(exprs)
        transform = spec.get("transform", "")
        if transform == "number":
            chain = f"parseFloat(String({chain}).replace(/[^0-9.-]/g,''))||null"
        elif transform == "array":
            chain = f"[].concat({chain}).filter(Boolean)"
        lines.append(f"    signal.{field} = {chain};")
        if spec.get("required"):
            lines.append(f"    if (signal.{field}==null) return false; // required")
    return lines


def _enhance_from_fields(fields: dict[str, Any]) -> str:
    lines = _field_lines(fields)
    if not lines:
        return "    // TODO: add extraction logic\n    return false;"
    lines += [
        "    signal.audience = help.retrieve('audience') || {};",
        "    return signal;",
    ]
    return "\n".join(lines)


def _ecommerce_items_js(signal_name: str, schema: str, custom_path: str) -> tuple[str, str]:
    """
    Returns (items_js_expr, action_field_js_expr) for the given signal and schema.
    items_js_expr  : JS expression resolving to an array of product items from `ec`
    action_field_js: JS expression resolving to the order actionField object from `ec`

    GA4  : ecommerce.items[]
    UA   : ecommerce.detail.products[] / ecommerce.add.products[] / ecommerce.purchase.products[]
           + ecommerce.purchase.actionField for order
    custom: ecommerce.<custom_path>[]
    auto : tries GA4 then UA paths — use when schema not yet confirmed
    """
    if schema == "ga4":
        items = "ec?.items || []"
        action = "{ id: ec?.transaction_id, revenue: ec?.value, currency: ec?.currency }"
    elif schema == "ua":
        if signal_name == "productView":
            items = "ec?.detail?.products || ec?.impressions || ec?.items || []"
        elif signal_name == "addToCart":
            items = "ec?.add?.products || ec?.items || []"
        elif signal_name == "order":
            items = "ec?.purchase?.products || ec?.items || []"
        else:
            items = "ec?.items || []"
        action = "ec?.purchase?.actionField || ec?.checkout?.actionField || {}"
    elif schema == "custom" and custom_path:
        # Traverse the custom dot-path from ec
        accessor = "ec"
        for part in custom_path.split("."):
            accessor = f"{accessor}?.['{part}']" if not part.isidentifier() else f"{accessor}?.{part}"
        items = f"{accessor} || ec?.items || []"
        action = "ec?.purchase?.actionField || {}"
    else:
        # "auto" — try GA4 first, fall back to UA (safe for unknown schemas)
        if signal_name == "productView":
            items = "ec?.items || ec?.detail?.products || ec?.impressions || []"
        elif signal_name == "addToCart":
            items = "ec?.items || ec?.add?.products || []"
        elif signal_name == "order":
            items = "ec?.items || ec?.purchase?.products || []"
        else:
            items = "ec?.items || []"
        action = "ec?.purchase?.actionField || { id: ec?.transaction_id, revenue: ec?.value }"
    return items, action


def _enhance_from_web_event(signal_name: str, fields: dict[str, Any], profile: dict[str, Any]) -> str:
    """
    Generate an enhance function that reads from help.webEvent (dataLayer push).
    Handles GA4 (ecommerce.items[]) and UA Enhanced Ecommerce
    (ecommerce.detail/add/purchase.products[]) structures, plus custom paths.
    Field names are tried with both GA4 (item_id, item_name) and UA (id, name) conventions.
    Falls back to DOM selectors when webEvent data is absent.
    """
    email_capture = profile.get("settings", {}).get("emailCapture", "disabled")
    inspection = profile.get("inspection", {})
    schema = inspection.get("ecommerceSchema") or "auto"
    custom_path = inspection.get("ecommerceItemsPath", "")
    lines: list[str] = []

    if email_capture != "disabled":
        lines += [
            "    const _email = sessionStorage.getItem('aco_email_value');",
            "    if (_email && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(_email)) {",
            "        help.store('audience', { Email: _email });",
            "        signal.audience = { Email: _email };",
            "    }",
        ]

    if signal_name in ("addToCart", "productView", "productConfiguration", "order"):
        items_expr, action_expr = _ecommerce_items_js(signal_name, schema, custom_path)
        lines += [
            "    const ec = help.webEvent?.customEvent?.data?.ecommerce;",
            f"    const items = {items_expr};",
            "    const item = items[0] || {};",
            f"    const actionField = {action_expr};",
            "    // Field names: GA4 uses item_id/item_name, UA uses id/name — try both",
        ]
        field_lines = _field_lines(fields) if fields else []
        if field_lines:
            lines += field_lines
        else:
            # Sensible defaults per signal — dual field name convention (GA4 || UA)
            if signal_name == "addToCart":
                lines += [
                    "    signal.productId = item?.item_id || item?.id || help.cssGet('[data-product-id]','dataset.productId') || null;",
                    "    if (!signal.productId) return false; // required",
                    "    signal.productName = item?.item_name || item?.name || help.cssGet(\"meta[property='og:title']\", 'content') || null;",
                    "    signal.unitPrice = typeof item?.price === 'number' ? item.price : parseFloat(item?.price) || null;",
                    "    signal.itemQuantity = item?.quantity || 1;",
                    "    signal.currency = ec?.currency || null;",
                    "    signal.productCategory = item?.item_category || item?.category || null;",
                    "    signal.brandName = item?.item_brand || item?.brand || null;",
                    "    signal.productUrls = [help.cssGet(\"meta[property='og:url']\", 'content') || window.location.href];",
                    "    signal.imageUrls = [help.cssGet(\"meta[property='og:image']\", 'content') || null].filter(Boolean);",
                ]
            elif signal_name == "productView":
                lines += [
                    "    signal.productId = item?.item_id || item?.id || help.cssGet('[data-product-id]','dataset.productId') || null;",
                    "    if (!signal.productId) return false; // required",
                    "    signal.productName = item?.item_name || item?.name || help.jsonLdGet('0.name') || help.cssGet(\"meta[property='og:title']\", 'content') || null;",
                    "    signal.unitPrice = typeof item?.price === 'number' ? item.price : parseFloat(item?.price) || parseFloat(help.jsonLdGet('0.offers.0.price')) || null;",
                    "    signal.currency = ec?.currency || help.jsonLdGet('0.offers.0.priceCurrency') || null;",
                    "    signal.productCategory = item?.item_category || item?.category || null;",
                    "    signal.brandName = item?.item_brand || item?.brand || help.jsonLdGet('0.brand.name') || null;",
                    "    signal.sku = item?.item_variant || item?.sku || help.jsonLdGet('0.sku') || null;",
                    "    signal.productUrls = [help.cssGet(\"meta[property='og:url']\", 'content') || window.location.href];",
                    "    signal.imageUrls = [help.cssGet(\"meta[property='og:image']\", 'content') || null].filter(Boolean);",
                ]
            elif signal_name == "productConfiguration":
                lines += [
                    "    signal.productId = item?.item_id || item?.id || null;",
                    "    if (!signal.productId) return false; // required",
                    "    signal.productName = item?.item_name || item?.name || help.cssGet(\"meta[property='og:title']\", 'content') || null;",
                    "    signal.unitPrice = typeof item?.price === 'number' ? item.price : parseFloat(item?.price) || null;",
                    "    signal.currency = ec?.currencyCode || ec?.currency || null;",
                    "    signal.productCategory = item?.item_category || item?.category || null;",
                    "    signal.productUrls = [window.location.href];",
                    "    // TODO: set signal.configurationType ('colour'|'size'|'quantity') from the triggering interaction",
                ]
            elif signal_name == "order":
                lines += [
                    "    signal.orderId = actionField?.id || ec?.transaction_id || null;",
                    "    if (!signal.orderId) return false; // required",
                    "    signal.orderValue = typeof actionField?.revenue === 'number' ? actionField.revenue",
                    "        : parseFloat(actionField?.revenue) || ec?.value || null;",
                    "    signal.orderTax = typeof actionField?.tax === 'number' ? actionField.tax : parseFloat(actionField?.tax) || null;",
                    "    signal.orderShippingHandling = typeof actionField?.shipping === 'number' ? actionField.shipping : parseFloat(actionField?.shipping) || null;",
                    "    signal.currency = ec?.currency || null;",
                    "    signal.orderedItems = items.map(function(it) { return {",
                    "        productId: it?.item_id || it?.id || null,",
                    "        productName: it?.item_name || it?.name || null,",
                    "        unitPrice: typeof it?.price === 'number' ? it.price : parseFloat(it?.price) || null,",
                    "        itemQuantity: it?.quantity || 1,",
                    "        productCategory: it?.item_category || it?.category || null,",
                    "    }; });",
                    "    if (!signal.orderedItems.length) return false; // required",
                ]
    elif signal_name == "identification":
        lines += [
            "    const dlData = help.webEvent?.customEvent?.data;",
            "    const dlEmail = dlData?.email || dlData?.user_email || dlData?.userEmail || null;",
            "    const loginMethod = dlData?.method || dlData?.loginMethod || 'email';",
            "    if (dlEmail && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(dlEmail)) {",
            "        sessionStorage.setItem('aco_email_value', dlEmail);",
            "        help.store('audience', { Email: dlEmail });",
            "        signal.audience = { Email: dlEmail };",
            "        signal.loginMethod = loginMethod;",
            "    } else {",
            "        // Fallback: read email from any visible form field on the page",
            "        const emailEl = document.querySelector('input[type=\"email\"], input[name=\"email\"]');",
            "        const formEmail = emailEl?.value?.trim() || null;",
            "        if (!formEmail || !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(formEmail)) return false;",
            "        sessionStorage.setItem('aco_email_value', formEmail);",
            "        help.store('audience', { Email: formEmail });",
            "        signal.audience = { Email: formEmail };",
            "        signal.loginMethod = loginMethod;",
            "    }",
        ]
    elif signal_name == "onSiteSearch":
        search_param = profile.get("settings", {}).get("searchParameter", "q")
        lines += [
            "    // Read from dlListener data first; fall back to URL search param",
            "    const dlData = help.webEvent?.customEvent?.data || {};",
            "    // Try common field name patterns across different dataLayer implementations",
            "    const dlSearchTerm = dlData?.search_keyword || dlData?.searchTerm",
            "        || dlData?.query || dlData?.search_term || dlData?.term || null;",
            f"    signal.searchTerm = dlSearchTerm || (new URLSearchParams(location.search)).get({search_param!r}) || null;",
            "    if (!signal.searchTerm) return false; // required — only fires on search result pages",
            "    const dlCount = dlData?.total_number_of_items ?? dlData?.numberOfResults",
            "        ?? dlData?.resultCount ?? dlData?.total_results ?? null;",
            "    signal.numberOfResults = dlCount !== null ? Number(dlCount) : null;",
            "    signal.effect = signal.numberOfResults === 0 ? 'negative' : 'positive';",
        ]
    else:
        lines += _field_lines(fields)

    lines += [
        "    signal.audience = help.retrieve('audience') || {};",
        "    return signal;",
    ]
    return "\n".join(lines)


def _enhance_from_click(signal_name: str, click_info: dict[str, Any], fields: dict[str, Any]) -> str:
    """
    Generate an enhance function for a click-triggered signal (type 4 fallback).
    click_info comes from the console type 4 output the user pastes back.
    """
    lines: list[str] = []
    if click_info:
        target_sel = click_info.get("targetSelector", "")
        if target_sel:
            lines.append(f"    const target = document.querySelector({target_sel!r});")
            lines.append("    if (!target) return false;")
    field_lines = _field_lines(fields)
    lines += field_lines if field_lines else ["    // TODO: extract signal fields from DOM"]
    lines += [
        "    signal.audience = help.retrieve('audience') || {};",
        "    return signal;",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Patch helpers — rewrite one cfg.signals[key] block
# ---------------------------------------------------------------------------

def _make_on_events_js(on_events: list[dict[str, Any]]) -> str:
    if not on_events:
        return "[]"
    parts = []
    for ev in on_events:
        attrs = ev.get("attributes", {})
        attr_js = json.dumps(attrs, indent=16, ensure_ascii=False)
        parts.append(f"{{\n                attributes: {attr_js}\n            }}")
    return "[\n            " + ",\n            ".join(parts) + "\n        ]"


def _patch_signal_block(js: str, cfg_key: str, on_events: list, enhance_body: str) -> str:
    """
    Find the cfg.signals[cfg_key] block and replace its triggers + enhance.
    Uses a simple stack-based bracket finder to avoid multi-signal regex bleed.
    """
    # Locate the signal key
    key_pat = re.compile(rf"\b{re.escape(cfg_key)}:\s*\{{")
    m = key_pat.search(js)
    if not m:
        print(f"[ACO] WARNING: signal key {cfg_key!r} not found in base JS", file=sys.stderr)
        return js

    # Walk forward to find the matching closing brace
    start = m.start()
    brace_pos = m.end() - 1  # position of opening {
    depth = 1
    i = m.end()
    while i < len(js) and depth > 0:
        if js[i] == "{":
            depth += 1
        elif js[i] == "}":
            depth -= 1
        i += 1
    block_end = i  # exclusive

    block = js[start:block_end]

    # Patch triggers (replace triggers: [...] or onEvents: [...] — both map to triggers in msgHandler)
    on_events_str = _make_on_events_js(on_events)
    if re.search(r"\btriggers\s*:", block):
        block = re.sub(r"\btriggers\s*:\s*\[.*?\]", f"triggers: {on_events_str}", block, count=1, flags=re.DOTALL)
    elif re.search(r"\bonEvents\s*:", block):
        # Legacy profile key — rewrite to triggers so msgHandler picks it up
        block = re.sub(r"\bonEvents\s*:\s*\[.*?\]", f"triggers: {on_events_str}", block, count=1, flags=re.DOTALL)
    else:
        # Insert after the signal:{} block
        block = re.sub(r"(\},\s*\n)(\s*//)", rf"\1            triggers: {on_events_str},\n\2", block, count=1)

    # Patch enhance body.
    # Must handle inline `enhance: function(signal, help) {}` separately: the inline `}` is NOT
    # preceded by `\n`, so a naive (.*?)(\n\s*\}) skips over it and consumes the *signal block's*
    # closing `}` as the function end — stripping the block's `}` and corrupting the JS.
    indented_body = "\n" + enhance_body + "\n                "
    inline_pat = re.compile(r"(enhance:\s*function\s*\(signal,\s*help\)\s*\{)\s*\}")
    em = inline_pat.search(block)
    if em:
        block = block[:em.start()] + em.group(1) + indented_body + "}" + block[em.end():]
    else:
        enhance_pat = re.compile(r"(enhance:\s*function\s*\(signal,\s*help\)\s*\{)(.*?)(\n\s*\})", re.DOTALL)
        em = enhance_pat.search(block)
        if em:
            block = block[:em.start()] + em.group(1) + indented_body + em.group(3) + block[em.end():]
        else:
            print(f"[ACO] WARNING: enhance function not found for {cfg_key!r}", file=sys.stderr)

    return js[:start] + block + js[block_end:]


# ---------------------------------------------------------------------------
# Main cfg configuration
# ---------------------------------------------------------------------------


def _inject_audience_signal(js: str, profile: dict[str, Any]) -> str:
    """
    Inject the audience email-capture utility signal into cfg.signals.

    This signal fires on the same change event as the email field, captures
    the typed value, and stores it via help.store("audience", {Email: ...}).
    It always returns false — it is NOT an Acoustic Connect signal.

    Injected automatically whenever identification is enabled. Uses the most
    specific selector available: target.id if an id was confirmed, else target.name.
    """
    identification = profile.get("signals", {}).get("identification", {})
    if not identification.get("enabled"):
        return js

    selector = identification.get("selector", "")
    page_url  = identification.get("pageUrl", "/log-in/")
    reg_url   = profile.get("signals", {}).get("formSubmit", {}).get("pageUrl", "/consumer-registration/")

    # Determine trigger attribute — prefer id (more specific), fall back to name
    id_m   = re.search(r"""input#(\w+)""", selector)
    name_m = re.search(r"""name=['"](\w+)['"]""", selector)
    if id_m:
        trig_key, trig_val = "target.id",   id_m.group(1)
    elif name_m:
        trig_key, trig_val = "target.name", name_m.group(1)
    else:
        print("[ACO] WARNING: identification selector unclear — audience signal not injected", file=sys.stderr)
        return js

    audience_block = (
        "\n"
        "            // ---------------------------------------------------------------\n"
        "            // Audience utility signal — injected automatically when identification\n"
        "            // is configured. NOT an Acoustic Connect signal (always returns false).\n"
        "            // Captures the email address typed into the identified form field and\n"
        "            // stores it in sessionStorage. Other signals read from sessionStorage\n"
        "            // to populate their audience object (help.retrieve(\'audience\') || {}).\n"
        "            // ---------------------------------------------------------------\n"
        f"            audience: {{\n"
        f"                signal: {{ signalType: \"audience\" }},\n"
        f"                triggers: [{{ attributes: {{ \"event.type\": \"change\", \"{trig_key}\": \"{trig_val}\" }} }}],\n"
        f"                enhance: function (signal, help) {{\n"
        f"                    const _guardPaths = [{page_url!r}, {reg_url!r}];\n"
        f"                    if (!_guardPaths.some(function(p) {{ return location.pathname === p; }})) return false;\n"
        f"                    const rawEmail = help.webEvent?.target?.currState?.value || null;\n"
        f"                    if (!rawEmail || !help.validateEmailFormat(rawEmail)) return false;\n"
        f"                    // Always overwrite — keep sessionStorage current with latest typed value.\n"
        f"                    sessionStorage.setItem(\'aco_email_value\', rawEmail);\n"
        f"                    help.store(\'audience\', {{ Email: rawEmail }});\n"
        f"                    return false; // utility only — never logs to Acoustic Connect\n"
        f"                }}\n"
        f"            }}"
    )

    # Injection point: before the `        }` that closes cfg.signals,
    # identified by the pattern `            }\n        }\n    };`
    # (last signal block close, signals close, cfg close)
    close_pattern = "\n        }\n    };"
    idx = js.rfind(close_pattern)
    if idx == -1:
        print("[ACO] WARNING: could not find cfg.signals close — audience signal not injected", file=sys.stderr)
        return js

    return js[:idx] + audience_block + js[idx:]


def _update_privacy_targets(js: str, profile: dict[str, Any]) -> str:
    """
    Add the identified email field selectors to config.services.message.privacy targets.

    When identification is configured, the specific email field selectors
    (e.g. input#Email, [name='Email']) are added to the exclude:true/maskType:2
    privacy rule so the field is captured without masking.
    """
    identification = profile.get("signals", {}).get("identification", {})
    if not identification.get("enabled"):
        return js

    selector = identification.get("selector", "")
    id_m   = re.search(r"""input#(\w+)""", selector)
    name_m = re.search(r"""name=['"](\w+)['"]""", selector)

    new_targets: list[str] = []
    if id_m:
        new_targets.append(f'"#{id_m.group(1)}"')
    if name_m:
        new_targets.append(f'"[name=\\"{name_m.group(1)}\\"]"')

    if not new_targets:
        return js

    # Find the privacy targets closing line and insert before the regex-id entry
    # Pattern: `{ id: { regex: 'goAcoustic-com' }, idType: -2 }`
    marker = "{ id: { regex: 'goAcoustic-com' }, idType: -2 }"
    if marker not in js:
        return js

    extra = "".join(f"\n                {t}," for t in new_targets)
    comment = "\n                // Identified email field — captured without masking (identification signal):"
    return js.replace(marker, comment + extra + "\n                " + marker, 1)


def configure_init_log_signal(base_js: str, profile: dict[str, Any]) -> str:
    settings = profile.get("settings", {})
    customer = profile.get("customer", {})
    signals_cfg = profile.get("signals", {})
    inspection = profile.get("inspection", {})

    mode = settings.get("mode", "test")
    dl_name = customer.get("dataLayerName", "")
    dl_available = inspection.get("dataLayerAvailable", False)
    dl_events = inspection.get("dataLayerEvents", [])

    js = base_js

    # --- Top-level cfg flags ---
    is_test = mode == "test"
    js = re.sub(r"(fakeSignals\s*:\s*)(true|false)", rf"\g<1>{'true' if is_test else 'false'}", js)
    # Always enable logging in test mode so console output is visible
    js = re.sub(r"(eventLog\s*:\s*)(true|false)", rf"\g<1>{'true' if is_test else 'false'}", js)
    js = re.sub(r"(signalsLog\s*:\s*)(true|false)", r"\g<1>true", js)

    # --- GAdataLayerName ---
    effective_dl = dl_name if (dl_available and dl_name) else ""
    js = re.sub(r'(GAdataLayerName\s*:\s*)"[^"]*"', rf'\g<1>"{effective_dl}"', js)

    # --- GAeventsAllowList ---
    # Merge explicit dataLayerEvents with ecommerce event names from ecommerceEventMap.
    # ecommerceEventMap values are the actual event names discovered on the site
    # (e.g. "productDetailView", "addToCart", "purchase") which can differ per client.
    ec_event_map = inspection.get("ecommerceEventMap", {})
    ec_events = [v for k, v in ec_event_map.items() if v and not k.startswith("_")]
    all_dl_events = list(dict.fromkeys(ec_events + dl_events))  # ec events first, deduped
    if all_dl_events:
        allow_list_js = json.dumps(all_dl_events)
        js = re.sub(r"(GAeventsAllowList\s*:\s*)\[.*?\]", rf"\g<1>{allow_list_js}", js, count=1, flags=re.DOTALL)

    # --- Enable dlListener in messageTypes when any signal uses dataLayer trigger ---
    has_dl_signals = any(
        s.get("enabled") and s.get("triggerType") == "dataLayer"
        for s in signals_cfg.values()
    )
    if has_dl_signals and dl_available:
        js = js.replace('// "dlListener"', '"dlListener"', 1)

    # --- Per-signal configuration ---
    for profile_key, cfg_key in SIGNAL_KEY_MAP.items():
        sig_def = signals_cfg.get(profile_key, {})
        if not sig_def.get("enabled"):
            continue

        trigger_type = sig_def.get("triggerType", "load")
        on_events = sig_def.get("triggers", sig_def.get("onEvents", []))  # "onEvents" kept for backward compat
        fields = sig_def.get("fields", {})
        # dl_event: prefer explicit sig-level value, then fall back to ecommerceEventMap
        dl_event = sig_def.get("dataLayerEvent", "") or ec_event_map.get(profile_key, "")
        click_info = sig_def.get("clickInfo", {})

        # Build triggers if not already set in profile.
        # Attribute keys are dot-notation paths into the SDK's msgObj:
        #   type 2 LOAD   → screenview.type = "LOAD"
        #   type 4 click  → event.type = "click"
        #   type 4 change → event.type = "change"
        #   type 5 dl     → customEvent.name = "dlListener" + customEvent.data.event = "<name>"
        #   type 5 form   → customEvent.name = "formSubmit"
        if not on_events:
            if trigger_type == "load":
                on_events = [{"attributes": {"screenview.type": "LOAD"}}]
            elif trigger_type == "dataLayer" and dl_event:
                # Match the specific ecommerce event name in the dataLayer push.
                # customEvent.data.event is the original dataLayer event name (client-specific,
                # e.g. "productDetailView" on some sites, "view_item" for GA4 sites).
                on_events = [{"attributes": {
                    "customEvent.data.event": dl_event,
                }}]
            elif trigger_type == "dataLayer":
                # Event name not yet known — match all dlListener pushes
                on_events = [{"attributes": {"customEvent.name": "dlListener"}}]
            elif trigger_type == "formSubmit":
                on_events = [{"attributes": {"customEvent.name": "formSubmit"}}]
            elif trigger_type == "click":
                # Match any click event; enhance function filters by element identity.
                on_events = [{"attributes": {"event.type": "click"}}]
            elif trigger_type in ("valueChange", "change"):
                # valueChange/change — use target.name from selector when available.
                sel = sig_def.get("selector", "")
                name_m = re.search(r"""name=['\"]([^'\"]+)['\"]""", sel) if sel else None
                if name_m:
                    on_events = [{"attributes": {"event.type": "change", "target.name": name_m.group(1)}}]
                else:
                    on_events = [{"attributes": {"event.type": "change"}}]

        # Build enhance function
        if trigger_type == "dataLayer" and dl_available:
            enhance_body = _enhance_from_web_event(profile_key, fields, profile)
        elif profile_key == "identification":
            # Email capture from webEvent — reads currState.value from Type 4 change event.
            # Per schema: use help.webEvent.target.currState.value (no DOM scan).
            # Guards to sign-in / registration pages; deduplicates via sessionStorage.
            page_url = sig_def.get("pageUrl", "/log-in/")
            reg_url  = profile.get("signals", {}).get("formSubmit", {}).get("pageUrl", "/consumer-registration/")
            enhance_body = "\n".join([
                f"    const _guardPaths = [{page_url!r}, {reg_url!r}];",
                "    if (!_guardPaths.some(function(p) { return location.pathname === p; })) return false;",
                "    const rawEmail = help.webEvent?.target?.currState?.value || null;",
                "    if (!rawEmail || !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(rawEmail)) return false;",
                "    if (sessionStorage.getItem('aco_email_value') === rawEmail) return false;",
                "    sessionStorage.setItem('aco_email_value', rawEmail);",
                "    help.store('audience', { Email: rawEmail });",
                "    signal.audience = { Email: rawEmail };",
                "    signal.loginMethod = 'email';",
                "    return signal;",
            ])
        elif trigger_type == "click":
            enhance_body = _enhance_from_click(profile_key, click_info, fields)
        elif profile_key == "onSiteSearch":
            search_param = profile.get("settings", {}).get("searchParameter", "q")
            enhance_body = "\n".join([
                "    // URL-only fallback (no dataLayer) — used when triggerType is load/click",
                f"    signal.searchTerm = (new URLSearchParams(location.search)).get({search_param!r}) || null;",
                "    if (!signal.searchTerm) return false; // required — only fires on search result pages",
                "    const resultsEl = document.querySelector('[data-result-count],[data-total-results],[data-count]');",
                "    signal.numberOfResults = resultsEl",
                "        ? parseInt(resultsEl.dataset.resultCount || resultsEl.dataset.totalResults || resultsEl.dataset.count || 0)",
                "        : null;",
                "    signal.effect = signal.numberOfResults === 0 ? 'negative' : 'positive';",
                "    signal.audience = help.retrieve('audience') || {};",
                "    return signal;",
            ])
        else:
            enhance_body = _enhance_from_fields(fields) if fields else (
                "    signal.url = location.href;\n"
                "    signal.audience = help.retrieve('audience') || {};\n"
                "    return signal;"
                if profile_key == "pageView" else
                "    // TODO: add extraction logic\n    return false;"
            )

        js = _patch_signal_block(js, cfg_key, on_events, enhance_body)

    return js


# ---------------------------------------------------------------------------
# Full SDK assembly (insert into template)
# ---------------------------------------------------------------------------

def build_full_sdk(configured_init_log_signal: str, profile: dict[str, Any]) -> str:
    customer = profile.get("customer", {})
    app_key = customer.get("appKey", "TODO")
    collector_url = customer.get("collectorUrl", "TODO")

    if not SDK_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"SDK template not found: {SDK_TEMPLATE_PATH}")

    template = SDK_TEMPLATE_PATH.read_text(encoding="utf-8")
    if SDK_INSERT_MARKER not in template:
        raise ValueError(f"Marker not found in sdk-template.js: {SDK_INSERT_MARKER!r}")

    sdk = template.replace(
        SDK_INSERT_MARKER,
        SDK_INSERT_MARKER + "\n\n" + configured_init_log_signal + "\n",
    )
    sdk = sdk.replace('"%%APP_KEY%%"', json.dumps(app_key))
    sdk = sdk.replace('"%%COLLECTOR_URL%%"', json.dumps(collector_url))
    return sdk


# ---------------------------------------------------------------------------
# Tampermonkey userscript
# ---------------------------------------------------------------------------

def build_tampermonkey(profile: dict[str, Any], bundle_filename: str, bundle_abs_path: str) -> str:
    """
    Build a lightweight Tampermonkey userscript that @require-loads the SDK bundle
    from the local file system.  The bundle itself (acoConnectSdkConfig-*.js) is NOT
    inlined here — Tampermonkey fetches it from the file:// URL on each page load,
    so testers only need to swap the .js file to pick up new rounds.

    bundle_filename : e.g. "acoConnectSdkConfig-hm.js"  (basename only, for comments)
    bundle_abs_path : absolute OS path to the .js file   (used in @require)
    """
    customer = profile.get("customer", {})
    settings = profile.get("settings", {})
    inspection = profile.get("inspection", {})

    name = customer.get("name", "Customer")
    prod = customer.get("productionDomain", "")
    staging = customer.get("stagingDomain", "")
    mode = settings.get("mode", "test")
    rnd = inspection.get("round", 0)

    match_lines = [f"// @match        https://{prod}/*"]
    if staging:
        match_lines.append(f"// @match        https://{staging}/*")

    # Tampermonkey requires file:// URLs with triple slash on Mac/Linux
    # and file:/// on Windows — file:/// works on all platforms.
    require_url = "file:///" + bundle_abs_path.replace("\\", "/").lstrip("/")

    return dedent(f"""\
        // ==UserScript==
        // @name         Acoustic SDK — {name} [{mode.upper()}] r{rnd}
        // @namespace    https://acoustic.com/sdk
        // @version      1.{rnd}
        // @description  Acoustic Tealeaf/Connect SDK for {name} — {mode} mode, round {rnd}
        // @author       Acoustic SDK Configuration Assistant
        {chr(10).join(match_lines)}
        // @require      {require_url}
        // @grant        none
        // @run-at       document-end
        // ==/UserScript==

        // Generated: {datetime.now(timezone.utc).isoformat()}
        // Round: {rnd} | Mode: {mode}
        //
        // HOW TO USE:
        //   1. Install Tampermonkey in Chrome (tampermonkey.net)
        //   2. In Tampermonkey Settings → Security, add the absolute path of your output
        //      folder to "Allowlist for @require" — e.g.:  file://{bundle_abs_path[:bundle_abs_path.rfind('/')+1]}*
        //      (Without this, Tampermonkey blocks local file:// @require for security.)
        //   3. Tampermonkey dashboard → + → paste this file content → Save
        //      OR: Utilities → Import from file → select this .user.js file
        //   4. The script auto-loads {bundle_filename} from disk on every page visit.
        //      To update: regenerate {bundle_filename} (no need to reinstall this script).
        //
        // CONSOLE GUIDE (open DevTools > Console on the customer site):
        //   Type 2  = Page load (screenview) — fires on every navigation
        //   Type 4  = Interaction (click, change) — inspect target attributes
        //   Type 5  = Signal fired — expand payload to verify required fields
        //   signalsLog:true shows every emitted signal payload
        //   eventLog:true   shows every SDK event processed
    """)


# ---------------------------------------------------------------------------
# Bookmarklet
# ---------------------------------------------------------------------------

def make_bookmarklet(full_sdk: str) -> str:
    import urllib.parse
    compressed = re.sub(r"\s+", " ", full_sdk).strip()
    return "javascript:" + urllib.parse.quote(compressed, safe="~()*!.'")


# ---------------------------------------------------------------------------
# Review / instructions markdown
# ---------------------------------------------------------------------------

def review_markdown(profile: dict[str, Any], warnings: list[str], d_slug: str, bundle_name: str) -> str:
    customer = profile["customer"]
    inspection = profile.get("inspection", {})
    rnd = inspection.get("round", 0)
    dl_available = inspection.get("dataLayerAvailable")
    dl_events = inspection.get("dataLayerEvents", [])
    mappings = profile.get("mappings", [])
    enabled = [k for k, v in profile.get("signals", {}).items() if v.get("enabled")]
    mode = profile["settings"]["mode"]

    rows = [
        f"# SDK Implementation Review — Round {rnd}",
        "",
        f"- **Customer:** {customer['name']}",
        f"- **Domain:** {customer['productionDomain']}",
        f"- **Mode:** {mode}",
        f"- **Signals:** {', '.join(enabled) or 'None'}",
        f"- **DataLayer:** {'Yes — ' + ', '.join(dl_events) if dl_available and dl_events else 'Not detected / not configured'}",
        "",
        "---",
        "",
        "## How to inject the SDK (Tampermonkey — recommended)",
        "",
        f"1. Install [Tampermonkey](https://www.tampermonkey.net/) in Chrome if not already installed",
        f"2. In Tampermonkey **Settings → Security**, add your output folder to **Allowlist for @require**:",
        f"   e.g. `file:///path/to/output/{d_slug}/*`  (required so local file:// @require loads)",
        f"3. Open the Tampermonkey dashboard → **+** → paste the contents of `acoConnectSdkConfig-{d_slug}.user.js` → Save",
        f"   OR: **Utilities → Import from file** → select `acoConnectSdkConfig-{d_slug}.user.js`",
        f"4. The script auto-loads `{bundle_name}` from disk on every page visit",
        f"5. To update: regenerate `{bundle_name}` (no need to reinstall the userscript)",
        "",
        "**Alternative — DevTools console** (no extension needed, one page at a time):",
        f"- Open DevTools > Console, paste `{bundle_name}` contents, press Enter",
        "",
        "---",
        "",
        "## Reading the console",
        "",
        "With `eventLog: true` and `signalsLog: true` active in test mode, look for:",
        "",
        "| Console type | What it means | What to do |",
        "|---|---|---|",
        "| `[ACO] type 2` | Page load / screenview | Confirm `pageView` fires with correct URL |",
        "| `[ACO] type 4` | Click / interaction | Copy `target.id` or `target.attributes.class` → use as `triggers` attribute |",
        "| `[ACO] type 5` (signal) | Your configured signal fired | Inspect the payload — check required fields |",
        "| `[ACO] type 5` (dlListener) | A dataLayer push was captured | Confirm it matches the signal you expect |",
        "",
        "---",
        "",
        "## Iterative configuration workflow",
        "",
        "**Round 0 → 1: discover dataLayer events**",
        "```",
        "1. Install Tampermonkey script, visit the site",
        "2. Open Console — perform key actions (add to cart, checkout, search)",
        "3. Note which dataLayer events appear as [ACO] type 5 dlListener",
        "4. Update website profile:",
        "   inspection.dataLayerAvailable = true",
        "   inspection.dataLayerEvents = [\"add_to_cart\", \"purchase\", ...]",
        "   signals.addToCart.dataLayerEvent = \"add_to_cart\"",
        "5. Regenerate (increment round), reinstall script",
        "```",
        "",
        "**Round 1 → 2: configure signal enhance functions**",
        "```",
        "1. With events in GAeventsAllowList, signals now fire as type 5 in console",
        "2. Expand the payload — check which fields are null or missing",
        "3. Update signals.addToCart.fields with correct source mappings",
        "   OR note the webEvent.customEvent.data path and update the enhance function",
        "4. Regenerate, reinstall, verify payload is complete",
        "```",
        "",
        "**No dataLayer — click fallback**",
        "```",
        "1. In console, look for [ACO] type 4 events when you click 'Add to cart'",
        "2. Copy target.id or target.attributes.class from the type 4 output",
        "3. Update website profile:",
        "   signals.addToCart.triggerType = \"click\"",
        "   signals.addToCart.clickInfo = { targetId: \"add-to-cart-btn\" }",
        "4. Regenerate — the enhance function will use DOM selectors instead",
        "```",
        "",
        "---",
        "",
        "## Signal mapping",
        "",
        "| Signal | Attribute | Required | Source | Example | Confidence | Status |",
        "|---|---|---:|---|---|---:|---|",
    ]

    for item in mappings:
        cells = [
            item.get("signal", ""),
            item.get("attribute", ""),
            "Yes" if item.get("required") else "No",
            item.get("sourceType", ""),
            str(item.get("exampleValue", "")),
            str(item.get("confidence", "")),
            item.get("status", ""),
        ]
        rows.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |")

    if not mappings:
        rows.append("| — | — | — | — | — | — | No mappings yet — complete round 0 |")

    rows += ["", "## Validation warnings", ""]
    rows.extend(f"- {w}" for w in warnings)
    if not warnings:
        rows.append("- None.")

    rows += [
        "",
        "## Production deployment",
        "",
        "1. Complete all rounds — all required signal fields confirmed in console",
        "2. Set `settings.mode = \"real\"` in profile and regenerate",
        "3. In the regenerated JS: `fakeSignals: false`, `eventLog: false`",
        "4. Deploy via GTM Custom HTML tag or direct `<script>` tag to staging",
        "5. Verify live signals in the Acoustic Connect dashboard",
        "6. Monitor volume, rejects, PII exposure",
    ]

    return "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--base-js", type=Path, required=False, default=None,
        metavar="PATH",
        help=(
            "Path to a pre-fetched initLogSignal.js. "
            "If omitted the script fetches it automatically from BASE_INIT_LOG_SIGNAL_URL. "
            "Supply this flag only when the CDN is unreachable from the current environment."
        ),
    )
    args = parser.parse_args()

    try:
        profile = load_json(args.profile)
        errors, warnings = validate(profile)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    profile["schemaVersion"] = 1
    profile["generatedAt"] = datetime.now(timezone.utc).isoformat()
    slug = slugify(profile["customer"]["name"])
    d_slug = domain_slug(profile["customer"].get("productionDomain", ""))
    # OUTPUT NAMING CONVENTION — DO NOT CHANGE
    # SDK bundle:           acoConnectSdkConfig-{domain-slug}.js
    # Tampermonkey config:  acoConnectSdkConfig-{domain-slug}.tamperMonkeyConfig.js
    # domain-slug derived from productionDomain (e.g. www2.acmeretail.com → acmeretail)
    bundle_name = f"acoConnectSdkConfig-{d_slug}.js"
    inspection_round = profile.get("inspection", {}).get("round", 0)
    args.out.mkdir(parents=True, exist_ok=True)

    base_js = load_base(args.base_js)
    configured_js = configure_init_log_signal(base_js, profile)
    # Inject audience utility signal into initLogSignal
    configured_js = _inject_audience_signal(configured_js, profile)
    full_sdk = build_full_sdk(configured_js, profile)
    # Update privacy targets in configureSDK() — must run on full_sdk (template layer)
    full_sdk = _update_privacy_targets(full_sdk, profile)

    config_path = args.out / f"{slug}-customer-signal-config.json"
    bundle_path = args.out / bundle_name
    tm_path = args.out / f"acoConnectSdkConfig-{d_slug}.tamperMonkeyConfig.js"
    review_path = args.out / f"{slug}-implementation-review.md"

    bundle_abs = str(bundle_path.resolve())
    tampermonkey = build_tampermonkey(profile, bundle_name, bundle_abs)

    config_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # --- TODO hard-block: bundle must be clean before delivery ---
    todo_lines = [i+1 for i, ln in enumerate(full_sdk.splitlines()) if "// TODO:" in ln]
    if todo_lines:
        print(f"[ACO] ERROR: Config contains {len(todo_lines)} unresolved TODO line(s): {todo_lines}", file=sys.stderr)
        print("[ACO] Fix: add field sources to the profile signals, then regenerate.", file=sys.stderr)
        sys.exit(2)  # exit code 2 = TODOs present
    bundle_path.write_text(full_sdk, encoding="utf-8")
    tm_path.write_text(tampermonkey, encoding="utf-8")
    review_path.write_text(review_markdown(profile, warnings, d_slug, bundle_name), encoding="utf-8")

    result: dict[str, Any] = {
        "round": inspection_round,
        "bundle": bundle_abs,
        "bundleName": bundle_name,
        "tampermonkey": str(tm_path.resolve()),
        "config": str(config_path.resolve()),
        "review": str(review_path.resolve()),
        "warnings": warnings,
        "nextSteps": _next_steps(profile, bundle_name),
    }

    print(json.dumps(result, indent=2))
    return 0


def _next_steps(profile: dict[str, Any], bundle_name: str = "") -> list[str]:
    inspection = profile.get("inspection", {})
    rnd = inspection.get("round", 0)
    dl = inspection.get("dataLayerAvailable")
    dl_events = inspection.get("dataLayerEvents", [])
    d_slug = domain_slug(profile["customer"].get("productionDomain", ""))
    tm_name = bundle_name.replace(".js", ".tamperMonkeyConfig.js") if bundle_name else f"acoConnectSdkConfig-{d_slug}.tamperMonkeyConfig.js"

    steps = [f"Install {tm_name} via Tampermonkey (ensure output folder is in @require allowlist)"]

    if rnd == 0:
        steps += [
            "Visit: homepage, product page, cart, checkout, order confirmation, search",
            "In DevTools Console: perform add-to-cart, search, checkout — note [ACO] type 4 and type 5 dlListener events",
            "Report back: which dataLayer events fired? (or 'no dataLayer' if none seen)",
        ]
    elif dl is True and not dl_events:
        steps += [
            "Update inspection.dataLayerEvents in the profile with the events you saw",
            "Set each signal's dataLayerEvent field (e.g. addToCart.dataLayerEvent = 'add_to_cart')",
            "Regenerate (increment inspection.round)",
        ]
    elif dl is True and dl_events:
        steps += [
            "Verify type 5 signals fire with correct payloads in console",
            "For any null fields: update signal.fields with the correct webEvent path",
            "Regenerate when all required fields are confirmed",
        ]
    elif dl is False:
        steps += [
            "Look at [ACO] type 4 events in console for each key interaction",
            "Copy target.id or target.attributes from type 4 output for each signal",
            "Update each signal's clickInfo in the profile and regenerate",
        ]

    return steps


if __name__ == "__main__":
    sys.exit(main())
