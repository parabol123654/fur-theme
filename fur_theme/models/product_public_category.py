# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slug


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    fur_show_on_home = fields.Boolean(
        string="Show on Homepage",
        help="Show this category in the 'Product categories' grid of the Fur homepage.",
    )
    fur_product_categ_id = fields.Many2one(
        "product.category",
        string="Inventory Category",
        help="Product category (inventory, accounting) copied from this website category and "
        "given to its products.",
        index=True,
        ondelete="set null",
        copy=False,
    )
    # Odoo 15 has no URL field on the website categories (later versions do)
    website_url = fields.Char(
        string="Website URL", compute="_compute_website_url", help="URL of the category page of the shop."
    )

    @api.depends("name")
    def _compute_website_url(self):
        for category in self:
            category.website_url = "/shop/category/%s" % slug(category) if category.id else "#"

    @api.model_create_multi
    def create(self, vals_list):
        categories = super().create(vals_list)
        categories._fur_sync_product_categories()
        return categories

    def write(self, vals):
        res = super().write(vals)
        if {"name", "parent_id"} & set(vals):
            self._fur_sync_product_categories()
        return res

    def _fur_sync_product_categories(self):
        """Copy the website categories as product categories (same tree, English
        names: product categories are not translatable in Odoo 15); idempotent.
        Empty recordset: all of them."""
        ProductCategory = self.env["product.category"].sudo()
        categories = (self.sudo() or self.sudo().search([])).with_context(lang="en_US")
        # parents first
        for categ in categories.sorted(lambda c: (len(c.parent_path or ""), c.sequence, c.id)):
            parent = categ.parent_id.fur_product_categ_id
            target = categ.fur_product_categ_id
            if not target:
                target = ProductCategory.create({"name": categ.name, "parent_id": parent.id})
                categ.fur_product_categ_id = target
            elif target.parent_id != parent:
                target.parent_id = parent
            if target.name != categ.name:
                target.name = categ.name
        return categories.mapped("fur_product_categ_id")
