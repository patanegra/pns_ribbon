# -*- coding: utf-8 -*-
"""Configuration wizard for the PNS Ribbon environment indicator.

This module provides a TransientModel-based wizard that reads and writes
the ``ir.config_parameter`` entries consumed by the client-side ribbon
(``ribbon.js``).  It is the single source of truth for the ribbon
appearance and includes:

* **Text** — multi-line, stored as ``<br>``-joined HTML.
* **Colors** — always normalized to a canonical ``rgba(r, g, b, a)``
  string (accepts ``#hex``, ``rgb(...)`` and ``rgba(...)`` on input).
* **History** — a JSON list of the 20 most recent color combinations
  (deduplicated by the ``(fg, bg)`` pair), persisted server-side in
  ``ir.config_parameter``.
* **Master switch** — ``enabled`` flag to hide the ribbon without
  uninstalling the module.
* **Shadow toggle** — cosmetic ``shadow`` flag to remove the drop-shadow
  and dashed border for a flatter look.

Example — how the wizard interacts with ``ir.config_parameter``::

    # Read current ribbon text
    icp = self.env['ir.config_parameter'].sudo()
    html = icp.get_param('pns_ribbon.html', '')   # e.g. "TEST<br>{dbname}"

    # Write a new background color
    icp.set_param('pns_ribbon.backgroundColor', 'rgba(0, 128, 255, 0.6)')
"""

import json
import re

from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError

# ---------------------------------------------------------------------------
# System-parameter keys.  Every key lives under the ``pns_ribbon.`` namespace
# to avoid collisions with the OCA module ``web_environment_ribbon`` (which
# uses ``ribbon.*``).
# ---------------------------------------------------------------------------
PARAM_HTML = 'pns_ribbon.html'
PARAM_FG = 'pns_ribbon.textColor'
PARAM_BG = 'pns_ribbon.backgroundColor'
PARAM_HISTORY = 'pns_ribbon.history'
PARAM_ENABLED = 'pns_ribbon.enabled'
PARAM_SHADOW = 'pns_ribbon.shadow'


def _param_bool(value, default=True):
    """Interpret an ``ir.config_parameter`` value as a boolean.

    Falsy strings (``'0'``, ``'false'``, ``'off'``, ``'no'``) are treated
    as ``False``; everything else (including ``None`` / empty) falls back to
    *default*.

    Example::

        >>> _param_bool('1')
        True
        >>> _param_bool('off')
        False
        >>> _param_bool(None, default=True)
        True
    """
    if value is None or value == '':
        return default
    return str(value).strip().lower() not in ('0', 'false', 'off', 'no')


# ---------------------------------------------------------------------------
# Canonical color format: always ``rgba(r, g, b, a)``.
# Both text-color and background-color are persisted in this form.
# ---------------------------------------------------------------------------
_DEFAULT_FG = 'rgba(255, 255, 255, 1)'
_DEFAULT_BG = 'rgba(255, 0, 0, 0.5)'
_HISTORY_LIMIT = 20

_BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
_NL_RE = re.compile(r'\r\n|\r|\n')

# Input validation: we accept ``#hex``, ``rgb(...)`` and ``rgba(...)`` and
# normalize everything to ``rgba(r, g, b, a)`` on save.
_HEX_RE = re.compile(r'^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$')
_RGB_ANY_RE = re.compile(
    r'^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*'
    r'(?:,\s*(0|1|0?\.\d+)\s*)?\)$',
    re.IGNORECASE,
)


