# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2009 - present STRACONX S.A. 
#    (http://openerp.straconx.com) All Rights Reserved.
#                       
#    This program is private software.
#
#
##############################################################################

{
    "name" : "Recosting for Invoices without cost",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "category" : "Generic Modules /Migration",
    "website" : "http://openerp.straconx.com",
    "description": """
    Recosting for Invoices without cost
    """,
    "depends" : [   "base",
                    "straconx_invoice",
                    "straconx_sales",
                    "straconx_logistics",
                ],
    "init_xml" : [],
    "update_xml" : [
                    'views/str_recosting.xml',
                    'views/str_menu.xml',
                    ],
    "demo_xml" : [],
    "installable": True
}
