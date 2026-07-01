# -*- coding: utf-8 -*-
"""Tests for pns_ribbon — color parsing, normalization, history and config.

This module covers:

* **Pure-function unit tests** (``TestColorParsing``, ``TestParamBool``,
  ``TestHexToRgba``) — no Odoo dependency, fast, run anywhere.
* **Odoo integration tests** (``TestRibbonConfig``) — require a running
  Odoo test database, exercise the wizard's ``default_get``,
  ``action_save`` and ``action_remove_history`` flows against real
  ``ir.config_parameter`` records.
"""

import json
import unittest

from odoo.tests.common import TransactionCase

from ..models.ribbon_config import (
    _parse_rgba,
    _is_valid_color,
    _to_rgba,
    _normalize_color,
    _hex_to_rgba,
    _param_bool,
    _load_history,
    _push_history,
    _entry_key,
    _DEFAULT_FG,
    _DEFAULT_BG,
    _HISTORY_LIMIT,
    PARAM_HTML,
    PARAM_FG,
    PARAM_BG,
    PARAM_ENABLED,
    PARAM_SHADOW,
    PARAM_HISTORY,
)


# ---------------------------------------------------------------------------
# Pure-function tests (no Odoo required)
# ---------------------------------------------------------------------------

class TestColorParsing(unittest.TestCase):
    """Test ``_parse_rgba`` and ``_is_valid_color`` with various inputs."""

    # --- _parse_rgba ---------------------------------------------------------

    def test_hex_6_digit(self):
        self.assertEqual(_parse_rgba('#FF0000'), (255, 0, 0, 1.0))

    def test_hex_3_digit(self):
        self.assertEqual(_parse_rgba('#0AF'), (0, 170, 255, 1.0))

    def test_hex_lowercase(self):
        self.assertEqual(_parse_rgba('#ff8000'), (255, 128, 0, 1.0))

    def test_rgb(self):
        self.assertEqual(_parse_rgba('rgb(10, 20, 30)'), (10, 20, 30, 1.0))

    def test_rgba(self):
        self.assertEqual(_parse_rgba('rgba(10, 20, 30, 0.5)'), (10, 20, 30, 0.5))

    def test_rgba_full_opacity(self):
        self.assertEqual(_parse_rgba('rgba(0, 0, 0, 1)'), (0, 0, 0, 1.0))

    def test_rgba_zero_opacity(self):
        self.assertEqual(_parse_rgba('rgba(0, 0, 0, 0)'), (0, 0, 0, 0.0))

    def test_rgba_whitespace(self):
        self.assertEqual(
            _parse_rgba('  rgba( 10 , 20 , 30 , 0.5 )  '),
            (10, 20, 30, 0.5),
        )

    def test_invalid_none(self):
        self.assertIsNone(_parse_rgba(None))

    def test_invalid_empty(self):
        self.assertIsNone(_parse_rgba(''))

    def test_invalid_garbage(self):
        self.assertIsNone(_parse_rgba('not-a-color'))

    def test_invalid_named_color(self):
        # We intentionally do NOT support CSS named colors.
        self.assertIsNone(_parse_rgba('red'))

    def test_clamps_rgb_to_255(self):
        r, g, b, a = _parse_rgba('rgb(999, 0, 0)')
        self.assertEqual(r, 255)

    def test_clamps_alpha(self):
        _, _, _, a = _parse_rgba('rgba(0, 0, 0, 0.999)')
        self.assertLessEqual(a, 1.0)

    # --- _is_valid_color -----------------------------------------------------

    def test_valid_hex(self):
        self.assertTrue(_is_valid_color('#ABC'))

    def test_valid_rgba(self):
        self.assertTrue(_is_valid_color('rgba(0, 0, 0, 0.5)'))

    def test_invalid_string(self):
        self.assertFalse(_is_valid_color('banana'))

    # --- _to_rgba / _normalize_color -----------------------------------------

    def test_to_rgba_from_hex(self):
        result = _to_rgba('#FF0000', _DEFAULT_FG)
        self.assertEqual(result, 'rgba(255, 0, 0, 1)')

    def test_to_rgba_from_short_hex(self):
        result = _to_rgba('#0AF', _DEFAULT_FG)
        self.assertEqual(result, 'rgba(0, 170, 255, 1)')

    def test_to_rgba_passthrough(self):
        result = _to_rgba('rgba(10, 20, 30, 0.5)', _DEFAULT_FG)
        self.assertEqual(result, 'rgba(10, 20, 30, 0.5)')

    def test_to_rgba_invalid_falls_back(self):
        result = _to_rgba('garbage', 'rgba(1, 2, 3, 0.4)')
        self.assertEqual(result, 'rgba(1, 2, 3, 0.4)')

    def test_normalize_is_alias(self):
        a = _to_rgba('#FFF', _DEFAULT_FG)
        b = _normalize_color('#FFF', _DEFAULT_FG)
        self.assertEqual(a, b)


