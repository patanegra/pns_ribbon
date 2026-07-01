# Contributing to PNS Ribbon

Thank you for your interest in contributing!

## Reporting Issues

Please [open an issue](../../issues) with:
- Your Odoo version (e.g. 17.0, 14.0).
- Steps to reproduce the problem.
- Expected vs. actual behavior.

## Development Setup

The development repository uses a **multi-stack layout** that differs from
what end users see on GitHub.  The published branches (13.0, 14.0, …, 19.0)
are generated automatically from this layout by `publish.sh`.

### Source layout

```
pns_ribbon/                         ← development repo (main branch)
├── common/                         # Shared across all Odoo versions
│   ├── LICENSE                     # Apache 2.0
│   ├── data/parameters.xml        # Default system parameters (noupdate)
│   └── static/description/        # Module icon, screenshots
├── stacks/
│   ├── owl1/pns_ribbon/            # Odoo 13-14 (legacy widgets)
│   └── owl2/pns_ribbon/            # Odoo 15-19+ (OWL components)
├── docs/                           # Internal documentation
├── CHANGELOG.md
├── CONTRIBUTING.md
└── README.md
```

### How stacks work

- **`common/`** contains files shared by all Odoo versions: data XML, static
  assets (icon, screenshots), and the LICENSE.
- **`stacks/owl1/`** and **`stacks/owl2/`** each contain a complete module
  directory.  The only differences between stacks are the widget registration
  mechanism (legacy `AbstractField` vs OWL `Component`) and the asset
  declaration format (`<template inherit_id>` vs `<record model="ir.asset">`).
- **`publish.sh`** merges `common/` + `stacks/owlX/` into flat, installable
  branches per Odoo version and pushes them to GitHub.

### Publishing workflow

```bash
# After making changes on main:
git push origin main                             # push to internal bare
publish.sh --remote github --force               # regenerate version branches
```

See the internal doc `git_2_implementacion.md` in `pns_suite/docs/` for the
full procedure.

## Pull Requests

1. Fork the repository and create a branch from `main`.
2. Make your changes — keep commits focused and well-described.
3. Ensure comments and docstrings are in English.
4. Open a pull request with a clear description of what you changed and why.

## Code Style

- **Python**: PEP 8.  Docstrings in English with examples where helpful (see `ribbon_config.py` for the pattern).
- **JavaScript**: Standard style, JSDoc on exported functions.
- **No framework dependencies in the ribbon itself** — `ribbon.js` and `ribbon.css` must remain vanilla (no `odoo.define`, no OWL, no jQuery).

## License

By contributing you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
