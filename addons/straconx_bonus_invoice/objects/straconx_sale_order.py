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
from osv import osv,fields
from tools.translate import _
import decimal_precision as dp

class sale_order(osv.osv):
    _inherit="sale.order"
    
    def get_prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        vals_order_line_move=super(sale_order,self).get_prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context)
        vals_order_line_move['qty']=line.qty
        vals_order_line_move['bonus_qty']=line.bonus_qty
        return vals_order_line_move
    
sale_order()

class sale_order_line(osv.osv):
    
    def get_amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            for f in field_names:
                if f == 'price_subtotal':
                    if line.discount != 0.0:
                        res[line.id][f] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
                    else:
                        res[line.id][f] = line.price_unit * line.qty
                elif f == 'price_subtotal_incl':
                    taxes = [t for t in line.product_id.taxes_id]
                    if line.qty == 0.0:
                        res[line.id][f] = 0.0
                        continue
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, price, line.qty)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id][f] = self.pool.get('res.currency').round(cr, uid, cur, computed_taxes['total'])
        return res
    
    _inherit = "sale.order.line"
    
    _columns = {
               'product_uom_qty': fields.float('Total Quantity', digits_compute= dp.get_precision('Product UoS'), readonly=True, states={'draft': [('readonly', False)]}),
               "bonus_qty":fields.float("Bonus", digits_compute= dp.get_precision('Product UoS'), help="Quantity awarded as bonus.Bonus must be greater than or equal to 0."),
               "qty":fields.float("Quantity", digits_compute= dp.get_precision('Product UoS')),
                }
    _defaults = {
               "bonus_qty":0,
               "qty":1,
               }
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,uom=False, qty_uos=0, uos=False, name='', partner_id=False,
                          lang=False, update_tax=True, date_order=False,
                          packaging=False,fiscal_position=False, flag=False,
                          shop_id=None, location_id=None, context=None):
        bonus_qty = 0
        if(context is None):
            context = {}
        if(qty):
            if(qty < 0):
                qty = qty * -1
        values =super(sale_order_line,self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, shop_id, location_id, context)
        value = values["value"]
        if(not product):
            bonus_qty = 0
        value["qty"] = qty
        value["product_uos_qty"] = qty + bonus_qty
        value["product_uom_qty"] = qty + bonus_qty
        value["bonus_qty"] = bonus_qty
        values["value"] = value
        return values
    
    def onchange_qty(self, cr, uid, ids,qty,bonus_qty,pricelist,
            product, product_uom_qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, shop_id=None,location_id=None, context=None):
        
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
        values = super(sale_order_line,self).product_id_change(
                      cr,uid,ids,pricelist,product,qty,
                      uom,qty_uos,uos,name,partner_id,
                      lang,update_tax,date_order,packaging,
                      fiscal_position,flag,shop_id,location_id,context)
        value = values["value"]
        value["qty"] = qty
        value["product_uos_qty"] = total_quantity
        value["product_uom_qty"] = total_quantity
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
    
sale_order_line()