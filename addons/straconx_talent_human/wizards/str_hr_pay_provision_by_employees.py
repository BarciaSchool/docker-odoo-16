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

from osv import fields, osv
import tools
from tools.translate import _
from tools.safe_eval import safe_eval as eval

class hr_pay_provision_employees(osv.osv_memory):

    _name ='hr.pay.provision.employees'
    
    _columns = {
        "company_id":fields.many2one('res.company','Company'),       
        "employee_ids": fields.many2many('hr.employee', 'hr_employee_group_rel1', 'payslip_id', 'employee_id', 'Employees'),
    }      
    def compute_sheet(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        pay_line_pool = self.pool.get('hr.pay.provision.line')
        res= {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
#         if not data['employee_ids']:
#             raise osv.except_osv(_("Warning !"), _("You must select employee(s) to generate pay provision"))
        if not objs.provision_id.account_id:
            raise osv.except_osv(_("Warning !"), _("You must select account on the type of provision to pay"))
        for emp in emp_pool.browse(cr, uid, data['employee_ids'], context=context):
            line_ant_ids=pay_line_pool.search(cr, uid, [('pay_provision_id','=',objs.id),('employee_id','=',emp.id)])
            if line_ant_ids:
                continue
#            for line in objs.line_ids:
#                if emp.id == line.employee_id.id:
#                    raise osv.except_osv(_('Warning !'), _('The employee(s) selected already assigned'))
            if not emp.partner_id:
                raise osv.except_osv(_('Error'), _(('the employee %s does not have a partner created')% (emp.name)))
            contract_ids = slip_pool.get_contract(cr, uid, emp, objs.date_from, objs.date_to, context=context)
            sql='''SELECT am.id 
                FROM account_move_line AS am, account_account AS a
                WHERE am.account_id = a.id AND am.partner_id = %s 
                AND am.credit > 0 AND am.reconcile_id is Null 
                AND a.type='other' AND am.state = 'valid' 
                AND am.date >= %s AND am.date<= %s AND am.account_id=%s'''
            cr.execute(sql,(emp.partner_id.id,objs.date_from,objs.date_to,objs.provision_id.account_id.id))
            atts = cr.fetchall()
            if not atts:
                raise osv.except_osv(_('Error'), _(('Ya fue pagada la provision del empleado %s ')% (emp.name)))
            if atts:
                res = {
                    'employee_id': emp.id,
                    'contract_id':contract_ids and contract_ids[0] or False,
                    'pay_provision_id':objs.id,
                    'move_line_ids':[[6, 0, [c[0] for c in atts]]]
                }
                pay_line_pool.create(cr, uid, res, context)
        return {'type': 'ir.actions.act_window_close'}

hr_pay_provision_employees()


class hr_provision_advance_employees(osv.osv_memory):

    _name ='hr.provision.advance.employees'
    
    _columns = {
        "company_id":fields.many2one('res.company','Company'),       
        "employee_ids": fields.many2many('hr.employee', 'hr_employee_group_rel2', 'payslip_id', 'employee_id', 'Employees'),
    } 
    
    def compute_sheet_advance(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        pay_line_pool = self.pool.get('hr.provision.advance.line')
        res= {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
#         if not data['employee_ids']:
#             raise osv.except_osv(_("Warning !"), _("You must select employee(s) to generate pay provision"))
        if not objs.adv_provision_id.account_id:
            raise osv.except_osv(_("Warning !"), _("You must select account on the type of provision to pay"))
        for emp in emp_pool.browse(cr, uid, data['employee_ids'], context=context):
            line_ant_ids=pay_line_pool.search(cr, uid, [('provision_advance_id','=',objs.id),('employee_id','=',emp.id)])
            if line_ant_ids:
                continue
#            for line in objs.line_ids:
#                if emp.id == line.employee_id.id:
#                    raise osv.except_osv(_('Warning !'), _('The employee(s) selected already assigned'))
            if not emp.partner_id:
                raise osv.except_osv(_('Error'), _(('the employee %s does not have a partner created')% (emp.name)))
            contract_ids = slip_pool.get_contract(cr, uid, emp, objs.date_from, objs.date_to, context=context)
            sql='''SELECT am.id 
                FROM account_move_line AS am, account_account AS a
                WHERE am.account_id = a.id AND am.partner_id = %s 
                AND am.credit > 0 AND am.reconcile_id is Null 
                AND a.type='other' AND am.state = 'valid' 
                AND am.date >= %s AND am.date<= %s AND am.account_id=%s 
                group by am.date, am.id'''
            cr.execute(sql,(emp.partner_id.id,objs.date_from,objs.date_to,objs.adv_provision_id.account_id.id))
            atts = cr.fetchall()
            if atts:
                res = {
                    'employee_id': emp.id,
                    'contract_id':contract_ids and contract_ids[0] or False,
                    'provision_advance_id':objs.id,
                    'move_line_ids':[[6, 0, [c[0] for c in atts]]]
                }
                pay_line_pool.create(cr, uid, res, context)
        return {'type': 'ir.actions.act_window_close'}

hr_provision_advance_employees()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: