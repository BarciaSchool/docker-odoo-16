# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
##############################################################################


{
    'name': 'Customization for withholdings Management in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Wittholdings based in rules SRI',
    'author': " STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """
    This module customize the wittholding adapted to the rules SRI.
    * Permit sequence control in sale or purchase wittholding.
    * Permit generate a witthold for some invoices in  the case of partners who are contributors special""",
    'depends': ['straconx_account',
                'straconx_sri',
                'straconx_invoice',
                'straconx_debit_notes',
                'straconx_payments'],
    'init_xml': [],
    'update_xml': ['report/straconx_withhold_report.xml',
                   'workflow/withhold_workflow.xml',
                   'wizard/withhold_wizard_view.xml',
                   'views/withhold_view.xml',
                   'views/withhold_lines_view.xml',
                   'views/invoice_view.xml',
                   'views/voucher_view.xml',
                   'views/straconx_menu.xml',
                   "security/ir.model.access.csv",
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
