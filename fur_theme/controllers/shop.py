# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from werkzeug.urls import url_encode

from odoo import _, http
from odoo.http import request
from odoo.tools import format_amount

from odoo.addons.http_routing.models.ir_http import url_for
from odoo.addons.website_sale.controllers.main import TableCompute, WebsiteSale


class FurShop(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search="", min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(
            page=page, category=category, search=search, min_price=min_price, max_price=max_price, ppg=ppg, **post
        )
        # a search without a chosen sort: best matches first
        values = getattr(response, "qcontext", None)
        if search and not post.get("order") and values and values.get("search_product"):
            ranked = values["search_product"].sorted(
                request.env["product.template"]._fur_search_rank(values.get("search") or search)
            )
            offset, ppg = values["pager"]["offset"], values["ppg"]
            products = ranked[offset:offset + ppg]
            values.update(
                search_product=ranked,
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
