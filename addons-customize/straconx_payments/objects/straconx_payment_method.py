# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################

import time
from lxml import etree
import decimal_precision as dp

import netsvc
import pooler
from osv import fields, osv, orm
from tools.translate import _
from tools import amount_to_text_es


class account_move(osv.osv):
    _inherit = "account.move"
    _columns = {'narration': fields.text('Narration', states={'posted': [('readonly', True)]})}
account_move()


class payments_voucher(osv.osv):
    _name = "payments.voucher"
    _columns = {"payments_id": fields.many2one('account.payments', 'Vales'),
                "voucher_id": fields.many2one('account.voucher', 'Pagos'),
                "final_beneficiary": fields.many2one('res.partner', 'Pagos'),
                "amount": fields.float("Monto", digits_compute=dp.get_precision('Account')),
                }
payments_voucher()


class account_move_line(osv.osv):
    _inherit = "account.move.line"
    _columns = {'pending': fields.boolean('Pending', states={'posted': [('readonly', True)]})}
account_move_line()


class account_payment_method(osv.osv):

    def _check_amount(self, cr, uid, ids):
        b = True
        for payment in self.browse(cr, uid, ids):
            if (payment['amount'] <= 0 and payment['amount_received'] <= 0 and payment['amount_credit'] <= 0):
                b = False
        return b

    def _check_unique(self, cr, uid, ids):
        b = True
        for payment in self.browse(cr, uid, ids):
            if payment.cheque_id:
                check_old = self.search(cr, uid, [('partner_id', '=', payment.cheque_id.partner_id.id),
                                                  ('bank_account_id', '=', payment.cheque_id.bank_account_id.id),
                                                  ('name', '=', payment.cheque_id.name), ('state', '=', payment.cheque_id.state)])
                if check_old:
                    for ch in check_old:
                        chk_id = self.browse(cr, uid, ch)
                        if chk_id.id != payment.cheque_id.id or chk_id.state == payment.cheque_id.state:
                            b = False
        return b

    def _change(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for pay in self.browse(cr, uid, ids, context=context):
            result[pay.id] = 0.0
            if pay.mode_id and pay.mode_id.cash:
                if pay.amount_received > pay.amount:
                    result[pay.id] = pay.amount_received-pay.amount
        return result

    def _calculate_amount_partial(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for line in self.browse(cr, uid, ids, context=context):
                res[line.id] = line.number_of_quotas and round(line.amount/line.number_of_quotas, 2) or 0
            return res

    _name="account.payments"
    _columns={
        "mode_id": fields.many2one("payment.mode","Type",readonly=True,states={"draft":[("readonly",False)]}),
        "name": fields.char("Document No.",size=40,readonly=True,states={"draft":[("readonly",False)]}),
        "cheque_id": fields.many2one("check.receipt","Cheque",readonly=True,states={"draft":[("readonly",False)]}),
        "type_account_bank": fields.many2one("res.bank.emisor","Emisor",readonly=True,states={"draft":[("readonly",False)]}),
        "type": fields.selection([("receipt","Receipt"),("payment","Payment")],"Mode"),
        "beneficiary": fields.char("Beneficiary",size=120,readonly=True,states={"draft":[("readonly",False)]}, help="Llenar este campo solamente si el beneficiario es distinto al Proveedor"),
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
        "authorization_credit": fields.char("authorization",size=37,readonly=True,states={"draft":[("readonly",False)]}),
        "state": fields.selection([("draft","Borrador"),("hold","Pendiente"),("paid","Pagado"),("rejected","Devuelto"),("protested","Protestado"),("exchanged","Canjeado"),("cancel","Anulado")],"State", readonly=True),
        "vouch_id": fields.many2one("account.voucher","Voucher",readonly=True,states={"draft":[("readonly",False)]}),
        "vouch_name": fields.related('vouch_id','reference', type="char", size=200,relation="account.voucher",store=True, string="Voucher"),
        "shop_id":fields.many2one("sale.shop","Shop",required=1),
        "period_id":fields.many2one('account.period','Period',readonly=True, states={'draft':[('readonly',False)]}),
        "debit_note_id": fields.many2one("account.debit.note","Debit Note",readonly=True,states={"draft":[("readonly",False)]}),
        'required_bank':fields.boolean('Required Bank', required=False),
        'required_document':fields.boolean('Required Document', required=False),
        'required_seq':fields.boolean('Required Sequence', required=False),
        'required_seq_check':fields.boolean('Required Sequence', required=False),
        'cash':fields.boolean('Cash', required=False),
        'authorization':fields.boolean('authorization', required=False),
        'check': fields.related('mode_id','check', type='boolean', relation='payment.mode', string='Check?', readonly=True),
        'credit_card': fields.related('mode_id','credit_card', type='boolean', relation='payment.mode', string='credit card?', readonly=True),
        'deposit_id':fields.many2one('deposit.register', 'deposit', required=False),
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}), 
        'pending':fields.boolean('Pending', states={'posted':[('readonly',True)]}),
        "user_id":fields.many2one('res.users','User'),
        'motive':fields.char('Motive', size=250),
        'number_deposit':fields.char('Number Deposit', size=32, readonly=True, states={"draft":[("readonly",False)],"hold":[("readonly",False)]}, help="This number is used by deposit credit card payments"),
        "amount_commission": fields.float("Amount Commission",readonly=True,states={"draft":[("readonly",False)],"hold":[("readonly",False)]},digits_compute= dp.get_precision('Account')),
        'old_id': fields.many2one('account.payments', 'Old Cheque', required=False),
        'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
        'statement_line_id': fields.many2one('account.bank.statement.line', 'Statement Line', readonly=True),
        'credit_note_id': fields.many2one("account.invoice","Credit Notes",readonly=True,states={"draft":[("readonly",False)]}),
        'credit_notes':fields.boolean('Credit Note', required=False),
        'discount_employee':fields.boolean("Discount employee"),
        'number_of_quotas':fields.integer("Quotas"),
        'collection_form':fields.selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', select=True, readonly=True,states={'draft': [('readonly', False)]}),
        'amount_partial':fields.function(_calculate_amount_partial, method=True, string='Next Amount Paid', store=True, digits_compute=dp.get_precision('Sale Price')),      
        "pay_vouch_ids": fields.one2many("payments.voucher","payments_id","Payments", readonly=True,states={"draft":[("readonly",False)]}),     
        'debit_notes':fields.boolean('Debit Notes', required=False),    
        'nb_print':fields.integer('Impresiones'),
        'move_id_line': fields.many2one('account.move.line', 'Línea Contable'),
        'required_line_account':fields.boolean('Requiere línea contable', required=False),
        "amount_credit": fields.float("Monto Crédito",  states={'draft':[('readonly',False)]}),
        'active': fields.boolean('Active')
    }

    _defaults={
        "type": lambda self,cr,uid,context: context.get("type","receipt"),
        "partner_id": lambda self,cr,uid,context: context.get("partner_id",False),
        "state": lambda *a: "draft",
        "deposit_date": lambda *a: time.strftime('%Y-%m-%d'),
        "received_date": lambda *a: time.strftime('%Y-%m-%d'),
        "payment_date": lambda *a: time.strftime('%Y-%m-%d'),
        "company_id": lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
        "user_id": lambda obj, cr, uid, context: uid,
        'active': True
        
#        "mode_id":False,
    }
    
    _order = 'bank_id asc, partner_id asc, deposit_date asc, received_date asc, bank_account_id asc, name asc'
    _rec_name = 'mode_id'
    _constraints = [(_check_amount,'El valor de los pagos realizados es diferente al valor a pagar o ya existe otro cheque con el mismo número, empresa y cuenta bancaria. Por favor revise.' ,['amount'])]
    _sql_constraints = [
                    ('cheque_out_uniq','unique(bank_account_id,name,partner_id,state)', 'There is another cheque with this number and this partner, please verify'),
                    ]
    
    
    def on_change_company(self, cr, uid, ids, comp=False, company_id=False,context=None):
        result = {}
        if comp != company_id:
            result['company_id']=company_id
            result['mode_id']= self.pool.get('payment.mode').search(cr,uid,[('company_id','=',company_id)])[0]
        return {'value':result, 'domain':{'mode_id':[('company_id', '=',company_id)]}}
                
    def on_change_mode_payment(self, cr, uid, ids, mode=False, partner=False, amount=0.00, type='receipt', company_id=False, date=None, shop_id=False, amount_payment_mode=0.00,context=None):
        result = {}
        domain={}
        res=[]
        c=0
        result['required_seq_check']= False
        if context is None:
            context={} 
            partner_cheque = []
        else:
            partner_cheque = context.get('partner_id',False)
        if not (partner or context.get('receivable',False)):
            raise osv.except_osv(_('Invalid action!'), _('You must define first a partner!'))
        if type in ('payment','advance_supplier'):
            domain['mode_id']=[('only_payment','=', True),('company_id','=',company_id)]
        else:
            domain['mode_id']=[('only_receipt','=', True),('company_id','=',company_id)]
        shop_id = shop_id or context.get('shop',False)
        result['shop_id']=shop_id
        payment_date = time.strftime("%Y-%m-%d %H:%M:%S")
        if not amount_payment_mode:
            amount_payment_mode = 0.00
        if amount:
            new_amount = amount - amount_payment_mode
            result['amount']= new_amount
        if shop_id:
