# Site Category Context Library

**Purpose:** When the SDK-config-assistant inspects a new customer site, it must first classify the site into one of the categories below. Each category defines what "product", "addToCart", "order", and related concepts mean for that business — preventing the assistant from guessing or defaulting to physical-goods ecommerce semantics when they don't apply.

**How to use:** During Step 2 (site inspection / profiling), run the category-detection checklist to determine the site's category. Load the matching section below to inform signal field mappings for the entire session. If a site matches more than one category, apply the primary category and note the secondary.

---

## Category Detection Checklist

Run these checks in order. Stop at the first match.

| Priority | Signal | Category |
|---|---|---|
| 1 | Site sells seats/tickets to named shows, concerts, or performances | `performing-arts` |
| 2 | Site is a hospital, clinic, or doctor/specialist finder | `healthcare` |
| 3 | Site collects donations for missions, causes, or charitable campaigns | `nonprofit-fundraising` |
| 4 | Site sells insurance plans or financial protection products | `insurance` |
| 5 | Site sells loans, accounts, mortgages, or banking products | `financial-services` |
| 6 | Site sells memberships (tiered, annual, recurring) | `membership-association` |
| 7 | Site sells books, printables, or educational curricula | `education-publishing` |
| 8 | Site sells oracle cards, spiritual books, courses, or wellness content | `spiritual-wellness-ecommerce` |
| 9 | Site sells resort stays, golf, or hospitality packages | `hospitality-travel` |
| 10 | Site sells telecom plans, ISP services, or utility plans | `telecom-utilities` |
| 11 | Site is a B2B application portal (e.g. pub lease, franchise, dealer) | `b2b-application-portal` |
| 12 | Site is a media / lead-gen / advertising platform | `media-leadgen` |
| 13 | Site uses a standard ecommerce platform (BigCommerce, Shopify, Prestashop, WooCommerce) and sells physical goods | `standard-ecommerce` |
| 14 | No match | `unknown` — surface to user before proceeding |

---

## Category Definitions

---

### `standard-ecommerce`

**What it is:** Physical goods sold through a standard ecommerce platform with SKUs, cart, checkout, and order confirmation.

**What "product" means:** A discrete physical item with a stock-keeping unit (SKU). A product may have variants (size, colour, qty).

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | Shopper views a product detail page | SKU / `item_id` from dataLayer or DOM | Product title | Department / `item_category` from dataLayer or breadcrumb |
| `productConfiguration` | Shopper selects a variant (size, colour, qty) | Same SKU | Same product title | Same category |
| `addToCart` | Shopper adds item to cart | SKU / `item_id` | Product title | `item_category` |
| `order` | Purchase confirmed on order confirmation page | Per-line SKU | Per-line product title | Per-line category |

**dataLayer schema:** Prefer GA4 (`ecommerce.items[]`) over UA (`ecommerce.detail.products[]`). Check `data-product-id`, `data-sku`, JSON-LD `Product` schema as fallbacks.

**productId consistency rule:** SKU must be identical across `productView → addToCart → order`. Check for variant-suffixing (e.g. `SKU-RED` vs `SKU`) and case differences.

**"Cart" is a real cart.** Standard add-to-cart → cart page → checkout → confirmation flow.

**No-SKU fallback:** If no SKU exists (e.g. digital-only items), use the URL slug of the product page as productId.

---

### `performing-arts`

**What it is:** Sites selling tickets to named theatrical shows, concerts, musicals, operas, dance performances, or events at a venue.

**What "product" means:** A **show or performance** — not a seat or a venue. The show title (or a production-season ID, where the back-end ticketing platform provides one) is the canonical product identifier.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a show detail/listing page | Production season ID (if the back-end exposes one) OR show title slug | Show title from page `<h1>` | `"performance"` (always) |
| `productConfiguration` | User selects date, performance, or seat type | Production season ID + performance ID | Show title | `"performance"` |
| `addToCart` | User adds tickets to basket | Production season ID | Show title | `"performance"` |
| `order` | Booking confirmed | Per-line: season ID + performance ID | Show title / performance description | `"performance"` |

