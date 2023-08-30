# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2012 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
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
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from itertools import groupby
import tools
import logging


class many2manysym(fields.many2many):

    def get(self, cr, obj, ids, name, user=None, offset=0, context={}, values={}):
        res = {}
        if not ids:
            return res
        ids_s = ','.join(map(str, ids))
        for id in ids:
            res[id] = []
        limit_str = self._limit is not None and ' limit %d' % self._limit or ''

        for (self._id2, self._id1) in [(self._id2, self._id1), (self._id1, self._id2)]:
            cr.execute('select '+self._id2+','+self._id1+' from '+self._rel+' where '+self._id1+' in ('+ids_s+')'+limit_str+' offset %s', (offset,))
            for r in cr.fetchall():
                res[r[1]].append(r[0])
        return res

# Product Application
class productapplication(osv.osv):
    _name = 'product.application'
    _description = "product.application"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=6,),
    }

    _sql_constraints = [
        ('code_uniq', 'unique(name)','The code of the application must be unique !')
    ]

productapplication()

# Product Model
class product_applicationmodel(osv.osv):
    _name = 'product.applicationmodel'
    _description = "product.applicationmodel"
    _columns = {
        'name': fields.char('Model', size=64, required=True),
        'code': fields.char('Code', size=15,),
        'parent_id': fields.many2one('product.applicationmodel','Brand', help='Name of the parent category'),
        'active': fields.boolean('Active'),
    }

    _defaults = {'active': lambda *a: True}

    _sql_constraints = [
        ('code_uniq', 'unique (name)','The code of the application must be unique !')
    ]

product_applicationmodel()

# Product Application Area
class product_applicationarea(osv.osv):
    _name = 'product.applicationarea'
    _description = "product.applicationarea"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=6,),
    }

_defaults = {'active': lambda *a: True}

_sql_constraints = [
        ('code_uniq', 'unique(name)','The code of the application must be unique !')
    ]

product_applicationarea()

# Product Application Subarea
class product_applicationsubarea(osv.osv):
    _name = 'product.applicationsubarea'
    _description = "product.applicationsubarea"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=6,),
    }

_defaults = {'active': lambda *a: True}

_sql_constraints = [
        ('code_uniq', 'unique (name)','The code of the application must be unique !')
    ]

product_applicationsubarea()

# Product Library
class product_library(osv.osv):
    _name = 'product.library'
    _description = "Product Library"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=16,),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': lambda *a: True
    }

product_library()

# Product Collection
class product_collection(osv.osv):
    _name = 'product.collection'
    _description = "Product Collection"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=16,),
    }

product_collection()

# Product Manufacturer
class product_manufacturer(osv.osv):
    _name = 'product.manufacturer'
    _description = "Product Manufacturer"
    _columns = {
        'name': fields.many2one('product.application', 'Application', ondelete='cascade'),
        'model_name': fields.many2one('product.applicationmodel', 'Application Model', ondelete='cascade'),
        'born_date': fields.char('Start year',size=4, required=False),
        'death_date': fields.char('End year', size=4, required=False),
        'quantityapl': fields.integer('Quantity', size=4, required=False),
        'oem': fields.char('OEM',size=40),
        'note': fields.text('Comments', size=128, traslate=True),
        'area_name': fields.many2one('product.applicationarea', 'Application Area', ondelete='cascade'),
        'subarea_name': fields.many2one('product.applicationsubarea', 'Application Subarea', ondelete='cascade'),
        'editor_ids': fields.many2many('res.partner', 'author_editor_rel', 'author_id', 'partner_id', 'Partner', select=1),
    }

product_manufacturer()

# Competition Product Code
class codcomp(osv.osv):
    _name = 'product.codcomp'
    _description = "Competition Product Code"
    _columns = {
        'name': fields.char('Category',size=64, required=True, help='Name of the category'),
        'code': fields.char('Code', size=6,),
        'parent_id': fields.many2one('product.clasification','Parent Category', help='Name of the parent category'),
        'active': fields.boolean('Active'),
    }

_defaults = {'active': lambda *a: True}
_sql_constraints = [
        ('code_uniq', 'unique (name)','The code of the codcomp must be unique !')
    ]
codcomp()

