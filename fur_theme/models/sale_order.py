# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    fur_customer_note = fields.Text(
        string="Customer Request", help="Written by the customer on the Fur cart page."
    )
