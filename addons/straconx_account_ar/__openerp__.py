# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012 - present STRACONX S.A. (http://openerp.straconx.com) All Rights Reserved.
#
##############################################################################

{
    "name": "Argentina - Construction Chart of Accounts",
    "version": "1.0",
    "author": "STRACONX S.A.",
    "category": "Localization/Account Charts",
    "website": "http://openerp.straconx.com",
    "description": """
    Argentina Chart of Accounts
    * Chart of Accounts based for Argentina.
    """,
    "license": "GPL-3",
    "depends": ["straconx_account",
                "straconx_states_ar",
                "straconx_afip"
                ],
    "init_xml": [],
    "update_xml": ["data/account_types.xml",
                   "data/argentina_banks.xml",
                   "data/account_chart.xml",
                   "data/taxes_data.xml",
                   "data/public_partners.xml",
                   "wizard/l10n_chart_ar_wizard.xml",
                   "views/strx_res_currency_view.xml"
                   ],
    "demo_xml": [],
    "active": False,
    "installable": True,
    "auto_install": False
}