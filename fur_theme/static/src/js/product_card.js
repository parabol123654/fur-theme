import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import wSaleUtils from "@website_sale/js/website_sale_utils";

/**
 * Cart button of the Fur product cards (template fur_theme.product_card):
 * Odoo 18 only handles the "Add to cart" of its own shop tiles, so the card
 * calls the cart route itself.
 */
publicWidget.registry.FurProductCard = publicWidget.Widget.extend({
    selector: ".o_fur_product_card button[name='add_to_cart']",
    events: {
        click: "_onClick",
    },

    async _onClick(ev) {
        ev.preventDefault();
        if (this.el.disabled) {
            return;
        }
        this.el.disabled = true;
        try {
            const data = await rpc("/shop/cart/update_json", {
                product_id: parseInt(this.el.dataset.productId),
                add_qty: 1,
                display: false,
                force_create: true,
            });
            // website setting "Add to cart: go to cart"
            if (document.documentElement.dataset.add2cartRedirect === "0") {
                window.location.href = "/shop/cart";
                return;
            }
            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showCartNotification(this.call.bind(this), data.notification_info);
        } finally {
            this.el.disabled = false;
        }
    },
});

export default publicWidget.registry.FurProductCard;
