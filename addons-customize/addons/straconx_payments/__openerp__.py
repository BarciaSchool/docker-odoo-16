# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A.   
#    (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################


{
    'name': 'Customization for Payment Management in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Payments and deposits',
    'description': """
    The module adapted to Ecuadorian law.
    This Module define cash register open by users of system.
    Define receipt collect for each salesman exist in your system.
    Define some forms of payment: cash, checks, credit card.
    Allows exchange of checks.
    Permit deposit the values collect, closed the cash register and concilied.
    Need execute query in sql/convertir_numero_texto.sql for reports in pentaho_reports
    """,
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'depends': [
                'account_payment',
                'sale', 
                'straconx_account',
                'straconx_salesman',
                'straconx_partners',
                'straconx_credit_notes',
                'straconx_debit_notes',
                'pentaho_reports',
                ],
    'init_xml': [],
    'update_xml': [
                    'data/straconx_payments_sequence.xml',
                    'workflow/book_salesman_workflow.xml',
                    'workflow/receipt_salesman_workflow.xml',
                    'workflow/book_receipt_workflow.xml',
                    'workflow/check_book_workflow.xml',
                    'wizard/straconx_open_statement.xml',
                    'wizard/deposit_cash_view.xml',
                    'wizard/refund_check_view.xml',                                       
                    'wizard/change_box_out_view.xml',   
                    'wizard/straconx_reopen_statement.xml',                
                    'report/straconx_cash_box_form.xml',
                    'views/straconx_company.xml',
                    'views/straconx_shop.xml',
                    'views/partner_view.xml',
                    'views/straconx_res_bank.xml',
                    'views/straconx_user.xml',
                    'views/straconx_statement.xml',
                    'views/straconx_payments_mode_view.xml',
                    'views/straconx_payments_method.xml',
                    'views/straconx_receipt_voucher_view.xml',
                    'views/straconx_cheques_voucher_view.xml',
                    'views/straconx_voucher.xml',
                    'views/straconx_voucher_supplier.xml',
                    'views/straconx_debit_note_view.xml',
                    'views/straconx_menu_payment.xml',
                    'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