**Production-season ID pattern:** Some arts-sector ticketing back-ends expose `productId = productionSeasonId`, supplemented by `performanceId` for configuration/order signals. `productCategory` is always `"performance"`. Additional items (programmes, merchandise) use `productCategory: "additional item"`.

**Sites with no back-end IDs:** Use show title from DOM (`h1`, `.col-sm-12.text-center h1`, `#ctl25_PanelDetails > div > h1`) as both productId and productName.

**"addToCart" is seat selection / basket add.** There is no traditional shopping cart page — the basket is usually an in-session state within the ticketing flow.

**"Order" = completed booking.** Order confirmation typically shows a booking reference. Per-ticket items map to a single show.

**No SKU concept.** Do not use seat numbers or row/seat as productId — these are per-ticket allocations, not the product itself.

**productCategory is always `"performance"`.** Do not try to derive it from genre, venue, or section — this is fixed across all arts clients.

---

### `healthcare`

**What it is:** Hospitals, health systems, clinics, or specialist finder sites where users search for doctors, services, or book appointments.

**What "product" means:** A **healthcare service or clinical specialty**, or a **named physician/doctor**. There are no SKUs. The service name or doctor name is the product identifier.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a service page or doctor profile | Service name or doctor name (from page heading) | Same as productId | Service line (e.g. `"Cardiology"`, `"Primary Care"`) |
| `productConfiguration` | User selects appointment type or insurance | Service/doctor name | Same | Service line |
| `addToCart` | User initiates appointment scheduling | Doctor name (`.m-doctor-teaser__heading`) | Same | `"Doctor Appointment"` |
| `order` | Appointment booking confirmed | `"Doctor Appointment"` (static) | `"Doctor Appointment"` | Service line |

**No traditional ecommerce.** Transactions are zero-cost from the user's perspective (covered by insurance/NHS). The "conversion" is a completed appointment request or booking.

**productId = productName** for doctors and services — there is no numeric ID. Use the human-readable name as the identifier.

**"Cart" does not exist.** The appointment scheduler is the conversion flow. Map `addToCart` to the "Request appointment" or "Book now" click.

**Identification signal is important** — logged-in patient portals often expose patient ID for the `identification` signal.

---

### `nonprofit-fundraising`

**What it is:** Charity and non-profit sites where the primary conversion is a donation, pledge, or sponsorship of a named cause, mission, or campaign.

**What "product" means:** A **donation cause, mission, or campaign** — not a physical item. The "product" the donor is "buying" is the cause they are supporting.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a cause/mission/project page | `"donation"` + cause title (e.g. `"donation for John Smith"`) | Same | `"donation"` or campaign type |
| `productConfiguration` | User selects donation amount or frequency | Same cause ID | Same | `"donation"` |
| `addToCart` | User adds donation to basket / pledge form | Cause title with `"donation for "` prefix | Same | `"donation"` |
| `order` | Donation completed (thank-you page) | Per-cause: `item_id` from GA4 dataLayer or cause title | `item_name` or cause title | `item_category` (e.g. `"general-missionary"`) |

**Cause-name productId pattern:** Some mission-giving sites use `productId = "donation for " + missionaryName`, with GA4 `ecommerce.items[]` for the order signal and `item_category` defaulting to something like `"general-missionary"`.

**Static-partnership pattern:** Some organisations frame all giving as a single "partnership" with the org rather than distinct causes — in that case all signals intentionally use a static productId/productName such as `"Partnership"`.

**Amount-in-productId pattern:** University and campaign giving sites often construct productId from type + amount (e.g. `type.toLowerCase() + "-" + amount"` → `"annual-100"`), with productName from the campaign form header and productCategory from the CTA button text.

**"Cart" is a giving basket.** Many non-profit platforms allow adding multiple causes. If no basket exists, treat each donation form submission as a single-item order.

**Amount and frequency are NOT productId.** They are `unitPrice` and a custom attribute — not part of the product identifier. The productId identifies the cause, not the amount.

**GA4 dataLayer is common** — check for `ecommerce.items[]` on thank-you pages.

---

### `insurance`

**What it is:** Sites selling insurance policies — health, life, pet, travel, or property — typically with named tiers (Basic, Standard, Preferred, Premium).

