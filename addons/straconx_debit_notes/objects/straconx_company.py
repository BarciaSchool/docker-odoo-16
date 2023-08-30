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
            'property_account_advance_customer': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Advance Account Customer',
                method=True,
                view_load=True,
                domain="[('type', '=', 'payable')]",),
            'property_account_advance_supplier': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Advance Account Supplier',
                method=True,
                view_load=True,
                domain="[('type', '=', 'receivable')]",),
            }

res_company()