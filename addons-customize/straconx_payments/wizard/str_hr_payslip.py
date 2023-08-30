# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

import time
import calendar
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from dateutil import rrule

from osv import fields,osv
from tools.translate import _
import decimal_precision as dp
import tools
import netsvc

class hr_payslip(osv.osv):
    _inherit = 'hr.payslip'

    def _calculate_total_slip(self, cr, uid, ids, name, args, context):
        if not ids: return {}
        result = {}
        for payslip in self.browse(cr, uid, ids, context=context):
            result[payslip.id] = 0.0
            for line in payslip.line_ids:
                if not line.is_provision:
                    result[payslip.id] += float(line.quantity) * line.amount
        return result
    
    def _compute_hours(self, cr, uid, ids, name, args, context=None):
        result = {}
        for pay in self.browse(cr, uid, ids, context=context):
            working_hours_on_day=0
            if pay.date_from and pay.date_to and pay.contract_id:
                day_from = datetime.strptime(pay.date_from,"%Y-%m-%d")
                day_to = datetime.strptime(pay.date_to,"%Y-%m-%d")
                nb_of_days = (day_to - day_from).days + 1
                for day in range(0, nb_of_days):
                    working_hours_on_day += self.pool.get('resource.calendar').working_hours_on_day(cr, uid, pay.contract_id.working_hours, day_from + timedelta(days=day), context)
            result[pay.id]= working_hours_on_day
        return result

    def _compute_total_discounts(self, cr, uid, ids, name, args, context=None):
        result = {}
        for payslip in self.browse(cr, uid, ids, context=context):
            result[payslip.id] = 0.0
            for lines in payslip.discount_lines_ids:
                    result[payslip.id] += lines.amount
        return result
       
    _columns = {
        'total_of_hours': fields.function(_compute_hours, type='float', method=True, string='Total of hours', store=True),
        'wk_days': fields.float('Work Days', digits_compute=dp.get_precision('Payroll'), readonly=True, states={'draft': [('readonly', False)]}),
        'total_payslip_lines': fields.function(_calculate_total_slip, method=True, type='float', string='Total of Payslip', digits_compute=dp.get_precision('Payroll'),store=True), 
        'leaves_days_line_ids': fields.one2many('hr.payslip.leaves_days', 'payslip_id', 'Payslip Leaves Days', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'discount_lines_ids':fields.one2many('hr.payslip.discount', 'payslip_id', 'Payslip', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'check_id':fields.many2one('account.payments', 'Check', readonly=True),
        'department_id': fields.related ('contract_id','department_id',type="many2one", relation="hr.department",string='Department',store=True),
        'payslip_run_id': fields.many2one('hr.payslip.run', 'Payslip Batches', readonly=True,),
        'total_discounts': fields.function(_compute_total_discounts, type='float', method=True, string='Total Discount'),
        'area_id': fields.many2one('account.area', 'Area',readonly=True, states={'draft': [('readonly', False)]}),
        'period_payment':fields.many2one('hr.period', 'Slip Period',readonly=True, states={'draft': [('readonly', False)]}),        
        'mode_id':fields.many2one('payment.mode', 'Modo de Pago', readonly=False, required = False),
        }
 
#    _order = 'employee_id asc'    

    _sql_constraints = [('reference_uniq', 'unique (employee_id,period_payment,state,company_id)','Slip period must be unique. Please check !')]
                        
                        
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
#         inp_ids = []    
#         input_obj = self.pool.get('hr.payslip.input')    
        payslips = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for t in payslips:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete payslip(s) that are done !'))
#         if unlink_ids:
#             input_ids = input_obj.search(cr, uid,[('payslip_id','=',payslips)])
#             for input in input_ids:
#                 inp_ids.append(input.input_id)
#             input_obj.unlink(cr,uid,unlink_ids, context=context)    
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True

    def get_worked_day_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
       
        def was_on_leave2(employee_id, datetime_day, datetime_day2, context=None):
            res = False
            holiday_ids = []
            day = datetime_day.strftime("%Y-%m-%d")
            day2 = datetime_day2.strftime("%Y-%m-%d")
            init = datetime.strptime((day2[0:8]+'01'),"%Y-%m-%d")
            day_init = init.strftime("%Y-%m-%d")
            holiday = self.pool.get('hr.holidays').search(cr, uid, [('state','=','validate'),('employee_id','=',employee_id),('type','=','remove')])
            if holiday: 
                for hol_id in self.pool.get('hr.holidays').browse(cr, uid, holiday):
                    if (hol_id.date_to >= day_init and hol_id.date_to <= day2) or (hol_id.date_to >= day2 and hol_id.date_from <= day2):
                        holiday_ids.append(hol_id.id) 
                    else: 
                        holiday_ids = []
            return holiday_ids
        nb_total = 0.0
        nb_days = 0.0
        res = []
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            if not contract.working_hours:
                continue
            attendances = {
                 'name': _("Normal Working Days paid at 100%"),
                 'sequence': 1,
                 'code': 'WORK100',
                 'number_of_days': 0.0,
                 'number_of_hours': 0.0,
                 'contract_id': contract.id,
            }
            if contract.date_start:
                if contract.date_start > date_from:
                    day_from = datetime.strptime(contract.date_start,"%Y-%m-%d")
                else:
                    day_from = datetime.strptime(date_from,"%Y-%m-%d")                    
            if contract.date_end and contract.date_end <= date_to:
                day_to = datetime.strptime(contract.date_end,"%Y-%m-%d")
            else:
                day_to = datetime.strptime(date_to,"%Y-%m-%d")
            day_to2 = datetime.strptime(date_to,"%Y-%m-%d")
            if  day_to.day in (28,29,30,31):
                day_to = 30
            else:
                day_to=day_to.day
            nb_of_days = (day_to - day_from.day) + 1
            nb_of_days2 = nb_of_days
            leaves=[]
            for day in range(0, nb_of_days2):
                leave_ids = was_on_leave2(contract.employee_id.id, day_from + timedelta(days=day), day_to2, context=context)
                if leave_ids:
                    leaves.extend(leave_ids)
            leaves = list(set(leaves))
            if leaves:
                for le in self.pool.get('hr.holidays').browse(cr, uid, leaves, context=context):
                    if le.date_from and le.date_to:
                        holiday_from = datetime.strptime(le.date_from[0:10],"%Y-%m-%d")
                        holiday_init = datetime.strptime((le.date_to[0:8]+'01'),"%Y-%m-%d")                        
                        holiday_to = datetime.strptime(le.date_to[0:10],"%Y-%m-%d")
                        day_to2 = datetime.strptime(date_to,"%Y-%m-%d")
                        if holiday_from >= day_from:
                            if day_to2.month==2 or day_to2.day in (28,29,30,31):
                                day_to2 = 30 
                                nb_days = (day_to2 - holiday_from.day) +1
                            else:   
                                nb_days = (day_to2 - holiday_from).days +1
                        elif holiday_init == day_from and holiday_to >= day_to2:
                            nb_days = 15 
                        elif holiday_to >= day_to2:
                            #nb_of_days = (holiday_init - day_from).days -1                            
                            if day_to2.month==2 or day_to2.day in (28,29,30,31):
                                day_to2 = 30 
                                nb_days = (day_to2 - holiday_from.day)+1
                            else:
                                nb_days = (day_to2 - holiday_from).days +1      
                        elif holiday_init == day_from and holiday_to >= day_from:
                            nb_days = (holiday_to - day_from).days +1      
                        elif holiday_to >= day_from or holiday_to >= holiday_init:
#                             nb_of_days = (holiday_to - day_from).days
                            nb_days = (holiday_to - holiday_from).days +1   
                        else:
                            nb_days = (holiday_to - holiday_from).days +1
            for day in range(0, nb_of_days):
                working_hours_on_day = self.pool.get('resource.calendar').working_hours_on_day(cr, uid, contract.working_hours, day_from + timedelta(days=day), context)
                attendances['number_of_days'] += 1.0
                nb_total += 1.0
                attendances['number_of_hours'] += working_hours_on_day            
            if (nb_total - nb_days) > 0 and nb_days <=15: 
                attendances['number_total_days'] = nb_total - nb_days
            else:
                attendances['number_total_days'] = 30 - nb_days
            res += [attendances]

        income_lines = self.pool.get('hr.incomes.lines')
        incomes = income_lines.search(cr, uid, [('contract_id','=',contract_ids[0]),('state','=','approve')]) 
        for inc in incomes:
            i = income_lines.browse(cr,uid,inc,context) 
            if i.income_type_id.type_income == 'extra_hours':
                if self._validate_date(date_to, i.input_id.collection_form):
                    inputs = {
                             'name': i.name,
                             'code': i.income_type_id.code,
                             'contract_id': i.contract_id.id,
                             'number_of_hours':i.quantity, 
                             'percentage_extra': i.income_type_id.value_extra,
                             'number_of_days': 0.00,     
                             'input_id': i.input_id.id,
                             'i_id': i.id
                            }
                    res += [inputs]
        return res
    
    def get_leaves_day_lines(self, cr, uid, employee_id, contract_ids, date_from, date_to, context=None):
        
        def was_on_leave(employee_id, datetime_day, datetime_day2, context=None):
            res = False
            holiday_ids = []
            day = datetime_day.strftime("%Y-%m-%d")
            day2 = datetime_day2.strftime("%Y-%m-%d")
            init = datetime.strptime((day2[0:8]+'01'),"%Y-%m-%d")
            day_init = init.strftime("%Y-%m-%d")
            holiday = self.pool.get('hr.holidays').search(cr, uid, [('state','=','validate'),('employee_id','=',employee_id),('type','=','remove')])
            if holiday: 
                for hol_id in self.pool.get('hr.holidays').browse(cr, uid, holiday):
                    if (hol_id.date_to >= day_init and hol_id.date_to <= day2) or (hol_id.date_to >= day2 and hol_id.date_from <= day2):
                        holiday_ids.append(hol_id.id) 
                    else: 
                        holiday_ids = []
            return holiday_ids
        
        res = []
        nation_pool = self.pool.get('hr.holidays.national')
        nations_ids = nation_pool.search(cr,uid,[('date','>=',date_from),('date','<=',date_to)])
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            if not contract.working_hours:
                continue
            day_from = datetime.strptime(date_from,"%Y-%m-%d")
            day_to = datetime.strptime(date_to,"%Y-%m-%d")
            nb_of_days = (day_to - day_from).days + 1
            leaves=[]
            for day in range(0, nb_of_days):
                leave_ids = was_on_leave(contract.employee_id.id, day_from + timedelta(days=day), day_to, context=context)
                if leave_ids:
                    leaves.extend(leave_ids)
            leaves = list(set(leaves))
            first_quarter_day = 0.00
            second_quarter_day = 0.00
            first_q = []
            second_q = []
            for dt in rrule.rrule(rrule.DAILY,dtstart=datetime.strptime(date_from,"%Y-%m-%d"),until=datetime.strptime(date_to,"%Y-%m-%d")):
                if int(dt.day) <=15:
                    first_q.append(int(dt.day))
                else:
                    second_q.append(int(dt.day))           
            if leaves:
                for le in self.pool.get('hr.holidays').browse(cr, uid, leaves, context=context):
                    if le.date_from and le.date_to:
                        holiday_from = datetime.strptime(le.date_from[0:10],"%Y-%m-%d")
                        holiday_init = datetime.strptime((le.date_to[0:8]+'01'),"%Y-%m-%d")                        
                        holiday_to = datetime.strptime(le.date_to[0:10],"%Y-%m-%d")
                        day_from = datetime.strptime(date_from,"%Y-%m-%d")
                        day_to = datetime.strptime(date_to,"%Y-%m-%d")
                        if holiday_from >= day_from:
                            if day_to.month==2 or day_to.day in (28,29,30,31):
                                day_to = 30 
                                nb_of_days = (day_to - holiday_from.day) +1
                            else:   
                                nb_of_days = (day_to - holiday_from).days +1
                        elif holiday_init == day_from and holiday_to >= day_to:
                            nb_of_days = 15 
                        elif holiday_to >= day_to:
                            #nb_of_days = (holiday_init - day_from).days -1                            
                            if day_to.month==2 or day_to.day in (28,29,30,31):
                                day_to = 30 
                                nb_of_days = (day_to - holiday_from.day)+1
                            else:
                                nb_of_days = (day_to - holiday_from).days +1      
                        elif holiday_init == day_from and holiday_to >= day_from:
                            nb_of_days = (holiday_to - day_from).days +1      
                        elif holiday_to >= day_from or holiday_to >= holiday_init:
#                             nb_of_days = (holiday_to - day_from).days
                            nb_of_days = (holiday_to - holiday_from).days +1   
                        else:
                            nb_of_days = (holiday_to - holiday_from).days +1
                        for dt in rrule.rrule(rrule.DAILY,dtstart=holiday_from,until=holiday_to):
                            if holiday_from.month == holiday_to.month:
                                if int(dt.day) <=15:
                                    first_quarter_day+=1
                                else:
                                    second_quarter_day += 1
                            elif holiday_to.month > holiday_from.month: 
                                if int(dt.day) <=15:
                                    second_quarter_day += 1
                                else:
                                    first_quarter_day+=1                                
                    if not le.justified:
                        code='leave_unjustified'
                    leave_line = {
                         'leave_id': le.id,
                         'name': le.holiday_status_id.name,
                         'code': le.holiday_status_id.name,
                         'number_of_days': nb_of_days,
                         'number_total_days': le.number_of_days,
                         'number_of_hours': le.number_of_hours,
                         'date_from': le.date_from[0:10],
                         'date_to': le.date_to[0:10],
                         'first_quarter_day': first_quarter_day,
                         'second_quarter_day': second_quarter_day,                         
                         'contract_id': contract.id,
                    }
                    res += [leave_line]        
            if nations_ids:
                for nhi in nations_ids:
                    leave_line = {                                  
                             'name': _("Holidays"),
                             'code': _("Holidays"),
                             'number_of_days': 1,
                             'number_total_days': 1,
                             'number_of_hours': 0.00,
                             'date_from': le.date_from[0:10],
                             'date_to': le.date_to[0:10],
                             'contract_id': contract.id,
                        }
                    res += [leave_line]
        return res
    
    def _validate_date(self, date_to, collection_form, context={}):
        date_to = datetime.strptime(date_to,"%Y-%m-%d")
        date_new = date_to + timedelta(days=1)
        b=False
        if date_new.day == 16:
            if collection_form in ('middle_month','middle_end_month'):
                b=True
        elif date_new.month > date_to.month or date_new.year > date_to.year:
            if collection_form in ('end_month','middle_end_month'):
                b=True
        return b
    
    def get_discount_lines(self, cr, uid, employee_id, date_to, contract_ids, context=None):
        if contract_ids:
            res = []
            discount_line_obj=self.pool.get('hr.discount.lines')
            discount_lines_ids= discount_line_obj.search(cr, uid, [('employee_id','=',employee_id),('discount_id.state','in',('approve','paid')),('state','=','draft'),('date','<=',date_to)])
            for discount_lines in discount_line_obj.browse(cr, uid, discount_lines_ids, context):
                if self._validate_date(date_to, discount_lines.discount_id.collection_form):                    
                    if date_to[8:10] == '15' or discount_lines.discount_id.collection_form != 'middle_end_month':
                        discount_line = {
                                        'name':discount_lines.name,
                                        'date': discount_lines.date,
                                        'amount': discount_lines.amount,
                                        'code':discount_lines.discount_id.name.code,
                                        'number_quota': discount_lines.number_quota,
                                        'discount_line_id':discount_lines.id,
                                        'expense_type_id':discount_lines.discount_id.name.id,
                                        'ref':discount_lines.ref,
                                        'internal':discount_lines.discount_id.name.internal
                                    }
                    elif discount_lines.discount_id.collection_form == 'middle_end_month':
                        discount_line = {
                                        'name':discount_lines.name,
                                        'date': discount_lines.date,
                                        'amount': discount_lines.amount,
                                        'code':discount_lines.discount_id.name.code,
                                        'number_quota': discount_lines.number_quota,
                                        'discount_line_id':discount_lines.id,
                                        'expense_type_id':discount_lines.discount_id.name.id,
                                        'ref':discount_lines.ref,
                                        'internal':discount_lines.discount_id.name.internal
                                    }
                    res += [discount_line]
            return res
    
    def get_inputs(self, cr, uid, contract_ids, date_from, date_to, payslip_id, context=None):
        res = []
        income_lines = self.pool.get('hr.incomes.lines')
        incomes = income_lines.search(cr, uid, [('contract_id','=',contract_ids[0]),('input_id.state','in',('approve','paid')),('state','=','approve'),('date','<=',date_to)]) 
        for inc in incomes:
            i = income_lines.browse(cr,uid,inc,context) 
            if i.income_type_id.type_income == 'other':
                if self._validate_date(date_to, i.input_id.collection_form):
                    inputs = {
                             'name': i.name,
                             'income_type_id': i.income_type_id.id,
                             'amount': i.amount,
                             'quantity': i.quantity,
                             'price':i.price,
                             'contract_id': i.contract_id.id,
                             'input_id': i.input_id.id,
                             'i_id': i.id,
                            }
                    res += [inputs]               
        return res                    
    
    def onchange_days_id(self, cr, uid, ids, period_payment, employee_id=False, contract_id=False, company_id=False, period_id=False, context=None):
        if context is None:
            context = {}
        period_obj = self.pool.get('hr.period')
        employ_ob = self.pool.get('hr.employee')
        journal_ids= self.pool.get('account.journal').search(cr,uid,[('company_id','=',company_id),('type','=','discount_employee')])
        if not journal_ids:
            raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
        else:
            journal_id= journal_ids[0]

#         if employee_id:
#             unemployee = employ_ob.browse(cr,uid,employee_id).unemployee
#             if unemployee == True:
#                 raise osv.except_osv(_('Error'), _('Employee not have a active contract'))
#             else:
#                 unemployee = True
        unemployee=False
        days = None
#        period_id = False
#         company_id = False
        if company_id:
            company_id=company_id
        else:
#             raise osv.except_osv(_('Need a company!'), _('You must defined a company for this payslip'))
            company_id=False
        if period_payment:
            date_from = period_obj.browse(cr,uid,period_payment).date_start
            date_to = period_obj.browse(cr,uid,period_payment).date_stop
        else:
            return False
        
        if period_id and period_id==self.pool.get('account.period').search(cr, uid, [('date_start','<=',date_from),('date_stop','>=',date_to), ('company_id', '=', company_id)])[0] :
            period_id = period_id            
        elif date_from and date_to and company_id:
            period_id = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date_from),('date_stop','>=',date_to), ('company_id', '=', company_id)])[0]            
        else:
            raise osv.except_osv(_('Need a account period!'), _('You must defined a account period for this payslip'))

        res = {}        
        if contract_id and unemployee==False:
            date_contract = self.pool.get('hr.contract').browse(cr,uid,contract_id).date_start
            if date_contract < date_from:
                date_from = date_from
            else:
                date_from = date_contract

