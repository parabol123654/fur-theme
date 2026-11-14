# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
"""One-step checkout on the cart page: payment method + 5 contact fields.

The order goes through Odoo's own payment flow (a custom-provider transaction
set to pending, then /payment/status -> /shop/payment/validate ->
/shop/confirmation), only the address, delivery and payment pages are skipped.
"""
import re

from odoo.fields import Command
from odoo.http import request, route

from odoo.addons.fur_theme.models.payment_provider import FUR_PAYMENT_MODES
from odoo.addons.website_sale.controllers.cart import Cart

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FORM_FIELDS = ("name", "phone", "email", "street", "note")


class FurCart(Cart):

    def _cart_values(self, **post):
        values = super()._cart_values(**post)
        order_sudo = request.cart
        if self.env.website.fur_enabled and order_sudo and order_sudo.website_order_line:
            values["fur_checkout"] = self._fur_checkout_values(order_sudo)
        return values

    # === HELPERS === #

    def _fur_payment_providers(self, order_sudo):
        providers = self.env["payment.provider"].sudo().search([
            ("code", "=", "custom"),
            ("custom_mode", "in", FUR_PAYMENT_MODES),
            ("is_published", "=", True),
            ("company_id", "=", order_sudo.company_id.id),
            ("website_id", "in", [False, self.env.website.id]),
        ], order="sequence, id")
        return providers.filtered(lambda provider: provider._fur_checkout_payment_method())

    @staticmethod
    def _fur_one_line_address(partner):
        return ", ".join(part for part in (partner.street, partner.street2, partner.city) if part)

    def _fur_checkout_values(self, order_sudo, form=None, errors=None):
        providers = self._fur_payment_providers(order_sudo)
        if form is None:
            form = dict.fromkeys(_FORM_FIELDS, "")
            if not order_sudo._is_anonymous_cart():
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
            errors["name"] = self.env._("Please enter your full name.")
        if not 9 <= len(re.sub(r"\D", "", form["phone"])) <= 15 or re.search(r"[^\d\s().+-]", form["phone"]):
            errors["phone"] = self.env._("Please enter a valid phone number.")
        if form["email"] and not _EMAIL.match(form["email"]):
            errors["email"] = self.env._("Please enter a valid email address.")
        if not form["street"]:
            errors["street"] = self.env._("Please enter your delivery address.")
        if not provider:
            errors["provider_id"] = self.env._("Please choose a payment method.")
        return errors

    def _fur_checkout_partner(self, order_sudo, form):
        """Set the customer of the cart from the form: a new contact for a
        visitor; for a signed-in customer, their own address when it matches
        (or is still empty), otherwise a new delivery address."""
        website = self.env.website
        PartnerSudo = self.env["res.partner"].sudo()
        address = {
            "name": form["name"],
            "phone": form["phone"],
            "street": form["street"],
            "country_id": (website.company_id.country_id or self.env.ref("base.vn")).id,
        }
        if order_sudo._is_anonymous_cart():
            values = {
                **address,
                "email": form["email"] or False,
                "type": "contact",
                "company_id": website.company_id.id,
                "user_id": website.salesperson_id.id,
            }
            if request.lang.code in website.language_ids.mapped("code"):
                values["lang"] = request.lang.code
            if website.specific_user_account:
                values["website_id"] = website.id
            partner_sudo = PartnerSudo.create(values)
            order_sudo._update_address(
                partner_sudo.id, {"partner_id", "partner_invoice_id", "partner_shipping_id"}
            )
            order_sudo.message_unsubscribe(website.partner_id.ids)
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
            order_sudo._update_address(customer.id, {"partner_shipping_id"})
            return customer
        delivery = PartnerSudo.create({**address, "type": "delivery", "parent_id": customer.id})
        order_sudo._update_address(delivery.id, {"partner_shipping_id"})
        return delivery

    # === ROUTES === #

    @route("/shop/fur/checkout", type="http", methods=["POST"], auth="public", website=True, sitemap=False)
    def fur_checkout(self, **post):
        order_sudo = request.cart
        if not self.env.website.fur_enabled or not order_sudo or not order_sudo.website_order_line:
            return request.redirect("/shop/cart")
        # The cart step (public checkout allowed, cart ready) is the only one left.
        if redirect := self.env["website.checkout.step"].validate_checkout_progress("/shop/address", order_sudo):
            return request.redirect(redirect)

        form = {fname: (post.get(fname) or "").strip() for fname in _FORM_FIELDS}
        form["provider_id"] = post.get("provider_id") or ""
        provider_sudo = self._fur_payment_providers(order_sudo).filtered(
            lambda provider: str(provider.id) == form["provider_id"]
        )
        errors = self._fur_checkout_errors(form, provider_sudo)
        if errors or order_sudo._has_blocking_alerts():
            response = self.cart()
            response.qcontext["fur_checkout"] = self._fur_checkout_values(order_sudo, form, errors)
            return response

        self._fur_checkout_partner(order_sudo, form)
        order_sudo.fur_customer_note = form["note"] or False
        order_sudo._update_cart_taxes_and_prices()
        request.session["sale_last_order_id"] = order_sudo.id
        if not order_sudo.amount_total:  # nothing to pay: /shop/payment/validate confirms it
            return request.redirect("/shop/payment/validate")

        tx_sudo = self._create_transaction(
            provider_id=provider_sudo.id,
            payment_method_id=provider_sudo._fur_checkout_payment_method().id,
            token_id=None,
            amount=order_sudo.amount_total,
            currency_id=order_sudo.currency_id.id,
            partner_id=order_sudo.partner_invoice_id.id,
            flow="redirect",
            tokenization_requested=False,
            landing_route="/shop/payment/validate",
            custom_create_values={"sale_order_ids": [Command.set([order_sudo.id])]},
        )
        request.session["__website_sale_last_tx_id"] = tx_sudo.id
        tx_sudo._record({"reference": tx_sudo.reference})  # custom providers: set to pending
        return request.redirect("/payment/status")
