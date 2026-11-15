/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

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
    start() {
        this._onMainFormChange = this._onMainFormChange.bind(this);
        document.addEventListener("change", this._onMainFormChange);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        document.removeEventListener("change", this._onMainFormChange);
        this._super(...arguments);
    },

    get mainForm() {
        return document.querySelector("#product_details");
    },

    _onSwatchClick(ev) {
        const valueId = ev.currentTarget.dataset.valueId;
        const input = this.mainForm?.querySelector(`input.js_variant_change[value="${valueId}"]`);
        if (input && !input.checked) {
            input.click(); // fires the change website_sale listens to
        }
        this._syncFromMainForm();
    },

    _onActionClick(ev) {
        const action = ev.currentTarget.dataset.furAction;
        const selector = action === "buy_now" ? ".o_we_buy_now" : "#add_to_cart";
        this.mainForm?.querySelector(selector)?.click();
    },

    _onMainFormChange(ev) {
        if (ev.target.matches?.("#product_details input.js_variant_change")) {
            this._syncFromMainForm();
        }
    },

    /** Highlight the swatches of the values checked in the main form. */
    _syncFromMainForm() {
        const checked = new Set(
            [...(this.mainForm?.querySelectorAll("input.js_variant_change:checked") || [])].map((i) => i.value)
        );
        for (const attr of this.el.querySelectorAll(".o_fur_sticky_attr")) {
            const names = [];
            for (const swatch of attr.querySelectorAll(".o_fur_sticky_swatch")) {
                const active = checked.has(swatch.dataset.valueId);
                swatch.classList.toggle("active", active);
                if (active) {
                    names.push(swatch.dataset.valueName);
                }
            }
            const label = attr.querySelector(".o_fur_sticky_attr_value");
            if (label) {
                label.textContent = names.join(", ");
            }
        }
    },
});

export default publicWidget.registry.FurStickyBuy;
