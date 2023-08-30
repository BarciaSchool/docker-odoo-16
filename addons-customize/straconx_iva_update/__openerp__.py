# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2016 - present STRACONX S.A. (http://openerp.straconx.com) All Rights Reserved.
#
##############################################################################

{
    "name": "Ecuador - New IVA Taxes 2016",
    "version": "1.0",
    "author": "STRACONX S.A.",
    "category": "Localization/Account Charts",
    "website": "http://openerp.straconx.com",
    "description": """New Taxes 2016""",
    "license": "GPL-3",
    "depends": ["straconx_account_ec"],
    "init_xml": [],
    "update_xml": ["data/taxes_data.xml",
                   "data/update_taxes.sql",
                   ],
    "demo_xml": [],
    "active": True,
    "installable": True,
    "application": False,
    "auto_install": False
}