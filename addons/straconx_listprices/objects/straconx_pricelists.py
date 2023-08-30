# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
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
import time
from tools.translate import _
import decimal_precision as dp



class price_discount(osv.osv):

    def _get_currency(self, cr, uid, ctx):
        comp = self.pool.get('res.users').browse(cr,uid,uid).company_id
        if not comp:
            comp_id = self.pool.get('res.company').search(cr, uid, [])[0]
            comp = self.pool.get('res.company').browse(cr, uid, comp_id)
        return comp.currency_id.id

    _name = "discount.price.product"
    _description = "Discount Price"
    _columns = {
        'name' : fields.char("Price Name", size=32, required=True, translate=True, help="Name of this kind of price."),
        'discount': fields.float("Discount"),
        'list_active' : fields.boolean("Active"),
        'date_start': fields.datetime('Start Date', help="Starting date for this pricelist version to be valid."),
        'date_end': fields.datetime('End Date', help="Ending date for this pricelist version to be valid."),
        'currency_id' : fields.many2one('res.currency', "Currency", required=True, help="The currency the field is expressed in."),
    }
    _defaults = {
        "currency_id": _get_currency
    }

price_discount()

class discount_segmento(osv.osv):
    _inherit = 'res.partner.segmento'    

    def _get_historical_discount(self, cr, uid, ids, field_name, field_value, arg, context={}):
        res = {}
        product_hist = self.pool.get('product.historic.segmento')
        for id in ids:
            if self.browse(cr, uid, id).discount != self.browse(cr, uid, id).list_discount_historical:
                res[id] = self.browse(cr, uid, id).discount
                product_hist.create(cr, uid, {
                    'segmento_id' : id,
                    'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'discount': self.browse(cr, uid, id).discount,
                    'user_id':uid,
               },context)
        return res
    
    _columns = {
        'discount': fields.float("Discount"),
        'list_discount_historical': fields.function(_get_historical_discount, method=True, string='Discount Price', type='float',digits_compute= dp.get_precision('Price'),
            store={'res.partner.segmento': (lambda self, cr, uid, ids, c={}: ids, ['discount'], 50),}, 
            help="Latest Recorded Discount Value"),
        'list_price_historical_ids': fields.one2many('product.historic.segmento','segmento_id','Historical Discount'),
            }
    
discount_segmento()

class product_discount_segmento(osv.osv):
    _order= "name"
    _name = "product.historic.segmento"
    _description = "Historical Discount Segment List"

    _columns = {
        'segmento_id': fields.many2one('res.partner.segmento',string='Segmento', required=True),
        'name': fields.datetime(string='Date',  required=True),
        'discount': fields.float(string='Discount',digits_compute= dp.get_precision('Price')),
        'user_id': fields.many2one('res.users', 'User'),        
    }
    _defaults = { 'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                  'user_id': lambda obj, cr, uid, context: uid,
    }

product_discount_segmento()


# Discount for Category

class discount_category(osv.osv):
    _inherit = 'product.category'    

    def _get_historical_discount(self, cr, uid, ids, field_name, field_value, arg, context={}):
        res = {}
        product_hist = self.pool.get('product.historic.category')
        for id in ids:
            if self.browse(cr, uid, id).discount != self.browse(cr, uid, id).list_discount_historical:
                res[id] = self.browse(cr, uid, id).discount
                product_hist.create(cr, uid, {
                    'categ_id' : id,
                    'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'discount': self.browse(cr, uid, id).discount,
                    'user_id':uid,
               },context)
        return res
    
    _columns = {
        'discount': fields.float("Discount"),
        'list_discount_historical': fields.function(_get_historical_discount, method=True, string='Discount Price', type='float',digits_compute= dp.get_precision('Price'),
            store={'product.category': (lambda self, cr, uid, ids, c={}: ids, ['discount'], 50),}, 
            help="Latest Recorded Discount Value"),
        'list_price_historical_ids': fields.one2many('product.historic.category','categ_id','Historical Discount'),
            }
    
discount_category()

