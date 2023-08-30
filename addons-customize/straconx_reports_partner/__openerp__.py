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
    'name': 'Partner List Report',
    'version': '0.9',
    'category': 'Reporting',
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends': ["straconx_partners",
                "straconx_payments",
                "straconx_invoice"],
    'description': """Customization for Partner List Report in Ecuador.""",
    "init_xml": [],
    'update_xml': [
        'report/report_statement.xml',
        ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}