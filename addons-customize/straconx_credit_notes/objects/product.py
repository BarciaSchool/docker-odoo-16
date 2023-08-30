
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
from tools.translate import _

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'property_account_refund_sale': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Refund Customer Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value refund sales for the current product"),
        'property_account_refund_purchase': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Refund Supplier Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value refund purchase for the current product"),
        'property_account_discount_sale': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Discount Customer Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value discount sales for the current product"),
        'property_account_discount_purchase': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Discount Supplier Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value discount purchases for the current product"),
    }

product_template()

class product_category(osv.osv):
    _inherit = 'product.category'
    _columns ={
        'permit_refund':fields.boolean('Permit refund', required=False),
        'property_account_refund_sale_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Refund Customer Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value refund sales for the current product category"),
        'property_account_refund_purchase_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Refund Supplier Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value refund purchase for the current product category"),
        'property_account_discount_sale_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Discount Customer Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value discount sales for the current product category"),
        'property_account_discount_purchase_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Discount Supplier Account",
            method=True,
            view_load=True,
            help="This account will be used for invoices to value discount purchases for the current product category"),
    }
    _defaults = {'permit_refund':True}
product_category()