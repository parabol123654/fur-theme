# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from werkzeug.urls import url_encode

from odoo import _, http
from odoo.http import request
from odoo.osv import expression
from odoo.tools import format_amount

from odoo.addons.http_routing.models.ir_http import url_for
from odoo.addons.website_sale.controllers.main import TableCompute, WebsiteSale


class FurShop(WebsiteSale):

    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        """The shop search looks in the product name and code only: every
        word must be in them (Odoo 14 does that). Odoo also looks in the
        descriptions, which made a full product name match dozens of products,
        and slowly. A search of 3 words or more that no product fully matches
        (a typo) falls back to the products matching all the words but one."""
        domain = super()._get_search_domain(search, category, attrib_values, search_in_description=False)
        Product = request.env["product.template"]
        words = Product._fur_search_words(search)
        if len(words) <= 2 or Product.search_count(domain):
            return domain
        partial = [
            super(FurShop, self)._get_search_domain(
                " ".join(words[:index] + words[index + 1:]), category, attrib_values, search_in_description=False
            )
            for index in range(len(words))
        ]
        return expression.OR(partial)

    @http.route()
    def shop(self, page=0, category=None, search="", ppg=False, **post):
        response = super().shop(page=page, category=category, search=search, ppg=ppg, **post)
        # a search without a chosen sort: best matches first
        values = getattr(response, "qcontext", None)
        if search and not post.get("order") and values and values.get("products"):
            Product = request.env["product.template"].with_context(bin_size=True)
            # Odoo 14 does not keep the whole result of the search: read it again
            search_product = Product.search(
                self._get_search_domain(search, values["category"], values["attrib_values"])
            )
            ranked = search_product.sorted(Product._fur_search_rank(values.get("search") or search))
            offset, ppg = values["pager"]["offset"], values["ppg"]
            products = ranked[offset:offset + ppg]
            values.update(
                products=products,
                bins=TableCompute().process(products, ppg, values["ppr"]),
            )
        return response


class FurSearch(http.Controller):

    @http.route("/fur/search/suggest", type="json", auth="public", website=True)
    def suggest(self, term="", limit=8):
        """Products of the header search dropdown."""
        website = request.website
        Product = request.env["product.template"]
        products, count = Product._fur_search_suggest(term, website, limit=min(int(limit or 8), 20))
        prices = website._fur_product_prices(products)
        currency = website.get_current_pricelist().currency_id
        items = []
        for product in products:
            price = prices.get(product.id, {})
            amount = price.get("price_reduce", product.list_price)
            base = price.get("base_price")
            items.append({
                "name": product._fur_short_name(),
                "code": product.default_code or "",
                "url": product.website_url,
                "image": website.image_url(product, "image_128"),
                "price": format_amount(request.env, amount, currency) if amount else _("Contact"),
                "base_price": format_amount(request.env, base, currency) if base and base > amount else "",
            })
        return {
            "items": items,
            "count": count,
            "more_url": url_for("/shop") + "?" + url_encode({"search": term}),
            "more_label": _("See all %(count)s results", count=count),
            "empty_label": _("No product found"),
        }
