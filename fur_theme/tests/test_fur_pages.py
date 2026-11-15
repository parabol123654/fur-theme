# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import json

import lxml.html

from odoo.fields import Command
from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.base.models.assetsbundle import AssetsBundle

from .common import FurCommon


# The first page of a run compiles the frontend assets, which can take more
# than the 10 seconds url_open waits by default.
TIMEOUT = 120


def _get_html(self, url, expected_status=200):
    response = self.url_open(url, timeout=TIMEOUT)
    self.assertEqual(response.status_code, expected_status, url)
    return lxml.html.fromstring(response.content)


def _jsonrpc(self, url, params):
    """Call a type="json" route with the session of ``url_open``."""
    response = self.url_open(
        url, data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": params}),
        headers={"Content-Type": "application/json"}, timeout=TIMEOUT,
    )
    self.assertEqual(response.status_code, 200, url)
    result = response.json()
    self.assertNotIn("error", result, url)
    return result.get("result")


@tagged("post_install", "-at_install")
class TestFurPages(HttpCase, FurCommon):

    _get_html = _get_html

    def test_homepage_sections(self):
        html = self._get_html("/")
        self.assertTrue(html.xpath("//header[hasclass('o_fur_header')]"), "Fur header")
        self.assertTrue(html.xpath("//form[hasclass('o_fur_search')][@action='/shop']"), "Search bar")
        self.assertTrue(html.xpath("//div[@id='o_fur_hero']"), "Hero carousel")
        # Bootstrap 4 carousel: one indicator per slide, the first one active
        dots = html.xpath("//div[@id='o_fur_hero']//ol[hasclass('carousel-indicators')]/li")
        self.assertEqual(
            [(d.get("data-slide-to"), d.get("class")) for d in dots], [("0", "active"), ("1", None), ("2", None)],
            "One hero indicator per slide",
        )
        self.assertEqual(len(html.xpath("//div[@id='o_fur_hero']//div[hasclass('carousel-item')]")), 3)
        self.assertEqual(len(html.xpath("//div[hasclass('o_fur_service')]")), 4, "Service strip")
        categ_links = html.xpath("//a[hasclass('o_fur_category_card')]/@href")
        self.assertIn(self.categ_office.website_url, categ_links)
        product_names = [n.text_content().strip() for n in html.xpath("//h3[hasclass('o_fur_product_name')]")]
        self.assertIn(self.chair.name, product_names)
        self.assertNotIn(self.unpublished.name, product_names)
        blocks = html.xpath("//section[hasclass('o_fur_home_block')]")
        titles = [b.xpath("string(.//h2[hasclass('o_fur_block_title')])").strip() for b in blocks]
        self.assertIn(self.categ_office.name, titles, "One block per homepage category")
        office = blocks[titles.index(self.categ_office.name)]
        self.assertIn(self.categ_chair.website_url, office.xpath(".//ul[hasclass('o_fur_block_pills')]//a/@href"),
                      "Sub-category pills in the block head")
        self.assertLessEqual(len(office.xpath(".//article[hasclass('o_fur_product_card')]")), 8)
        self.assertTrue(office.xpath(".//button[@name='add_to_cart']"), "Quick add-to-cart in the blocks")
        project_links = html.xpath("//a[hasclass('o_fur_project_card')]/@href")
        self.assertIn(self.project.website_url, project_links)
        self.assertTrue(html.xpath("//div[hasclass('o_fur_footer')]"), "Fur footer")

    def test_contact_float_buttons(self):
        website = self.website.sudo()
        website.company_id.phone = False
        website.write({"fur_hotline": "0909 123 456", "fur_zalo": False, "fur_zalo_2": False, "fur_messenger": False})
        html = self._get_html("/")
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_phone')]/@href"), ["tel:0909123456"])
        self.assertFalse(html.xpath("//a[hasclass('o_fur_contact_zalo')]"), "No Zalo number, no Zalo button")
        self.assertFalse(html.xpath("//a[hasclass('o_fur_contact_messenger')]"))

        # Zalo numbers: Zalo buttons only, the second number is not shown
        website.write({"fur_zalo": "0909 123 456", "fur_zalo_2": "0327 191 347", "fur_messenger": "https://m.me/fur"})
        html = self._get_html("/")
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_zalo')]/@href"),
                         ["https://zalo.me/0909123456", "https://zalo.me/0327191347"])
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_phone')]/@href"), ["tel:0909123456"])
        self.assertNotIn("0327", "".join(html.xpath("//body//text()")))
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_messenger')]/@href"), ["https://m.me/fur"])
        website.write({"fur_zalo_2": False, "fur_messenger": False})

        website.fur_zalo = "https://zalo.me/g/furshop"
        html = self._get_html("/shop")
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_zalo')]/@href"), ["https://zalo.me/g/furshop"])

        website.write({"fur_hotline": False, "fur_zalo": False})
        html = self._get_html("/")
        self.assertFalse(html.xpath("//div[hasclass('o_fur_contact_float')]"), "No number, no buttons")

    def test_whatsapp_buttons(self):
        website = self.website.sudo()
        website.company_id.phone = False
        website.write({"fur_hotline": False, "fur_zalo": False, "fur_zalo_2": False, "fur_messenger": False,
                       "fur_whatsapp": "+1 (555) 0100-200"})
        html = self._get_html("/")
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_whatsapp')]/@href"), ["https://wa.me/15550100200"])
        html = self._get_html(self.chair.website_url)
        self.assertIn("https://wa.me/15550100200", html.xpath("//a[hasclass('o_fur_whatsapp_cta')]/@href"))
        website.fur_whatsapp = "0044 20 7946 0000"
        html = self._get_html("/")
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_whatsapp')]/@href"), ["https://wa.me/442079460000"])
        website.fur_whatsapp = "https://wa.me/message/ABC"
        html = self._get_html("/")
        self.assertEqual(html.xpath("//a[hasclass('o_fur_contact_whatsapp')]/@href"), ["https://wa.me/message/ABC"])
        website.fur_whatsapp = False
        html = self._get_html("/")
        self.assertFalse(html.xpath("//div[hasclass('o_fur_contact_float')]"))

    def test_footer_contacts(self):
        website = self.website.sudo()
        website.write({"fur_hotline": "+1 555 0100 200", "fur_opening_hours": "Mon - Sun: 8:00 - 20:00"})
        website.company_id.email = "fur-test@example.com"
        html = self._get_html("/")
        footer = html.xpath("//div[hasclass('o_fur_footer')]")[0]
        self.assertIn("mailto:fur-test@example.com", footer.xpath(".//a/@href"))
        self.assertIn("tel:+1 555 0100 200", footer.xpath(".//a/@href"))
        hours = " ".join(footer.xpath(".//ul[hasclass('o_fur_footer_hours')]//text()"))
        self.assertIn("Mon - Sun: 8:00 - 20:00", hours)

    def test_brand_is_the_website_logo(self):
        website = self.website.sudo()
        html = self._get_html("/")
        header_logo = html.xpath("//header//a[hasclass('o_fur_brand')]/img/@src")[0]
        self.assertIn("/web/image/website/%s/logo" % website.id, header_logo)
        self.assertTrue(html.xpath("//div[hasclass('o_fur_footer')]//a[hasclass('o_fur_brand_on_dark')]/img"),
                        "Footer logo on a light card")
        website.fur_footer_logo = self._create_image("#FFFFFF")
        html = self._get_html("/")
        footer_brand = html.xpath("//div[hasclass('o_fur_footer')]//a[hasclass('o_fur_brand')]")[0]
        self.assertIn("/fur_footer_logo", footer_brand.xpath("./img/@src")[0], "Dedicated footer logo")
        self.assertNotIn("o_fur_brand_on_dark", footer_brand.get("class"), "No white card behind it")
        website.write({"logo": False, "fur_footer_logo": False, "fur_brand_name": "Fur Test Brand"})
        html = self._get_html("/")
        self.assertEqual(html.xpath("string(//header//span[hasclass('o_fur_wordmark')])"), "Fur Test Brand",
                         "No logo: the brand name")

    def test_shop_and_category_pages(self):
        html = self._get_html("/shop")
        self.assertTrue(html.xpath("//section[hasclass('o_fur_page_banner')]"))
        self.assertTrue(html.xpath("//div[@id='wrap'][hasclass('o_fur_shop')]"))
        html = self._get_html(self.categ_office.website_url)
        title = html.xpath("//h1[hasclass('o_fur_page_title')]")[0].text_content().strip()
        self.assertEqual(title, self.categ_office.name)
        pills = [a.text_content().strip() for a in html.xpath("//div[hasclass('o_fur_subcategs')]//a")]
        self.assertIn(self.categ_chair.name, pills)
        tiles = html.xpath("//div[@id='products_grid']//*[hasclass('o_wsale_products_item_title')]")
        self.assertTrue(any(self.chair.name in t.text_content() for t in tiles))

    def test_product_page(self):
        html = self._get_html(self.chair.website_url)
        self.assertTrue(html.xpath("//ul[hasclass('o_fur_perks')]"), "Perks block")
        related = [n.text_content().strip() for n in html.xpath(
            "//section[hasclass('o_fur_related')]//h3[hasclass('o_fur_product_name')]"
        )]
        self.assertIn(self.desk.name, related)
        self.assertNotIn(self.chair.name, related)

    def test_menu_hover_panel(self):
        Menu = self.env["website.menu"].sudo()
        Menu.create({"name": "Office", "url": self.categ_office.website_url,
                     "parent_id": self.website.menu_id.id, "website_id": self.website.id})
        html = self._get_html("/")
        panel_links = html.xpath("//li[hasclass('o_fur_menu_has_panel')]//a[hasclass('o_fur_menu_panel_link')]/@href")
        self.assertIn(self.categ_chair.website_url, panel_links)
        self.assertTrue(html.xpath("//div[@id='o_fur_offcanvas']//button[hasclass('o_fur_offcanvas_toggle')]"))

    def test_product_page_layout(self):
        attribute = self.env["product.attribute"].sudo().create({
            "name": "Fur Test Colour", "display_type": "color", "create_variant": "no_variant",
            "value_ids": [Command.create({"name": "Oak", "html_color": "#C8A165"}),
                          Command.create({"name": "Walnut", "html_color": "#5C4033"})],
        })
        product = self.env["product.template"].sudo().create({
            "name": "Fur Test Table - BT01", "default_code": "BT01", "list_price": 900000,
            "website_description": "<p>Solid oak table.</p>",
            "website_published": True, "public_categ_ids": [Command.set(self.categ_chair.ids)],
            "attribute_line_ids": [Command.create({"attribute_id": attribute.id, "value_ids": [Command.set(attribute.value_ids.ids)]})],
        })
        html = self._get_html(product.website_url)
        self.assertEqual(html.xpath("string(//h1[hasclass('o_fur_pdp_title')])").strip(), "Fur Test Table")
        meta = html.xpath("string(//ul[hasclass('o_fur_pdp_meta')])")
        self.assertIn("BT01", meta)
        self.assertIn(self.categ_chair.name, meta, "Deepest category")
        self.assertEqual(len(html.xpath("//label[hasclass('css_attribute_color')]")), 2)
        self.assertEqual(len(html.xpath("//div[hasclass('o_fur_sticky_buy')]//button[hasclass('o_fur_sticky_swatch')]")), 2)
        self.assertTrue(html.xpath("//div[@id='product_details']//a[hasclass('o_we_buy_now')]"), "Buy now button")
        self.assertEqual(len(product.product_variant_ids), 1, "Colours do not create variants")
        self.assertTrue(html.xpath("//ul[hasclass('o_fur_pdp_tabs')]"), "Description / buying guide tabs")
        self.assertTrue(html.xpath("//div[@id='o_fur_tab_info']//div[@id='product_full_description']"),
                        "Description inside the first tab")
        self.assertTrue(html.xpath("//div[@id='o_fur_tab_guide']//div[hasclass('o_fur_buy_guide')]//li"),
                        "Default buying guide")
        self.assertFalse(html.xpath("//div[@id='o_product_terms_and_share']/p"), "No sample terms text")

    def test_projects_pages(self):
        html = self._get_html("/projects")
        links = html.xpath("//a[hasclass('o_fur_project_card')]/@href")
        self.assertIn(self.project.website_url, links)
        self.assertNotIn(self.project_draft.website_url, links)
        html = self._get_html("/projects?project_type=apartment")
        self.assertNotIn(self.project.website_url, html.xpath("//a[hasclass('o_fur_project_card')]/@href"))
        self._get_html("/projects?project_type=not-a-type")  # ignored, no crash
        html = self._get_html(self.project.website_url)
        self.assertIn(self.project.name, html.xpath("//h1[hasclass('o_fur_page_title')]")[0].text_content())
        used = [n.text_content().strip() for n in html.xpath("//h3[hasclass('o_fur_product_name')]")]
        self.assertIn(self.chair.name, used)
        # Unpublished or archived project: 404 for visitors, visible for designers.
        archived = self.project.sudo().copy({"name": "Fur Test Archived", "is_published": True})
        archived_url = archived.website_url
        archived.active = False
        self._get_html(self.project_draft.website_url, expected_status=404)
        self._get_html(archived_url, expected_status=404)
        new_test_user(self.env, login="fur_designer", groups="base.group_user,website.group_website_designer")
        self.authenticate("fur_designer", "fur_designer")
        self._get_html(self.project_draft.website_url)

    def test_projects_sitemap(self):
        response = self.url_open("/sitemap.xml", timeout=TIMEOUT)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.project.website_url.encode(), response.content)
        self.assertNotIn(self.project_draft.website_url.encode(), response.content)

    def test_footer_and_perks(self):
        partner = self.website.company_id.partner_id.sudo()
        partner.street = "1 Fur Test Street"
        html = self._get_html("/")
        footer = html.xpath("string(//div[hasclass('o_fur_footer')])")
        self.assertNotIn("1 Fur Test Street", footer, "Address hidden")
        self.assertIn("/delivery-installation", html.xpath("//div[hasclass('o_fur_footer')]//a/@href"))
        self.assertTrue(html.xpath("//ul[hasclass('o_fur_toplinks')]//a[@href='/projects']"))
        html = self._get_html(self.chair.website_url)
        self.assertEqual(len(html.xpath("//ul[hasclass('o_fur_perks')]/li")), 2, "Warranty and assembly only")
        self._get_html("/delivery-installation")

    def test_header_actions_and_contact_page(self):
        self.website.sudo().fur_hotline = "0909 555 123"
        html = self._get_html("/")
        actions = html.xpath("//ul[hasclass('o_fur_actions')]")[0]
        self.assertEqual(actions.xpath(".//li[hasclass('o_fur_action_hotline')]//a/@href"), ["tel:0909555123"])
        self.assertTrue(actions.xpath(".//a[@href='/shop/cart']"))
        self.assertTrue(actions.xpath(".//a[@href='/web/login']"))
        html = self._get_html("/contactus")
        self.assertTrue(html.xpath("//form[@id='contactus_form']"))
        for sample in ("s_title", "s_faq_list", "s_map"):
            self.assertFalse(html.xpath(f"//div[@id='wrap']//section[hasclass('{sample}')]"), sample)

    def test_menu_home_icon_and_flyout(self):
        self.website.sudo()._fur_setup_menu()
        sub = self.env["product.public.category"].sudo().create({
            "name": "Fur Test Gaming Chairs", "parent_id": self.categ_chair.id,
        })
        self.env["product.template"].sudo().create({
            "name": "Fur Test Gaming Chair", "list_price": 100, "is_published": True,
            "public_categ_ids": [Command.set(sub.ids)],
        })
        html = self._get_html("/")
        self.assertTrue(html.xpath("//a[hasclass('o_fur_menu_home')][@href='/']"))
        self.assertIn(sub.website_url, html.xpath("//ul[hasclass('o_fur_menu_flyout')]//a/@href"),
                      "Third level in a side list")

    def test_theme_can_be_switched_off(self):
        self.website.sudo().fur_enabled = False
        html = self._get_html("/")
        self.assertFalse(html.xpath("//header[hasclass('o_fur_header')]"))
        self.assertTrue(html.xpath("//header[@id='top']"), "Odoo's own header is back")
        self.assertFalse(html.xpath("//div[@id='o_fur_hero']"))
        self.assertEqual(len(html.xpath("//div[@id='wrap']")), 1)
        html = self._get_html("/shop")
        self.assertFalse(html.xpath("//section[hasclass('o_fur_page_banner')]"))


