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
    'name': 'Account Reports',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """Account Reports.""",
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'depends': ['straconx_account',
                ],
    'init_xml': [],
    'update_xml': ['data/data.sql',
                   'report/straconx_general_ledger.xml',
                   'views/straconx_ledger_statement.xml',
                   'views/straconx_invoice.xml',
                   'views/straconx_account_financial_report_view.xml',
                   'views/straconx_menu.xml',
                   'security/ir.model.access.csv'],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
