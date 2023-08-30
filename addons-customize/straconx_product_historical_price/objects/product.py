#!/usr/bin/python
# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) OpenERP Venezuela (<http://openerp.com.ve>).
#    All Rights Reserved
###############Credits######################################################
#    Coded by: Vauxoo C.A.           
#    Planified by: Nhomar Hernandez
#    Audited by: Vauxoo C.A.
#############################################################################
#   Modifications by: STRACONX S.A.
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
################################################################################
from osv import osv
from osv import fields
from tools.translate import _
import decimal_precision as dp
import pooler
import time
import math

class product_product(osv.osv):
    """
    product_historical
    """
    def _get_historical_price(self, cr, uid, ids, field_name, field_value, arg, context={}):
        res = {}
        product_hist = self.pool.get('product.historic.price')
        for id in ids:
            if self.browse(cr, uid, id).list_price != self.browse(cr, uid, id).list_price_historical:
                res[id] = self.browse(cr, uid, id).list_price
                product_hist.create(cr, uid, {
                    'product_id' : id,
                    'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': self.browse(cr, uid, id).list_price,
                    'p_net': self.browse(cr, uid, id).p_net,
                    'product_uom':self.browse(cr, uid, id).uom_id.id,
                    'margin_prod': self.browse(cr, uid, id).margin_prod,
                    'user_id':uid,
               },context)
        return res
    
    def _get_historical_cost(self, cr, uid, ids, field_name, field_value, arg, context={}):
        res = {}
        product_hist = self.pool.get('product.historic.cost')
        for id in ids:
            if self.browse(cr, uid, id).standard_price != self.browse(cr, uid, id).cost_historical:
                res[id] = self.browse(cr, uid, id).standard_price
                product_hist.create(cr, uid, {
                    'product_id' : id,
                    'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': self.browse(cr, uid, id).standard_price,
                    'user_id':uid,
               },context)
        return res
    
    _inherit = 'product.product'
    _columns = {
        'list_price_historical': fields.function(_get_historical_price, method=True, string='Latest Price', type='float',digits_compute= dp.get_precision('List_Price_Historical'),
            store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['list_price'], 50),}, 
            help="Latest Recorded Historical Value"),
        'list_price_historical_ids': fields.one2many('product.historic.price','product_id','Historical Prices'),
        'cost_historical': fields.function(_get_historical_cost, method=True, string=' Latest Cost', type='float',digits_compute= dp.get_precision('Cost_Historical'),
            store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['standard_price'], 50),}, 
            help="Latest Recorded Historical Cost"),
        'cost_historical_ids': fields.one2many('product.historic.cost','product_id','Historical Prices'),
        
    }
        
    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        unlink_product_tmpl_ids = []
        tmp_id = False
        product_historic_price_obj= self.pool.get('product.historic.price')
        product_historic_cost_obj= self.pool.get('product.historic.cost')
        for product in self.browse(cr,uid,ids):
            if product.product_tmpl_id:
                tmpl_id = product.product_tmpl_id.id
            else:
                tmp_id = False
            inv_search = product_historic_price_obj.search(cr,uid,[('product_id','=',product.id)])
            stk_search = product_historic_cost_obj.search(cr,uid,[('product_id','=',product.id)])
            if len(inv_search)<=1 and len(stk_search)<=1:
                product_historic_price_obj.unlink(cr, uid, inv_search, context=context)
                product_historic_cost_obj.unlink(cr,uid,stk_search,context=context)
                if tmp_id:
                    unlink_product_tmpl_ids.append(tmpl_id)
                    unlink_ids.append(product.id)
                    self.pool.get('product.template').unlink(cr, uid, unlink_product_tmpl_ids, context=context)
        if not unlink_ids:
            unlink_ids = ids        
        return super(product_product, self).unlink(cr, uid, unlink_ids, context=context)
            
product_product()

class product_historic_price(osv.osv):
    _order= "name desc"
    _name = "product.historic.price"
    _description = "Historical Price List"

    _columns = {
        'product_id': fields.many2one('product.product',string='Product related to this Price', required=True),
        'name': fields.datetime(string='Date',  required=True),
        'price': fields.float(string='Precio Bruto',digits_compute= dp.get_precision('Price')),
        'p_net': fields.float(string='Precio Neto',digits_compute= dp.get_precision('Price')),
        'margin': fields.float(string='% Margen',digits_compute= dp.get_precision('Price')),
        'product_uom': fields.many2one('product.uom', string="Supplier UoM", help="Choose here the Unit of Measure in which the prices and quantities are expressed below."),
        'user_id': fields.many2one('res.users', 'User'),        
    }
    _defaults = { 'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                  'user_id': lambda obj, cr, uid, context: uid,
    }

product_historic_price()

class product_historic_cost(osv.osv):
    _order= "name desc" 
    _name = "product.historic.cost"
    _description = "Historical Price List"

    _columns = {
        'product_id': fields.many2one('product.product', string='Product related to this Cost', required=True),
        'name': fields.datetime(string='Date', required=True),
        'price': fields.float(string='Cost', digits_compute= dp.get_precision('Costo')),
        'product_uom': fields.many2one('product.uom', string="Supplier UoM", help="Choose here the Unit of Measure in which the prices and quantities are expressed below."),
        'user_id': fields.many2one('res.users', 'User'),                
    }
    _defaults = {'name': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
                 'user_id': lambda obj, cr, uid, context: uid, 
    }
product_historic_cost()
