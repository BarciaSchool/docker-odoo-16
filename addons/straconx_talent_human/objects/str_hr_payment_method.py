# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
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

from osv import fields,osv
from tools.translate import _
import time

class account_payment_method(osv.osv):
    
    _inherit = 'account.payments'
    _columns={
              'slip_id':fields.many2one('hr.payslip', 'Payslip', required=False),
              'discount_id': fields.many2one("hr.discount","Discount",readonly=True,states={"hold":[("readonly",False)]}),
              'provision_id':fields.many2one('hr.pay.provision', 'Provision', required=False),
#              'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
              }
    
#     def unlink(self, cr, uid, ids, context=None):
#         payment = self.browse(cr, uid, ids,context=context)
#         unlink_ids = []
#         for pay in payment:
#             if pay.slip_id or pay.provision_id:
#                 if pay.state != 'draft':
#                     raise osv.except_osv(_('Invalid action!'), _('You can delete Cheque with only state hold'))
#             unlink_ids.append(pay.id)
#         return super(account_payment_method, self).unlink(cr, uid, unlink_ids, context)
    
    def button_paid(self,cr,uid,ids,context={}):
        if context is None:
            context={}
        context['search_shop']=True
        rule_obj=self.pool.get('hr.salary.rule')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for chk in self.browse(cr,uid,ids):
            move_id=None
            if chk.type=='payment':
                if chk.slip_id:
                    if chk.slip_id.state !='done':
                        raise osv.except_osv(_('Error'), _('You can not pay the check because payroll is not in done status'))
                
                    if not chk.slip_id.journal_id:
                        raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by payslip'))
                    name=self.pool.get('ir.sequence').next_by_id(cr, uid, chk.slip_id.journal_id.sequence_id.id)
                    if not chk.beneficiary:
                        ref=name
                    else:
                        ref='Pago a %s' % (chk.beneficiary)
                    period_id = self.pool.get('account.period').search(cr, uid, [('date_start','<=',chk.slip_id.date_to),('date_stop','>=',chk.slip_id.date_to),])[0] or False
                    rule_id=rule_obj.search(cr, uid, [('calculate_wage','=',True),('account_debit', '!=',None),('account_credit', '!=',None)])
                    if not rule_id:
                        raise osv.except_osv(_('Invalid action!'), _('you must defined a rule default of calculate wage'))
                    account_debit=rule_obj.browse(cr, uid, rule_id[0], context).account_credit.id
#                    company=self.pool.get('res.users').browse(cr, uid, uid, context).company_id
#                    bank_id=bank_obj.search(cr, uid, [('partner_id','=',company.partner_id.id),('default_bank','=',True)])
#                    if not bank_id:
#                        raise osv.except_osv(_('Error'), _('You must have a account bank by default'))
#                    account_credit=bank_obj.browse(cr, uid, bank_id[0], context).account_id.id or False
                    account_credit=chk.bank_account_id.account_id.id or False
                    if not account_credit:
                        raise osv.except_osv(_('Error'), _('You must defined a account of payroll in the account bank selected'))
                    move = {'name': name,
                            'journal_id': chk.slip_id.journal_id.id,
                            'date': time.strftime('%Y-%m-%d'),
                            'ref': ref,
                            'period_id': period_id
                            }
                    move_id = move_pool.create(cr, uid, move,context=context)
                    move_line_pool.create(cr, uid,{
                        'name': ref or '/',
                        'debit': chk.amount,
                        'credit': 0,
                        'account_id': account_debit,
                        'move_id': move_id,
                        'journal_id': chk.slip_id.journal_id.id,
                        'period_id': period_id,
                        'partner_id': False,
                        'date': time.strftime('%Y-%m-%d'),
                        },context=context)
                    move_line_pool.create(cr, uid, {
                        'name': ref or '/',
                        'debit': 0,
                        'credit': chk.amount,
                        'account_id': account_credit,
                        'move_id': move_id,
                        'journal_id': chk.slip_id.journal_id.id,
                        'period_id': period_id,
                        'partner_id': False,
                        'date': time.strftime('%Y-%m-%d'),
                        },context=context)
            self.write(cr, uid, [chk.id], {'move_id':move_id,'payment_date':time.strftime('%Y-%m-%d')})
        return super(account_payment_method, self).button_paid(cr, uid, ids, context)

    def create_checks(self,cr,uid,ids,context={}): 
        for chk in self.browse(cr,uid,ids):        
            if chk.move_id:
                move_id = chk.move_id.id
            else:
                move_id = False 
            if chk.discount_id:
                discount_id = chk.discount_id.id
            else:
                discount_id = False
            if chk.slip_id:
                slip_id = chk.slip_id.id
            else:
                slip_id = False
            if chk.debit_note_id:
                debit_note_id = chk.debit_note_id.id
            else:
                debit_note_id = False
            if chk.provision_id:
                provision_id = chk.provision_id.id
            else:
                provision_id = False
                
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
                   'discount_id':discount_id,
                   'slip_id':slip_id,
                   'debit_note_id': debit_note_id,
                   'provision_id':provision_id,
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
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'straconx_talent_human', "act_view_cheque_employee")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['nodestroy'] = True
            action['domain'] = "[('id','in', ["+','.join(map(str,checks_ids))+"])]"
        return action
        
account_payment_method()