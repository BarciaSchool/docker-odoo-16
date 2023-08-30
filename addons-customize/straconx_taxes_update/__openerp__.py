# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 - present STRACONX S.A. (http://openerp.straconx.com) All Rights Reserved.
#                       
##############################################################################

{
    "name" : "Ecuador - New Taxes 2015",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
	"category" : "Localization/Account Charts",
    "website" : "http://openerp.straconx.com",
    "description": """
    New Taxes 2015
    """,
    "license" : "GPL-3",
    "depends" : [   
#                     "straconx_account",
                ],
    "init_xml" : [],
    "update_xml" : [
                    "data/taxes_data.xml",
                    "data/update_taxes.sql",
                   ],
    "demo_xml" : [],
    "active": True,
    "installable": False,
    "application": False,
    "auto_install": False    
}