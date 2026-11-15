odoo.define("fur_theme.offcanvas", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");

    /**
     * Off-canvas menu of the Fur header (template fur_theme.header), opened by
     * the hamburger button. Bootstrap 4 has no off-canvas component: the
     * panel is shown with the "show" class, over a backdrop.
     */
    publicWidget.registry.FurOffcanvas = publicWidget.Widget.extend({
        selector: ".o_fur_header",
        events: {
            "click [data-fur-toggle='offcanvas']": "_onToggle",
            "click [data-fur-dismiss='offcanvas']": "_onClose",
            "click .o_fur_offcanvas_backdrop": "_onClose",
            "keydown": "_onKeydown",
        },

        /**
         * @override
         */
        start: function () {
            this.panel = this.el.querySelector(".o_fur_offcanvas");
            return this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        destroy: function () {
            this._toggle(false);
            this._super.apply(this, arguments);
        },

        /**
         * @private
         * @param {boolean} show
         */
        _toggle: function (show) {
            if (!this.panel) {
                return;
            }
            this.panel.classList.toggle("show", show);
            document.body.classList.toggle("o_fur_offcanvas_open", show);
            if (show && !this.backdrop) {
                this.backdrop = document.createElement("div");
                this.backdrop.className = "o_fur_offcanvas_backdrop";
                this.el.appendChild(this.backdrop);
            } else if (!show && this.backdrop) {
                this.backdrop.remove();
                this.backdrop = null;
            }
        },
        _onToggle: function (ev) {
            ev.preventDefault();
            this._toggle(!this.panel.classList.contains("show"));
        },
        _onClose: function (ev) {
            ev.preventDefault();
            this._toggle(false);
        },
        _onKeydown: function (ev) {
            if (ev.key === "Escape") {
                this._toggle(false);
            }
        },
    });

    return publicWidget.registry.FurOffcanvas;
});
