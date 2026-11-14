# Fur - Furniture eCommerce Theme (`fur_theme`) — Odoo 20.0

Yellow and navy eCommerce theme for furniture and interior design shops:
homepage, mega menu, shop and category pages, product page, one-step checkout
on the cart page, projects showcase (`/projects`), instant product search,
floating call / WhatsApp / Zalo / Messenger buttons. English and Vietnamese.

## Install

```bash
odoo -d <db> -i fur_theme              # theme only
odoo -d <db> -i fur_theme --with-demo  # + sample furniture shop
```

Dependencies: `website_sale`, `payment_custom`, `auth_signup`, `account`.

## Configure

- **Website › Configuration › Websites › (website) › Fur Theme**: switch the
  theme on/off for that website, brand name, footer logo (for the dark footer),
  hotline, WhatsApp, Zalo numbers, Messenger
  link, opening hours, buying & payment guide (second tab of the product page).
- Logo: **Website › Configuration › Settings** (the header and footer show the
  website logo; without one, the brand name).
- eCommerce category: **Show on Homepage**; product and project: **Featured on Homepage**.
- **Website › Site › Content › Projects**: interior projects.
- Bank transfer / cash on delivery providers are created and published on
  install; set the bank account on the bank transfer provider.

## Demo data

4 categories with 10 sub-categories, 34 products and 6 projects, plus a demo
menu, logo and contacts. Pictures come from Odoo's own demo pictures
(`product`, `website`, `website_sale` modules), referenced, not copied.

## Tests

```bash
odoo -d <testdb> --db-filter='^<testdb>$' -i fur_theme --test-tags /fur_theme --stop-after-init
```

The checkout tour needs Chrome and the `websocket-client` Python package.

License: OPL-1 (see LICENSE). Author: Sanxus Lab.
