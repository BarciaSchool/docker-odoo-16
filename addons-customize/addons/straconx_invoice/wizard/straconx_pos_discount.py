# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 20011 STRACONX S.A. 
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

from osv import osv, fields
import decimal_precision as dp

class pos_discount(osv.osv_memory):
    _name = 'invoice.discount'
    _description = 'Add a Global Discount'
    _columns = {
        'offer': fields.float('Offer (%)', digits_compute=dp.get_precision('Account'))
    }
    _defaults = {
        'offer': 10,
    }


    def apply_discount(self, cr, uid, ids, context=None):
        order_ref = self.pool.get('account.invoice')
        order_line_ref = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)
        if isinstance(record_id, (int, long)):
            record_id = [record_id]
        for order in order_ref.browse(cr, uid, record_id, context=context):
            order_line_ref.write(cr, uid, [x.id for x in order.invoice_line], {'offer':this.offer}, context=context)
        return {}

pos_discount()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
