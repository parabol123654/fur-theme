odoo.define("fur_theme.product_card", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");
    const wSaleUtils = require("website_sale.utils");

    /**
     * Cart button of the Fur product cards (template fur_theme.product_card:
     * homepage blocks, related products, project pages): adds one unit of the
     * product to the cart without leaving the page and updates the cart
     * badge of the header. The /shop tiles keep website_sale's own handler.
     */
    publicWidget.registry.FurProductCard = publicWidget.Widget.extend({
        selector: ".o_fur_product_card",
        events: {
            "click button[name='add_to_cart']": "_onClickAddToCart",
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickAddToCart: function (ev) {
            ev.preventDefault();
            const button = ev.currentTarget;
            if (button.disabled) {
                return;
            }
            button.disabled = true;
            return this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    product_id: parseInt(button.dataset.productId, 10),
                    add_qty: 1,
                    force_create: true,
                    display: false,
                },
            }).then(function (data) {
                wSaleUtils.updateCartNavBar(data);
            }).guardedCatch(function () {
                // nothing: the error dialog is Odoo's
            }).then(function () {
                button.disabled = false;
            });
        },
    });

    return publicWidget.registry.FurProductCard;
});