# Product Attributes
class dm_material(osv.osv):
    _name = 'product.attribute'
    _description = 'Product Attribute'
    _columns = {
        'code': fields.char('Code', size=10, select=True),
        'name': fields.char('Name', required=True, size=30, translate=True),
        'description': fields.char('Description', required=True, size=60),
    }
    _order = 'name'
dm_material()

class product_attribute(osv.osv):
    _name = "product.manufacturerattribute"
    _description = "Product Attributes"
    
    def attr_name_get(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for product in self.browse(cr, uid, ids):
                value = ''
                attr = ''
                measure = ''
                if product.value:
                    value = str(product.value)
                if product.measurements_id:
                    measure = product.measurements_id.name
                if product.attribute_id:
                    attr = product.attribute_id.name
                #name = attr + ': '+ value +' '+ measure
                res[product.id] = attr + ': '+ value +' '+ measure
            return res
        
    
    _columns = {
        'name': fields.function(attr_name_get, method=True, type="char", size=256, string='Name'),
        'value' : fields.float('Value'),
        'measurements_id' : fields.many2one('product.uom', 'Measurements'),
        'attribute_id' : fields.many2one('product.attribute', 'Attribute'),        
        'product_id' : fields.many2one('product.template', 'Product', required=True, ondelete='cascade', select=True),
    }
        
product_attribute()

# Relations with product and 
class product_manufacturer_rel(osv.osv):
    _name = "product.manufacturer.rel"
    _rec_name = "product_manufacturer_id"
    _columns = {
        'author_id': fields.many2one('product.manufacturer', 'Author', ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Book', ondelete='cascade')
    }
product_manufacturer_rel()

class product_product(osv.osv):
    _inherit = 'product.product'

    def create(self, cr, uid, vals, context= None):
        def _uniq(seq):
            keys = {}
            for e in seq:
                keys[e] = 1
            return keys.keys()

        # add link from editor to supplier:
        if 'editor' in vals:
            editor_id = vals['editor']
            supplier_model = self.pool.get('library.editor.supplier')
            supplier_ids = [idn for idn in supplier_model.search(cr, uid, [('name', '=', editor_id)]) if idn > 0]
            suppliers = supplier_model.browse(cr, uid, supplier_ids, context)
            for obj in suppliers:
                supplier = [
                    0, 0, {'pricelist_ids': [], 'name': obj.supplier_id.id, 'sequence': obj.sequence, 'qty': 0,
                    'delay': 1, 'product_code': False, 'product_name': False}
                ]
                if 'seller_ids' not in vals:
                    vals['seller_ids'] = [supplier]
                else:
                    vals['seller_ids'].append(supplier)

        return super(product_product, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context={}):
        if not default:
            default = {}
        default.update({'author_ids': []})
        return super(product_product, self).copy(cr, uid, id, default, context)
                        
    _columns = {
        'link_ids': many2manysym('product.product', 'product_produc_rel', 'product_id1', 'product_id2', 'Equivalent Products'),
        'link_ids1': many2manysym('product.product', 'product_produc1_rel', 'product_id1', 'product_id2', 'New Products'),
        'link_ids2': many2manysym('product.product', 'product_produc2_rel', 'product_id1', 'product_id2', 'Principal Products'),
        'link_ids3': many2manysym('product.product', 'product_produc3_rel', 'product_id1', 'product_id2', 'Accesories Products'),
        'link_ids4': many2manysym('product.product', 'product_produc4_rel', 'product_id1', 'product_id2', 'Adapted Products'),
        'attribute_ids': fields.one2many('product.manufacturerattribute', 'product_id', 'Attributes', traslate="True"),
        'author_ids': fields.many2many('product.manufacturer', 'product_manufacturer_id', 'product_id', 'author_id', 'Models'),
    }

product_product()

class product_template(osv.osv):
    
    _inherit = "product.template"
    _columns = {
        'codcomp': fields.many2one('product.codcomp', 'Cod Comp', required=False),
        }
product_template()

class library_author(osv.osv):
    _inherit = 'product.manufacturer'
    _columns = {
        'book_ids': fields.many2many('product.product', 'product_manufacturer_id', 'author_id', 'product_id', 'Models', select=1),
    }
library_author()