#        res.update(self.onchange_employee_id(cr, uid, ids, date_from, date_to, employee_id, contract_id, context)['value'])
        res.update(self.onchange_employee_id(cr,uid,ids, employee_id, contract_id, period_payment, company_id, period_id)['value'])
        if not date_from and date_to:
            raise osv.except_osv(_('Error'), _('Need a generate hr payment periods for fiscal year.'))
        if date_from and date_to:
            if date_from > date_to:
                raise osv.except_osv(_('Error'), _('Date from is greater then Date to'))
            else:
                day_from = datetime.strptime(date_from, "%Y-%m-%d")
                day_to = datetime.strptime(date_to, "%Y-%m-%d")
                if day_to.month==2 or day_to.day in (28,29,30,31):
                    day_to = 30                 
                    days = (day_to - day_from.day) +1
                else:   
                    days = (day_to - day_from).days +1

                if days >= 31:                    
                    days = 30
                elif str(day_to)[5:7]== '02': 
                    if str(day_to)[8:10] in ('28','29') and str(day_from)[8:10] in ('01') and days in (27,28,29):
                        days = 30
                    elif str(day_to)[8:10] in ('28','29','15') and str(day_from)[8:10] in ('01','16') and days in (12,13,14):
                        days = 15
                    else:
                        days = (day_to - day_from).days        
                elif str(day_to)[8:10]== '15':
                    days = 15
                elif days<30 and days>16:
                    days = days + 1
                else:
                    days = days                             
            res['period_id'] = period_id
            res['journal_id']=journal_id
            res['date_from'] = date_from            
            res['date_to'] = date_to
            res['wk_days'] = days
        return {'value':res}
    
    def onchange_contract_id(self, cr, uid, ids, date_from, date_to, employee_id=False, contract_id=False, context=None):
        if context is None:
            context = {}
        res = {'value':{
                 'line_ids': [],
                 'name': '',
                 }
              }
        context.update({'contract': True})
        contract_obj = self.pool.get('hr.contract')
        if not contract_id:
            res['value'].update({'struct_id': False, 'journal_id':False})
        else:        
            journal_id = contract_id and contract_obj.browse(cr, uid, contract_id, context=context).journal_id.id or False
            res['value'].update({'journal_id': journal_id})
        return res
    
    def onchange_employee_id(self, cr, uid, ids, employee_id=False, contract_id=False, period_payment = False, company_id=False, period_id=False, context=None):
        res = None
        employee_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        worked_days_obj = self.pool.get('hr.payslip.worked_days')
        input_obj = self.pool.get('hr.payslip.input')
        leave_obj = self.pool.get('hr.payslip.leaves_days')
        discount_obj = self.pool.get('hr.payslip.discount')
        period_obj = self.pool.get('hr.period')
        if context is None:
            context = {}
        #delete old worked days lines
        old_worked_days_ids = ids and worked_days_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_worked_days_ids:
            worked_days_obj.unlink(cr, uid, old_worked_days_ids, context=context)

        #delete old input lines
        old_input_ids = ids and input_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_input_ids:
            input_obj.unlink(cr, uid, old_input_ids, context=context)
        
        #delete old leaves lines    
        old_leave_ids = ids and leave_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_leave_ids:
            leave_obj.unlink(cr, uid, old_leave_ids, context=context)
            
        #delete old discount lines    
        old_discount_ids = ids and discount_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_discount_ids:
            discount_obj.unlink(cr, uid, old_discount_ids, context=context)


        #defaults
        res = {'value':{
                      'line_ids':[],
                      'input_line_ids': [],
                      'worked_days_line_ids': [],
                      'leaves_days_line_ids': [],
                      'discount_lines_ids':[],
                      'name':'',
                      'contract_id': False,
                      'struct_id': False,
                      'area_id': False,
                      }
            }
        if not employee_id:
            return res
        if period_payment:
            date_from = period_obj.browse(cr,uid,period_payment).date_start
            date_to = period_obj.browse(cr,uid,period_payment).date_stop        
        if not date_from and date_to:
            raise osv.except_osv(_('Error'), _('Need a generate hr payment periods for fiscal year.'))
        if date_from and date_to:
            if date_from > date_to:
                raise osv.except_osv(_('Error'), _('Date from is greater then Date to'))
            else:
                day_from = datetime.strptime(date_from, "%Y-%m-%d")
                day_to = datetime.strptime(date_to, "%Y-%m-%d")                
                days = (day_to - day_from).days
                if days >= 31:                    
                    days = 30
                elif str(day_to)[5:7]== '02': 
                    if str(day_to)[8:10] in ('28','29') and str(day_from)[8:10] in ('01') and days in (28,29):
                        days = 30
                    elif str(day_to)[8:10] in ('28','29') and str(day_from)[8:10] in ('01','16') and days in (13,14):
                        days = 15
                    else:
                        days = (day_to - day_from).days                    
                else:
                    days = days                              
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        employee_id = employee_obj.browse(cr, uid, employee_id, context=context)
        if employee_id.unemployee==True:
            return res
        if employee_id.department_id:
            area_id = employee_id.department_id.area_id.id
        else:
            contract_old = contract_obj.browse(cr,uid,contract_id,context) 
            area_id = contract_old.department_id.area_id.id
        res['value'].update({
                    'name': _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                    'company_id': employee_id.company_id.id,
                    'area_id': area_id
        })
                        
        if not context.get('contract', False):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
            if contract_ids:
                struct_ids = self.pool.get('hr.contract').browse(cr,uid,contract_ids[0]).struct_id
                if struct_ids:
                    struct_id = contract_ids and contract_obj.read(cr, uid, contract_ids[0], ['struct_id'], context=context)['struct_id'][0] or False
                else:
                    raise osv.except_osv(_('Invalid action !'), _('Contract Employee has not salary structure !'))
                journal_ids = self.pool.get('hr.contract').browse(cr,uid,contract_ids[0]).journal_id    
                if journal_ids:
                    journal_id= contract_ids and contract_obj.read(cr, uid, contract_ids[0], ['journal_id'], context=context)['journal_id'][0] or False
                else:
                    raise osv.except_osv(_('Invalid action !'), _('Contract Employee has not Salary Journal !'))
                date_contract = contract_obj.browse(cr,uid,contract_ids[0]).date_start                
                if date_contract >= date_from and date_to >= date_contract:
                    date_from = contract_obj.browse(cr,uid,contract_ids[0]).date_start
                else:
                    date_from = date_from                    
                leave_line_ids = self.get_leaves_day_lines(cr, uid, employee_id.id, contract_ids, date_from, date_to, context=context)                                            
                worked_days_line_ids = self.get_worked_day_lines(cr, uid, contract_ids, date_from, date_to, context=context)
                input_line_ids = self.get_inputs(cr, uid, contract_ids, date_from, date_to, ids, context=context)
                discount_lines_ids=self.get_discount_lines(cr, uid, employee_id.id, date_to, contract_ids, context)                
                if date_to >= date_contract:
                    res['value'].update({
#                         'struct_id': contract_ids and contract_obj.read(cr, uid, contract_ids[0], ['struct_id'], context=context)['struct_id'][0] or False,
#                         'journal_id': contract_ids and contract_obj.read(cr, uid, contract_ids[0], ['journal_id'], context=context)['journal_id'][0] or False,
                        'struct_id':struct_id,
                        'contract_id': contract_ids and contract_ids[0] or False,
                        'date_from':date_from,
                        'wk_days':days,
                        'journal_id':journal_id,
                        'worked_days_line_ids': worked_days_line_ids,
                        'input_line_ids': input_line_ids,
                        'leaves_days_line_ids': leave_line_ids,
                        'discount_lines_ids':discount_lines_ids,
                        })
                return res 
            else:
                return res

    def get_contract(self, cr, uid, employee, date_from, date_to, context=None):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.pool.get('hr.contract')
        clause = []
        #a contract is valid if it ends between the given dates
        clause_1 = ['&',('date_end', '<=', date_to),('date_end','>=', date_from)]
        #OR if it starts between the given dates
        clause_2 = ['&',('date_start', '<=', date_to),('date_start','>=', date_from)]
        #OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = [('date_start','<=', date_from),'|',('date_end', '=', False),('date_end','<=', date_to)]
        clause_final =  [('employee_id', '=', employee.id),('contract_active','=',True),'|','|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(cr, uid, clause_final, context=context)
        return contract_ids
    
    def compute_sheet(self, cr, uid, ids, context=None):
        for payslip in self.browse(cr, uid, ids, context):
            date_from=payslip.date_from
            date_to=payslip.date_to
            clause_1=['&',('date_from','>=',date_from),('date_from','<=',date_to)]
            clause_2=['&',('date_to','>=',date_from),('date_to','<=',date_to)]
            clause_final =  [('employee_id', '=', payslip.employee_id.id),('id','not in',tuple(ids)),('state','=','done'),'|'] + clause_1 + clause_2
            old_payslip = self.search(cr, uid, clause_final, context=context)
            if old_payslip:
                raise osv.except_osv(_('Error !'),_("Already exists payroll that was generated within this date range for the employee"))            
        return super(hr_payslip, self).compute_sheet(cr, uid, ids, context)
    
    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, employee_id, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.employee_id = employee_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(amount) as sum\
                            FROM hr_payslip as hp, hr_payslip_input as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()[0]
                return res or 0.0
                        
        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours\
                            FROM hr_payslip as hp, hr_payslip_worked_days as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done'\
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0
            
        class LeaveDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours\
                            FROM hr_payslip as hp, hr_payslip_leaves_days as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done'\
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)\
                            FROM hr_payslip as hp, hr_payslip_line as pl \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s",
                            (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()
                return res and res[0] or 0.0

        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules = {}
        categories_dict = {}
        blacklist = []
        payslip_obj = self.pool.get('hr.payslip')
#        inputs_obj = self.pool.get('hr.payslip.worked_days')
        obj_rule = self.pool.get('hr.salary.rule')
        payslip = payslip_obj.browse(cr, uid, payslip_id, context=context)
        worked_days = {}
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days[worked_days_line.code] = worked_days_line
        leave_days = {}
        for leave_days_line in payslip.leaves_days_line_ids:
            leave_days[leave_days_line.code] = leave_days_line
        inputs = {}
        for input_line in payslip.input_line_ids:
            inputs[input_line.code] = input_line
#        discounts = {}
#        for discount_line in payslip.discount_lines_ids:
#            discounts[discount_line.code] = discount_line        
        categories_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, categories_dict)
#        input_obj = InputLine(self.pool, cr, uid, payslip.employee_id.id, inputs)
        worked_days_obj = WorkedDays(self.pool, cr, uid, payslip.employee_id.id, worked_days)
        leaves_days_obj = LeaveDays(self.pool, cr, uid, payslip.employee_id.id, leave_days)
#        discounts_obj = DiscountLine(self.pool, cr, uid, payslip.employee_id.id, discounts)
        payslip_obj = Payslips(self.pool, cr, uid, payslip.employee_id.id, payslip)
        rules_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, rules)

        localdict = {'categories': categories_obj, 'rules': rules_obj, 
                     'payslip': payslip_obj, 'worked_days': worked_days_obj, 'leaves_days': leaves_days_obj,
                     'leaves': payslip.leaves_days_line_ids,'inputs': payslip.input_line_ids, 
                     'discounts':payslip.discount_lines_ids, 'extra_hours':payslip.worked_days_line_ids}
        #get the ids of the structures on the contracts and their parent id as well
        structure_ids = self.pool.get('hr.contract').get_all_structures(cr, uid, contract_ids, context=context)
        #get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]

        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            employee = contract.employee_id
            localdict.update({'employee': employee, 'contract': contract})
            for rule in obj_rule.browse(cr, uid, sorted_rule_ids, context=context):
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                #check if the rule can be applied
                if obj_rule.satisfy_condition(cr, uid, rule.id, localdict, context=context) and rule.id not in blacklist:
                    #compute the amount of the rule
                    amount, qty, rate= obj_rule.compute_rule(cr, uid, rule.id, localdict, context=context)
                    #check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    #set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules[rule.code] = rule
                    #sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    #create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'is_provision':rule.is_provision
                    }
                else:
                    #blacklist this rule and its children
                    blacklist += [id for id, seq in self.pool.get('hr.salary.rule')._recursive_search_of_rules(cr, uid, [rule], context=context)]

        result = [value for code, value in result_dict.items()]
        
        return result
       
    def create_move_line_payslip(self, cr, uid, line, partner, name, date, account, journal, period,amount, move_ids, reference, company_id, l_discount_id, analytic_account_id, shop_id, department_id, cost_journal, context=None):
        sql = """insert into account_move_line (journal_id,date_maturity,partner_id,name,date,debit,credit,account_id,amount_currency,currency_id,reference,quantity,product_id,product_uom_id,analytic_account_id,period_id,move_id,state,company_id,l_discount_id, tax_code_id,tax_amount,shop_id,department_id,cost_journal,active) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,True)"""
        currency_id = self.pool.get('res.company').browse(cr,uid,company_id).currency_id.id
        acc_acc_obj = self.pool.get('account.account')
        required_analytic = self.pool.get('res.company').browse(cr,uid,company_id).required_analytic
        analytic_account_id = None
        if account:
            analytic_id = acc_acc_obj.browse(cr,uid,account)
            if analytic_id and analytic_id.type=='other' and analytic_id.user_type.code in ('income','expense') and required_analytic:
                aa_id = analytic_id.analytic_account_id.id
                analytic_account_id =self.pool.get('account.analytic.account').browse(cr,uid,aa_id).id
                if not analytic_account_id and required_analytic:
                    raise osv.except_osv(_('Warning'), _('You can define a analytic account in the account %s for generate salary moves')%(analytic_id.code))
        if not cost_journal:
            cost_journal = None
        partner_id = self.pool.get('res.partner').browse(cr,uid,partner)
        if not department_id:
            raise osv.except_osv(_('Warning'), _('You can define a department for the partner %s for generate salary moves')%(partner_id.name))        
        if not shop_id:
            raise osv.except_osv(_('Warning'), _('You can define a shop for the partner %s for generate salary moves')%(partner_id.name))        
        
        cd = self.pool.get('res.currency').browse(cr,uid,currency_id).rate
        state_move = 'valid'
        if context is None:
            context={}        
        if not line:
            analytic_account_id=analytic_account_id
            tax_code_id=None
            tax_amount=None
        else:
            #analytic_account_id=line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or False
            analytic_account_id=analytic_account_id
            tax_code_id=line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False
            tax_amount=line.salary_rule_id.account_tax_id and amount or 0.0
        if l_discount_id:
            l_discount_id = l_discount_id
        else:
            l_discount_id = None
        if context.get('adjust_credit',False):
            debit=0.0
            credit=amount
            analytic_account_id=None
            tax_code_id=None
            tax_amount=0.0
        if context.get('adjust_debit',False):
            debit=amount
            credit=0.0
            analytic_account_id=None
            tax_code_id=None
            tax_amount=0.0
        if context.get('debit',False):
            debit=amount > 0.0 and amount or 0.0
            credit=amount < 0.0 and -amount or 0.0
        if context.get('credit',False):
            debit=amount < 0.0 and -amount or 0.0
            credit=amount > 0.0 and amount or 0.0
        line={'name': name,
              'date': date,
              'partner_id': partner,
              'debit': debit,
              'credit': credit,
              'account_id': account,
              'journal_id': journal,
              'period_id': period,
              'reference':reference, 
              'company_id': company_id,
              'move_id': move_ids,
              'analytic_account_id': analytic_account_id,
              'tax_code_id': tax_code_id,
              'tax_amount': tax_amount,
              'l_discount_id': l_discount_id,
              'department_id': department_id,
              'cost_journal': cost_journal, 
              'shop_id': shop_id,             
                }            
        cr.execute(sql,(journal,None,partner,name,date,debit,credit,account,((debit+credit)*cd),currency_id,reference,1,None,None,analytic_account_id,period,move_ids,state_move,company_id,l_discount_id,tax_code_id,tax_amount,shop_id, department_id,cost_journal))
        return line
    
    
    def process_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        pay_pool = self.pool.get('account.payments')
        move_line_pool = self.pool.get('account.move.line')
        timenow = time.strftime('%Y-%m-%d')
        to_reconcile=[]
        cost_journal = False
        debit_account_id = False
        credit_account_id = False
        if context is None:
            context={}
        for slip in self.browse(cr, uid, ids, context=context):
            line_ids=[]
            accounts_ids = {}
            debit_sum = 0.0
            credit_sum = 0.0
            journal_id = slip.journal_id.id
            company_id = slip.company_id.id
            analytic_account_id = False
            department_id = slip.employee_id.department_id.id
            shop_id = slip.employee_id.shop_id.id