**What "product" means:** An **insurance plan or tier** — typically identified by a plan code or a tier name.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a plan comparison or details page | Plan code (e.g. `PLAN100`) or URL slug | Tier name (e.g. `"Standard"`, `"Preferred"`, `"Premium"`) | `"insurance-plans"` or product line |
| `productConfiguration` | User selects coverage options, deductibles, or extras | Same plan code | Same tier name | Same |
| `addToCart` | User selects a plan to proceed with | Same plan code | Same tier name | Same |
| `order` | Application/purchase confirmed | Plan code | Tier name | `"insurance-plans"` |

**Plan-code pattern:** Some insurance sites use short plan codes per tier (e.g. `PLAN100` = Standard, `PLAN200` = Preferred, `PLAN300` = Premium), detectable from a URL fragment, DOM event data, or a custom dataLayer.

**URL-slug plan pattern:** Others derive productId from the URL itself — `productId = segments[1]` (the plan slug from `/insurance-plans/[plan-slug]`), with productName read from a page banner heading element.

**No physical cart.** The application wizard IS the checkout. Map `addToCart` to plan selection, `order` to the final confirmation page.

**Multi-product per order is rare** — most insurance purchases are single-plan. Do not assume `orderedItems[]` will have multiple entries.

---

### `financial-services`

**What it is:** Banks, credit unions, lenders, and financial institutions where users apply for loans, open accounts, or access financial products.

**What "product" means:** A **financial product** — savings account, loan type, mortgage, investment account, insurance policy. There are no SKUs. The product type IS the product.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a product landing page (e.g. "Home Loan") | URL slug or product type (e.g. `"home-loan"`) | Page `<h1>` or product display name | Product category (e.g. `"loans"`, `"accounts"`, `"insurance"`) |
| `productConfiguration` | User enters loan amount, term, or account type | Same product type | Same | Same |
| `addToCart` | User starts an application | Product type + term/amount if meaningful | Product display name | Product line |
| `order` | Application submitted / account opened | Product type | Product name | Product line |

**Loan-application funnel pattern:** productId and productName are the loan type (e.g. `"personal-loan"`) derived from the URL or application step; unitPrice = loan amount requested.

**Regional-bank pattern:** Products include accounts, home loans, personal loans, business banking — these sites often need direct DOM/URL inspection to populate fields, since there's no consistent template.

**Credit-union pattern:** Similar to banking — products are membership accounts, share certificates, auto loans, etc.

**"addToCart" is starting an application.** There is no physical cart. The application wizard steps are the checkout flow.

**"Order" is form submission / application received.** Often no dollar amount at this stage — the loan amount or account balance may be captured as `unitPrice`.

**Identification signal is high-value** — many banking sites have authenticated portals. Capture member/customer ID for `identification` signal.

---

### `membership-association`

**What it is:** Professional associations, golf clubs, alumni organisations, or content subscription sites where the product is a membership tier.

**What "product" means:** A **membership tier or plan** — identified by tier name.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views membership options | Tier name (e.g. `"Basic"`, `"VIP"`, `"Executive"`) | Same as productId | `"Membership"` (always) |
| `productConfiguration` | User selects a tier | Same tier name | Same | `"Membership"` |
| `addToCart` | User adds a membership to cart | Same tier name | Same | `"Membership"` |
| `order` | Membership purchase confirmed | Tier name | Tier name | `"Membership"` |

**Tier-name productId pattern:** Tier names are read directly from a pricing-table element (e.g. an uppercase tier label class) and used as-is for productId/productName. productCategory is always `"Membership"`.

**productId = productName = tier name.** There is no numeric ID.

**Annual vs monthly** is a `productConfiguration` attribute, not a different productId.

---

### `education-publishing`

**What it is:** Educational publishers, book sellers, curriculum providers, or digital resource sites targeting schools, parents, or students. May include a donation component.

**What "product" means:** An **educational resource** — book, printable, magazine, curriculum kit, or digital download.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a resource/book detail page | Book/resource title (from an item-detail heading element) | Same | `"Book"` / `"Magazine"` / `"Printable"` (detect from page type) |
| `productConfiguration` | User selects format (print vs digital, grade level) | Same title | Same | Same |
| `addToCart` | User adds to cart | Title | Title | Resource type |
| `order` | Checkout complete | Per-item title | Per-item title | Resource type |

