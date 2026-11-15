import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Cart button of the Fur product cards (template fur_theme.product_card):
 * Odoo 19 only handles the "Add to cart" of its own shop tiles, so the card
 * calls the cart service itself.
 */
export class FurProductCard extends Interaction {
    static selector = ".o_fur_product_card button[name='add_to_cart']";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.locked(this.onClick, true) },
    };

    async onClick() {
        const { productId, productTemplateId, productType, showQuantity } = this.el.dataset;
        await this.waitFor(
            this.services["cart"].add(
                {
                    productTemplateId: parseInt(productTemplateId),
                    productId: parseInt(productId),
                    isCombo: productType === "combo",
                },
                { showQuantity: Boolean(showQuantity) }
            )
        );
    }
}

registry.category("public.interactions").add("fur_theme.product_card", FurProductCard);
