# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
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

class res_company(osv.osv):
    _inherit = "res.company"
    
    _columns = {
        'property_discount_sales': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Sales Discount Account',
                method=True,
                view_load=True,
                domain="[('type', '=', 'other')]",),
        'property_discount_purchase': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Purchase Discount Account',
                method=True,
                view_load=True,
                domain="[('type', '=', 'other')]",),
        'property_rounding_difference': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Diferencias por Redondeo',
                method=True,
                view_load=True,
                domain="[('type', '=', 'other')]",),
        'property_analytic_account': fields.property( 
                'account.analytic.account',
                type='many2one',
                relation='account.analytic.account',
                string='Default Analytic Account',
                method=True,
                view_load=True),
        'pricelist': fields.boolean('Use list_price', help='If is check, price for product is based in listprice, otherwise, price is based in product form'),
        'amount_cc': fields.float('Monto máximo de compra de Consumidor Final'),
        'required_analytic': fields.boolean('Analytic Account required', help='If is check, you can active a analytic account'),            
    }
    
    _defaults = {
        'amount_cc': 200.00         
                 }
res_company()