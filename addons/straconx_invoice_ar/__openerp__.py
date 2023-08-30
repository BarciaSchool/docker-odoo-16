# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#
#    This program is private software.
#
#
##############################################################################

{
    'name': 'Customization for Invoice Management in Argentina',
    'version': '1.0',
    'category': 'Argentina Location/Invoices based in rules AFIP',
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """
    This module customize the invoices adapted to the rules AFIP.
    * Permit sequence control in sale or purchase invoices.
    * Maintains control of users for invoices canceled""",
    'depends': ['account_cancel',
                'straconx_afip',
                'straconx_account_ar',
                'straconx_authorizations',
                'straconx_partners',
                'straconx_products',
                'straconx_salesman',
                'straconx_purchase',
                'straconx_listprices',
                ],
    'init_xml': [],
    'update_xml': ['report/straconx_invoice_report.xml',
                   'data/journal_data.xml',
                   'data/sequence_data.xml',
                   'data/straconx_invoice_email_templates.xml',
                   'report/straconx_account_form.xml',
                   'wizard/straconx_pos_discount.xml',
                   'views/invoice_view.xml',
                   'views/invoice_supplier_view.xml',
                   'views/straconx_liquidation.xml',
                   'views/straconx_other_documents.xml',
                   'views/straconx_invoice_line.xml',
                   'views/straconx_user_view.xml',
                   'views/invoice_shops_reports.xml',
                   "wizard/force_stock_picking.xml",
                   "wizard/force_stock_picking.xml",
                   "wizard/installer.xml",
                   'views/straconx_menu.xml',
                   "security/ir.model.access.csv"
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
