# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import base64
import io

from PIL import Image

from odoo.tests import SavepointCase


class FurCommon(SavepointCase):
    """Self-contained Fur catalogue: tests never rely on the demo data."""

    @classmethod
    def _create_image(cls, color):
        stream = io.BytesIO()
        Image.new("RGB", (64, 64), color).save(stream, "PNG")
        return base64.b64encode(stream.getvalue())

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].get_current_website()
        cls.public_user = cls.website.user_id
        # Prices in the company currency, as website_sale's own tests do
        cls.website.get_current_pricelist().write({"currency_id": cls.env.company.currency_id.id})
        # Unprefixed URLs whatever the database default language.
        # _activate_lang: English is inactive on a database created in Vietnamese.
        english = cls.env["res.lang"]._activate_lang("en_US")
        cls.website.sudo().write({
            "language_ids": [(4, english.id)],
            "default_lang_id": english.id,
            "fur_brand_name": "Fur",
            # the demo sets these: tests start from a website without them
            "fur_footer_logo": False,
            "fur_whatsapp": False,
        })
        # Our records only on the homepage, even on a database with demo data.
        cls.env["product.public.category"].sudo().search([]).fur_show_on_home = False
        cls.env["product.template"].sudo().search([]).fur_featured = False
        cls.env["fur.project"].sudo().search([]).is_featured = False
        Category = cls.env["product.public.category"]
        cls.categ_office = Category.create({"name": "Fur Test Office", "fur_show_on_home": True})
        cls.categ_chair = Category.create({
            "name": "Fur Test Chairs", "parent_id": cls.categ_office.id, "fur_show_on_home": True,
        })
        cls.categ_hidden = Category.create({"name": "Fur Test Not On Home"})
        cls.chair = cls.env["product.template"].create({
            "name": "Fur Test Chair GX00",
            "list_price": 2750000,
            "compare_list_price": 3800000,
            # No default sales tax: a Vietnamese company adds 10% VAT and shows
            # prices tax included, which would shift every asserted price.
            "taxes_id": [(5, 0, 0)],
            "website_published": True,
            "fur_featured": True,
            "public_categ_ids": [(6, 0, (cls.categ_office | cls.categ_chair).ids)],
            "image_1920": cls._create_image("#F8CB0C"),
        })
        cls.desk = cls.env["product.template"].create({
            "name": "Fur Test Desk BG00",
            "list_price": 1250000,
            "website_published": True,
            "public_categ_ids": [(6, 0, cls.categ_office.ids)],
        })
        cls.unpublished = cls.env["product.template"].create({
            "name": "Fur Test Hidden Cabinet",
            "list_price": 5000000,
            "website_published": False,
            "fur_featured": True,
            "public_categ_ids": [(6, 0, cls.categ_office.ids)],
        })
        Project = cls.env["fur.project"]
        cls.project = Project.create({
            "name": "Fur Test Office Project",
            "subtitle": "Austin",
            "project_type": "office",
            "location": "Austin, Texas",
            "summary": "A test project.",
            "is_featured": True,
            "is_published": True,
            "product_tmpl_ids": [(6, 0, cls.chair.ids)],
            "image_1920": cls._create_image("#13254E"),
        })
        cls.project_draft = Project.create({
            "name": "Fur Test Draft Project",
            "project_type": "apartment",
            "is_published": False,
        })
