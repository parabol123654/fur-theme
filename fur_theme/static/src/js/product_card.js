/** @odoo-module **/

import publicWidget from "web.public.widget";
import wSaleUtils from "website_sale.utils";

/**
 * Cart button of the Fur product cards (template fur_theme.product_card:
 * homepage blocks, related products, project pages): adds the product and
 * updates the cart badge without leaving the page, as the shop grid does.
 */
publicWidget.registry.FurProductCard = publicWidget.Widget.extend({
    selector: ".o_fur_product_card",
    events: {
        "click button[name='add_to_cart']": "_onClickAddToCart",
    },

    async _onClickAddToCart(ev) {
        const button = ev.currentTarget;
        button.disabled = true;
        try {
            const data = await this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    product_id: parseInt(button.dataset.productId),
                    add_qty: 1,
                    display: false,
                    force_create: true,
                },
            });
            // website setting "Add to cart: go to cart"
            if (document.documentElement.dataset.add2cartRedirect === "0") {
                window.location.href = "/shop/cart";
                return;
            }
            sessionStorage.setItem("website_sale_cart_quantity", data.cart_quantity);
            wSaleUtils.updateCartNavBar(data);
        } finally {
            button.disabled = false;
        }
    },
});

export default publicWidget.registry.FurProductCard;
