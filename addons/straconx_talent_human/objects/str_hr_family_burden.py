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
import netsvc
from datetime import date, datetime, timedelta

from osv import fields, osv
from tools import config
from tools.translate import _

class hr_family_burden(osv.osv):
    
    def _current_age(self,cr,uid,ids,field_name,arg,context):
        res = {}
        today = datetime.today()
        dob = today
        age = 0        
        for family_burden in self.browse(cr, uid, ids):
            if family_burden.birth_date:
                dob = datetime.strptime(family_burden.birth_date,'%Y-%m-%d')            
                age = today.year - dob.year
            res[family_burden.id]= age            
        return res

    def _current_bonus(self,cr,uid,ids,field_name,arg,context):
        res = {}
        bonus=True
        today = datetime.today()
        dob = today
        for family_burden in self.browse(cr, uid, ids):
            if family_burden.relationship not in ('child','wife_husband','couple'):
                bonus = False
            if family_burden.birth_date:
                dob = datetime.strptime(family_burden.birth_date,'%Y-%m-%d')            
                age = today.year - dob.year
                if age >18 and family_burden.is_inhab == False and family_burden.relationship not in ('wife_husband','couple'):
                    bonus = False 
                else:
                    bonus = True
            res[family_burden.id]= bonus            
        return res

    _name = 'hr.family.burden' 
    _columns = {    
                    'employee_id':fields.many2one('hr.employee', 'Employee', required=False), 
                    'name':fields.char('Name', size=200, required=True,),
                    'last_name':fields.char('Last Name', size=200, required=True,),
                    'birth_date': fields.date('Birth Date', required=False,),
                    'relationship':fields.selection([
                        ('child', 'Child'),
                        ('wife_husband', 'Wife/Husband'),
                        ('parent', 'Parent'),
                        ('couple','Couple'),
                        ('other','Other'),
                        ('grandchildren', 'Grandchildren'),
                        ], 'Relationship', select=True,),
                    'age' : fields.function(_current_age,method=True,string='Age',type='integer',store=True),
                    'working':fields.boolean('Work?'),
                    'email_personal':fields.char('Personal Email', size=200),
                    'work_place':fields.char('Work Place', size=200),
                    'work_address':fields.char('Work Address', size=200),
                    'work_phone':fields.char('Work Phone', size=10 ),
                    'cell_phone':fields.char('Cell Phone', size=10),
                    'bonus' : fields.function(_current_bonus,method=True,string='Bonus',type='boolean',store=True),
                    #'bonus':fields.boolean('Bonus?'),
                    'is_inhab':fields.boolean('inability?'),
                    }
hr_family_burden()
