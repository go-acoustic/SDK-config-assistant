#!/usr/bin/env python3
"""Validate a customer SDK profile without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED_MODES = {"test", "real"}
ALLOWED_IMPLEMENTATION_MODES = {"guided", "website-assisted", "datalayer-assisted", "diff"}
ALLOWED_STATUSES = {
    "Found automatically",
    "Inferred with confidence",
    "Needs confirmation",
    "Not available on page",
    "Requires customer dataLayer/API/event payload",
}
ALLOWED_SOURCES = {
    "URL",
    "Meta tag",
    "JSON-LD",
    "DOM selector",
    "dataLayer",
    "sessionStorage",
    "localStorage",
    "AJAX response",
    "customer-provided value",
    "fallback/default",
}
KNOWN_SIGNALS = {
    "pageView",
    "identification",
    "productView",
    "addToCart",
    "order",
    "onSiteSearch",
    "formSubmit",
    "formInteraction",
    "productConfiguration",
    "richMediaInteraction",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Profile root must be a JSON object.")
    return value


def validate(profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    customer = profile.get("customer")
    settings = profile.get("settings")
    signals = profile.get("signals")

    if not isinstance(customer, dict):
        errors.append("customer must be an object.")
        customer = {}
    if not isinstance(settings, dict):
        errors.append("settings must be an object.")
        settings = {}
    if not isinstance(signals, dict):
        errors.append("signals must be an object.")
        signals = {}

    for field in ("name", "productionDomain", "appKey", "collectorUrl"):
        if not str(customer.get(field, "")).strip():
            errors.append(f"customer.{field} is required.")
        elif str(customer[field]).strip().upper() == "TODO":
            warnings.append(f"customer.{field} still contains TODO.")

    mode = settings.get("mode")
    if mode not in ALLOWED_MODES:
        errors.append(f"settings.mode must be one of {sorted(ALLOWED_MODES)}.")
    implementation_mode = settings.get("implementationMode")
    if implementation_mode not in ALLOWED_IMPLEMENTATION_MODES:
        errors.append(
            f"settings.implementationMode must be one of {sorted(ALLOWED_IMPLEMENTATION_MODES)}."
        )

    unknown_signals = sorted(set(signals) - KNOWN_SIGNALS)
    if unknown_signals:
        warnings.append(f"Unknown signals: {', '.join(unknown_signals)}.")

    if mode == "real":
        unresolved = [
            item
            for item in profile.get("mappings", [])
            if item.get("required") is True
            and item.get("status")
            not in {"Found automatically", "Inferred with confidence"}
        ]
        if unresolved:
            errors.append(
                f"Real mode has {len(unresolved)} unresolved required mapping(s)."
            )

    for index, mapping in enumerate(profile.get("mappings", [])):
        prefix = f"mappings[{index}]"
        if not isinstance(mapping, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        if mapping.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{prefix}.status is invalid.")
        if mapping.get("sourceType") not in ALLOWED_SOURCES:
            errors.append(f"{prefix}.sourceType is invalid.")
        confidence = mapping.get("confidence")
        if not isinstance(confidence, int) or not 0 <= confidence <= 100:
            errors.append(f"{prefix}.confidence must be an integer from 0 to 100.")
        if mapping.get("required") and not mapping.get("attribute"):
            errors.append(f"{prefix}.attribute is required.")

    for signal_name, signal in signals.items():
        if not isinstance(signal, dict):
            errors.append(f"signals.{signal_name} must be an object.")
            continue
        if signal.get("enabled") and not signal.get("triggerType"):
            errors.append(f"signals.{signal_name}.triggerType is required when enabled.")
        if signal.get("enabled") and not isinstance(signal.get("fields", {}), dict):
            errors.append(f"signals.{signal_name}.fields must be an object.")

    email_capture = settings.get("emailCapture", "disabled")
    identification = signals.get("identification", {})
    if identification.get("enabled") and email_capture == "disabled":
        errors.append(
            "identification cannot be enabled when settings.emailCapture is disabled."
        )

    serialized = json.dumps(profile)
    sensitive_patterns = {
        "password": r'"(?:password|passcode)"\s*:',
        "payment card": r'"(?:cardNumber|creditCard|cvv|cvc)"\s*:',
        "secret/token": r'"(?:apiSecret|accessToken|refreshToken)"\s*:',
    }
    for label, pattern in sensitive_patterns.items():
        if re.search(pattern, serialized, re.IGNORECASE):
            errors.append(f"Profile appears to include a {label} field.")

    if not profile.get("evidence"):
        warnings.append("No browser inspection evidence is recorded.")
    if not profile.get("mappings"):
        warnings.append("No signal mapping rows are recorded.")
    if mode == "real" and profile.get("questions"):
        warnings.append("Real mode still has unanswered questions.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    try:
        profile = load_json(args.profile)
        errors, warnings = validate(profile)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors, warnings = [str(error)], []

    result = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": f"{len(errors)} error(s), {len(warnings)} warning(s)",
    }
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["summary"])
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
