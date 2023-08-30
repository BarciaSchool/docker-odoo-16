# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2012-2013 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Customization for Credit Notes Management in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Credit Notes based in rules SRI',
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """
    This module customize the credit Notes adapted to the rules SRI.
    * Permit sequence control in refund sale or refund purchase invoices.
    * Permit specific a motive by the sales and purchase refund
    * Can choose the Invoice which comes the refund
    * Can create the Credit Note from the customer or supplier invoice""",
    'depends': ['straconx_account',
                'straconx_partners'
                # 'straconx_sri',
                # 'straconx_invoice',
                ],
    'init_xml': [],
    'update_xml': ['report/straconx_account_form.xml',
                   'wizard/authorization_refund.xml',
                   'wizard/account_invoice_refund.xml',
                   'views/product_view.xml',
                   'views/payment_term_view.xml',
                   'views/motive_refund_view.xml',
                   'views/invoice_refund_view.xml',
                   'views/straconx_menu.xml',
                   'security/ir.model.access.csv',
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}