#             if not analytic_account_id:
#                 raise osv.except_osv(_('Warning'), _('You can define a analytic account in shop for generate salary moves'))
            cost_journal_ids = self.pool.get('account.analytic.journal').search(cr,uid,[('default','=',True),('active','=',True)])
            if cost_journal_ids:
                cost_journal = cost_journal_ids[0]
            context['search_shop']=True
            if not slip.period_id:
                search_periods = self.pool.get('account.period').find(cr, uid, slip.date_to, context=context)
                period_id = search_periods and search_periods[0] or None
            else:
                period_id = slip.period_id.id
            name = _('Payslip of %s') % (slip.employee_id.name)
            move = {
                'name':name,
                'details':'Nómina de Colaboradores',
                'narration': name,
                'date': slip.date_to,
                'ref': slip.number,
                'journal_id': journal_id,
                'period_id': period_id,
                'company_id': company_id,
                'partner_id': slip.employee_id.partner_id.id,
                'company_id': slip.company_id.id,
                'shop_id': slip.employee_id.shop_id.id,
            }

            move_ids = self.pool.get('account.move').create(cr,uid,move)
            l_dis_ids = []
            for line in slip.line_ids:
                if line.total != 0 and line.salary_rule_id.generate_move:
                    amt = slip.credit_note and -line.total or line.total
                    if not line.salary_rule_id.multi:
                        debit_account_id = line.salary_rule_id.account_debit.id
                        credit_account_id = line.salary_rule_id.account_credit.id
                    else:
                        for acc in line.salary_rule_id.account_ids:
                            if slip.employee_id.department_id.area_id.id == acc.area_id.id:
                                debit_account_id = acc.account_debit.id
                                credit_account_id = acc.account_credit.id
                    l_discount_id = False
                    if not debit_account_id or not credit_account_id:
                        raise osv.except_osv(_('Warning'), _('You can define account for generate salary moves'))                         
                    if not accounts_ids.has_key(debit_account_id):                            
                        accounts_ids[debit_account_id]=amt
                    else:
                        accounts_ids[debit_account_id]+=amt
                    if not accounts_ids.has_key(credit_account_id):
                        accounts_ids[credit_account_id]=-amt
                    else:
                        accounts_ids[credit_account_id]-=amt
            if slip.discount_lines_ids:
                for discount in slip.discount_lines_ids: 
                    amt = 0.00
                    if discount and discount.amount>0:   
                        l_discount_id = discount.discount_line_id.id
                        l_dis_ids.append(l_discount_id)                                             
                        account_debit= slip.journal_id.default_credit_account_id.id                       
                        if not account_debit:
                            raise osv.except_osv(_('Error'), _('You must define a debit account in journal'))                                                     
                        account_credit= discount.expense_type_id.debit_account_id.id
                        if not account_credit:
                            raise osv.except_osv(_('Error'), _('You must define a credit account in journal'))
                        amt = discount.amount                     
                        if discount.name and discount.ref:
                            discount_name = discount.name + ' ' + discount.ref
                        else:
                            discount_name = discount.name 
                        if account_debit:
                            credit_line=self.create_move_line_payslip(cr, uid, None, slip.employee_id.partner_id.id, discount_name or '/', slip.date_to, account_credit, journal_id, period_id, discount.amount, move_ids, slip.number, company_id,l_discount_id, analytic_account_id, shop_id ,department_id,cost_journal,{'credit':True})
                            line_ids.append(credit_line)                                                
                        if not accounts_ids.has_key(account_debit):                            
                            accounts_ids[account_debit]=amt
                        else:
                            accounts_ids[account_debit]+=amt
                        if not discount.discount_line_id.discount_id.collection_form:
                            raise osv.except_osv(_('Error'), _('El descuento %s ha sido cambiado de estado luego de generar el preeliminar de la nómina para el colaborador %s')%(discount.discount_line_id.discount_id.name,slip.employee_id.name))
                        if discount.discount_line_id.discount_id.collection_form == 'middle_end_month' and slip.date_to[8:10] != '15':                                                        
                            if discount.discount_line_id.amount2 >0 and discount.discount_line_id.payslip_id:
                                discount.discount_line_id.write({'payslip_id2':slip.id,'state':'approve'})
                            else:
                                if discount.discount_line_id.amount2 >0:
                                    discount.discount_line_id.write({'payslip_id':slip.id,'state':'draft'})
                                else:
                                    discount.discount_line_id.write({'payslip_id':slip.id,'state':'approve'})
                        else:
                            if discount.discount_line_id.discount_id.collection_form == 'middle_end_month':
                                if discount.discount_line_id.amount2 >0:
                                    discount.discount_line_id.write({'payslip_id':slip.id,'state':'draft'})
                                else:
                                    discount.discount_line_id.write({'payslip_id':slip.id,'state':'approve'})
                            else:
                                discount.discount_line_id.write({'payslip_id':slip.id,'state':'approve'})
                        self.pool.get('hr.discount').test_state(cr, uid,[discount.discount_line_id.discount_id.id],{})
            for d in accounts_ids.keys():        
                name_account = self.pool.get('account.account').browse(cr,uid,d).name
                l_discount_id = False
                if accounts_ids[d] > 0:
                    debit_line=self.create_move_line_payslip(cr, uid, None, slip.employee_id.partner_id.id, name_account, slip.date_to, d, journal_id, period_id, accounts_ids[d], move_ids, slip.number, company_id, l_discount_id, analytic_account_id, shop_id, department_id,cost_journal,{'debit':True})
                    line_ids.append(debit_line)
                    debit_sum += debit_line['debit'] - debit_line['credit']
                if accounts_ids[d] < 0:                 
                    credit_line=self.create_move_line_payslip(cr, uid, None, slip.employee_id.partner_id.id, name_account, slip.date_to, d, journal_id, period_id, accounts_ids[d], move_ids, slip.number, company_id, l_discount_id,analytic_account_id, shop_id, department_id,cost_journal, {'debit':True})
                    line_ids.append(credit_line)
                    credit_sum += credit_line['credit'] - credit_line['debit']    
            if not slip.journal_id.default_credit_account_id or not slip.journal_id.default_debit_account_id:
                raise osv.except_osv(_('Warning'), _('A difference exist of amounts but are not configured in the journal accounts %s')%(slip.journal_id.name,))        
            self.pool.get('account.move').post(cr,uid,[move_ids])           
            if slip.input_line_ids:
                for income in slip.input_line_ids:
                    if income.i_id:
                        income.i_id.write({'payslip_id':slip.id,'state':'paid'})                        
                        self.pool.get('hr.incomes').test_state(cr, uid,[income.i_id.input_id.id],{})
            if slip.worked_days_line_ids:
                for income in slip.worked_days_line_ids:
                    if income.code == 'HE50' or income.code=='HE100':
                        income.i_id.write({'payslip_id':slip.id,'state':'paid'})                        
                        self.pool.get('hr.incomes').test_state(cr, uid,[income.i_id.input_id.id],{})                      
            slip.write({'move_id': move_ids,'period_id':period_id}, context=context)            
            context['fy_closing']=True    
            move_new = move_pool.browse(cr,uid,move_ids)
            self.write(cr, uid, slip.id, {'paid': True, 'state': 'done'}, context=context)
            if move_new and move_new.line_id and l_dis_ids:
                for nline in move_new.line_id: 
                    print move_new.partner_id.name
                    credit_val=self.pool.get('account.move.line').browse(cr,uid,nline.id)                    
                    if credit_val.credit > 0 and credit_val.l_discount_id:
                        l_ant = self.pool.get('hr.discount.lines').browse(cr,uid,credit_val.l_discount_id.id)
                        move_ant = l_ant.move_line_id.id
                        move_rec = nline.id
                        if move_ant and move_rec:
                            if not move_ant:
                                raise osv.except_osv(_('Warning'), _('The discount not have account move in approve state %s for partner %s')%(l_ant.discount_id.name,l_ant.partner_id.name))
                            else:
                                to_reconcile.append([move_ant, move_rec])
                                print self.pool.get('account.move').browse(cr,uid,move_new).id, self.pool.get('account.move').browse(cr,uid,move_rec).id
        for rec_ids in to_reconcile:
            print rec_ids
            if len(rec_ids) >= 2:
                move_line_pool.reconcile_partial(cr, uid, rec_ids, context=context)

                                