def _parse_rgba(value):
    """Parse a CSS color string into an ``(r, g, b, a)`` tuple.

    Accepts ``#hex`` (3 or 6 digits), ``rgb(r, g, b)`` and
    ``rgba(r, g, b, a)``.  Returns ``None`` if the input is invalid.

    Example::

        >>> _parse_rgba('#FF0000')
        (255, 0, 0, 1.0)
        >>> _parse_rgba('rgba(0, 128, 255, 0.5)')
        (0, 128, 255, 0.5)
        >>> _parse_rgba('not-a-color') is None
        True
    """
    v = (value or '').strip()
    if _HEX_RE.match(v):
        h = v[1:]
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = _RGB_ANY_RE.match(v)
    if m:
        r = min(255, int(m.group(1)))
        g = min(255, int(m.group(2)))
        b = min(255, int(m.group(3)))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, max(0.0, min(1.0, a)))
    return None


def _is_valid_color(value):
    """Return ``True`` if *value* is a recognized CSS color string."""
    return _parse_rgba(value) is not None


def _to_rgba(value, default):
    """Normalize any valid CSS color to ``'rgba(r, g, b, a)'``.

    Falls back to *default* if *value* is not parseable.

    Example::

        >>> _to_rgba('#0AF', 'rgba(0, 0, 0, 1)')
        'rgba(0, 170, 255, 1)'
    """
    parsed = _parse_rgba(value) or _parse_rgba(default) or (0, 0, 0, 1.0)
    r, g, b, a = parsed
    return 'rgba(%d, %d, %d, %s)' % (r, g, b, ('%g' % round(a, 3)))


def _normalize_color(value, default):
    """Alias for :func:`_to_rgba` — kept for readability at call sites."""
    return _to_rgba(value, default)


def _hex_to_rgba(hex_color, opacity):
    """Convert a legacy history entry (``#hex`` + integer opacity 0-100).

    Older history entries stored the background as a hex color with a
    separate integer opacity field.  This helper converts them to the
    current canonical ``rgba(...)`` format.

    Example::

        >>> _hex_to_rgba('#FF0000', 50)
        'rgba(255, 0, 0, 0.5)'
    """
    h = (hex_color or '').strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        op = min(100, max(0, int(opacity)))
    except (ValueError, TypeError):
        return _DEFAULT_BG
    return 'rgba(%d, %d, %d, %s)' % (r, g, b, round(op / 100.0, 3))


def _load_history(icp):
    """Load the history list from ``ir.config_parameter``.

    Returns a list of dicts (possibly empty) with at least ``text``,
    ``fg`` and ``bg`` keys.  Silently returns ``[]`` on parse errors.
    """
    raw = icp.get_param(PARAM_HISTORY, '') or ''
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []


def _entry_key(entry):
    """Deduplication key: the ``(fg, bg)`` color pair, normalized to rgba.

    The text content is intentionally excluded — we only want one entry per
    unique color combination in the history grid.
    """
    fg = entry.get('fg') or _DEFAULT_FG
    bg = entry.get('bg') or _DEFAULT_BG
    if 'op' in entry and _HEX_RE.match((bg or '').strip()):
        bg = _hex_to_rgba(bg, entry.get('op'))
    return (_normalize_color(fg, _DEFAULT_FG), _normalize_color(bg, _DEFAULT_BG))


def _push_history(icp, entry):
    """Add *entry* to the front of the history, removing any duplicate."""
    key = _entry_key(entry)
    history = [e for e in _load_history(icp) if _entry_key(e) != key]
    history.insert(0, entry)
    icp.set_param(PARAM_HISTORY, json.dumps(history[:_HISTORY_LIMIT]))


