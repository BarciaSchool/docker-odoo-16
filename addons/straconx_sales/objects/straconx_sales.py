# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby
from account_voucher import account_voucher
import method

from osv import fields, osv
from tools.translate import _
import netsvc
import tools
import decimal_precision as dp
import logging
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare

# Add brand, list_price, margin, discount and cost_price, and automatic calculation for fields.

sql = """SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo 
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

# Add categ_id,  purchase_price and cost_price    
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
                            ids = self.pool.get('product.category').search(cr, uid, [('name', operator, value)], context=context)
                            new_args.append(('categ_id', 'in', ids))
                    if new_args:
                            new_args.append(('categ_id', '!=', False))
            return new_args
    
#     def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
#             uom=False, qty_uos=0, uos=False, name='', partner_id=False,
#             lang=False, update_tax=True, date_order=False, packaging=False,
#             #fiscal_position=False, flag=False, line_ids=None, secuence=False, shop_id=None, context=None):
#             fiscal_position=False, flag=False, line_ids=None, shop_id=None, location_id=None, context=None):
#         try:
#             result = {}
#             warning = {}
#             if not partner_id:
#                 raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sales form !\nPlease set one customer before choosing a product.'))
#             product_uom_obj = self.pool.get('product.uom')
#             partner_obj = self.pool.get('res.partner')
#             product_obj = self.pool.get('product.product')
#             shop_obj = self.pool.get('sale.shop')
#             if partner_id:
#                 lang = partner_obj.browse(cr, uid, partner_id).lang
#             context = {'lang': lang, 'partner_id': partner_id}
#             if location_id:
#                 context['location']=location_id
#     
#             if not product:
#                 return {'value': {'th_weight': 0, 'product_packaging': False,
#                     'product_uos_qty': qty, 'tax_id':[]}, 'domain': {'product_uom': [],
#                        'product_uos': []}}
#             if not date_order:
#                 date_order = time.strftime('%Y-%m-%d')
#                 
#             frm_cur = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id     
#             to_cur = self.pool.get('res.partner').browse(cr, uid, partner_id).property_product_pricelist.currency_id.id
#             if product:
#                 line = self.browse(cr, uid, id)
#                 discount = line.discount or 0.00
#                 disc = discount
#                 list_price = self.pool.get('product.product').browse(cr, uid, product).list_price
#                 purchase_price = self.pool.get('product.product').browse(cr, uid, product).standard_price
#                 price_unit = (self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product, qty or 1.0, partner_id, {'uom': uom,'date': date_order,})[pricelist])*(1-round(disc/100,4))
#                 price = self.pool.get('res.currency').compute(cr, uid, frm_cur, to_cur, purchase_price, round=False)
#                 product_categ_obj = self.pool.get('product.product').browse(cr, uid, product).product_tmpl_id
#                 discount_price = self.pool.get('product.product').browse(cr, uid, product).list_price
#                 discount_percent =  (1 - round(price_unit/list_price, 2))*100
#                 discount_order = self.pool.get('product.product').browse(cr, uid, product).list_price - price_unit
#                 discount_order_total = (self.pool.get('product.product').browse(cr, uid, product).list_price - price_unit)*qty
#                 margin_unit = round(price_unit - price,4)
#                 margin = round(price_unit - price,4)*qty
#                 margin_percent = (1 - round(price / price_unit , 4))*100
#                 totalcostline = self.pool.get('product.product').browse(cr, uid, product).standard_price * qty
#                 price_subtotal = (price_unit*(1-round(disc/100,4)))* qty
#                 offer_value = price_unit*round(disc/100,4)
#                 categ_id = product_categ_obj.categ_id.id
#                 if shop_id:
#                     percent_minum= shop_obj.browse(cr, uid, shop_id, context=None).min_utility_margen
#                     if margin_percent >= percent_minum:
#                         result['autorized'] = True
#                     else:
#                         warn_msg = _("the profit margin from these sales is less than that established by the shop.\n"
#                                 "Please authorization request.")
#                         warning['title']= _('Margin Incorrect !')
#                         warning['message']= warn_msg
#                         result['autorized'] = False
#                 result['categ_id'] = categ_id
#                 result.update({'price_unit': price_unit}) 
#                 result.update({'offer_value': offer_value})
#                 result.update({'discount': discount})
#                 result.update({'discount_order': discount_order})
#                 result.update({'discount_order_total': discount_order_total})
#                 result.update({'discount_price': list_price})  
#                 result.update({'discount_percent': discount_percent})
#                 result.update({'purchase_price': price})
#                 result.update({'margin_unit': margin_unit})
#                 result.update({'margin': margin})
#                 result.update({'margin_percent': margin_percent})
#                 result.update({'price_subtotal': price_subtotal})
#                 result.update({'price_subtotal_incl': price_subtotal})
#                 result.update({'total_cost_line': totalcostline})
#     
#             
#             product_obj = product_obj.browse(cr, uid, product, context=context)
#             if not packaging and product_obj.packaging:
#                 packaging = product_obj.packaging[0].id
#                 result['product_packaging'] = packaging
#     
#             if packaging:
#                 default_uom = product_obj.uom_id and product_obj.uom_id.id
#                 pack = self.pool.get('product.packaging').browse(cr, uid, packaging, context=context)
#                 q = product_uom_obj._compute_qty(cr, uid, uom, pack.qty, default_uom)
#                 if qty and (q and not (qty % q) == 0):
#                     ean = pack.ean or _('(n/a)')
#                     qty_pack = pack.qty
#                     type_ul = pack.ul
#                     warn_msg = _("You selected a quantity of %d Units.\n"
#                                 "But it's not compatible with the selected packaging.\n"
#                                 "Here is a proposition of quantities according to the packaging:\n\n"
#                                 "EAN: %s Quantity: %s Type of ul: %s") % \
#                                     (qty, ean, qty_pack, type_ul.name)
#                     warning['title']=_('Picking Information !')
#                     warning['message']= warn_msg
#                 result['product_uom_qty'] = qty
#     
#             uom2 = False
#             if uom:
#                 uom2 = product_uom_obj.browse(cr, uid, uom)
#                 if product_obj.uom_id.category_id.id != uom2.category_id.id:
#                     uom = False
#             if uos:
#                 if product_obj.uos_id:
#                     uos2 = product_uom_obj.browse(cr, uid, uos)
#                     if product_obj.uos_id.category_id.id != uos2.category_id.id:
#                         uos = False
#                 else:
#                     uos = False
#             if product_obj.description_sale:
#                 result['notes'] = product_obj.description_sale
#             fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
#             if update_tax: #The quantity only have changed
#                 result['delay'] = (product_obj.sale_delay or 0.0)
#                 result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
#                 result.update({'type': product_obj.procure_method})
#     
#             if not flag:
#                 result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context)[0][1]
#             domain = {}
#             if (not uom) and (not uos):
#                 result['product_uom'] = product_obj.uom_id.id
#                 if product_obj.uos_id:
#                     result['product_uos'] = product_obj.uos_id.id
#                     result['product_uos_qty'] = qty * product_obj.uos_coeff
#                     uos_category_id = product_obj.uos_id.category_id.id
#                 else:
#                     result['product_uos'] = False
#                     result['product_uos_qty'] = qty
#                     uos_category_id = False
#                 result['th_weight'] = qty * product_obj.weight
#                 domain = {'product_uom':
#                             [('category_id', '=', product_obj.uom_id.category_id.id)],
#                             'product_uos':
#                             [('category_id', '=', uos_category_id)]}
#     
#             elif uos and not uom: # only happens if uom is False
#                 result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
#                 result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
#                 result['th_weight'] = result['product_uom_qty'] * product_obj.weight
#             elif uom: # whether uos is set or not
#                 default_uom = product_obj.uom_id and product_obj.uom_id.id
#                 q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
#                 if product_obj.uos_id:
#                     result['product_uos'] = product_obj.uos_id.id
#                     result['product_uos_qty'] = qty * product_obj.uos_coeff
#                 else:
#                     result['product_uos'] = False
#                     result['product_uos_qty'] = qty
#                 result['th_weight'] = q * product_obj.weight        # Round the quantity up
#     
#             if not uom2:
#                 uom2 = product_obj.uom_id
#             if product_obj.qty_available  < qty :
#                 warning['title']=_('Not enough stock !')
#                 warning['message']= _('You plan to sell %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') %(qty, uom2 and uom2.name or product_obj.uom_id.name,
#                         max(0,product_obj.virtual_available), product_obj.uom_id.name,
#                         max(0,product_obj.qty_available), product_obj.uom_id.name)
#             if not pricelist:
#                 warning['title']=_('No Pricelist !')
#                 warning['message']= _( 'You have to select a pricelist or a customer in the sales form !\n'
#                                        'Please set one before choosing a product.')
#             else:
#                 price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
#                         product, qty or 1.0, partner_id, {
#                             'uom': uom,
#                             'date': date_order,
#                             })[pricelist]
#                 if price is False:
#                     warning['title']=_('No valid pricelist line found !')
#                     warning['message']= _( "Couldn't find a pricelist line matching this product and quantity.\n"
#                                            "You have to change either the product, the quantity or the pricelist.")
#                 else:
#                     result.update({'price_unit': price})
#             return {'value': result, 'domain': domain, 'warning': warning}
#         except ZeroDivisionError:
#             raise osv.except_osv(_('Error!'), _("The price of product is equals to 0"))
            
    def sequence_change(self, cr, uid, ids, sale_line_ids, shop_id=None, context=None):
        if not shop_id:
            raise osv.except_osv(_('No Shop Defined !'), _('You must select a Shop.'))
        shop = self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
        sequence = method.sequence_change(sale_line_ids, shop, context)
        if not sequence:
            raise osv.except_osv(_('Error !'), _('You can not generate more than %s lines per sales order.') % str(shop.limits_line_invoice))
        return {'value':{'sequence':sequence}}
    
    def price_by_product(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        if not product_id:
            return 0.0
        if not pricelist:
            raise osv.except_osv(_('No Pricelist !'),
                _('You have to select a pricelist in the sale form !\n' \
                'Please set one before choosing a product.'))
        p_obj = self.pool.get('product.product').browse(cr, uid, [product_id])[0]
        uom_id = p_obj.uom_po_id.id
        vals_price = self.pool.get('product.pricelist').price_get(cr, uid,
            [pricelist], product_id, qty or 1.0, partner_id, {'uom': uom_id})
        price = vals_price[pricelist]
        unit_price = price or p_obj.list_price
        if unit_price is False:
            raise osv.except_osv(_('No valid pricelist line found !'),
                _("Couldn't find a pricelist line matching this product" \
                " and quantity.\nYou have to change either the product," \
                " the quantity or the pricelist."))            
        return unit_price
    
    def product_uom_change(self, cursor, user, ids, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False, name='', partner_id=False, update_tax=True, date_order=False, shop_id=None, location_id=None, context=None):
        context = context or {}
        lang = ('lang' in context and context['lang'])
        prod_id = self.pool.get('product.template').browse(cursor,user,product)
        uom_id = self.pool.get('product.uom').browse(cursor,user,uom)
        if uom_id.name == 'Yardas':
            cant = qty /(prod_id.uos_coeff)
            res = self.product_id_change(cursor, user, ids, pricelist, product,
                    qty=cant, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                    partner_id=partner_id, update_tax=update_tax,
                    date_order=date_order, shop_id=shop_id, location_id=location_id , context=context)
        else:
            res = self.product_id_change(cursor, user, ids, pricelist, product,
                    qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                    partner_id=partner_id, update_tax=update_tax,
                    date_order=date_order, shop_id=shop_id, location_id=location_id , context=context)
        if 'product_uom' in res['value']:
            del res['value']['product_uom']
        if not uom:
            res['value']['price_unit'] = 0.0
        return res
    
    def __get_tax_amount(self, cr, uid, ids, pricelist_id, brw_pproduct, context=None):
        tax_amount = 0
        if(pricelist_id):
            if self.pool.get('product.pricelist').browse(cr, uid, pricelist_id, context=context).type in ('sale'):
                taxes = brw_pproduct.taxes_id and brw_pproduct.taxes_id
            else:
                taxes = brw_pproduct.supplier_taxes_id and brw_pproduct.supplier_taxes_id
            if taxes:
                for tax in taxes:
                    if tax.ref_base_code_id.tax_type == 'vat':
                        tax_amount = tax.amount
            else:
                tax_amount = 0.00        
        return tax_amount
    
    def onchange_discount_prices(self, cr, uid, ids,
                                qty, partner_id, product_id, pricelist_id,
                                discount_price, purchase_price,
                                discount_percent, discount, shop_id, context=None):
        discount_price = discount_price or 0
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sales form !\nPlease set one customer before choosing a product.'))
        if not product_id:
                        return {'value': {'th_weight': 0, 'product_packaging': False,
                'product_uos_qty': qty, "discount_price":0, "discount_percent":0, "discount_order":0,
                "discount_order_total":0, "price_unit":0, "purchase_price":0,
                "discount":0, "offer_value":0, "offer_value_total":0, "price_subtotal":0,
                "total_cost_line":0, "margin_unit":0, "margin":0}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        brw_pproduct = self.pool.get("product.product").browse(cr, uid, product_id, context=context)
        tax_amount = self.__get_tax_amount(cr, uid, ids, pricelist_id, brw_pproduct, context=context)
        discount_and_price = self.get_discount_and_price(cr, uid, ids, qty, partner_id, product_id, pricelist_id, context=context)                
        if(discount_price): 
            if(purchase_price > discount_price):
                return {"value":self.__get_val_discount(cr, uid, ids, discount_and_price[3],
                                                        discount_percent, discount, purchase_price, shop_id, qty,
                                                        tax_amount, context=context),"warning":{"title":"Error de Validación","message":"Precio no debe ser menor al costo."}} 
            return {"value":self.__get_val_discount(cr, uid, ids, discount_price,
                                                    discount_percent, discount, purchase_price, shop_id, qty,
                                                    tax_amount, context=context)}                                                
        return {"value":self.__get_val_discount(cr, uid, ids, discount_and_price[3],
                        discount_percent, discount, purchase_price, shop_id, qty,
                        tax_amount, context=context), "warning":{"title":"Error de Validación", "message":"Precio no debería ser 0"}}
    
    def __get_val_discount(self, cr, uid, ids, discount_price, discount_percent, discount, purchase_price,
                   shop_id, qty, tax_amount, context=None):
        price_unit = (discount_price) * (1 - round(discount_percent / 100, 4))
        vals = self.onchange_discount(cr, uid, ids, price_unit, discount, qty, purchase_price, shop_id).get("value", {})
        vals.update({
                    "purchase_price":purchase_price,
                    "discount_percent":discount_percent,
                    "discount_price":discount_price,
                    "price_unit":price_unit,
                    'discount': discount,
                    'discount_order': discount_price - price_unit,
                    'discount_order_total': (discount_price - price_unit) * qty,
                    'total_cost_line': purchase_price * qty,
        })
        return vals
    
    def _get_uom_id(self, cr, uid, *args):
        return False
    
    def get_discount_and_price(self, cr, uid, ids, qty, partner_id, product_id, pricelist_id, context=None):
        context = (context is None) and {} or context
        srch_pp_version = self.pool.get("product.pricelist.version").search(cr, uid, [('active', '=', True), ('pricelist_id', '=', pricelist_id)])
        discount = 0.0
        price_unit = 0.0
        price = 0.0
        OBJ_PRODUCT_PRODUCT = self.pool.get("product.product")
        brw_pproduct = OBJ_PRODUCT_PRODUCT.browse(cr, uid, product_id, context=context)        
        #tax_amount = self.__get_tax_amount(cr, uid, ids, pricelist_id, brw_pproduct, context=context)        
        if(srch_pp_version):
            OBJ_PRODUCT_PRICELIST_ITEM = self.pool.get("product.pricelist.item")
            srch_pplist_item = OBJ_PRODUCT_PRICELIST_ITEM.search(cr, uid, [('price_version_id', '=', srch_pp_version[0]), ('product_id', '=', product_id)])
            if(srch_pplist_item):
                brw_pplist_item = OBJ_PRODUCT_PRICELIST_ITEM.browse(cr, uid, srch_pplist_item[0], context=context)
                if(qty >= brw_pplist_item.min_base):
                    discount = brw_pplist_item.price_discount or 0
                    if(discount):
                        price = brw_pplist_item.price_base - (brw_pplist_item.price_base * discount / 100)                    
                        #price_unit = price + (price * tax_amount)
                        return (price, discount, price_unit, brw_pplist_item.price_base or 0)
        if partner_id:
            brw_r_partner = self.pool.get("res.partner").browse(cr, uid, partner_id, context=context)
            type = ('type' in context) and context['type'] or 'sale_order'
            if type in ('sale_order'):
                if brw_r_partner.segmento_id:
                    discount = brw_r_partner.segmento_id.discount or 0
                    if(discount):
                        price = brw_pproduct.list_price * (1 - (discount / 100)) or 0
                        #price_unit = price + (price * tax_amount)
                        return (price, discount, price_unit, brw_pproduct.list_price)
        if(brw_pproduct.categ_id):
            discount = brw_pproduct.categ_id.discount or 0
            if(discount):
                price = brw_pproduct.list_price * (1 - (discount / 100))                
                #price_unit = price + (price * tax_amount)
                return (price, discount, price_unit, brw_pproduct.list_price)
        discount = brw_pproduct.discount_percent or 0
        price = brw_pproduct.list_price * (1 - (discount / 100))
        #price_unit = price + (price * tax_amount)
        return (price, discount, price_unit, brw_pproduct.list_price)
    
    def product_id_change(self, cr, uid, ids, pricelist=False, product=False, qty=0, uom=False, qty_uos=0, uos=False, name='', partner_id=False, update_tax=True,date_order=False, packaging=False,fiscal_position=False, flag=False, shop_id=None, location_id=None, context=None):        
        context = context or {}
        lang = context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sales form !\nPlease set one customer before choosing a product.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_pool = self.pool.get('product.product')
        shop_obj = self.pool.get('sale.shop')
        context = {'lang': lang, 'partner_id': partner_id}
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}
        if not product:
            return {'value': {'th_weight': 0, 'product_packaging': False,
                'product_uos_qty': qty, "discount_price":0, "discount_percent":0, "discount_order":0,
                "discount_order_total":0, "price_unit":0, "purchase_price":0,
                "discount":0, "offer_value":0, "offer_value_total":0, "price_subtotal":0,
                "total_cost_line":0, "margin_unit":0, "margin":0}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if(not qty and (product or name)):
            return {"value":{"discount_order_total":0, "offer_value_total":0, "price_subtotal":0, "total_cost_line":0, "margin":0},
                    "warning":{"title":_("Validation Error!"), "message":_("Quantity can not be lower than or equal to 0")}}       
        qty = (qty < 0) and -qty or qty 
        if location_id:
            context['location'] = location_id
        else:
            context['location'] = shop_obj.browse(cr, uid, shop_id).warehouse_id.lot_stock_id.id or None
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        res = self.product_packaging_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, packaging, context=context)
        result = res.get('value', {})
        warning_msgs = res.get('warning') and res['warning']['message'] or ''
        product_obj = product_pool.browse(cr, uid, product, context=context)
        values = (0, 0, 0)
        try:
            frm_cur = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id     
            to_cur = self.pool.get('res.partner').browse(cr, uid, partner_id).property_product_pricelist.currency_id.id
            discount = ids and self.browse(cr, uid, ids[0], context).discount or 0.00  # #es la oferta
            list_price = product_obj.list_price
            purchase_price = product_obj.standard_price
            values = self.get_discount_and_price(cr, uid, ids, qty, partner_id, product, pricelist, context=context)
            price_unit = values[0] * (1 - round(discount / 100, 4))
            # price_unit = (self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product, qty or 1.0, partner_id, {'uom': uom,'date': date_order,})[pricelist])*(1-round(discount/100,4))
            price = self.pool.get('res.currency').compute(cr, uid, frm_cur, to_cur, purchase_price, round=False)  # #al coomputar elv alor de la moneda cmabia el porcentaje
            # discount_price = self.pool.get('product.product').browse(cr, uid, product).list_price

            # #discount_percent =  (1 - round(price_unit/list_price, 2))*100
            # #a corregir            
            discount_percent = values[1]
            # discount_order = self.pool.get('product.product').browse(cr, uid, product).list_price - price_unit
            # discount_order_total = (self.pool.get('product.product').browse(cr, uid, product).list_price - price_unit)*qty
            margin_unit = round(price_unit - price, 4)
            margin = round(price_unit - price, 4) * qty
            margin_percent = (1 - round(price / price_unit , 4)) * 100
            # totalcostline = purchase_price * qty
            price_subtotal = (values[0] * (1 - round(discount / 100, 4))) * qty
            offer_value = values[0] * round(discount / 100, 4)
            if shop_id:
                percent_minum = shop_obj.browse(cr, uid, shop_id, context=None).min_utility_margen
                if margin_percent >= percent_minum:
                    result['authorized'] = True
                else:
                    warning['title'] = _('Margin Incorrect !')
                    warning['message'] = _("the profit margin from these sales is less than that established by the shop.\n"
                            "Please authorization request.")
                    result['authorized'] = False
            discount_order = list_price - values[0]
            result.update({'price_unit': values[0],
                           'offer_value': offer_value,
                           'offer_value_total': offer_value * qty,
                           'discount': discount,
                           'discount_order': discount_order,
                           'discount_order_total': discount_order * qty,
                           'discount_price': list_price,
                           'discount_percent': discount_percent,
                           'purchase_price': price,
                           'margin_unit': margin_unit,
                           'margin': margin,
                           'margin_percent': margin_percent,
                           'price_subtotal': price_subtotal,
                           'price_subtotal_incl': price_subtotal,
                           'total_cost_line': purchase_price * qty,
                           'categ_id' : product_obj.categ_id.id,
                           })
        except ZeroDivisionError:
            raise osv.except_osv(_('Error!'), _("The list price of product is equals to 0"))

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        if uom and qty > 0:
            categ = self.pool.get('product.uom.categ').browse(cr, uid, uom).decimals
            if categ == False:
                valor = str(qty)
                dec = valor.split('.')
                if (int(dec[1]) > 0):
                    raise osv.except_osv(_('Check quantity!'), _("The UOM no permitted quantity with decimals"))

        if product_obj.description_sale:
            result['notes'] = product_obj.description_sale
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax:  # The quantity only have changed
            result['delay'] = (product_obj.sale_delay or 0.0)
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
            result.update({'type': product_obj.procure_method})

        if not flag:
            if not name:
                result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}

        elif uos and not uom:  # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom:  # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty 
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                result['product_uom_qty'] = qty
            result['th_weight'] = q * product_obj.weight  # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        compare_qty = float_compare(product_obj.virtual_available * uom2.factor, qty * product_obj.uom_id.factor, precision_rounding=product_obj.uom_id.rounding)
        if (product_obj.type == 'product') and int(compare_qty) == -1 \
          and (product_obj.procure_method == 'make_to_stock'):
            warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
                    (qty, uom2 and uom2.name or product_obj.uom_id.name,
                     max(0, product_obj.virtual_available), product_obj.uom_id.name,
                     max(0, product_obj.qty_available), product_obj.uom_id.name)
            warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg + "\n\n"
#        else:
#             price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
#                     product, qty or 1.0, partner_id, {
#                         'uom': uom or result.get('product_uom'),
#                         'date': date_order,
#                         })[pricelist]
#            price=values[2]
            if price is False:
                warn_msg = _("Couldn't find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg + "\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error !'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}
    
    def onchange_discount(self, cr, uid, ids, price_unit, discount, qty, cost, shop_id, *a):
        res = {}
        warning = {}
        if qty > 0 :
            if discount >= 0:
                res['offer_value'] = price_unit * discount / 100
                res['offer_value_total'] = (price_unit * discount / 100) * qty
                subtotal = (price_unit * qty) - ((price_unit * discount / 100) * qty)
                res['price_subtotal'] = subtotal
                res['margin_unit'] = (price_unit * (1 - discount / 100)) - cost
                margen = ((price_unit * (1 - discount / 100)) - cost) * qty
                res['margin'] = margen
                if subtotal > 0:
                    res['margin_percent'] = (margen / subtotal) * 100
                    maximo = self.pool.get('res.users').browse(cr, uid, uid, context=None).max_offer
                    margin_shop = self.pool.get('sale.shop').browse(cr, uid, shop_id, context=None).min_utility_margen
                    if discount > maximo or (margen / subtotal) * 100 < margin_shop:
                        warn_msg = _("You have exceed a Discount in the sale form.\n"
                                    "Please authorization request.")
                        warning = {
                            'title': _('Exceed Discount !'),
                            'message': warn_msg
                            }
                        res['authorized'] = False
                    else:
                        res['authorized'] = True
        else: 
            raise osv.except_osv('Error!', _("Put quantity in your sale order line"))
        return {'value': res, 'warning': warning}

#    def price_by_product_multi(self, cr, uid, ids, context=None):
#        if context is None:
#            context = {}
#        res = {}.fromkeys(ids, 0.0)
#        lines = self.browse(cr, uid, ids, context=context)
#
#        pricelist_ids = [line.order_id.pricelist_id.id for line in lines]
#        products_by_qty_by_partner = [(line.product_id.id, line.product_uom_qty, line.order_id.partner_id.id) for line in lines]
#
#        price_get_multi_res = self.pool.get('product.pricelist').price_get_multi(cr, uid, pricelist_ids, products_by_qty_by_partner, context=context)
#
#        for line in lines:
#            pricelist = line.order_id.pricelist_id.id
#            product_id = line.product_id
#
#            if not product_id:
#                res[line.id] = 0.0
#                continue
#            if not pricelist:
#                raise osv.except_osv(_('No Pricelist !'),
#                    _('You have to select a pricelist in the sale form !\n' \
#                    'Please set one before choosing a product.'))
#
#            price = price_get_multi_res[line.product_id.id][pricelist]
#
#            unit_price = price or product_id.list_price
#            res[line.id] = unit_price
#            if unit_price is False:
#                raise osv.except_osv(_('No valid pricelist line found !'),
#                    _("Couldn't find a pricelist line matching this product" \
#                    " and quantity.\nYou have to change either the product," \
#                    " the quantity or the pricelist."))
#        return res

    def _get_amount(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for line in self.browse(cr, uid, ids, context=context):
                # values = self.get_discount_and_price(cr, uid, ids, line.product_uom_qty, line.order_id.partner_id.id, line.product_id.id, line.order_id.pricelist_id.id, context=context)
                # price = self.price_by_product(cr, uid, ids, line.order_id.pricelist_id.id, line.product_id.id, line.product_uom_qty, line.order_id.partner_id.id)
                price_unit = line.discount_price - (line.discount_price * (line.discount_percent / 100))
                res[line.id] = price_unit
            return res
   
    def get_line_attr(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])   
        for line in self.browse(cr, uid, ids, context=context):
            field_names = (isinstance(field_names, list)) and field_names or [field_names]
            frm_cur = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id     
            to_cur = self.pool.get('res.partner').browse(cr, uid, line.order_id.partner_id.id).property_product_pricelist.currency_id.id
            purchase_price = self.pool.get('res.currency').compute(cr, uid, frm_cur, to_cur, line.product_id.standard_price, round=False)  # #al coomputar elv alor de la moneda cmabia el porcentaje
            info = self.get_discount_and_price(cr, uid, ids, line.product_uom_qty, line.order_id.partner_id.id, line.product_id.id, line.order_id.pricelist_id.id, context={"type":"sale_order"})
            values = self.onchange_discount_prices(cr, uid, [line.id], line.product_uom_qty, line.order_id.partner_id.id,
                                                 line.product_id.id, line.order_id.pricelist_id.id, line.discount_price, purchase_price,
                                                 info[1], line.discount, line.order_id.shop_id.id, context=context).get("value", {})
            for field_name in field_names:
                res[line.id][field_name] = values.get(field_name, 0.00)
        return res
    
    def _line_attr(self, cr, uid, ids, field_name, arg, context=None):
        return self.get_line_attr(cr, uid, ids, field_name, arg, context)
    
    def get_amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')
        # self.price_by_product_multi(cr, uid, ids)
        for line in self.browse(cr, uid, ids, context=context):
 #           values=self.get_discount_and_price(cr, uid, ids, line.product_uom_qty, line.order_id.partner_id.id, line.product_id.id, line.order_id.pricelist_id.id, context=context)
                res[line.id] = 0.0
                if field_names == 'price_subtotal':
                    if line.discount != 0.0:
                        res[line.id]= (line.price_unit * (1 - round(line.discount / 100, 4))) * line.product_uom_qty 
                        # res[line.id][f] = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
                    else:
                        res[line.id] = line.price_unit * line.product_uom_qty
                elif field_names == 'price_subtotal_incl':
                    taxes = [t for t in line.product_id.taxes_id]
                    if line.product_uom_qty == 0.0:
                        res[line.id]= 0.0
                        continue
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, price, line.product_uom_qty)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = self.pool.get('res.currency').round(cr, uid, cur, computed_taxes['total'])
        return res
            
    def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        return self.get_amount_line_all(cr, uid, ids, field_names, arg, context)
    
#    def write(self, cr, uid, ids, values, context=None):
#        try:
#            sequence = values['sequence']
#            values['sequence1'] = sequence
#            return super(sale_order_line, self).write(cr, uid, ids, values, context)
#        except:
#            return super(sale_order_line, self).write(cr, uid, ids, values, context)
        
        
#    def create(self, cr, uid, values, context=None):
#        try:
#            sequence = values['sequence']
#            values['sequence1'] = sequence
#            return super(sale_order_line, self).create(cr, uid, values, context)
#        except:
#            return super(sale_order_line, self).create(cr, uid, values, context)
        
    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'discount':0})
        return super(sale_order_line, self).copy_data(cr, uid, id, default, context=context)
    
    def _check_qty_line(self, cr, uid, ids):
        b = True
        for line in self.browse(cr, uid, ids):
            categ = self.pool.get('product.uom.categ').browse(cr, uid, line.product_uom.id).decimals
            if categ == False:
                valor = str(line.product_uom_qty)
                dec = valor.split('.')
                if (int(dec[1]) > 0):
                    b = False
            else:
                b = True
        return b

# Create columns
    _columns = {
            'categ_id': fields.function(_get_categ_id, fnct_search=_categ_id_search, obj="product.category", method=True, type="many2one", string='Category'),
            'discount_price': fields.float('PVP', digits_compute=dp.get_precision('Sale Price')),  # Price without discount
#            'discount_order': fields.float('Discount Price', digits_compute=dp.get_precision('Sale Price')), # Discount value based in list price
#            'discount_order_total': fields.float('Total Discount', digits_compute=dp.get_precision('Sale Price')), # Discount value based in list price
#            'discount_percent': fields.float('% Disc.', digits_compute=dp.get_precision('Sale Price')), # Price with discount
           # "discount_price":fields.function(_line_attr, method=True,multi='sale_order_line_amount', string='PVP', store=True, digits_compute=dp.get_precision('Sale Price')),
            "discount_order":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Discount Price', store=True, digits_compute=dp.get_precision('Sale Price')),
            "discount_order_total":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Total Discount', store=True, digits_compute=dp.get_precision('Sale Price')),
            "discount_percent":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='% Disc', store=True, digits_compute=dp.get_precision('Sale Price')),
            'price_unit': fields.function(_get_amount, method=True, string='Unit Price', store=True, digits_compute=dp.get_precision('Sale Price')),
            'price_subtotal': fields.function(_amount_line_all, method=True, string='Subtotal',digits_compute=dp.get_precision('Sale Price'),store=True),
#            'price_subtotal_incl': fields.float('Subtotal', digits_compute=dp.get_precision('Sale Price')),
#            'offer_value': fields.float('$ Offer', digits_compute=dp.get_precision('Sale Price')), # Offer value of line
#            'offer_value_total': fields.float('Total Offer', digits_compute=dp.get_precision('Sale Price')), # Total Offer of line
#            'margin_unit': fields.float('Margin Unit', digits_compute=dp.get_precision('Sale Price')), # Margin value of sale order line
#            'margin': fields.float('Margin', digits_compute=dp.get_precision('Sale Price')), # Margin value of sale order line
#            'margin_percent': fields.float('% Margin', digits_compute=dp.get_precision('Sale Price')), # Margin value of sale order line
#            'purchase_price': fields.float('Cost Price', digits_compute=dp.get_precision('Sale Price')), # Purchase price of sale order line
#            'total_cost_line': fields.float('Total Cost', digits_compute=dp.get_precision('Sale Price')), # Total Cost of sale order line
            'discount': fields.float('Discount (%)', digits_compute=dp.get_precision('Sale Price'), readonly=True, states={'draft': [('readonly', False)]}),
             "price_subtotal_incl":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Subtotal', store=True, digits_compute=dp.get_precision('Sale Price')),
            "offer_value":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='$ Offer', store=True, digits_compute=dp.get_precision('Sale Price')),
            "offer_value_total":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Total Offer', store=True, digits_compute=dp.get_precision('Sale Price')),
            "margin_unit":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Margin Unit', store=True, digits_compute=dp.get_precision('Sale Price')),
            "margin":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Margin', store=True, digits_compute=dp.get_precision('Sale Price')),
            "margin_percent":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='% Margin', store=True, digits_compute=dp.get_precision('Sale Price')),
            "purchase_price":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Cost Price', store=True, digits_compute=dp.get_precision('Sale Price')),
            "total_cost_line":fields.function(_line_attr, method=True, multi='sale_order_line_amount', string='Total Cost', store=True, digits_compute=dp.get_precision('Sale Price')),
            'authorized':fields.boolean('flag', required=False),
            'name': fields.char('Description', size=256, required=False, select=True, readonly=True, states={'draft': [('readonly', False)]}),
            'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True, required=False),
        }
    
    _defaults = {'authorized': lambda *a: False,
                 'sequence': 0,
                 'product_uom' : _get_uom_id,
                 }
    
    _constraints = [(_check_qty_line, 'The UOM no permitted quantity with decimals', ['product_uom_qty'])]
sale_order_line()



class sale_order(osv.osv):
    _inherit = "sale.order"
    _name = "sale.order"

#    def _amount_all_vat(self, cr, uid, ids, name, args, context=None):
#        res = {}
#        amount_tax = 0.0
#        for order in self.browse(cr, uid, ids, context=context):
#            res[order.id] = 0.0
#            for line in order.order_line:
#                for ab in line.product_id.taxes_id:
#                    if ab.tax_code_id.tax_type == 'vat':
#                        amount_tax += line.price_subtotal * ab.amount
#            res[order.id]= amount_tax
#        return res
        
    def _amount_all_vat_12(self, cr, uid, ids, name, args, context=None): 
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = 0.0
            for line in order.order_line:
                for ab in line.tax_id:
                    if ab.tax_code_id.tax_type == 'vat':
                        if ab.tax_code_id.code == 't601':     
                            res[order.id] += line.price_subtotal * ab.amount
        return res

#    def _amount_all_vat_00(self, cr, uid, ids, name, args, context=None):
#        res = {}
#        amount_tax = 0.0
#        for order in self.browse(cr, uid, ids, context=context):
#            res[order.id] = 0.0
#            for line in order.order_line:
#                for ab in line.product_id.taxes_id:
#                    if ab.description == '600':
#                        amount_tax += line.price_subtotal * ab.amount
#            res[order.id]= amount_tax
#        return res
        
# Add segmento, salesman, modified date_order, create_date, date_confirm for driver dates and time, and note.

    def _product_calculate_line(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for sale in self.browse(cr, uid, ids, context=context):
            result[sale.id] = {'totaldiscount':0.0,
                               'totaloffer':0.0,
                               'margin_val':0.0,
                               'totalqty':0,
                               
                               }
            for line in sale.order_line:
                result[sale.id]['totalqty'] += line.product_uom_qty or 0.0
                result[sale.id]['totaldiscount'] += line.discount_order_total or 0.0
                result[sale.id]['totaloffer'] += line.offer_value * line.product_uom_qty or 0.0
                result[sale.id]['margin_val'] += line.margin or 0.0
                
        return result
        
    

#    def _product_discount(self, cr, uid, ids, field_name, arg, context=None):
#        result = {}
#        for sale in self.browse(cr, uid, ids, context=context):
#            result[sale.id] = 0.0
#            for line in sale.order_line:
#                result[sale.id] += line.discount_order_total or 0.0
#        return result
#
#    def _product_offer(self, cr, uid, ids, field_name, arg, context=None):
#        result = {}
#        for sale in self.browse(cr, uid, ids, context=context):
#            result[sale.id] = 0.0
#            for line in sale.order_line:
#                if line.discount>0:
#                    result[sale.id] += line.discount_order_total or 0.0
#        return result
#
#    def _product_qty(self, cr, uid, ids, field_name, arg, context=None):
#        result = {}
#        for sale in self.browse(cr, uid, ids, context=context):
#            result[sale.id] = 0.0
#            for line in sale.order_line:
#                result[sale.id] += line.product_uom_qty or 0.0
#        return result

#    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
#        result = {}
#        for sale in self.browse(cr, uid, ids, context=context):
#            result[sale.id] = 0.0
#            for line in sale.order_line:
#                result[sale.id] += line.margin or 0.0
#        return result
    
    def _margin_total_percent(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for sale in self.browse(cr, uid, ids, context=context):
            result[sale.id] = 0.0
            if sale.margin_val > 0 and sale.amount_untaxed > 0:
                result[sale.id] = (sale.margin_val / sale.amount_untaxed) * 100
        return result

    def _get_order(self, cr, uid, ids, context=None):
        return super(sale_order, self.pool.get('sale.order'))._get_order(cr, uid, ids, context=context)
        
    def _get_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('type', 'pos_order')
       
    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        tp = context.get('type', False)
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.printer_point_ids:
            if tp == 'sale_order':
                if s.shop_id.wholesale:
                    return s.shop_id.id
            elif tp == 'consignment':
                if s.shop_id.consignment:
                    return s.shop_id.id
            elif tp == 'pos_order':
                if s.shop_id.point_of_sale:
                    return s.shop_id.id
            elif tp == 'headquarter':
                if s.shop_id.headquarter:
                    return s.shop_id.id
        return None

    def _get_company_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.company_ids:
            company_id = curr_user.company_ids[0].id
            return company_id
        return None



    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val1 = 0.0
            amount_tax = 0.0
            for line in order.order_line:
                val1 += line.price_subtotal
                for ab in line.tax_id:
                    if ab.tax_code_id.tax_type == 'vat':
                        amount_tax += line.price_subtotal * ab.amount
            res[order.id]['amount_tax'] = amount_tax
            res[order.id]['amount_untaxed'] = val1
            res[order.id]['amount_total'] = val1 + amount_tax
        return res
        
    def _get_date_valid(self,cr,uid,context=None):
        days=self.pool.get("res.users").browse(cr,uid,uid,context=context).company_id.number_days_validate or 0
        return (datetime.now() + relativedelta(days=days)).strftime('%Y-%m-%d')
        
    def _get_salesman(self, cr, uid, context=None):
        res = self.pool.get('salesman.salesman').search(cr, uid, [('user_id', '=', uid)])
        return res and res[0] or None
    
    def _get_segmento(self, cr, uid, context=None):
        res = self.pool.get('res.partner.segmento').search(cr, uid, [('is_default', '=', True)])
        return res and res[0] or None


    _columns = {
        'carrier_id':fields.many2one("delivery.carrier", "Delivery Method", readonly=True, states={'draft': [('readonly', False)]}, help="Complete this field if you plan to invoice the shipping based on picking."),
        'invoice_later': fields.boolean('Invoice Later?', readonly=True, states={'draft': [('readonly', False)]}),
        'is_backorder':fields.boolean('Is Backorder?', required=False),
        'name': fields.char('Order Reference', size=64, required=True, readonly=True, select=True),
        'printer_id':fields.many2one('printer.point', 'Printer Point', readonly=True, states={'draft':[('readonly', False)]}, domain="[('shop_id', '=', shop_id)]"),
        'note':fields.char('Notes', size=64, states={'draft': [('readonly', False)]}),
        'is_superv': fields.related('user_id', 'is_supervisor', string='is supervisor', type='boolean', readonly=True),
        # 'is_superv': fields.boolean('is_superv', required=False),
        # 'pricelist_id1': fields.many2one('product.pricelist', 'Pricelist', readonly=True, help="Pricelist for current sales order."),
        'payment_term': fields.many2one('account.payment.term', 'Payment Term', required=True, readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position', required=True, readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'segmento_id':fields.many2one('res.partner.segmento', 'Segmento', readonly=True, states={'draft': [('readonly', False)]},),
        'salesman_id': fields.many2one('salesman.salesman', 'Assigned Salesman', readonly=True, states={'draft': [('readonly', False)]},),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'date_order': fields.datetime('Ordered Date', required=True, readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True, help="Date on which sales order is created."),
        'date_confirm': fields.datetime('Confirmation Date', select=True, help="Date on which sales order is confirmed."),
        'date_valid': fields.date('Valid Date', required=True, readonly=True, select=True, help="Date on which quotation order expired.", states={'draft': [('readonly', False)]}),
        'totaldiscount': fields.function(_product_calculate_line, method=True, type="float", digits_compute=dp.get_precision('Sale Price'), string='Discount', store=True, multi='products'),
        'totaloffer': fields.function(_product_calculate_line, method=True, type="float", digits_compute=dp.get_precision('Sale Price'), string='Offer', store=True, multi='products'),
        'totalqty': fields.function(_product_calculate_line, method=True, type="float", digits_compute=dp.get_precision('Product UoM'), string='Total Qty', store=True, multi='products'),
        'margin_val': fields.function(_product_calculate_line, method=True, string='Margin', digits_compute=dp.get_precision('Sale Price'), store=True, help="It gives profitability by calculating the difference between the Unit Price and Cost Price.", multi='products'),
        # 'amount_total_vat': fields.function(_amount_all_vat, method=True, digits_compute=dp.get_precision('Sale Price'), string='Total',store=True),
        'amount_total_vat_12': fields.function(_amount_all_vat_12, method=True, digits_compute=dp.get_precision('Sale Price'), string='VAT 12%', store=True),
        # 'amount_total_vat_00': fields.function(_amount_all_vat_00, method=True, digits_compute=dp.get_precision('Sale Price'), string='VAT 0%',store=True),
        'enddate': fields.datetime('End Date'),
        'margin_total_percent': fields.function(_margin_total_percent, method=True, digits_compute=dp.get_precision('Sale Price'), string='Margin Total %', store=True),
        'authorized':fields.boolean('authorized', required=False),
        'verify':fields.boolean('verify', required=False),
        'wizard_auth':fields.boolean('wizard auth', required=False),
        'supervisor_id':fields.many2one('res.users', 'Supervisor', required=False),
        'date_authorized': fields.datetime('Date Authorization'),
        'nb_sale_order':fields.integer('Number of Sale Order Print', readonly=True),
        'print_status_sale_order': fields.char('Sale Order Print Status', size=32),
        'nb_quotation_order':fields.integer('Number of Quotation Order Print', readonly=True),
        'print_status_quotation_order': fields.char('Quotation Print Status', size=32),
        'company_id': fields.many2one('res.company','Company',readonly=True, states={'draft': [('readonly', False)]},),
        'type':fields.selection([('sale_order', 'Sale Order'), ('pos_order', 'POS Order'), ('consignment', 'Consignment'), ], 'Type', readonly=True),
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Sale Price'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax."),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Sale Price'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Sale Price'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),

        }

    _order = 'name desc, shop_id asc'

    _defaults = {
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_confirm': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_valid': _get_date_valid,
        'invoice_quantity': 'procurement',
        'salesman_id': _get_salesman,
        'segmento_id': _get_segmento,
        'authorized': lambda *a: True,
        'type': _get_type,
        'shop_id':_get_shop,
        'nb_sale_order':0,
        'nb_quotation_order':0,
        'order_policy': 'picking',
#        'company_id': lambda self, cr, uid, context: self.pool.get('res.company').search(cr, uid, [('id','=',1)])[0] or False,
        'company_id': _get_company_id, 
        'carrier_id': lambda self, cr, uid, context: self.pool.get('delivery.carrier').search(cr, uid, [('name','=','RETIRO PERSONAL')])[0] or False,
    }
    
           
#     def onchange_address_id(self, cr, uid, ids, address_order_id, context=None):
#         salesman_partner_id = False
#         if address_order_id:
#             address = self.pool.get('res.partner.address').browse(cr, uid, address_order_id, context)
#             salesman_partner_id = address.salesman_assigned.id
#         return {'value': {'salesman_id': salesman_partner_id}}
    
    def onchange_partner_id(self, cr, uid, ids, partner_id=False,context=None):
        value = {}
        if not partner_id:
            return {'value': {'segmento_category_id':False,'partner_invoice_id': False, 'partner_shipping_id': False, 'partner_order_id': False, 'payment_term': False, 'fiscal_position': False}}
        addr = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['delivery', 'invoice', 'contact'])
        part = self.pool.get('res.partner').browse(cr, uid, partner_id)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
        value = {
            'partner_invoice_id': addr['invoice'],
            'partner_order_id': addr['contact'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': dedicated_salesman,
        }
        add= addr['contact']
        if pricelist:
            value['pricelist_id'] = pricelist
        vals=value
        brw_res_partner=self.pool.get("res.partner").browse(cr,uid,partner_id,context=context)
        vals['segmento_category_id']=brw_res_partner.segmento_category_id and brw_res_partner.segmento_category_id.id or False
        add_part = self.pool.get('res.partner.address').browse(cr,uid,add)
        vals['salesman_id']=add_part.salesman_assigned.id
        return {'value':value}
    
    def onchange_shop_id(self, cr, uid, ids, shop_id, company_id, context=None):
        if context is None:
            context = {}
        printer_obj = self.pool.get('printer.point')
        curr_user = self.pool.get('res.users').browse(cr, uid, [uid, ], context)[0]
        shop_ids = []
        printer_point_ids = []
        box_id = None
        if not company_id:
            for s in curr_user.company_ids:
                company_id = curr_user.company_ids[0].id                
        # Se verifica que el usuario tenga tiendas asignadas
        if not curr_user.printer_point_ids:
            raise osv.except_osv(_('Warning!'), _("You do not have Cash Box assigned, please check"))
        for s in curr_user.printer_point_ids:
            printer_point_ids.append(s.id)
#        Se valida que las tiendas que tenga el usuario asiganda sean del tipo correcto de donde se crea la orden de venta
        type = context.get('type', 'headquarter')
        if type == 'sale_order':
            for box in printer_obj.browse(cr, uid, printer_point_ids, context):
                if box.shop_id.wholesale:
                    shop_ids.append(box.shop_id.id)
        if type == 'consignment':
            for box in printer_obj.browse(cr, uid, printer_point_ids, context):
                if box.shop_id.consignment:
                    shop_ids.append(box.shop_id.id)
        if type == 'pos_order':
            for box in printer_obj.browse(cr, uid, printer_point_ids, context):
                if box.shop_id.point_of_sale:
                    shop_ids.append(box.shop_id.id)
        v = {}
        if shop_id and company_id:
            shop = self.pool.get('sale.shop').browse(cr, uid, shop_id)        
            if shop.company_id.id != company_id:
                sh_ids = self.pool.get('sale.shop').search(cr, uid, [('company_id','=',company_id)])
                shop_id = sh_ids[0]
                v['shop_id']=shop_id 
        else:
            sh_ids = self.pool.get('sale.shop').search(cr, uid, [('company_id','=',company_id)])[0]
            shop_id = sh_ids
            v['shop_id']=shop_id        
        if shop_id:
            shop = self.pool.get('sale.shop').browse(cr, uid, shop_id)
            print_point = self.pool.get('printer.point').search(cr, uid, [('shop_id','=',shop_id)])[0]
            print_id = self.pool.get('printer.point').browse(cr,uid,print_point)
            v['project_id'] = shop.project_id.id
            v['location_id'] = shop.warehouse_id.lot_stock_id.id
            v['printer_id'] = print_id.id
            # Que faire si le client a une pricelist a lui ?
            if shop.pricelist_id.id:
                v['pricelist_id'] = shop.pricelist_id.id
                # v['pricelist_id1'] = shop.pricelist_id.id
            if type in ('sale_order', 'consignment', 'pos_order') :
                box_id = printer_obj.search(cr, uid, [('id', 'in', printer_point_ids), ('shop_id', '=', shop_id)])
            if box_id:
                v['printer_id'] = box_id[0]
            if curr_user.is_supervisor:
                v['is_superv'] = True
            
        return {'value': v, 'domain':{'printer_id':[('shop_id', '=', shop_id)]}}
        
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'authorized': True, 'verify': False, 'wizard_auth': False, 'date_order': time.strftime('%Y-%m-%d %H:%M:%S')})
        return super(sale_order, self).copy(cr, uid, id, default, context=context)
    
#    def write(self, cr, uid, ids, values, context=None):
#        try:
#            pricelist = values['pricelist_id']
#            values['pricelist_id1'] = pricelist
#            return super(sale_order, self).write(cr, uid, ids, values, context)
#        except:
#            return super(sale_order, self).write(cr, uid, ids, values, context)
#        
#    def create(self, cr, uid, values, context=None):
#        try:
#            pricelist = values['pricelist_id']
#            values['pricelist_id1'] = pricelist
#            return super(sale_order, self).create(cr, uid, values, context)
#        except:
#            return super(sale_order, self).create(cr, uid, values, context)
        
    def verify_auth(self, cr, uid, ids, context=None):
        for sale in self.browse(cr, uid, ids):
            if sale.order_line:
                for line in sale.order_line:
                    if not line.authorized:
                        cr.execute("""UPDATE sale_order set authorized = False, wizard_auth = False WHERE id = %s""", (sale.id,))
                        return False
        return True
    
    def verify_sale_order(self, cr, uid, ids, context=None):
        self.button_dummy(cr, uid, ids, context)
        for sale in self.browse(cr, uid, ids):
            b = True
            lines_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale.id), ('authorized', '=', False)])
            if lines_ids:
                b = False
            sale.write({'authorized':b, 'verify':True})
        return True
    
    def button_dummy(self, cr, uid, ids, context=None):
        for sale in self.browse(cr, uid, ids, context):
            lines_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale.id), ('product_uom_qty', '<=', 0)])
            if lines_ids:
                raise osv.except_osv(_('Error!!'), _('Can not exist lines of products with quantity 0'))
        return self.write(cr, uid, ids, {}, context)
    
    def action_cancel_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'authorized': True, 'verify': False, 'wizard_auth': False})
        return super(sale_order, self).action_cancel_draft(cr, uid, ids, args)
    
    def action_wait(self, cr, uid, ids, *args):
        for sale in self.browse(cr, uid, ids, context=None):
            cr.execute(sql, (sale.shop_id.id, 'sale'))
            res = cr.fetchall()
            if not res:
                raise osv.except_osv(_('Error!!'), _('You must assign a Sales Journal for the shop %s') % sale.shop_id.name)
            lines_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale.id), ('authorized', '=', False)])
            if lines_ids:
                raise osv.except_osv(_('Warning!'), _("You need authorization to do this sales, Press Calculate and digit the authorization"))
        return super(sale_order, self).action_wait(cr, uid, ids, args)
    
    def _get_date_planned(self, cr, uid, order, line, start_date, context=None):
        date_planned = datetime.strptime(start_date, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=line.delay or 0.0)    
        date_planned = (date_planned - timedelta(days=order.company_id.security_lead)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return date_planned
    
    def _prepare_order_picking(self, cr, uid, order, context=None):
        if order.segmento_id:
            segmento = order.segmento_id.id
        else:
            segmento_ids = self.pool.get('res.partner.segmento').search(cr, uid, [('is_default', '=', True)],)
            segmento = segmento_ids and segmento_ids[0] or None
        if order.salesman_id:
            salesman = order.salesman_id.id
        else:
            salesman_ids = self.pool.get('salesman.salesman').search(cr, uid, [('name', '=', uid)])
            salesman = salesman_ids and salesman_ids[0] or False
        pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.out')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': order.date_order,
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'sale_id': order.id,
            'partner_id': order.partner_id.id,
            'address_id': order.partner_order_id.id,
            'note': order.note,
            'invoice_state': (order.order_policy == 'picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
            'carrier_id':order.carrier_id.id or order.partner_id.property_delivery_carrier.id or None,
            'shop_id': order.shop_id.id,
            'warehouse_id':uid,
            'segmento_id': segmento,
            'salesman_id': salesman,
            'digiter_id': order.user_id.id,
            'local_address_partner': order.partner_order_id.name,
            'address_partner':order.partner_order_id.street,
            'more_information':order.carrier_id.more_information,
            'printer_id':order.printer_id.id,
            'invoice_later':order.invoice_later or False,
        }
            
    def get_prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        if order.location_id:
            location_id = order.location_id.id
        else:
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id
        ubication = None
        ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id', '=', line.product_id.id), ('location_ubication_id', '=', location_id)])
        if ubication_ids:
            ubication = self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
        return {
            'name': line.name[:250],
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'address_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            # 'state': 'waiting',
            'note': line.notes,
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0,
            'ubication_id':ubication
        }
    
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        return self.get_prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context)
        
    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Create the required procurements to supply sale order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sale order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sale order to which the order lines belong
        :param list(browse_record) order_lines: sale order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if ommitted.
        :return: True
        """
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []

        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)

            if line.product_id:
                if line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    if not picking_id:
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                    move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context))
                else:
                    # a service has no stock move
                    move_id = False

