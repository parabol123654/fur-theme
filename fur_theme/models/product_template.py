# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import remove_accents


class ProductTemplate(models.Model):
    _inherit = "product.template"

    fur_featured = fields.Boolean(
        string="Featured on Homepage",
        help="Show this product in the 'Featured products' section of the Fur homepage.",
    )
    # Odoo 15 has no "compare to" price (website_sale adds this field in 16.0)
    compare_list_price = fields.Float(
        string="Compare to Price",
        digits="Product Price",
        help="Shown crossed out next to the sales price on the website when it is higher.",
    )

    # ------------------------------------------------------------ prices
    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False,
                              parent_combination=False, only_template=False):
        """The "compare to" price is shown the way Odoo 15 shows a pricelist
        discount: it becomes the crossed-out ``list_price`` of the combination
        when it is higher than the price and the pricelist shows no discount
        of its own."""
        info = super()._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template,
        )
        if not self.compare_list_price or info.get("has_discounted_price"):
            return info
        website = self.env["website"].get_current_website() if self.env.context.get("website_id") else False
        pricelist = pricelist or (website and website.get_current_pricelist())
        currency = pricelist.currency_id if pricelist else self.currency_id
        compare = self.compare_list_price
        if currency != self.currency_id:
            company = (website and website.company_id) or self.env.company
            compare = self.currency_id._convert(compare, currency, company, fields.Date.today())
        if website:
            # same tax display (B2B / B2C) as the price, see website_sale
            product = self.env["product.product"].browse(info["product_id"]) or self
            partner = self.env.user.partner_id
            tax_display = (
                self.user_has_groups("account.group_show_line_subtotals_tax_excluded")
                and "total_excluded" or "total_included"
            )
            fpos = self.env["account.fiscal.position"].sudo().get_fiscal_position(partner.id)
            product_taxes = product.sudo().taxes_id.filtered(lambda tax: tax.company_id == website.company_id)
            taxes = fpos.map_tax(product_taxes)
            compare = self.env["account.tax"]._fix_tax_included_price_company(
                compare, product_taxes, taxes, website.company_id
            )
            compare = taxes.compute_all(compare, currency, 1, product, partner)[tax_display]
        if currency.compare_amounts(compare, info["price"]) == 1:
            info.update(fur_list_price=info["list_price"], list_price=compare, has_discounted_price=True)
        return info

    def get_google_analytics_data(self, combination):
        # analytics keep the real list price, not the "compare to" price
        if "fur_list_price" in combination:
            combination = dict(combination, list_price=combination["fur_list_price"])
        return super().get_google_analytics_data(combination)

    def _website_show_quick_add(self):
        """A product can be added to the cart from a card: products without a
        price show "Contact" instead (Odoo 15 has no such website option)."""
        self.ensure_one()
        return bool(self.sale_ok and self.list_price and self._is_add_to_cart_possible())

    def _fur_price_on_request(self):
        """No price: the product page shows a contact button instead of the
        price and the cart button."""
        self.ensure_one()
        return not self.list_price

    # ------------------------------------------------------------ search
    @api.model
    def _search_get_detail(self, website, order, options):
        """The shop search looks in the product name and code only: every
        word must be in them. Odoo also looks in the descriptions, which made
        a full product name match dozens of products, and slowly."""
        detail = super()._search_get_detail(website, order, options)
        detail["search_fields"] = ["name", "default_code", "product_variant_ids.default_code"]
        return detail

    @api.model
    def _search_build_domain(self, domain_list, search, fields, extra=None):
        """Every word of a search must match (Odoo 15 does that); a search of
        3 words or more that no product fully matches (a typo) falls back to
        the products matching all the words but one."""
        domain = super()._search_build_domain(domain_list, search, fields, extra)
        words = self._fur_search_words(search)
        if len(words) <= 2 or self.search_count(domain):
            return domain
        partial = [
            super(ProductTemplate, self)._search_build_domain(
                domain_list, " ".join(words[:index] + words[index + 1:]), fields, extra
            )
            for index in range(len(words))
        ]
        return expression.OR(partial)

    @api.model
    def _fur_search_words(self, text):
        return [word for word in (text or "").split() if word]

    @api.model
    def _fur_search_domain(self, text, website):
        domain = website.sale_product_domain()
        for word in self._fur_search_words(text):
            domain = expression.AND([domain, [
                "|", ("name", "ilike", word), ("product_variant_ids.default_code", "ilike", word),
            ]])
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
            name = re.sub(r"\s*[-–]\s*%s\s*$" % re.escape(code), "", name, flags=re.IGNORECASE)
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
            copies = template.public_categ_ids.mapped("fur_product_categ_id")
            deepest = template.public_categ_ids.sorted(lambda c: len(c.parent_path or ""), reverse=True)
            target = deepest.mapped("fur_product_categ_id")[:1]
            if target and template.categ_id not in copies:
                template.categ_id = target
