# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2025-12-01

### Added
- Diagonal corner ribbon with configurable text, colors and opacity.
- Configuration wizard at *Settings > Technical > Ribbon* (admin only).
- Native `<input type="color">` picker with synchronized opacity slider and pasteable `rgba(...)` field.
- Live preview of text + colors while editing.
- History grid of the last 20 color combinations (click to reuse, × to remove).
- Variables: `{dbname}`, `{db_name}`, `{user}`, `{company}`.
- Master on/off switch (`pns_ribbon.enabled`) to hide the ribbon without uninstalling.
- Shadow toggle (`pns_ribbon.shadow`) for a flatter look.
- Framework-agnostic ribbon injection: works on Odoo 13 through 19+ without changes.
- OWL1 stack (Odoo 13-14) and OWL2 stack (Odoo 15-19+).
