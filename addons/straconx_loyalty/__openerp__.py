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
    "name" : "Loyalty Program",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "category" : "Ecuadorian Location/ Loyalty Program",
    "website" : "http://openerp.straconx.com",
    "description": """
    Loyalty program for POS sales.
    """,
    "license" : "GPL-3",
    "depends" : ["straconx_sales",
                ],
    "init_xml" : [],
    "update_xml" : [
                    'reports/straconx_loyalty_reports.xml',
                    'view/straconx_loyalty_view.xml',
                    'view/straconx_customer_view.xml',
                    'view/straconx_payments_view.xml',
                    'view/straconx_menu.xml',
                    'data/data.xml',
                    'security/ir.model.access.csv',
                    ],
    "demo_xml" : [],
    "installable": True
}