# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
#              (<http://openerp.straconx.com>). All Rights Reserved
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
    'name': 'Cash Voucher Payment',
    'version': '1.0',
    'category': 'Ecuadorian Location/Payments and deposits',
    'description': "",
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'depends': ['straconx_payments',
                # 'straconx_sales'
                ],
    'init_xml': [],
    'update_xml': [
                  'data/straconx_journal.xml',##creacion de diarios
#                  'report/straconx_cash_voucher_report.xml',
                  'report/straconx_petty_cash_report.xml',
                  'wizard/straconx_open_petty_cash_wizard.xml',##mensaje emergente vista
                  'wizard/straconx_cash_vouchers_wizard.xml',##vista principal para ingreso de vale de caja
                  'views/straconx_account_expense_cash.xml',##configurar las cuentas para pago de vale de caja
                  'views/straconx_user_petty_cash.xml',##vista de usuarios donde se modifica el valor maximo de la caja chica por usuario ,
                  'views/straconx_petty_cash.xml',##vista de la caja chica,
                  'views/straconx_cash_vouchers.xml',##vista secundaria ,ingreso de vale de caja o modificacion
                  'views/straconx_cash_voucher_menu.xml',##items de menu para módulo
                  'security/ir.model.access.csv'
                  ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
