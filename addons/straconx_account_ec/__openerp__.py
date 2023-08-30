# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012 - present STRACONX S.A. (http://openerp.straconx.com) All Rights Reserved.
#
##############################################################################

{
    "name": "Ecuador - Chart of Accounts NIIF 2012",
    "version": "1.0",
    "author": "STRACONX S.A.",
    "category": "Localization/Account Charts",
    "website": "http://openerp.straconx.com",
    "description": """
    Ecuador Chart of Accounts NIIF 2012
    * Chart of Accounts based for PYMES under Superintendencia de Compañías standars.
    * Defines tax code templates under Servicio de Rentas Internas standars.
    * Define the banks of Ecuador and add fields for a usability under taxes laws.
    * Create a structure for cash box, point of sales and warehouses for ecuadorian companies.
    """,
    "license": "GPL-3",
    "depends": ["straconx_vat",
                "straconx_states",
                "straconx_account"
                ],
    "init_xml": [],
    "update_xml": ["data/account_types.xml",
                   "data/ecuadorian_banks.xml",
                   "data/account_chart.xml",
                   "data/taxes_data.xml",
                   # "data/public_partners.xml",
                   "wizard/l10n_chart_ec_wizard.xml",
                   ],
    "demo_xml": [],
    "active": False,
    "installable": True,
    "auto_install": False
}