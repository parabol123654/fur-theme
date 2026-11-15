odoo.define("fur_theme.checkout_tour", function (require) {
    "use strict";

    const tour = require("web_tour.tour");

    const form = ".o_fur_quick_checkout";

    tour.register("fur_theme.checkout_tour", {
        test: true,
        url: "/",
    }, [
        {
            content: "Open the off-canvas menu with the hamburger button",
            trigger: ".o_fur_header .o_fur_burger",
        },
        {
            content: "The menu panel slides in over a backdrop",
            trigger: ".o_fur_header:has(.o_fur_offcanvas_backdrop) .o_fur_offcanvas.show a[href='/projects']:visible",
            run: function () {},
        },
        {
            content: "Close it",
            trigger: ".o_fur_offcanvas.show .o_fur_offcanvas_close",
        },
        {
            content: "Menu closed",
            trigger: ".o_fur_header:not(:has(.o_fur_offcanvas_backdrop)) .o_fur_offcanvas:not(.show)",
            run: function () {},
        },
        {
            content: "Fur homepage category block: add the chair to the cart",
            trigger: ".o_fur_home_block .o_fur_product_card:has(a:contains('Fur Test Chair GX00')) button[name='add_to_cart']",
        },
        {
            content: "Cart badge in the Fur header is updated",
            trigger: ".o_fur_header sup.my_cart_quantity:containsExact(1)",
            run: function () {},
        },
        {
            content: "Go to the cart",
            trigger: ".o_fur_header a[href='/shop/cart']",
        },
        {
            content: "Cart page shows the Fur trust bar",
            trigger: ".o_fur_checkout .o_fur_trustbar",
            run: function () {},
        },
        {
            content: "No checkout wizard: the cart page is the whole checkout",
            trigger: ".o_fur_checkout:not(:has(.wizard))",
            run: function () {},
        },
        {
            content: "Place the order without the contact fields: the browser refuses it",
            trigger: form + " button[name='o_fur_checkout']",
        },
        {
            content: "Still on the cart page",
            trigger: form + " input[name='name']:invalid",
            run: function () {},
        },
        { trigger: form + " input[name='name']", run: "text Nguyễn Văn Fur" },
        { trigger: form + " input[name='phone']", run: "text 0909 123 456" },
        { trigger: form + " input[name='street']", run: "text 123 Nguyễn Văn Linh, Quận 7, TP. Hồ Chí Minh" },
        { trigger: form + " textarea[name='note']", run: "text Giao giờ hành chính" },
        {
            content: "Choose cash on delivery: its instructions show up",
            trigger: form + " input[data-mode='cash_on_delivery']",
        },
        {
            trigger: form + " input[data-mode='cash_on_delivery'] ~ .o_fur_pm_desc:visible",
            run: function () {},
        },
        {
            content: "Choose bank transfer",
            trigger: form + " input[data-mode='wire_transfer']",
        },
        {
            content: "Place the order",
            trigger: form + " button[name='o_fur_checkout']",
        },
        {
            content: "Fur thank-you banner",
            trigger: ".o_fur_thanks:contains('Fur')",
            timeout: 30000,
            run: function () {
                window.location.href = "/contactus"; // stop the payment status polling
            },
        },
        {
            trigger: "#wrap form#contactus_form",
            run: function () {},
        },
    ]);
});
