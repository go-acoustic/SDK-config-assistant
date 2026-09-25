<!-- SYNTHETIC TEST FIXTURE: not real customer data -->
# SDK Implementation Review — Round 2

- **Customer:** Example Retail
- **Domain:** shop.example.com
- **Mode:** test
- **Signals:** pageView, productView, addToCart, identification
- **DataLayer:** Yes — view_item, view_item_list
- **Original SDK file name:** acoConnectSdkConfig-shop.js

## Signal mapping

| Signal | Attribute | Required | Source | Example | Confidence | Status |
|---|---|---:|---|---|---:|---|
| productView | productId | Yes | dataLayer | SKU-1001 | 95 | confirmed |
| addToCart | productId | Yes | sessionStorage | SKU-1001 | 40 | unverified |

## Escalated signals

- **addToCart**: signal_not_triggered after 2 correction attempts
- **identification**: email_verification_required

Readiness: Not ready
