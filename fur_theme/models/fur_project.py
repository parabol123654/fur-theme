# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.translate import html_translate

from odoo.addons.http_routing.models.ir_http import slug


class FurProject(models.Model):
    """A completed interior project shown on the /projects pages."""

    _name = "fur.project"
    _description = "Fur Interior Project"
    _inherit = [
        "website.seo.metadata",
        "website.published.multi.mixin",
        "image.mixin",
    ]
    _order = "sequence, id desc"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    project_type = fields.Selection(
        [
            ("office", "Office"),
            ("apartment", "Apartment"),
            ("house", "Townhouse & Villa"),
            ("hospitality", "Café & Hospitality"),
        ],
        string="Type",
        required=True,
        default="office",
    )
    location = fields.Char(translate=True, help="City or district, e.g. 'Brooklyn, New York'.")
    client_name = fields.Char(string="Client")
    area = fields.Float(string="Area (m²)")
    completion_date = fields.Date()
    subtitle = fields.Char(
        translate=True,
        help="Second line of the title on the homepage card, e.g. 'Tech startup, Austin'.",
    )
    summary = fields.Text(translate=True)
    description = fields.Html(translate=html_translate)
    is_featured = fields.Boolean(
        string="Featured on Homepage",
        help="Show this project in the 'Featured projects' section of the homepage.",
    )
    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Products Used",
        domain=[("sale_ok", "=", True)],
    )

    @api.depends("name")
    def _compute_website_url(self):
        super()._compute_website_url()
        for project in self:
            if project.id:
                project.website_url = "/projects/%s" % slug(project)

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res["default_opengraph"]["og:description"] = self.summary or ""
        res["default_opengraph"]["og:image"] = self.env["website"].image_url(self, "image_1024")
        res["default_meta_description"] = self.summary or ""
        return res
