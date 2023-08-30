# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
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

from osv import fields, osv
import time
import decimal_precision as dp
from tools.translate import _

class cash_consolidation(osv.osv):
    
    def _get_journal(self, cr, uid, context=None):
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','=','cash_consolidation')])
        return journal_ids and journal_ids[0] or None
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id)])
        return period_ids and period_ids[0] or None
    
    def _amount_total(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for cash in self.browse(cr, uid, ids, context=context):
            result[cash.id] = {'total_expenses':0.0,
                               'total_incomes':0.0,
                               }
            for expenses in cash.expenses_ids:
                result[cash.id]['total_expenses'] += expenses.amount or 0.00
            for incomes in cash.incomes_ids:
                result[cash.id]['total_incomes'] += incomes.amount or 0.00
        return result
    
    _name = "cash.consolidation"
    _columns = {
        'name':fields.char('Name Cash', size=32, required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'shop_id':fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft':[('readonly',False)]}),
        'printer_id':fields.many2one('printer.point', 'Printer', readonly=True, states={'draft':[('readonly',False)]}, domain="[('shop_id', '=', shop_id)]"),
        'user_id':fields.many2one('res.users', 'User', readonly=True, states={'draft':[('readonly',False)]}),
        'date': fields.date('Date',readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Fiscal Period', domain=[('state','<>','done')], readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'partner_id':fields.many2one('res.partner', 'partner', readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'account', readonly=True, states={'draft':[('readonly',False)]}),
        'journal_id': fields.many2one('account.journal', 'journal', readonly=True, states={'draft':[('readonly',False)]}),
        'expenses_move_id': fields.many2one('account.move', 'Accounting Entry Expenses', readonly=True,),
#        'incomes_move_id': fields.many2one('account.move', 'Accounting Entry Incomes', readonly=True,),
        'invoice_move_id': fields.many2one('account.move', 'Invoice Accounting Entry', readonly=True,),
        'amount_initial': fields.float('Amount Initital', digits_compute=dp.get_precision('Account'),readonly=True, states={'draft':[('readonly',False)]}),
#        'incomes_ids':fields.one2many('cash.consolidation.line.in', 'cash_id', 'Incomes', required=False),
        'expenses_ids':fields.one2many('cash.consolidation.line.in', 'cash_id', 'Moves', required=False),
        'invoices_ids':fields.one2many('invoice.consolidation.line.in', 'cash_id', 'Invoice', required=False),
        'comprob':fields.float('Proof', digits_compute=dp.get_precision('Account')),
        'estatus': fields.selection([('ok','Cuadrado'),('nook','Descuadrado')],'type', select=True),
#        'expenses_ids':fields.one2many('cash.consolidation.line.out', 'cash_id', 'Expenses', required=False),
        'state':fields.selection([
                                  ('draft','Draft'), 
                                  ('open','Open'),
                                  ('confirm','Confirm'),
                                  ('cancel','Cancel')],'State', select=True, readonly=True),
        }
    
    _defaults={
               'user_id': lambda obj, cr, uid, context: uid,
               'journal_id':_get_journal,
               'state': lambda *a: 'draft',
               'date': time.strftime('%Y-%m-%d'),
               'period_id': _get_period,
               'estatus': lambda *a: 'nook',
               'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'cash.consolidation'),
               'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'cash.consolidation', context=c),
               }
    
    def on_change_user(self, cr, uid, ids, user_id, context=None):
        res={'shop_id':None, 'printer_id':None}
        warning={}
        domain={}
        if user_id:
            shop=None
            user=self.pool.get('res.users').browse(cr, uid, user_id, context)
            if not user.printer_point_ids:
                warning = {'title': _('Error!'),'message': _(("The user %s must have to least a printer point.")%user.name)}
            for printer in user.printer_point_ids:
                shop=printer.shop_id.id
                break
            result=self.on_change_shop(cr, uid, ids, shop, user_id, context)
            res.update(result['value'])
            domain.update(result['domain'])
            res['shop_id']=shop
        return {'value':res, 'warning':warning, 'domain':domain}
    
    def on_change_shop(self, cr , uid, ids, shop_id, user_id, context=None):
        res={}
        if not user_id:
            return {'value':{'shop_id':None, 'printer_id':None}}
        user=self.pool.get('res.users').browse(cr, uid, user_id, context)
        shop_list=[]
        cash_list=[]
        box_id=[]
        for printer in user.printer_point_ids:
            cash_list.append(printer.id)
            shop_list.append(printer.shop_id.id)
        if shop_id:
            box_id=self.pool.get('printer.point').search(cr, uid, [('id', 'in', cash_list),('shop_id', '=', shop_id)])
            res['printer_id']=box_id and box_id[0] or None
        return {'value':res, 'domain':{'shop_id':[('id','in', shop_list)],'printer_id':[('id','in', box_id)]}}
    
    def on_change_company(self, cr, uid, ids, company_id, context=None):
        res={}
        if company_id:
            company=self.pool.get('res.company').browse(cr, uid, company_id)
            res['partner_id']= company.partner_id.id
            res['account_id']=company.partner_id.property_account_receivable.id
        return {'value':res}
    
    def on_change_date(self, cr, uid, ids, date, context={}):
        res={'period_id':None}
        if date:
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date), ('company_id', '=', user.company_id.id)])
            res['period_id']= period_ids and period_ids[0] or None
        return {'value':res}
    
    def action_open(self, cr, uid, ids, context=None):        
        for cash in self.browse(cr, uid, ids, context):
            expenses_lines=map(lambda x: self.pool.get('cash.consolidation.line.in').create(cr, uid, {'move_type_id':x}), self.pool.get('move.type').search(cr, uid, [('type','in',('in','out')),('shop_ids','in',cash.shop_id.id or [])], order="sequence asc"))
            invoice_lines=map(lambda x: self.pool.get('invoice.consolidation.line.in').create(cr, uid, {'invoice_type_id':x}), self.pool.get('invoice.type').search(cr, uid, [('type','in',('iva','noiva'))]))
            cash.write({'expenses_ids':[[6, 0, expenses_lines]],'invoices_ids':[[6, 0, invoice_lines]],'state':'open'})
        return True
    
    def comprobate_move_lines(self, cr, uid, cash, move, context=None):
        move_line_pool=self.pool.get('account.move.line')
        move_line_ids=move_line_pool.search(cr, uid, [('move_id','=',move.id),('account_id','=',cash.account_id.id)])
        for line in move_line_pool.browse(cr, uid, move_line_ids, context):
            move_lines=[]
            if line.reconcile_id:
                move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
            if line.reconcile_partial_id:
                move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
            if len(move_lines) > 2:
                raise osv.except_osv(_('Error !'), _('You can not Re-Open this cash that has registered reconciliations, please check!'))
            else:
                self.pool.get('account.move.reconcile').unlink(cr, uid, line.reconcile_id and line.reconcile_id.id or line.reconcile_partial_id and line.reconcile_partial_id.id or None)
        return True
        
    
    def action_re_open(self, cr, uid, ids, context={}):
        move_pool = self.pool.get('account.move')
        move_cancel=[]
        for cash in self.browse(cr, uid, ids, context):
            if cash.expenses_move_id:
                self.comprobate_move_lines(cr, uid, cash, cash.expenses_move_id, context)
                move_cancel.append(cash.expenses_move_id.id)
            if cash.invoice_move_id:
                self.comprobate_move_lines(cr, uid, cash, cash.invoice_move_id, context)
                move_cancel.append(cash.invoice_move_id.id)
        move_pool.button_cancel(cr, uid, move_cancel)
        move_pool.unlink(cr, uid, move_cancel)
        self.write(cr, uid, ids, {'state':'open','comprob':0.00})
        return True
    
    def create_move_line(self, cr, uid, cash, name, account, amount, move_id, context={}):
        line={'name': 'CONTABILIZACIÓN DE ' +name,
              'date': cash.date,
              'partner_id': cash.partner_id.id,
              'account_id': account,
              'journal_id': cash.journal_id.id,
              'reference': cash.shop_id.name +' '+ cash.printer_id.name +' '+ cash.date,
              'period_id': cash.period_id.id,
              'move_id': move_id,
              }
        if context.get('debit',False):
            line['debit']=amount
        if context.get('credit',False):
            line['credit']=amount
        return self.pool.get('account.move.line').create(cr, uid, line, context)
    
    def create_move(self, cr, uid, cash, description=''):
        name=self.pool.get('ir.sequence').next_by_id(cr, uid, cash.journal_id.sequence_id.id)
        res_move={'name': name,
                  'ref': cash.name + ' '+ cash.shop_id.name +' '+ cash.printer_id.name +' '+ cash.date,
                  'journal_id': cash.journal_id.id,
                  'date': cash.date,
                  'period_id': cash.period_id.id,
                  'shop_id': cash.shop_id.id or None,
                  'partner_id': cash.partner_id.id, 
                  'details': 'CIERRE DE CAJA '+ cash.name
                }
        return self.pool.get('account.move').create(cr, uid, res_move, context={})
    
    def register_expenses(self, cr, uid, cash, context={}):
        move_id=self.create_move(cr, uid, cash, '-expenses')
        amount=0.00
        move_line_id=None
        for expenses in cash.expenses_ids:
            if not (expenses.move_type_id.register_move and expenses.amount > 0):
                continue
            self.create_move_line(cr, uid, cash, expenses.move_type_id.name, expenses.move_type_id.account_id.id, expenses.amount, move_id, {'debit':True})
            amount+=expenses.amount
        if amount == cash.comprob:
            if amount > 0:
                move_line_id=self.create_move_line(cr, uid, cash, cash.name, cash.account_id.id, amount, move_id, {'credit':True})
                self.pool.get('account.move').post(cr, uid, [move_id])
                cash.write({'expenses_move_id':move_id})
            else:
                self.pool.get('account.move').unlink(cr, uid, [move_id])
        else:
            raise osv.except_osv(_('Invalid Amount Cash !'), _('Consolidated Cash is unbalanced!'))                   
        return move_line_id
    
    def register_incomes(self, cr, uid, cash, context={}):
        move_id=self.create_move(cr, uid, cash, '-incomes')
        amount=0.00
        move_line_id=None
        for incomes in cash.invoices_ids:
            if not incomes.invoice_type_id.register_move:
                continue
            if incomes.amount > 0:
                self.create_move_line(cr, uid, cash, incomes.invoice_type_id.name, incomes.invoice_type_id.account_id.id, incomes.amount_untaxed, move_id, {'credit':True})
                self.create_move_line(cr, uid, cash, incomes.invoice_type_id.account_id_iva.name, incomes.account_id_iva.account_collected_id.id, incomes.amount_taxes, move_id, {'credit':True})
            amount+=incomes.amount
        if amount > 0:
            move_line_id= self.create_move_line(cr, uid, cash, cash.name, cash.account_id.id, amount, move_id, {'debit':True})
            self.pool.get('account.move').post(cr, uid, [move_id])
            cash.write({'invoice_move_id':move_id})
        else:
            self.pool.get('account.move').unlink(cr, uid, [move_id])
        return move_line_id
    
    def action_confirm(self, cr, uid, ids, context=None):
        rec_list_ids=[]
        for cash in self.browse(cr, uid, ids, context):
            line_incomes=self.register_incomes(cr, uid, cash, context)
            line_expenses=self.register_expenses(cr, uid, cash, context)
