# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.fur_theme.hooks import FUR_SHOP_LAYOUT, ODOO_SHOP_LAYOUT, post_init_hook, uninstall_hook

from .common import FurCommon


@tagged("post_install", "-at_install")
class TestFurModels(FurCommon):

    def test_home_categories_flagged_first(self):
        categories = self.website._fur_home_categories(limit=50)
        self.assertIn(self.categ_office, categories)
        self.assertIn(self.categ_chair, categories)
        self.assertNotIn(self.categ_hidden, categories, "Only flagged categories when some are flagged")

    def test_home_categories_fallback_to_roots(self):
        self.env["product.public.category"].sudo().search([]).fur_show_on_home = False
        categories = self.website._fur_home_categories(limit=500)
        self.assertIn(self.categ_hidden, categories)
        self.assertNotIn(self.categ_chair, categories, "Fallback lists root categories only")

    def test_featured_products_are_published(self):
        website = self.website.with_user(self.public_user)
        products = website._fur_featured_products(limit=50)
        self.assertIn(self.chair, products)
        self.assertNotIn(self.unpublished, products)

    def test_product_prices_include_compare_price(self):
        prices = self.website._fur_product_prices(self.chair)
        self.assertEqual(prices[self.chair.id]["price_reduce"], 2750000)
        self.assertEqual(prices[self.chair.id]["base_price"], 3800000)
        self.assertEqual(self.website._fur_product_prices(self.env["product.template"]), {})

    def test_related_products(self):
        related = self.website.with_user(self.public_user)._fur_related_products(self.chair)
        self.assertIn(self.desk, related)
        self.assertNotIn(self.chair, related)
        self.assertNotIn(self.unpublished, related)

    def test_category_images(self):
        categories = self.categ_office | self.categ_chair
        images = self.website._fur_category_images(categories)
        self.assertEqual(images[self.categ_chair.id], self.chair, "First product of the category")
        self.assertEqual(images[self.categ_office.id], self.chair, "Sub-category products count too")
        self.categ_chair.sudo().image_1920 = self._create_image("#FFFFFF")
        images = self.website._fur_category_images(categories)
        self.assertEqual(images[self.categ_chair.id], self.categ_chair, "Own picture wins")
        empty = self.env["product.public.category"].sudo().create({"name": "Fur Test Empty"})
        self.assertEqual(self.website._fur_category_images(empty)[empty.id], empty)

    def test_flag_urls_and_languages(self):
        # (code, url_code, name, active, flag_image_url), see res.lang.get_available
        vi = ("vi_VN", "vi", "Tiếng Việt", True, "/vn.png")
        en = ("en_GB", "en_GB", "English (UK)", True, "/gb.png")
        fr = ("fr_FR", "fr", "Français", True, "/fr.png")
        self.assertTrue(self.website._fur_flag_url(vi).endswith("flag_vn.svg"))
        self.assertTrue(self.website._fur_flag_url(en).endswith("flag_gb.svg"))
        self.assertEqual(self.website._fur_flag_url(fr), "/fr.png")
        self.assertEqual(self.website._fur_header_languages([vi]), [], "No pills for one language")
        self.website.sudo().default_lang_id = self.env["res.lang"]._activate_lang("en_US")
        self.assertEqual(
            self.website._fur_header_languages([vi, ("en_US", "en", "English (US)", True, "/us.png"), fr])[0][0],
            "en_US", "Default language first",
        )

    def test_project_url_and_access(self):
        self.assertTrue(self.project.website_url.startswith("/projects/"))
        self.assertIn(str(self.project.id), self.project.website_url)
        visible = self.env["fur.project"].with_user(self.public_user).search([])
        self.assertIn(self.project, visible)
        self.assertNotIn(self.project_draft, visible, "Visitors only see published projects")
        featured = self.website.with_user(self.public_user)._fur_featured_projects(limit=50)
        self.assertIn(self.project, featured)
        self.assertNotIn(self.project_draft, featured)

    def test_hooks_only_touch_default_grid(self):
        Website = self.env["website"].sudo()
        custom = Website.create({"name": "Custom grid", "shop_ppr": 2, "shop_ppg": 8})
        default = Website.create({"name": "Default grid", **ODOO_SHOP_LAYOUT})
        post_init_hook(self.env.cr, self.registry)
        self.assertEqual((default.shop_ppr, default.shop_ppg), tuple(FUR_SHOP_LAYOUT.values()))
        self.assertEqual((custom.shop_ppr, custom.shop_ppg), (2, 8))
        uninstall_hook(self.env.cr, self.registry)
        self.assertEqual((default.shop_ppr, default.shop_ppg), tuple(ODOO_SHOP_LAYOUT.values()))
        self.assertEqual((custom.shop_ppr, custom.shop_ppg), (2, 8))

    def test_short_name_drops_trailing_reference(self):
        product = self.env["product.template"].sudo().create({"name": "Ghế Test Lưng Lưới - GX77", "default_code": "GX77"})
        self.assertEqual(product._fur_short_name(), "Ghế Test Lưng Lưới")
        product.default_code = "OTHER"
        self.assertEqual(product._fur_short_name(), "Ghế Test Lưng Lưới - GX77", "Only its own reference is dropped")

    def test_menu_categories_from_category_url(self):
        Menu = self.env["website.menu"].sudo()
        root = self.website.menu_id
        office_menu = Menu.create({"name": "Office", "url": self.categ_office.website_url, "parent_id": root.id})
        other_menu = Menu.create({"name": "Shop", "url": "/shop", "parent_id": root.id})
        self.assertEqual(self.website._fur_menu_categories(office_menu), self.categ_chair)
        self.assertFalse(self.website._fur_menu_categories(other_menu))


