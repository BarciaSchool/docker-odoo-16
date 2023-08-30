# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A (Jorge Valdiviezo) 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

{
        "name" : "Ecuadorian Commission salesman",
        "version" : "1.0",
        "author" :  "STRACONX S.A.",
        "website" : "http://www.straconx.com/",
        "category" : "Ecuadorian Legislation",
        "description": """Commission for salesman""",
        "depends" : [
                     'sale_forecast',
                     'straconx_account',
                     'straconx_salesman',
                     'straconx_payments',
                     ],
        "init_xml" : [ 
                      ],
        "demo_xml" : [ ],
        "update_xml" : ['data/diarios_contables.xml',
                        'wizard/commission_for_salesman.xml',
                        'views/table_commission_view.xml',
#                        'views/straconx_salesman.xml',
                        'views/straconx_segmento.xml',
                        'views/sale_forecast_view.xml',
                        'views/sale_forecast_line_view.xml',
                        'views/straconx_company.xml',
                         ],
        "installable": True
}

