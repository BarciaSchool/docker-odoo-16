# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

{
        "name" : "Manufacturer",
        "version" : "1.16",
        "author" :  "Straconx S.A.",
        "website" : "http://www.straconx.com/",
        "category" : "Manufacturing",
        "description": """Manufacturing proccess x STRACONX Customers""",
        "depends" : [
                     'mrp',
                     'straconx_account',
                     'straconx_logistics',
                     'straconx_sri',
                     ],
        "init_xml" : [ 
                      ],
        "demo_xml" : [ ],
        "update_xml" : [
                        'wizard/straconx_convertion_product.xml',                        
                        'views/straconx_logistics_view.xml',
                        'report/straconx_mrp_report.xml',
						'views/straconx_mrp_view.xml',
                        'views/straconx_menu.xml',                        
                         ],
        "installable": True
}
