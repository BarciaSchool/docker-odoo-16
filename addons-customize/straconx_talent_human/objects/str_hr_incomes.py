# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from osv import fields,osv
from tools.translate import _
import decimal_precision as dp
import tools
import netsvc

class hr_incomes(osv.osv):

    _name = 'hr.incomes'
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal=self.pool.get('account.journal').search(cr, uid, [('type','=','discount_employee')])
        return journal and journal[0] or None
    
    def _amount_to_paid(self, cr, uid, ids, name, args, context=None):
        result = {}
        for incomes in self.browse(cr, uid, ids, context=context):
            result[incomes.id]={}
            amount_to_paid=0
            if incomes.state=='cancel':
                amount_to_paid = 0.00
            if incomes.name.generate_lines_employee:
                for line in incomes.lines_ids:
                    amount_to_paid += line.amount
            else:
                amount_to_paid= incomes.amount
            result[incomes.id]={'amount_to_paid':amount_to_paid}
        return result
    
    def _compute_values_incomes(self, cr, uid, ids, name, args, context):
        result = {}
        for incomes in self.browse(cr, uid, ids, context=context):
            result[incomes.id] = {'amount_paid':0.0
                                   }
            for lines in incomes.lines_ids:
                if lines.state == 'paid':
                    result[incomes.id]['amount_paid'] += lines.amount
        return result
        
    def _paid(self, cr, uid, ids, name, args, context=None):
        result = {}
        for incomes in self.browse(cr, uid, ids, context=context):                
            if round(incomes.amount_paid,2) >= round(incomes.amount_to_paid,2):
                result[incomes.id] = True
                                      
            else:
                result[incomes.id] =False
                                    
        return result
    
    _columns = {    
                'name':fields.many2one('hr.transaction.type', 'Name', required=False,readonly=True,states={'draft': [('readonly', False)]},domain=[('type_income','in',('other','extra_hours'))]),
                'type':fields.selection([('other','Other'),('extra_hours','Extra Hours')],'type'),
                'generate_lines_employee':fields.related('name', 'generate_lines_employee', type='boolean', string='Generate Lines of all employee', readonly=True),
                'ref':fields.char('Ref',size=256,required=False,readonly=True,states={'draft': [('readonly', False)]}),
                'period_id': fields.many2one('account.period', 'Account Period',states={'draft': [('readonly', False)]}, readonly=True, domain=[('state','<>','done')], help="Keep empty to use the period of the validation date."),
                'journal_id': fields.many2one('account.journal', 'Expense Journal',states={'draft': [('readonly', False)]}, readonly=True, required=True),
                'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
                'user_id': fields.many2one('res.users', 'User', readonly=True, states={'draft': [('readonly', False)]}, select=True),
                'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}),
                'partner_id': fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]}),
                'collection_form':fields.selection([('middle_month','Primera Quincena'),('end_month','Fin de mes'),('middle_end_month','Quincena y Fin de mes'),], 'Collection Form', select=True, readonly=True,states={'draft': [('readonly', False)]}),
                'date': fields.date('Date register',readonly=True,states={'draft': [('readonly', False)]}),
                'date_from': fields.date('Date From',readonly=True,states={'draft': [('readonly', False)]}),
                'date_to': fields.date('Date to',readonly=True,states={'draft': [('readonly', False)]}),
                'amount': fields.float('Amount', digits_compute=dp.get_precision('Payroll'), readonly=True,states={'draft': [('readonly', False)]}),
                'lines_ids':fields.one2many('hr.incomes.lines', 'input_id', 'Pays', required=False),
                'amount_to_paid': fields.function(_amount_to_paid, type='float', method=True, string='Amount to Paid', store=True, multi="amount_to_paid"),
                'amount_paid': fields.function(_compute_values_incomes, type='float', method=True, string='Amount Paid',multi="values_discount"),
                'paid': fields.function(_paid, type='boolean', method=True, string='Paid?',),
                'state': fields.selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True),                
                }
    
    _defaults={
        "state": "draft",
        'user_id': lambda obj, cr, uid, context: uid,
        'date_from': time.strftime('%Y-%m-%d'),
        'date': time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.input', context=c),
        'type': lambda obj, cr, uid, context: context.get('type','other'),
        "journal_id": _get_journal,
        }

    _sql_constraints = [('income_month_uniq', 'unique(name, company_id,date_from,ref)', 'There can be one income type by type, ref and date in a same month!')]
    
    def test_state(self, cr, uid, ids, context=None):
        for incomes in self.browse(cr, uid, ids, context):
            if incomes.paid:
                incomes.write({'state':'paid'})
            else:
                incomes.write({'state':'approve'})
        return True
    
    def onchange_date(self, cr, uid, ids, date=False, company_id=None, context=None):
        res={}
        if context is None:
            context = {}
        if not (date and company_id):
            return {'value':{'period_id':False,'journal_id':False}}
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date), ('company_id', '=', company_id)])
        journal_ids= self.pool.get('account.journal').search(cr,uid,[('company_id','=',company_id),('type','=','discount_employee')])
        if not journal_ids:
            raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
        else:
            journal_id= journal_ids[0]           
        res['period_id']=period_ids and period_ids[0] or None
        res['journal_id']=journal_id
        return {'value':res}
    
    def onchange_trans_id(self, cr, uid, ids, type_id=False, context=None):
        res={}
        transaction_obj = self.pool.get('hr.transaction.type')
        if context is None:
            context = {}
        if transaction_obj:
            ttype = transaction_obj.browse(cr,uid,type_id)
            if ttype.collection_form:
                res['collection_form']=ttype.collection_form
            else:
                res['collection_form']=None
        return {'value':res}

    def get_employee_ids(self, cr, uid, ids, context=None):
        hce = self.pool.get('hr.contract.income')
        lines = self.pool.get('hr.incomes.lines')
        types = self.pool.get('hr.transaction.type')
        contract = self.pool.get('hr.contract')
        d_name = self.browse(cr,uid,ids[0])  
        if d_name.name:
            htt = d_name.name.id
            company_id = d_name.company_id.id                
            datas = hce.search(cr,uid,[('name','=',htt),('company_id','=',company_id)])
            if datas:
                for d in datas:
                    contract_ids  = hce.browse(cr,uid,d).contract_id.id or None
                    if contract_ids:
                        hce_price = hce.browse(cr,uid,d).price or 0.00
                        hce_quantity = 0.0
                        
                        hce_amount = round(hce_price*hce_quantity,2)                    
                        hce_ref = hce.browse(cr,uid,d).ref or None
                        empl = self.pool.get('hr.contract').search(cr,uid,[('id','=',contract_ids),('company_id','=',company_id),('contract_active','=',True)])
                        if empl:
                            for cont_ids in contract.browse(cr, uid, empl):
                                emp = cont_ids.employee_id.id
                            empl_ids = self.pool.get('hr.employee').search(cr,uid,[('id','=',emp),('company_id','=',company_id),('unemployee','=',False)])
                            id_s = ids[0]
                            if empl_ids: 
                                empl_id = self.pool.get('hr.contract').browse(cr,uid,empl[0]).employee_id.id 
                                #pay_ids = self.pool.get('hr.payslip').search(cr,uid,[('employee_id','=',empl_id),('company_id','=',company_id),('period_id','=',d_name.period_id)])                        
                                if empl_id:
                                    old_lines = lines.search(cr,uid,[('employee_id','=',empl_id),('date','=',d_name.date_from),('state','=','draft'),('income_type_id','=',d_name.name.id)])
                                    if not old_lines:
                                        if types.browse(cr,uid,htt).type_income=='extra_hours':
                                            quantity=0.00
                                        else:
                                            quantity=1.00
                                        lines.create(cr,uid,{
                                                'employee_id':empl_id, 
                                                'name':types.browse(cr,uid,htt).name,
                                                'date':d_name.date_from,
                                                'ref':hce_ref,
                                                'code':d_name.name.code,
                                                'name': d_name.name.name,
                                                'income_type_id': d_name.name.id,
                                                'quantity':quantity,                                        
                                                'price': hce_price,
                                                #'payslip':pay_ids[0],
                                                'amount':hce_amount,
                                                'input_id':id_s,
                                                'contract_id': contract_ids,
                                                'state':'draft'})
       
        return True

    def button_approve(self, cr, uid, ids, context=None):
        lines_ids = []
        for incomes in self.browse(cr, uid, ids, context):
            if not incomes.period_id:
                period=self.pool.get('account.period').search(cr, uid, [('date_start','<=',incomes.date_from),('date_stop','>=',incomes.date_from),])
                period_id = period and period[0] or False
            else:
                period_id = incomes.period_id.id
            if not incomes.lines_ids:
                raise osv.except_osv(_('Error'), _(('The incomes need a amount > 0 para continue')))
            else:
                for l in incomes.lines_ids:
                    if l.amount > 0:
                        self.pool.get('hr.incomes.lines').write(cr,uid,l.id,{'state':'approve'})
                    else:
                        lines_ids.append(l.id)
                self.write(cr,uid,ids,{'state':'approve', 'period_id':period_id})
                self.pool.get('hr.incomes.lines').unlink(cr, uid, lines_ids)
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        l_obj = self.pool.get('hr.incomes.lines')
        lines = l_obj.search(cr,uid,[('input_id','in',ids)])        
        for l_id in lines:
            l = l_obj.browse(cr,uid,l_id)            
            if l.state in ('draft'):
                unlink_ids.append(l['id'])                
            else:
                raise osv.except_osv(_('Invalid action !'), _('Only Can delete Discount(s) in state draft !'))
        if unlink_ids:
            l_obj.unlink(cr,uid,unlink_ids)    
        return super(hr_incomes,self).unlink(cr, uid, ids, context=context)
        
        
    def button_canceled(self, cr, uid, ids, context=None):
        for income in self.browse(cr, uid, ids, context):
            for lines in income.lines_ids:
                if lines.state=='paid' and lines.payslip_id:
                    raise osv.except_osv(_('Invalid action!'), _('you can not canceled the income because already generate a payment'))
                else:
                    self.pool.get('hr.incomes.lines').write(cr,uid,lines.id,{'state':'cancel'})
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
    def button_set_draft(self, cr, uid, ids, context=None):
        for income in self.browse(cr, uid, ids, context):
            for lines in income.lines_ids:
                if lines.state=='approve' or lines.state=='paid' and lines.payslip_id:
                    raise osv.except_osv(_('Invalid action!'), _('you can not canceled the income because already generate a payment'))
                else:
                    self.pool.get('hr.incomes.lines').write(cr,uid,lines.id,{'state':'draft'})
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def paid_to_approve(self, cr, uid, ids,payslip, context = None):
#         if isinstance (ids, (int, long)): 
#             ids = [ids]
        for income in self.browse(cr, uid, ids, context):
            for lines in income.lines_ids:
                if lines.state == 'paid' and lines.payslip_id.id == payslip:
                    self.pool.get('hr.incomes.lines').write(cr, uid, lines.id,{'state':'approve'})
                    self.pool.get('hr.incomes.lines').write(cr, uid, lines.id,{'payslip_id':None})
        self.write(cr, uid, ids, {'state':'approve'})
        return True            
                
        
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'ref': None,
            'state': 'draft',
            'date': False,
            'date_from':False
        })
        return super(hr_incomes, self).copy(cr, uid, id, default, context=context)

