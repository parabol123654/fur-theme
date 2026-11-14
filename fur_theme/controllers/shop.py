# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from urllib.parse import urlencode

from odoo import http
from odoo.http import request
from odoo.tools import format_amount

from odoo.addons.website_sale.controllers.main import WebsiteSale


class FurShop(WebsiteSale):

    def _shop_lookup_products(self, options, post, search, website):
        fuzzy_search_term, product_count, search_result = super()._shop_lookup_products(
            options, post, search, website
        )
        # a search without a chosen sort: best matches first
        if search and not post.get("order"):
            search_result = search_result.sorted(
                request.env["product.template"]._fur_search_rank(fuzzy_search_term or search)
            )
        return fuzzy_search_term, product_count, search_result


class FurSearch(http.Controller):

    @http.route("/fur/search/suggest", type="jsonrpc", auth="public", website=True, readonly=True)
    def suggest(self, term="", limit=8):
        """Products of the header search dropdown."""
        website = request.env.website
        Product = request.env["product.template"]
        products, count = Product._fur_search_suggest(term, website, limit=min(int(limit or 8), 20))
        prices = website._fur_product_prices(products)
        currency = website.currency_id
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
                "price": format_amount(request.env, amount, currency) if amount else request.env._("Contact"),
                "base_price": format_amount(request.env, base, currency) if base and base > amount else "",
            })
        return {
            "items": items,
            "count": count,
            "more_url": request.env["ir.http"]._url_for("/shop") + "?" + urlencode({"search": term}),
            "more_label": request.env._("See all %(count)s results", count=count),
            "empty_label": request.env._("No product found"),
        }
