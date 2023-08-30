# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A. (Lajonner Crespín Moran)   
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
    'name': 'Cash Voucher Payment Extension',
    'version': '1.0',
    'category': 'Ecuadorian Location/Payments and deposits',
    'description': "A extension from straconx_cash_voucher",
    'author': "Lajonner Crespín Moran - lajonner.crespin@straconx.com - STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'depends': ['straconx_cash_voucher','straconx_sales'],
    'init_xml': [],
    'update_xml': [
                   "wizard/straconx_payment_sales.xml",
                  ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}