class product_discount_category(osv.osv):
    _order= "name"
    _name = "product.historic.category"
    _description = "Historical Discount Category List"

    _columns = {
        'categ_id': fields.many2one('product.category',string='Category', required=True),
        'name': fields.datetime(string='Date',  required=True),
        'discount': fields.float(string='Discount',digits_compute= dp.get_precision('Price')),
        'user_id': fields.many2one('res.users', 'User'),        
    }
    _defaults = { 'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                  'user_id': lambda obj, cr, uid, context: uid,
    }

product_discount_segmento()

class product_pricelist(osv.osv):

    _inherit = "product.pricelist"
    
    _columns ={
        'visible_discount': fields.boolean('Visible Discount'),
    }
    _defaults = {
         'visible_discount': True,
    }
    
    def price_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        currency_obj = self.pool.get('res.currency')
        product_obj = self.pool.get('product.product')
        product_template_obj = self.pool.get('product.template')
        product_category_obj = self.pool.get('product.category')
        product_uom_obj = self.pool.get('product.uom')
        supplierinfo_obj = self.pool.get('pricelist.partnerinfo')
        price_type_obj = self.pool.get('product.price.type')
        partner_obj = self.pool.get('res.partner')
        segmento_obj = self.pool.get('res.partner.segmento')
        date = time.strftime('%Y-%m-%d')
        if 'date' in context:
            date = context['date']
        if 'type' in context:
            type = context['type']
        else:
            type = 'out_invoice'
        # Revisa el producto, si tiene descuentos en producto, categoría o segmento.///
        p_prod = product_obj.browse(cr,uid,prod_id,context).list_price
        price_partner = 0
        #####
        ##1 segmento
        if partner:
            partner = partner_obj.browse(cr, uid,partner,context)
            if type in ('out_invoice','out_refund'):
                if partner.segmento_id:
                    d_segm = partner.segmento_id.discount
                    price_partner = p_prod * (1-(d_segm/100))
                else:
                    raise osv.except_osv(_('Warning !'), _("Customer need a segment for sales."))
        
        ##2 categoria del producto
        if prod_id:
            p_disc_categ = product_obj.browse(cr,uid,prod_id,context).categ_id.discount            
            if type in ('out_invoice','out_refund'):
                price_product = product_obj.browse(cr,uid,prod_id,context).discount_price or p_prod             
                price_categ = p_prod *(1-(p_disc_categ/100))
                if price_categ >0 and price_product >0:
                    if price_product <= price_categ:
                        price = price_product
                    else:
                        price = price_categ
                else:
                    price = price_product
            elif type in ('in_invoice','in_refund'):
                p_id = product_obj.browse(cr,uid,prod_id,context).product_tmpl_id.id
                price_fob = 0
                sinfo = supplierinfo_obj.search(cr, uid,[('product_id', '=', p_id),('partner_id', '=', partner.id)],context=context)
                if sinfo:
                    qty_in_product_uom = qty
                    cr.execute('SELECT * ' \
                               'FROM pricelist_partnerinfo ' \
                               'WHERE id IN %s' \
                               'AND min_quantity <= %s ' \
                               'ORDER BY min_quantity DESC LIMIT 1', (tuple(sinfo),qty_in_product_uom,))
                    res2 = cr.dictfetchone()
                    if res2:
                        price = res2['price']                
                    elif not res2:
                        price = product_obj.browse(cr,uid,prod_id,context).standard_price
                    else:
                        price = price                                         
                else:
                    price = product_obj.browse(cr,uid,prod_id,context).standard_price                        

                price_fob = product_obj.browse(cr, uid, prod_id, context=context).fob
                if price <> price_fob:
                    product_obj.write(cr, uid, prod_id, {'fob':price}, context)            
            else:
                price = 0
        
        if price_partner > 0:
                if price_partner >= price:
                    price = price
                else:
                    price = price_partner
        
        if not price and type in ('out_invoice','out_refund'):  
            raise osv.except_osv(_('Warning !'), _("Product need a price for continue operation."))        
        return ids and {ids[0]:price} or 0.0
    
product_pricelist()