**URL-pattern product-type detection:** Some catalogues encode product type in the URL path (e.g. distinct path segments for "printable" vs "magazine" vs "book" items), with productId read from a bolded title element.

**Category fallback pattern:** When no explicit type is available, productCategory can default to a broad label (e.g. `"Books"`) and fall back to a breadcrumb value when present.

**Donation component:** Some education-publishing sites also collect donations. When the page is a donation flow, productId = `"${amount}USD Donation"`, productCategory = `"Donation"`. These are separate from book purchases.

**productId = productName** — resource title is the identifier (no SKU system).

---

### `spiritual-wellness-ecommerce`

**What it is:** Spiritual authors, wellness brands, and related publishers selling books, oracle card decks, online courses, and digital downloads — typically built on Magento/Adobe Commerce.

**What "product" means:** A **spiritual or wellness product** — book, card deck, online course, or digital download — with format as the key category discriminator.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a product page | SKU (`sku` attribute or product input value) or product title | Product title (`.product-item-name a` or `h1.product-title`) | Format type from `div.product-format` or meta (`"Card Deck"`, `"Book"`, `"Online Course"`, `"Audio"`) |
| `productConfiguration` | User selects a format variant (hardcover vs digital) | Same SKU | Same title | Same format |
| `addToCart` | User adds to cart | SKU from `input[name="product"]` value | Product title | Format from DOM or meta |
| `order` | Purchase confirmed | Per-item: SKU or title | Per-item title | Per-item format from a format-type column |

**Magento SKU pattern:** productId = SKU from `input[name="product"]`. productName from `.product-item-name a`. productCategory from `div.product-format` or `og:site_name` meta, falling back to URL segment pattern matching. This pattern is common across a family of related brand sites sharing one platform — apply the same extraction pattern to each.

**Format is critical for product category.** These sites sell the same content in multiple formats. The format type (Book, Card Deck, Online Course, Audio Download) IS the category.

---

### `hospitality-travel`

**What it is:** Hotels, resorts, golf courses, or travel booking sites where users search for and reserve stays, activities, or packages.

**What "product" means:** A **bookable experience or accommodation** — resort stay, golf round, tee time, or package.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a room, package, or activity | Resort/venue name from `input[name="resort"]` or URL | Same as productId | `"Resort Accommodations"` or activity type (e.g. `"Select golf by day"`) |
| `productConfiguration` | User selects dates, room type, or guest count | Same resort name | Same | Same category |
| `addToCart` | User proceeds to booking/reservation | Same resort/venue name | Same | `"Resort Accommodations"` |
| `order` | Booking confirmed | Resort name | Resort name | Activity / stay category |

**Resort-name productId pattern:** productId and productName = resort name from a hidden form field (e.g. `input[name="resort"]`). productCategory = `"Resort Accommodations"` for stays; a golf-specific label for golf booking flows. Detect from the URL path.

**Golf-specific:** A round of golf is a product. The course name is the productId.

**No traditional SKU.** Booking reference or reservation ID appears only at order completion — do not use as productId.

**"addToCart" is adding to a booking basket or proceeding past a date/type selection step.** The booking wizard IS the checkout.

---

### `telecom-utilities`

**What it is:** Telecommunications providers (internet, mobile, cable), ISPs, or utility companies (electricity, gas) where users shop for service plans or manage their accounts.

**What "product" means:** A **service plan or utility service** — internet tier, mobile plan, electricity rate plan, etc.

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a plan/service details page | Plan name/ID from dataLayer `item_id` or URL slug | Plan display name `item_name` | Service type (e.g. `"internet"`, `"mobile"`, `"electricity"`) |
| `productConfiguration` | User selects speed tier, contract length, or add-ons | Plan ID | Plan name | Service type |
| `addToCart` | User adds plan to order | Plan ID from `item_id` | Plan name from `item_name` | `item_category` |
| `order` | Service order / sign-up confirmed | Per-line plan ID | Plan name | Service category |

