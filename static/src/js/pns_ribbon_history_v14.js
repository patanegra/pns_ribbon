odoo.define('pns_ribbon.PnsRibbonHistory', function (require) {
    "use strict";
    // -----------------------------------------------------------------------
    // pns_ribbon_history — Legacy widget for Odoo 13-14 (owl1 / AbstractField).
    //
    // Displays a flex-wrap grid of colored cards, one per recent color
    // combination stored in the ``pns_ribbon.history`` system parameter.
    //
    // Interactions:
    //   • Click on a card → fills the form fields with that entry.
    //   • Click "×" on a card → deletes that entry from the history
    //     (server-side, no confirmation dialog).
    // -----------------------------------------------------------------------

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');

    var PnsRibbonHistory = AbstractField.extend({
        className: 'o_field_pns_ribbon_history',
        supportedFieldTypes: ['char', 'text'],

        _renderEdit: function () { this._renderItems(); },
        _renderReadonly: function () { this._renderItems(); },

        /** Parse the JSON value from the record into an array of entries. */
        _entries: function () {
            try {
                var raw = this._histJson != null ? this._histJson : (this.value || '[]');
                var data = JSON.parse(raw);
                return _.isArray(data) ? data : [];
            } catch (e) {
                return [];
            }
        },

        /** Build the colored card grid from the current entries. */
        _renderItems: function () {
            var self = this;
            this.$el.empty().addClass('d-flex flex-wrap');
            var entries = this._entries();
            if (!entries.length) {
                this.$el.append($('<span class="text-muted"/>').text('—'));
                return;
            }
            entries.forEach(function (entry) {
                var $item = $('<div/>').css({
                    'position': 'relative',
                    'margin': '8px 6px 0 0',
                });
                var $del = $('<span/>').text('×').attr('title', 'Remove').css({
                    'position': 'absolute',
                    'top': '-7px',
                    'right': '-7px',
                    'width': '16px',
                    'height': '16px',
                    'line-height': '14px',
                    'text-align': 'center',
                    'border-radius': '50%',
                    'background': '#fff',
                    'border': '1px solid #888',
                    'color': '#444',
                    'font-size': '11px',
                    'cursor': 'pointer',
                });
                var $box = $('<div/>').attr('title', 'Click to reuse').css({
                    'padding': '6px 12px',
                    'border-radius': '4px',
                    'font-weight': 'bold',
                    'text-align': 'center',
                    'min-width': '110px',
                    'cursor': 'pointer',
                    'color': entry.fg || '',
                    'background': entry.bg || '',
                }).text(entry.text || '');
                $del.on('click', function (ev) { ev.stopPropagation(); self._remove(entry); });
                $box.on('click', function () { self._apply(entry); });
                $item.append($del).append($box);
                self.$el.append($item);
            });
        },

        /** Apply a history entry to the wizard form fields. */
        _apply: function (entry) {
            this.trigger_up('field_changed', {
                dataPointID: this.dataPointID,
                changes: {
                    ribbon_text: entry.text || '',
                    text_color: entry.fg || '',
                    bg_color: entry.bg || '',
                },
            });
        },

        /** Remove a history entry server-side and refresh the local state. */
        _remove: function (entry) {
            var self = this;
            this._rpc({
                model: 'pns.ribbon.config',
                method: 'action_remove_history',
                args: [entry.fg, entry.bg],
            }).then(function (json) {
                // Immediate local repaint: do not depend on the legacy client
                // propagating the field change (it was readonly before and
                // would be ignored).
                self._histJson = json;
                self._renderItems();
                self.trigger_up('field_changed', {
                    dataPointID: self.dataPointID,
                    changes: { history_json: json },
                });
            });
        },
    });

    fieldRegistry.add('pns_ribbon_history', PnsRibbonHistory);
    return PnsRibbonHistory;
});
