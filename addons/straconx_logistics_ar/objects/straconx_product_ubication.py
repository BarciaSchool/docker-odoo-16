# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011- present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp


class stock_location(osv.osv):
    _inherit = 'stock.location'
    _columns = {
        'location_ids':fields.one2many('ubication', 'location_id', 'Locations', required=False),
        'valuation_in_account_id': fields.many2one('account.account', 'Stock Valuation Account (Incoming)', domain = [('type','=','stock')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved from an internal location "
                                                        "into this location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
        'valuation_out_account_id': fields.many2one('account.account', 'Stock Valuation Account (Outgoing)', domain = [('type','=','stock')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved out of this location "
                                                        "and into an internal location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),

    }

    def name_get(self, cr, uid, ids, context=None):
        return super(osv.osv,self).name_get(cr,uid,ids,context)         

stock_location()

class ubication(osv.osv):
    _name = "ubication"
    _description = "Ubications"
    
    def _get_product_ubication(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('product.ubication').browse(cr, uid, ids, context=context):
            if line.product_id.height <= 0  and line.product_id.width <= 0 and line.product_id.long <= 0:
                raise osv.except_osv('Error!', _("the products need a height, width and long greater to 0 "))
            else:
                result[line.ubication_id.id] = True
        return result.keys()

    def _get_product(self, cr, uid, ids, context=None):
        result = {}
        try:
            for product in self.pool.get('product.product').browse(cr, uid, ids, context=context):
                for ubication in product.ubication_ids:
                    result[ubication.ubication_id.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()
            
    _columns = {
    'name': fields.char('Address', size=20, help='Ubication: location+ rack + row + case'),
    'location_id': fields.many2one('stock.location', 'Ubication'),
    'shop_ubication_id': fields.related('location_id','location_id', type='many2one', relation='stock.location', string='Shop location', store=True),    
    'height': fields.float('Height'),
    'width': fields.float('Width'),
    'long_ubication': fields.float('Long'),    
    'product_ids':fields.one2many('product.ubication', 'ubication_id', 'Products', required=False),
    }

    _sql_constraints = [
        ('height_greater_0', 'CHECK (height>0)', 'Error! Height must be greater than 0.'),
        ('width_greater_0', 'CHECK (width>0)', 'Error! Width must be greater than 0.'),
        ('long_greater_0', 'CHECK (long_ubication>0)', 'Error! Long must be greater than 0.'),
        ('name_unique', 'unique(name,location_id)','Error! Ubications name are uniques'),
    ]

    def onchange_shop_location(self, cr, uid, ids, location_id=None, context=None):
        values={}
        if location_id:
            shop_ubication_id = self.pool.get('stock.location').browse(cr,uid,location_id).location_id.id
            values['shop_ubication_id']=shop_ubication_id

        return {'value': values}
    
    _order = 'name asc, location_id asc, name asc'

#    _defaults = {'shop_ubication_id':_get_shop_location}

ubication()

class product_ubication(osv.osv):
    _name = "product.ubication"
                
    def get_product(self, cr, uid, ids, context=None):
        result = {}
        try:
            for product in self.pool.get('product.product').browse(cr, uid, ids, context=context):
                for ubication in product.ubication_ids:
                    result[ubication.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()
    
    def _get_product(self, cr, uid, ids, context=None):
        return self.pool.get('product.ubication').get_product(cr, uid, ids, context)
    
    def get_ubication(self, cr, uid, ids, context=None):
        result = {}
        try:
            for ubication in self.pool.get('ubication').browse(cr, uid, ids, context=context):
                for ub in ubication.product_ids:
                    result[ub.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()
    
    def _get_ubication(self, cr, uid, ids, context=None):
        return self.pool.get('product.ubication').get_ubication(cr, uid, ids, context)

    def get_product_qty(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for pubication in self.browse(cr, uid, ids, context=context):
            qty=0
            context.update({'location':pubication.ubication_id.location_id.id,
                            'states': ('done',),
                            'ubication_id':pubication.ubication_id.id,
                            'what': ('in', 'out')})
            if not pubication.product_id:
                self.unlink(cr, uid, [pubication.id], context)
                continue
            qty=self.pool.get('product.product').get_product_available(cr, uid, [pubication.product_id.id],context)[pubication.product_id.id]
            res[pubication.id] = qty
        return res

    def _get_product_qty(self, cr, uid, ids, field_name, arg, context=None):
        return self.pool.get("product.ubication").get_product_qty(cr, uid, ids, field_name, arg, context)
    
    def _get_categ_id(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for obj in self.browse(cr, uid, ids):
                if obj.product_id:
                    product_obj=self.pool.get('product.product').browse(cr,uid,obj.product_id.id)
                    res[obj.id] = product_obj.categ_id and product_obj.categ_id.id or False
                else:
                    res[obj.id] = None
            return res

    def _get_codant(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for obj in self.browse(cr, uid, ids):
                if obj.product_id.codant:
                    res[obj.id] = obj.product_id.codant
                else:
                    res[obj.id] = ''
            return res

    _columns = {
    'ubication_id':fields.many2one('ubication', 'Ubication', required=False, ondelete='cascade'),
    'name': fields.related('ubication_id','name',type="char",string="Name"),
    'product_id':fields.many2one('product.product', 'Product', required=False, ondelete='cascade'),
    'codant':fields.related('product_id','codant', type='char', string='CodAnt',readonly=True),
    'location_ubication_id': fields.related('ubication_id','location_id', type='many2one', relation='stock.location', string='Location', readonly=True, store=True),
    'shop_ubication_id': fields.related('location_ubication_id','location_id', type='many2one', relation='stock.location', string='Shop location', store=True),    
    'default_code':fields.related('product_id','default_code', type='char', string='Ref.',readonly=True),
    'categ_id': fields.function(_get_categ_id,obj="product.category", method=True, type="many2one", string='Category',
                                store={'product.ubication': (lambda self, cr, uid, ids, c={}: ids, ['product_id'], 1),
                                       'product.product': (_get_product, None, 1)
                                       }),
    'qty': fields.function(_get_product_qty, method=True, type='float', string='Qty Product',
                           store={'product.ubication': (lambda self, cr, uid, ids, c={}: ids, None, 1),
                                  'product.product': (_get_product, None, 2),
                                  'ubication': (_get_ubication, None, 3),                                  
                                       }),    }
    
    _defaults = {'qty': lambda *a: 0,
                 }

    _sql_constraints = [('ubication_product_uniq','unique(ubication_id,product_id)', 'This product already exists in this ubication, please check')]
     
    def onchange_ubication(self, cr, uid, ids, ubication=None, context=None):
        values={}
        if ubication:
            values['ubication_id']=ubication
        return {'value': values}
    
    def onchange_product(self, cr, uid, ids, product=None, context=None):
        values={}
        if product:
            values['product_id']=product
        return {'value': values}
     
product_ubication()