#                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context))
#                proc_ids.append(proc_id)
#                line.write({'procurement_id': proc_id})
#                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")
        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            self.pool.get('stock.picking').action_assign(cr, uid, [picking_id, ])

        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True
    
    def _inv_get(self, cr, uid, order, context=None):
        inv_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        cr.execute(sql, (order.shop_id.id, 'sale'))
        res = cr.fetchall()
        if not res:
            raise osv.except_osv(_('Error !'),
                _('There is no sales journal defined for this shop: "%s" (id:%d)') % (order.shop_id.name, order.shop_id.id))
        result = inv_obj.onchange_cash(cr, uid, [], order.company_id.id, order.shop_id.id, 'out_invoice', order.printer_id.id, res[0][0])['value']
        result['journal_id'] = res[0][0]
        result['printer_id'] = order.printer_id.id
        result['document_type'] = inv_obj._document_type(cr, uid, {'journal_type':journal_obj.browse(cr, uid, res[0][0],).type})
        return result
    
    def manual_invoice(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        wf_service = netsvc.LocalService("workflow")
        inv_ids = set()
        inv_ids1 = set()
        pik_ids = []
        b = True
        for id in ids:
            printer_id = self.pool.get('sale.order').browse(cr, uid, id).printer_id.id
            line_auth_obj = self.pool.get('sri.authorization.line')
            line_auth_ids = line_auth_obj.search(cr, uid, [('name', '=', 'sale'), ('printer_id', '=', printer_id), ('state', '=', True)])
            for line in line_auth_ids:
                if line_auth_obj.browse(cr, uid, line, context).type_printer == 'manual':
#            if self.pool.get('sale.order').browse(cr, uid, id).printer_id.type_printer == 'manual':           
                    b = False
            for record in self.pool.get('sale.order').browse(cr, uid, id).invoice_ids:
                inv_ids.add(record.id)
        # inv_ids would have old invoices if any
        for id in ids:
            wf_service.trg_validate(uid, 'sale.order', id, 'manual_invoice', cr)
            for record in self.pool.get('sale.order').browse(cr, uid, id).invoice_ids:
                inv_ids1.add(record.id)
            # capturo los picking que fueron generados en el proceso anterior del workflow
            for picking in self.pool.get('sale.order').browse(cr, uid, id).picking_ids:
                if picking.state not in ('draft', 'cancel'):
                    pik_ids.append(picking.id)
                    self.pool.get('stock.picking').action_assign(cr, uid, [picking.id], context)
                    wf_service.trg_validate(uid, 'stock.picking', picking.id, 'button_done', cr)
        inv_ids = list(inv_ids1.difference(inv_ids))
        
        if inv_ids:
            # picking=self.pool.get('account.invoice').browse(cr, uid, inv_ids[0], context).picking_id.id or None
            self.pool.get('stock.picking').write(cr, uid, pik_ids, {
                'invoice_state': 'invoiced',
                'invoice_ids': [[6, 0, inv_ids]]}, context=context)
            if b:
                wf_service.trg_validate(uid, 'account.invoice', inv_ids[0], 'invoice_open', cr)

        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False,
        return {
            'name': _('Customer Invoices'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }
    
    def _get_vals(self, vals):
        new_invoice_line = []
        invoice_line_list = vals.get('order_line', [])
        for line in invoice_line_list:
            if line[0] in (0, 1):
                if(line[2].has_key("product_uom_qty")):
                    if(not line[2].get("product_uom_qty", 0)):
                        continue
                if(line[2].get('product_id', False) != False and line[2].get('name', False) != False):
                    new_invoice_line.append(line)                   
            elif line[0] == 2:
                new_invoice_line.append(line)
            else:
                new_invoice_line.append(line)
        if invoice_line_list:
            vals.update({'order_line':new_invoice_line})
        return vals
    
    def create(self, cr, uid, vals, context=None):
        vals = self._get_vals(vals)
        return super(sale_order, self).create(cr, uid, vals, context)
    
    def write(self, cr, uid, ids, vals, context=None):
        vals = self._get_vals(vals)
        return super(sale_order, self).write(cr, uid, ids, vals, context)
    
    def authorize_sale_order(self, cr, uid, ids, context=None):
        context=(context is None) and {} or context
        for brw_sale_order in self.browse(cr, uid, ids, context=context):
            if(not brw_sale_order.company_id.authorize_sales_order):
                if(not brw_sale_order.authorized):
                    line_ids=[ line.id for line in brw_sale_order.order_line]
                    self.pool.get("sale.order.line").write(cr,uid,line_ids,{'authorized':True},context)
                    self.write(cr, uid,[brw_sale_order.id],{'authorized':True, 'wizard_auth':True,'supervisor_id':uid,'date_authorized':time.strftime('%Y-%m-%d %H:%M:%S')}, context)
            else:                
                new_context=context.copy()
                new_context.update({"active_model":"sale.order","type":"sale_order",'search_default_user_id': uid,"active_id":ids[0],"active_ids":ids})
                return{
                    'name':_("Validate Offer"),
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'wizard.authorization',
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'context': new_context
                    }
        return True

sale_order()
