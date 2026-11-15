# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
"""One-step checkout on the cart page: payment method + 5 contact fields.

The order goes through Odoo's own payment flow (a custom-provider transaction
set to pending, then /payment/status -> /shop/payment/validate ->
/shop/confirmation), only the address, delivery and payment pages are skipped.
"""
import re

from odoo import SUPERUSER_ID, _
from odoo.fields import Command
from odoo.http import request, route

from odoo.addons.fur_theme.models.payment_provider import FUR_PAYMENT_MODES
from odoo.addons.website_sale.controllers.main import WebsiteSale

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FORM_FIELDS = ("name", "phone", "email", "street", "note")


class FurCart(WebsiteSale):

    def _cart_values(self, **post):
        values = super()._cart_values(**post)
        order_sudo = request.website.sale_get_order()
        if request.website.fur_enabled and order_sudo and order_sudo.website_order_line:
            values["fur_checkout"] = self._fur_checkout_values(order_sudo)
        return values

    def _get_shop_payment_errors(self, order):
        # An order of the one-step checkout has no delivery step: the shop
        # calls the customer to arrange the delivery.
        if request.website.fur_enabled and order and order.id == request.session.get("fur_checkout_order_id"):
            return []
        return super()._get_shop_payment_errors(order)

    # === HELPERS === #

    def _fur_payment_providers(self, order_sudo):
        providers = request.env["payment.provider"].sudo().search([
            ("code", "=", "custom"),
            ("custom_mode", "in", FUR_PAYMENT_MODES),
            ("state", "=", "enabled"),
            ("is_published", "=", True),
            ("company_id", "=", order_sudo.company_id.id),
            ("website_id", "in", [False, request.website.id]),
        ], order="sequence, id")
        return providers.filtered(lambda provider: provider._fur_checkout_payment_method())

    @staticmethod
    def _fur_one_line_address(partner):
        return ", ".join(part for part in (partner.street, partner.street2, partner.city) if part)

    def _fur_checkout_values(self, order_sudo, form=None, errors=None):
        providers = self._fur_payment_providers(order_sudo)
        if form is None:
            form = dict.fromkeys(_FORM_FIELDS, "")
            if not order_sudo._is_public_order():
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
        if order_sudo._is_public_order():
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
            order_sudo.write({
                "partner_id": partner_sudo.id,
                "partner_invoice_id": partner_sudo.id,
                "partner_shipping_id": partner_sudo.id,
            })
            # as Odoo's own address step does
            order_sudo.message_partner_ids = [
                Command.link(partner_sudo.id), Command.unlink(website.partner_id.id),
            ]
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
        delivery = PartnerSudo.create({**address, "type": "delivery", "parent_id": customer.id})
        order_sudo.partner_shipping_id = delivery
        return delivery

    # === ROUTES === #

    @route()
    def checkout(self, **post):
        # "Buy now" (Odoo 17 sends it to /shop/checkout?express=1): the cart
        # page is the whole checkout
        if request.website.fur_enabled and post.get("express"):
            return request.redirect("/shop/cart")
        return super().checkout(**post)

    @route()
    def shop_payment_validate(self, sale_order_id=None, **post):
        # A free order of the one-step checkout (nothing to pay, no transaction):
        # confirmed as Odoo does, which then shows the order in the portal.
        # Odoo 17 would first raise "No shipping method is selected": the
        # one-step checkout has no delivery step.
        order_sudo = request.website.sale_get_order()
        if (
            sale_order_id is None
            and request.website.fur_enabled
            and order_sudo
            and order_sudo.id == request.session.get("fur_checkout_order_id")
            and order_sudo.state == "draft"
            and order_sudo.order_line
            and not order_sudo.amount_total
            and not order_sudo.get_portal_last_transaction()
        ):
            order_sudo.with_context(send_email=True).with_user(SUPERUSER_ID).action_confirm()
            request.website.sale_reset()
            return request.redirect(order_sudo.get_portal_url())
        return super().shop_payment_validate(sale_order_id=sale_order_id, **post)

    @route("/shop/fur/checkout", type="http", methods=["POST"], auth="public", website=True, sitemap=False)
    def fur_checkout(self, **post):
        order_sudo = request.website.sale_get_order()
        if not request.website.fur_enabled or not order_sudo or not order_sudo.website_order_line:
            return request.redirect("/shop/cart")
        # The cart step (public checkout allowed, draft cart) is the only one left.
        if redirection := self.checkout_redirection(order_sudo):
            return redirection

        form = {fname: (post.get(fname) or "").strip() for fname in _FORM_FIELDS}
        form["provider_id"] = post.get("provider_id") or ""
        provider_sudo = self._fur_payment_providers(order_sudo).filtered(
            lambda provider: str(provider.id) == form["provider_id"]
        )
        errors = self._fur_checkout_errors(form, provider_sudo)
        if errors or not order_sudo._is_cart_ready():
            response = self.cart()
            response.qcontext["fur_checkout"] = self._fur_checkout_values(order_sudo, form, errors)
            return response

        fiscal_position = order_sudo.fiscal_position_id
        self._fur_checkout_partner(order_sudo, form)
        order_sudo.fur_customer_note = form["note"] or False
        # taxes and prices of the customer, as Odoo's address step does
        if order_sudo.fiscal_position_id != fiscal_position:
            order_sudo._recompute_taxes()
        request.website.sale_get_order(update_pricelist=True)
        request.session["sale_last_order_id"] = order_sudo.id
        request.session["fur_checkout_order_id"] = order_sudo.id
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
        # custom providers: set to pending
        tx_sudo._handle_notification_data("custom", {"reference": tx_sudo.reference})
        return request.redirect("/payment/status")
