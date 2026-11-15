# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models
from odoo.tools import file_open

# Payment modes offered by the Fur one-step checkout (cart page), in display order.
FUR_PAYMENT_MODES = ("wire_transfer", "cash_on_delivery")

# name, help message (shown under the selected option) and pending message
# (confirmation page) of each mode, in English then Vietnamese.
_FUR_PROVIDER_TEXTS = {
    "wire_transfer": {
        "image": "payment_custom/static/description/icon.png",
        "name": ("Bank transfer", "Thanh toán bằng chuyển khoản"),
        "pre_msg": (
            "<p>Transfer the order amount to our bank account: the account details and the"
            " payment reference are shown as soon as the order is placed.</p>"
            "<p>Our staff will call you to confirm the order and arrange the delivery once the"
            " payment is received.</p>",
            "<p>Quý khách chuyển khoản số tiền của đơn hàng vào tài khoản ngân hàng của công ty:"
            " thông tin tài khoản và nội dung chuyển khoản hiển thị ngay sau khi đặt hàng.</p>"
            "<p>Nhân viên sẽ gọi điện xác nhận đơn hàng và sắp xếp giao hàng ngay khi nhận được"
            " thanh toán.</p>",
        ),
        "pending_msg": (
            "<p>Please transfer the order amount using the details below. We will call you to"
            " confirm the order as soon as the payment is received.</p>",
            "<p>Quý khách vui lòng chuyển khoản theo thông tin bên dưới. Nhân viên sẽ gọi điện xác"
            " nhận đơn hàng ngay khi nhận được thanh toán.</p>",
        ),
    },
    "cash_on_delivery": {
        "image": "fur_theme/static/src/img/payment_method_cash_on_delivery.png",
        "name": ("Cash on delivery", "Thanh toán tại điểm giao hàng"),
        "pre_msg": (
            "<p>Pay in cash to the delivery staff when you receive the goods.</p>"
            "<p>Our sales staff will call you to confirm the order and the delivery time.</p>",
            "<p>Quý khách thanh toán bằng tiền mặt cho nhân viên giao hàng khi nhận hàng.</p>"
            "<p>Nhân viên kinh doanh sẽ gọi điện xác nhận đơn hàng và thời gian giao hàng.</p>",
        ),
        "pending_msg": (
            "<p>Your order has been received. Please pay the delivery staff when you receive the"
            " goods; we will call you to confirm the delivery time.</p>",
            "<p>Đơn hàng của quý khách đã được tiếp nhận. Quý khách thanh toán cho nhân viên giao"
            " hàng khi nhận hàng; chúng tôi sẽ gọi điện xác nhận thời gian giao hàng.</p>",
        ),
    },
}


def _terms(field, value):
    """The translatable terms of an html value, in document order."""
    terms = []
    field.translate(lambda term: terms.append(term) or term, value)
    return terms


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    # Odoo 16's payment_custom only knows the wire transfer mode.
    custom_mode = fields.Selection(
        selection_add=[("cash_on_delivery", "Cash On Delivery")],
        ondelete={"cash_on_delivery": "set null"},
    )

    @api.model
    def _fur_setup_checkout_providers(self):
        """Publish one custom provider per Fur payment mode for each website
        company, reusing an existing provider of that mode when there is one.

        Names and messages are (re)written: this runs once, on install or on
        the upgrade that introduced the one-step checkout.
        """
        vietnamese = "vi_VN" in dict(self.env["res.lang"].get_installed())
        websites = self.env["website"].search([], order="sequence, id")
        # xmlids (fur_theme.payment_provider_<mode>) for the main website's company
        main_company = websites[:1].company_id
        for company in websites.company_id:
            for sequence, mode in enumerate(FUR_PAYMENT_MODES, start=1):
                texts = _FUR_PROVIDER_TEXTS[mode]
                provider = self.search([
                    ("code", "=", "custom"), ("custom_mode", "=", mode), ("company_id", "=", company.id),
                ]).sorted(lambda p: (not p.is_published, p.state != "enabled", p.id))[:1]
                if not provider:
                    # Odoo 16 has no payment methods: the picture is the provider's
                    with file_open(texts["image"], "rb") as image:
                        image = image.read()
                    provider = self.create({
                        "name": texts["name"][0],
                        "code": "custom",
                        "custom_mode": mode,
                        "company_id": company.id,
                        "redirect_form_view_id": self.env.ref("payment_custom.redirect_form").id,
                        "image_128": base64.b64encode(image),
                    })
                provider.with_context(lang="en_US").write({
                    "state": "enabled",
                    "is_published": True,
                    "sequence": sequence,
                    "name": texts["name"][0],
                    "pre_msg": texts["pre_msg"][0],
                    "pending_msg": texts["pending_msg"][0],
                })
                if vietnamese:
                    for fname in ("name", "pre_msg", "pending_msg"):
                        english, translation = texts[fname]
                        field = self._fields[fname]
                        if callable(field.translate):  # html: translated term by term
                            translation = dict(zip(
                                _terms(field, provider.with_context(lang="en_US")[fname]),
                                _terms(field, translation),
                            ))
                        provider.update_field_translations(fname, {"vi_VN": translation})
                if company == main_company:
                    self.env["ir.model.data"]._update_xmlids([{
                        "xml_id": f"fur_theme.payment_provider_{mode}",
                        "record": provider,
                        "noupdate": True,
                    }])
