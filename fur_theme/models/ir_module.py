# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _update_translations(self, filter_lang=None, overwrite=False):
        result = super()._update_translations(filter_lang=filter_lang, overwrite=overwrite)
        # after the module's .po files: unchanged website copies of the Fur
        # pages get the new translations too
        if "fur_theme" in self.mapped("name"):
            self.env["website"]._fur_sync_view_copies()
        return result
