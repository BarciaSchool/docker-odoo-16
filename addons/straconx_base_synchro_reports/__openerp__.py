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
    "name": "Multi-DB Synchronization",
    "version": "0.1",
    "author": "OpenERP SA",
    "category": "Tools",
    "description": """
Synchronization with all objects.
=================================

Configure servers and trigger synchronization with its database objects.
""",
    "depends": ["base",
                "straconx_authorizations",
                "straconx_base_synchro",
                "straconx_logistics",
                "straconx_sales", 
                "straconx_trade"],
    "demo_xml": [],
    "update_xml": [
        "report/straconx_base_synchro_report.xml",
        "wizard/straconx_product_ubication.xml",
        "wizard/straconx_migrate_obj.xml",
        "views/straconx_shop.xml",
        "views/straconx_salesman.xml",        
        "views/stock_picking.xml",
        "views/straconx_discount_shop.xml",
        "views/straconx_menu.xml",        
        "security/ir.model.access.csv",
        ],
    "installable": True,
    "auto_install": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
