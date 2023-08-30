# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################


from osv import fields, osv
from tools.translate import _
import time
from datetime import datetime
import decimal_precision as dp
import netsvc
from account_voucher import account_voucher

class wizard_pay_invoice(osv.osv_memory):
    _name = "wizard.invoice.pay"
        
    def _debt(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for pay in self.browse(cr, uid, ids, context=context):
            rdc = self.pool.get('decimal.precision').search(cr,uid,[('name','=','Account')]) 
            rd = self.pool.get('decimal.precision').browse(cr,uid,rdc[0]).digits
            debt = 0.00
            paid = 0.00
            if pay.payment_ids:
                for paylines in pay.payment_ids:
                    if paylines.mode_id:
                        paid += round(paylines.amount,rd)
                debt = round(paid - pay.amount  ,rd)
            result[pay.id]={'change':debt,'paid':paid} 
        return result
    
    _columns = {
                'partner_id':fields.many2one('res.partner', 'partner', required=False),
                'journal_id':fields.many2one('account.journal', 'Journal', required=False),
                'payment_ids':fields.one2many('wizard.invoice.pay.lines', 'wizard_id', 'payments', required=False),
                'shop_id':fields.many2one('sale.shop', 'Shop', required=False),
                'amount': fields.float('Total amount', digits_compute= dp.get_precision('Account')),
                'change': fields.function(_debt, method=True,type="float", string='Change', store=False,digits_compute= dp.get_precision('Account'), multi='debt'),
                'paid': fields.function(_debt, method=True,type="float", string='Paid', store=False,digits_compute= dp.get_precision('Account'), multi='debt'),
                }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        line_pay={}
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
        
    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, amount_paid=0.00, shop_id=False, context=None):
        context = context or {} 
        amount_debt = 0.00
        amount_received = 0.00
        change = 0.00
        line_osv = self.pool.get('wizard.invoice.pay.lines')
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['amount','amount_received','change','name'], context)
        for line in line_dr_ids:
            amount_debt += line.get('amount',0.0)
        change = amount_debt - amount_paid  
        return {'value': {'paid':amount_debt,'change':change}}

    def create_voucher(self, cr, uid, invoice, wizard, amount_pay, payment_ids, credit_notes, context={}):
        line_ids=[]
        line_cr_ids=[]
        line_dr_ids=[]
        voucher_obj=self.pool.get('account.voucher')
        vals_onchange=voucher_obj.on_change_receipt(cr, uid, [],None, 'receipt', context)
        values=vals_onchange['value']
        vals_onchange=voucher_obj.onchange_partner_id(cr, uid, [],wizard.partner_id.id, wizard.journal_id.id,wizard.amount,None,'receipt',time.strftime('%Y-%m-%d'),{'invoice_id':invoice.id, 'pos':True, 'credit_notes':credit_notes.keys()})
        values.update(vals_onchange['value'])
        total_credit=wizard.paid
        if not context:
            context = {}
        pos = context.get('pos',False)
        for line in values.get('line_dr_ids',[]):
            if line.get('move_line_id',None):
                move = self.pool.get('account.move.line').browse(cr, uid, line['move_line_id'])
                if move.invoice.id in credit_notes.keys():
                    line.update({'amount':credit_notes[move.invoice.id]})
                    if line['amount_unreconciled'] == line['amount']:
                        line['reconcile'] = True
                    line_dr_ids.append((0,0,line))

        for line in values.get('line_cr_ids',[]):
            amount = min(line.get('amount_unreconciled',0.0), abs(total_credit))
            line.update({'amount':amount})
            if line['amount_unreconciled'] == line['amount']:
                line['reconcile'] = True
            total_credit -= amount
            line_cr_ids.append((0,0,line))            
        values.update({'partner_id':wizard.partner_id.id,
                       'shop_id':wizard.shop_id.id,
                       'line_ids':line_ids,
                       'line_dr_ids':line_dr_ids,
                       'line_cr_ids':line_cr_ids,
                       'amount':amount_pay,
                       'journal_id':wizard.journal_id.id,
                       'name':invoice.origin or invoice.name or None,
                       'type':'receipt',
                       'company_id': wizard.shop_id.company_id.id,
                       'payments':[[6, 0, payment_ids]]})
        context['type']='receipt'