hr_incomes()

class hr_incomes_lines(osv.osv):
    _name = 'hr.incomes.lines'
    
    def _get_totals_input(self, cr, uid, ids, name, args, context=None):
        result = {}
        amount = 0.00
        for prices in self.browse(cr, uid, ids, context=context):
            if prices.income_type_id.type_income == 'extra_hours':
                if prices.quantity > 0:
                    amount = prices.quantity
            else:
                if prices.price > 0 and prices.quantity > 0:
                    amount = prices.price * prices.quantity
    #             else:
    #                 raise osv.except_osv(_('Error'), _('Need a register with positive numbers'))
            result[prices.id]=amount
        return result
    
    
    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'income_type_id':fields.many2one('hr.transaction.type', 'Income Type', required=False),
        'code': fields.related('income_type_id','code', type='char', size=64, readonly=True, string='Code', help="The code that can be used in the salary rules"),
        'employee_id':fields.many2one('hr.employee', 'Employee',readonly=True,states={'draft': [('readonly', False)]}),
        'employee_name': fields.char('Empleado', size=250),
        'date': fields.date('Date'),
        'ref':fields.char('Reference', size=64, readonly=True,states={'draft': [('readonly', False)]}),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Payroll'),readonly=True,states={'draft': [('readonly', False)]}),
        'price': fields.float('Price', digits_compute=dp.get_precision('Payroll'),readonly=True,states={'draft': [('readonly', False)]}),
        'state': fields.selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True),
        'input_id':fields.many2one('hr.incomes','Income', required=False),
        'payslip_id': fields.many2one('hr.payslip', 'Pay Slip', required=False, ondelete='cascade', select=True),
        'payslip_id2': fields.many2one('hr.payslip', 'Nómina', required=False, ondelete='cascade', select=True),
        'amount': fields.function(_get_totals_input, type='float', digits=(16,2), method=True, string='Amount', store=True),
        'contract_id': fields.many2one('hr.contract', 'Contract', required=False, help="The contract for which applied this input"),                                
    }
      
    _order = 'employee_id asc'
        
    _defaults = {
                 'quantity': 0.00,
                 'price': 0.00         
                 
                 }
    def onchange_total(self, cr, uid, ids, quantity=0.00, price=0.00, context=None):
        res={}
        if quantity and price:
            amount = round(quantity*price,2)
            res['amount']=amount or 0.00
        return {'value':res}


    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'payslip_id': False,
            'state': 'draft',
        })
        return super(hr_incomes_lines, self).copy_data(cr, uid, id, default, context=context)
    
hr_incomes_lines()