#            cr.execute('select payment_id from rel_shop_payment where shop_id = %s',(context['shop'],))
            cr.execute('select payment_id from rel_shop_payment where shop_id = %s',(shop_id,))
            res=cr.fetchall()
            res= [i[0] for i in res]
        if context.get('received_date',False):
            received_date = context.get('received_date',False)
        else: 
            received_date = time.strftime('%Y-%m-%d')
            period_id = self.pool.get('account.period').search(cr, uid, [('date_start','<=',received_date),('date_stop','>=',received_date),('company_id','>=',company_id)])[0]
            result['period_id']=period_id
        if partner:
            if type in ('payment','advance_supplier'):
                md_obj = self.pool.get('payment.mode').browse(cr, uid, mode, context)           
                if md_obj.others and md_obj.required_line_account: 
                    result['partner_id']=partner
                else:
                    partner=self.pool.get('res.company').browse(cr, uid, company_id, context).partner_id.id
                    pt = self.pool.get('res.partner').browse(cr,uid,partner,context)
    #                 if not supplier:
    #                     supplier = pt.beneficiary
    #                 if not supplier:
    #                     supplier = pt.name
                    result['partner_id']=partner
                    
                    if partner_cheque:
                        pt_cheque = self.pool.get('res.partner').browse(cr,uid,partner_cheque,context)
                        beneficiary = pt_cheque.beneficiary or pt_cheque.name
                        result['beneficiary']=beneficiary                    
            else:
                result['partner_id']=partner
                cr.execute('select payment_id from rel_partner_payment where partner_id = %s',(partner,))
                res1=cr.fetchall()
                [res.remove(r[0]) for r in res1 if r[0] in res]
                domain['mode_id'].append(('id','in', res))
            partner_obj=self.pool.get('res.partner').browse(cr, uid, partner, context)
            #supplier_obj=self.pool.get('res.partner').browse(cr, uid, supplier, context)
            if not mode:
                if partner_obj.payment_type_supplier:
                    mode=partner_obj.payment_type_supplier.id
                    if partner_obj.bank_ids:
                        result['mode_id']=mode
                        result['company_id']=company_id
                        result['bank_account_id']=partner_obj.bank_ids[0].id
                        result['bank_id']=partner_obj.bank_ids[0].bank.id
                        result['payment_date']=payment_date
                        result['required_bank']=self.pool.get('payment.mode').browse(cr, uid, mode, context).required_bank
                        result['required_document']=self.pool.get('payment.mode').browse(cr, uid, mode, context).required_document
                        result['required_seq']=self.pool.get('payment.mode').browse(cr, uid, mode, context).required_seq
                        result['authorization']=self.pool.get('payment.mode').browse(cr, uid, mode, context).authorization
                        result['cash']=self.pool.get('payment.mode').browse(cr, uid, mode, context).cash
                        result['credit_card']=self.pool.get('payment.mode').browse(cr, uid, mode, context).credit_card
                        result['credit_notes']=self.pool.get('payment.mode').browse(cr, uid, mode, context).credit_notes
                        result['debit_notes']=self.pool.get('payment.mode').browse(cr, uid, mode, context).debit_notes
                        result['required_line_account']=self.pool.get('payment.mode').browse(cr, uid, mode, context).required_line_account  
            elif mode:                            
                mode_pay=self.pool.get('payment.mode').browse(cr, uid, mode, context)
                result['cash']=mode_pay.cash
                result['company_id']=company_id
                result['credit_card']=mode_pay.credit_card
                result['required_bank']=mode_pay.required_bank
                result['required_seq']=mode_pay.required_seq
                result['required_document']=mode_pay.required_document                
                result['authorization']=mode_pay.authorization
                result['required_line_account']=mode_pay.required_line_account
                result['credit_notes']=mode_pay.credit_notes
                result['debit_notes']=mode_pay.debit_notes   
                result['required_line_account']=mode_pay.required_line_account
                result['discount_employee']=mode_pay.discount_employee                                                     
                if (mode_pay.check and mode_pay.to_deposit):
                    result['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                elif (mode_pay.credit_card and mode_pay.only_receipt):
                    result['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                elif (mode_pay.others and mode_pay.only_receipt):
                    result['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    result['deposit_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                if type in('payment','advance_supplier'):
                    if mode_pay.required_bank and mode_pay.check:
                        if not mode_pay.bank_ids:
                            raise osv.except_osv(_('Error!'), _('You need a define a Cheque Book in this payment mode!'))    
                        else:                    
                            for bank_id in mode_pay.bank_ids:
                                if bank_id.state == 'open' and c==0:
                                    c=1    
                                    account_bank = bank_id
                                    result['bank_account_id'] = account_bank.name.id                    
                                    result['bank_id'] = account_bank.bank.id
                                    result['required_seq_check']=account_bank.s_sequence
                                    next_cheque = self.pool.get('check.receipt').search(cr,uid,[('book_id','=',account_bank.id),('state','=','open')],order='name asc',limit=1)
                                    result['name'] = next_cheque and self.pool.get('check.receipt').browse(cr,uid,next_cheque[0],context).name or None 
                                    result['cheque_id']= next_cheque and next_cheque[0] or None
                            if c==0:
                                raise osv.except_osv(_('Error!'), _('You need a select a Cheque Book in open state!'))
    #                        self.pool.get('check.receipt').write(cr,uid,name_cheque.id,{'state':'process','amount':amount,'process_date':date_p})
                    else:
                        result['bank_account_id'] = ''                    
                        result['bank_id'] = ''
                        result['name'] = ''
                        result['cheque_id'] = ''
                    result['emission_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                    result['process_date']=time.strftime("%Y-%m-%d %H:%M:%S")
                    result['payment_date']=time.strftime("%Y-%m-%d %H:%M:%S")
#                    result['beneficiary']=supplier
        return {'value':result, 'domain':domain}
    
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

    def on_change_credit_note(self, cr, uid, ids, credit_note=None, amount=0, context=None):
        result={}
        if not amount:
            amount = 0.00
        if credit_note:
            credit_note = self.pool.get('account.invoice').browse(cr, uid, credit_note, context)
            if credit_note.residual >= amount:
                result['amount']=credit_note.residual
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
    
    def onchange_number_of_quotas(self,cr,uid,ids,number_of_quotas,discount_employee,amount,context=None):
        if(discount_employee):
            if(number_of_quotas):
                if(number_of_quotas<0):                    
                    number_of_quotas=number_of_quotas*-1
                    return {"value":{"number_of_quotas":number_of_quotas,
                                     "amount_partial":round(amount/(number_of_quotas),2)
                                     },"warning":{"title":_("Validation Error!"),"message":_("The number of quotas to pay must be greater than 0")}}
                return {"value":{"amount_partial":round(amount/(number_of_quotas),2)}}
            return {"value":{"number_of_quotas":1,"amount_partial":amount},"warning":{"title":_("Validation Error!"),"message":_("The number of quotas to pay must be greater than 0")}}
        return {"value":{"number_of_quotas":0,"amount_partial":0}}
    
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

    def on_change_amount_receive(self, cr, uid, ids, amount_receive=None, amount=None, mode=None, context=None):
        values={}
        if mode:
            if amount_receive:
                if self.pool.get('payment.mode').browse(cr, uid, mode, context).cash:
                    if amount_receive>amount:
                        values['change']=amount_receive-amount
        return {'value':values}

    def unlink(self, cr, uid, ids, context=None):
        for pay in self.browse(cr, uid, ids, context):
            if pay.state != 'draft':
                raise osv.except_osv(_('Invalid action!'), _('You can only delete Payments with state Draft'))
            else:
                pay.write({'active':False})
        return super(account_payment_method, self).unlink(cr, uid, ids, context)
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not len(ids):
            return [] 
        for payment in self.browse(cr, uid, ids, context):
            name=""
            if payment.mode_id:
                name=name+"%s"%(payment.mode_id.name)
            res.append((payment.id, name))
        return res
    
    def button_paid(self,cr,uid,ids,context={}):
        self.write(cr, uid, ids, {"state":"paid"})
        for check in self.browse(cr, uid, ids):
            if check.cheque_id:
                self.pool.get('check.receipt').write(cr, uid, [check.cheque_id.id], {'state':'paid', 'amount':check.amount,'process_date':time.strftime('%Y-%m-%d')})
        return True

    def cancel_check(self, cr, uid, ids, context=None):
        payment = self.browse(cr, uid, ids,context=context)
        move_pool = self.pool.get('account.move')
        for pay in payment:
            if pay.state in ('hold','paid'):
                if pay.move_id.state=='posted':
                    move_pool.button_cancel(cr, uid, [pay.move_id.id], context={})
                    move_pool.unlink(cr, uid, [pay.move_id.id], context={})
                    self.write(cr,uid,[pay.id],{'state':'cancel'})
            if pay.cheque_id:
                self.pool.get('check.receipt').write(cr, uid, pay.cheque_id.id, {'state':'cancel','anulled_date':time.strftime('%Y-%m-%d')})
        return True
    

    def button_cancel_changed(self,cr,uid,ids,context={}):
        for chk in self.browse(cr,uid,ids):
            if chk.move_id:
                self.pool.get('account.move').button_cancel(cr, uid, [chk.move_id.id], context={})
                self.pool.get('account.move').unlink(cr, uid, [chk.move_id.id], context={})
            if chk.statement_line_id:
                if chk.statement_line_id.statement_id.state != 'open':
                    raise osv.except_osv(_("Error"),_("You can not cancel de changed check because the cash register is not state valid."))
                statement_id=chk.statement_line_id.statement_id
                pay=chk.statement_line_id.payment_id
                self.pool.get('account.payments').write(cr, uid, [pay.id], {'state':'draft'})
                self.pool.get('account.payments').unlink(cr, uid, [pay.id], context)
#                 cr.execute("DELETE FROM account_bank_statement_line WHERE id = %s", (chk.statement_line_id.id,))
                cr.execute("UPDATE account_bank_statement_line SET active=False, amount=0.00 WHERE id = %s", (chk.statement_line_id.id,))
                #self.pool.get('account.bank.statement').write(cr, uid, [statement_id],{})
                statement_id.write({})
            chk.write({"state":"hold"})
        return True

    def copy_data(self, cr, uid, id, default=None, context=None):
        if context is None:
            context={}
        if not context.get('flag',False):
            raise osv.except_osv(_("Error"),_("You can't duplicate a check or another payment."))
        else:
            return super(account_payment_method, self).copy_data(cr, uid, id, default,context)
    
    def button_protested_rejected(self,cr,uid,ids,data={},context=None):
        if context is None:
            context={}
        debit_note_pool=self.pool.get('account.debit.note')
        debit_note_line_pool=self.pool.get('account.debit.note.line')
        type=data.get('type', False)
        debit_note=[]
        for chk in self.browse(cr,uid,ids):
            if type:
                journal_ids=self.pool.get('account.journal').search(cr, uid, [('type','=','debit_note')])
                if not journal_ids:
                    raise osv.except_osv(_("Error"),_("You must create a Debit Note Journal"))
                if data.get('date',False):
                    period_id=self.pool.get('account.period').search(cr, uid, [('date_start','<=',data['date']),('date_stop','>=',data['date'])])
                type = 'exchanged' 
                type = data.get('type','exchanged')
                
                if type == 'exchanged':
                    account_id=chk.mode_id.debit_account_id.id
                elif type == 'protested':
                    if chk.deposit_id.account_deposit_id:
                        account_id=chk.deposit_id.account_deposit_id.id
                    else:
                        account_id=chk.mode_id.debit_account_id.id
                elif type == 'customer_changed':
                    account_id=chk.mode_id.debit_account_id.id
                    type = 'exchanged'
                else:
                    if chk.deposit_id:
                        account_id=chk.deposit_id.account_deposit_id.id
                    else:
                        account_id=chk.mode_id.debit_account_id.id
                debit_note_id = debit_note_pool.create(cr, uid, {
                                                     'partner_id':chk.partner_id.id,
                                                     #'account_id':chk.deposit_id.account_deposit_id.id,
                                                     'account_id':account_id,
                                                     'user_id':uid,
                                                     'journal_id':journal_ids[0],
                                                     'date':data['date'] or time.strftime('%Y-%m-%d'),
                                                     'period_id':period_id and period_id[0] or False,
                                                     'name': 'NOTA DE DEBITO POR CHEQUE '+type,
                                                     'reference': 'CHEQUE #'+chk.name+'/ BANCO '+chk.bank_account_id.bank.name,
                                                     'type':'debit_customer',
                                                     'narration':type
                                                    })
                debit_note.append(debit_note_id)
                
                debit_note_line_pool.create(cr, uid,{
                                                     'account_id':data['account_id'],
                                                     'name':'CHEQUE '+type+'/CUENTA # '+chk.bank_account_id.acc_number,
                                                     'amount':chk.amount,
                                                     'debit_note_id':debit_note_id,
                                                     })
                debit_note_line_pool.create(cr, uid,{
                                                     'account_id':data['account_id'],
                                                     'name':'N/D POR CHEQUE '+type,
                                                     'amount':data['amount_debit_note'],
                                                     'debit_note_id':debit_note_id,
                                                     })
                chk.write({'state':type,'return_date':data['date']})
        debit_note_pool.button_dummy(cr, uid,debit_note,context)
        debit_note_pool.confirm_debit_note(cr, uid,debit_note,context)
        return debit_note
    
    def on_change_debit_note(self, cr, uid, ids, debit_note=None, amount=0, context=None):
        result={}
        if not amount:
            amount = 0.00
        if debit_note:
            debit_note = self.pool.get('account.debit.note').browse(cr, uid, debit_note, context)
            if debit_note.residual >= amount:
                result['amount']=debit_note.residual
        return {'value':result}    
    
    def create_checks(self,cr,uid,ids,context={}): 
        for chk in self.browse(cr,uid,ids):        
            if chk.move_id:
                move_id = chk.move_id.id
            else:
                move_id = False 
            chk_id = self.pool.get('account.payments').create(cr, uid, {
                   'mode_id':chk.mode_id.id,
                   'type':chk.type,
                   'beneficiary':chk.beneficiary,
                   'received_date':chk.received_date,
                   'partner_id':chk.partner_id.id,
                   'amount':chk.amount,
                   'bank_account_id':chk.bank_account_id.id,
                   'bank_id':chk.bank_id.id,
                   'move_id': move_id,
                   'required_bank':chk.required_bank,
                   'required_document':chk.required_document,
                   'old_id':chk.id,
               })
            self.write(cr, uid, [chk.id], {'move_id':False,'state':'cancel'})
        return chk_id
    
    def button_generate(self,cr,uid,ids,context={}):
        if context is None:
            context = {}            
        data_pool = self.pool.get('ir.model.data')
        chk_id = self.create_checks(cr, uid, ids, context=context)
        action_model = False
        action = {}
        checks_ids = [] 
        checks_ids += [chk_id]
        if not checks_ids:
            raise osv.except_osv(_('Error'), _('No Cheques were created'))
        else:
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'straconx_payments', "act_view_cheque_in")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['nodestroy'] = True
            action['domain'] = "[('id','in', ["+','.join(map(str,checks_ids))+"])]"
        return action  
    
account_payment_method()