@tagged("post_install", "-at_install")
class TestFurCheckout(HttpCase, FurCommon):
    """One-step checkout on the cart page: payment method + contact form,
    then Odoo's payment status and confirmation pages."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["payment.acquirer"].sudo()._fur_setup_checkout_providers()
        # Odoo 15 computes the payment reference of a wire transfer with the
        # sales journal: a database without a chart of accounts has none
        company = cls.website.company_id
        Journal = cls.env["account.journal"].sudo()
        if not Journal.search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1):
            Journal.create({"name": "Fur Test Sales", "code": "FURS", "type": "sale", "company_id": company.id})
        cls.providers = {
            mode: cls.env.ref("fur_theme.payment_provider_%s" % mode)
            for mode in ("wire_transfer", "cash_on_delivery")
        }

    _jsonrpc = _jsonrpc

    def _last_order(self):
        return self.env["sale.order"].sudo().search(
            [("order_line.product_id", "in", self.chair.product_variant_ids.ids)], order="id desc", limit=1
        )

    def _add_chair_and_open_cart(self):
        self._jsonrpc("/shop/cart/update_json", {
            "product_id": self.chair.product_variant_id.id,
            "add_qty": 1,
        })
        response = self.url_open("/shop/cart", timeout=TIMEOUT)
        self.assertEqual(response.status_code, 200)
        return lxml.html.fromstring(response.content)

    def test_setup_is_idempotent(self):
        Provider = self.env["payment.acquirer"].sudo()
        Provider._fur_setup_checkout_providers()
        for mode, provider in self.providers.items():
            same_mode = Provider.search([
                ("provider", "=", "transfer"), ("custom_mode", "=", mode),
                ("company_id", "=", provider.company_id.id), ("state", "=", "enabled"),
            ])
            self.assertEqual(same_mode, provider, mode)
            self.assertTrue(provider.pre_msg, mode)
            self.assertTrue(provider.pending_msg, mode)

    def test_cart_page_form(self):
        html = self._add_chair_and_open_cart()
        form = html.xpath("//form[hasclass('o_fur_quick_checkout')]")
        self.assertTrue(form, "Checkout form on the cart page")
        form = form[0]
        self.assertEqual(form.get("action"), "/shop/fur/checkout")
        self.assertEqual(
            [i.get("name") for i in form.xpath(".//input[@type!='hidden' and @type!='radio'] | .//textarea")],
            ["name", "phone", "email", "street", "note"],
        )
        modes = form.xpath(".//input[@name='provider_id']/@data-mode")
        self.assertEqual(modes, ["wire_transfer", "cash_on_delivery"])
        self.assertEqual(form.xpath(".//input[@name='provider_id'][@checked]/@data-mode"), ["wire_transfer"])
        self.assertFalse(html.xpath("//div[hasclass('wizard')]"), "No checkout steps")
        self.assertFalse(html.xpath("//a[contains(@href, '/shop/checkout')]"), "No link to Odoo's checkout steps")
        self.assertTrue(html.xpath("//div[hasclass('oe_cart')]//div[hasclass('o_fur_cart_total')]//div[@id='cart_total']"),
                        "Total under the lines")

    def test_invalid_form_is_rendered_again(self):
        html = self._add_chair_and_open_cart()
        csrf = html.xpath("//form[hasclass('o_fur_quick_checkout')]//input[@name='csrf_token']/@value")[0]
        response = self.url_open("/shop/fur/checkout", data={
            "csrf_token": csrf, "provider_id": str(self.providers["wire_transfer"].id),
            "name": "Nguyễn Văn Fur", "phone": "12ab", "email": "not-an-email", "street": "",
        }, timeout=TIMEOUT)
        self.assertEqual(response.status_code, 200)
        html = lxml.html.fromstring(response.content)
        invalid = html.xpath("//form[hasclass('o_fur_quick_checkout')]//*[hasclass('is-invalid')]/@name")
        self.assertEqual(sorted(invalid), ["email", "phone", "street"])
        self.assertEqual(html.xpath("//input[@name='name']/@value"), ["Nguyễn Văn Fur"], "Typed values kept")
        self.assertFalse(self._last_order().transaction_ids)

    def test_cash_on_delivery_order(self):
        html = self._add_chair_and_open_cart()
        csrf = html.xpath("//form[hasclass('o_fur_quick_checkout')]//input[@name='csrf_token']/@value")[0]
        cod = self.providers["cash_on_delivery"]
        response = self.url_open("/shop/fur/checkout", data={
            "csrf_token": csrf, "provider_id": str(cod.id),
            "name": "Trần Thị Fur", "phone": "0909 000 111", "email": "",
            "street": "12 Lê Lợi, Quận 1, TP. Hồ Chí Minh", "note": "Gọi trước khi giao",
        }, allow_redirects=False, timeout=TIMEOUT)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith("/payment/status"))
        order = self._last_order()
        self.assertEqual(order.partner_id.name, "Trần Thị Fur")
        self.assertEqual(order.partner_id.phone, "0909 000 111")
        self.assertEqual(order.partner_shipping_id.street, "12 Lê Lợi, Quận 1, TP. Hồ Chí Minh")
        self.assertEqual(order.fur_customer_note, "Gọi trước khi giao")
        self.assertEqual(order.transaction_ids.acquirer_id, cod)
        self.assertEqual(order.transaction_ids.acquirer_id.custom_mode, "cash_on_delivery")
        self.assertEqual(order.transaction_ids.state, "pending")
        self.assertEqual(order.state, "sent", "Quotation sent, as for any pending payment")
        # Odoo's own end of the checkout: the landing route, then the confirmation page
        self.assertEqual(order.transaction_ids.landing_route, "/shop/payment/validate")
        response = self.url_open("/shop/payment/validate", timeout=TIMEOUT)
        self.assertTrue(response.url.endswith("/shop/confirmation"), response.url)
        html = lxml.html.fromstring(response.content)
        thanks = html.xpath("string(//section[hasclass('o_fur_thanks')])")
        self.assertIn("Fur", thanks)
        self.assertIn(order.name, thanks)
        self.assertIn("pay the delivery staff", html.xpath("string(//div[hasclass('oe_website_sale_tx_status')])"),
                      "Pending message of the payment mode")
        self.assertFalse(self.url_open("/shop/cart", timeout=TIMEOUT).text.count("o_fur_quick_checkout"), "The cart is empty again")

    def test_checkout_tour(self):
        self.start_tour("/", "fur_theme.checkout_tour", login=None)
        order = self._last_order()
        self.assertTrue(order, "The tour created an order for the chair")
        self.assertEqual(order.partner_id.name, "Nguyễn Văn Fur")
        self.assertEqual(order.partner_id.phone, "0909 123 456")
        self.assertEqual(order.fur_customer_note, "Giao giờ hành chính")
        tx = order.transaction_ids[:1]
        self.assertEqual(tx.acquirer_id, self.providers["wire_transfer"])
        self.assertEqual(tx.state, "pending")


@tagged("post_install", "-at_install")
class TestFurSearch(HttpCase, FurCommon):

    _get_html = _get_html

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Product = cls.env["product.template"]
        cls.stripes = Product.create({
            "name": "Ghế Xoay Furtest Lưng Chỉ Ngang Hiện Đại - LGT68", "default_code": "LGT68",
            "list_price": 670000, "website_published": True, "taxes_id": [Command.clear()],
        })
        cls.mesh = Product.create({
            "name": "Ghế Xoay Furtest Lưng Lưới Hiện Đại - LGT60", "default_code": "LGT60",
            "list_price": 550000, "website_published": True, "taxes_id": [Command.clear()],
            # a description holding the other words must not make it match
            "description_sale": "Lưng chỉ ngang",
        })

    _jsonrpc = _jsonrpc

    def _shop_names(self, search):
        html = self._get_html("/shop?search=%s" % search)
        return [" ".join(t.split()) for t in html.xpath("//*[hasclass('o_fur_tile_name')]//text()")]

    def test_every_word_in_name_or_code(self):
        self.assertEqual(self._shop_names("Ghế Xoay Furtest Lưng Chỉ Ngang"), ["Ghế Xoay Furtest Lưng Chỉ Ngang Hiện Đại"])
        self.assertEqual(self._shop_names("LGT60"), ["Ghế Xoay Furtest Lưng Lưới Hiện Đại"])
        # a typo: Odoo's partial match, best match first
        names = self._shop_names("Ghế Xoay Furtest Lưng Chỉ Ngang Typoo")
        self.assertEqual(names[0], "Ghế Xoay Furtest Lưng Chỉ Ngang Hiện Đại")

    def test_suggest_route(self):
        result = self._jsonrpc("/fur/search/suggest", {"term": "furtest lưng"})
        self.assertEqual(result["count"], 2)
        self.assertEqual({item["code"] for item in result["items"]}, {"LGT68", "LGT60"})
        self.assertIn("/shop?search=", result["more_url"])
        first = self._jsonrpc("/fur/search/suggest", {"term": "LGT6"})["items"]
        self.assertEqual(len(first), 2)
        self.assertEqual(self._jsonrpc("/fur/search/suggest", {"term": "x"})["items"], [])

    def test_shop_cards_show_cart_button(self):
        view = self.env.ref("website_sale.products_add_to_cart").sudo()
        view.active = False
        html = self._get_html("/shop?search=LGT68")
        self.assertFalse(html.xpath("//div[hasclass('o_wsale_product_btn')]//a[hasclass('a-submit')]"))
        self.website.sudo()._fur_setup_shop_cards()
        self.assertTrue(view.active)
        html = self._get_html("/shop?search=LGT68")
        self.assertTrue(html.xpath("//div[hasclass('o_wsale_product_btn')]//a[hasclass('a-submit')]/*[local-name()='svg']"),
                        "Cart button with the Fur icon on the shop cards")

    def test_compare_price_and_price_on_request(self):
        self.stripes.sudo().compare_list_price = 990000
        self.mesh.sudo().list_price = 0
        html = self._get_html("/shop?search=LGT6")
        tiles = {
            tile.xpath("string(.//*[hasclass('o_fur_product_code')])").split()[-1]: tile
            for tile in html.xpath("//form[hasclass('oe_product_cart')]")
        }
        crossed = tiles["LGT68"].xpath(".//del[not(hasclass('d-none'))]//span[hasclass('oe_currency_value')]/text()")
        self.assertEqual([c.replace(",", "").replace(".00", "") for c in crossed], ["990000"], "Compare price crossed out")
        self.assertFalse(tiles["LGT60"].xpath(".//a[hasclass('a-submit')]"), "No price: no cart button")
        self.assertTrue(tiles["LGT60"].xpath(".//span[hasclass('o_fur_price_contact')]"), "No price: 'Contact'")
        html = self._get_html(self.mesh.website_url)
        self.assertFalse(html.xpath("//a[@id='add_to_cart']"))
        self.assertTrue(html.xpath("//div[hasclass('o_fur_price_request')]//a[@href='/contactus']"))
        items = {item["code"]: item for item in self._jsonrpc("/fur/search/suggest", {"term": "LGT6"})["items"]}
        self.assertTrue(items["LGT68"]["base_price"])
        self.assertEqual(items["LGT60"]["price"], "Contact")


@tagged("post_install", "-at_install")
class TestFurTermsAndAssets(HttpCase, FurCommon):

    _get_html = _get_html

    def test_frontend_styles_compile(self):
        files, _remains = self.env["ir.qweb"]._get_asset_content("web.assets_frontend")
        bundle = AssetsBundle("web.assets_frontend", files, env=self.env)
        css = b"".join(attachment.raw for attachment in bundle.css()).decode()
        self.assertFalse(bundle.css_errors, "Fur SCSS must compile (else Odoo serves an old style)")
        # a style file cut short by mistake goes unnoticed otherwise
        for selector in (".o_fur_footer h6", ".o_fur_footer_contact", ".o_fur_copyright_row",
                         ".o_fur_suggest_item", ".o_fur_contact_messenger", ".o_fur_desc_img"):
            self.assertIn(selector, css)

    def test_terms_link_only_when_the_page_exists(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("account.use_invoice_terms", False)
        html = self._get_html("/")
        self.assertNotIn("/terms", html.xpath("//div[hasclass('o_fur_footer')]//a/@href"))
        ICP.set_param("account.use_invoice_terms", True)
        self.website.company_id.sudo().terms_type = "html"
        html = self._get_html("/")
        self.assertIn("/terms", html.xpath("//div[hasclass('o_fur_footer')]//a/@href"))


@tagged("post_install", "-at_install")
class TestFurCopyrightBar(HttpCase, FurCommon):

    _get_html = _get_html

    def test_copyright_bar(self):
        html = self._get_html("/")
        bar = html.xpath("//div[hasclass('o_fur_copyright')]")
        self.assertTrue(bar, "Fur copyright bar")
        self.assertIn("Copyright", bar[0].xpath("string(.//div[hasclass('o_fur_copyright_name')])"))
        self.assertTrue(bar[0].xpath(".//div[hasclass('o_fur_copyright_brand')]//a[@target='_blank']"),
                        "Powered by Odoo opens in a new tab")