#             if not slip.employee_id.bank_account_id: 
#                     bank_ids = self.pool.get('res.partner.bank').search(cr,uid,[('partner_id','=',slip.company_id.partner_id.id),('default_bank','=',True)])
#                     if bank_ids:
#                         acc_bank = self.pool.get('res.partner.bank').browse(cr, uid,bank_ids[0])
#                         if acc_bank:
#                             acc = acc_bank.id
#                             bank_account_id = acc_bank.id
#                             bank_id = acc_bank.bank.id
#                             if slip.employee_id.partner_id:
#                                 check_id = pay_pool.create_check(cr,uid, [], slip.mode_id.id, slip.employee_id.partner_id.name, slip.date_to, slip.employee_id.partner_id.id, slip.total_payslip_lines, bank_account_id, bank_id,False,slip.id, False, False, slip.employee_id.shop_id.id)
#                                 self.write(cr, uid, [slip.id], {'check_id':check_id})
#                             else:                                                                                                                              
#                                 raise osv.except_osv(_('Error'), _('El colaborador %s no tiene creado una empresa para realizar los pagos')%(slip.employee_id.name))
#                     else:
#                         raise osv.except_osv(_('Error'), _('Necesita configurar una cuenta bancaria para los pagos de la compañía'))            

        return True
    
    def set_to_draft(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        checks_pool = self.pool.get('account.payments')
        discount_line_pool = self.pool.get('hr.discount.lines')
        wf_service = netsvc.LocalService("workflow")
        inc_ids = []
        for slip in self.browse(cr, uid, ids, context):
            if slip.check_id:
                if slip.check_id.state != 'draft':
                    #raise osv.except_osv(_('Error'), _('You can not change to state payroll in draft because there is a paid check'))
                    checks_pool.cancel_check(cr,uid,[slip.check_id.id],context=None)
                else:
                    self.pool.get('account.payments').unlink(cr, uid, [slip.check_id.id], context)
            if slip.payslip_run_id:
                if slip.payslip_run_id.state=='close':
                    raise osv.except_osv(_('Error'), _('Para cancelar esta Rol de Colaborador, primero debe cambiar a borrador la Nómina General de este período'))            
#             for discount in slip.discount_lines_ids:
#                 if discount.discount_line_id:
#                     #discount_line_pool.line_button_set_draft(cr,uid,[discount.discount_line_id.id])
#             for income in slip.input_line_ids:
#                 if income.i_id:
#                     self.pool.get('hr.incomes.lines').write(cr,uid,income.i_id.id,{'state':'draft','payslip_id':False})
            inc_ids = []
            if slip.input_line_ids:                               
                inc_ids = [income.input_id.id for income in slip.input_line_ids]    
                self.pool.get('hr.incomes').paid_to_approve(cr,uid,inc_ids,slip.id,context=None)   
            wkd_ids = []
            pay_ids = []
            if slip.worked_days_line_ids:
                for income in slip.worked_days_line_ids:
                    if income.code == 'HE50' or income.code == 'HE100':
                        wkd_ids.append(income.input_id.id)
                self.pool.get('hr.incomes').paid_to_approve(cr,uid,wkd_ids, slip.id,context=None)
            dis_ids = []    
            if slip.discount_lines_ids:
                    slip_id = slip.id
                    try:
                        dis_ids = [discount.discount_line_id.discount_id.id for discount in slip.discount_lines_ids]
                    except:
                        for discount in slip.discount_lines_ids:
                            dis_id = self.pool.get('hr.discount.lines').browse(cr,uid,discount.id)
                            if dis_id:
                                dis_ids.append(dis_id.id)
                    self.pool.get('hr.discount').approve_to_draft(cr,uid,dis_ids,slip_id,context=None)   
                    
            if slip.move_id:
                move_pool.button_cancel(cr, uid, [slip.move_id.id], context={})
                move_pool.trans_unreconcile(cr, uid, [slip.move_id.id], context={})
                move_pool.unlink(cr, uid, [slip.move_id.id], context={}) 
            wf_service.trg_delete(uid, 'hr.payslip', slip.id, cr)
            wf_service.trg_create(uid, 'hr.payslip', slip.id, cr)
        return self.write(cr, uid, ids, {'state': 'draft','check_id':False}, context=context)
    
hr_payslip()

class hr_payslip_line(osv.osv):

    _inherit = 'hr.payslip.line'
    _columns = {
        'is_provision':fields.boolean('Is Provision', required=False),
        'payslip_run_id': fields.related ('slip_id','payslip_run_id',type="many2one", relation="hr.payslip.run",string='Payslip Run',store=True),
        'department_id': fields.related ('slip_id','department_id',type="many2one", relation="hr.department",string='Department',store=True),
        'active': fields.boolean('Active')        
#        'payslip_run_id': fields.many2one('hr.payslip.run', 'Payslip Run', readonly=True, states={'draft': [('readonly', False)]}),
    }

    _defaults = {
        'active': True
                 }

    
    def unlink(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context):
            self.write(cr,uid,ids,{'active':False, 'amount':0.00, 'quantity':0.00})
        return True
    

hr_payslip_line()

class hr_payslip_discount(osv.osv):
    _name = 'hr.payslip.discount'
    _columns = {
        'name':fields.char('Name', size=128, required=True, readonly=False),
        'code': fields.related('expense_type_id','code', type='char', size=128, readonly=True, string='Code'),
        'internal': fields.related('expense_type_id', 'internal', type='boolean', string='Internal', readonly=True, store=True),
        'date': fields.date('Date'),
        'ref':fields.char('Reference', size=128, required=False, readonly=False),
        'amount': fields.float('amount', digits_compute=dp.get_precision('Payroll'), readonly=False),
        'number_quota': fields.integer('Number Quota'),
        'payslip_id':fields.many2one('hr.payslip', 'Payslip', required=False, ondelete="cascade"),
        'discount_line_id':fields.many2one('hr.discount.lines', 'Discount Line', required=False),
        'expense_type_id':fields.many2one('hr.transaction.type', 'Expense Type', required=False),
        'active': fields.boolean('Active')
    }
    
    _defaults = {
        'active': True
                 }

    def unlink(self, cr, uid, ids, context=None):
        for discount in self.browse(cr, uid, ids, context):
            self.write(cr,uid,ids,{'active':False, 'amount':0.00, 'number_quota':0.00, 'discount_line_id': False, 'payslip_id':False })
        return True    

    def onchange_number_quota(self, cr, uid, ids, number_quota=0, discount_line_id=None,context=None):
        if context is None:
            context = {}
        res = {}
        if not discount_line_id:
            return res
        if number_quota <=0:
            raise osv.except_osv(_('Error'), _('The quota must be greater than 0'))
        discount_line=self.pool.get('hr.discount.lines').browse(cr, uid, discount_line_id, context)
#         discount_line_search = self.pool.get('hr.discount.lines').search(cr, uid, [('discount_id','=',discount_line.discount_id.id),('number_quota','=',number_quota)])
#         if not discount_line_search:
#             raise osv.except_osv(_('Error'), _('Not exist a line of discount with this number of quota'))
#         res['discount_line_id']= discount_line_search[0]
        #TODO: Change discount_line_id for change_quotas in discount payslip
        res['name']= _("%s (%s quotas)") % (discount_line.discount_id.name.name, number_quota)
        return {'value':res}
hr_payslip_discount()

class hr_payslip_leaves_days(osv.osv):
    _name = 'hr.payslip.leaves_days'
    _inherit = 'hr.payslip.worked_days'
    _columns ={
               'leave_id': fields.many2one('hr.holidays','Ausencia'),
               'number_total_days': fields.integer('Total de días'),
               'date_from': fields.date('Fecha Inicio'),
               'date_to': fields.date('Fecha Final'),
               'first_quarter_day': fields.integer('Días Primera Quincena'),
               'second_quarter_day': fields.integer('Días Segunda Quincena'),
               }
hr_payslip_leaves_days()

class hr_payslip_input(osv.osv):
    _inherit = 'hr.payslip.input'  
    
    _columns = {
        'income_type_id':fields.many2one('hr.transaction.type', 'Income Type', required=False),
        'code': fields.related('income_type_id','code', type='char', size=64, readonly=True, string='Code', help="The code that can be used in the salary rules"),
#        'employee_id':fields.many2one('hr.employee', 'Employee',readonly=True,states={'draft': [('readonly', False)]}),
#        'date': fields.date('Date'),
#        'ref':fields.char('Reference', size=64, readonly=True,states={'draft': [('readonly', False)]}),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Payroll')),
        'price': fields.float('Price', digits_compute=dp.get_precision('Payroll')),
        'input_id':fields.many2one('hr.incomes','Income', required=False),
        'i_id': fields.many2one('hr.incomes.lines','Income Line', required=False),
        'payslip_id': fields.many2one('hr.payslip', 'Pay Slip', required=False, ondelete='cascade', select=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Payroll'),readonly=True),
#        'state': fields.selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True),                        
    }
        
hr_payslip_input()

class hr_payslip_worked_days(osv.osv):

    _inherit = 'hr.payslip.worked_days'
    _columns = {
        'i_id':fields.many2one('hr.incomes.lines', 'Type', required=False),
        'input_id':fields.many2one('hr.incomes', 'Type', required=False),        
        'transaction_id':fields.many2one('hr.transaction.type', 'Type', required=False),
        'percentage_extra': fields.float('% value Hours Extra', digits_compute=dp.get_precision('Payroll')),
        'number_total_days': fields.integer('Total de días'),
    }
    
    def on_change_transaction(self, cr, uid, ids, transaction_id=None, context=None):
        res={}
        if transaction_id:
            transaction=self.pool.get('hr.transaction.type').browse(cr, uid, transaction_id)
            res['code']=transaction.code
            res['name']=transaction.name
            res['percentage_extra']=transaction.value_extra
        return {'value':res}
hr_payslip_worked_days()
