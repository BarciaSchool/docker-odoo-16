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
from tools.translate import _
import decimal_precision as dp
import time

class res_partner(osv.osv):
    
    _inherit = "res.partner"
    _columns = {
              "last_bonus_qty":fields.float("Bonus quantity", digits=(12, 6), help="Last quantity awarded as bonus")
              }
    _defaults = {
               "last_bonus_qty":0
               }
    def onchange_last_bonus_qty(self, cr, uid, ids, last_bonus_qty, context=None):
        values = {}
        if(last_bonus_qty):
            if(last_bonus_qty < 0):
                last_bonus_qty = last_bonus_qty * -1
                values["warning"] = {"title":_("Validation Error!"), "message":_("BONUS must be greater than or equal to 0.PLEASE CHECK!.The amount has been adjusted.")}
        values["value"] = {"last_bonus_qty":last_bonus_qty}
        return values
        
res_partner()

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    
    def write(self,cr,uid,ids,vals,context=None):
        if(vals.get("state",False)=="open"):
            for browse_account_invoice in self.browse(cr,uid,ids,context):
                line_ids=self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',browse_account_invoice.id),('bonus_qty','>',browse_account_invoice.partner_id.last_bonus_qty)],order="bonus_qty")
                for line in self.pool.get('account.invoice.line').browse(cr, uid, line_ids):
                    browse_account_invoice.partner_id.write({"last_bonus_qty":line.bonus_qty})
                    break
        return super(account_invoice,self).write(cr,uid,ids,vals,context)
   
    def clean_values_invoice_cancel(self, cr, uid, ids, context):
        cr.execute("""UPDATE account_invoice_tax set base = 0.0, amount = 0.0, base_amount = 0.0,
                        tax_amount = 0.0 WHERE invoice_id = %s""",(tuple(ids)))
        cr.execute("""UPDATE account_invoice_line set quantity = 0.0,qty = 0.00,bonus_qty = 0.0 , cost_price = 0.0, discount = 0.0, price_unit = 0.0,
                            price_subtotal = 0.0 WHERE invoice_id = %s""",(tuple(ids)))
        cr.execute("""UPDATE account_invoice set amount_tax_withhold_vat = 0.0, amount_tax_withhold = 0.0, amount_tax_other = 0.0, 
                        amount_untaxed = 0.0, amount_total = 0.0, amount_total_vat = 0.0, residual=0.0, amount_base_vat_12 = 0.0
                       WHERE id = %s""",(tuple(ids)))
        return True
    
    def get_amount_total_invoice(self,cr,uid,ids,name,args,context=None):
        res = {}    
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'pretotal':0.0,
                'amount_untaxed':0.0,
                'amount_total_vat': 0.0,
                'amount_total': 0.0,
                'amount_total_discount': 0.00,
                'amount_total_offer': 0.00
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_total_vat'] += line.iva_value
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
                res[invoice.id]['amount_total_discount']+= line.discount_value_total 
                res[invoice.id]['amount_total_offer'] += line.offer_value_total
                res[invoice.id]['pretotal'] += line.price_product*line.qty
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_untaxed'] + res[invoice.id]['amount_total_vat']
        return res
    
    def get_refund_cleanup_lines(self, cr, uid, lines):
        for line in lines:
            invoice=self.browse(cr,uid,line['invoice_id'][0],context=None)
            old_line_id=line['id']
            del line['id']
            del line['invoice_id']
            for field in ('company_id', 'partner_id', 'account_id', 'product_id',
                          'uos_id', 'account_analytic_id', 'tax_code_id', 'base_code_id'):
                line[field] = line.get(field, False) and line[field][0]
            qty_rest=line['qty']-line['quantity_refund']
            if qty_rest==0:
                continue
            line['qty'] = qty_rest
            line['quantity']=qty_rest+line['bonus_qty']
            line['quantity_refund'] = 0
            line['old_line_id']=old_line_id
            if invoice.type=="out_invoice":
                type='out_refund'
            elif invoice.type=="in_invoice":
                type='in_refund'
            result=self.pool.get('account.invoice.line').product_id_change(cr, uid, [],
                            line['product_id'],line['uos_id'], type=type, partner_id=invoice.partner_id.id, fposition_id=invoice.fiscal_position.id)['value']
            if result.get('account_id',False):
                line['account_id'] = result['account_id']
            if 'invoice_line_tax_id' in line:
                line['invoice_line_tax_id'] = [(6,0, line.get('invoice_line_tax_id', [])) ]
        return map(lambda x: (0,0,x), lines)
        
