#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

import netsvc
from osv import fields, osv
import tools
from tools.translate import _
import decimal_precision as dp
from openerp.addons.hr_payroll.hr_payroll import hr_payslip

class straconx_budgets_payroll(osv.osv):
    
    _name = 'straconx.budgets.payroll'
    
    _columns = {
            'project_id':fields.many2one('account.analytic.journal', 'Proyecto', required=False),
            'percentage': fields.float('Porcentaje'),
            'period_id':fields.many2one('account.period', 'Mes de arranque', readonly=False),
            'wbs_phase_id':fields.many2one('account.analytic.phase', 'Subfase/Tarea', required=False),
            'analytic_id':fields.many2one('account.analytic.account', 'Cuenta Analitica', required=False),
            'desde':fields.many2one('hr.period', 'Desde', required=False),
            'hasta':fields.many2one('hr.period', 'Hasta', required=False),    
            'state':fields.selection([('active','Activo'),('inactive','Inactivo'),],'Estado',readonly=False,),
                    }
    
    _defaults = {  
        'state': 'active',  
        'period_id': lambda self, cr, uid, context: self.pool.get('account.period').search(cr, uid,
                                                                           [('date_start', '<=', time.strftime('%Y-%m-%d')),
                                                                            ('date_stop', '>=', time.strftime('%Y-%m-%d'))])[0]
        }
    

    def create(self, cr, uid, vals, context=None):
        if (vals.get('desde') and vals.get('hasta')):
            desde = self.pool.get('hr.period').browse(cr, uid, vals.get('desde'))
            hasta = self.pool.get('hr.period').browse(cr, uid, vals.get('hasta'))
            if desde.date_start > hasta.date_start:
                raise osv.except_osv(_('Acción Inválida!'), _('El período de inicio debe ser menor que el período de fin.'))
        return super(straconx_budgets_payroll, self).create(cr, uid, vals, context)

straconx_budgets_payroll()


class straconx_hr_contract(osv.osv):
    _inherit = 'hr.contract' 
    #Do not touch _name it must be same as _inherit
    
    def _check_percentage(self,cr,uid,ids):
        b=True
        s=0.00
        for contract in self.browse(cr, uid, ids):
            if contract.budgets_ids:
                for bud_id in contract.budgets_ids:
                    s+=bud_id.percentage
                if s > 100:
                    b=False
        return b
    
    _columns = {
            'budgets_ids':fields.many2many('straconx.budgets.payroll','budgets_contracts_rel','contract_id','budgets_id','Proyectos'), 
                    }
    _constraints = [(_check_percentage,'El porcentaje de participación es mayor a 100',['percentage'])]
straconx_hr_contract()

class straconx_hr_payslip(osv.osv):
    _inherit = 'hr.payslip' 
    #Do not touch _name it must be same as _inherit
    #_name = 'hr.payslip'
    
    def process_sheet(self, cr, uid, ids, context=None):
        res={}
        context= {'payslip_id': ids[0]}
        res = super(straconx_hr_payslip, self).process_sheet(cr, uid, ids, context)
        return True
    
    
    def create_move_line_payslip(self, cr, uid, line, partner, name, date, account, journal, period,amount, move_ids, reference, company_id, l_discount_id, analytic_account_id, shop_id, department_id, cost_journal, context=None):
        res={}
        analytic_account_id = None
        value = 0.00
        debit = 0.00
        credit = 0.00
        wbs_phase = False
        acc_acc_obj = self.pool.get('account.account')        
        #res.update({'wbs_phase': order_line.wbs_phase.id})
        ids= context.get('payslip_id',False)
        payslip_id = self.browse(cr,uid,ids)
        if account:
            analytic_id = acc_acc_obj.browse(cr,uid,account)
            if analytic_id and analytic_id.user_type.code == 'expense':
                if payslip_id.contract_id.budgets_ids:
                    for project in payslip_id.contract_id.budgets_ids:
                        if project.desde.date_start <= payslip_id.period_payment.date_start:
                            if not project.hasta or (project.hasta.date_start >= payslip_id.period_payment.date_start):        
                                value = (amount*project.percentage)/100
                                analytic_account_id = project.analytic_id.id
                                cost_journal= project.project_id.id
                                wbs_phase =project.wbs_phase_id.id
                                res = super(straconx_hr_payslip, self).create_move_line_payslip(cr, uid, line, partner, name, date, account, journal, period,value, move_ids, reference, company_id, l_discount_id, analytic_account_id, shop_id, department_id, cost_journal, context)
                                move_ids = int(move_ids)
                                cr.execute("""SELECT MAX(id) FROM account_move_line where move_id = %s""", (move_ids,))                             
                                line_id = cr.fetchall()
                                cr.execute("""UPDATE account_move_line set wbs_phase = %s where id = %s""",(wbs_phase,line_id[0][0]))
                                if context.get('adjust_credit',False):
                                    debit=0.0
                                    credit=amount
                                if context.get('adjust_debit',False):
                                    debit=amount
                                    credit=0.0
                                if context.get('debit',False):
                                    debit=amount > 0.0 and amount or 0.0
                                    credit=amount < 0.0 and -amount or 0.0
                                if context.get('credit',False):
                                    debit=amount < 0.0 and -amount or 0.0
                                    credit=amount > 0.0 and amount or 0.0 
                                res.update({'credit':credit, 'debit':debit})
                else:
                    res = super(straconx_hr_payslip, self).create_move_line_payslip(cr, uid, line, partner, name, date, account, journal, period,amount, move_ids, reference, company_id, l_discount_id, analytic_account_id, shop_id, department_id, cost_journal, context)                
            else:
                res = super(straconx_hr_payslip, self).create_move_line_payslip(cr, uid, line, partner, name, date, account, journal, period,amount, move_ids, reference, company_id, l_discount_id, analytic_account_id, shop_id, department_id, cost_journal, context)                               
        
        return res
straconx_hr_payslip()