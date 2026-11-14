# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import logging

_logger = logging.getLogger(__name__)

# The Fur shop grid is designed for 4 cards per row (see fur_shop.scss).
FUR_SHOP_LAYOUT = {"shop_ppr": 4, "shop_ppg": 20}
ODOO_SHOP_LAYOUT = {"shop_ppr": 3, "shop_ppg": 21}


def enable_unaccent(cr):
    """Accent-insensitive search ("ghe xoay" finds "Ghế Xoay"): Odoo uses
    PostgreSQL's unaccent when the database has it (after a restart)."""
    try:
        with cr.savepoint():
            cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
            # as Odoo does for a database created with --unaccent
            # (odoo/modules/db.py): its trigram indexes need an immutable
            # unaccent, the accent rules never change during a database's life
            cr.execute("ALTER FUNCTION unaccent(text) IMMUTABLE")
    except Exception as error:  # needs a database user allowed to create extensions
        _logger.warning("Fur: unaccent extension not created (%s): searches stay accent-sensitive", error)


def post_init_hook(env):
    """Apply the Fur shop grid to websites still using Odoo's default grid and
    publish the payment modes of the cart page checkout."""
    websites = env["website"].search(
        [("shop_ppr", "=", ODOO_SHOP_LAYOUT["shop_ppr"]), ("shop_ppg", "=", ODOO_SHOP_LAYOUT["shop_ppg"])]
    )
    websites.write(FUR_SHOP_LAYOUT)
    enable_unaccent(env.cr)
    env["website"].search([])._fur_setup_shop_cards()
    env["payment.provider"]._fur_setup_checkout_providers()
    # inventory categories for the shop categories that already exist
    env["product.public.category"]._fur_sync_product_categories()
    env["product.template"].search([])._fur_set_product_category()
    # products without a price show "Contact" instead of an add-to-cart button
    env["website"].search([]).write({"prevent_sale": True, "prevent_sale_for": "zero_price"})


def uninstall_hook(env):
    """Give websites back Odoo's default grid if they still use Fur's."""
    websites = env["website"].search(
        [("shop_ppr", "=", FUR_SHOP_LAYOUT["shop_ppr"]), ("shop_ppg", "=", FUR_SHOP_LAYOUT["shop_ppg"])]
    )
    websites.write(ODOO_SHOP_LAYOUT)
