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
    'name': 'Invoices Reports',
    'version': '1.0',
    'description': """Invoice Reports""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com/',
    'depends': ['straconx_invoice_ar'],
    'init_xml': [],
    'update_xml': [
        "views/invoice_shops_reports.xml",
        "report/straconx_invoice_reports.xml",
    ],
    'installable': True,
    'active': False,
}
