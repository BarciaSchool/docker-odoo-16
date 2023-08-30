# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 STRACONX S.A. (<http://openerp.straconx.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import time
from osv import fields, osv

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _columns = {
                'purchase_line_id': fields.many2one('purchase.order.line','Line Order'),
                }
account_invoice_line()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
                'purchase_order_id':fields.many2one('purchase.order', 'Purchase Order'),
                }

account_invoice()
