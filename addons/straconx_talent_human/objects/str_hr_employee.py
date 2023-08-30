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

import string
import time
import netsvc
from datetime import date, datetime, timedelta
import re

#from mx import DateTime
import datetime

from osv import fields, osv
from tools import config
from tools.translate import _

class employee_health(osv.osv):
    _name = 'hr.employee.health'
    _columns = {
        'doctor':fields.char('Doctor', size=90),
        'name':fields.char('Subject', size=50),
        'message': fields.text('Description'),
        'date_revision': fields.datetime('Date'),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=False),
    }
    _defaults= {
        'date_revision':lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }
    _order = 'date_revision desc'
employee_health()

class employee_partner(osv.osv):
    _name = 'hr.employee.history'
    _columns = {
        'name':fields.char('Subject', size=50),
        'message': fields.text('Description'),
        'date_note': fields.datetime('Date'),
        'user_id': fields.many2one('res.users', 'User Responsible'),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=False),
        'state':fields.selection([('open','Open'),('close','Close'),('resolve','Resolve'),('pending','Pending'),('cancel','Cancel')],'Status'),
    }
    _defaults= {
        'date_note':lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda self, cr, uid, context: uid,
        'state':lambda *a:'open',
        }
    _order = 'date_note desc'
employee_partner()

# class hr_employee_substitute(osv.osv):
#     _name = 'hr.employee.substitute'
#     _columns = {
#         'employee_id':fields.many2one('hr.employee', 'Employee', required=False), 
#         'name':fields.char('Name', size=200, required=True,),
#         'birth_date': fields.date('Birth Date'),
#         'relationship':fields.selection([
#             ('child', 'Child'),
#             ('parent', 'Parent'),
#             ('brother', 'Brother'),
#             ('sister', 'Sister'),
#             ('grandchildren', 'Grandchildren'),
#             ('wife_husband', 'Wife/Husband'),
#             ('couple','Couple'),
#             ('other','Other'),
#             ], 'Relationship', select=True,),
#     }
# hr_employee_substitute()

