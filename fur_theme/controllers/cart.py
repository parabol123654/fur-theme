# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
"""One-step checkout on the cart page: payment method + 5 contact fields.

The order goes through Odoo's own payment flow (a wire transfer transaction
set to pending, then /payment/process -> /shop/payment/validate ->
/shop/confirmation), only the address and payment pages are skipped.
"""
import re

from odoo import _
from odoo.http import request, route

from odoo.addons.fur_theme.models.payment_provider import FUR_PAYMENT_MODES
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website_sale.controllers.main import WebsiteSale

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FORM_FIELDS = ("name", "phone", "email", "street", "note")


class FurCart(WebsiteSale):

    @route()
    def cart(self, access_token=None, revive="", **post):
        response = super().cart(access_token=access_token, revive=revive, **post)
        values = getattr(response, "qcontext", None)
        if values is not None and request.website.fur_enabled and post.get("type") != "popover":
            order_sudo = values.get("website_sale_order")
            if order_sudo and order_sudo.website_order_line:
                values["fur_checkout"] = self._fur_checkout_values(order_sudo)
        return response

    # === HELPERS === #

    def _fur_payment_providers(self, order_sudo):
        return request.env["payment.acquirer"].sudo().search([
            ("provider", "=", "transfer"),
            ("custom_mode", "in", FUR_PAYMENT_MODES),
            ("state", "=", "enabled"),
            ("company_id", "=", order_sudo.company_id.id),
            ("website_id", "in", [False, request.website.id]),
        ], order="sequence, id")

    @staticmethod
    def _fur_is_anonymous_cart(order_sudo):
        return order_sudo.partner_id == request.website.user_id.sudo().partner_id

    @staticmethod
    def _fur_one_line_address(partner):
        return ", ".join(part for part in (partner.street, partner.street2, partner.city) if part)

    def _fur_checkout_values(self, order_sudo, form=None, errors=None):
        providers = self._fur_payment_providers(order_sudo)
        if form is None:
            form = dict.fromkeys(_FORM_FIELDS, "")
            if not self._fur_is_anonymous_cart(order_sudo):
                shipping = order_sudo.partner_shipping_id
                form.update({
                    "name": shipping.name or "",
                    "phone": shipping.phone or order_sudo.partner_id.phone or "",
                    "email": order_sudo.partner_id.email or "",
                    "street": self._fur_one_line_address(shipping),
                })
            form["note"] = order_sudo.fur_customer_note or ""
            provider_id = providers[:1].id
        else:
            provider_id = int(form["provider_id"]) if form.get("provider_id", "").isdigit() else None
        return {
            "providers": providers,
            "provider_id": provider_id,
            "form": form,
            "errors": errors or {},
        }

    def _fur_checkout_errors(self, form, provider):
        errors = {}
        if not form["name"]:
            errors["name"] = _("Please enter your full name.")
        if not 9 <= len(re.sub(r"\D", "", form["phone"])) <= 15 or re.search(r"[^\d\s().+-]", form["phone"]):
            errors["phone"] = _("Please enter a valid phone number.")
        if form["email"] and not _EMAIL.match(form["email"]):
            errors["email"] = _("Please enter a valid email address.")
        if not form["street"]:
            errors["street"] = _("Please enter your delivery address.")
        if not provider:
            errors["provider_id"] = _("Please choose a payment method.")
        return errors

    def _fur_checkout_partner(self, order_sudo, form):
        """Set the customer of the cart from the form: a new contact for a
        visitor; for a signed-in customer, their own address when it matches
        (or is still empty), otherwise a new delivery address."""
        website = request.website
        PartnerSudo = request.env["res.partner"].sudo().with_context(tracking_disable=True)
        address = {
            "name": form["name"],
            "phone": form["phone"],
            "street": form["street"],
            "country_id": (website.company_id.country_id or request.env.ref("base.vn")).id,
        }
        if self._fur_is_anonymous_cart(order_sudo):
            values = dict(
                address,
                email=form["email"] or False,
                type="contact",
                company_id=website.company_id.id,
                team_id=website.salesteam_id.id,
                user_id=website.salesperson_id.id,
            )
            if request.lang.code in website.mapped("language_ids.code"):
                values["lang"] = request.lang.code
            if website.specific_user_account:
                values["website_id"] = website.id
            partner_sudo = PartnerSudo.create(values)
            # as /shop/address does for a new billing address
            order_sudo.partner_id = partner_sudo
            order_sudo.with_context(not_self_saleperson=True).onchange_partner_id()
            order_sudo.partner_invoice_id = partner_sudo
            order_sudo.partner_shipping_id = partner_sudo
            order_sudo.message_partner_ids = [(4, partner_sudo.id), (3, website.partner_id.id)]
            return partner_sudo

        customer = order_sudo.partner_id
        if form["email"] and not customer.email:
            customer.email = form["email"]
        shipping = order_sudo.partner_shipping_id
        if (shipping.name, shipping.phone or "", self._fur_one_line_address(shipping)) == (
            form["name"], form["phone"], form["street"]
        ):
            return shipping
        if not customer.street and customer.name == form["name"]:
            customer.write({"phone": form["phone"], "street": form["street"], "country_id": address["country_id"]})
            order_sudo.partner_shipping_id = customer
            return customer
        delivery = PartnerSudo.create(dict(address, type="delivery", parent_id=customer.id))
        order_sudo.partner_shipping_id = delivery
        return delivery

    def _fur_create_transaction(self, order_sudo, acquirer_sudo):
        """A wire transfer transaction for the cart, as the payment page
        creates it (/shop/payment/transaction, form flow), set to pending
        straight away: there is nothing to pay online."""
        Transaction = request.env["payment.transaction"].sudo()
        invoice_partner = order_sudo.partner_invoice_id
        if not invoice_partner.country_id:
            # an Odoo 14 transaction needs the country of the customer, which
            # Odoo's address page asks for
            invoice_partner.country_id = request.website.company_id.country_id or request.env.ref("base.vn")
        # not order._create_payment_transaction(): it wants a journal on the
        # acquirer, which a database without a chart of accounts does not have
        tx_sudo = Transaction.create({
            "acquirer_id": acquirer_sudo.id,
            "amount": order_sudo.amount_total,
            "currency_id": order_sudo.pricelist_id.currency_id.id,
            "partner_id": invoice_partner.id,
            "type": order_sudo._get_payment_type(),
            "return_url": "/shop/payment/validate",
            "sale_order_ids": [(6, 0, [order_sudo.id])],
        })
        tx_sudo._log_payment_transaction_sent()
        last_tx_sudo = Transaction.browse(request.session.get("__website_sale_last_tx_id")).exists()
        if last_tx_sudo:
            PaymentProcessing.remove_payment_transaction(last_tx_sudo)
        PaymentProcessing.add_payment_transaction(tx_sudo)
        request.session["__website_sale_last_tx_id"] = tx_sudo.id
        # what the wire transfer form posts to /payment/transfer/feedback
        Transaction.form_feedback({
            "reference": tx_sudo.reference,
            "amount": tx_sudo.amount,
            "currency": tx_sudo.currency_id.name,
        }, "transfer")
        return tx_sudo

    # === ROUTES === #

    @route("/shop/fur/checkout", type="http", methods=["POST"], auth="public", website=True, sitemap=False)
    def fur_checkout(self, **post):
        order_sudo = request.website.sale_get_order()
        if not request.website.fur_enabled:
            return request.redirect("/shop/cart")
        # a draft cart with lines, as for Odoo's own checkout pages
        redirection = self.checkout_redirection(order_sudo)
        if redirection:
            return redirection

        form = {fname: (post.get(fname) or "").strip() for fname in _FORM_FIELDS}
        form["provider_id"] = post.get("provider_id") or ""
        provider_sudo = self._fur_payment_providers(order_sudo).filtered(
            lambda provider: str(provider.id) == form["provider_id"]
        )
        errors = self._fur_checkout_errors(form, provider_sudo)
        if errors:
            response = self.cart()
            response.qcontext["fur_checkout"] = self._fur_checkout_values(order_sudo, form, errors)
            return response

        self._fur_checkout_partner(order_sudo, form)
        order_sudo.fur_customer_note = form["note"] or False
        # as /shop/confirm_order does
        order_sudo.onchange_partner_shipping_id()
        order_sudo.order_line._compute_tax_id()
        request.session["sale_last_order_id"] = order_sudo.id
        request.website.sale_get_order(update_pricelist=True)
        if not order_sudo.amount_total:  # nothing to pay: /shop/payment/validate confirms it
            return request.redirect("/shop/payment/validate")

        self._fur_create_transaction(order_sudo, provider_sudo)
        return request.redirect("/payment/process")
