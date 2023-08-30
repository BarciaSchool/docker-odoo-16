# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A. 
#              (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################


{
    'name': 'Customization for Payment Management in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Debit Notes SRI and internal',
    'description': """
    The module adapted to Ecuadorian law.
    Create a new object called account.debit.note.
    defines debit notes for customers and suppliers.
    defines advances for customers and suppliers.
    The debit notes SRI are changing the object invoice.""",
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'depends': [
                'straconx_account',
                'straconx_partners',
                # 'straconx_invoice',
                'straconx_credit_notes',
                ],
    'init_xml': [],
    'update_xml': [
                   'report/straconx_account_form.xml',
                   'data/straconx_journal_data.xml',
                   'views/straconx_company.xml',
                   'views/straconx_advances.xml',
                   'views/straconx_debit_note.xml',
                   'views/straconx_sri_debit_note.xml',
                   'views/straconx_menu.xml',
                   'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
