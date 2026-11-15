# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import base64
import logging
import re

from odoo import fields, models
from odoo.http import request
from odoo.tools import file_open

from odoo.addons.http_routing.models.ir_http import unslug_url

_logger = logging.getLogger(__name__)

# Sample contacts of the demo shop (demo data only).
DEMO_HOTLINE = "+1 555 0100 200"
DEMO_EMAIL = "hello@example.com"

# Menu URL of a shop category: /shop/category/<slug>-<id>, optionally
# language-prefixed and with a query string.
_CATEGORY_URL = re.compile(r"/shop/category/(?:[^/?#]*-)?(\d+)/?(?:[?#]|$)")


class Website(models.Model):
    _inherit = "website"

    fur_brand_name = fields.Char(
        string="Brand Name",
        translate=True,
        help="Shown next to the logo when the website has none, in the homepage slides and on "
        "the thank-you page. Empty: the website name.",
    )
    fur_hotline = fields.Char(string="Hotline", help="Shown in the header menu and footer.")
    fur_zalo = fields.Char(
        string="Zalo",
        help="Phone number or zalo.me link of the floating Zalo button. Empty: no Zalo button.",
    )
    fur_zalo_2 = fields.Char(
        string="Zalo (2nd)",
        help="Phone number or zalo.me link of a second floating Zalo button (the number itself is not shown).",
    )
    fur_whatsapp = fields.Char(
        string="WhatsApp",
        help="Phone number in international format (e.g. +1 555 0100 200) or wa.me link of the "
        "floating WhatsApp button. Empty: no WhatsApp button.",
    )
    fur_footer_logo = fields.Image(
        string="Footer Logo",
        max_width=1024,
        max_height=512,
        help="Logo version for the dark footer (light text). Empty: the website logo on a white card.",
    )
    fur_messenger = fields.Char(string="Messenger", help="Facebook / Messenger link of the floating Messenger button.")
    fur_opening_hours = fields.Char(string="Opening Hours", help="Shown in the footer.")
    fur_buy_guide = fields.Html(
        string="Buying & Payment Guide",
        translate=True,
        sanitize_attributes=False,
        default=lambda self: self._fur_default_buy_guide(),
        help="Second tab of the product page. Can also be edited on the page with the website builder.",
    )
    fur_enabled = fields.Boolean(
        string="Use Fur Theme",
        default=True,
        help="Use the Fur header, footer, homepage and shop layout on this website. "
        "Untick it to give this website back Odoo's own layout.",
    )

    # ------------------------------------------------------------------
    # Homepage data helpers (called from QWeb, so they must stay cheap
    # and must never leak unpublished records to visitors).
    # ------------------------------------------------------------------

    def _fur_home_categories(self, limit=8):
        """Categories flagged for the homepage grid, falling back to root ones."""
        self.ensure_one()
        Category = self.env["product.public.category"]
        domain = self.website_domain()
        categories = Category.search(domain + [("fur_show_on_home", "=", True)], limit=limit)
        if not categories:
            categories = Category.search(domain + [("parent_id", "=", False)], limit=limit)
        return categories

    def _fur_featured_products(self, limit=8):
        """Published sellable products flagged as featured (newest first as fallback)."""
        self.ensure_one()
        Product = self.env["product.template"]
        domain = self.sale_product_domain()
        products = Product.search(
            domain + [("fur_featured", "=", True)], order="website_sequence, id", limit=limit
        )
        if not products:
            products = Product.search(domain, order="create_date desc, id desc", limit=limit)
        return products

    def _fur_home_sections(self, limit=8):
        """Homepage blocks, one per homepage category: its sub-categories (the
        pills of the block head) and its first published products."""
        self.ensure_one()
        Product = self.env["product.template"]
        sections = []
        for categ in self._fur_home_categories():
            products = Product.search(
                self.sale_product_domain() + [("public_categ_ids", "child_of", categ.id)],
                order="fur_featured desc, website_sequence, id desc", limit=limit,
            )
            if products:
                sections.append({"category": categ, "children": categ.child_id, "products": products})
        return sections

    def _fur_home_section_products(self, sections):
        products = self.env["product.template"]
        for section in sections:
            products |= section["products"]
        return products

    def _fur_featured_projects(self, limit=3):
        self.ensure_one()
        Project = self.env["fur.project"]
        domain = self.website_domain() + [("is_published", "=", True)]
        projects = Project.search(domain + [("is_featured", "=", True)], limit=limit)
        if not projects:
            projects = Project.search(domain, limit=limit)
        return projects

    def _fur_category_images(self, categories):
        """Record to take each category card picture from: the category itself
        when it has an image, else its first published product (from the
        category or a sub-category).

        Image presence is read with ``bin_size`` (no picture payload) and only
        categories without a picture cost a (limit=1) product search.

        :return: dict {category id: record with an ``image_*`` field}
        """
        self.ensure_one()
        holders = {}
        Product = self.env["product.template"]
        for category in categories.with_context(bin_size=True):
            if category.image_128:
                holders[category.id] = category
                continue
            product = Product.search(
                self.sale_product_domain() + [("public_categ_ids", "child_of", category.id)],
                order="website_sequence, id",
                limit=1,
            )
            holders[category.id] = product or category
        return holders

    def _fur_product_prices(self, products):
        """Price values (``price_reduce``, optional crossed-out ``base_price``)
        per template id, computed like the /shop grid does."""
        self.ensure_one()
        prices = {}
        for product in products.with_context(website_id=self.id):
            info = product._get_combination_info(only_template=True)
            prices[product.id] = {"price_reduce": info["price"]}
            if info["has_discounted_price"]:
                prices[product.id]["base_price"] = info["list_price"]
        return prices

    def _fur_has_wishlist(self):
        """The wishlist is an optional module in Odoo 14 (website_sale_wishlist):
        the heart buttons only show when it is installed and switched on."""
        self.ensure_one()
        return "product.wishlist" in self.env and self.is_view_active("website_sale_wishlist.add_to_wishlist")

    def _fur_wishlist_variant_ids(self):
        """Variant ids in the visitor's wishlist, fetched once per page."""
        self.ensure_one()
        if not request or not self._fur_has_wishlist():
            return set()
        return set(self.env["product.wishlist"].current().mapped("product_id").ids)

    def _fur_brand(self):
        """Brand name of the website: the theme setting, else the website name."""
        self.ensure_one()
        return self.fur_brand_name or self.name or self.company_id.name or ""

    def _fur_default_buy_guide(self):
        return """
<h3>How to order</h3>
<ol>
<li>Choose the product, its options and the quantity, then click <b>Add to cart</b> (or <b>Buy now</b> to check out straight away).</li>
<li>Click the cart icon at the top right to review your order.</li>
<li>Fill in your name, phone number and delivery address under the cart, choose a payment method and confirm the order.</li>
<li>We call you to confirm the order and schedule the delivery and installation.</li>
</ol>
<p>Need advice before ordering? Call our hotline or use the chat buttons on the right of the screen.</p>
<h3>How to pay</h3>
<ul>
<li><b>Bank transfer:</b> the bank account and the payment reference are shown as soon as the order is placed, and in the order confirmation email.</li>
<li><b>Cash on delivery:</b> pay the delivery staff when you receive the goods.</li>
</ul>
"""

    def _fur_setup_shop_cards(self):
        """Shop cards show a cart button (Odoo 14 option "Add to Cart" of the
        shop page, off by default)."""
        view = self.env.ref("website_sale.products_add_to_cart", raise_if_not_found=False)
        if view and not view.active:
            view.active = True
        for website in self:
            copy = website.with_context(website_id=website.id).viewref(
                "website_sale.products_add_to_cart", raise_if_not_found=False
            )
            if copy and not copy.active:
                copy.active = True

    def _fur_sync_view_copies(self):
        """Website copies of Fur pages (made when a page is edited with the
        website builder) that were not changed: they get the translations
        of the module's page again (after each load of the translations)."""
        View = self.env["ir.ui.view"].sudo().with_context(active_test=False, lang=None)
        Translation = self.env["ir.translation"].sudo()
        terms_domain = [("type", "=", "model_terms"), ("name", "=", "ir.ui.view,arch_db")]
        updated = 0
        for copy in View.search([("key", "=like", "fur_theme.%"), ("website_id", "!=", False)]):
            generic = View.search([("key", "=", copy.key), ("website_id", "=", False)], limit=1)
            if not generic or generic.arch_db != copy.arch_db:
                continue
            existing = {
                (term.lang, term.src): term
                for term in Translation.search(terms_domain + [("res_id", "=", copy.id)])
            }
            changed = False
            for term in Translation.search(terms_domain + [("res_id", "=", generic.id)]):
                if not term.value:
                    continue
                mine = existing.get((term.lang, term.src))
                if not mine:
                    Translation.create({
                        "type": "model_terms", "name": "ir.ui.view,arch_db", "res_id": copy.id,
                        "lang": term.lang, "src": term.src, "value": term.value, "state": "translated",
                    })
                    changed = True
                elif mine.value != term.value:
                    mine.write({"value": term.value, "state": "translated"})
                    changed = True
            updated += changed
        if updated:
            View.invalidate_cache(["arch_db", "arch"])
            _logger.info("Fur: translations of %s website page copies updated", updated)
        return True

    def _fur_has_terms_page(self):
        """The shop's terms page (/shop/terms) is linked when the terms &
        conditions are switched on (Invoicing settings). Odoo 14 has no
        /terms page of the company (later versions do)."""
        self.ensure_one()
        return (
            str(self.env["ir.config_parameter"].sudo().get_param("account.use_invoice_terms")).lower()
            not in ("false", "0", "", "none")
        )

    def _fur_hotline(self):
        self.ensure_one()
        return self.fur_hotline or self.company_id.phone or ""

    def _fur_tel_url(self):
        """tel: link of the hotline, without the spaces people type in it."""
        digits = re.sub(r"[^\d+]", "", self._fur_hotline())
        return "tel:%s" % digits if digits else ""

    @staticmethod
    def _fur_zalo_link(value):
        """A pasted link is kept, a phone number becomes https://zalo.me/<number>."""
        value = (value or "").strip()
        if value.startswith(("http://", "https://")):
            return value
        digits = re.sub(r"\D", "", value)
        return "https://zalo.me/%s" % digits if digits else ""

    def _fur_zalo_url(self):
        """Zalo chat link of the Zalo field."""
        self.ensure_one()
        return self._fur_zalo_link(self.fur_zalo)

    def _fur_zalo_urls(self):
        """Links of the floating Zalo buttons (main one first, no duplicate)."""
        self.ensure_one()
        urls = [self._fur_zalo_url(), self._fur_zalo_link(self.fur_zalo_2)]
        return list(dict.fromkeys(url for url in urls if url))

    @staticmethod
    def _fur_whatsapp_link(value):
        """A pasted link is kept, a phone number becomes https://wa.me/<number>
        (international format: the leading + or 00 is dropped)."""
        value = (value or "").strip()
        if value.startswith(("http://", "https://")):
            return value
        digits = re.sub(r"\D", "", value)
        if digits.startswith("00"):
            digits = digits[2:]
        return "https://wa.me/%s" % digits if digits else ""

    def _fur_whatsapp_url(self):
        """WhatsApp chat link of the WhatsApp field."""
        self.ensure_one()
        return self._fur_whatsapp_link(self.fur_whatsapp)

    def _fur_menu_categories(self, menu):
        """Sub-categories shown under a menu entry that links to a shop
        category (/shop/category/<slug>-<id>), in the category order."""
        self.ensure_one()
        Category = self.env["product.public.category"]
        match = _CATEGORY_URL.search(menu.url or "")
        if not match:
            return Category
        return Category.search(
            self.website_domain() + [("parent_id", "=", int(match.group(1)))],
            order="sequence, id",
        )

    def _fur_menu_is_active(self, menu):
        """The menu entry links to the current page (as website.submenu does)."""
        url = menu.clean_url()
        return bool(request and url and unslug_url(request.httprequest.path) == unslug_url(url))

    def _fur_header_languages(self, languages):
        """Languages for the flag pills: default language first, hidden when
        the website has a single language. ``languages``: the frontend
        languages of the page, as (code, url_code, name, active, flag_image_url)
        tuples (``res.lang.get_available``)."""
        self.ensure_one()
        if len(languages) < 2:
            return []
        default = self.default_lang_id.code
        return sorted(languages, key=lambda lg: (lg[0] != default, lg[2]))

    def _fur_flag_url(self, lang):
        """Flag picture of a frontend language (``lang`` is one of the tuples
        of ``_fur_header_languages``): the theme's own round flags for
        Vietnamese and English (British flag), Odoo's flag for any other
        language."""
        code = lang[0] or ""
        if code.startswith("vi"):
            return "/fur_theme/static/src/img/flag_vn.svg"
        if code.startswith("en"):
            return "/fur_theme/static/src/img/flag_gb.svg"
        return lang[4]

    # ------------------------------------------------------------------
    # Demo setup (called from demo/fur_website_demo.xml only)
    # ------------------------------------------------------------------

    def _fur_setup_demo(self):
        """Turn the default website into the demo furniture shop: Fur menu,
        sample contacts, logos."""
        website = self[:1] or self.env.ref("website.default_website")
        company = website.company_id

        website.write({
            "name": "Fur Furniture",
            "fur_brand_name": "Fur",
            "fur_hotline": DEMO_HOTLINE,
            "fur_whatsapp": DEMO_HOTLINE,
            "fur_opening_hours": "Mon - Sun: 8:00 - 20:00",
            "shop_ppr": 4,
            "shop_ppg": 20,
        })
        if not company.email:
            company.email = DEMO_EMAIL
        if not company.phone:
            company.phone = DEMO_HOTLINE

        for field, path in (
            ("logo", "fur_theme/static/src/img/logo_on_yellow.svg"),
            ("fur_footer_logo", "fur_theme/static/src/img/logo_on_dark.svg"),
            ("favicon", "fur_theme/static/src/img/favicon.png"),
        ):
            with file_open(path, "rb") as image:
                website[field] = base64.b64encode(image.read())
        demo_categories = self.env["product.public.category"].browse(
            self.env["ir.model.data"].search([
                ("model", "=", "product.public.category"), ("module", "=", "fur_theme"),
            ]).mapped("res_id")
        ).filtered(lambda c: not c.parent_id).sorted(lambda c: (c.sequence, c.id))
        website._fur_setup_menu(demo_categories)
        # Only the demo categories in the menu: other modules' demo categories
        # (website_sale's Desks, Boxes...) are dropped from the main menu.
        demo_urls = {"/", *demo_categories.mapped("website_url")}
        website.menu_id.child_id.filtered(
            lambda m: m.url and m.url.startswith("/shop/category/") and m.url not in demo_urls
        ).unlink()

        # Keep the demo shop about furniture: unpublish other modules' demo products.
        fur_ids = self.env["ir.model.data"].search(
            [("model", "=", "product.template"), ("module", "=", "fur_theme")]
        ).mapped("res_id")
        self.env["product.template"].search(
            [("id", "not in", fur_ids), ("is_published", "=", True)]
        ).is_published = False
        return True

    def _fur_setup_menu(self, categories=None):
        """Main menu = Home + the top-level shop categories; each category
        entry drops its sub-categories down on hover. Projects and Contact are
        links of the header top bar. Other entries of the main menu are kept
        after them. ``categories``: the top-level categories to list (default:
        all top-level categories of the website)."""
        languages = [code for code, _name in self.env["res.lang"].get_installed()]
        if "en_US" not in languages:  # the source terms, on a database created in another language
            languages.append("en_US")
        for website in self:
            Menu = self.env["website.menu"]
            root = website.menu_id
            home = {"en_US": "Home", "vi_VN": "Trang chủ"}
            wanted = [({lang: home.get(lang, home["en_US"]) for lang in languages}, "/")] + [
                ({lang: categ.with_context(lang=lang).name for lang in languages}, categ.website_url)
                for categ in (categories or self.env["product.public.category"].search(
                    website.website_domain() + [("parent_id", "=", False)], order="sequence, id"
                ))
            ]
            existing = {menu.url: menu for menu in root.child_id}
            for sequence, (names, url) in enumerate(wanted, start=1):
                menu = existing.pop(url, None)
                if menu:
                    menu.write({"sequence": sequence})
                else:
                    menu = Menu.with_context(lang="en_US").create({
                        "name": names.get("en_US") or next(iter(names.values())), "url": url, "parent_id": root.id,
                        "website_id": website.id, "sequence": sequence,
                    })
                # English (the source term) last: on a database with a single
                # language Odoo 14 writes a translation to the source term too
                for lang in sorted(names, key=lambda code: code == "en_US"):
                    if menu.with_context(lang=lang).name != names[lang]:
                        menu.with_context(lang=lang).name = names[lang]
            for sequence, menu in enumerate(existing.values(), start=len(wanted) + 1):
                menu.sequence = sequence

    def _fur_related_products(self, product, limit=4):
        """Alternative products, completed with products of the same category."""
        self.ensure_one()
        domain = self.sale_product_domain() + [("id", "!=", product.id)]
        related = product.alternative_product_ids.filtered_domain(domain)[:limit]
        if len(related) < limit and product.public_categ_ids:
            related |= self.env["product.template"].search(
                domain + [
                    ("id", "not in", related.ids),
                    ("public_categ_ids", "in", product.public_categ_ids.ids),
                ],
                order="website_sequence, id",
                limit=limit - len(related),
            )
        return related