@tagged("post_install", "-at_install")
class TestFurInventoryCategories(FurCommon):

    def test_website_categories_copied_to_inventory(self):
        office = self.categ_office.fur_product_categ_id
        chairs = self.categ_chair.fur_product_categ_id
        self.assertEqual(office.name, self.categ_office.name)
        self.assertEqual(chairs.parent_id, office, "Same tree as the website categories")
        self.assertEqual(self.chair.categ_id, chairs, "Deepest website category")
        self.categ_chair.sudo().name = "Fur Test Seats"
        self.assertEqual(chairs.name, "Fur Test Seats", "Renames follow")
        self.desk.sudo().public_categ_ids = [(6, 0, self.categ_chair.ids)]
        self.assertEqual(self.desk.categ_id, chairs, "Changing the website category moves the product")


@tagged("post_install", "-at_install")
class TestFurViewCopies(FurCommon):

    def test_unchanged_website_copy_gets_translations(self):
        self.env["res.lang"].sudo()._activate_lang("vi_VN")
        View = self.env["ir.ui.view"].sudo()
        Translation = self.env["ir.translation"].sudo()

        def translate(view, value):
            term = Translation.search([
                ("type", "=", "model_terms"), ("name", "=", "ir.ui.view,arch_db"),
                ("res_id", "=", view.id), ("lang", "=", "vi_VN"), ("src", "=", "See all"),
            ])
            if term:
                term.write({"value": value, "state": "translated"})
            else:
                Translation.create({
                    "type": "model_terms", "name": "ir.ui.view,arch_db", "res_id": view.id,
                    "lang": "vi_VN", "src": "See all", "value": value, "state": "translated",
                })

        generic = View.create({
            "name": "Fur Test Page", "type": "qweb", "key": "fur_theme.test_copy_page",
            "arch": '<t t-name="fur_theme.test_copy_page"><p>See all</p></t>',
        })
        translate(generic, "Xem tất cả")
        copy = generic.copy({"website_id": self.website.id, "key": generic.key})
        edited = generic.copy({"website_id": self.website.id, "key": "fur_theme.test_copy_page_2",
                               "arch": '<t t-name="x"><p>Edited</p></t>'})
        translate(copy, "Cũ")
        View.invalidate_cache()
        self.assertIn("Cũ", copy.with_context(lang="vi_VN").arch_db)
        self.env["website"]._fur_sync_view_copies()
        self.assertIn("Xem tất cả", copy.with_context(lang="vi_VN").arch_db)
        self.assertIn("Edited", edited.arch_db, "Edited copies are left alone")
