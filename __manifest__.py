# -*- coding: utf-8 -*-
{
    'name': 'PNS Ribbon',
    'version': '1.0.0',
    'category': 'Web',
    'summary': 'Visual ribbon (TEST/DEV banner) to identify non-production instances.',
    'description': """
Lightweight module that shows a configurable ribbon/banner in the corner
to clearly identify non-production instances (TEST/DEV).

Works on all Odoo versions (13-19+).

Where to configure (administrators only):
Settings > Technical > Ribbon

- Text (one line per row; variables {dbname}, {user}, {company}).
- Text and background color in a single rgba(r, g, b, a) format: color
  picker plus opacity control plus pasteable rgba field, with validation
  and live preview.
- History of the last 20 color combinations (no duplicates), shown as a
  grid, reusable with one click and removable with an "x".

Or via Settings > Technical > Parameters > System Parameters:

- pns_ribbon.html : text to show ({dbname} = database name).
- pns_ribbon.textColor : text color, e.g. rgba(255, 255, 255, 1).
- pns_ribbon.backgroundColor : background color, e.g. rgba(255, 0, 0, 0.5).
""",
    'author': 'PATANEGRA Soft',
    'website': 'https://patanegra.com',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'data/parameters.xml',
        'views/ribbon_config_views.xml',
        'views/assets.xml',
    ],
    # Apache License 2.0 — see LICENSE file
    'license': 'Other OSI approved licence',
    'installable': True,
    'auto_install': False,
}
