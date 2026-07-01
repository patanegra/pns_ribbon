/** @odoo-module **/
// ---------------------------------------------------------------------------
// pns_ribbon_history — OWL2 history widget (Odoo 15-19+).
//
// Displays a flex-wrap grid of colored cards, one per recent color
// combination stored in the ``pns_ribbon.history`` system parameter.
// Each card shows the ribbon text with the corresponding foreground and
// background colors.
//
// Interactions:
//   • **Click** on a card → fills the form fields with that entry.
//   • **Click "×"** on a card → deletes that entry from the history
//     (server-side, no confirmation dialog).
// ---------------------------------------------------------------------------

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class PnsRibbonHistory extends Component {
    static template = "pns_ribbon.PnsRibbonHistory";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ entries: this._read() });
    }

    /** Parse the JSON value from the record into an array of entries. */
    _read() {
        const rec = this.props.record;
        const raw = (rec ? rec.data[this.props.name] : this.props.value) || "[]";
        try {
            const data = JSON.parse(raw);
            return Array.isArray(data) ? data : [];
        } catch (e) {
            return [];
        }
    }

    /** Apply a history entry to the wizard form fields. */
    apply(entry) {
        const rec = this.props.record;
        if (!rec) {
            return;
        }
        rec.update({
            ribbon_text: entry.text || "",
            text_color: entry.fg || "",
            bg_color: entry.bg || "",
        });
    }

    /** Remove a history entry server-side and refresh the local state. */
    async remove(entry, ev) {
        ev.stopPropagation();
        const rec = this.props.record;
        const model = rec ? rec.resModel : "pns.ribbon.config";
        let json;
        try {
            json = await this.orm.call(model, "action_remove_history", [entry.fg, entry.bg]);
        } catch (e) {
            json = JSON.stringify(this.state.entries.filter((e2) => e2 !== entry));
        }
        this.state.entries = JSON.parse(json || "[]");
        // Sync the field value: prevents a re-render / re-mount of the form
        // from reviving the just-deleted entry by reading stale JSON.
        if (rec) {
            try {
                await rec.update({ [this.props.name]: json });
            } catch (e) {
                // On versions where the field doesn't accept update, local
                // state is sufficient.
            }
        }
    }
}

export const pnsRibbonHistory = {
    component: PnsRibbonHistory,
    supportedTypes: ["char", "text"],
};

registry.category("fields").add("pns_ribbon_history", pnsRibbonHistory);