**GA4 dataLayer pattern:** `item_id`, `item_name`, `item_category` from `ecommerce.items[]` — the most reliable source when present.

**Utility rate-plan pattern:** "Products" are rate plans or service tiers; productId/productName typically need direct domain inspection since there's no consistent template.

**No physical SKU.** Plan codes or plan names (e.g. `"500Mbps-internet"`) serve as productId.

**Account authentication is common.** Capture `identification` signal on login/account pages.

---

### `b2b-application-portal`

**What it is:** Business-to-business portals where the conversion is a business application, partnership request, or trade account — not a consumer purchase.

**What "product" means:** The **business opportunity** being applied for — e.g. for a pub-lease portal, this is a pub (identified by a pub code).

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | Applicant views a business opportunity listing | Opportunity code from URL (e.g. `?pubCode=`) | Opportunity name | Business type |
| `productConfiguration` | Applicant starts filling application | Same opportunity code | Same | Same |
| `addToCart` | N/A — no cart concept | — | — | — |
| Custom: `pubApplicationStarted` | Applicant begins an application | `href.split("pubCode=")[1]` | Opportunity name | — |
| Custom: `pubApplicationCompleted` | Application submitted | Opportunity code | Opportunity name | — |

**Custom-signal application-funnel pattern:** Some B2B application portals use custom signal types (e.g. `"pubApplicationStarted"` / `"pubApplicationCompleted"`) instead of standard `addToCart`/`order`, holding productId on a nested array on the signal.

**No standard cart or order signal.** The entire funnel is captured through custom signal types.

**For other B2B portals:** Map "starting application" to a custom signal or `productConfiguration`, and "submitted application" to `order` with a static `productId` describing the product/service applied for.

---

### `media-leadgen`

**What it is:** Digital media, advertising networks, or lead generation platforms where the primary event is a lead submission or ad interaction rather than a product purchase.

**What "product" means:** A **lead or conversion event** tracked by a lead tracking ID (LTID). There is no product SKU — the lead itself is the "product".

**Signal semantics:**

| Signal | Meaning | productId source | productName source | productCategory source |
|---|---|---|---|---|
| `productView` | User views a landing page / offer | LTID from `webEvent.customEvent.data.ltid` | Same as productId (or derived) | `"Conversion"` |
| `order` | Lead submitted / conversion captured | LTID | LTID | `"Conversion"` |

**Lead-tracking-ID pattern:** `signal.productId = help.webEvent.customEvent.data.ltid`. productCategory is always `"Conversion"`. pageCategory derived from a URL path segment, treating root as `"homepage"`.

**No cart concept.** Lead forms are the conversion. `addToCart` and `productConfiguration` signals are not applicable.

---

## When a Site Spans Multiple Categories

Some sites have multiple distinct sections that each require different signal semantics. Handle as follows:

1. **Publisher with a donation flow** — apply `education-publishing` as primary. Switch to `nonprofit-fundraising` semantics when the URL path indicates a donation/giving page.

2. **Events site with a membership component** — apply `performing-arts` as primary (event ticketing). May also have `membership-association` content — confirm the current URL before applying either set of semantics.

3. **University or institutional giving site** — primary category is `nonprofit-fundraising` (giving campaigns), but the site also has general institutional pages: the `pageView` signal applies across all pages, while product signals only fire on giving pages.

4. **A family of sub-brand sites sharing one platform** — apply the same category and extraction pattern (e.g. the same Magento-based selectors) across all sub-brand sites in the family.

---

## Categories with No Current Customers (Reserved for Future Use)

| Category | Description | Signal notes |
|---|---|---|
| `saas-software` | SaaS platforms — trial signups, plan upgrades | Product = plan tier; "addToCart" = start trial |
| `automotive` | Car dealer, configurator, or fleet sites | Product = vehicle model + trim; no traditional order |
| `food-delivery` | Restaurant or food delivery ordering | High-cardinality products; order signal fires on delivery confirmation |
| `gaming-lottery` | Online gaming, casino, or lottery sites | Product = game type; compliance considerations |
| `events-conference` | Professional event / conference registration | Product = event + session; order = registration confirmed |
