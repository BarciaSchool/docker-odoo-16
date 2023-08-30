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

from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta
from osv import fields, osv
from tools.translate import _
#import decimal_precision as dp
import netsvc

class purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def action_picking_create(self,cr, uid, ids, *args):
        picking_id = False
        for order in self.browse(cr, uid, ids):
            loc_id = order.partner_id.property_stock_supplier.id
            istate = 'none'
            if order.invoice_method=='picking':
                istate = '2binvoiced'
            pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.in')
            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                'name': pick_name,
                'origin': order.name+((order.origin and (':'+order.origin)) or ''),
                'type': 'in',
                'address_id': order.dest_address_id.id or order.partner_address_id.id,
                'invoice_state': istate,
                'purchase_id': order.id,
                'company_id': order.company_id.id,
                'salesman_id': order.solicited.id,
                'shop_id':order.shop_id.id,
                'move_lines' : [],
            })
            todo_moves = []
            if order.location_id:
                location_id = order.location_id.id
            else:
                location_id = order.shop_id.warehouse_id.lot_stock_id.id
            for order_line in order.order_line:
                if not order_line.product_id:
                    continue
                if order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
#                    ubication_ids = None
#                    ubication=None
#                    if self.pool.get('stock.location').browse(cr, uid,location_id, context=None).location_ids:
#                        for perch in self.pool.get('stock.location').browse(cr, uid,location_id, context=None).location_ids:
#                            ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('ubication_id','=',perch.id),('product_id','=',order_line.product_id.id)])
#                            if ubication_ids:
#                                ubication = perch.id
#                                break
                    ubication=None
                    ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',order_line.product_id.id),('location_ubication_id','=',location_id)])
                    if ubication_ids:
                        ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context={}).ubication_id.id           
                    dest = order.location_id.id
                    move = self.pool.get('stock.move').create(cr, uid, {
                        'name': order.name + ': ' +(order_line.name or ''),
                        'product_id': order_line.product_id.id,
                        'categ_id':order_line.categ_id.id,
                        'product_qty': order_line.product_qty,
                        'product_uos_qty': order_line.product_qty,
                        'product_uom': order_line.product_uom.id,
                        'product_uos': order_line.product_uom.id,
                        'date': order_line.date_planned,
                        'date_expected': order_line.date_planned,
                        'location_id': loc_id,
                        'location_dest_id': dest,
                        'picking_id': picking_id,
                        'move_dest_id': order_line.move_dest_id.id,
                        'state': 'draft',
                        'purchase_line_id': order_line.id,
                        'company_id': order.company_id.id,
                        'price_unit': order_line.final_price,
                        'categ_id': order_line.product_id.categ_id.id,
                        'ubication_id':ubication,
                    })
                    if order_line.move_dest_id:
                        self.pool.get('stock.move').write(cr, uid, [order_line.move_dest_id.id], {'location_id':order.location_id.id})
                    todo_moves.append(move)
            self.pool.get('stock.move').action_confirm(cr, uid, todo_moves)
            self.pool.get('stock.move').force_assign(cr, uid, todo_moves)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            #wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_done', cr)
        return picking_id


purchase_order()
