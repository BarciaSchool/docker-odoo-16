# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from tools.translate import _
import decimal_precision as dp


class product_product(osv.osv):
    _inherit = 'product.product'

    def _calculate_margin(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context):
            margin = 0
            if product.discount_price >0 and product.standard_price>0:
                if product.discount_price > product.standard_price:
                    margin = (1 - (product.standard_price/product.discount_price))*100
            res[product.id] = margin
        return res

    def _get_discount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context):
            discount_price = product.list_price * (1 - (product.discount_percent/100))
            res[product.id] = discount_price
        return res
    
    def _verified_price(self, cr, uid, ids, context=None):
        b = True
        for product in self.browse(cr, uid, ids, context):
            if product.discount_percent < 0:
                raise osv.except_osv(_('Negative Discount !'), _('Product have a negative discount. Check please!'))
            if product.discount_price >0 and product.standard_price>0 and product.sale_ok:
                if product.discount_price < product.standard_price:
                    raise osv.except_osv(_('Error!'), _(("%s has a standard price = %s is greater than discount Price = %s") %(product.name, product.standard_price, product.discount_price)))
        return b
    
    def price_segmento(self, cr, uid, ids, context=None):
        segment_obj=self.pool.get('res.partner.segmento')
        segment_ids=segment_obj.search(cr, uid, [])
        for segment in segment_obj.browse(cr, uid, segment_ids, context):
            for product in self.browse(cr, uid, ids):
                cr.execute("""SELECT id FROM price_segmento
                                WHERE segmento_id = %s AND product_id = %s""",(segment.id,product.id))
                res2 = cr.dictfetchone()
                if not res2:
                    self.pool.get('price.segmento').create(cr, uid, {'segmento_id':segment.id,
                                                                    'product_id':product.id,
                                                                      })
        return True

    _columns = {
        'discount_percent':fields.float('% Discount'),
        'discount_price': fields.function(_get_discount, method=True, string='Discount Price',digits_compute=dp.get_precision('Purchase Price'),store=True),
        'price_segmento_ids':fields.one2many('price.segmento', 'product_id', 'Price Segmento'),
        'margin_base': fields.function(_calculate_margin, method=True, string='% Margin', digits_compute=dp.get_precision('Purchase Price')),
    }
    
    _constraints = [(_verified_price, 'has a standard price is greater than list Price', ['standard_price','list_price'])]
    
    def create(self, cr, uid, vals, context=None):
        res = super(product_product, self).create(cr, uid, vals, context=context)
        sql="""INSERT INTO price_segmento (product_id,segmento_id) 
                    SELECT %s,id FROM res_partner_segmento"""
        cr.execute(sql,(res,))
        return res
    
#    def write(self, cr, uid, ids, vals, context=None):
#        res_id = super(product_product, self).write(cr, uid, ids, vals, context=context)
#        if vals.has_key('list_price'):
#            self.price_segmento(cr, uid, ids, context)
#        return res_id
#    
    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        default.update({
            'price_segmento_ids':[],
            })
        return super(product_product, self).copy(cr, uid, id, default, context)
       
    def onchange_margin(self, cr, uid, ids, discount_price=0.00, standard_price=0.00, context=None):
        margin = 0
        res = {}
        for product in self.browse(cr, uid, ids, context):
            if discount_price >0 and standard_price>0:
                if discount_price > standard_price:
                    margin = (1 - (standard_price/discount_price))*100
                else:
                    margin = 0
            res[product.id] = margin
        return res

        
product_product()

class pricelist_partnerinfo(osv.osv):
    _inherit = 'pricelist.partnerinfo'
    _columns = {
        'partner_id': fields.related('suppinfo_id','name', type='many2one', relation='res.partner', string='Partner',store=True),
        'product_id': fields.related('suppinfo_id','product_id', type='many2one', relation='product.template', string='Product',store=True),
    }
    _order = 'min_quantity asc'

pricelist_partnerinfo()

class product_supplierinfo(osv.osv):
    _inherit = "product.supplierinfo"

    def _get_supplier_lines(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('pricelist.partnerinfo').browse(cr, uid, ids, context=context):
            result[line.suppinfo_id.id] = True
        return result.keys()
    
    def _calc_qty(self, cr, uid, ids, name, args, context=None):        
        res = {}
        for supplier in self.browse(cr,uid,ids,context):
            res[supplier.id] ={}            
            cr.execute('SELECT * ' \
                       'FROM pricelist_partnerinfo ' \
                       'WHERE suppinfo_id = %s' \
                        'ORDER BY min_quantity ASC LIMIT 1', (str(supplier.id)))
            res2 = cr.dictfetchone()
            if res2:
                res[supplier.id]['qty'] = res2['min_quantity']
                res[supplier.id]['price_supplier'] = res2['price']
                res[supplier.id]['min_qty']= res2['min_quantity']                        
        return res            

    _columns = {
    'qty': fields.function(_calc_qty, type='float', string='Quantity', multi="qty",
            store={
            'product.supplierinfo': (lambda self, cr, uid, ids, c={}: ids, ['pricelist_ids'], 50),
            'pricelist.partnerinfo': (_get_supplier_lines, None, 50),
                           }),
    'min_qty': fields.function(_calc_qty, type='float', string='Min. Quant.', multi="qty", 
            store={
            'product.supplierinfo': (lambda self, cr, uid, ids, c={}: ids, ['pricelist_ids'], 50),
            'pricelist.partnerinfo': (_get_supplier_lines, None, 50),
                           }),
    'price_supplier': fields.function(_calc_qty, type='float', string='Price', multi="qty",
            store={
            'product.supplierinfo': (lambda self, cr, uid, ids, c={}: ids, ['pricelist_ids'], 50),
            'pricelist.partnerinfo': (_get_supplier_lines, None, 50),
                           }),
    }
    _sql_constraints = [
                        ('supplier_uniq','unique(name, product_id)', 'Products and partner must be unique'),
                        ]

product_supplierinfo()
