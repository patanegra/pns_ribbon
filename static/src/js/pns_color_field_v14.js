odoo.define('pns_ribbon.PnsColorField', function (require) {
    "use strict";
    // -----------------------------------------------------------------------
    // pns_color — Legacy widget for Odoo 13-14 (owl1 / AbstractField).
    //
    // Renders three synchronized controls for a single rgba(r, g, b, a)
    // value:
    //   1. <input type="color"> — visual RGB picker
    //   2. <input type="range"> — opacity slider (0-100 %)
    //   3. <input type="text">  — pasteable rgba/rgb/#hex string
    //
    // Accepts #hex, rgb(...) and rgba(...) on input and normalizes
    // everything to rgba(r, g, b, a) on commit.  Invalid input is flagged
    // with a red border (Bootstrap is-invalid class).
    // -----------------------------------------------------------------------

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');

    var HEX_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;
    var RGB_ANY_RE = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(0|1|0?\.\d+)\s*)?\)$/i;

    /** Parse a CSS color string into {r, g, b, a} or null. */
    function parseRgba(v) {
        v = (v || '').trim();
        if (HEX_RE.test(v)) {
            var h = v.slice(1);
            if (h.length === 3) {
                h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
            }
            return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: 1 };
        }
        var m = v.match(RGB_ANY_RE);
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

    /** Return true if v is a recognized CSS color string. */
    function isValidColor(v) {
        return parseRgba(v) !== null;
    }

    function fmtAlpha(a) {
        return String(Math.round(a * 1000) / 1000);
    }

    /** Format an {r, g, b, a} object as 'rgba(r, g, b, a)'. */
    function toRgba(o) {
        return 'rgba(' + o.r + ', ' + o.g + ', ' + o.b + ', ' + fmtAlpha(o.a) + ')';
    }

    /** Format an {r, g, b} object as '#RRGGBB'. */
    function toHex(o) {
        var h = function (n) {
            n = Math.min(255, n).toString(16);
            return n.length < 2 ? '0' + n : n;
        };
        return ('#' + h(o.r) + h(o.g) + h(o.b)).toUpperCase();
    }

    var PnsColorField = AbstractField.extend({
        className: 'o_field_pns_color',
        tagName: 'span',
        supportedFieldTypes: ['char'],
        events: _.extend({}, AbstractField.prototype.events, {
            'input input[type="color"]': '_onPickerInput',
            'change input[type="color"]': '_onPickerCommit',
            'input input.o_pns_color_opacity': '_onOpacityInput',
            'change input.o_pns_color_opacity': '_onOpacityCommit',
            'input input.o_pns_color_text': '_onTextInput',
            'change input.o_pns_color_text': '_onTextCommit',
        }),

        _renderEdit: function () {
            this.$el.empty();
            var o = parseRgba(this.value) || { r: 0, g: 0, b: 0, a: 1 };
            this.$picker = $('<input type="color"/>').val(toHex(o));
            this.$opacity = $('<input type="range" min="0" max="100" step="1" class="o_pns_color_opacity"/>')
                .css('width', '90px')
                .val(Math.round(o.a * 100));
            this.$text = $('<input type="text" class="o_pns_color_text o_input"/>')
                .attr('placeholder', 'rgba(r, g, b, a)')
                .css('max-width', '185px')
                .val(this.value || '');
            this.$el.append(this.$picker).append(' ')
                .append($('<span class="text-muted" style="font-size:12px;"/>').text('Opacity '))
                .append(this.$opacity).append(' ')
                .append(this.$text);
        },

        _renderReadonly: function () {
            this.$el.empty();
            var $swatch = $('<span/>').css({
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'border': '1px solid #888',
                'border-radius': '3px',
                'vertical-align': 'middle',
                'background': this.value || '',
            });
            this.$el.append($swatch).append(' ')
                .append($('<span class="text-muted"/>').text(this.value || ''));
        },

        /** Prefer the live text-input value if it parses; fall back to record. */
        _currentParts: function () {
            var fromText = this.$text ? parseRgba(this.$text.val()) : null;
            return fromText || parseRgba(this.value) || { r: 0, g: 0, b: 0, a: 1 };
        },

        /** Update the live preview box (if present) with the given rgba value. */
        _applyLive: function (rgba) {
            var box = document.querySelector('.pns_ribbon_preview_box');
            if (!box) {
                return;
            }
            if (this.name === 'bg_color') {
                box.style.background = rgba;
            } else {
                box.style.color = rgba;
            }
        },

        /**
         * Reflect an rgba value across all three controls, skipping the one
         * currently being edited to avoid fighting the user's input.
         */
        _sync: function (o, skip) {
            var rgba = toRgba(o);
            if (skip !== 'text' && this.$text) {
                this.$text.val(rgba).removeClass('is-invalid');
            }
            if (skip !== 'picker' && this.$picker) {
                this.$picker.val(toHex(o));
            }
            if (skip !== 'opacity' && this.$opacity) {
                this.$opacity.val(Math.round(o.a * 100));
            }
            return rgba;
        },

        _onPickerInput: function (ev) {
            var o = parseRgba($(ev.currentTarget).val()) || { r: 0, g: 0, b: 0, a: 1 };
            o.a = this._currentParts().a;
            this._applyLive(this._sync(o, 'picker'));
        },
        _onPickerCommit: function (ev) {
            var o = parseRgba($(ev.currentTarget).val()) || { r: 0, g: 0, b: 0, a: 1 };
            o.a = this._currentParts().a;
            this._setValue(toRgba(o));
        },

        _onOpacityInput: function (ev) {
            var o = this._currentParts();
            o.a = Math.max(0, Math.min(100, parseInt($(ev.currentTarget).val(), 10) || 0)) / 100;
            this._applyLive(this._sync(o, 'opacity'));
        },
        _onOpacityCommit: function (ev) {
            var o = this._currentParts();
            o.a = Math.max(0, Math.min(100, parseInt($(ev.currentTarget).val(), 10) || 0)) / 100;
            this._setValue(toRgba(o));
        },

        _onTextInput: function (ev) {
            var v = $(ev.currentTarget).val();
            var o = parseRgba(v);
            $(ev.currentTarget).toggleClass('is-invalid', v.trim() !== '' && !o);
            if (o) {
                this._applyLive(this._sync(o, 'text'));
            }
        },
        _onTextCommit: function (ev) {
            var o = parseRgba($(ev.currentTarget).val());
            if (o) {
                this._setValue(toRgba(o));
            }
        },
    });

    fieldRegistry.add('pns_color', PnsColorField);

    return PnsColorField;
});
