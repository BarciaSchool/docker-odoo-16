# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from tools.translate import _
from osv import fields, osv
import time

class refund(osv.osv_memory):
    
    _name = 'refund'
    _columns = {
                'amount_check': fields.float('amount Check', digits=(16,2)),
                'name':fields.char('Number Check', size=32, required=False, readonly=False),
                'partner_id':fields.many2one('res.partner','Partner'),
                'account_id':fields.many2one('account.account','Account'),
                'amount_debit_note': fields.float('Amount Debit Note', digits=(16,2)),
                'date_rejected': fields.date('Rejected Date'),
                'date_changed': fields.date('Changed Date'),
                'pending':fields.boolean('Pending'),
                'motive':fields.char('Motive', size=60),
                'user_id':fields.many2one('res.users', 'User', required=False),
                'statement_id':fields.many2one('account.bank.statement', 'Cash statement', required=False),
                'mode_id':fields.many2one('payment.mode', 'mode', required=False),
               }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        if 'value' not in context.keys():
            for obj in objs:
                res['amount_check']=obj.amount
                res['name']=obj.name
                res['partner_id']=obj.partner_id.id
                res['user_id']=uid
                account=None
                amount_debit_note=0
                if context.get('type',False) == 'protested':
                    if not obj.bank_account_id.bank.account_protested_id:
                        raise osv.except_osv(_('Error!'), _("Usted debe ingresar una cuenta contable para cheques Protestados en la configuración del Banco"))
                    else:
                        account=obj.bank_account_id.bank.account_protested_id.id
                        amount_debit_note=obj.bank_id.amount_protested
                elif context.get('type',False) == 'rejected':
                    if not obj.bank_account_id.bank.account_rejected_id:
                        raise osv.except_osv(_('Error!'), _("Usted debe ingresar una cuenta contable para cheques Devueltos en la configuración del Banco"))
                    else:
                        account=obj.bank_account_id.bank.account_rejected_id.id
                        amount_debit_note=obj.bank_account_id.bank.amount_rejected
                elif context.get('type',False) == 'exchanged':
                    res['date_changed']=time.strftime('%Y-%m-%d')
                    res['motive']='CANJE DE CHEQUE'
