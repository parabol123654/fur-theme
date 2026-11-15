# Fur - Furniture eCommerce Theme (`fur_theme`) — Odoo 15.0

Yellow and navy eCommerce theme for furniture and interior design shops:
homepage, mega menu, shop and category pages, product page, one-step checkout
on the cart page, projects showcase (`/projects`), instant product search,
floating call / WhatsApp / Zalo / Messenger buttons. English and Vietnamese.

## Install

```bash
odoo -d <db> -i fur_theme --without-demo=all  # theme only
odoo -d <db> -i fur_theme                     # + sample furniture shop (database with demo data)
```

Dependencies: `website_sale`, `payment_transfer`, `auth_signup`, `account`.
The wishlist hearts on the product cards show when `website_sale_wishlist` is installed.

## Configure

- **Website › Configuration › Websites › (website) › Fur Theme**: switch the
  theme on/off for that website, brand name, footer logo (for the dark footer),
  hotline, WhatsApp, Zalo numbers, Messenger
  link, opening hours, buying & payment guide (second tab of the product page).
- Logo: **Website › Configuration › Settings** (the header and footer show the
  website logo; without one, the brand name).
- eCommerce category: **Show on Homepage**; product and project: **Featured on Homepage**.
- **Website › Projects**: interior projects.
- Product: **Compare to Price** (crossed-out price); a product without a price
  shows "Contact" instead of the cart button.
- Bank transfer / cash on delivery payment acquirers (two "Wire Transfer"
  acquirers, field **Fur Checkout Mode**) are created and enabled on install;
  the bank accounts shown after a bank transfer order are those of the
  company's bank journals (pending message of the acquirer).

## Demo data

4 categories with 10 sub-categories, 34 products and 6 projects, plus a demo
menu, logo and contacts. Pictures come from Odoo's own demo pictures
(`product` and `website` modules), referenced, not copied; Odoo 15 ships few
furniture pictures, so some sample products share one.

## Tests

```bash
odoo -d <testdb> --db-filter='^<testdb>$' -i fur_theme --test-tags /fur_theme --stop-after-init
```

The checkout tour needs Chrome and the `websocket-client` Python package.

License: LGPL-3 (see LICENSE). Author: Manh Nguyen.
