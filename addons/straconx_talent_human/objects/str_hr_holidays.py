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

from osv import fields,osv
import time
from tools.translate import _
import datetime
from datetime import timedelta

class hr_holidays(osv.osv):
    _inherit = 'hr.holidays'
    
    def _calculate_hours_calendar(self, cr, uid, contract=None, date_from=None, date_to=None):
        working_hours_on_day=0
        if contract:
            dt = date_to - date_from
            for day in range(0, dt.days):
                working_hours_on_day += self.pool.get('resource.calendar').working_hours_on_day(cr, uid, contract.working_hours, date_from + timedelta(days=day))
        return working_hours_on_day
    
    def _compute_number_of_days(self, cr, uid, ids, name, args, context=None):
        result = {}
        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        day=0
        hours=0
        for hol in self.browse(cr, uid, ids, context=context):
            if hol.date_from and hol.date_to:
                result[hol.id]={}
                from_dt = datetime.datetime.strptime(hol.date_from, DATETIME_FORMAT)
                to_dt = datetime.datetime.strptime(hol.date_to, DATETIME_FORMAT)
#                 if to_dt.month==2 or to_dt.day in (28,29,30,31):
#                     to_dt = 30 
                dt = to_dt - from_dt
#                if dt.days >0:
                day=dt.days +1
                if dt.days <0:                                        
                    hours+=self._calculate_hours_calendar(cr, uid, hol.contract_id,from_dt,to_dt)
                hours+=dt.seconds/3600
                result[hol.id]['number_of_days'] = day
                result[hol.id]['number_of_hours'] = hours
        return result
    
    _columns = {
        'number_of_days': fields.function(_compute_number_of_days, type='float', method=True, string='Number of Days', store=True, multi='number_of_days'),
        'number_of_hours': fields.function(_compute_number_of_days, type='float', method=True, string='Number of hours', store=True,multi='number_of_hours'),
        'contract_id': fields.many2one('hr.contract', 'Contract'),
        'justified':fields.boolean('justified?', required=False),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'holiday_type': fields.selection([('employee','By Employee'),('category','All employees')], 'Allocation Type', help='By Employee: Allocation/Request for individual Employee, All Employees: Allocation/Request for all employees in Company', required=True),        
    }

    _defaults={
               'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.holidays', context=c),
               }
    
    def onchange_employee_id(self, cr, uid, ids, employee_id=False,company_id=False, context=None):
        res={}
        if context is None:
            context = {}
        if not (employee_id):
            return res
        employee_id = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        if employee_id.unemployee==True:
            return res
        contract_id = employee_id.contract_ids and employee_id.contract_ids[0].id or None
        res['contract_id']= contract_id
        return {'value':res}
    
    def onchange_date_from(self, cr, uid, ids, date_to, date_from, employee_id):
        result = {}
        if date_to and date_from and employee_id:
            employee_id = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            contract_ids = self.pool.get('hr.payslip').get_contract(cr, uid, employee_id, date_from, date_to)
            result['contract_id']= contract_ids and contract_ids[0] or False
        return {'value':result}

    def holidays_confirm(self, cr, uid, ids, context=None):
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.holiday_type == 'employee':
                if not holiday.contract_id:
                    raise osv.except_osv(_('Error'), _('Do not exist contract with dates defined by employee'))
        return super(hr_holidays, self).holidays_confirm(cr, uid, ids, context)
    
    def onchange_sec_id(self, cr, uid, ids, status, context=None):
        warning = {}
        double_validation = False
        obj_holiday_status = self.pool.get('hr.holidays.status')
        if status:
            holiday_status = obj_holiday_status.browse(cr, uid, status, context=context)
            double_validation = holiday_status.double_validation
            name= holiday_status.name
            if holiday_status.categ_id and holiday_status.categ_id.section_id and not holiday_status.categ_id.section_id.allow_unlink:
                warning = {
                    'title': "Warning for ",
                    'message': "You won\'t be able to cancel this leave request because the CRM Sales Team of the leave type disallows."
                }
        return {'warning': warning, 'value': {'double_validation': double_validation,'name':name}}

hr_holidays()

class hr_holidays_status(osv.osv):
    _inherit = "hr.holidays.status"

    _columns={
        'name': fields.char('Description', required=False, size=64),
        'is_paid':fields.boolean('Paid?'),
        'paid_cia': fields.float('% Paid for company'),
	}

    _defaults={
               'paid_cia':0.0,
               }
hr_holidays_status()

class hr_national_holidays(osv.osv):
    _name = 'hr.holidays.national'
    _columns = {
        'name': fields.char('Name', size=64),
        'date': fields.date('Holiday'),
        'shop_ids': fields.many2many('sale.shop','rel_holiday_shop','shop_id','holiday_id','Shops'),
    }
    _sql_constraints = [('name_unique','unique(name)','Holidays Name must be unique')]
    
hr_national_holidays()    