#            rec_list_ids.append([line_expenses])
            rec_list_ids.append([line_expenses,line_incomes])            
        for rec_ids in rec_list_ids:
            if len(rec_ids) >= 2:
                self.pool.get('account.move.line').reconcile_partial(cr, uid, rec_ids, context=context)
        self.write(cr, uid, ids, {'state':'confirm','estatus':'ok'})
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
    def set_to_draft(self, cr, uid, ids, context=None):
        out_list= in_list=[]
        for cash in self.browse(cr, uid, ids, context):
            for output in cash.expenses_ids:
                out_list.append(output.id)
            for income in cash.invoices_ids:
                in_list.append(income.id)
        self.pool.get('cash.consolidation.line.in').unlink(cr, uid, out_list, context)
        self.pool.get('invoice.consolidation.line.in').unlink(cr, uid, in_list, context)
        if context is None:
            context.update({'shop_id':cash.shop_id.id})
        self.write(cr, uid, ids, {'state':'draft'})
        return True
    
    def unlink(self, cr , uid, ids, context=None):
        for cash in self.browse(cr, uid, ids, context=context):
            if cash.state != 'draft':
                raise osv.except_osv(_('Invalid action !'), _('Only Can delete Cash(s) consolidation(s) in state draft !'))
        return super(cash_consolidation, self).unlink(cr, uid, ids, context=context)
    
    def create(self, cr, uid, vals, context=None):
        sql = [
            ('user_id', '=', vals.get('user_id', uid)),
            ('state', '=', 'open'),
            ('printer_id', '=', vals.get('printer_id', None)),
            ('shop_id','=',vals.get('shop_id', None))
        ]
        if context is None:
            context.update({'shop_id':vals.get('shop_id')})    
        open_jrnl = self.search(cr, uid, sql)
        if open_jrnl:
            raise osv.except_osv(_('Error'), _('You can not have two open cash consolidation for the same point printer'))
        return super(osv.osv, self).create(cr, uid, vals, context=context)
           
