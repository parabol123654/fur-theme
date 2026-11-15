# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import re
from collections import Counter

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import remove_accents
from odoo.tools.sql import escape_psql


class ProductTemplate(models.Model):
    _inherit = "product.template"

    fur_featured = fields.Boolean(
        string="Featured on Homepage",
        help="Show this product in the 'Featured products' section of the Fur homepage.",
    )

    # ------------------------------------------------------------ search
    def _get_website_sale_search_fields(self, search_in_description=True):
        """The shop search looks in the product name and code only: every
        word must be in them. Odoo also looks in
        the descriptions, which made a full
        product name match dozens of products, and slowly."""
        return ["name", "default_code", "product_variant_ids.default_code"]

    @api.model
    def _search_get_detail(self, website, order, options):
        # Odoo 18 has no hook for the search fields
        detail = super()._search_get_detail(website, order, options)
        detail["search_fields"] = self._get_website_sale_search_fields()
        return detail

    @api.model
    def _search_build_domain(self, domain_list, search, fields, extra=None):
        """Every word of a search must match, as Odoo 18 does; a partial
        match (all the words but one, but two from 5 words: what Odoo 20
        accepts) is kept for a 3+ word search no product fully matches (a
        typo)."""
        domain = super()._search_build_domain(domain_list, search, fields, extra)
        words = self._fur_search_words(search)
        if len(words) <= 2 or self.search_count(domain, limit=1):
            return domain
        domain = expression.AND(domain_list)
        matches = Counter()
        for word in words:
            subdomains = [[(field, "ilike", escape_psql(word))] for field in fields]
            if extra:
                subdomains.append(extra(self.env, word))
            matches.update(self.search(expression.AND([domain, expression.OR(subdomains)])).ids)
        threshold = len(words) - (1 if len(words) < 5 else 2)
        return expression.AND([domain, [("id", "in", [id_ for id_, count in matches.items() if count >= threshold])]])

    @api.model
    def _fur_search_words(self, text):
        return [word for word in (text or "").split() if word]

    @api.model
    def _fur_search_domain(self, text, website):
        domain = website.sale_product_domain()
        for word in self._fur_search_words(text):
            domain = expression.AND([domain, expression.OR([
                [(field, "ilike", word)] for field in self._get_website_sale_search_fields()
            ])])
        return domain

    @api.model
    def _fur_search_rank(self, text):
        """Sort key of a product for a search text: same code first, then the
        codes starting with it, then the
        names holding the most searched words as whole words, the whole text
        (earliest first), then shorter names. Accents are ignored."""
        def plain(value):
            return remove_accents((value or "").lower().replace("đ", "d"))

        words = [plain(word) for word in self._fur_search_words(text)]
        needle = " ".join(words)

        def rank(product):
            name, code = plain(product.name), plain(product.default_code)
            tokens = set(re.findall(r"\w+", name))
            position = name.find(needle)
            return (
                code != needle,
                not (code and code.startswith(needle)),
                -sum(word in tokens for word in words),
                position < 0,
                max(position, 0),
                len(name),
            )
        return rank

    @api.model
    def _fur_search_suggest(self, text, website, limit=8):
        """Products for the header search dropdown, best matches first."""
        if len((text or "").strip()) < 2:
            return self.browse(), 0
        domain = self._fur_search_domain(text, website)
        products = self.search(domain, limit=200)
        return products.sorted(self._fur_search_rank(text))[:limit], self.search_count(domain)

    def _fur_short_name(self):
        """Name without the trailing " - <reference>" the catalogue appends
        ("Ghế Xoay Lưng Lưới - GX92" -> "Ghế Xoay Lưng Lưới"): the reference is
        shown on its own line, so a clamped name keeps its meaningful part."""
        self.ensure_one()
        name = self.name or ""
        code = (self.default_code or "").strip()
        if code:
            name = re.sub(rf"\s*[-–]\s*{re.escape(code)}\s*$", "", name, flags=re.IGNORECASE)
        return name or self.name

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._fur_set_product_category()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if "public_categ_ids" in vals and "categ_id" not in vals:
            self._fur_set_product_category()
        return res

    def _fur_set_product_category(self):
        """Give each product the inventory copy of its deepest website category,
        unless it already has the copy of one of its website categories."""
        for template in self.sudo().filtered("public_categ_ids"):
            copies = template.public_categ_ids.fur_product_categ_id
            deepest = template.public_categ_ids.sorted(lambda c: len(c.parent_path or ""), reverse=True)
            target = deepest.fur_product_categ_id[:1]
            if target and template.categ_id not in copies:
                template.categ_id = target
