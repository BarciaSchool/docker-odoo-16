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
    'name': 'Credit Card Liquidation in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location',
    'author': " STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """
    This module customize the liquidation proccess for credit card in Ecuador.
                    """,
    'depends': [
                    'straconx_payments',
                    'straconx_withhold',
                ],
    'init_xml': [],
    'update_xml': [
                   'wizard/deposit_check.xml',                   
                   'report/straconx_credit_card_report.xml',
                   'views/straconx_deposit_credit_card.xml',
                   'views/company_view.xml',
                   'views/straconx_deposit_register.xml',
                   'views/invoice_credit_card_view.xml',
                   'views/straconx_menu.xml',                                      
#                   "security/ir.model.access.csv",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