cash_consolidation()


class cash_consolidation_line_in(osv.osv):
    
    _name = "cash.consolidation.line.in"
    _columns = {
        'cash_id':fields.many2one('cash.consolidation', 'Cash', ondelete='cascade'),
        'move_type_id':fields.many2one('move.type', 'Move Type', required=False, ondelete='restrict'),
        'amount': fields.float('amount', digits=(16,2)),
        'sequence': fields.related('move_type_id', 'sequence', type='integer', string='Seq.'),
        'reference':fields.char('Reference', size=128, required=False),
        'register_move': fields.related('move_type_id', 'register_move', type='boolean', string='Register in Move Account?',),
        'required_reference': fields.related('move_type_id', 'required_reference', type='boolean', string='Required Reference?',),
        'quantity': fields.integer('quantity')
        }
    
    def onchange_move_type(self, cr, uid, ids, move_type, context=None):
        res={}
        if move_type:
            move=self.pool.get('move.type').browse(cr, uid, move_type)
            res['sequence']=move.sequence
            res['register_move']=move.register_move
            res['required_reference']=move.required_reference
            res['amount']=0.00
        return {'value':res}
    _rec_name="move_type_id"
cash_consolidation_line_in()

class invoice_consolidation_line_in(osv.osv):
    
    _name = "invoice.consolidation.line.in"
    _columns = {
        'cash_id':fields.many2one('cash.consolidation', 'Cash', ondelete='cascade'),
        'invoice_type_id':fields.many2one('invoice.type', 'Invoice Type', required=False, ondelete='restrict'),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'amount_untaxed':fields.float('Amount Untaxed', digits_compute=dp.get_precision('Account')),
        'amount_taxes':fields.float('Amount Taxes', digits_compute=dp.get_precision('Account')),
        'sequence': fields.related('invoice_type_id', 'sequence', type='integer', string='Seq.'),
        'register_move': fields.related('invoice_type_id', 'register_move', type='boolean', string='Register in Move Account?',),
        'account_id_iva': fields.related('invoice_type_id', 'account_id_iva', type='many2one', relation='account.tax', string='IVA Account',),
        'quantity': fields.integer('quantity')
        }
    
    def onchange_invoice_type(self, cr, uid, ids, invoice_type, context=None):
        res={}
        if invoice_type:
            move=self.pool.get('invoice.type').browse(cr, uid, invoice_type)
            res['sequence']=move.sequence
            res['register_move']=move.register_move            
            res['amount']=0.00
        return {'value':res}
    _rec_name="invoice_type_id"
    
    def onchange_amount(self, cr, uid, ids, amount, account_id_iva=False, context=None):
        res={}
        if amount:
            if account_id_iva:
                taxes = self.pool.get('account.tax').browse(cr,uid,account_id_iva,context).amount
                res['amount_untaxed']=amount / (1 + taxes)
                res['amount_taxes']=amount / (1 + taxes) * taxes            
            else:
                res['amount_untaxed']=amount
                res['amount_taxes']=0.00
        else:
            res['amount']=0.00
        return {'value':res}
    
invoice_consolidation_line_in()