class hr_employee(osv.osv):

    _inherit = 'hr.employee'

    def _current_employee_age(self,cr,uid,ids,field_name,arg,context):
        res = {}
        today = datetime.date.today()
        dob = today
        for employee in self.browse(cr, uid, ids):            
            if employee.birthday:
                dob = datetime.datetime.strptime(employee.birthday,'%Y-%m-%d')            
            res[employee.id] = today.year - dob.year
        return res
    
    def _get_data_employee(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for employee in self.browse(cr, uid, ids, context=context):
            res[employee.id]={'department_id':None,
                              'job_id':None}
            contract_active = self.pool.get('hr.contract').search(cr, uid, [('employee_id','=',employee.id),('contract_active','=',True)], limit=1)
            if contract_active:
                contract= self.pool.get('hr.contract').browse(cr, uid, contract_active[0], context)
                res[employee.id]['department_id']=contract.department_id.id or False
                res[employee.id]['job_id']=contract.job_id.id or False
                print employee.id 
                employee.write({'job_id': contract.job_id.id, 'department_id': contract.department_id.id})
                #cr.execute("""update hr_employee set write_date=now(), job_id = %s , department_id = %s where id = %s""",(contract.job_id.id,contract.department_id.id, employee.id))
        return res
    
    def _get_contract(self, cr, uid, ids, context=None):
        result = {}
        for contract in self.pool.get('hr.contract').browse(cr, uid, ids, context=context):
            result[contract.employee_id.id] = True
        return result.keys()
    
    def _get_shop(self, cr, uid, context=None):
        user=self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.shop_id and user.shop_id.id or None

    _columns = {
        'name1':fields.char('name', size=256),
        'partner_id': fields.many2one('res.partner', 'Partner', help="Partner that is related to the current employee. Accounting transaction will be written on this partner belongs to employee."),
        'vat': fields.related('partner_id', 'vat', string='R.U.C / CI', type='char', size=32, readonly=True, store=True),
        'child_ids':fields.one2many('hr.family.burden', 'employee_id', 'Family', ),
        'education_ids':fields.one2many('hr.education.level', 'employee_id', 'Childrens', ),
        'education_ids':fields.one2many('hr.education.level', 'employee_id', 'Childrens', ),
        'first_name':fields.char('First Name', size=255), 
        'second_name':fields.char('Second Name', size=255), 
        'last_name':fields.char('Last Name', size=255), 
        'mother_last_name':fields.char('Mother Last Name', size=255),
        'extension':fields.char('Extension', size=6), 
        'address_id': fields.many2one('res.partner.address', 'Working Address', domain=[('partner_id','=',1)]),
        'address_home_id': fields.many2one('res.partner.address','Home Address', size = 256),
        'home_phone':fields.char('Home Phone', size=10), 
        'home_mobile':fields.char('Home Mobile', size=10), 
        'personal_email': fields.char('Personal E-mail', size=240),
        'bbmesenger_id': fields.char('Blackberry Messenger ID', size=20),
        'inability': fields.boolean('Inability',help="Is a CONADIS Inability?"),
        'emergency_home_phone':fields.char('Emergency Home Phone', size=10), 
        'emergency_home_mobile':fields.char('Emergency Home Mobile', size=10),
        'location_id': fields.many2one('city.city', 'Location'),
        'work_location_region':fields.many2one('res.partner.address', 'Region'),
        'age': fields.function(_current_employee_age,method=True,string='Age',type='integer',store=True),
        'marital': fields.selection([('single', 'Single'), ('married', 'Married'), ('widower', 'Widower'), ('divorced', 'Divorced'),('union','Free Union')], 'Marital Status'),
        'employee_history_id': fields.one2many('hr.employee.history','employee_id','Employee History Notes'),
        'disability': fields.char('Disability', size=50), 
        'health_history_id': fields.one2many('hr.employee.health','employee_id','Employee Health History'),
        'unemployee': fields.boolean('Ex-Employee'),
        'substitute': fields.boolean('Substitute disability'),
        'substitute_id': fields.many2one('hr.family.burden', 'Substitute'),
        'shop_id': fields.many2one('sale.shop', 'Shop'),
        'department_id': fields.function(_get_data_employee, method=True, type='many2one', relation='hr.department', string='Department', readonly=False, multi="data",
                        store={
                               'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['contract_ids'], 5),
                               'hr.contract': (_get_contract, 'department_id', 6),}),
        'job_id': fields.function(_get_data_employee, method=True, type='many2one', relation='hr.job', string='Job', readonly=False, multi="data",
                        store={                        
                                'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['contract_ids'], 1),
                               'hr.contract': (_get_contract, 'job_id', 2),}),
        'parent_id': fields.related('department_id','manager_id', type='many2one', relation="hr.employee", string='Manager', readonly=True, store=True),
        }
    
    _defaults= {
        'shop_id':_get_shop,
        }
        
    def _check_recursion(self, cr, uid, ids, context=None):        
        return True
    
    _order = "name1 asc, last_name asc, mother_last_name asc, first_name asc, second_name asc"
    
    _sql_constraints = [('employee_uniq', 'unique(name1, partner_id)', 'A client can not be assigned twice as employee!'),
    ]
    
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Hierarchy of Employees.', ['parent_id']),
    ]

    def onchange_shop_id(self, cr, uid, ids, shop_id=False, context=None):
        values={}
        add_id = 0
        if shop_id:
            add_id= self.pool.get('sale.shop').browse(cr, uid, shop_id, context=context).partner_address_id.id
            values['address_id']=add_id
        return {'value':values} 
    
    def onchange_address_id(self, cr, uid, ids, address_id=False, context=None):
        values={}
        add_id = 0
        if address_id:
            shop_id= self.pool.get('sale.shop').search(cr, uid, [('partner_address_id','=',address_id)])
            values['shop_id']=shop_id[0]
        return {'value':values} 
            
    def onchange_name(self,cr,uid,ids,first_name='',second_name='',last_name='',mother_last_name='',context=None):
        values={}
        res = ''
        if last_name:
            res += last_name+' '
        if mother_last_name:
            res += mother_last_name+' '
        if first_name:
            res += first_name+' '
        if second_name:
            res += second_name+' '
        values['name']=res
        values['name1']=res
        return {'value':values}
    
    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('name' , False):
            vals['name1']=vals['name']
        if vals.get('department_id' , False):
            vals['department_id']=vals['department_id']
        if vals.get('job_id' , False):
            vals['job_id']=vals['job_id']            
        return super(hr_employee, self).write(cr, uid, ids, vals, context)

    def create(self, cr, uid, vals, context={}):
        if vals.get('name' , False):
            vals['name1']=vals['name']
        if vals.get('department_id' , False):
            vals['department_id']=vals['department_id']
        if vals.get('job_id' , False):
            vals['job_id']=vals['job_id']                        
        return super(hr_employee,self).create(cr, uid, vals, context)

    def onchange_partner(self, cr, uid, ids, partner_id, context=None):
        result={}
        if partner_id:
            employee = self.pool.get('hr.employee').search(cr,uid,[('partner_id','=',partner_id)])
            if employee:
                raise osv.except_osv(_('Invalid action !'), _('A client can not be assigned twice as employee!'))
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            if partner.type_vat not in ('ci','passport'):
                raise osv.except_osv(_('Invalid action !'), _('The partner need a ci or passport, ruc is not permited'))
            if not partner.employee:
                self.pool.get('res.partner').write(cr,uid,ids,{'employee':True})
            result['vat']= partner.vat
            result['bank_account_id']= partner.bank_ids and partner.bank_ids[0].id or None
            address_dict = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['default'])
            address_id = address_dict and address_dict['default'] or False
            if address_id:
                address=self.pool.get('res.partner.address').browse(cr, uid, address_id, context)
                result['address_home_id']= address_id
                result['personal_email']= address.email
                result['home_phone']= address.phone
                result['home_mobile']= address.mobile
                result['location_id']= address.location_id.id
        return {'value': result}

    def onchange_company(self, cr, uid, ids, company, context=None):
        domain={}
        result={}
        if company:
            company_id = self.pool.get('res.company').browse(cr, uid, company, context=context)
            domain['address_id']=[('partner_id','=',company_id.partner_id.id)]
            address = self.pool.get('res.partner').address_get(cr, uid, [company_id.partner_id.id], ['default'])
            address_id = address and address['default'] or False
            if address_id:
                address = self.pool.get('res.partner.address').browse(cr, uid, address_id, context)
                result = {'address_id' : address_id,
                          'work_email': address.email, 
                          'work_phone': address.phone, 
                          'mobile_phone': address.mobile}
        return {'value': result,'domain': domain}
    
    def onchange_user(self, cr, uid, ids, user_id, context=None):
        result=super(hr_employee, self).onchange_user(cr, uid, ids, user_id, context)
        if user_id:
            user=self.pool.get('res.users').browse(cr, uid, user_id, context)
            result['value']['company_id']=user.company_id.id
            result['value'].update(self.onchange_company(cr, uid, ids, user.company_id.id, context)['value'])
            if not user.partner_id:
                result['warning']={'title':_('No Partner found!'), 'message':_("The user has not a partner created, please selected one")}
            else:
                result['value']['partner_id']=user.partner_id.id
                result['value'].update(self.onchange_partner(cr, uid, ids, user.partner_id.id, context)['value'])
        return result
                                        
hr_employee()