class RibbonConfig(models.TransientModel):
    """Interactive configuration wizard for the PNS Ribbon.

    Opened via *Settings > Technical > Ribbon* (administrators only).
    Reads current values from ``ir.config_parameter`` on ``default_get``,
    renders a live preview via ``onchange``, and writes back on save —
    then forces a full page reload so the ribbon JS picks up the new
    parameters immediately.

    **Design notes for AI/LLM readers:**

    * This is a ``TransientModel`` (wizard), not a regular model.  Records
      are ephemeral and do not persist between wizard openings.
    * Colors are always stored in canonical ``rgba(r, g, b, a)`` format.
      The wizard accepts ``#hex``, ``rgb(...)`` and ``rgba(...)`` on input
      and normalizes them before saving.
    * The history is a JSON array stored in a single ``ir.config_parameter``
      key (``pns_ribbon.history``).  Each entry is a dict with ``text``,
      ``fg`` and ``bg`` keys.  Entries are deduplicated by the ``(fg, bg)``
      pair — the most recent one wins.
    """

    _name = 'pns.ribbon.config'
    _description = 'Ribbon Configuration'

    enabled = fields.Boolean(
        string='Show ribbon', default=True,
        help="Uncheck to keep the module installed but fully hidden (e.g. in production).",
    )
    shadow = fields.Boolean(
        string='Drop shadow', default=True,
        help="Subtle shadow under the ribbon. Uncheck for a flatter, less noticeable look.",
    )
    ribbon_text = fields.Text(
        string='Ribbon text',
        help="One line per row. Variables: {dbname}, {user}, {company}.",
    )
    text_color = fields.Char(
        string='Text color', default=_DEFAULT_FG,
        help="Color in rgba(r, g, b, a) format. a is the opacity from 0 to 1.",
    )
    bg_color = fields.Char(
        string='Background color', default=_DEFAULT_BG,
        help="Color in rgba(r, g, b, a) format. a is the opacity from 0 to 1.",
    )
    preview = fields.Html(string='Preview', readonly=True, sanitize=False)
    # Translatable help legend (variables + color format), uses _() for .po.
    help_html = fields.Html(string='Help', readonly=True, sanitize=False)
    # JSON [{text, fg, bg}] consumed by the ``pns_ribbon_history`` widget
    # (click = reuse).  Not readonly so the widget can sync after deleting.
    history_json = fields.Text(string='Recent')

    def _help_html(self):
        """Build the translatable help text shown below the color fields."""
        line1 = _(
            "Variables: {dbname} = database / instance, {user} = current user, "
            "{company} = company. One line per row."
        )
        line2 = _(
            "Color format: always rgba(r, g, b, a). r, g, b are 0-255; a is the "
            "opacity from 0 (transparent) to 1 (opaque). Pick the color and set the "
            "opacity, or paste an rgba value."
        )
        return Markup(
            '<div class="text-muted">{}</div><div class="text-muted">{}</div>'
        ).format(line1, line2)

    def _substitute_vars(self, text):
        """Replace placeholder variables in the ribbon text.

        Supported placeholders (case-sensitive):

        * ``{dbname}`` / ``{db_name}`` — current database name
        * ``{user}`` — current user's display name
        * ``{company}`` — current company's name
        """
        text = text or ''
        db = self.env.cr.dbname
        text = text.replace('{dbname}', db).replace('{db_name}', db)
        text = text.replace('{user}', self.env.user.name or '')
        text = text.replace('{company}', self.env.company.name or '')
        return text

    def _render_preview(self, text, text_color, bg_color):
        """Return an HTML snippet for the live preview box.

        The preview mirrors the ribbon's final look with substituted
        variables, using inline styles so it works without extra CSS.
        """
        body = escape(self._substitute_vars(text)).replace('\n', Markup('<br/>'))
        fg = _normalize_color(text_color, _DEFAULT_FG)
        bg = _normalize_color(bg_color, _DEFAULT_BG)
        return Markup(
            '<div class="pns_ribbon_preview_box" '
            'style="display:inline-block;min-width:140px;padding:6px 18px;'
            'border-radius:4px;font-weight:bold;text-align:center;'
            'color:{fg};background:{bg};">{body}</div>'
        ).format(fg=fg, bg=bg, body=body)

    def _history_display(self, icp):
        """Return the normalized history as ``[{text, fg, bg}]`` for the widget.

        Handles backward compatibility with older history entries that stored
        the background as ``#hex`` + an integer ``op`` (opacity 0-100).
        Deduplicates by the ``(fg, bg)`` pair, keeping the most recent entry.
        """
        out = []
        seen = set()
        for entry in _load_history(icp):
            fg = entry.get('fg') or _DEFAULT_FG
            bg = entry.get('bg') or _DEFAULT_BG
            # Backward compat: old format stored bg as hex + integer opacity.
            if 'op' in entry and _HEX_RE.match((bg or '').strip()):
                bg = _hex_to_rgba(bg, entry.get('op'))
            fg = _normalize_color(fg, _DEFAULT_FG)
            bg = _normalize_color(bg, _DEFAULT_BG)
            key = (fg, bg)
            if key in seen:
                continue
            seen.add(key)
            out.append({'text': entry.get('text') or '', 'fg': fg, 'bg': bg})
        return out

    @api.model
    def default_get(self, fields_list):
        """Load current values from ``ir.config_parameter`` into the wizard."""
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        res['enabled'] = _param_bool(icp.get_param(PARAM_ENABLED, '1'), True)
        res['shadow'] = _param_bool(icp.get_param(PARAM_SHADOW, '1'), True)
        html = icp.get_param(PARAM_HTML, '') or ''
        res['ribbon_text'] = _BR_RE.sub('\n', html)
        res['text_color'] = _normalize_color(icp.get_param(PARAM_FG, ''), _DEFAULT_FG)
        res['bg_color'] = _normalize_color(icp.get_param(PARAM_BG, ''), _DEFAULT_BG)
        res['preview'] = self._render_preview(
            res.get('ribbon_text'), res.get('text_color'), res.get('bg_color'),
        )
        res['help_html'] = self._help_html()
        res['history_json'] = json.dumps(self._history_display(icp))
        return res

    @api.onchange('ribbon_text', 'text_color', 'bg_color')
    def _onchange_preview(self):
        """Refresh the preview box whenever text or colors change."""
        for record in self:
            record.preview = record._render_preview(
                record.ribbon_text, record.text_color, record.bg_color,
            )

    def _validated_color(self, value, default, label):
        """Parse and validate a color value; raise ``UserError`` if invalid."""
        v = (value or '').strip()
        if not v:
            return default
        if not _is_valid_color(v):
            raise UserError(_("Invalid color for %s: %s", label, v))
        return _to_rgba(v, default)

    def action_save(self):
        """Persist the wizard values to ``ir.config_parameter`` and reload.

        A full page reload (``ir.actions.client / reload``) ensures the
        ribbon JS re-reads all parameters from the server-rendered
        ``window.pns_ribbon_data`` block.  This is more robust than a
        live-update approach, which would depend on JS that might be
        cached by the browser or a proxy.
        """
        self.ensure_one()
        fg = self._validated_color(self.text_color, _DEFAULT_FG, _("Text color"))
        bg = self._validated_color(self.bg_color, _DEFAULT_BG, _("Background color"))
        html = _NL_RE.sub('<br>', self.ribbon_text or '')
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param(PARAM_ENABLED, '1' if self.enabled else '0')
        icp.set_param(PARAM_SHADOW, '1' if self.shadow else '0')
        icp.set_param(PARAM_HTML, html)
        icp.set_param(PARAM_FG, fg)
        icp.set_param(PARAM_BG, bg)
        _push_history(icp, {'text': self.ribbon_text or '', 'fg': fg, 'bg': bg})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def action_remove_history(self, fg, bg):
        """Remove a color combination from the history (no confirmation).

        Returns the updated history as a JSON string so the client-side
        widget can refresh immediately without a round-trip.
        """
        icp = self.env['ir.config_parameter'].sudo()
        target = (_normalize_color(fg, _DEFAULT_FG), _normalize_color(bg, _DEFAULT_BG))
        history = [e for e in _load_history(icp) if _entry_key(e) != target]
        icp.set_param(PARAM_HISTORY, json.dumps(history[:_HISTORY_LIMIT]))
        return json.dumps(self._history_display(icp))