#                    if not obj.bank_id.account_exchanged_id:
#                        raise osv.except_osv(_('Error!'), _("You must enter an account of settings Exchanged Checks in the bank"))
#                    else:
#                        account=obj.bank_id.account_exchanged_id.id
#                        amount_debit_note=0.00
                res['account_id']=account
                res['amount_debit_note']=amount_debit_note
                #res['motive']=obj.motive
        else:
            res = context['value']
        return res
    
    def onchange_user(self, cr, uid, ids, user, context=None):
        res={}
        if user:
            statement=self.pool.get('account.bank.statement').search(cr, uid, [('state','=','open'),('user_id','=',user)])
            res['statement_id']= statement and statement[0] or None
        return {'value':res}
    
    def button_exchanged(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        cheque=self.pool.get(context['active_model']).browse(cr, uid, context['active_id'])
        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.statement_id:
                raise osv.except_osv(_('Error!'), _("You must enter the cash statement for the user selected"))
            journal_id=self.pool.get('account.journal').search(cr, uid, [('type','=','moves')], limit=1)
            if not journal_id:
                raise osv.except_osv(_('Error!'), _("You must a journal of moves"))
            if not wizard.motive:
                motive='CANJE DE CHEQUE'
            else:
                motive=wizard.motive
            move_id = move_pool.create(cr, uid, {
                        'name': 'CANJE DE CHEQUE ' or '',
                        'shop_id': cheque.shop_id.id,
                        'journal_id': journal_id[0],
                        'date': wizard.date_changed,
                        'ref': 'CANJE DE CHEQUE #' + cheque.name or '/',
                        'period_id': wizard.statement_id.period_id.id or False,
                        })
            account_credit=cheque.mode_id.debit_account_id.id
            account_debit=wizard.mode_id.debit_account_id.id
            move_line_pool.create(cr, uid, {
                'name': cheque.mode_id.name or '/',
                'debit': 0,
                'credit': cheque.amount,
                'account_id': account_credit or None,
                'move_id': move_id,
                'journal_id': journal_id[0],
                'period_id': wizard.statement_id.period_id.id or False,
                'partner_id': cheque.partner_id.id or None,
                'date': wizard.date_changed,
                'statement_id': wizard.statement_id.id,
            }, context)
            id_move = move_line_pool.create(cr, uid, {
                    'name': wizard.mode_id.name,
                    'debit': cheque.amount,
                    'credit': 0,
                    'account_id': account_debit or None,
                    'move_id': move_id,
                    'journal_id': journal_id[0],
                    'period_id': wizard.statement_id.period_id.id or False,
                    'partner_id': cheque.partner_id.id or None,
                    'date': wizard.date_changed,
                    'statement_id': wizard.statement_id.id,
                }, context)
            if cheque.type=='receipt':
                tp='customer'
            elif cheque.type=='payment':
                tp='supplier'
            pay=self.pool.get('account.payments').create(cr, uid, {'partner_id':cheque.partner_id.id,
                                                               'amount':cheque.amount,
                                                               'mode_id':wizard.mode_id.id,
                                                               'amount_received':cheque.amount,
                                                               'received_date':wizard.date_changed,
                                                               'state':'paid',
                                                               'type':cheque.type,
                                                               })
            vals= {
                   'ref': motive,
                   'statement_id': wizard.statement_id.id,
                   'journal_id':journal_id[0],
                   'amount':cheque.amount,
                   'date':wizard.date_changed,
                   'partner_id':cheque.partner_id.id,
                   'account_id':wizard.mode_id.debit_account_id.id,
                   'payment_id':pay,
                   'name':'CANJE DE CHEQUE #' + cheque.name or '',
                   'type':tp,
                   'company_id':wizard.statement_id.user_id.company_id.id,
                   'move_line_id':id_move
                 }
            statement_line=self.pool.get('account.bank.statement.line').create(cr, uid, vals, context=context)
            #self.pool.get('account.bank.statement').write(cr, uid, [wizard.statement_id.id], {}, context)
            if move_id:
                move_pool.post(cr, uid, [move_id], context)
            self.pool.get(context['active_model']).write(cr, uid, context['active_id'],{'state':'exchanged','statement_line_id':statement_line,'move_id':move_id})
        return {'type': 'ir.actions.act_window_close'}
    
    def button_refund(self, cr, uid, ids, context=None):
        data_pool = self.pool.get('ir.model.data')
        if context is None:
            context={}
        data={}
        debit_note_ids=[]
        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.account_id:
                raise osv.except_osv(_('Error!'), _("You must enter the account for the refund Check"))
            if not wizard.date_rejected:
                data['date']=time.strftime('%Y-%m-%d')
            else:
                data['date']=wizard.date_rejected
            data['account_id']=wizard.account_id.id
            data['amount_debit_note']=wizard.amount_debit_note or 0.00
            data['type']=context.get('type',False)
            data['pending']=True
            data['motive']=wizard.motive
            context.update({'date':wizard.date_rejected or time.strftime('%Y-%m-%d')})
            debit_note_ids+= self.pool.get('account.payments').button_protested_rejected(cr, uid, context['active_ids'], data, context)
            
        if not debit_note_ids:
            raise osv.except_osv(_('Error'), _('No Debit Note were created'))
        action_model,action_id = data_pool.get_object_reference(cr, uid, 'straconx_debit_notes', "action_debit_customer")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,debit_note_ids))+"])]"
        return action

    def button_changed_date(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.date_changed:
                date=time.strftime('%Y-%m-%d')
            else:
                date=wizard.date_changed
        self.pool.get(context['active_model']).write(cr, uid, context['active_ids'], {'deposit_date':date}, context)
        return {'type': 'ir.actions.act_window_close'}
    
refund()
