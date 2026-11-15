odoo.define("fur_theme.product_sticky_buy", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");

    /**
     * Sticky buy box of the Fur product page (template fur_theme.product_sticky_buy).
     *
     * It holds no form of its own: a swatch clicks the matching radio of the main
     * product form, and its buttons click the main "Add to cart" / "Buy now", so
     * website_sale keeps doing the combination, price and cart work.
     */
    publicWidget.registry.FurStickyBuy = publicWidget.Widget.extend({
        selector: ".o_fur_sticky_buy",
        events: {
            "click .o_fur_sticky_swatch": "_onSwatchClick",
            "click [data-fur-action]": "_onActionClick",
        },

        /**
         * @override
         */
        start: function () {
            this._onMainFormChange = this._onMainFormChange.bind(this);
            document.addEventListener("change", this._onMainFormChange);
            return this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        destroy: function () {
            document.removeEventListener("change", this._onMainFormChange);
            this._super.apply(this, arguments);
        },

        _getMainForm: function () {
            return document.querySelector("#product_details");
        },

        _onSwatchClick: function (ev) {
            const valueId = ev.currentTarget.dataset.valueId;
            const mainForm = this._getMainForm();
            const input = mainForm && mainForm.querySelector('input.js_variant_change[value="' + valueId + '"]');
            if (input && !input.checked) {
                input.click(); // fires the change website_sale listens to
            }
            this._syncFromMainForm();
        },

        _onActionClick: function (ev) {
            const mainForm = this._getMainForm();
            const selector = ev.currentTarget.dataset.furAction === "buy_now" ? ".o_we_buy_now" : "#add_to_cart";
            const button = mainForm && mainForm.querySelector(selector);
            if (button) {
                button.click();
            }
        },

        _onMainFormChange: function (ev) {
            if (ev.target.matches && ev.target.matches("#product_details input.js_variant_change")) {
                this._syncFromMainForm();
            }
        },

        /**
         * Highlight the swatches of the values checked in the main form.
         */
        _syncFromMainForm: function () {
            const mainForm = this._getMainForm();
            const checked = new Set(
                Array.from(mainForm ? mainForm.querySelectorAll("input.js_variant_change:checked") : [])
                    .map(function (input) { return input.value; })
            );
            this.el.querySelectorAll(".o_fur_sticky_attr").forEach(function (attr) {
                const names = [];
                attr.querySelectorAll(".o_fur_sticky_swatch").forEach(function (swatch) {
                    const active = checked.has(swatch.dataset.valueId);
                    swatch.classList.toggle("active", active);
                    if (active) {
                        names.push(swatch.dataset.valueName);
                    }
                });
                const label = attr.querySelector(".o_fur_sticky_attr_value");
                if (label) {
                    label.textContent = names.join(", ");
                }
            });
        },
    });

    return publicWidget.registry.FurStickyBuy;
});
