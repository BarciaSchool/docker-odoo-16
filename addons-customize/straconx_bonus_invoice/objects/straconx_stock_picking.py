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
from osv import osv, fields
import decimal_precision as dp
from tools.translate import _

class stock_picking(osv.osv):
    
    _name = "stock.picking"
    _inherit = "stock.picking"
    
    def get_prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
        vals_stock_picking = super(stock_picking, self).get_prepare_invoice_line(cr, uid, group, picking, move_line, invoice_id, invoice_vals, context)
        vals_stock_picking['qty'] = move_line.qty
        vals_stock_picking['bonus_qty'] = move_line.bonus_qty
        return vals_stock_picking
    
stock_picking()

class stock_move(osv.osv):
    
    _inherit = "stock.move"
    _columns = {
               'product_qty': fields.float('Total Quantity', digits_compute=dp.get_precision('Product UoM'), states={'done': [('readonly', True)]}),
               "bonus_qty":fields.float("Bonus", digits_compute=dp.get_precision('Product UoM'), help="Quantity awarded as bonus.Bonus must be greater than or equal to 0."),
               "qty":fields.float("Quantity", digits_compute=dp.get_precision('Product UoM')),
                }
    _defaults = {
               "bonus_qty":0,
               } 
    
    def onchange_quantity(self, cr, uid, ids, product_id, product_qty, product_uom, product_uos):
        return self.onchange_qty(cr, uid, ids, product_qty, 0, product_id, product_qty, product_uom, product_uos)
    
    def onchange_qty(self, cr, uid, ids, qty, bonus_qty, product_id, product_qty, product_uom, product_uos):
        repaired = False
        if(qty):
            if(qty < 0):
                qty = qty * -1
        if(bonus_qty):
            if(bonus_qty < 0):
                repaired = -1
                bonus_qty = 0
            if(bonus_qty > qty):
                repaired = -2
                bonus_qty = 0    
        total_quantity = qty + bonus_qty
        values = super(stock_move, self).onchange_quantity(cr, uid, ids, product_id,total_quantity, product_uom, product_uos)
        value = values["value"]
        value["qty"] = qty
        value["product_qty"] = total_quantity
        value["bonus_qty"] = bonus_qty
        values["value"] = value
        if(repaired):
            if(repaired == -1):
                values["warning"] = {"title":_("Validation Error!"), "message":_("BONUS must be greater than or equal to 0.PLEASE CHECK!.The amount has been adjusted.")}
                return values
            if(repaired == -2):
                values["warning"] = {"title":_("Validation Error!"), "message":_("BONUS not be greater than QUANTITY.PLEASE CHECK!.")}        
                return values
        return values
    
stock_move()
