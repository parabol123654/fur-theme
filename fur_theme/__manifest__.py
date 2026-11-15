# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
{
    "name": "Fur - Furniture eCommerce Theme",
    "summary": "Furniture & interior design eCommerce theme: homepage, shop, product page, "
    "one-step checkout, projects showcase, instant search",
    "description": """
Furniture eCommerce theme for Odoo 18.0 Community and Enterprise.

* Header with logo, instant product search, hotline, cart, account and flag language switcher
* Homepage: hero slider, service strip, category grid, one product block per category,
  featured projects
* Shop and category pages with banner, sub-category pills and product cards
* Product page with sticky buy box, perks, hotline card, description and buying guide tabs
* One-step checkout on the cart page (bank transfer, cash on delivery)
* Projects showcase (/projects) with list, filters and detail pages
* Floating call, WhatsApp, Zalo and Messenger buttons
* English and Vietnamese
""",
    "version": "18.0.1.0.0",
    "category": "Website/Theme",
    "author": "Manh Nguyen",
    "license": "LGPL-3",
    "website": "https://github.com/parabol123654/fur-theme",
    "support": "parabol123654@gmail.com",
    "depends": [
        "website_sale",
        "website_sale_wishlist",
        "website_sale_comparison",
        "payment_custom",
        "auth_signup",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/fur_security.xml",
        "data/fur_policy_page.xml",
        "views/fur_project_views.xml",
        "views/product_views.xml",
        "views/fur_menus.xml",
        "views/sale_order_views.xml",
        "views/templates/layout.xml",
        "views/templates/contactus.xml",
        "views/templates/homepage.xml",
        "views/templates/shop.xml",
        "views/templates/product.xml",
        "views/templates/checkout.xml",
        "views/templates/projects.xml",
        "views/templates/page_titles.xml",
    ],
    "demo": [
        "demo/fur_product_demo.xml",
        "demo/fur_project_demo.xml",
        "demo/fur_website_demo.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            (
                "after",
                "website/static/src/scss/primary_variables.scss",
                "fur_theme/static/src/scss/primary_variables.scss",
            ),
        ],
        "web.assets_frontend": [
            "fur_theme/static/src/scss/fonts.scss",
            "fur_theme/static/src/scss/fur_common.scss",
            "fur_theme/static/src/scss/fur_header.scss",
            "fur_theme/static/src/scss/fur_footer.scss",
            "fur_theme/static/src/scss/fur_home.scss",
            "fur_theme/static/src/scss/fur_shop.scss",
            "fur_theme/static/src/scss/fur_product.scss",
            "fur_theme/static/src/scss/fur_checkout.scss",
            "fur_theme/static/src/scss/fur_projects.scss",
            "fur_theme/static/src/js/product_card.js",
            "fur_theme/static/src/js/product_sticky_buy.js",
            "fur_theme/static/src/js/search_suggest.js",
        ],
        "web.assets_tests": [
            "fur_theme/static/tests/tours/**/*",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}
