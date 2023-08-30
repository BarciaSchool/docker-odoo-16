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
#import decimal_precision as dp
import netsvc

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def delivery_picking_available(self,cr, uid, picking_id, context):
        if(context is None):
            context={}
        wf_service = netsvc.LocalService("workflow")
        self.draft_force_assign(cr, uid, [picking_id], context)##
        if(context.get("force_availability",False)):##forzar disponibilidad dejando este o no el stock en negativo
            self.force_assign(cr, uid,[picking_id],context)
        else:
            self.action_assign(cr, uid, [picking_id], context)##
        mv_pend=self.pool.get('stock.move').search(cr, uid, [('picking_id','=',picking_id),('state','=','confirmed')])
        if not mv_pend:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_done', cr)
        else:
            partial_data={}
            for m in self.pool.get('stock.move').browse(cr, uid, mv_pend):
                qty=self.pool.get('stock.location')._product_get(cr, uid, m.location_id.id, [m.product_id.id], {'uom': m.product_uom.id})[m.product_id.id]
                if qty > 0:
                    partial_data['move%s' % (m.id)] = {
                                'product_id': m.product_id.id,
                                'product_qty': qty,
                                'product_uom': m.product_uom.id,
                                'prodlot_id': m.prodlot_id.id,
                            }
            for move in self.browse(cr, uid, picking_id, context).move_lines:
                if move.id in mv_pend:
                    continue
                partial_data['move%s' % (move.id)] = {
                            'product_id': move.product_id.id,
                            'product_qty': move.product_qty,
                            'product_uom': move.product_uom.id,
                            'prodlot_id': move.prodlot_id.id,
                        }
            if partial_data:
                self.do_partial(cr, uid, [picking_id], partial_data, context=context)
        return True
    
    def action_drafted(self, cr, uid, ids, context=None):
        """ Changes picking state to draft.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        move_obj = self.pool.get('stock.move')
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.delivery_status == 'sent':
                raise osv.except_osv(_('Invalid Action!'), _('You can not change this picking to draft because exist delivery note in state sent.'))
            flag=False
            if pick.invoice_ids:
                for invoice in pick.invoice_ids:
                    if invoice.pos:
                        flag=True
                    if invoice.state in ('open','paid'):
                        raise osv.except_osv(_('Invalid Action!'), _('You can not change this picking to draft because exist invoices related in state open or paid.'))
            if pick.backorder_id and flag:
                self.pool.get('stock.picking').action_drafted(cr, uid, [pick.backorder_id.id], context)
                self.pool.get('stock.picking').unlink(cr, uid, [pick.backorder_id.id], context)
            if pick.pick_pendding_id and pick.consigment:
                pending = self.pool.get('stock.picking').browse(cr,uid,pick.pick_pendding_id.id)
                if pending:
                    self.pool.get('stock.picking').action_drafted(cr, uid, [pick.pick_pendding_id.id], context)
                    self.pool.get('stock.picking').unlink(cr, uid, [pick.pick_pendding_id.id], context)
                else:
                    self.pool.get('stock.picking').write(cr,uid,pick.id,{'pick_pendding_id':False})                    
            if pick.invoice_state == 'invoiced':
                pick.write({'invoice_state':'2binvoiced'})
            ids2 = [move.id for move in pick.move_lines]
            move_obj.action_drafted(cr, uid, ids2, context)
            wf_service.trg_delete(uid, 'stock.picking', pick.id, cr)
            wf_service.trg_create(uid, 'stock.picking', pick.id, cr)
        self.write(cr, uid, ids, {'state': 'draft',
                                  })
        self.log_picking(cr, uid, ids, context=context)
        return super(stock_picking, self).action_drafted(cr, uid, ids, context)

    def action_cancel(self, cr, uid, ids, context=None):
        res= super(stock_picking, self).action_cancel(cr, uid, ids, context)
        for pick in self.browse(cr, uid, ids, context):
            if pick.sale_id:
                self.pool.get('sale.order').action_cancel(cr, uid, [pick.sale_id.id],context)
        return res
    
    def action_backorder(self, cr, uid, ids, context=None):
        sale_order_line_obj = self.pool.get('sale.order.line')
        sale_order_obj = self.pool.get('sale.order')
        for pick in self.browse(cr, uid, ids, context=context):
            sale_new=None
            for move in pick.move_lines:
                if move.is_backorder:
                    if not sale_new:
                        if not pick.sale_id:
                            raise osv.except_osv(_('Error!'), _("you can not create the backorder because this picking have not sales order associated"))
                        sale_new = sale_order_obj.copy(cr, uid, pick.sale_id.id,
                            {
                            'order_line' : [],
                            'state':'draft',
                            'origin':pick.sale_id.name,
                            'is_backorder':True,
                            'flag':True,
                            'flag1':False,
                            'flag2':False,
                            })
                    if not move.sale_line_id:
                        raise osv.except_osv(_('Error!'), _("you can not create the backorder because the line with the product %s that have not sales order line associated"),(move.product_id.name))
                    defaults = {
                                'order_id': sale_new,
                                'state': 'draft',
                                'autorized':True,
                                }
                    sale_order_line_obj.copy(cr, uid, move.sale_line_id.id, defaults)
                    self.pool.get('stock.move').write(cr, uid, [move.id], {'state':'draft'} ,context)
                    self.pool.get('stock.move').lost_unlink(cr, uid, [move.id,], context)
            if sale_new:
                sale_order_obj.button_dummy(cr, uid, [sale_new], context)
        return True
    
stock_picking()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def action_done(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done','cancel']:
                continue
            if move.picking_id.type == 'in':
                if move.product_id.list_price<=0:
                    if move.product_id.categ_id.percentage_sale <0 and move.product_id.sale_ok:
                        raise osv.except_osv(_('Error!'), _("The product doesn't have a percentage sale in the category for calculate the price sale"))
                    else:
                        price=move.price_unit * (move.product_id.categ_id.percentage_sale/100)
                        self.pool.get('product.product').write(cr, uid, [move.product_id.id], {'list_price':price})
            else:
                company_id = move.company_id.id
        return super(stock_move, self).action_done(cr, uid, ids, context)
    
stock_move()