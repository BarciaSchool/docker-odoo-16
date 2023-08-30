# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or#    (at your option) any later version.
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

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class lost_sales(osv.osv):

    def _get_categ_id(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for obj in self.browse(cr, uid, ids):
                if obj.product_id.categ_id:
                    res[obj.id] = obj.product_id.categ_id.id
                else:
                    res[obj.id] = ''
            return res

    def _categ_id_search(self, cr, uid, obj, name, args, context):
            if not len(args):
                    return []
                    new_args = []
                    for argument in args:
                            operator = argument[1]
                            value = argument[2]
                            ids = self.pool.get('product.category').search(cr, uid, [('name',operator,value)], context=context)
                            new_args.append( ('categ_id','in',ids) )
                    if new_args:
                            new_args.append( ('categ_id','!=',False) )
            return new_args

    _name="lost.sales"
    _columns = {
                'product_id':fields.many2one('product.product', 'Producto', required=False),
                'qty': fields.float('Quantity', digits=(16,2)),
                'uom_id':fields.many2one('product.uom', 'UOM', required=False),
                'date': fields.datetime('Date Lost'),
                'picking_id':fields.many2one('stock.picking', 'Picking', required=False),
#                'type_lost': fields.selection([
#                    ('no_stock','No Stock'),
#                    ('another_warehouse','Another Warehouse'),
#                    ('catalog','Product in catalog'),
#                    ('other','Other'),],
#                    'Type Lost'),
                'note': fields.text('Motive'),
                'partner_id':fields.many2one('res.partner', 'Client', required=False),
                'shop_id':fields.many2one('sale.shop', 'Shop', required=False),
                'salesman_id':fields.many2one('salesman.salesman', 'Salesman', required=False),
                'ref_sale':fields.char('Ref sale Order', size=32, required=False, readonly=False),
                'categ_id': fields.function(_get_categ_id, fnct_search=_categ_id_search, obj="product.category", method=True, type="many2one", string='Category',store=True),
    }
lost_sales()
