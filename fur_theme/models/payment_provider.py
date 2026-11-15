# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models
from odoo.tools import file_open

# Payment modes offered by the Fur one-step checkout (cart page), in display order.
FUR_PAYMENT_MODES = ("wire_transfer", "cash_on_delivery")

# name, help message (shown under the selected option) and pending message
# (confirmation page, cash on delivery only) of each mode, in English then Vietnamese.
_FUR_PROVIDER_TEXTS = {
    "wire_transfer": {
        "image": "payment_transfer/static/src/img/transfer_icon.png",
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
        # pending message: the one Odoo 15 writes for wire transfers (it lists
        # the company's bank accounts and the payment reference)
    },
    "cash_on_delivery": {
        "image": "payment_transfer/static/src/img/transfer_icon.png",
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


class PaymentAcquirer(models.Model):
    """Odoo 15 has a single manual payment acquirer type, "Wire Transfer"
    (payment_transfer): the Fur checkout uses one such acquirer per payment
    mode, told apart by ``custom_mode`` (the name of the equivalent field of the
    custom payment providers of later Odoo versions)."""

    _inherit = "payment.acquirer"

    custom_mode = fields.Selection(
        [("wire_transfer", "Wire Transfer"), ("cash_on_delivery", "Cash on Delivery")],
        string="Fur Checkout Mode",
        help="Payment mode of the Fur one-step checkout (cart page) this wire transfer acquirer is "
        "offered as. Empty: not offered on the cart page.",
        copy=False,
    )

    @api.model
    def _fur_setup_checkout_providers(self):
        """Publish one wire transfer acquirer per Fur payment mode for each
        website company, reusing an existing acquirer of that mode when there
        is one (Odoo's own "Wire Transfer" acquirer for the bank transfer).

        Names and messages are (re)written: this runs once, on install or on
        the upgrade that introduced the one-step checkout.
        """
        vietnamese = "vi_VN" in dict(self.env["res.lang"].get_installed())
        websites = self.env["website"].search([], order="sequence, id")
        # xmlids (fur_theme.payment_provider_<mode>) for the main website's company
        main_company = websites[:1].company_id
        Acquirer = self.with_context(active_test=False)
        for company in websites.mapped("company_id"):
            for sequence, mode in enumerate(FUR_PAYMENT_MODES, start=1):
                texts = _FUR_PROVIDER_TEXTS[mode]
                acquirer = Acquirer.search([
                    ("provider", "=", "transfer"), ("custom_mode", "=", mode), ("company_id", "=", company.id),
                ], order="id", limit=1)
                if not acquirer and mode == "wire_transfer":
                    acquirer = Acquirer.search([
                        ("provider", "=", "transfer"), ("custom_mode", "=", False), ("company_id", "=", company.id),
                    ], order="id", limit=1)
                if not acquirer:
                    with file_open(texts["image"], "rb") as image:
                        image = base64.b64encode(image.read())
                    acquirer = self.create({
                        "name": texts["name"][0],
                        "provider": "transfer",
                        "company_id": company.id,
                        "redirect_form_view_id": self.env.ref("payment_transfer.redirect_form").id,
                        "image_128": image,
                    })
                acquirer.write({"custom_mode": mode, "state": "enabled", "sequence": sequence, "display_as": False})
                # English (the source terms) last: on a database with a single
                # language Odoo 15 writes a translation to the source term too
                for lang, index in (("vi_VN", 1), ("en_US", 0)):
                    if lang == "vi_VN" and not vietnamese:
                        continue
                    acquirer.with_context(lang=lang).write({
                        fname: texts[fname][index] for fname in ("name", "pre_msg", "pending_msg") if fname in texts
                    })
                if company == main_company:
                    self.env["ir.model.data"]._update_xmlids([{
                        "xml_id": "fur_theme.payment_provider_%s" % mode,
                        "record": acquirer,
                        "noupdate": True,
                    }])
