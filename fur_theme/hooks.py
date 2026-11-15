# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# The Fur shop grid is designed for 4 cards per row (see fur_shop.scss); it is
# also Odoo 16's default grid, so the two hooks below change nothing there.
FUR_SHOP_LAYOUT = {"shop_ppr": 4, "shop_ppg": 20}
ODOO_SHOP_LAYOUT = {"shop_ppr": 4, "shop_ppg": 20}


def enable_unaccent(cr):
    """Accent-insensitive search ("ghe xoay" finds "Ghế Xoay"): Odoo uses
    PostgreSQL's unaccent when the database has it (after a restart)."""
    try:
        with cr.savepoint():
            cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    except Exception as error:  # needs a database user allowed to create extensions
        _logger.warning("Fur: unaccent extension not created (%s): searches stay accent-sensitive", error)


def post_init_hook(cr, registry):
    """Apply the Fur shop grid to websites still using Odoo's default grid and
    publish the payment modes of the cart page checkout."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    websites = env["website"].search(
        [("shop_ppr", "=", ODOO_SHOP_LAYOUT["shop_ppr"]), ("shop_ppg", "=", ODOO_SHOP_LAYOUT["shop_ppg"])]
    )
    websites.write(FUR_SHOP_LAYOUT)
    enable_unaccent(cr)
    env["website"]._fur_setup_product_page()
    env["payment.provider"]._fur_setup_checkout_providers()
    # inventory categories for the shop categories that already exist
    env["product.public.category"]._fur_sync_product_categories()
    env["product.template"].search([])._fur_set_product_category()
    # products without a price show a "Contact Us" button instead of add-to-cart
    env["website"].search([]).write({"prevent_zero_price_sale": True})


def uninstall_hook(cr, registry):
    """Give websites back Odoo's default grid if they still use Fur's."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    websites = env["website"].search(
        [("shop_ppr", "=", FUR_SHOP_LAYOUT["shop_ppr"]), ("shop_ppg", "=", FUR_SHOP_LAYOUT["shop_ppg"])]
    )
    websites.write(ODOO_SHOP_LAYOUT)