account_invoice()

class account_invoice_line(osv.osv):

    _inherit = "account.invoice.line"
    
    _columns = {
               "bonus_qty":fields.float("Bonus", digits=(12, 2), help="Quantity awarded as bonus.Bonus must be greater than or equal to 0."),
               "qty":fields.float("Quantity", digits=(12, 2)),
                }
    _defaults = {
               "bonus_qty":0,
               "qty":1,
               }
    
    def get_amount_taxes(self, cr, uid, ids, field_names, arg, context=None):
        account_tax_obj = self.pool.get('account.tax')
        account_tax_code_obj = self.pool.get('account.tax.code')
        res={}
        for line in self.browse(cr, uid, ids, context=None):
            res[line.id]={'iva_value':0.0,}
            try:
                taxes = account_tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, line.price_unit, line.qty, line.product_id or [], partner=line.invoice_id.partner_id or False)
                for t in taxes.get('taxes'):
                    tax_code=account_tax_code_obj.browse(cr, uid, t.get('tax_code_id',None))
                    if line.invoice_id.type in ('out_invoice','out_refund') and tax_code.code == 't601':
                        res[line.id]['iva_value']+= t['amount']
                    elif line.invoice_id.type in ('in_invoice','in_refund') and tax_code.code in ('t721','t722','t723','t724','t725'):
                        res[line.id]['iva_value']+= t['amount']
            except:
                continue
        return res


    def get_amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        user=self.pool.get('res.users').browse(cr, uid, uid, context)
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id:
                product = line.product_id
                cost_price = product.standard_price
            else:
                product = []
                cost_price = line.price_unit
            if cost_price > 0 and line.price_unit >0:
                margin = ((line.price_unit - cost_price)/line.price_unit)*100
            else:
                margin = 0.00
            taxes = account_tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, line.price_unit, line.qty, product, partner=line.invoice_id.partner_id or False)
            cur = line.invoice_id.currency_id or user.company_id.currency_id or None
            res[line.id]['price_subtotal'] = cur and cur_obj.round(cr, uid, cur, taxes['total']) or taxes['total'] 
            res[line.id]['cost_price'] = cost_price
            res[line.id]['cost_subtotal'] = cost_price * line.quantity
            res[line.id]['margin'] = margin
        return res
    
