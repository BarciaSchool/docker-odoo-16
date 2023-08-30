# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################


{
    "name" : "Ecuador - module for consolidation cash company BUEN HOGAR",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "category" : "Ecuadorian Location/Consolidation Cash",
    "website" : "http://openerp.straconx.com",
    "description": """
    Module that permit make consolidation cash of expenses and incomes.
    """,
    "license" : "GPL-3",
    "depends" : [
                 "straconx_account",
                 "straconx_account_bh",
                ],
    "init_xml" : [],
    "update_xml" : [
                    'report/straconx_cash_consolidation_report.xml',                    
                    'data/data.xml',
                    'wizard/open_cash_consolidation.xml',
                    'views/cash_consolidation_view.xml',
                    'views/move_type_view.xml',
                    'views/invoice_type_view.xml',
                    'views/straconx_menu.xml',
                    ],
    "demo_xml" : [],
    "installable": True
}