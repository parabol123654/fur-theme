import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Sticky buy box of the Fur product page (template fur_theme.product_sticky_buy).
 *
 * It holds no form of its own: a swatch clicks the matching radio of the main
 * product form, and its buttons click the main "Add to cart" / "Buy now", so
 * website_sale keeps doing the combination, price and cart work.
 */
export class FurStickyBuy extends Interaction {
    static selector = ".o_fur_sticky_buy";
    dynamicContent = {
        ".o_fur_sticky_swatch": { "t-on-click": this.onSwatchClick },
        "[data-fur-action]": { "t-on-click": this.onActionClick },
        _document: { "t-on-change": this.onMainFormChange },
    };

    get mainForm() {
        return document.querySelector("#product_details");
    }

    onSwatchClick(ev) {
        const valueId = ev.currentTarget.dataset.valueId;
        const input = this.mainForm?.querySelector(`input.js_variant_change[value="${valueId}"]`);
        if (input && !input.checked) {
            input.click(); // fires the change website_sale listens to
        }
        this.syncFromMainForm();
    }

    onActionClick(ev) {
        const action = ev.currentTarget.dataset.furAction;
        this.mainForm?.querySelector(action === "buy_now" ? ".o_we_buy_now" : "#add_to_cart")?.click();
    }

    onMainFormChange(ev) {
        if (ev.target.matches?.("#product_details input.js_variant_change")) {
            this.syncFromMainForm();
        }
    }

    /** Highlight the swatches of the values checked in the main form. */
    syncFromMainForm() {
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
    }
}

registry.category("public.interactions").add("fur_theme.sticky_buy", FurStickyBuy);
