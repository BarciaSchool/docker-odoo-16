# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved	   
#
#
##############################################################################


{
    "name" : "Customer Base Extension",
    "version" : "1.0",
    "depends" : [
                "straconx_account",
                "straconx_invoice",
                "straconx_logistics",
                "straconx_bh",
                "pentaho_reports",
                "straconx_base_synchro",
                    ],
    "author" : "STRACONX S.A.",
    "category": 'Generic Modules/Base',
    "website" : "http://openerp.straconx.com/",
    "description": """Init data x Almacenes Buenhogar E.W. Cia. Ltda.""",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
            "report/reports_straconx_bh.xml",
            ],
    "active": False,
    "installable": True,
}
