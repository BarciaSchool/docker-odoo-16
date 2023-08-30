# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
#
##############################################################################

{
    "name" : "Product label printing wizards",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "website" : "http://openerp.straconx.com",
    "license" : "GPL-3",
    "category" : "Generic Modules",
    "description": """
    Provides an editable grid to fill in with products and label quantities
    to print. Adds a button on pickings to automatically fill in this grid
    from their data.
    """,
    "depends" : [ 
                 "product",
                 "straconx_logistics",
                 "straconx_products",
                 "pentaho_reports",
                 ],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "reports/pentaho_labels_report.xml",
        "views/label_wizard.xml",
        "views/label_action.xml",
        "views/str_menu.xml",
    ],
    "active": False,
    "installable": True
}
