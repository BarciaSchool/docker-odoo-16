##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A. and 
#    Ecuadorenlinea.net (<http://openerp.straconx.com - 
#    http://www.ecuadorenlinea.net>). All Rights Reserved
#    
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

from tools.safe_eval import safe_eval as eval

class hr_payslip_comision(osv.osv):
    _name = 'hr.sectorialcomission'
    _columns = {
        'code': fields.char('Code', size=4, required=True),
        'name': fields.char('Name', size=256, required=True),
        'branch': fields.char('Branch', size=256, required=True),
        'active': fields.boolean('Active')
    }
    _sql_constraints = [('code_uniq', 'unique(code)','The code of the Sectorial Comission must be unique !'),
                        ('name_uniq', 'unique(name)','The name of the Sectorial Comission must be unique !'),
                        ('branch_uniq', 'unique(branch)','The branch of the Sectorial Comission must be unique !'),
                        ]
    _defaults = {'active': lambda *a: True}
    
hr_payslip_comision()

class hr_payslip_tables(osv.osv):
    _name = 'hr.payslip.tables'
    _columns = {
        'sectorial_comission': fields.many2one('hr.sectorialcomission','Sectorial Comission', required=True),
        'code': fields.char('Code', size=4,required=True),
        'name': fields.char('Name', size=256, required=True),
        'basic_wages': fields.float('Basic Wage', digits=(16,2), help="Basic Wage"),
    }
    _sql_constraints = [('code_uniq', 'unique(code)','The code of the Sectorial Table must be unique !')]
hr_payslip_tables()

class hr_payslip_legal(osv.osv):
    _name = 'hr.legal.wages'
    _columns = {
		'name': fields.integer('Year'),        
        'basic_wages': fields.float('Basic Wage', digits_compute=dp.get_precision('Payroll'), help="Basic Wage"),
    }
    _sql_constraints = [('name_uniq', 'unique(name)','The code of the Legal Wages must be unique !'),
                        ('name_greater', 'check(name<2999)','Please enter a number into 1999 - 2999 !'),
                        ('name_lower', 'check(name>1999)','Please enter a number into 1999 - 2999 !'),
                        ]
    
    def onchange_wage(self, cr, uid, ids, name=False, wage=False, context=None):
        res={}
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        company_obj = self.pool.get('res.company')
        date = time.strftime('%Y-%m-%d')
        date = datetime.strptime(date[0:10],"%Y-%m-%d")
        year = date.year
        if name == year:
            company_obj.write(cr, uid, [company], {'basic_salary':wage}, context=context)
        return res
    
hr_payslip_legal()
