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
    'name': 'International Trade for Ecuadorian localisation',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """International Trade for Ecuadorian localisation""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends': ['purchase',
                'account',
                'straconx_purchase',
                'straconx_account',
                'straconx_logistics',
                'straconx_authorizations',
                'straconx_payments'
                ],
    'init_xml': [],
    'update_xml': [
                   "report/straconx_trade_report.xml",
                   "edi/straconx_trade.xml",
                   "wizards/straconx_transfer_new.xml",
                   "workflow/purchase_order_workflow.xml",
                   "data/straconx_data.xml",
				   "views/straconx_company.xml",
                   "views/straconx_tax_duty.xml",
                   "views/straconx_tradetax.xml",
                   "views/straconx_invoice_line.xml",
                   "views/straconx_products.xml",
                   "views/straconx_purchase.xml",
                   'views/straconx_landed_cost.xml',
                   'views/straconx_trade_view.xml',
                   'views/straconx_incoming_international_view.xml',
                   'views/invoice_view.xml',
                   'views/straconx_menu.xml',
                   'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
