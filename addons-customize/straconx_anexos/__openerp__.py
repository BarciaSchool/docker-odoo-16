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
        "name" : "Ecuadorian Anexos",
        "version" : "1.16",
        "author" :  "Straconx S.A.",
        "website" : "http://www.straconx.com/",
        "category" : "Ecuadorian Legislation",
        "description": """ATS and REOC for Commercial Companies""",
        "depends" : [
                     'straconx_account',
                     'straconx_withhold',
                     'straconx_invoice',
                     'straconx_payments',
                     'straconx_sri',

                     ],
        "init_xml" : ['data/countries.xml'],                       
        "demo_xml" : [ ],
        "update_xml" : [
						'views/company_view.xml',
						'wizard/form_103_view.xml',
						'wizard/ats_view.xml',
						'views/straconx_menu.xml',
                        
                         ],
        "installable": True
}