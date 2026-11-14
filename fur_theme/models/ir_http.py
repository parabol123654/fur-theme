# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        # i18n_extra/vi.po carries Vietnamese for website_sale/website JS
        # strings Odoo 20 has not translated yet; the website only receives a
        # module's JS translations when the module is listed here.
        return super()._get_translation_frontend_modules_name() + ["fur_theme"]
