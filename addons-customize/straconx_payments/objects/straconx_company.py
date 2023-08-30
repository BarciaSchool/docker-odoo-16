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
            'property_account_commission_credit_card': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Credit Card Commission Account',
                method=True,
                view_load=True,
                domain="[('type', '=', 'other')]",),
            'property_tax_vat_product_00': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de IVA base 0%',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'vat'),('type_tax_use','=','purchase'),('amount','=',0)]",),  
            'property_tax_vat_product_12': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de IVA base 12%',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'vat'),('type_tax_use','=','purchase'),('amount','!=',12)]",),  
            'property_tax_withhold_product': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de Retención en la Fuente para Compras',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'withhold'),('type_tax_use','=','purchase')]",),
            'property_tax_withhold_vat_product': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de Retención de IVA para Compras',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'withhold_vat'),('type_tax_use','=','purchase')]",),            
            'property_tax_position_partners': fields.property( 
                'sri.tax.sustent',
                type='many2one',
                relation='sri.tax.sustent',
                string='Sustento Predeterminado de las Empresas',
                method=True,
                view_load=True,),
            'property_account_customer_withhold': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de Retención en la Fuente para Ventas',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'withhold'),('type_tax_use','=','sale')]",),
            'property_account_customer_withhold_vat': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de Retención de IVA para Ventas',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'withhold_vat'),('type_tax_use','=','sale')]",),
            'partner_id_taxes': fields.many2one('res.partner','Taxes Partner'),                
            'property_tax_payment_isd': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Cuenta por Pagar ISD',
                method=True,
                view_load=True),                  
            }

res_company()
