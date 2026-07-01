/** @odoo-module **/
// ---------------------------------------------------------------------------
// pns_color — OWL2 color-picker field widget (Odoo 15-19+).
//
// Renders three synchronized controls for a single ``rgba(r, g, b, a)``
// value:
//   1. ``<input type="color">`` — visual RGB picker
//   2. ``<input type="range">`` — opacity slider (0-100 %)
//   3. ``<input type="text">``  — pasteable rgba/rgb/#hex string
//
// Accepts ``#hex``, ``rgb(...)`` and ``rgba(...)`` on input and normalizes
// everything to ``rgba(r, g, b, a)`` on commit.  Invalid input is flagged
// with a red border (Bootstrap ``is-invalid`` class).
//
// The widget also updates a live preview box (CSS class
// ``.pns_ribbon_preview_box``) if one exists in the current form.
// ---------------------------------------------------------------------------

import { registry } from "@web/core/registry";
import { Component, useRef } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const HEX_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;
const RGB_ANY_RE = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(0|1|0?\.\d+)\s*)?\)$/i;

/**
 * Parse a CSS color string into ``{r, g, b, a}`` or ``null``.
 *
 * @param {string} v - Color string (``#hex``, ``rgb(...)``, ``rgba(...)``).
 * @returns {{r: number, g: number, b: number, a: number}|null}
 */
export function parseRgba(v) {
    v = (v || "").trim();
    if (HEX_RE.test(v)) {
        let h = v.slice(1);
        if (h.length === 3) {
            h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
        }
        return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: 1 };
    }
    const m = v.match(RGB_ANY_RE);
    if (m) {
        return {
            r: Math.min(255, parseInt(m[1], 10)),
            g: Math.min(255, parseInt(m[2], 10)),
            b: Math.min(255, parseInt(m[3], 10)),
            a: m[4] != null ? Math.max(0, Math.min(1, parseFloat(m[4]))) : 1,
        };
    }
    return null;
}

/** Return ``true`` if *v* is a recognized CSS color string. */
export function isValidColor(v) {
    return parseRgba(v) !== null;
}

function fmtAlpha(a) {
    return String(Math.round(a * 1000) / 1000);
}

/** Format an ``{r, g, b, a}`` object as ``'rgba(r, g, b, a)'``. */
export function toRgba(o) {
    return `rgba(${o.r}, ${o.g}, ${o.b}, ${fmtAlpha(o.a)})`;
}

/** Format an ``{r, g, b}`` object as ``'#RRGGBB'``. */
function toHex(o) {
    const h = (n) => Math.min(255, n).toString(16).padStart(2, "0");
    return ("#" + h(o.r) + h(o.g) + h(o.b)).toUpperCase();
}

export class PnsColorField extends Component {
    static template = "pns_ribbon.PnsColorField";
    static props = { ...standardFieldProps };

    setup() {
        this.textRef = useRef("text");
        this.pickerRef = useRef("picker");
        this.opacityRef = useRef("opacity");
    }

    get rawValue() {
        const rec = this.props.record;
        return (rec ? rec.data[this.props.name] : this.props.value) || "";
    }
    get parts() {
        return parseRgba(this.rawValue) || { r: 0, g: 0, b: 0, a: 1 };
    }
    get hexView() {
        return toHex(this.parts);
    }
    get opacityView() {
        return Math.round(this.parts.a * 100);
    }

    _currentParts() {
        // Prefer the live text-input value if it parses; fall back to record.
        const fromText = this.textRef.el ? parseRgba(this.textRef.el.value) : null;
        return fromText || this.parts;
    }

    /** Update the live preview box (if present) with the given rgba value. */
    _applyLive(rgba) {
        const box = document.querySelector(".pns_ribbon_preview_box");
        if (!box) {
            return;
        }
        if (this.props.name === "bg_color") {
            box.style.background = rgba;
        } else {
            box.style.color = rgba;
        }
    }

    /** Commit *rgba* to the Odoo record (triggers onchange). */
    _commit(rgba) {
        if (this.props.record) {
            this.props.record.update({ [this.props.name]: rgba });
        } else if (this.props.update) {
            this.props.update(rgba);
        }
    }

    /**
     * Reflect an rgba value across all three controls, skipping the one
     * currently being edited to avoid fighting the user's input.
     */
    _sync(o, skip) {
        const rgba = toRgba(o);
        if (skip !== "text" && this.textRef.el) {
            this.textRef.el.value = rgba;
            this.textRef.el.classList.remove("is-invalid");
        }
        if (skip !== "picker" && this.pickerRef.el) {
            this.pickerRef.el.value = toHex(o);
        }
        if (skip !== "opacity" && this.opacityRef.el) {
            this.opacityRef.el.value = Math.round(o.a * 100);
        }
        return rgba;
    }

    onPickerInput(ev) {
        const o = parseRgba(ev.target.value) || { r: 0, g: 0, b: 0, a: 1 };
        o.a = this._currentParts().a;
        this._applyLive(this._sync(o, "picker"));
    }
    onPickerChange(ev) {
        const o = parseRgba(ev.target.value) || { r: 0, g: 0, b: 0, a: 1 };
        o.a = this._currentParts().a;
        this._commit(toRgba(o));
    }

    onOpacityInput(ev) {
        const o = this._currentParts();
        o.a = Math.max(0, Math.min(100, parseInt(ev.target.value, 10) || 0)) / 100;
        this._applyLive(this._sync(o, "opacity"));
    }
    onOpacityChange(ev) {
        const o = this._currentParts();
        o.a = Math.max(0, Math.min(100, parseInt(ev.target.value, 10) || 0)) / 100;
        this._commit(toRgba(o));
    }

    onTextInput(ev) {
        const o = parseRgba(ev.target.value);
        ev.target.classList.toggle("is-invalid", ev.target.value.trim() !== "" && !o);
        if (o) {
            this._applyLive(this._sync(o, "text"));
        }
    }
    onTextChange(ev) {
        const o = parseRgba(ev.target.value);
        if (o) {
            this._commit(toRgba(o));
        }
    }
}

export const pnsColorField = {
    component: PnsColorField,
    supportedTypes: ["char"],
};

registry.category("fields").add("pns_color", pnsColorField);
