/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

const form = ".o_fur_quick_checkout";

registry.category("web_tour.tours").add("fur_theme.checkout_tour", {
    test: true,
    steps: () => [
        {
            content: "Fur homepage category block: add the chair to the cart",
            trigger: ".o_fur_home_block .o_fur_product_card:has(a:contains('Fur Test Chair GX00')) button[name='add_to_cart']",
            run: "click",
        },
        {
            content: "Cart badge in the Fur header is updated",
            trigger: ".o_fur_header sup.my_cart_quantity:containsExact(1)",
            isCheck: true,
        },
        tourUtils.goToCart(),
        {
            content: "Cart page shows the Fur trust bar",
            trigger: ".o_fur_checkout .o_fur_trustbar",
            isCheck: true,
        },
        {
            content: "No checkout wizard: the cart page is the whole checkout",
            trigger: ".o_fur_checkout:not(:has(.o_wizard))",
            isCheck: true,
        },
        {
            content: "Place the order without the contact fields: the browser refuses it",
            trigger: `${form} button[name='o_fur_checkout']`,
            run: "click",
        },
        {
            content: "Still on the cart page",
            trigger: `${form} input[name='name']:invalid`,
            isCheck: true,
        },
        { trigger: `${form} input[name='name']`, run: "text Nguyễn Văn Fur" },
        { trigger: `${form} input[name='phone']`, run: "text 0909 123 456" },
        { trigger: `${form} input[name='street']`, run: "text 123 Nguyễn Văn Linh, Quận 7, TP. Hồ Chí Minh" },
        { trigger: `${form} textarea[name='note']`, run: "text Giao giờ hành chính" },
        {
            content: "Choose cash on delivery: its instructions show up",
            trigger: `${form} input[data-mode='cash_on_delivery']`,
            run: "click",
        },
        {
            trigger: `${form} input[data-mode='cash_on_delivery'] ~ .o_fur_pm_desc:visible`,
            isCheck: true,
        },
        {
            content: "Choose bank transfer",
            trigger: `${form} input[data-mode='wire_transfer']`,
            run: "click",
        },
        {
            content: "Place the order",
            trigger: `${form} button[name='o_fur_checkout']`,
            run: "click",
        },
        {
            content: "Fur thank-you banner on Odoo's confirmation page",
            trigger: ".o_fur_thanks:contains('Fur')",
            timeout: 30000,
            isCheck: true,
        },
    ],
});
