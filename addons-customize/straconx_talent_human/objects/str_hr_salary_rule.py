# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
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

class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    _columns = {
        'calculate_wage':fields.boolean('calculate Wage', required=False),
        'is_provision':fields.boolean('Is Provision', required=False),
        'generate_move':fields.boolean('Generate Move Account', required=False, help="check this field if your rule generate lines move account in the move account"),
        'company_id':fields.many2one('res.company','Company'),
        'multi':fields.boolean('Required Account x Area'),
        'account_ids': fields.one2many('hr.account.position','rule_id','Account x Area'),
        }
    
    _default={
              'generate_move':True,
              'multi':False
              }
    _order = 'category_id asc, sequence asc'


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        payslip_obj = self.pool.get('hr.payslip.line')
        payslip_search = payslip_obj.search(cr,uid,[('salary_rule_id','in',ids)])
        unlink_ids = []
        if payslip_search:            
            raise osv.except_osv(_('Invalid action !'), _('No se pueden borrar reglas salariales que tengan Nóminas generadas'))
        else:
            for i in self.browse(cr,uid,ids):
                unlink_ids.append(i.id)        
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True

hr_salary_rule()

class hr_salary_rule_category(osv.osv):
    _inherit = 'hr.salary.rule.category'
    _columns = {
                'account_id':fields.many2one('account.account', 'Account', help="This field is to reconcile the accounts discount"),
        }
hr_salary_rule_category()