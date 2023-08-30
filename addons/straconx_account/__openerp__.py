# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012 - present STRACONX S.A. (http://openerp.straconx.com) All Rights Reserved.
#
##############################################################################

{
    "name": "Ecuador - Account Personalization",
    "version": "1.0",
    "author": "STRACONX S.A.",
    "category": "Localization/Account Charts",
    "website": "http://openerp.straconx.com",
    "description": """
    Ecuador - Account Personalization
    * Create a structure for cash box, point of sales and warehouses for ecuadorian companies.
    """,
    "license": "GPL-3",
    "depends": ["account",
                "analytic",
                "sale",
                "purchase",
                "web_remove_quick_create",
                "account_payment",
                "straconx_warning",
                "straconx_vat",
                "pentaho_reports",
                "hr"
                ],
    "init_xml": ["data/no_dashboard.xml"],
    "update_xml": ["data/straconx_data.xml",
                   "data/payment_term_data.xml",
                   "report/straconx_move_report.xml",
                   "wizard/straconx_account_chart_view.xml",
                   "wizard/account_crossing_reconcile_view.xml",
                   "views/straconx_company.xml",
                   "views/straconx_account_view.xml",
                   "views/types_view.xml",
                   "views/res_partner_address.xml",
                   "views/journal_view.xml",
                   "views/account_template.xml",
                   "views/account_tax_view.xml",
                   "views/printer_point_view.xml",
                   "views/res_user_view.xml",
                   "views/shop_view.xml",
                   "views/straconx_area.xml",
                   "views/res_bank_view.xml",
                   "views/straconx_menu.xml",
                   "security/security.xml",
                   "security/ir.model.access.csv",
                   ],
    "demo_xml": [],
    "active": True,
    "installable": True,
    "auto_install": False
}