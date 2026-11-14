import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";

/**
 * Suggestions under the header search box (template fur_theme.header):
 * products whose name or code holds every typed word, best matches first
 * (route /fur/search/suggest). Enter without a highlighted suggestion still
 * submits the form to /shop?search=...
 */
export class FurSearchSuggest extends Interaction {
    static selector = ".o_fur_search";
    dynamicContent = {
        "input[name='search']": {
            "t-on-input": this.debounced(this.onInput, 250),
            "t-on-keydown": this.onKeydown,
            "t-on-focus": this.onFocus,
        },
        _root: { "t-on-focusout": this.debounced(this.onFocusOut, 150) },
    };

    setup() {
        this.input = this.el.querySelector("input[name='search']");
        this.input.setAttribute("autocomplete", "off");
        this.keepLast = new KeepLast();
        this.menu = null;
        this.active = -1;
    }

    destroy() {
        this.close();
    }

    async onInput() {
        const term = this.input.value.trim();
        if (term.length < 2) {
            this.close();
            return;
        }
        this.el.classList.add("o_fur_search_loading");
        const result = await this.keepLast.add(
            this.waitFor(rpc("/fur/search/suggest", { term, limit: 8 }))
        );
        this.el.classList.remove("o_fur_search_loading");
        if (this.input.value.trim() === term) {
            this.show(result);
        }
    }

    onFocus() {
        if (this.menu && this.menu.childElementCount) {
            this.menu.classList.remove("d-none");
        } else if (this.input.value.trim().length >= 2) {
            this.onInput();
        }
    }

    onFocusOut() {
        if (!this.el.contains(document.activeElement)) {
            this.menu?.classList.add("d-none");
        }
    }

    onKeydown(ev) {
        const links = this.menu ? [...this.menu.querySelectorAll("a")] : [];
        if (ev.key === "Escape") {
            this.menu?.classList.add("d-none");
        } else if ((ev.key === "ArrowDown" || ev.key === "ArrowUp") && links.length) {
            ev.preventDefault();
            const step = ev.key === "ArrowDown" ? 1 : -1;
            this.active = (this.active + step + links.length) % links.length;
            links.forEach((link, index) => link.classList.toggle("active", index === this.active));
        } else if (ev.key === "Enter" && this.active >= 0 && links[this.active]) {
            ev.preventDefault();
            window.location.href = links[this.active].href;
        }
    }

    show(result) {
        if (!this.menu) {
            this.menu = document.createElement("div");
            this.menu.className = "o_fur_suggest";
            this.menu.setAttribute("role", "listbox");
            this.el.appendChild(this.menu);
        }
        this.active = -1;
        this.menu.replaceChildren();
        this.menu.classList.remove("d-none");
        if (!result.items.length) {
            const empty = document.createElement("div");
            empty.className = "o_fur_suggest_empty";
            empty.textContent = result.empty_label;
            this.menu.appendChild(empty);
            return;
        }
        for (const item of result.items) {
            const link = document.createElement("a");
            link.className = "o_fur_suggest_item";
            link.href = item.url;
            link.setAttribute("role", "option");
            const img = document.createElement("img");
            img.src = item.image;
            img.alt = "";
            img.loading = "lazy";
            const text = document.createElement("span");
            text.className = "o_fur_suggest_text";
            const name = document.createElement("span");
            name.className = "o_fur_suggest_name";
            name.textContent = item.name;
            const meta = document.createElement("span");
            meta.className = "o_fur_suggest_meta";
            if (item.code) {
                const code = document.createElement("span");
                code.className = "o_fur_suggest_code";
                code.textContent = item.code;
                meta.appendChild(code);
            }
            const price = document.createElement("b");
            price.textContent = item.price;
            meta.appendChild(price);
            if (item.base_price) {
                const base = document.createElement("del");
                base.textContent = item.base_price;
                meta.appendChild(base);
            }
            text.append(name, meta);
            link.append(img, text);
            this.menu.appendChild(link);
        }
        if (result.count > result.items.length) {
            const more = document.createElement("a");
            more.className = "o_fur_suggest_more";
            more.href = result.more_url;
            more.textContent = result.more_label;
            this.menu.appendChild(more);
        }
    }

    close() {
        this.menu?.remove();
        this.menu = null;
        this.active = -1;
    }
}

registry.category("public.interactions").add("fur_theme.search_suggest", FurSearchSuggest);
