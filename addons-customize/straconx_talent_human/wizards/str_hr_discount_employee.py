# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.

##############################################################################

from datetime import datetime
from dateutil import relativedelta
from osv import fields, osv
from tools.translate import _

class hr_discount_employees(osv.osv_memory):

    _name ='hr.discount.employees'
    _description = 'Generate discount lines for all selected employees'
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'hr_employee_discount_rel', 'discount_id', 'employee_id', 'Employees'),
    }
    
    def compute_sheet(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        discount = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
        self.pool.get('hr.contract.expense').search(cr,uid,[('name','=',discount)])
        
        if not data['employee_ids']:
            raise osv.except_osv(_("Warning !"), _("You must select employee(s) to generate payslip(s)"))
        if discount.number_of_quotas > 0:
            b = discount.quotas_paid
            day_from=datetime.strptime(discount.date_from,'%Y-%m-%d')
            flag=True
            if day_from.day >15:
                flag=False
            while b < discount.number_of_quotas:            
                b += 1
                if discount.collection_form == 'middle_month':
                    if not flag:
                        day_from = day_from + relativedelta.relativedelta(months=int(1), day=15)
                    else:
                        day_from = day_from + relativedelta.relativedelta(day=15)
                        flag=False
                    discount_date = day_from.strftime('%Y-%m-%d')
                elif discount.collection_form == 'end_month':
                    day_from = day_from + relativedelta.relativedelta(months=int(1), day=1, days=-1)
                    discount_date = day_from.strftime('%Y-%m-%d')
                    day_from= day_from + relativedelta.relativedelta(months=1)
                else:
                    if not flag:
                        flag=True
                        day_from = day_from + relativedelta.relativedelta(months=int(1), day=1, days=-1)
                        discount_date = day_from.strftime('%Y-%m-%d')
                        day_from= day_from + relativedelta.relativedelta(months=1)
                    else:
                        flag=False
                        day_from = day_from + relativedelta.relativedelta(day=15)
                        discount_date = day_from.strftime('%Y-%m-%d')
                for emp in emp_pool.browse(cr, uid, data['employee_ids'], context=context):
                    for line in discount.lines_ids:
                        if emp.id == line.employee_id.id:
                            continue
                    self.pool.get('hr.discount.lines').create(cr, uid, {
                                                'state':'draft',
                                                'name': _('%s - %s (%s quota)') % (discount.name.name, discount.ref, b),
#                                                'name':discount.name.name +' - '+discount.ref,
                                                'date':discount_date,
                                                'amount':0,
                                                'discount_id':discount.id,
                                                'employee_id': emp.id,
                                                'number_quota':b,
                                                })
        return {'type': 'ir.actions.act_window_close'}

hr_discount_employees()
