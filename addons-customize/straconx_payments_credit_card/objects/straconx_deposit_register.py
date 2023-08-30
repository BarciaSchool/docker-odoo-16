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

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class deposit_register(osv.osv):
    
    _inherit="deposit.register"
    _columns = {
                'withhold_ids':fields.many2one('account.withhold', 'Retención T/C'),
                'invoice_id': fields.many2one('account.invoice','Factura'),
                'other_commission': fields.float('Otras Comisiones', digits=(16,2)),
                'amount_commission': fields.float('Valor Comisión Bancaria', digits=(16,2),readonly=True,states={"draft":[("readonly",False)]}),
                'recaps': fields.char('Lote', size=20),
                }
    
    def action_deposit(self,cr,uid,ids,context={}):
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        account_tax_pool = self.pool.get('account.tax')
        new_amount = 0.00
        if context:
            invoice_tc = context.get('invoice_tc',False)
            if invoice_tc:
                invoice_tc = self.pool.get('account.invoice').browse(cr,uid,invoice_tc)
                for move_line in invoice_tc.move_id.line_id:
                    if move_line.credit>0.00:
                        move_tc = move_line.id
        for dp in self.browse(cr,uid,ids):
            move_id=None
            date=None
            partner_id = None
            pay=[]
            rec_list_ids=[]
            debit = 0.00
            credit = 0.00
            amount=0                
            with_amount = 0.00
            if not move_id:
                date = dp.date
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date),])
#                 if dp.deposit_credit_card:
#                     raise osv.except_osv(_('Invalid action !'), _('You must define a partner in the bank selected!'))
                if dp.deposit_checks:
                    name = 'DEPOSITO DE CHEQUES -'+ str(dp.number_deposit)
                    ref = dp.number_deposit
                    detail = 'PAGO DE TARJETA DE CRÉDITO'
                    credit_card_amount=0
                    checks_amount=0
                    partner_id = dp.company_id.partner_id.id
                elif dp.deposit_credit_card:
                    name = 'DEPOSITO DE RECAP DE T/C '+dp.receipt
                    ref = dp.receipt
                    detail = 'DEPOSITO DE CHEQUES'
                    checks_amount=0
                    credit_card_amount=0
                    #partner_id = dp.bank_id.partner_id.id
                    
                move_id = move_pool.create(cr, uid, {
                    'name': name,
                    'partner_id': partner_id,
                    'journal_id': dp.journal_id.id,
                    'details': detail,
                    'date': date,
                    'ref': ref,
                    'shop_id': dp.user_id.shop_id.id,
                    'company_id': dp.company_id.id,
                    'period_id': period_ids[0] or False
                })

            if dp.deposit_checks:
                for chk in dp.cheks_ids:
                    line_statement_id= self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',chk.id)])
                    if line_statement_id:
                        line_statement_id=line_statement_id[0]
                        line_statement=self.pool.get('account.bank.statement.line').browse(cr, uid,line_statement_id,context)
                        new_amount = line_statement.amount
                        
                    move_line = {
                        'name': chk.mode_id.name,
                        'reference': chk.name,
                        'debit': 0,
                        'credit': round(new_amount,2),
                        'account_id': chk.mode_id.debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': dp.journal_id.id,
                        'period_id': period_ids[0],
                        'shop_id': dp.user_id.shop_id.id,
                        'partner_id': chk.partner_id.id,
                        'date': date,                        
                    }
                    credit += round(new_amount,2)
                    amount+=new_amount
                    checks_amount=amount
                    id_move=move_line_pool.create(cr, uid, move_line)
                    pay.append(chk.id)
                    if chk.mode_id.debit_account_id.type in ('receivable','payable','liquidity'):
                        line_statement_id= self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',chk.id)])
                        if line_statement_id:
                            line_statement_id=line_statement_id[0]
                            line_statement=self.pool.get('account.bank.statement.line').browse(cr, uid,line_statement_id,context)
                            rec_ids = [id_move, line_statement.move_line_id.id]
                            rec_list_ids.append(rec_ids)
                
                if checks_amount > 0:
                    move_line = {
                            'name': 'DEPOSITO DE CHEQUES',
                            'reference': dp.number_deposit,
                            'debit': round(checks_amount,2),
                            'credit': 0,
                            'account_id': dp.account_deposit_id.id,
                            'move_id': move_id,
                            'journal_id': dp.journal_id.id,
                            'period_id': period_ids[0],
                            'partner_id': self.pool.get('res.users').browse(cr, uid, dp.user_id.id, context=context).company_id.id,
                            'date': date,
                        }
                    id_move=move_line_pool.create(cr, uid, move_line)
                    debit += round(checks_amount,2)                    
                
            if dp.deposit_credit_card and dp.cheks_ids:
                for chk in dp.cheks_ids:
                    line_statement_id= self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',chk.id)])
                    if line_statement_id:
                        line_statement_id=line_statement_id[0]
                        line_statement=self.pool.get('account.bank.statement.line').browse(cr, uid,line_statement_id,context)
                        if dp.withhold_ids:
                            with_amount = round(dp.withhold_ids.total * chk.amount/dp.amount,2)
                        new_amount = chk.amount - with_amount

                    move_line = {
                        'name': chk.mode_id.name,
                        'reference': chk.name,
                        'debit': 0,
                        'credit': round(new_amount,2),
                        'account_id': chk.mode_id.debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': dp.journal_id.id,
                        'period_id': period_ids[0],
                        'shop_id': dp.user_id.shop_id.id,
                        'partner_id': chk.partner_id.id,
                        'date': date,                        
                    }
                    credit += round(new_amount,2)
                    amount+=new_amount
                    credit_card_amount=amount
                    id_move=move_line_pool.create(cr, uid, move_line)
                    pay.append(chk.id)
                    if chk.mode_id.debit_account_id.type in ('receivable','payable'):
                        line_statement_id= self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',chk.id)])
                        if line_statement_id:
                            line_statement_id=line_statement_id[0]
                            line_statement=self.pool.get('account.bank.statement.line').browse(cr, uid,line_statement_id,context)
                            rec_ids = [id_move, line_statement.move_line_id.id]
                            rec_list_ids.append(rec_ids)
                
                if dp.other_commission>0:
                    move_line = {
                            'name': 'COMISION BANCARIA POR PAGO T/C ' + dp.receipt,
                            'reference':dp.receipt,
                            'debit': round(dp.other_commission,2),
                            'credit': 0,
                            'account_id': dp.company_id.property_account_commission_credit_card.id,
                            'move_id': move_id,
                            'journal_id': dp.journal_id.id,
                            'period_id': period_ids[0],
                            'partner_id': dp.company_id.partner_id.id,
                            'date': date,
                        }
                    debit += round(dp.other_commission,2)
                    credit_card_amount = credit_card_amount - dp.other_commission 
                    id_move=move_line_pool.create(cr, uid, move_line)
           
                if dp.invoice_id:
                    for move in dp.invoice_id.move_id.line_id:
                        if move.credit > 0:
                            move_line = {
                                    'name': 'FACTURA DE COMISIÓN DE T/C ',
                                    'reference':move.ref,
                                    'debit': round(move.credit,2),
                                    'credit': 0,
                                    'account_id': move.account_id.id,
                                    'move_id': move_id,
                                    'journal_id': dp.journal_id.id,
                                    'period_id': period_ids[0],
                                    'partner_id': dp.company_id.partner_id.id,
                                    'date': date,
                                }
                            debit += round(move.credit,2)
                            credit_card_amount = credit_card_amount - move.credit
                            id_move=move_line_pool.create(cr, uid, move_line)                            
                            if move_tc:
                                rec_ids = [move_tc, id_move]
                                rec_list_ids.append(rec_ids)
                            else:
                                raise osv.except_osv(_('¡Acción Inválida!'), _('No se encuentra el movimiento contable correspondiente a la factura de comisiones de este voucher de T/C'))
                                                        
                if credit_card_amount > 0:
                    move_line = {
                            'name': 'DEPOSITO DE VOUCHER POR COBRO T/C',
                            'reference': dp.receipt,
                            'debit': round(credit_card_amount,2),
                            'credit': 0,
                            'account_id': dp.account_deposit_id.id,
                            'move_id': move_id,
                            'journal_id': dp.journal_id.id,
                            'period_id': period_ids[0],
                            'partner_id': self.pool.get('res.users').browse(cr, uid, dp.user_id.id, context=context).company_id.id,
                            'date': date,
                        }
                    id_move=move_line_pool.create(cr, uid, move_line)
                    debit += round(credit_card_amount,2)                    
            elif dp.deposit_credit_card and not dp.cheks_ids:
                credit_card_amount = context.get('amount_deposit',0.00)
                if credit_card_amount > 0:
                    move_line = {
                            'name': 'DEPOSITO DE VOUCHER POR COBRO T/C',
                            'reference': dp.number_deposit,
                            'debit': round(credit_card_amount,2),
                            'credit': 0.00,
                            'account_id': dp.account_deposit_id.id,
                            'move_id': move_id,
                            'journal_id': dp.journal_id.id,
                            'period_id': period_ids[0],
                            'partner_id': self.pool.get('res.users').browse(cr, uid, dp.user_id.id, context=context).company_id.id,
                            'date': date,
                        }
                    move_line_pool.create(cr, uid, move_line)
                    move_line = {
                            'name': 'PAGO DE VOUCHER DE T/C',
                            'reference': dp.receipt,
                            'debit': 0.00,
                            'credit': round(credit_card_amount,2),
                            'account_id': dp.company_id.property_account_active_credit_card.id,
                            'move_id': move_id,
                            'journal_id': dp.journal_id.id,
                            'period_id': period_ids[0],
                            'partner_id': dp.bank_id.partner_id.id,
                            'date': date,
                        }
                    move_line_pool.create(cr, uid, move_line)
            if pay:
                self.pool.get('account.payments').write(cr, uid, pay, {'state':'paid','payment_date':date})
            if move_id:
                move_pool.post(cr, uid, [move_id], context)
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, rec_ids)            
            if move_pool.browse(cr,uid,move_id).line_id:
                for line in move_pool.browse(cr,uid,move_id).line_id: 
                        if line.reconcile_partial_id:
                            move_round_id = context.get('move_round_id',False)
                            if move_round_id:
                                rec_new_ids = [line.id, move_round_id]
                                try:
                                    move_line_pool.reconcile_partial(cr, uid, rec_new_ids)
                                except:
                                    continue                        
            name =  self.pool.get('ir.sequence').next_by_code(cr, uid, 'deposit.register')
        self.write(cr,uid,ids,{"state": "deposit",'name':name,'move_id':move_id})
        return True
    
    def action_cancel(self,cr,uid,ids,context={}):        
        account_move_obj = self.pool.get('account.move')
        for dp in self.browse(cr,uid,ids):
            if dp.invoice_id:
                self.pool.get('account.invoice').cancel_only_invoice(cr, uid, [dp.invoice_id.id], context)
            if dp.move_id:
                for moves_lines in dp.move_id.line_id:
                    if moves_lines.reconcile_id:
                        cr.execute("""update account_move_line set write_date=now(), reconcile_id=Null where reconcile_id = %s""",(moves_lines.reconcile_id.id,))
                        cr.execute("""delete from account_move_reconcile where id = %s""",(moves_lines.reconcile_id.id,))
                account_move_obj.button_cancel(cr, uid, [dp.move_id.id], context=context)
                account_move_obj.unlink(cr, uid, [dp.move_id.id], context=context)
            if dp.withhold_ids:
                self.pool.get('account.withhold').action_annulled(cr, uid, [dp.withhold_ids.id], context)
            if dp.cheks_ids:
                for tc in dp.cheks_ids:
                    self.pool.get('account.payments').write(cr,uid,[tc.id],{'state':'hold'})
                    
        self.write(cr,uid,[dp.id],{'invoice_id':False,'withhold_ids':False, 'move_id':False, 'state':'draft','date':None, 'process_date':None, 'amount_commission':0.00, 'other_commission':0.00, 'date': None})             
        return True

    def onchange_date_tc(self, cr, uid, ids, from_date, to_date, check=False, cheks_ids=False , context=None):
        payment_obj = self.pool.get('account.payments')
        res={}
        if not cheks_ids:
            payment_ids = []
        else:
            payment_ids = []
            for payd in cheks_ids[0][2]: 
                payment_ids.append(payd)
        if context is None: 
            context = {}
        else:
            bank_id = context.get('bank_id',False)
            recaps = context.get('recaps',False)
            if recaps:
                recaps = "%"+recaps
        if not (from_date and to_date):
            return res
        if to_date < from_date:
            raise osv.except_osv(_("Error"),_("To data is greater to from date."))
        if check==True:
            payment_ids = payment_obj.search(cr, uid,[('check','=',True),('type','=','receipt'),('deposit_date','>=',from_date),('deposit_date','<=',to_date),('state','=','hold')])
        else:
            payment_tc = []
            if bank_id and recaps: 
                payment_tc = payment_obj.search(cr, uid,[('mode_id.credit_card','=',True),('type','=','receipt'),('deposit_date','>=',from_date),('deposit_date','<=',to_date),('state','=','hold'),('bank_id','=',bank_id),('name','=',recaps)],order='name,bank_id')
            elif bank_id and not recaps:
                payment_tc = payment_obj.search(cr, uid,[('mode_id.credit_card','=',True),('type','=','receipt'),('deposit_date','>=',from_date),('deposit_date','<=',to_date),('state','=','hold'),('bank_id','=',bank_id)], order='bank_id')
            elif not bank_id and recaps:
                payment_tc = payment_obj.search(cr, uid,[('mode_id.credit_card','=',True),('type','=','receipt'),('deposit_date','>=',from_date),('deposit_date','<=',to_date),('state','=','hold'),('name','like',recaps)], order='name')                
        if payment_tc:
            for new_paid in payment_tc: 
                payment_ids.append(new_paid)
        res['cheks_ids']=list(set(payment_ids))
        return {'value':res}

deposit_register()