#    def get_amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
#        res = {}
#        tax_obj = self.pool.get('account.tax')
#        cur_obj = self.pool.get('res.currency')
#        for line in self.browse(cr, uid, ids):
#            price = line.price_unit
#            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.qty, product=line.product_id, address_id=line.invoice_id.address_invoice_id, partner=line.invoice_id.partner_id)
#            res[line.id] = taxes['total']
#            if line.invoice_id:
#                cur = line.invoice_id.currency_id
#                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
#        return res
    
    def get_calculate_discount(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = {
                          'offer_value_total':round((line.price_product * (1 - line.discount / 100)) * line.offer / 100 * line.qty, 2),
                          'discount_value_total':round((line.price_product * line.discount / 100 * line.qty) or 0.00, 2)
                          }
        return res   
    
    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, currency_id=False, context=None, company_id=None, discount=0, offer=0, shop_id=False):
        bonus_qty = 0
        if(context is None):
            context = {}
        if(qty):
            if(qty < 0):
                qty = qty * -1
        values = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id, context, company_id, discount, offer, shop_id)
        value = values["value"]
        if(type == "out_invoice"):
            if(not product):
                bonus_qty = 0
            if(not name and product):
                browse_product = self.pool.get("product.product").browse(cr, uid, product, context)
                name_product = browse_product and browse_product.name or ''
                if(name != name_product and partner_id):
                    browse_partner = self.pool.get("res.partner").browse(cr, uid, partner_id, context)
                    bonus_qty = browse_partner and browse_partner.last_bonus_qty or 0        
        if(bonus_qty > qty):
            values["warning"] = {"title":_("Validation Error!"), "message":_("BONUS not be greater than QUANTITY.PLEASE CHECK!.")}        
        value["qty"] = qty
        value["quantity"] = qty + bonus_qty
        value["bonus_qty"] = bonus_qty
        values["value"] = value
        return values
    
    def validate_qty(self, cr, uid, ids, qty, bonus_qty, quantity,type,context=None,other_args={}):
        validate={"value":{
                   "bonus_qty":bonus_qty,
                   "qty":qty,
                   "quantity":quantity}
                  }
        has_line_old=(type=='out_refund') and other_args.get('old_line_id',False)
        browse_invoice_line_old=False
        ##devolucion
        if(has_line_old):
            browse_invoice_line_old=self.browse(cr, uid,other_args['old_line_id'],context)
            has_line_old=browse_invoice_line_old and True or False
        
        if(qty):
            ##cantidad es negativa
            if(qty < 0):
                qty=qty * -1
                validate['value']['qty']=qty
                        
            if(has_line_old):##devolucion y tiene linea atada
                if(qty>browse_invoice_line_old.qty):##cantidad devuleta es mayor a la vendida
                    validate['value']['qty']=browse_invoice_line_old.qty
                    validate['warning']={"title":_("Validation Error!"), "message":_("BONUS must be greater than or equal to 0.PLEASE CHECK!.The amount has been adjusted.")}        
                    return validate
            
                if(other_args['qty_flag']):
                    relative=qty and (qty/browse_invoice_line_old.qty) or 1
                    bonus_qty=browse_invoice_line_old.bonus_qty*relative
                    validate['value']['bonus_qty']=round(bonus_qty,2)
                    return validate
                
        if(bonus_qty):
            ##bonificacion deberia ser mayor a 0
            if(bonus_qty < 0):
                validate['value']['bonus_qty']=0
                validate['warning']={"title":_("Validation Error!"), "message":_("BONUS must be greater than or equal to 0.PLEASE CHECK!.The amount has been adjusted.")}
                return validate
            
            if(bonus_qty > qty):##cantidad del bono es mayor a la cantidad
                validate['value']['bonus_qty']=0
                validate["warning"] = {"title":_("Validation Error!"), "message":_("BONUS not be greater than QUANTITY.PLEASE CHECK!.")}
                return validate     
        
            if(has_line_old):##devolucion y tiene liena atada
                if(bonus_qty>browse_invoice_line_old.bonus_qty):
                    validate['value']['bonus_qty']=browse_invoice_line_old.bonus_qty           
                    validate["warning"] = {"title":_("Validation Error!"), "message":_("The BONUS RETURNED is greater than the BONUS BILLED. The amount was %s.PLEASE CHECK!.The amount has been adjusted.".replace("%s",str(bonus_qty)))}
                    return validate
                
        return validate
    
    def onchange_qty(self, cr, uid, ids, qty, bonus_qty, quantity, product, uom, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, currency_id=False, context=None, company_id=None, discount=0, offer=0, shop_id=False,other_args={}):
        if(other_args is None):
            other_args={}
        other_args['qty_flag']=True
        value_qtys=self.validate_qty(cr, uid, ids, qty, bonus_qty, quantity, type, context, other_args)
        qty= value_qtys['value']['qty']
        bonus_qty= value_qtys['value']['bonus_qty']
        values = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id, context, company_id, discount, offer, shop_id)
        total_quantity = qty + bonus_qty
        value = values["value"]
        value["qty"] = qty
        value["quantity"] = total_quantity
        value["bonus_qty"] = bonus_qty
        values["value"] = value
        if(value_qtys.get("warning",False)):
            values["warning"]=value_qtys["warning"]
        return values
    
    def onchange_bonus_qty(self, cr, uid, ids, qty, bonus_qty, quantity, product, uom, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, currency_id=False, context=None, company_id=None, discount=0, offer=0, shop_id=False,other_args={}):
        if(other_args is None):
            other_args={}
        other_args['qty_flag']=False
        value_qtys=self.validate_qty(cr, uid, ids, qty, bonus_qty, quantity, type, context, other_args)
        qty= value_qtys['value']['qty']
        bonus_qty= value_qtys['value']['bonus_qty']
        values = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id, context, company_id, discount, offer, shop_id)
        total_quantity = qty + bonus_qty
        value = values["value"]
        value["qty"] = qty
        value["quantity"] = total_quantity
        value["bonus_qty"] = bonus_qty
        values["value"] = value
        if(value_qtys.get("warning",False)):
            values["warning"]=value_qtys["warning"]
        return values
    
account_invoice_line()

class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        company_currency = inv.company_id.currency_id.id 
                
        for line in inv.invoice_line:
            line_tax = line.price_unit
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, line_tax , line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id)['taxes']:
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = tax['price_unit'] * line['qty']

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = t['base']
            t['amount'] = t['amount']
            t['base_amount'] = t['base_amount']
            t['tax_amount'] = t['tax_amount']

        return tax_grouped

    _columns = {
        'name': fields.char('Tax Description', size=256, required=True),
            }

account_invoice_tax()
