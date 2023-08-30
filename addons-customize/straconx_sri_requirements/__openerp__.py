# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

{
        "name" : "Ecuadorian SRI Requirements",
        "version" : "1.0",
        "author" :  "Straconx S.A.",
        "website" : "http://www.straconx.com/",
        "category" : "Ecuadorian Legislation",
        "description": """SRI Requirements for authorizations automatics""",
        "depends" : [
                     'straconx_account',
#                      'straconx_invoice',
#                      'straconx_logistics',
                     'straconx_withhold',
                     'straconx_sri',            
                     ],
        "init_xml" : [],
        "demo_xml" : [],
        "update_xml" : ['data/data.xml',
                        'views/sequence_type_view.xml',
                        'views/sri_type_transaction.xml',
                        'views/sri_create_xml_view.xml',
                        'views/straconx_account_invoice.xml',
                        'views/straconx_menu.xml',     
                        'security/ir.model.access.csv'                   
                        ],
        "installable": True
}