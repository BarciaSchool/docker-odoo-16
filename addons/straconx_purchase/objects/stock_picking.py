# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - 20011 STRACONX S.A. (<http://openerp.straconx.com>).
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

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def action_cancel(self, cr, uid, ids, context=None):
        res= super(stock_picking, self).action_cancel(cr, uid, ids, context)
        for pick in self.browse(cr, uid, ids, context):
            if pick.purchase_id:
                self.pool.get('purchase.order').action_cancel(cr, uid, [pick.purchase_id.id],context)
        return res
    
stock_picking()

class stock_partial_picking(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        pick_obj = self.pool.get('stock.picking')
        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            has_product_cost = (pick.type == 'in' and pick.purchase_id)
            for m in pick.move_lines:
                if m.state in ('done','cancel') :
                    continue
                if has_product_cost and m.product_id.cost_method == 'average' and m.purchase_line_id:
                    # We use the original PO unit purchase price as the basis for the cost, expressed
                    # in the currency of the PO (i.e the PO's pricelist currency)
                    list_index = 0
#                    for item in res['product_moves_in']:
                    for item in res['move_ids']:
                        if item['move_id'] == m.id:
                            res['move_ids'][list_index]['cost'] = m.purchase_line_id.final_price
                            res['move_ids'][list_index]['currency'] = m.picking_id.purchase_id.pricelist_id.currency_id.id
                        list_index += 1
        return res
stock_partial_picking()