class TestParamBool(unittest.TestCase):
    """Test ``_param_bool`` — boolean coercion of system parameter values."""

    def test_true_values(self):
        for v in ('1', 'true', 'True', 'yes', 'anything'):
            self.assertTrue(_param_bool(v), f'{v!r} should be True')

    def test_false_values(self):
        for v in ('0', 'false', 'False', 'off', 'no', 'OFF', 'NO'):
            self.assertFalse(_param_bool(v), f'{v!r} should be False')

    def test_none_default_true(self):
        self.assertTrue(_param_bool(None, default=True))

    def test_none_default_false(self):
        self.assertFalse(_param_bool(None, default=False))

    def test_empty_default_true(self):
        self.assertTrue(_param_bool('', default=True))


class TestHexToRgba(unittest.TestCase):
    """Test ``_hex_to_rgba`` — legacy history format conversion."""

    def test_basic(self):
        self.assertEqual(_hex_to_rgba('#FF0000', 50), 'rgba(255, 0, 0, 0.5)')

    def test_full_opacity(self):
        self.assertEqual(_hex_to_rgba('#00FF00', 100), 'rgba(0, 255, 0, 1.0)')

    def test_zero_opacity(self):
        self.assertEqual(_hex_to_rgba('#0000FF', 0), 'rgba(0, 0, 255, 0.0)')

    def test_short_hex(self):
        result = _hex_to_rgba('#F00', 75)
        self.assertEqual(result, 'rgba(255, 0, 0, 0.75)')

    def test_invalid_hex_returns_default(self):
        result = _hex_to_rgba('garbage', 50)
        self.assertEqual(result, _DEFAULT_BG)


class TestEntryKey(unittest.TestCase):
    """Test ``_entry_key`` — deduplication key for history entries."""

    def test_simple(self):
        entry = {'text': 'TEST', 'fg': '#FFF', 'bg': '#F00'}
        fg, bg = _entry_key(entry)
        self.assertEqual(fg, 'rgba(255, 255, 255, 1)')
        self.assertEqual(bg, 'rgba(255, 0, 0, 1)')

    def test_text_ignored(self):
        """The text content does NOT affect the dedup key."""
        a = _entry_key({'text': 'A', 'fg': '#FFF', 'bg': '#F00'})
        b = _entry_key({'text': 'B', 'fg': '#FFF', 'bg': '#F00'})
        self.assertEqual(a, b)

    def test_legacy_opacity(self):
        """Legacy entries with ``op`` field get properly normalized."""
        entry = {'text': 'X', 'fg': '#FFF', 'bg': '#FF0000', 'op': 50}
        fg, bg = _entry_key(entry)
        self.assertEqual(bg, 'rgba(255, 0, 0, 0.5)')


# ---------------------------------------------------------------------------
# Odoo integration tests
# ---------------------------------------------------------------------------

