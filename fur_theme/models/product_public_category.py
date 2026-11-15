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
        index="btree_not_null",
        ondelete="set null",
        copy=False,
    )

    website_url = fields.Char(
        string="Website URL",
        compute="_compute_website_url",
        help="Shop page of the category.",
    )

    @api.depends("name")
    def _compute_website_url(self):
        for category in self:
            category.website_url = f"/shop/category/{slug(category)}" if category.id else False

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
        """Copy the website categories as product categories (same tree, names
        in every installed language); idempotent. Empty recordset: all of them."""
        ProductCategory = self.env["product.category"].sudo()
        categories = self.sudo() or self.sudo().search([])
        languages = [code for code, _name in self.env["res.lang"].get_installed()]
        # Odoo 17 does not translate product category names: they take the
        # name in the main language of the (first) website
        translated = bool(ProductCategory._fields["name"].translate)
        main_lang = self.env["website"].sudo().search([], limit=1).default_lang_id.code or "en_US"
        # parents first
        for categ in categories.sorted(lambda c: (len(c.parent_path or ""), c.sequence, c.id)):
            parent = categ.parent_id.fur_product_categ_id
            target = categ.fur_product_categ_id
            if not target:
                target = ProductCategory.with_context(lang="en_US").create({
                    "name": categ.with_context(lang="en_US").name, "parent_id": parent.id,
                })
                categ.with_context(lang="en_US").fur_product_categ_id = target
            elif target.parent_id != parent:
                target.parent_id = parent
            if not translated:
                name = categ.with_context(lang=main_lang).name
                if target.name != name:
                    target.name = name
                continue
            names = {lang: categ.with_context(lang=lang).name for lang in languages}
            if any(target.with_context(lang=lang).name != name for lang, name in names.items()):
                target.update_field_translations("name", names)
        return categories.fur_product_categ_id
