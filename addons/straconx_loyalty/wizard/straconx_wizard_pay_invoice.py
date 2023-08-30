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
from datetime import date
from datetime import datetime
import datetime as dt 
#from datetime import datetime, date, timedelta
import decimal_precision as dp
import netsvc
import binascii
import os
import uuid



class wizard_pay_invoice(osv.osv_memory):
    _inherit = "wizard.invoice.pay"

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        line_pay={}
        valor= 0
        mode_ids = []
        payment_ids = []
        self.pool.get(context['active_model']).button_reset_taxes(cr, uid,context['active_ids'], context)
        self.pool.get(context['active_model']).write(cr, uid,context['active_ids'], context)
        active_ids = context.get('active_ids',False)
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        account_invoice = context.get('active_model',False)
        if account_invoice:
            ai = self.pool.get('account.invoice').browse(cr,uid,context['active_id'])
            if ai.withhold:
                withhold = ai.withhold_id.total
        if 'value' not in context.keys():                
            for obj in objs:
                journal_ids=self.pool.get('account.journal').search(cr, uid, [('type','=','moves')], limit=1)
                res['shop_id']=obj.shop_id.id
                res['partner_id']=obj.partner_id.id
                res['company_id']=obj.partner_id.id
                res['amount']=obj.amount_total
                res['beneficiary']=obj.company_id.name 
                type_pay = 'receipt'
                res['type']= type_pay
                res['journal_id']=journal_ids and journal_ids[0] or None 
                context.update({'invoice_id':active_ids})
                cr.execute('select payment_id from rel_shop_payment rsp left join payment_mode pm on pm.id = rsp.payment_id where shop_id = %s and only_receipt = True and pos = True',[obj.shop_id.id,])
                paids=cr.fetchall()
                paids= [i[0] for i in paids]
                lines = self.pool.get('payment.mode').search(cr,uid,[('id','in',paids),('only_receipt','=',True)])
                if lines:
                    for l in lines:
                        lines_id = self.pool.get('payment.mode').browse(cr,uid,l)
                        if lines_id:
                            mode = lines_id
                            if mode:
                                line_pay=({'mode_id':mode.id,
                                           'partner_id':obj.partner_id.id,
                                           'amount': 0.00,
                                           'amount_received': 0.00,
                                           'received_date':time.strftime("%Y-%m-%d %H:%M:%S"),
                                           'company_id':obj.shop_id.company_id.id,
                                           'shop_id':obj.shop_id.id, 
                                           'type':type_pay,
                                           'state':'draft',
                                           'required_bank':mode.required_bank,    
                                           'required_bank': mode.required_bank,
                                           'required_document':mode.required_document,
                                           'authorization': mode.authorization,
                                           'cash':mode.cash,
                                           'check':mode.check,
                                           'others':mode.others,
                                           'credit_notes': mode.credit_notes,
                                           'debit_notes':mode.debit_notes,
                                           'bonus': mode.bonus,
                                           'credit_card': mode.credit_card,
                                           'discount_employee': mode.discount_employee,
                                           'required_line_account':mode.required_line_account,
                                           'deposit_date':time.strftime("%Y-%m-%d %H:%M:%S")  
                                           })
                            else:
                                raise osv.except_osv(_('Error!'),_('No hay formas de pago definidas para esta tienda.'))
                        payment_ids.append(line_pay)
                    res['payment_ids']=payment_ids
        else:
            res = context['value']
        return res
        
    def pay(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        loyalty_obj = self.pool.get('sales.loyalty')
        loyalty_partner_obj = self.pool.get('sales.loyalty.partner')
        partner_obj = self.pool.get('res.partner')
        period_obj = self.pool.get('account.period')
        partner_line_obj = self.pool.get('sales.loyalty.partner.line')
        if context is None:
            context={}
        cash = 0.00
        l_part_id = []
        credit_card = 0.00
        check = 0.00
        credit_note = 0.00
        deposit = 0.00
        total = 0.00
        penalization = 1.00
        bank_id = False
        amount_discount = 0.00
        amount_untaxed = 0.00
        date_start = False
        date_expired = False
        partner_id = False
        today = time.strftime("%Y-%m-%d")
        bonus_ids = False
        res=super(wizard_pay_invoice,self).pay(cr, uid, ids, context)
        pos = context.get('default_pos',False)
        invoice = context.get('invoice',False)
        revised = False
        for wizard in self.browse(cr, uid, ids, context):
            for pay in wizard.payment_ids:
                if pay.mode_id.cash:
                    cash += pay.amount
                elif pay.mode_id.credit_card:
                    credit_card += pay.amount
                elif pay.mode_id.check:
                    check +=pay.amount
                elif pay.mode_id.deposit:
                    deposit += pay.amount
                elif pay.mode_id.credit_notes:
                    credit_note += pay.amount
                if pay.bank_id:
                    bank_id = pay.bank_id.id
                if pay.mode_id.bonus and pay.campaing_id.id and pay.bonus_id:
                        bonus_ids = partner_line_obj.search(cr, uid,[('campaing_id','=',pay.campaing_id.id),('partner_id','=',pay.partner_id.id),('state','=','pending')])
                        if bonus_ids:
                            partner_line_obj.write(cr,uid,bonus_ids,{'state':'redimed'})

        loyalty_ids = loyalty_obj.search(cr,uid,[('active','=',True),('date_to','>=',today)])
        if loyalty_ids:
            loyalty_id = loyalty_obj.browse(cr,uid,loyalty_ids[-1])
            penalization = loyalty_id.penalization *0.01
            days_start = loyalty_id.days_start
            days_end = loyalty_id.days_start + loyalty_id.days
        else:
            return res
        if invoice:
            invoice_id = invoice_obj.browse(cr,uid,invoice)
            partner_id = invoice_id.partner_id 
            amount_untaxed = invoice_id.amount_untaxed 
            amount_discount = invoice_id.amount_total_offer + invoice_id.amount_total_discount
            date_invoice = dt.datetime.strptime(invoice_id.date_invoice, '%Y-%m-%d').date()  
            fecha_1 = today[0:4] + '-11-01'               
            fecha_1 = dt.datetime.strptime(fecha_1, '%Y-%m-%d').date()    
            fecha_2 = today[0:4] + '-11-15'
            fecha_2 = dt.datetime.strptime(fecha_2, '%Y-%m-%d').date()     
            fecha_3 = today[0:4] + '-11-16'
            fecha_3 = dt.datetime.strptime(fecha_3, '%Y-%m-%d').date()  
            fecha_4 = today[0:4] + '-11-30'
            fecha_4 = dt.datetime.strptime(fecha_4, '%Y-%m-%d').date()  
            year = str(int(today[0:4]) + 1)
            if date_invoice >= fecha_1 and date_invoice <= fecha_2:
                date_start = year + '-01-01'
                date_start = dt.datetime.strptime(date_start, '%Y-%m-%d').date() 
                date_expired = year + '-01-31'
                date_expired = dt.datetime.strptime(date_expired, '%Y-%m-%d').date() 
            elif date_invoice >= fecha_3 and date_invoice <= fecha_4:
                date_start = year + '-02-01'
                date_start = dt.datetime.strptime(date_start, '%Y-%m-%d').date() 
                date_expired = year + '-02-28'
                date_expired = dt.datetime.strptime(date_expired, '%Y-%m-%d').date()
            else:
                date_start = year + '-03-01'
                date_start = dt.datetime.strptime(date_start, '%Y-%m-%d').date() 
                date_expired = year + '-03-31'
                date_expired = dt.datetime.strptime(date_expired, '%Y-%m-%d').date()
            if invoice_id.amount_total < (cash+credit_card+check+deposit-credit_note):
                cash = cash - ((cash+credit_card+check+deposit-credit_note)-invoice_id.amount_total)            
#             date_start = date_invoice + dt.timedelta(days=days_start)
#             date_expired = date_invoice + dt.timedelta(days=days_end)
        if amount_discount==0.00:
            penalization = 1
        
        for x in range(1,len(invoice_id.vat)):
            if x == 4:
                valor = int(invoice_id.vat[x])            
        if partner_id:
            if valor <= 5 and (partner_id.segmento_id.name=="TIENDAS" or not partner_id.segmento_id):
                if not partner_id.loyalty_card:
                    loyalty_card = str(uuid.uuid4().get_hex().upper()[0:15])
                    partner_obj.write(cr,uid,[invoice_id.partner_id.id],{'loyalty_card':loyalty_card})
                    l_part_id=[loyalty_partner_obj.create(cr,uid,{'name':loyalty_card, 'partner_id':partner_id.id,'vat':partner_id.vat})]
                else:
                    l_part_id = loyalty_partner_obj.search(cr, uid, [('partner_id','=',partner_id.id)])
                    if not l_part_id:
                        l_part_id=[loyalty_partner_obj.create(cr,uid,{'name':partner_id.loyalty_card, 'partner_id':partner_id.id,'vat':partner_id.vat})]            
        if pos:
            
            if valor <= 5 and (partner_id.segmento_id.name=="TIENDAS" or not partner_id.segmento_id) and not pay.mode_id.bonus:
                for line in loyalty_id.loyalty_ids:
                    if line.mode_id=='cash' and line.from_amount <= cash <= line.to_amount: 
                        total += (cash*line.bonus*0.01*penalization)
                    elif line.mode_id=='credit_card' and line.from_amount <= credit_card <= line.to_amount and line.bank_id.id == bank_id:
                            total += (credit_card*line.bonus*0.01*penalization)
                            revised = True
                    elif line.mode_id=='credit_card' and line.from_amount <= credit_card <= line.to_amount and (not line.bank_id.id) and not revised:
                            total += (credit_card*line.bonus*0.01*penalization)
                    elif line.mode_id=='check' and line.from_amount <= check <= line.to_amount:
                            total += (check*line.bonus*0.01*penalization)
                    elif line.mode_id=='deposit' and line.from_amount <= deposit <= line.to_amount:
                            total += (deposit*line.bonus*0.01*penalization)
                    elif line.mode_id=='credit_note' and line.from_amount <= credit_note <= line.to_amount:
                            total -= (credit_note*line.bonus*0.01)
                if date_expired:
                    period_ids = period_obj.search(cr, uid, [('date_start','<=',date_expired),('date_stop','>=',date_expired)])
                    if period_ids:
                        period_id = period_obj.browse(cr,uid,period_ids[0])
                    else:
                        period_id = invoice_id.period_id
                            
                if total > 0.00:
                    type_bonus = 'add'
                    mode_id = 'input'
                else:
                    type_bonus = 'subtract'
                    mode_id = 'output'
    
                if invoice_id.amount_untaxed >0.00:
                    vat_rest =  invoice_id.amount_untaxed /invoice_id.amount_total                
                    total = total*vat_rest
                    percent = (total / invoice_id.amount_untaxed)*100                
                if l_part_id:
                    l_part_name=l_part_id[-1]
                if total !=0.00:                
                    vals = {
                            'type': type_bonus,
                            'mode_id': mode_id,
                            'invoice_id': invoice_id.id,
                            'date': invoice_id.date_invoice,
                            'campaing_id': loyalty_id.id,
                            'bonus': total,
                            'pending':total,
                            'name': l_part_name,
                            'amount_invoice': invoice_id.amount_untaxed,
                            'percent': percent,
                            'partner_id':invoice_id.partner_id.id,
                            'date_start': date_start,
                            'date_expired': date_expired,
                            'period_id': period_id.id,
                            'state':'pending'              
                            } 
                
                    self.pool.get('sales.loyalty.partner.line').create(cr,uid,vals,context)
        return res
        
wizard_pay_invoice()



class payment(osv.osv_memory):
    _inherit = "wizard.invoice.pay.lines"
    
    _columns = {
                'bonus': fields.boolean("Bonos"),
                "campaing_id": fields.many2one("sales.loyalty", "Código de Campaña"),
                "bonus_id": fields.many2one("sales.loyalty.partner", "Código del Bono"),
                }
    
    def on_change_bonus_id(self, cr, uid, ids, partner_id=False, campaing_id=False ,bonus=False, amount=0.00, inv=False, context=None):
        result = {}
        bonus_ids = False
        valor_fact = 0.00
        amount2= 0.00
        valor = 0.00
        campaing_obj = self.pool.get('sales.loyalty')
        partner_obj = self.pool.get('sales.loyalty.partner')
        partner_line_obj = self.pool.get('sales.loyalty.partner.line')
        partner_obj = self.pool.get('res.partner')
        today = time.strftime("%Y-%m-%d")
        code_ids = partner_line_obj.search(cr,uid,[('partner_id','=',partner_id)])
        if code_ids:
            bonus_code = partner_line_obj.browse(cr,uid,code_ids[0]).id
            result['bonus_id'] = bonus_code
        if not amount:
            amount = 0.00
        if bonus:
            if campaing_id:
                campaing_id = campaing_obj.browse(cr,uid,campaing_id)                
                valor_fac = inv*campaing_id.maximun_pay/100.00
                if campaing_id.acumuled:
                    bonus_ids = partner_line_obj.search(cr, uid,[('campaing_id','=',campaing_id.id),('partner_id','=',partner_id),('state','=','pending')])
                else:
                    bonus_ids = partner_line_obj.search(cr, uid, [('campaing_id','=',campaing_id.id),('partner_id','=',partner_id),('state','=','pending'),('date_start','<=',today),('date_expired','>=',campaing_id.date_expired)])
            if bonus_ids:
                    for l in bonus_ids:
                        amount = partner_line_obj.browse(cr,uid,l).bonus
                        if valor_fac > round(amount,2):
                            amount2 += round(amount,2)
                            valor_fac = valor_fac- round(amount,2)
                        else:
                            valor = round(amount,2) - valor_fac
                            amount2 += valor_fac
                            valor_fac = 0.00
            result['amount'] = amount2

        return {'value':result}

payment()
