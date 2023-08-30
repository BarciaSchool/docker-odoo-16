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
    "depends": ["base","sale"],
    "demo_xml": [],
    "update_xml": [
        "views/base_synchro_view.xml",
        "wizard/base_synchro_view.xml",
        "security/ir.model.access.csv",
        "data/base_reports_mail.xml",
        "views/straconx_menu.xml",
        ],
    "installable": True,
    "auto_install": False,
    "images": ['images/1_servers_synchro.jpeg','images/2_synchronize.jpeg','images/3_objects_synchro.jpeg',],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
