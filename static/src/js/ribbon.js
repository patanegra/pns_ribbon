(function() {
    "use strict";

    // -----------------------------------------------------------------------
    // ribbon.js — PNS Ribbon environment indicator (client-side).
    //
    // This script is injected into every page via a QWeb ``web.layout``
    // inheritance.  It reads its configuration from ``window.pns_ribbon_data``
    // (server-rendered in the ``<head>``) and creates a fixed-position
    // ``<div id="pns-ribbon">`` in the top-left corner.
    //
    // The script is **framework-agnostic**: no dependency on ``odoo.define``,
    // OWL, jQuery or any bundler.  It works identically across Odoo 13-19+.
    //
    // Configuration object (``window.pns_ribbon_data``):
    //   db         — database name (fallback: ``odoo.session_info.db``)
    //   user       — current user's display name
    //   company    — current company's name
    //   html       — ribbon text with ``<br>`` for line breaks
    //   color      — CSS text color  (e.g. ``rgba(255,255,255,1)``)
    //   background — CSS background  (e.g. ``rgba(255,0,0,0.5)``)
    //   enabled    — master switch   (``'0'`` / ``'False'`` = hidden)
    //   shadow     — shadow toggle   (``'0'`` = flat, no shadow/border)
    // -----------------------------------------------------------------------

    /**
     * Return ``true`` if *v* represents a falsy/"off" value.
     * Recognized: ``'0'``, ``'False'``, ``'false'``, boolean ``false``.
     */
    function isOff(v) {
        return v === '0' || v === 'False' || v === 'false' || v === false;
    }

    /** Replace **all** occurrences of *needle* in *haystack* with *value*. */
    function replaceAll(haystack, needle, value) {
        return (haystack || '').split(needle).join(value || '');
    }

    /**
     * Build (or rebuild) the ribbon ``<div>`` from a configuration object.
     *
     * If the ribbon is disabled (``data.enabled`` is falsy) or has already
     * been injected, it is removed first — this allows live rebuilds.
     */
    function buildRibbon(data) {
        data = data || {};

        // Remove any existing ribbon to allow live rebuilds.
        var existing = document.getElementById('pns-ribbon');
        if (existing && existing.parentNode) {
            existing.parentNode.removeChild(existing);
        }

        // Master switch: when disabled, nothing is rendered.
        if (isOff(data.enabled)) {
            return;
        }

        var dbName = data.db || "";
        if (!dbName && window.odoo && window.odoo.session_info && window.odoo.session_info.db) {
            dbName = window.odoo.session_info.db;
        }

        var html = data.html;
        if (html === 'False') html = '';

        // Text to display (fallback to default placeholder).
        var ribbonText = html || "TEST<br>{dbname}";

        // Substitute dynamic placeholders (all occurrences).
        ribbonText = replaceAll(ribbonText, '{dbname}', dbName);
        ribbonText = replaceAll(ribbonText, '{db_name}', dbName);
        ribbonText = replaceAll(ribbonText, '{user}', data.user);
        ribbonText = replaceAll(ribbonText, '{company}', data.company);

        // Un-escape HTML entities (e.g. ``&lt;br&gt;`` produced by Odoo's
        // ``t-esc`` directive).
        var txt = document.createElement("textarea");
        txt.innerHTML = ribbonText;
        ribbonText = txt.value;

        var ribbon = document.createElement('div');
        ribbon.id = 'pns-ribbon';
        ribbon.innerHTML = ribbonText;

        if (data.color && data.color !== 'False') {
            ribbon.style.color = data.color;
        }
        if (data.background && data.background !== 'False') {
            ribbon.style.backgroundColor = data.background;
        }

        // Optional shadow: removing box-shadow AND the dashed border makes
        // the ribbon flat and discreet.
        if (isOff(data.shadow)) {
            ribbon.style.setProperty('box-shadow', 'none', 'important');
            ribbon.style.setProperty('border', 'none', 'important');
        }

        document.body.appendChild(ribbon);
    }

    /** Initial injection: read server-rendered data from ``<head>``. */
    function injectRibbon() {
        buildRibbon(window.pns_ribbon_data || {});
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(injectRibbon, 1000);
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(injectRibbon, 1000);
        });
    }
})();
