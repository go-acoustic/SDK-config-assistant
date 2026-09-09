# Contributing

This skill is developed in an internal Acoustic repository and published here. Changes are made
internally and ported across, so if you work at Acoustic, start there rather than opening a PR on
this repo.

## Never commit customer information

This repository is public. Nothing that identifies a customer may be committed to it — not in code,
not in documentation, not in an example:

- customer or account names, and any internal codename for one
- customer domains, subdomains, or URLs
- DOM selectors, dataLayer keys, or page markup taken from a customer's live site
- plan codes, tenant identifiers, environment names, or account numbers
- test-run records, analytics output, or saved website profiles

Use placeholders in examples instead. The conventional ones are **Acme Retail** /
`acmeretail.com`, and **Northwind Trading** / `northwindtrading.co.uk` where a second is needed.
Where a real name was only illustrating that behaviour varies between sites, say that — "some
sites", "a live EU tenant" — rather than naming anyone.

Do not add `docs/`, `analytics/`, or `profiles/` directories here. Those exist in the internal
copy and hold customer data by design; they are not part of what is published.

## Git history is public too

A public repository's history is public, and removing a name in a later commit does not unpublish
it — the removing commit's own diff shows what it removed. So fix it in the working tree and commit
once. If you have already pushed customer information to this repo, do not try to patch over it:
raise it with the code owners in `CODEOWNERS` straight away.

## Review

`main` requires a pull request and a review from the code owners listed in `CODEOWNERS`.
