# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class deposit_register(osv.osv):
    
    def _total_commission(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for dp in self.browse(cr, uid, ids, context=context):
            result[dp.id] = 0.0
            for line in dp.cheks_ids:
                result[dp.id] += line.amount_commission or 0.0
        return result
    
    def _get_default_journal(self, cr, uid, context=None):
        journal_id=self.pool.get('account.journal').search(cr, uid, [('type','=','moves')])
        if not journal_id: 
            return None
        return journal_id[0]
    
    def _get_amount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = 0.0
            if line.amount_cash > 0:
                res[line.id] = line.amount_cash
            for check in line.cheks_ids:
                if check.amount > 0:
                    res[line.id] += check.amount
        return res
        
    def _get_total_docs(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = 0
            for check in line.cheks_ids:
                if check.amount > 0:
                    res[line.id] += 1
        return res

        
        
    _name="deposit.register"
    _columns = {
                'name': fields.char('Deposit Register', size=64, readonly=True, states={'draft': [('readonly', False)]}, select=True),
                'printer_id':fields.many2one('printer.point', 'Cash', readonly=True),
                "mode_id": fields.many2one("payment.mode","Type deposit", readonly=True),
                "bank_id": fields.many2one("res.bank","Bank",readonly=True,states={"draft":[("readonly",False)]}),
                "amount": fields.function(_get_amount, method=True,type="float", string='Total Amount', store=True),
                "amount_cash": fields.float("Amount",readonly=True),
                'total_docs':fields.function(_get_total_docs, method=True, type='integer', string='# Docs', store=True),
                'date': fields.date('Date deposit', readonly=True),
                'cash_id':fields.many2one('account.bank.statement', 'Cash Register', readonly=True),
                'receipt':fields.char('Deposit Receipt Number', size=32, readonly=True,states={"draft":[("readonly",False)]}),
                'deposit_checks':fields.boolean('Check', required=False),
                'deposit_credit_card':fields.boolean('credit card', required=False),
                'cheks_ids':fields.one2many('account.payments', 'deposit_id', 'Check to deposit', readonly=True,states={"draft":[("readonly",False)]}),
                'account_deposit_id':fields.many2one('account.account', 'Account to Deposit', readonly=True,states={"draft":[("readonly",False)]}),
                'to_date': fields.date('To Date deposit',readonly=True,states={"draft":[("readonly",False)]}),
                'from_date': fields.date('From Date deposit',readonly=True,states={"draft":[("readonly",False)]}),
                'user_id':fields.many2one('res.users', 'User', readonly=True,states={"draft":[("readonly",False)]}),
                'shop_id':fields.many2one('sale.shop', 'Tienda', readonly=True,states={"draft":[("readonly",False)]}),
                'company_id':fields.many2one('res.company', 'Compañía', readonly=True,states={"draft":[("readonly",False)]}),
                'number_deposit':fields.char('Number of Deposit', size=32),
                "state": fields.selection([('draft','Draft'),('confirmed','Confirmed'),('deposit','deposit'), ('cancel','Canceled')],'State', readonly=True),
                'journal_id':fields.many2one('account.journal', 'Journal'),
                'check': fields.related('mode_id','check', type='boolean', relation='payment.mode', string='Check?', readonly=True ,store=True),
                #'amount_commission': fields.float('amount commission', digits=(16,2), readonly=True),
                "amount_commission": fields.function(_total_commission, method=True,type="float", string='Valor Comisión Bancaria',readonly=True,states={"draft":[("readonly",False)]}),
                #'checks': fields.related('mode_id','check', type='boolean', relation='payment.mode', string='Check?', readonly=True ,store=True),
                #'credit_card': fields.related('mode_id','credit_card', type='boolean', relation='payment.mode', string='Credit Card?', readonly=True ,store=True),
                'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
                'process_date': fields.date('Process Date',readonly=True,states={"draft":[("readonly",False)]}),
                'active': fields.boolean('Activo')
    }
    
    _sql_constraints = [('deposit_unique_statement','unique(mode_id,receipt,cash_id,state)', 'El depósito ya existe en otra caja. Por favor revisar.')]    

    _defaults={
        "deposit_checks": lambda *a: False,
        "deposit_credit_card": lambda *a: False,
        "state": lambda *a: 'draft',
        "journal_id": _get_default_journal,
        'user_id': lambda obj, cr, uid, context: uid,
        'process_date':lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        'shop_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).shop_id.id,
        'active': True
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_("Error"),_("You can't duplicate a deposit register."))    
    
    def onchange_date(self, cr, uid, ids, from_date, to_date, check=False, context=None):
        payment_obj = self.pool.get('account.payments')
        res={}
        if context is None: 
            context = {}
        if not (from_date and to_date):
            return res
        if to_date < from_date:
            raise osv.except_osv(_("Error"),_("To data is greater to from date."))
        if check==True:
            payment_ids = payment_obj.search(cr, uid,[('check','=',True),('type','=','receipt'),('deposit_date','>=',from_date),('deposit_date','<=',to_date),('state','=','hold')])
        else:
            payment_ids = payment_obj.search(cr, uid,[('mode_id.credit_card','=',True),('type','=','receipt'),('deposit_date','>=',from_date),('deposit_date','<=',to_date),('state','=','hold'),('bank_id','=',context.get('bank_id',False))])
        res['cheks_ids']=payment_ids
        return {'value':res}
    
    def action_confirmed(self,cr,uid,ids,context={}):
        for dp in self.browse(cr,uid,ids):
            if dp.deposit_checks and not dp.cheks_ids:
                raise osv.except_osv(_("Error"),_("No se puede realizar el depósito porque no tiene cheques."))
            else:
                for tp in dp.cheks_ids:
                    if tp.state <> 'hold':
                        raise osv.except_osv(_("Error"),_("El recap # %s del cliente %s se encuentra en estado %s. Solo se puede depositar los documentos en estado Pendiente")%(tp.name, tp.partner_id.name, tp.state))            
            if not dp.journal_id:
                raise osv.except_osv(_("Error"),_("Please enter a journal type move"))            
        self.write(cr,uid,ids,{"state": "confirmed"})
        return True
    
    def action_cancel(self,cr,uid,ids,context={}):
        for dp in self.browse(cr,uid,ids):
            if dp.state == "deposit":
                raise osv.except_osv(_("Error"),_("You can not cancel registration deposited"))
        self.write(cr,uid,ids,{"state": "cancel"})
        return True
    
    def action_set_draft(self,cr,uid,ids,context={}):
        self.write(cr,uid,ids,{"state": "draft"})
        return True
        
    def action_deposit(self,cr,uid,ids,context={}):
        if context is None:
            context={}
        context['search_shop']=True
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line') 
        for dp in self.browse(cr,uid,ids):
            move_id=None
            date=None
            pay=[]
            rec_list_ids=[]
            if dp.cheks_ids:
                amount=0
                for chk in dp.cheks_ids:
                    credit_card_amount=0
                    if not move_id:
                        if dp.deposit_checks:
                            name = 'DEPOSITO DE CHEQUES /'+dp.number_deposit
                        else:
                            name = 'DEPOSITO DE TARJETAS  /'+ chk.name 
                        date=time.strftime('%Y-%m-%d')
                        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date)])
                        move_id = move_pool.create(cr, uid, {
                            'name': name,
                            'journal_id': dp.journal_id.id,
                            'date': date,
                            'shop_id': dp.shop_id.id,
                            'ref': dp.number_deposit,
                            'period_id': period_ids[0] or False
                        })
                    move_line = {
                        'name': chk.mode_id.name or '/',
                        'debit': 0,
                        'credit': chk.amount,
                        'account_id': chk.mode_id.debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': dp.journal_id.id,
                        'period_id': period_ids[0],
                        'partner_id': chk.partner_id.id,
                        'date': date,                        
                    }
                    amount+=chk.amount
                    credit_card_amount=chk.amount
                    id=move_line_pool.create(cr, uid, move_line)
                    if chk.mode_id.debit_account_id.type in ('receivable','payable'):
                        #print self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',chk.id)])
                        line_statement_id= self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',chk.id)])
                        if line_statement_id:
                            line_statement_id=line_statement_id[0]
                            line_statement=self.pool.get('account.bank.statement.line').browse(cr, uid,line_statement_id,context)
                            rec_ids = [id, line_statement.move_line_id.id]
                            rec_list_ids.append(rec_ids)
                    pay.append(chk.id)
                    if dp.deposit_credit_card:
                        if chk.amount_commission>0:
                            move_line = {
#                                    'name': 'Depósito de Cheques # Papeleta '+chk.number_deposit,
                                    'name': name,
                                    'debit': chk.amount_commission,
                                    'credit': 0,
                                    'account_id': context['wizard'].account_commission_id.id,
                                    'move_id': move_id,
                                    'journal_id': dp.journal_id.id,
                                    'period_id': period_ids[0],
                                    'partner_id': self.pool.get('res.users').browse(cr, uid, dp.user_id.id, context=context).company_id.partner_id.id,
                                    'date': date,
                                }
                            id=move_line_pool.create(cr, uid, move_line)
                            credit_card_amount-=chk.amount_commission
                        move_line = {
#                                 'name': 'Depósito de Cheques # Papeleta '+chk.name,
                                'name': name,
                                'debit': credit_card_amount,
                                'credit': 0,
                                'account_id': dp.account_deposit_id.id,
                                'move_id': move_id,
                                'journal_id': dp.journal_id.id,
                                'period_id': period_ids[0],
                                'partner_id': self.pool.get('res.users').browse(cr, uid, dp.user_id.id, context=context).company_id.id,
                                'date': date,
                            }
                        id=move_line_pool.create(cr, uid, move_line)
                        amount=0
                if amount>0:
                    move_line = {
                                'name': 'Depósito de Cheques # Papeleta'+dp.receipt,
                                'debit': amount,
                                'credit': 0,
                                'account_id': dp.account_deposit_id.id,
                                'move_id': move_id,
                                'journal_id': dp.journal_id.id,
                                'period_id': period_ids[0],
                                'partner_id': self.pool.get('res.users').browse(cr, uid, dp.user_id.id, context=context).company_id.id,
                                'date': date,
                            }
                    id=move_line_pool.create(cr, uid, move_line)
            if pay:
                self.pool.get('account.payments').write(cr, uid, pay, {'state':'paid','payment_date':date})
            if move_id:
                move_pool.post(cr, uid, [move_id], context)
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, rec_ids)
            name =  self.pool.get('ir.sequence').next_by_code(cr, uid, 'deposit.register')
            process_date = time.strftime('%Y-%m-%d')
        self.write(cr,uid,ids,{"state": "deposit",'name':name,'move_id':move_id,'process_date':process_date})
        return True

    def unlink(self, cr, uid, ids, context=None):
        stat = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for t in stat:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('¡Acción Inválida !'), _('Para inactivar un registro de depósito, debe primero anularlo'))
        self.write(cr,uid,unlink_ids,{'active':False})
        return True

deposit_register()
