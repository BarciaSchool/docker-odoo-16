# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 STRACONX S.A. (<http://openerp.straconx.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from osv import fields, osv

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
            'schedule_pay': fields.selection([
#                ('daily', 'Daily'),
#                ('weekly', 'Weekly'),
                ('bi-monthly', 'Bi-monthly'),
                ('monthly', 'Monthly'),
                ], 'Scheduled Pay', select=True),
            'pay_bi_monthly': fields.float('% Pay Bi-monthly'),
            'basic_salary': fields.float('Basic Salary'),
            'property_account_employee_receivable': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Employee Credit Account',
                method=True,
                view_load=True,
                domain="[('type','=','receivable')]",),                
            }
    _defaults = {
        'schedule_pay': 'monthly',
    }

res_company()


class sale_shop(osv.osv):
    
    _inherit = 'sale.shop'
    _columns = {
                'city':fields.related('partner_address_id','city',type='char', string="City"),
                }
    
sale_shop()