class product_pricelist_item(osv.osv):
    _inherit = "product.pricelist.item"
    _columns = {
        'class_id': fields.many2one('product.clasification', 'Product Clasification', ondelete='cascade'),
        'min_base': fields.integer('Base Quantity', required=True),
        'min_quantity': fields.integer('Min. Quantity', required=True),
        'min_bonus': fields.integer('Bonus', required=True),
        'price_base': fields.float('Base Price', digits_compute= dp.get_precision('Price')),
        'price_gross': fields.float('Gross Price', digits_compute= dp.get_precision('Price')),
        'price_tax': fields.float('Taxes', digits_compute= dp.get_precision('Price')),
        'price_final': fields.float('Final Price', digits_compute= dp.get_precision('Price')),                        
        'standard_price': fields.float('Cost', digits_compute= dp.get_precision('Price')),
        'margin': fields.float('Margin', digits_compute= dp.get_precision('Price')),
        'price_discount': fields.float('% Discount', digits_compute= dp.get_precision('Price')),        
    }

    _defaults = {
        'min_base': lambda *a: 1,
        'min_quantity': lambda *a: 1,
        'min_bonus': lambda *a: 0,
    }

    def onchange_product(self, cr, uid, ids, product_id=False,price_base=0.00,price_discount=0.00, min_quantity=1.00, min_base=1.00, min_bonus=0.00, price_version_id=False ,context=None):        
        result = {}
        warning = {}
        price_gross = 0.00
        taxes = False
        price_tax = 0.00
        price_final = 0.00
        standard_price = 0.00
        margin = 0.00
        if product_id:
            prod = self.pool.get('product.product').browse(cr,uid,product_id)
            id_temp = prod.product_tmpl_id.id
            ptem = self.pool.get('product.template').browse(cr,uid,id_temp)             
            categ_id = ptem.categ_id.id
            class_id = prod.clasification_cat.id
            if not price_base or price_base ==0.00:
                price_base = ptem.list_price
            elif price_base <> ptem.list_price:
                price_base = price_base
            else:
                price_base = price_base            
            tax_amount=0
            if(price_version_id):
                l_id = self.pool.get('product.pricelist.version').browse(cr,uid,price_version_id).pricelist_id.id
                type_l = self.pool.get('product.pricelist').browse(cr,uid,l_id).type
                if type_l in ('sale'):
                    taxes = prod.taxes_id and prod.taxes_id
                else:
                    taxes = prod.supplier_taxes_id and prod.supplier_taxes_id
                if taxes:
                    for tax in taxes:
                        if tax.ref_base_code_id.tax_type=='vat':
                            tax_amount = tax.amount
                else:
                    tax_amount = 0.00 
            if price_base >= 0.00:
                price_gross = round(price_base * (1 - (price_discount/100)),4)
                price_tax = price_gross * tax_amount
                price_final = price_gross + price_tax
            else:
                raise osv.except_osv(_('Negative Price!'), _('Need a positive price for continue.'))   
            cost = ptem.standard_price
            if cost:
                if cost > 0 and price_gross> 0 and min_base > 0:
                    standard_price = cost
                    margin = (((price_gross*min_base) - (standard_price*(min_base+min_bonus)))/(price_gross*min_base)*100)
                    if margin <0:
                        warning = {'title': _('Warning!'),'message': _(('Margin for product %s is negative. Check please.')%ptem.name)}
                else:
                    warning = {'title': _('Warning!'),'message': _(('Cost for product %s is 0 or negative. Check please.')%ptem.name)}
                    standard_price = ptem.standard_price
                    margin = 0.00             
            result['categ_id']=categ_id
            result['class_id']=class_id
            result['price_base']=price_base
            result['price_gross']=price_gross
            result['price_tax']=price_tax
            result['price_final']=price_final
            result['standard_price']=standard_price
            result['margin']=margin
        else:
            result['categ_id']=False
            result['class_id']=False
            result['price_base']=0.00
            result['price_gross']=0.00
            result['price_tax']=0.00
            result['price_final']=0.00
            result['standard_price']=0.00
            result['margin']=0.00
        return {'value': result,'warning': warning}        
    
product_pricelist_item()

class product_pricelist_version(osv.osv):
    _inherit = "product.pricelist.version"
    _description = "Pricelist Version"
    _columns = {
        'categ_id': fields.many2one('product.category', 'Product Category', ondelete='cascade', help="Set a category of product if this rule only apply to products of a category and his children. Keep empty for all products"),
        'class_id': fields.many2one('product.clasification', 'Product Classification', ondelete='cascade'),
                }
product_pricelist_version()                                        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

