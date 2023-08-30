# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

import time

import netsvc
from osv import fields, osv
import tools
from tools.translate import _
import decimal_precision as dp
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta


class hr_contract(osv.osv):
    _inherit = 'hr.contract'

    def _compute_number_of_pays(self, cr, uid, ids, name, args, context=None):
        result = {}
        for contract in self.browse(cr, uid, ids, context=context):
            if contract.schedule_pay=='daily':
                pay=1.0/30.0
            elif contract.schedule_pay == 'weekly':
                pay=1.0/4.0
            elif contract.schedule_pay == 'bi-monthly':
                pay=1.0/2.0
            elif contract.schedule_pay == 'monthly':
                pay=1.0
            else:
                raise osv.except_osv(_('Error'), _('Do not exist contract with dates defined by employee'))
            result[contract.id]=pay
        return result
    
    def _get_historical_wage(self, cr, uid, ids, field_name, field_value, arg, context={}):
        res = {}
        for contract in self.browse(cr, uid, ids):
            if contract.wage != contract.wage_historic:
                res[contract.id] = contract.wage
                self.pool.get('hr.contract.historic').create(cr, uid, {
                                        'contract_id' : contract.id,
                                        'wage': contract.wage,
                                        },context)
        return res
    
    def _get_employee(self, cr, uid, ids, context=None):
        contracts = []
        try:
            for employee in self.pool.get('hr.employee').browse(cr, uid, ids, context=context):
                contracts=self.pool.get('hr.contract').search(cr, uid, [('employee_id','=',employee.id)])
            return contracts
        except AttributeError:
            return contracts
        
    def _verify_contract(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            res[contract.id] = True
            if contract.employee_id.unemployee:
                res[contract.id] = False
            else:
                date_actual=time.strftime('%Y-%m-%d')
                if contract.date_start > date_actual:
                    res[contract.id]=False
                elif contract.date_end and contract.date_end < date_actual:
                    res[contract.id]=False
        return res

    def _get_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        duration = 0.00
        for contract in self.browse(cr, uid, ids, context=context):
            if contract.date_start:
                date_start = contract.date_start 
                if contract.date_end:
                    date_end = contract.date_end
                else:
                    date_end=time.strftime('%Y-%m-%d')
                day_start = datetime.strptime(date_start, "%Y-%m-%d")
                day_end = datetime.strptime(date_end, "%Y-%m-%d")
                days_c = (day_end - day_start).days
                duration = float(days_c) / 360 
            else:
                duration = 0.00  
            res[contract.id]=duration
        return res
    
    def _get_duration_history(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        duration = 0.00
        h_dur = 0.00
        employee = self.browse(cr, uid, ids[0]).employee_id
        for contracts in employee.contract_ids:
            if contracts.contract_active == False:
                h_dur += contracts.duration  
        for contract in self.browse(cr, uid, ids, context=context):
            if contract.date_start:
                date_start = contract.date_start 
                if contract.date_end:
                    date_end = contract.date_end
                else:
                    date_end=time.strftime('%Y-%m-%d')
                day_start = datetime.strptime(date_start, "%Y-%m-%d")
                day_end = datetime.strptime(date_end, "%Y-%m-%d")
                days_c = (day_end - day_start).days
                duration = float(days_c) / 360 
            else:
                duration = 0.00  
            res[contract.id]=duration+h_dur
        return res
        
    def _get_journal(self, cr, uid, context=None):
        journal=self.pool.get('account.journal').search(cr, uid, [('type','=','salary_employee')])
        return journal and journal[0] or None
    
    def _check_wage(self,cr,uid,ids):
        b=True
        for contract in self.browse(cr, uid, ids):
            if contract.wage <=0:
                b=False
        return b
    
    def _check_contract_active(self,cr,uid,ids):
        b=True
        res=self._verify_contract(cr, uid, ids, None, [], {})
        for contract in self.browse(cr, uid, ids):
            contract_ant=self.search(cr, uid, [('employee_id','=',contract.employee_id.id),('contract_active','=',True),('id','not in',tuple(ids))])
            if res[contract.id] and contract_ant:
                b=False
        return b
    
    _columns = {
        'department_id':fields.many2one('hr.department', 'Department', required=True),
        'company_id':fields.many2one('res.company', 'Company', required=True),
        'job_id': fields.many2one('hr.job', 'Job Title', required=True),
        'lines_historic_ids':fields.one2many('hr.contract.historic','contract_id', 'Historical Wage',readonly=True),
        'contract_income_ids':fields.one2many('hr.contract.income','contract_id', 'Income the employee'),
        'contract_expense_ids':fields.one2many('hr.contract.expense','contract_id', 'Expense the employee'),
        'pay_reserve_funds': fields.boolean('Pay Reserve Funds in payslip', help="active this field if the employee collect your reserves funds"),
        'pay_reserve_xiii': fields.boolean('Acumular XIII'),
        'pay_reserve_xiv': fields.boolean('Acumular XIV'),
        'number_of_pays': fields.function(_compute_number_of_pays, type='float', digits=(16,2), method=True, string='Number of Pays', help="This field indicate the number of pays by month"),
        'contract_active': fields.function(_verify_contract, method=True, type='boolean', string='Contract Active?',
                            store={'hr.contract': (lambda self, cr, uid, ids, c={}: ids, ['employee_id','date_start','date_end'], 1),
                                   'hr.employee': (_get_employee, ['unemployee'], 2),}),
        'duration': fields.function(_get_duration, method=True, type='float',digits=(16,2), string='Duration',
                            store={'hr.contract': (lambda self, cr, uid, ids, c={}: ids, ['employee_id','date_start','date_end'], 1),
                                   'hr.employee': (_get_employee, ['unemployee'], 2),}),                
        'history_duration': fields.function(_get_duration_history, method=True, type='float',digits=(16,2), string='Histórico Duración',
                    store={'hr.contract': (lambda self, cr, uid, ids, c={}: ids, ['employee_id','date_start','date_end'], 1),
                           'hr.employee': (_get_employee, ['unemployee'], 2),}, inverse="_write_name"),                
        'wage_historic': fields.function(_get_historical_wage, method=True, string='Wage historic', type='float',digits=(16,2),
                                         store={'hr.contract': (lambda self, cr, uid, ids, c={}: ids, ['wage'], 50),}, help="Latest Recorded Wage Value"),
        'schedule_pay': fields.related('company_id','schedule_pay', type='selection', selection=[('daily', 'Daily'),('monthly', 'Monthly'),('weekly', 'Weekly'),('bi-monthly', 'Bi-monthly')], readonly=True, string='Scheduled Pay'),
        'labor_type': fields.selection([("Directa","Directa"),("Indirecta","Indirecta")],"Labor Type"),
    }

    _constraints = [(_check_wage,'Wage is greater 0',['wage']),
                    (_check_contract_active,'You can not activate a contract already having an active contract, please first finalize active contracts',['contract_active'])]
    
    _defaults = {
        'journal_id':_get_journal,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.contract', context=c),
    }

    
    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        result={}
        if employee_id:
            employee=self.pool.get('hr.employee').browse(cr, uid, employee_id, context)
            result['company_id']=employee.company_id and employee.company_id.id or None
            result.update(self.onchange_company(cr, uid, ids, result['company_id'], context)['value'])
        return {'value':result}
    
    def onchange_company(self, cr, uid, ids, company_id, context=None):
        result={}
        if company_id:
            company=self.pool.get('res.company').browse(cr, uid, company_id, context)
            result['schedule_pay']= company.schedule_pay or None
            journal=self.pool.get('account.journal').search(cr, uid, [('type','=','salary_employee'),('company_id','=',company_id)])
            result['journal_id']=journal and journal[0] or None
        return {'value':result}
    
    def onchange_job_id(self, cr, uid, ids, job_id, emp_id, context=None):
        value={'department_id':None}
        if job_id:
            job=self.pool.get('hr.job').browse(cr, uid, job_id, context)
            value['department_id']=job.department_id and job.department_id.id

            cr.execute("""update hr_employee set write_date=now(), job_id = %s , department_id = %s where id = %s""",(job_id,job.department_id.id, emp_id))

#        value.update(self.onchange_department_id(cr, uid, ids, value['department_id'],context)['value'])
        return {'value':value}
    
    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        disc_obj = self.pool.get('hr.discount.lines')
        inco_obj = self.pool.get('hr.incomes.lines')
        cont_obj = self.pool.get('hr.contract')
        pays_obj = self.pool.get('hr.payslip')       
        if ids:
            for i in ids:
                emp_id = cont_obj.browse(cr,uid,i).employee_id.id
                if emp_id:                
                    pay_ids = pays_obj.search(cr,uid,[('employee_id','=',emp_id)]) 
                    if pay_ids:
                        raise osv.except_osv(_('Invalid action !'), _('Only can delete contract(s) with paylisp in draft state!'))                    
                    del_ids = disc_obj.search(cr,uid,[('employee_id','=',emp_id)])                 
                    if del_ids:
                        for d in del_ids:
                            del_id = disc_obj.browse(cr,uid,d)
                            if del_id.state == 'draft' and del_id.discount_id.state =='draft':
                                unlink_ids.append(del_id.discount_id.id)
                            else:
                                raise osv.except_osv(_('Invalid action !'), _('Only can delete contract(s) with discount in draft state!'))                    
                    if unlink_ids:
                        self.pool.get('hr.discount').unlink(cr,uid,unlink_ids)
                    inco_ids = inco_obj.search(cr,uid,[('contract_id','=',i)])
                    if inco_ids:
                        for d in inco_ids:
                            del_id = inco_obj.browse(cr,uid,d)
                            if del_id.state == 'draft' and del_id.input_id.state =='draft':                            
                                unlink_ids.append(del_id.input_id.id)
                            else:
                                raise osv.except_osv(_('Invalid action !'), _('Only can delete contract(s) with incomes in draft state!'))
                    if unlink_ids:
                        self.pool.get('hr.incomes').unlink(cr,uid,unlink_ids)
        return super(hr_contract,self).unlink(cr, uid, ids, context=context)    

hr_contract()

class hr_contract_historic(osv.osv):
    _name = "hr.contract.historic"
    _description = "Historical contract of employee"

    _columns = {
        'contract_id': fields.many2one('hr.contract',string='Contract', ondelete="cascade"),
        'name': fields.datetime(string='Date',  required=True),
        'wage': fields.float(digits=(16,2),string='wage'),
        'user_id': fields.many2one('res.users', 'User'),        
    }
    _defaults = {'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': lambda obj, cr, uid, context: uid,
    }

hr_contract_historic()

class hr_contract_line(object):
    _name = 'hr.contract.line'
    columns = {
        'name':fields.many2one('hr.transaction.type', 'Name', ondelete='cascade', required=True),
        'ref':fields.char('Reference', size=64, required=False, readonly=False),        
        'contract_id':fields.many2one('hr.contract', 'contract', required=False, ondelete="cascade"),
        'company_id':fields.related('contract_id','company_id',type='many2one',relation='res.company',string='Company',store=True),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Payroll')),
        'price': fields.float('Price', digits_compute=dp.get_precision('Payroll')),
        'amount': fields.float('amount', digits_compute=dp.get_precision('Payroll')),
        'collection_form':fields.selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', select=True),
    }

    _sql_constraints = [('disc_reference_uniq','unique(name,ref)', 'The reference for each discount must be unique')]
    
hr_contract_line()

class hr_contract_income(osv.osv,hr_contract_line):
    _name = 'hr.contract.income'
    _columns=hr_contract_line.columns
    _defaults = {'quantity': lambda *a: 1,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.contract.income', context=c),
             }
hr_contract_income()

class hr_contract_expense(osv.osv,hr_contract_line):
    _name = 'hr.contract.expense'
    _columns=hr_contract_line.columns
    _defaults = {'quantity': lambda *a: 1,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.contract.expense', context=c),
             }    
hr_contract_expense()
