# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################


from osv import fields, osv
from tools.translate import _
import time
import datetime as dt 
#from datetime import datetime, date, timedelta
import decimal_precision as dp
import netsvc
import binascii
import os
import uuid

class account_payment_method(osv.osv):
    _inherit="account.payments"

    def on_change_mode_payment(self, cr, uid, ids, mode=False, partner=False, amount=0.00, type='receipt', company_id=False, date=None, shop_id=False, amount_payment_mode=0.00,context=None):
        result = super(account_payment_method,self).on_change_mode_payment(cr,uid,ids, mode, partner, amount, type, company_id, date, shop_id, amount_payment_mode,context)
        if mode:
            mode_pay=self.pool.get('payment.mode').browse(cr, uid, mode, context)
            result['bonus']=mode_pay.bonus
        return result

account_payment_method()

class payment_mode(osv.osv):
    
    _inherit="payment.mode"
    _columns = {'bonus':fields.boolean('Bonos', required=False)}
    _defaults = {
        'bonus': lambda *a: False
                } 
    
payment_mode()


class account_invoice(osv.osv):
    
    _inherit = 'account.invoice'
    _columns = {'bonus':fields.boolean('Bonos', required=False)}
    _defaults = {
        'bonus': lambda *a: False
                }
    
    def action_cancel_draft(self, cr, uid, ids, *args):
        sales_loyalty_partner_obj = self.pool.get('sales.loyalty.partner.line')
        for invoice in self.browse(cr, uid, ids):
            line_ids = sales_loyalty_partner_obj.search(cr,uid,[('invoice_id','=',invoice.id)])
            for line_id in line_ids:
                sales_loyalty_partner_obj.write(cr,uid,line_id,{'state':'cancel','bonus':0.00,'pending':0.00,'active':False})
        return super(account_invoice, self).action_cancel_draft(cr, uid, ids)    
    
    
    def action_cancel(self, cr, uid, ids, *args):
        sales_loyalty_partner_obj = self.pool.get('sales.loyalty.partner.line')
        for invoice in self.browse(cr, uid, ids):
            line_ids = sales_loyalty_partner_obj.search(cr,uid,[('invoice_id','=',invoice.id)])
            for line_id in line_ids:
                sales_loyalty_partner_obj.write(cr,uid,line_id,{'state':'cancel','bonus':0.00,'pending':0.00,'active':False})
        return super(account_invoice, self).action_cancel(cr, uid, ids)    
    
#     def apply_bonus(self, cr,uid, ids, context=None):
#         result = {}
#         bonus_ids = False
#         bono = False
#         valor = 0.00
#         campaing_obj = self.pool.get('sales.loyalty')
#         partner_line_obj = self.pool.get('sales.loyalty.partner.line')
#         order_line_ref = self.pool.get('account.invoice.line')
#         today = time.strftime("%Y-%m-%d")
#         inv_id = self.browse(cr,uid,ids[0]) 
#         code_ids = partner_line_obj.search(cr,uid,[('partner_id','=',inv_id.partner_id.id)])
#         if code_ids:
#             bonus_code = partner_line_obj.browse(cr,uid,code_ids[0]).id
#             result['bonus_id'] = bonus_code
#         if not inv_id.amount_untaxed:
#             amount = 0.00
#         else:
#             amount = inv_id.amount_untaxed
#         campaing_ids = campaing_obj.search(cr,uid,[('active','=',True)])
#         if campaing_ids:
#             campaing_id = campaing_obj.browse(cr,uid,campaing_ids[-1])  
#             if campaing_id.acumuled:
#                 bonus_ids = partner_line_obj.search(cr, uid, [('campaing_id','=',campaing_id.id),('partner_id','=',inv_id.partner_id.id),('state','=','pending')])
#             else:
#                 bonus_ids = partner_line_obj.search(cr, uid, [('campaing_id','=',campaing_id.id),('partner_id','=',inv_id.partner_id.id),('state','=','pending'),('date_start','<=','2016-01-20'),('date_expired','>=','2016-01-20')])
#         if bonus_ids:
#             for line in inv_id.invoice_line:
#                 amount1 = round(line.price_subtotal_read,2)
#                 amount = amount1*campaing_id.maximun_pay/100.00 
#                 valor = 0.00
#                 for l in bonus_ids:
#                     bonus = partner_line_obj.browse(cr,uid,l).pending
#                     if amount >0:
#                         if amount > round(bonus,2):
#                             amount1= amount1-bonus
#                             amount=amount-bonus
#                             valor = valor +bonus
#                             partner_line_obj.write(cr, uid, [l],{'pending':0.00, 'state':'redimed','type':'subtract','mode_id':'output'})
#                             bono= True
#                         else:
#                             amount1 = amount1 - amount
#                             bonus = bonus - amount
#                             valor = valor +amount
#                             amount = 0.00
#                             partner_line_obj.write(cr, uid, [l],{'pending':bonus})
#                             bono= True
#                 context.update({'bonus':bono,'new_price':amount1,'price_bonus':valor})
#                 values=order_line_ref.onchange_offer(cr, uid, [line.id], line.product_id.id, line.offer, line.quantity, line.price_unit,line.margin,line.price_product,0.00,line.invoice_line_tax_id,line.price_iva,line.invoice_id.fiscal_position.id,context=context)['value']
#                 line.write(values)
#         self.button_reset_taxes(cr, uid, ids, context)
#         self.write(cr, uid, ids, {'bonus':bono})
#         return True

    
        
account_invoice()

class account_invoice_line(osv.osv):
    
    _inherit = 'account.invoice.line'
    _columns = {'price_bonus': fields.float('Dscto. Bono', digits_compute=dp.get_precision('AccountInvoice'),readonly=True)}
    
account_invoice_line()

