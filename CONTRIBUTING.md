# Contributing to PNS Ribbon

Thank you for your interest in contributing!

## Reporting Issues

Please [open an issue](../../issues) with:
- Your Odoo version (e.g. 17.0, 14.0).
- Steps to reproduce the problem.
- Expected vs. actual behavior.

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