class TestRibbonConfig(TransactionCase):
    """Integration tests for the ``pns.ribbon.config`` wizard.

    These tests exercise the full wizard lifecycle against a real Odoo
    database, verifying that ``default_get`` reads parameters, ``action_save``
    writes them, and ``action_remove_history`` modifies the persisted JSON.
    """

    def _icp(self):
        return self.env['ir.config_parameter'].sudo()

    def _set_params(self, **kwargs):
        icp = self._icp()
        mapping = {
            'html': PARAM_HTML,
            'fg': PARAM_FG,
            'bg': PARAM_BG,
            'enabled': PARAM_ENABLED,
            'shadow': PARAM_SHADOW,
            'history': PARAM_HISTORY,
        }
        for short, value in kwargs.items():
            icp.set_param(mapping[short], value)

    def _create_wizard(self):
        return self.env['pns.ribbon.config'].create({})

    # --- default_get ---------------------------------------------------------

    def test_default_get_reads_params(self):
        """Wizard should populate fields from ir.config_parameter."""
        self._set_params(
            html='STAGING<br>{dbname}',
            fg='rgba(0, 0, 0, 1)',
            bg='rgba(0, 128, 255, 0.6)',
            enabled='1',
            shadow='0',
        )
        wiz = self._create_wizard()
        self.assertEqual(wiz.ribbon_text, 'STAGING\n{dbname}')
        self.assertEqual(wiz.text_color, 'rgba(0, 0, 0, 1)')
        self.assertEqual(wiz.bg_color, 'rgba(0, 128, 255, 0.6)')
        self.assertTrue(wiz.enabled)
        self.assertFalse(wiz.shadow)

    def test_default_get_normalizes_hex(self):
        """Hex colors stored in params should be normalized to rgba."""
        self._set_params(fg='#FFFFFF', bg='#FF0000')
        wiz = self._create_wizard()
        self.assertEqual(wiz.text_color, 'rgba(255, 255, 255, 1)')
        self.assertEqual(wiz.bg_color, 'rgba(255, 0, 0, 1)')

    # --- action_save ---------------------------------------------------------

    def test_action_save_writes_params(self):
        """Saving the wizard should persist all values to ir.config_parameter."""
        wiz = self._create_wizard()
        wiz.ribbon_text = 'DEV\n{dbname}'
        wiz.text_color = '#FFFFFF'
        wiz.bg_color = 'rgba(0, 200, 0, 0.7)'
        wiz.enabled = False
        wiz.shadow = True

        result = wiz.action_save()

        icp = self._icp()
        self.assertEqual(icp.get_param(PARAM_HTML), 'DEV<br>{dbname}')
        self.assertEqual(icp.get_param(PARAM_FG), 'rgba(255, 255, 255, 1)')
        self.assertEqual(icp.get_param(PARAM_BG), 'rgba(0, 200, 0, 0.7)')
        self.assertEqual(icp.get_param(PARAM_ENABLED), '0')
        self.assertEqual(icp.get_param(PARAM_SHADOW), '1')

        # action_save returns a reload action.
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'reload')

    def test_action_save_pushes_history(self):
        """Each save should add a history entry."""
        wiz = self._create_wizard()
        wiz.ribbon_text = 'TEST'
        wiz.text_color = 'rgba(255, 255, 255, 1)'
        wiz.bg_color = 'rgba(255, 0, 0, 0.5)'
        wiz.action_save()

        history = json.loads(self._icp().get_param(PARAM_HISTORY, '[]'))
        self.assertGreaterEqual(len(history), 1)
        latest = history[0]
        self.assertEqual(latest['text'], 'TEST')
        self.assertEqual(latest['fg'], 'rgba(255, 255, 255, 1)')

    # --- action_remove_history -----------------------------------------------

    def test_remove_history_entry(self):
        """Removing a history entry should persist the change."""
        # Seed two entries.
        self._set_params(history=json.dumps([
            {'text': 'A', 'fg': 'rgba(255, 255, 255, 1)', 'bg': 'rgba(255, 0, 0, 0.5)'},
            {'text': 'B', 'fg': 'rgba(0, 0, 0, 1)', 'bg': 'rgba(0, 128, 0, 0.5)'},
        ]))

        Model = self.env['pns.ribbon.config']
        result_json = Model.action_remove_history(
            'rgba(255, 255, 255, 1)',
            'rgba(255, 0, 0, 0.5)',
        )
        result = json.loads(result_json)
        # Only entry B should remain.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'B')

    # --- history deduplication -----------------------------------------------

    def test_history_dedup(self):
        """Saving with the same colors twice should not duplicate the entry."""
        wiz = self._create_wizard()
        wiz.ribbon_text = 'FIRST'
        wiz.text_color = 'rgba(255, 255, 255, 1)'
        wiz.bg_color = 'rgba(255, 0, 0, 0.5)'
        wiz.action_save()

        wiz2 = self._create_wizard()
        wiz2.ribbon_text = 'SECOND'
        wiz2.text_color = 'rgba(255, 255, 255, 1)'
        wiz2.bg_color = 'rgba(255, 0, 0, 0.5)'
        wiz2.action_save()

        history = json.loads(self._icp().get_param(PARAM_HISTORY, '[]'))
        # Same color pair → only one entry (most recent text wins).
        fg_bg_pairs = [(e['fg'], e['bg']) for e in history]
        unique_pairs = set(fg_bg_pairs)
        self.assertEqual(len(fg_bg_pairs), len(unique_pairs))