#TODO: Modificar para hacerlo más rápido.
        voucher_id=voucher_obj.create(cr, uid, values, context)
        return voucher_id
    
    def get_dict_payment(self,cr,uid,payment_ids,pay,invoice,context=None):
        change = context.get('change',0.00)
        if pay.mode_id.cash and change >0:
            amount = pay.amount - change
        else:
            amount = pay.amount
        return {
                           'mode_id':pay.mode_id.id,
                           'type':pay.type,
                           'name':pay.name,
                           'beneficiary':pay.beneficiary,
                           'received_date':pay.received_date,
                           'deposit_date':pay.deposit_date,
                           'partner_id':pay.partner_id.id,
                           'shop_id': pay.shop_id.id,
                           'company_id': pay.company_id.id,
                           'amount': amount,
                           'amount_received':pay.amount_received,
                           'authorization_credit':pay.authorization_credit,
                           'authorization':pay.authorization,
                           'bank_account_id':pay.bank_account_id.id,
                           'bank_id':pay.bank_id.id,
                           'type_account_bank':pay.type_account_bank.id,
                           'required_bank':pay.required_bank,
                           'credit_notes': pay.credit_notes,
                           'debit_notes': pay.debit_notes,
                           'credit_note_id': pay.credit_note_id.id or False,
                           'debit_note_id': pay.debit_note_id.id or False,
                           'required_document':pay.required_document,
                           'required_line_account': pay.required_line_account
                           }
        
    def is_oneline2pay(self,pay):
        return True
    
    def append_payment(self,cr,uid,payment_ids,pay,invoice,context=None):
        if self.is_oneline2pay(pay):
            payment_ids.append(self.pool.get('account.payments').create(cr, uid,self.get_dict_payment(cr, uid, payment_ids, pay,invoice,context=context)))
        return payment_ids

    #@profile
    def pay(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        pos = context.get('default_pos',False)
        if pos:
            context.update({'pos':True})
        res={}
        invoice = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
        context.update({'invoice':invoice.id})
        cr.execute('SELECT id FROM account_invoice_line WHERE invoice_id = %s AND authorized = false',(invoice.id,))
        result = cr.fetchall()
        if result:
            cr.execute('UPDATE account_invoice SET AUTHORIZED = FALSE WHERE id = %s',(invoice.id,))
            raise osv.except_osv(_('Invoice not authorized!'),
                                     _('You must be solicited authorization to supervisor by this invoice, press calculate and digit the authorization'))
        else:
            cr.execute('UPDATE account_invoice SET AUTHORIZED = TRUE WHERE id = %s',(invoice.id,))                    

        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.journal_id:
                raise osv.except_osv(_('Error!'),_('You must enter a journal moves'))
            if not wizard.payment_ids:
                raise osv.except_osv(_('Error!'),_('You must entered at least one payment'))
            payment_ids=[]
            credit_notes={}
            debit_notes={} 
            amount_pay=0.00
            if wizard.paid == 0:
                raise osv.except_osv(_('Error!'),_('Necesita realizar por lo menos un pago para continuar'))
            if round(wizard.paid,2) < round(wizard.amount,2):
                raise osv.except_osv(_('Error!'),_('El valor de los pagos (%s) es menor que el valor a pagar (%s)')%(wizard.paid, wizard.amount))
            for pay in wizard.payment_ids:
                if pay.amount == 0:
                    self.pool.get('wizard.invoice.pay.lines').unlink(cr,uid,pay.id)
                else:
                    if wizard.change >0 and pay.cash:
                        context.update({'change':wizard.change})                        
                    if not pay.credit_note_id or pay.debit_note_id:
                        amount_pay+=pay.amount
                        payment_ids=self.append_payment(cr, uid, payment_ids, pay,invoice,context=context)
                    else:
                        if pay.credit_note_id:
                            if pay.amount > pay.credit_note_id.residual:
                                raise osv.except_osv(_('Error!'),_('No puede pagar un valor mayor al de la Nota de Crédito'))
                            credit_notes[pay.credit_note_id.id]=pay.amount
                            context.update({'credit_note_id':pay.credit_note_id.id})
                        if pay.debit_note_id:
                            if pay.amount > pay.debit_note_id.residual:
                                raise osv.except_osv(_('Error!'),_('No puede pagar un valor mayor al de la Nota de Débito'))
                            debit_notes[pay.debit_note_id.id]=pay.amount
                            context.update({'debit_note_id':pay.debit_note_id.id})
                            
                        payment_ids=self.append_payment(cr, uid, payment_ids, pay,invoice,context=context)
                        amount_pay+=pay.amount            
            amount_pay = amount_pay - wizard.change
            if round(amount_pay,2) >= round(invoice.amount_total,2):                        
                res1=self.pool.get(context['active_model']).action_validate(cr , uid, context['active_ids'],context=context)
                voucher_id=self.create_voucher(cr, uid, invoice, wizard, amount_pay, payment_ids, credit_notes, context)
                #invoice.write({'voucher_id':voucher_id})
                cr.execute("update account_invoice set write_date=now(), voucher_id=%s where id=%s",(voucher_id,invoice.id))
                res= self.pool.get('account.voucher').proforma_voucher_1(cr, uid, [voucher_id],context)
                if res.get('nodestroy',True):
                    res['nodestroy']=False
                if isinstance(res1, dict):
                    res1['context'].update({'return':res})
                    res1['nodestroy']=False
                    return res1
        return res
      
wizard_pay_invoice()

class payment(osv.osv_memory):
    _name = "wizard.invoice.pay.lines"
#    _inherit="account.payments"

    def _get_shop_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.printer_point_ids:
            if s.shop_id:
                shop_id = s.shop_id.id
            return shop_id 
        return None

    def _check_amount(self,cr,uid,ids):
        b=True
        for payment in self.browse(cr, uid, ids):
            if (payment['amount'] <= 0):
                b=False
        return b
    
    def _change(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for pay in self.browse(cr, uid, ids, context=context):
            result[pay.id]=0.0
            if pay.mode_id and pay.mode_id.cash:
#                 result[pay.id]=pay.change               
                if pay.amount_received >pay.amount:
                    result[pay.id]=pay.amount_received-pay.amount
        return result
    
    _columns = {
#                 "amount": fields.float("Debt Amount",digits_compute= dp.get_precision('Account')),
#                 "amount_received": fields.float("Amount Received",digits_compute= dp.get_precision('Account')),
                'wizard_id':fields.many2one('wizard.invoice.pay', 'wizard'),
                'credit_notes':fields.boolean('Credit Note', required=False),
                'debit_notes':fields.boolean('Debit Note', required=False),
                "credit_note_id": fields.many2one("account.invoice","Credit Notes",readonly=True,states={"draft":[("readonly",False)]}),
                "debit_note_id": fields.many2one("account.debit.note","Nota de Débito",readonly=True,states={"draft":[("readonly",False)]}),
                "shop_id":fields.many2one('sale.shop','shop',readonly=True,states={"draft":[("readonly",False)]}),
                "mode_id": fields.many2one("payment.mode","Type",readonly=True,states={"draft":[("readonly",False)]}),
                "name": fields.char("Document No.",size=20,readonly=True,states={"draft":[("readonly",False)]}),
                "cheque_id": fields.many2one("check.receipt","Cheque",readonly=True,states={"draft":[("readonly",False)]}),
                "type_account_bank": fields.many2one("res.bank.emisor","Emisor",readonly=True,states={"draft":[("readonly",False)]}),
                "type": fields.selection([("receipt","Receipt"),("payment","Payment")],"Mode"),
                "beneficiary": fields.char("Beneficiary",size=120,readonly=True,states={"draft":[("readonly",False)]}),
                "received_date": fields.date("Received Date"),
                "deposit_date": fields.date("Deposit Date",),
                "payment_date": fields.date("Payment Date"),
                "return_date": fields.date("Return Date",),
                "exchanged_date": fields.date("Exchanged Date",),
                "partner_id": fields.many2one("res.partner","Partner",readonly=True,states={"draft":[("readonly",False)]}),
                "amount": fields.float("Debt Amount",readonly=True,states={"draft":[("readonly",False)]},digits_compute= dp.get_precision('Account')),
                "amount_received": fields.float("Amount Received",readonly=True,states={"draft":[("readonly",False)]},digits_compute= dp.get_precision('Account')),
                'change': fields.function(_change, method=True,type="float", string='Change', store=False,digits_compute= dp.get_precision('Account')),
                "bank_account_id": fields.many2one("res.partner.bank","Account Bank",readonly=True,states={"draft":[("readonly",False)]}),        
                "bank_id": fields.many2one("res.bank","Bank",readonly=True,states={"draft":[("readonly",False)]}),
                "authorization_credit": fields.char("authorization",size=32,readonly=True,states={"draft":[("readonly",False)]}),
                "state": fields.selection([("draft","Draft"),("hold","Hold"),("paid","Paid"),("rejected","Rejected"),("protested","Protested"),("exchanged","Exchanged"),("cancel","Cancel")],"State", readonly=True),
                "vouch_id": fields.many2one("account.voucher","Voucher",readonly=True,states={"draft":[("readonly",False)]}),
                "vouch_name": fields.related('vouch_id','reference', type="char", size=200,relation="account.voucher",store=True, string="Voucher"),
                "period_id":fields.many2one('account.period','Period',readonly=True, states={'draft':[('readonly',False)]}),
                'required_bank':fields.boolean('Required Bank', required=False),
                'required_document':fields.boolean('Required Document', required=False),
                'required_seq':fields.boolean('Required Sequence', required=False),
                'cash':fields.boolean('Cash', required=False),
                'others':fields.boolean('Others', required=False),
                'authorization':fields.boolean('authorization', required=False),
                'check': fields.related('mode_id','check', type='boolean', relation='payment.mode', string='Check?', readonly=True),
                'credit_card': fields.related('mode_id','credit_card', type='boolean', relation='payment.mode', string='credit card?', readonly=True),
                'deposit_id':fields.many2one('deposit.register', 'deposit', required=False),
                'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}), 
                'pending':fields.boolean('Pending', states={'posted':[('readonly',True)]}),
                "user_id":fields.many2one('res.users','User'),
                'motive':fields.char('Motive', size=60),
                'number_deposit':fields.char('Number Deposit', size=32, readonly=True, states={"draft":[("readonly",False)],"hold":[("readonly",False)]}, help="This number is used by deposit credit card payments"),
                "amount_commission": fields.float("Amount Commission",readonly=True,states={"draft":[("readonly",False)],"hold":[("readonly",False)]},digits_compute= dp.get_precision('Account')),
                'old_id': fields.many2one('account.payments', 'Old Cheque', required=False),
                'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
                'statement_line_id': fields.many2one('account.bank.statement.line', 'Statement Line', readonly=True),
                'required_line_account':fields.boolean('Requiere línea contable', required=False),                
                'move_id_line': fields.many2one('account.move.line', 'Línea Contable'),
                }
    
    _defaults={
                "shop_id": _get_shop_id,
                "received_date": lambda *a: time.strftime('%Y-%m-%d'),
                "type": lambda self,cr,uid,context: context.get("type","receipt"),
                "partner_id": lambda self,cr,uid,context: context.get("partner_id",False),
                "state": lambda *a: "draft",
                "received_date": lambda *a: time.strftime('%Y-%m-%d'),
                "company_id": lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
                "user_id": lambda obj, cr, uid, context: uid,
               }
       
   
    def on_change_shop(self,cr,uid,ids,shop,mode_id,context=None):
        if context is None:
            context = {}
        values={'value':{},'domain':{}}
        m_payment = self.pool.get('payment.mode')
        mode_ids = []
        if shop:
            cr.execute('select payment_id from rel_shop_payment where shop_id = %s',[shop,])
            paids=cr.fetchall()
            paids= [i[0] for i in paids]
            lines = m_payment.search(cr,uid,[('id','in',paids),('only_receipt','=',True)])
            for l in lines:
                lines_id = self.pool.get('payment.mode').browse(cr,uid,l)
                mode_ids.append(lines_id.id)
            domain={'mode_id':[('id','in', mode_ids)]}
            values['domain']=domain

        if mode_id:
            mode_pay = m_payment.browse(cr,uid,mode_id)
            values['value']['cash']=mode_pay.cash
            values['value']['credit_card']=mode_pay.credit_card
            values['value']['required_bank']=mode_pay.required_bank
            values['value']['required_document']=mode_pay.required_document
            values['value']['required_line_account']=mode_pay.required_line_account
            values['value']['required_seq']=mode_pay.required_seq
            values['value']['authorization']=mode_pay.authorization
            if (mode_pay.check and mode_pay.to_deposit):
                values['value']['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
            elif mode_pay.credit_card:
                values['value']['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
            elif mode_pay.others:
                values['value']['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                values['value']['deposit_date']=None
        return values
    
    def on_change_amount_receive(self, cr, uid, ids, amount_receive=0.00, amount=0.00, mode=False, context=None):
        values={}
        partner_id = False
        if context:
            partner_id = context.get('partner_id',False)
        mode_payment = self.pool.get('payment.mode').browse(cr, uid, mode, context) 
        if mode:
            mode_pay=self.pool.get('payment.mode').browse(cr, uid, mode, context)
            values['cash']=mode_pay.cash
            values['company_id']=mode_pay.company_id.id
            values['credit_card']=mode_pay.credit_card
            values['required_bank']=mode_pay.required_bank
            values['required_document']=mode_pay.required_document
            values['required_seq']=mode_pay.required_seq
            values['authorization']=mode_pay.authorization
            values['required_line_account']=mode_pay.required_line_account            
            if (mode_pay.check and mode_pay.to_deposit):
                values['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                if partner_id:
                    abnk_ids = self.pool.get('res.partner.bank').search(cr,uid,[('partner_id','=',partner_id),('state','=','bank')])
                    if abnk_ids:
                        if len(abnk_ids)>0:
                            abnk_ids = self.pool.get('res.partner.bank').search(cr,uid,[('partner_id','=',partner_id),('default_bank','=',True)])
                            if abnk_ids:
                                bank_account_id = self.pool.get('res.partner.bank').browse(cr,uid,abnk_ids[0]).id
                                values['bank_account_id'] = bank_account_id 
            elif (mode_pay.credit_card and mode_pay.only_receipt):
                values['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
            elif (mode_pay.others and mode_pay.only_receipt):
                values['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                values['deposit_date']=None
            if amount_receive:
                if mode_payment.cash:
                    if amount_receive>=amount:
                        values['change']=amount_receive-amount
                    else:
                        values['amount_receive']=0
                        raise osv.except_osv(_('Error!'),_('El valor del monto recibido debe ser mayor al monto a pagar'))
                else:
                    values['amount_receive']=amount
            else:
                amount_receive = amount
                values['amount_receive'] = amount_receive
                values['amount'] = amount_receive
        return {'value':values}
                
                
                
    def on_change_bonus_id(self, cr, uid, ids, partner_id=False, campaing_id=False ,bonus=False, amount=0.00, context=None):
        result = {}
        bonus_ids = False
        campaing_obj = self.pool.get('sales.loyalty')
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
                if campaing_id.acumuled:
                    bonus_ids = partner_line_obj.search(cr, uid, [('campaing_id','=',campaing_id.id),('partner_id','=',partner_id),('state','=','pending')])
                else:
                    bonus_ids = partner_line_obj.search(cr, uid, [('campaing_id','=',campaing_id.id),('partner_id','=',partner_id),('state','=','pending'),('date_start','>=',today),('date_expired','<=',today)])
            if bonus_ids:
                    for l in bonus_ids:
                        amount += partner_line_obj.browse(cr,uid,l).bonus
            result['amount'] = amount

        return {'value':result}
    
    def on_change_credit_note(self, cr, uid, ids, credit_note=None, amount=0, context=None):
        result={}
        if not amount:
            amount = 0.00
        if credit_note:
            credit_note = self.pool.get('account.invoice').browse(cr, uid, credit_note, context)
            if credit_note.residual >= amount:
                result['amount']=credit_note.residual
        return {'value':result}

    def on_change_debit_note(self, cr, uid, ids, debit_note=None, amount=0, context=None):
        result={}
        if not amount:
            amount = 0.00
        if debit_note:
            debit_note = self.pool.get('account.debit.note').browse(cr, uid, debit_note, context)
            if debit_note.residual >= amount:
                result['amount']=debit_note.residual
        return {'value':result}

    def on_change_withhold(self, cr, uid, ids, withhold=None, amount=0, context=None):
        result={}
        if not amount:
            amount = 0.00
        if withhold:
            witthold = self.pool.get('account.invoice').browse(cr, uid, withhold, context)
            if withhold.residual >= amount:
                result['amount']=withhold.residual
        return {'value':result}


    def on_change_account_bank(self, cr, uid, ids, account_bank=None, partner_id=None, company_id=None, line_payments_ids=None, context=None):
        result = {}
        domain = {'bank_id':[]}
        if account_bank:
            if not (partner_id and company_id):
                return {}
            account_bank=self.pool.get('res.partner.bank').browse(cr, uid, account_bank)
            if self.pool.get('res.company').browse(cr, uid, company_id, context).partner_id.id == partner_id:
                next_cheque = self.pool.get('check.receipt').search(cr,uid,[('book_id.name','=',account_bank.id),('state','=','open')],order='name asc',limit=1)
                result['name'] = next_cheque and self.pool.get('check.receipt').browse(cr,uid,next_cheque[0],context).name or None 
                result['cheque_id']= next_cheque and next_cheque[0] or None
            bank_id= account_bank.bank.id
            result['bank_id']=bank_id
            domain={'bank_id':[('id','=',bank_id)]}
        return {'value':result, 'domain':domain}
    
    def on_change_cheque(self, cr, uid, ids, cheque_id=None, context=None):
        result = {}
        if cheque_id:
            name = self.pool.get('check.receipt').browse(cr,uid,cheque_id,context).name
            result['name']=str(name)
        return {'value':result}
        
    def on_change_amount(self, cr, uid, ids, line_payments_ids=[], amount=None, context=None):
        result = {}
        data=None
        if amount>0:
            if line_payments_ids:
                for line in line_payments_ids:
                    data=line[2]
                    if data:
                        if data.get('amount',False):
                            amount-= data['amount']
                            result['amount']=amount
                    else:
                        result['amount']=amount
            else:
                result['amount']=amount            
        return {'value':result}


    def on_change_move_line_id(self, cr, uid, ids, move_id_line=None, amount=0, context=None):
        result={}
        if not amount:
            amount = 0.00
        if move_id_line:
            move_id_line = self.pool.get('account.move.line').browse(cr, uid, move_id_line, context)
            if move_id_line.amount_currency >= amount:
                result['amount']=move_id_line.debit
                result['name'] = move_id_line.ref or move_id_line.reference
        return {'value':result}

payment()
