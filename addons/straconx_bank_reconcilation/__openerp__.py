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
        "name" : "Conciliación Bancaria",
        "version" : "1.16",
        "author" :  "Straconx S.A.",
        "website" : "http://www.straconx.com/",
        "category" : "Ecuadorian Legislation",
        "description": """ATS and REOC for Commercial Companies""",
        "depends" : ['account',
                     'straconx_account',
                     'straconx_payments',

                     ],
        "init_xml" : [ ],                       
        "demo_xml" : [ ],
        "update_xml" : [
                        'views/straconx_check_reconcilation.xml',
                        'views/straconx_debit_reconcilation.xml',
                        'views/straconx_menu.xml',                        
                         ],
        "installable": True
}
