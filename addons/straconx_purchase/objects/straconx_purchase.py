# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
##############################################################################


from osv import fields
from osv import osv
import time
from account_voucher import account_voucher
from datetime import datetime
from dateutil.relativedelta import relativedelta

import decimal_precision as dp
from tools.translate import _
import netsvc
from tools import amount_to_text_es
import base64,os,shutil,tarfile,StringIO,urllib


class purchase_category(osv.osv):
    _name = "purchase.category"
    _description = "Purchase Category"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=6),
        'info_required': fields.boolean('Info Aditional in Purchase'),
        'origin': fields.selection([('local', 'Local'), ('international', 'International')], 'Origin'),
    }

purchase_category()
# Based in purchase_discount module of Tiny SPRL.


class purchase_order_line(osv.osv):

    _name = "purchase.order.line"
    _inherit = "purchase.order.line"

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

    def _get_uom_id(self, cr, uid, context=None):
        return False

    _columns = {
        'order_id': fields.many2one('purchase.order', 'Order Reference', select=True, required=False, ondelete='cascade'),
        'date_planned': fields.date('Scheduled Date', readonly=False, select=True),
        'price_with_tax': fields.related('order_id', 'price_with_tax', type='boolean', string='Price with Tax', readonly=False),
        'discount': fields.float('Discount (%)', digits_compute=dp.get_precision('Purchase Price')),
        'offer': fields.float('Offer (%)', digits_compute=dp.get_precision('Purchase Price')),
        'discount_order': fields.float('$ Discount', digits_compute=dp.get_precision('Purchase Price')),
        'product_qty': fields.float('Quantity'),
        'categ_id': fields.many2one('product.category', 'Category'),
        'weight': fields.float('Gross weight', help="The gross weight in Kg."),
        'weight_total': fields.float('Total Weight', help="The gross weight in Kg."),
        'volume': fields.float('Volume', help="The volume in m3."),
        'volume_total': fields.float('Total Volume', help="The volume in m3."),
        'offer_order_total': fields.float('Total Offer', digits_compute=dp.get_precision('Purchase Price')),
        'discount_order_total': fields.float('Total Discount', digits_compute=dp.get_precision('Purchase Price')),
        'subtotal_with_taxes': fields.float('Subtotal with Taxes', digits_compute=dp.get_precision('Purchase Price')),
        'final_price': fields.float('Final Price', digits_compute=dp.get_precision('Purchase Price')),
        'price_subtotal': fields.float('Subtotal', digits_compute=dp.get_precision('Purchase Price')),
        'department_id': fields.many2one('hr.department', 'Departmento'),
        'cost_journal': fields.many2one('account.analytic.journal', 'Cost Journal'),

    }
    _defaults = {
        'discount': lambda *a: 0.0,
        'product_uom': _get_uom_id,
    }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty, uom, partner_id, categ_id=False, date_order=False, fiscal_position=False,
                          date_planned=False, name=False, price_unit=False, notes=False, discount=False, offer=False, shop_id=False,
                          price_with_tax=False, context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        account_tax_obj = self.pool.get('account.tax')
        uom_id = None
        taxes = False
        amount_tax = 0.0
        if not pricelist:
            raise osv.except_osv(_('No Pricelist !'),
                                 _('You have to select a pricelist or a supplier in the purchase form !\n Please set one before choosing a product.'))
        if not partner_id:
            raise osv.except_osv(_('No Partner!'),
                                 _('You have to select a partner in the purchase form !\nPlease set one partner before choosing a product.'))
        if not product and not name:
            return {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'notes': notes or'',
                              'product_uom': uom or False}, 'domain': {'product_uom': []}}
        if context is None:
            context = {}

        department_id = context.get('department_id', False)
#             price_with_tax = context.get('price_with_tax', False)
#         if shop_id:
#             shop = self.pool.get('sale.shop').read(cr,uid, shop_id, ['project_id'])['project_id']
#             if shop:
#                 account_analytic_id = shop
#             else:
#                 raise osv.except_osv(_('Error!'), _('You need a analytic account for continue.'))
        product_uom_pool = self.pool.get('product.uom')
        prod_name = name
        lang = False
        if partner_id:
            lang = self.pool.get('res.partner').read(cr, uid, partner_id, ['lang'])['lang']
        context['lang'] = lang
        context['partner_id'] = partner_id
        res = {}
        price_subtotal = 0.00
        prod_weight = 0.00
        weight_total = 0.00
        prod_volume = 0.00
        volume_total = 0.00
        res3 = False

        if uom:
            uom_id = product_uom_pool.browse(cr, uid, uom)
        if not date_order:
            date_order = time.strftime('%Y-%m-%d')
        qty = qty or 1.0
        seller_delay = 0
        dt = (datetime.now() + relativedelta(days=int(seller_delay) or 0.0)).strftime('%Y-%m-%d %H:%M:%S')

        prod = self.pool.get('product.product').browse(cr, uid, product, context=context)
        if prod:
            prod_uom_po = prod.uom_po_id
            categ_id = prod.categ_id.id
            prod_weight = prod.weight
            prod_name = self.pool.get('product.product').name_get(cr, uid, [prod.id], context=context)[0][1]
            weight_total = 0
            if prod.weight > 0:
                weight_total = prod_weight * qty

            prod_volume = prod.volume
            volume_total = 0
            if prod.volume > 0:
                volume_total = prod_volume * qty

            if not uom or uom_id.category_id.id != prod_uom_po.category_id.id:
                uom = prod_uom_po.id
            for s in prod.seller_ids:
                if s.name.id == partner_id:
                    seller_delay = s.delay
                    if s.product_uom:
                        temp_qty = product_uom_pool._compute_qty(cr, uid, s.product_uom.id, s.min_qty, to_uom_id=prod.uom_id.id)
                        temp_qty = float('%.2f' % temp_qty)
                        uom = s.product_uom.id  # prod_uom_po
                    temp_qty = s.min_qty  # supplier _qty assigned to temp
                    if qty < temp_qty:  # If the supplier quantity is greater than entered from user, set minimal.
                        qty = temp_qty
                        res.update({'warning': {'title': _('Warning'),
                                                'message': _('The selected supplier has a minimal quantity set to %s, you cannot purchase less.')
                                                % qty}})
            qty_in_product_uom = product_uom_pool._compute_qty(cr, uid, uom, qty, to_uom_id=prod.uom_id.id)
            qty_in_product_uom = float('%.2f' % qty_in_product_uom)
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                                                                 product, qty_in_product_uom or 1.0, partner_id,
                                                                 {'uom': uom,
                                                                  'date': date_order,
                                                                  'type': 'in_invoice'
                                                                  })[pricelist]
            prod_price = context.get('product_id', False)
            if prod_price:
                price_unit = price
            elif not prod_price:
                price_unit = price
            else:
                price_unit = price_unit
            if not taxes:
                taxes = account_tax_obj.browse(cr, uid, map(lambda x: x.id, prod.supplier_taxes_id))
            res3 = prod.uom_id.category_id.id

        if price_unit and price_with_tax:
            if taxes:
                for t in taxes:
                    tax_ids = t.id
                    if tax_ids:
                        tax_code = account_tax_obj.browse(cr, uid, tax_ids)
                        if tax_code.ref_base_code_id.tax_type == 'vat':
                            amount_tax = 0.0
                            amount_tax = price_unit * tax_code.amount
            else:
                amount_tax = 0.0
                price_final = price_unit
        else:
            amount_tax
            price_final = price_unit

        if price_unit:
            if discount > 0 or offer > 0:
                price_final = price_unit*(1 - discount/100)*(1 - offer/100)
                discount_order = price_unit * discount/100
                price_subtotal = qty * price_final
            else:
                price_final = price_unit
                discount_order = 0
                price_subtotal = qty * price_unit
            price_final = price_final + amount_tax
            price_subtotal = qty * price_final
        else:
            price_final = 0.00
            discount_order = 0.00
            price_subtotal = 0.00

        res.update({'value': {'price_unit': price_unit, 'name': prod_name, 'taxes_id': taxes,
                              'final_price': price_final, 'price_subtotal': price_subtotal, 'deparment_id': department_id,
                              'date_planned': date_planned or dt, 'discount_order': discount_order,
                              'notes': notes or prod.description_purchase, 'product_qty': qty, 'categ_id': categ_id,
                              'weight': prod_weight, 'weight_total': weight_total, 'volume': prod_volume,
                              'volume_total': volume_total, 'product_uom': uom}})
        domain = {}

        if taxes:
            fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
            res['value']['taxes_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)

        if uom:
            res2 = self.pool.get('product.uom').read(cr, uid, [uom], ['category_id'])
            domain = {'product_uom': [('category_id', '=', res2[0]['category_id'][0])]}
            if res3 and res2[0]['category_id'][0] != res3:
                raise osv.except_osv(_('Wrong Product UOM !'),
                                     _('You have to select a product UOM in the same category than the purchase UOM of the product'))
            res['domain'] = domain
        return res

    def offer_id_change(self, cr, uid, ids, product_id, qty, price_unit=0, discount=0, offer=0, price_with_tax=False, taxes=False, context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        res = {}
        tax_vat = 0.00
        account_tax_obj = self.pool.get('account.tax')
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            if not taxes:
                taxes = account_tax_obj.browse(cr, uid, map(lambda x: x.id, product.supplier_taxes_id))
        else:
            product = False
            taxes = []
        if context is None:
            context = {}
        if price_unit and price_with_tax and taxes:
            if taxes:
                if type(taxes) is list:
                    taxes = account_tax_obj.browse(cr, uid, taxes[0][2])
                for t in taxes:
                    tax_ids = t.id
                    if tax_ids:
                        tax_code = account_tax_obj.browse(cr, uid, tax_ids)
                        if tax_code.ref_base_code_id.tax_type == 'vat':
                            tax_vat = tax_code.amount
            else:
                tax_vat = 0.00
        else:
            tax_vat = 0.00

        if discount >= 0 or offer >= 0:
            price_unit = price_unit
            price_final = round(((price_unit/(1+tax_vat))*(1-(discount*0.01)))*(1-(offer*0.01)), dc)
            price_subtotal = round(price_final * qty, dc)
            subtotal_with_taxes = round(price_final*(1+tax_vat)*qty, dc)
            res.update({'value': {'final_price': price_final, 'price_subtotal': price_subtotal, 'price_unit': price_unit,
                                  'subtotal_with_taxes': subtotal_with_taxes}})
        return res

    def create(self, cr, uid, vals, context={}):
        if not vals.get('department_id', False):
            if vals.get('order_id', False):
                order_id = vals.get('order_id', False)
                department_id = self.pool.get('purchase.order').browse(cr, uid, order_id).department_id.id or False
                vals['department_id'] = department_id
        if not vals.get('cost_journal', False):
            if vals.get('order_id', False):
                order_id = vals.get('order_id', False)
                cost_journal_id = self.pool.get('purchase.order').browse(cr, uid, order_id).cost_journal.id or False
                vals['cost_journal'] = cost_journal_id
        if not vals.get('account_analytic_id', False):
            raise osv.except_osv(_('¡Aviso!'), _("Necesita asignar una cuenta de costo a cada línea de compra. Por favor, revise."))
        return super(purchase_order_line, self).create(cr, uid, vals, context)

purchase_order_line()


class purchase_order(osv.osv):
    _inherit = "purchase.order"

    def _amount_all_vat(self, cr, uid, ids, name, args, context=None):
        res = {}
        amount_tax = 0.0
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = 0.0
            for line in order.order_line:
                for ab in line.taxes_id:
                    if ab.tax_code_id.tax_type == 'vat':
                        amount_tax += line.price_subtotal * ab.amount
            res[order.id] = amount_tax
        return res

    def _amount_all_vat_12(self, cr, uid, ids, name, args, context=None):
        res = {}
        amount_tax = 0.0
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = 0.0
            for line in order.order_line:
                for ab in line.taxes_id:
                    if ab.tax_code_id.tax_type == 'vat':
                        amount_tax += line.price_subtotal * ab.amount
            res[order.id] = amount_tax
        return res

    def _amount_all_vat_00(self, cr, uid, ids, name, args, context=None):
        res = {}
        amount_tax = 0.0
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = 0.0
            for line in order.order_line:
                for ab in line.taxes_id:
                    if ab.description == '600':
                        amount_tax += line.price_subtotal * ab.amount
            res[order.id] = amount_tax
        return res

    def _purchase_pretotal(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        pretotal = 0.00
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                pretotal += line.price_unit * line.product_qty
            result[order.id] = pretotal
        return result

    def _purchase_discount(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        discount = 0.00
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                discount += line.discount_order_total
            result[order.id] = discount
        return result

    def _purchase_offer(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        offer = 0.00
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                offer += line.offer_order_total
            result[order.id] = offer
        return result

    def _purchase_quantity(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        quantity = 0.00
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                quantity += line.product_qty
            result[order.id] = quantity
        return result

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        amount_tax = 0.0
        amount_tax2 = 0.0
        pretotal = 0.00
        totaldiscount = 0.00
        totaloffer = 0.00
        totalquantity = 0.00
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'pretotal': 0.0,
                'totaldiscount': 0.00,
                'totaloffer': 0.00,
                'totalquantity': 0.00,
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'exempt': 0.0,
                'amount_total_perception': 0.0,
            }
            val1 = 0.0
            val2 = 0.0
            c = 0.00
            d = 0.00
            for line in order.order_line:
                for ab in line.taxes_id:
                    if ab.tax_code_id.tax_type == 'vat':
                        if ab.amount != 0:
                            amount_tax += (line.price_subtotal*ab.amount)
                            val1 += line.price_subtotal
                        else:
                            val2 += line.price_subtotal
                    if ab.tax_code_id.tax_type == 'perception':
                        amount_tax2 += line.price_subtotal * ab.amount_variable
                pretotal += line.subtotal_with_taxes
                totaldiscount += line.discount_order_total
                totaloffer += line.offer_order_total
                totalquantity += line.product_qty
            res[order.id]['amount_tax'] = round(amount_tax, dc)
            res[order.id]['amount_untaxed'] = round(val1, dc)
            res[order.id]['exempt'] = round(val2, dc)
            res[order.id]['amount_total'] = round((res[order.id]['exempt'] + res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] + amount_tax2), dc)
            res[order.id]['pretotal'] = round(pretotal, dc)
            res[order.id]['totaldiscount'] = round(totaldiscount, dc)
            res[order.id]['totaloffer'] = round(totaloffer, dc)
            res[order.id]['totalquantity'] = round(totalquantity, dc)
            res[order.id]['amount_total_perception']= amount_tax2
        return res

    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for purchase in self.browse(cursor, user, ids, context=context):
            tot = 0.0
            if purchase.id == 741:
                print "revisar"
            for invoice in purchase.invoice_ids:
                if invoice.state not in ('draft', 'cancel'):
                    tot += invoice.amount_untaxed
            value_purchase = purchase.amount_untaxed + purchase.exempt
            if value_purchase:
                res[purchase.id] = tot * 100.0 / value_purchase
            else:
                res[purchase.id] = 0.0
        return res

    def _minimum_planned_date(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for purchase in self.browse(cr, uid, ids, context=context):
            if purchase.wait_day <= 0:
                purchase.write({'wait_day': 3})
            purchase.refresh()
            min_date = (datetime.strptime(purchase.date_order, '%Y-%m-%d') + relativedelta(days=int(purchase.wait_day) or 0.0)).strftime('%Y-%m-%d')
            res[purchase.id] = min_date
        return res

#     def _get_order(self, cr, uid, ids, context=None):
#         result = {}
#         for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
#             result[line.order_id.id] = True
#         return result.keys()

    def _get_buy_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        tp = context.get('type', 'headquarter')
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.printer_point_ids:
            if tp == 'headquarter':
                if s.shop_id.headquarter:
                    return s.shop_id.id
        return None

    def _get_buyer(self, cr, uid, context=None):
        salesman_ids = self.pool.get('salesman.salesman').search(cr, uid, [('user_id', '=', uid),
                                                                           ('is_buyer', '=', True)])
        if salesman_ids:
            return uid
        else:
            return None

    def _get_cost_journal(self, cr, uid, context=None):
        cost_ids = self.pool.get('account.analytic.journal').search(cr, uid, [('default', '=', True)])
        if cost_ids:
            return cost_ids[-1]
        else:
            return None

    _columns = {
        'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines', readonly=True,
                                      states={'wait': [('readonly', False)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}),
        'name': fields.char('Order Reference', size=256, required=False),
        'atention': fields.char('Atención', size=64, states={'draft': [('readonly', False)]}),
        'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines', readonly=True, states={'draft': [('readonly', False)]}),
        'categ_id': fields.many2one('product.category', 'Brands', readonly=True, states={'draft': [('readonly', False)]}),
        'type_purchase': fields.many2one('purchase.category', string='Type', readonly=True, states={'draft': [('readonly', False)]}),
        'authorized': fields.many2one('res.users', 'Authorized by', readonly=True, states={'draft': [('readonly', False)]}),
        'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage', '!=', 'view')],
                                       readonly=True, states={'draft': [('readonly', False)]}),
        'solicited': fields.many2one('res.users', 'Solicitado por', readonly=True, states={'draft': [('readonly', False)]}),
        'manufacturer': fields.many2one('res.manufacturer', 'Manufacturer', readonly=True, states={'draft': [('readonly', False)]}),
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'wait_day': fields.integer('Wait day', readonly=True, states={'draft': [('readonly', False)]}),
        'expired_day': fields.integer('Expired day', readonly=True, states={'draft': [('readonly', False)]}),
        'payment_term': fields.many2one('account.payment.term', 'Payment Term', readonly=True, states={'draft': [('readonly', False)]}),
        'tpurchase': fields.selection([('purchase', 'Purchase'), ('expense', 'Expense'), ('fixed_assets', 'Fixed Assets')],
                                      'Purchase type', select=True),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position', readonly=True, states={'draft': [('readonly', False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=1, states={'draft': [('readonly', False)]}),
        'invoice_method': fields.selection([('manual', 'Based on Purchase Order lines'), ('order', 'Based on generated draft invoice'),
                                            ('picking', 'Based on receptions')], 'Invoicing Control', required=True,
                                           help="Based on Purchase Order lines: place individual lines in 'Invoice Control > Based on P.O. lines'"
                                           "from where you can selectively create an invoice.\n"
                                           "Based on generated invoice: create a draft invoice you can validate later.\n"
                                           "Based on receptions: let you create an invoice when receptions are validated.",
                                           states={'draft': [('readonly', False)]}),
        'minimum_planned_date': fields.function(_minimum_planned_date, string='Expected Date', type='date', select=True,
                                                help="This is computed as the minimum scheduled date of all purchase order lines' products.",
                                                store=True),
        'pretotal': fields.function(_amount_all, method=True, type="float", digits_compute=dp.get_precision('Account'), string='Pretotal',
                                    store=True, multi="sums"),
        'totaldiscount': fields.function(_amount_all, method=True, type="float", digits_compute=dp.get_precision('Account'), string='Total Discount',
                                         store=True, multi="sums"),
        'totaloffer': fields.function(_amount_all, method=True, type="float", digits_compute=dp.get_precision('Account'), string='Total Offer',
                                      store=True, multi="sums"),
        'totalquantity': fields.function(_amount_all, method=True, type="float", digits_compute=dp.get_precision('Product UoM'), string='Quantity',
                                         store=True, multi="sums"),
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                                          store=True, multi="sums", help="The amount without tax"),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Taxes',
                                      store=True, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Total',
                                        store=True, multi="sums", help="The total amount"),
        'amount_total_vat': fields.function(_amount_all_vat, method=True, digits_compute=dp.get_precision('Account'), string='Total', store=True),
        'amount_total_vat_12': fields.function(_amount_all_vat_12, method=True, digits_compute=dp.get_precision('Account'),
                                               string='VAT 12%', store=True),
        'amount_total_vat_00': fields.function(_amount_all_vat_00, method=True, digits_compute=dp.get_precision('Account'),
                                               string='VAT 0%', store=True),
        'price_with_tax': fields.boolean('Supplier Prices with Taxes?'),
        'amount_text': fields.char('Amount Text', size=500,),
        'department_id': fields.many2one('hr.department', 'Departmento', readonly=True, states={'draft': [('readonly', False)]}),
        'required_approval': fields.boolean('Required approval?'),
        'validator': fields.many2one('res.users', 'Validated by', states={'draft': [('readonly', False)]}),
        'exempt': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Exent Amount', store=True,
                                  multi="sums", help="The amount without tax"),
        'cost_journal': fields.many2one('account.analytic.journal', 'Cost Journal'),
        'web_link_approve': fields.char('Link', size=500),
        'invoiced_rate': fields.function(_invoiced_rate, string='Invoiced', type='float')
        }

    _sql_constraints = [
        ('wait_day_0', 'CHECK (wait_day>=0)', 'Error! Wait days must be greater tha, Falsen 0.'),
        ('expired_day_0', 'CHECK (expired_day>=0)', 'Error! Expired days must be greater than 0.'),
    ]

    _defaults = {
        'wait_day': 1,
        'shop_id': _get_buy_shop,
        'tpurchase': False,
        'invoice_method': False,
        'solicited': _get_buyer,
        'price_with_tax': lambda *a: 0,
        'name': lambda *a: False,
        'cost_journal': _get_cost_journal
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'state': 'draft',
                        'shipped': False,
                        'invoiced': False,
                        'invoice_ids': [],
                        'picking_ids': [],
                        'name': None,
                        })
        return super(osv.osv, self).copy(cr, uid, id, default, context)

    def onchange_partner_id(self, cr, uid, ids, partner_id, type_purchase):
        warning = {}
        if not partner_id:
            return {'value': {'partner_address_id': False, 'fiscal_position': False}}
        if not type_purchase:
            warning = {'title': _('Error!'), 'message': _(('Need select a type of purchase first.'))}
            return {'value': {'partner_id': False}, 'warning': warning}
        partner = self.pool.get('res.partner')
        tpur = self.pool.get('purchase.category').browse(cr, uid, type_purchase, context=None).origin
        pt = partner.browse(cr, uid, partner_id, context=None)
        supplier_address = partner.address_get(cr, uid, [partner_id], ['default'])
        if pt.origin:
            supplier = partner.browse(cr, uid, partner_id)
            pricelist = supplier.property_product_pricelist_purchase.id
            fiscal_position = supplier.property_account_position and supplier.property_account_position.id or False
            partner_payment_term_id = supplier.property_payment_term_supplier and supplier.property_payment_term_supplier.id or False
            return {'value': {'partner_address_id': supplier_address['default'], 'pricelist_id': pricelist, 'fiscal_position': fiscal_position,
                              'payment_term': partner_payment_term_id}}
        return {"value": {"partner_address_id": supplier_address['default']}}

    def onchange_buy_shop_id(self, cr, uid, ids, shop_id, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        shop_ids = []
        # Se verifica que el usuario tenga tiendas asignadas
        if not curr_user.printer_point_ids:
            raise osv.except_osv(_('Warning!'), _("You do not have shop assigned, please check"))
        tp = context.get('shop', 'headquarter')
        for s in curr_user.printer_point_ids:
            if tp == 'headquarter':
                if s.shop_id.headquarter:
                    shop_ids.append(s.shop_id.id)

        v = {}
        return {'value': v, 'domain': {'shop_id': [('id', 'in', shop_ids)]}}

    def onchange_solicited_id(self, cr, uid, ids, solicited, department_id, required_approval, context=None):
        user_obj = self.pool.get('res.users')
        department_obj = self.pool.get('hr.department')
        employee_obj = self.pool.get('hr.employee')
        manager_id = False
        if solicited:
            user_id = user_obj.browse(cr, uid, solicited)
            employee_ids = employee_obj.search(cr, uid, [('user_id', '=', user_id.id)])
            if employee_ids:
                department_id = employee_obj.browse(cr, uid, employee_ids[-1]).department_id
            elif user_id.context_department_id:
                department_id = user_id.context_department_id
            else:
                raise osv.except_osv(_('Error !'),
                                     _('Su usuario no está vinculado con ningún departamento. Por favor, solicite que revisen el'
                                       ' departamento asignado desde su Perfil de Colaborador '))
            if department_id and department_id.manager_id:
                manager_id = department_id.manager_id.user_id.id
            else:
                raise osv.except_osv(_('Error !'), _('Su departamento no tiene asignado un Superior. Por favor, solicite que asignen un Encargado del'
                                                     ' Departamento en Talento Humano/Departamentos'))
            if not manager_id:
                raise osv.except_osv(_('Error !'), _('Su departamento no tiene asignado un Superior. Por favor, solicite que asignen un Encargado del'
                                                     ' Departamento en Talento Humano/Departamentos'))
            if uid == manager_id:
                required_approval = False
            else:
                required_approval = True
            return {"value": {"department_id": department_id.id, 'required_approval': required_approval,
                              'solicited': solicited, 'validator': manager_id}}

    def wkf_up_order(self, cr, uid, ids, context=None):
        todo = []
        xml_id = 'email_required_purchase'
        mod_obj = self.pool.get('ir.model.data')
        for po in self.browse(cr, uid, ids, context=context):
            if not po.name:
                name = self.pool.get('ir.sequence').get(cr, uid, 'purchase.order')
            else:
                name = po.name
            if not po.order_line:
                raise osv.except_osv(_('Error !'),
                                     _('You cannot confirm a purchase order without any lines.'))
            if po.required_approval and uid != po.validator.id:
                state = 'wait'
                validator = po.validator.id
                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_purchase', xml_id)
                if not template_ids:
                    raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico'
                                                        ' para las Solicitudes de Compras.'))
                else:
                    template_id = template_ids[1]
                self._embed_url(cr, uid, ids, context=None)
                self.generate_email_approve(cr, uid, template_id, po.id, context)
            elif uid == po.validator.id:
                state = 'wait'
                validator = po.validator.id
            else:
                state = po.state
                validator = po.validator.id
            for id in ids:
                self.write(cr, uid, [id], {'state': state, 'validator': validator, 'name': name})
        return True

    def _embed_url(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data_pool = self.pool.get('ir.model.data')
        result = dict.fromkeys(ids, '')
        for this in self.browse(cr, uid, ids, context=context):
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'straconx_purchase', "straconx_purchase_action")
            share_url_template_hash_arguments = ['model', 'view_type', 'action_id', 'id']
            context.update({'share_url_template_hash_arguments': share_url_template_hash_arguments})
            user = this.validator.id
            data = dict(model='purchase.order', view_type='page', action_id=action_id, id=this.id)
            web_link_approve = this.share_url_template(context=context) % data
            this.write({'web_link_approve': web_link_approve})
        return True

    def share_url_template(self, cr, uid, _ids, context=None):
        # NOTE: take _ids in parameter to allow usage through browse_record objects
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='', context=context)
        if base_url:
            base_url += '/web/webclient/home'
            extra = context and context.get('share_url_template_extra_arguments')
            if extra:
                base_url += '&' + '&'.join('%s=%%(%s)s' % (x, x) for x in extra)
            hash_ = context and context.get('share_url_template_hash_arguments')
            if hash_:
                base_url += '#' + '&'.join('%s=%%(%s)s' % (x, x) for x in hash_)
        return base_url

    def wkf_approve_order(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):
            if uid == po.validator.id or uid == 1:
                self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self, cr, uid, context=context)})
            else:
                usuario_id = self.pool.get('res.users').browse(cr, uid, po.validator.id)
                raise osv.except_osv(_('Error!'), _('Solo puede aprobar este pedido de compras el usuario %s.') % (usuario_id.name))
        return True

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        crt = 0
        xml_id = 'email_approve_purchase'
        mod_obj = self.pool.get('ir.model.data')
        for po in self.browse(cr, uid, ids, context=context):
            if not po.order_line:
                raise osv.except_osv(_('Error !'), _('You cannot confirm a purchase order without any lines.'))
            if po.tpurchase in ('purchase', 'fixed_assets'):
                for order_line in po.order_line:
                    if order_line.product_id.type in ('product', 'consu'):
                        crt += 1
                if crt == 0:
                    raise osv.except_osv(_('Error!'), _('Las compras de inventario y/o activos fijos necesitan tener creado el producto'
                                                        ' correspondiente, no solo la referencia.'))
            if po.required_approval and uid != po.validator.id:
                state = 'confirmed'
                validator = po.validator.id
                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_purchase', xml_id)
                if not template_ids:
                    raise osv.except_osv(_('Error!'),
                                         _('No existe una plantilla para el envío del correo electrónico'
                                           ' para la Aprobación de Solicitudes de Compras.'))
                else:
                    template_id = template_ids[1]
                cr.commit()
                self.generate_email_approve(cr, uid, template_id, po.id, context)
            else:
                for line in po.order_line:
                    if line.state == 'draft':
                        todo.append(line.id)
                message = _("Purchase order '%s' is confirmed.") % (po.name,)
                self.log(cr, uid, po.id, message)
                self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
                state = 'confirmed'
                validator = uid
            for id in ids:
                self.write(cr, uid, [id], {'state': state, 'validator': validator})
        return True

    def onchange_type_purchase(self, cr, uid, ids, type, tpurchase, context=None):
        if context is None:
            context = {}
        v = {}
        if type:
            type_cod = self.pool.get('purchase.category').browse(cr, uid, type, context).origin
            if type_cod in ('international', 'local') and tpurchase in ('purchase', 'fixed_assets'):
                v['invoice_method'] = 'picking'
            elif type_cod in ('international', 'local') and tpurchase == 'expense':
                v['invoice_method'] = 'order'
            else:
                v['invoice_method'] = 'order'
        return {'value': v}

    def onchange_date(self, cr, uid, ids, date, wait_day, context=None):
        result = {}
        if date and wait_day >= 0:
            min_date = (datetime.strptime(date, '%Y-%m-%d') + relativedelta(days=int(wait_day) or 0.0)).strftime('%Y-%m-%d')
            result['minimum_planned_date'] = min_date
        return {'value': result}

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        price_iva = 0.00
        iva_value = 0.00
        if order_line:
            if order_line.order_id.company_id.currency_id.id != order_line.order_id.currency_id.id:
                cd = order_line.order_id.company_id.currency_id.rate
            else:
                cd = 1.00
            if order_line.taxes_id:
                for tax_code in order_line.taxes_id:
                    if tax_code.ref_base_code_id.tax_type == 'vat':
                        price_iva = (order_line.final_price * cd) * (1 + tax_code.amount)
                        iva_value = round(((order_line.product_qty*(order_line.final_price * cd))*tax_code.amount), dc)
            else:
                price_iva = (order_line.final_price * cd)
                iva_value = 0.00
        return {
            'name': order_line.name,
            'account_id': account_id,
            'price_unit': (order_line.final_price * cd) or 0.0,
            'price_iva': price_iva or 0.0,
            'iva_value': iva_value or 0.0,
            'quantity': order_line.product_qty,
            'product_id': order_line.product_id.id or False,
            'price_product': (order_line.price_unit *cd) or 0.0,
            'price_subtotal': (order_line.product_qty* (order_line.final_price * cd)) or 0.00,
            'discount': (order_line.discount *cd) or 0.0,
            'offer': (order_line.offer * cd) or 0.0,
            'uos_id': order_line.product_uom.id or False,
            'invoice_line_tax_id': [(6, 0, [x.id for x in order_line.taxes_id])],
            'account_analytic_id': order_line.account_analytic_id.id,
            'purchase_line_id': order_line.id,
            'department_id': order_line.department_id.id,
            'cost_journal': order_line.cost_journal.id or False
        }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        if context:
            if context.get('date_planned', None):
                date_planned = context.get('date_planned', None)
        else: 
            date_planned = order.date_order
        return {
            'name': self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.in'),
            'partner_id': order.partner_id.id,
            'origin': order.name + ((order.origin and (':' + order.origin)) or ''),
            'date': date_planned,
            'type': 'in',
            'shop_id': order.shop_id.id,
            'address_id': order.dest_address_id.id or order.partner_address_id.id,
            'invoice_state': '2binvoiced' if order.invoice_method == 'picking' else 'none',
            'purchase_id': order.id,
            'company_id': order.company_id.id,
            'move_lines': [],
        }

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, context=None):
        ubication = None
        if order.location_id:
            ub_ids = self.pool.get('product.ubication').search(cr, uid, [('location_ubication_id', '=', order.location_id.id),
                                                                         ('product_id', '=', order_line.product_id.id)])
            if ub_ids:
                ubication = self.pool.get('product.ubication').browse(cr, uid, ub_ids[0], context).ubication_id.id
            else:
                u = self.pool.get('ubication').search(cr, uid, [('location_id', '=', order.location_id.id)], limit=1)
                ubication = u and u[0] or None
        return {'name': order.name + ': ' + (order_line.name or ''),
                'product_id': order_line.product_id.id,
                'product_qty': order_line.product_qty,
                'product_uos_qty': order_line.product_qty,
                'product_uom': order_line.product_uom.id,
                'product_uos': order_line.product_uom.id,
                'date': order_line.date_planned,
                'date_expected': order_line.date_planned,
                'location_id': order.partner_id.property_stock_supplier.id,
                'location_dest_id': order.location_id.id,
                'ubication_id': ubication,
                'picking_id': picking_id,
                'address_id': order.dest_address_id.id or order.partner_address_id.id,
                'move_dest_id': order_line.move_dest_id.id,
                'state': 'draft',
                'purchase_line_id': order_line.id,
                'company_id': order.company_id.id,
                'price_unit': order_line.final_price,
                'department_id': order_line.department_id.id,
                }

    def has_stockable_product(self, cr, uid, ids, *args):
        b = False
        prod_catag = []
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('catalog'):
                    prod_catag.append(order_line.product_id.id)
                    b = True
                if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    b = True
                if not order_line.product_id:
                    b = True
        if prod_catag:
            self.pool.get('product.product').write(cr, uid, prod_catag, {'type': 'product'})
        return b

    def action_invoice_create(self, cr, uid, ids, context=None):
        res = False
        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')
        inv_line_obj = self.pool.get('account.invoice.line')
        for o in self.browse(cr, uid, ids):
            il = []
            fpos = o.fiscal_position or False
            for ol in o.order_line:
                if ol.product_id:
                    if ol.product_id.type in ('product', 'catal'):
                        a = ol.product_id.product_tmpl_id.property_stock_account_input.id
                        if not a:
                            a = ol.product_id.categ_id.property_stock_account_input_categ.id
                        if not a:
                            raise osv.except_osv(_('Error !'),
                                                 _('No existe cuenta contable definida para el producto: %s - %s (id:%d)') %
                                                 (ol.product_id.default_code, ol.product_id.name, ol.product_id.id,))
                    elif ol.product_id.type in ('consu', 'admin_service', 'service'):
                        a = ol.product_id.product_tmpl_id.property_account_expense.id
                    else:
                        a = self.pool.get('ir.property').get(cr, uid, 'property_account_expense_categ', 'product.category').id
                else:
                    a = self.pool.get('ir.property').get(cr, uid, 'property_account_expense_categ', 'product.category').id
                if not a:
                    raise osv.except_osv(_('Error !'), _('No existe cuenta contable definida para el producto: %s - %s (id:%d)') %
                                         (ol.product_id.default_code, ol.product_id.name, ol.product_id.id,))
                a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, a)
                inv_line_data = self._prepare_inv_line(cr, uid, a, ol, context=context)
                inv_line_id = inv_line_obj.create(cr, uid, inv_line_data, context=context)
                il.append(inv_line_id)
                ol.write({'invoiced': True, 'invoice_lines': [(4, inv_line_id)]}, context=context)

            pay_acc_id = o.partner_id.property_account_payable.id
            pay_acc_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, pay_acc_id)
            journal_ids = journal_obj.search(cr, uid, [('type', '=', 'purchase'), ('company_id', '=', o.company_id.id)], limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error !'),
                                     _('There is no purchase journal defined for this company: "%s" (id:%d)') % (o.company_id.name, o.company_id.id))
            if o.partner_address_id.country_id.id != o.company_id.country_id.id:
                source = 'international'
                tax_documents = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', 'TI')])
                tax_sustent = self.pool.get('sri.tax.sustent').search(cr, uid, [('code', '=', 'TI')])
            else:
                source = 'local'
                tax_documents = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '01')])
                tax_sustent = []
            inv = {
                'shop_id': o.shop_id.id,
                'name': o.partner_ref or o.name,
                'reference': o.partner_ref or o.name,
                'account_id': pay_acc_id,
                'type': 'in_invoice',
                'partner_id': o.partner_id.id,
                'currency_id': o.company_id.currency_id.id,
                'address_invoice_id': o.partner_address_id.id,
                'address_contact_id': o.partner_address_id.id,
                'country_id': o.partner_address_id.country_id.id,
                'journal_id': len(journal_ids) and journal_ids[0] or False,
                'origin': o.name,
                'invoice_line': [(6, 0, il)],
                'fiscal_position': o.fiscal_position.id or o.partner_id.property_account_position.id,
                'payment_term': o.payment_term.id or o.partner_id.property_payment_term and o.partner_id.property_payment_term.id or False,
                'company_id': o.company_id.id,
                'tpurchase': o.tpurchase,
                'origin_transaction': source,
                'purchase_order_id': o.id,
                'document_type': tax_documents and tax_documents[0] or None,
                'tax_sustent': tax_sustent and tax_sustent[0] or None,
                'segmento_id': o.partner_id.segmento_id.id,
            }
            context['type'] = 'in_invoice'
            inv_id = self.pool.get('account.invoice').create(cr, uid, inv, context)
            self.pool.get('account.invoice').button_compute(cr, uid, [inv_id], context=context, set_total=True)
            o.write({'invoice_ids': [(4, inv_id)]}, context=context)
            res = inv_id
        return res

    def onchange_line_id(self, cr, uid, ids, line_dr_ids, price_with_tax=False, context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        context = context or {}
        if not line_dr_ids:
            return {'value': {}}
        line_osv = self.pool.get("purchase.order.line")
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['price_subtotal', 'price_unit', 'product_qty',
                                                                                              'discount_order_total', 'offer_order_total'], context)
        amount_total = 0.00
        amount_tax = 0.00
        amount_tax2 = 0.00
        total_quantity = 0.00
        total_discount = 0.00
        total_offer = 0.00
        pretotal = 0.00
        exempt = 0.0
        total = 0.00
        for line in line_dr_ids:
            amount = line.get('price_subtotal', 0.0)
            price_unit = line.get('price_unit', 0.0)
            discount_order_total = line.get('discount_order_total', 0.0)
            offer_order_total = line.get('offer_order_total', 0.0)
            quantity = line.get('product_qty', 0.0)
            for ab in line.get('taxes_id', []):
                tax = ab[2]
                for l in tax:
                    t = self.pool.get('account.tax').browse(cr, uid, l)
                    if t.tax_code_id.tax_type == 'vat':
                        if t.amount != 0:
                            amount_tax += amount * t.amount
                            total += amount
                        else:
                            amount_tax += 0
                            exempt += amount
            pretotal += (quantity*price_unit)
            total_discount += discount_order_total
            total_offer += offer_order_total
            total_quantity += quantity
        pretotal = round(pretotal, dc)
        amount_tax = round(amount_tax, dc)
        exempt = round(exempt, dc)
        total_discount = round(total_discount, dc)
        total_offer = round(total_offer, dc)
        total = pretotal - total_discount - total_offer
        amount_total = pretotal + amount_tax + exempt
        return {'value': {'pretotal': pretotal, 'amount_untaxed': total, 'amount_total_vat_12': amount_tax, 'amount_total': amount_total,
                          'totaldiscount': total_discount, 'totaloffer': total_offer, 'totalquantity': total_quantity, 'exempt': exempt}}

    def button_dummy(self, cr, uid, ids, context=None):
        res = {}
        order = self.browse(cr, uid, ids[0])
        line_obj = self.pool.get('purchase.order.line')
        line_id = line_obj.search(cr, uid, [('order_id', '=', order.id)])
#        res1=line_obj._amount_line(cr, uid, line_id, prop = False, unknow_none = False ,unknow_dict=False)
        amount_untaxed = 0.0
        amount = 0.0
        amount_vat = 0.0
        amount_total = 0.0
        total_discount = 0.0
        total_offer = 0.0
        excempt = 0.0
        c = 0
        for line in order.order_line:
            total_discount += line.discount_order_total
            total_offer += line.offer_order_total
            amount = line.price_subtotal - (line.discount_order_total + line.offer_order_total)
            c = 0
            if line.taxes_id:
                for tax in line.taxes_id:
                    if tax.tax_code_id.tax_type == 'vat':
                        amount_vat += amount * tax.amount
                        c += 1
            if c > 0:
                amount_untaxed += amount
            else:
                excempt += amount
        amount_total = amount_untaxed + amount_vat + excempt
        amount_text_total = amount_to_text_es.amount_to_text(amount_total, 'DÓLARES AMERICANOS')
        res['amount_untaxed'] = amount_untaxed
        res['excempt'] = excempt
        res['amount_total_vat_12'] = amount_vat
        res['amount_total'] = amount_total
        res['totaloffer'] = total_offer
        res['totaldiscount'] = total_discount
        res['amount_text'] = amount_text_total
        return self.write(cr, uid, ids, res, context)

    def action_picking_create(self, cr, uid, ids, context=None):
        picking_ids = []
        lines= []
        or_ids = []
        crt = 0
        for order in self.browse(cr, uid, ids):
            if order.invoice_method == 'order':
                return False
            cr.execute('select  distinct date_planned from purchase_order_line where order_id = %s',[order.id, ])
            date = cr.fetchall()
            for order_line in order.order_line:
                if order_line.product_id.type in ('product', 'consu'):                                                
                    crt += 1
                    or_ids.append(order_line.id)
            if len(date) > 1 and crt >0:
                for dt in date:
                    lines = []
                    for line in order.order_line:
                        if line.date_planned == dt[0]:
                            lines.append(line.id)
                    context = {'date_planned': dt[0]}                            
                    picking_ids.extend(self._create_pickings_date(cr, uid, order,lines, None, context=context))
            elif crt > 0:
                picking_ids.extend(self._create_pickings(cr, uid, order, order.order_line, None, context=context))
        return picking_ids[0] if picking_ids else False
    
    def _create_pickings_date(self, cr, uid, order, lines, picking_id=False, context=None):
        if not picking_id: 
            picking_id = self.pool.get('stock.picking').create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
        todo_moves = []
        stock_move = self.pool.get('stock.move')
        p_order_line = self.pool.get('purchase.order.line')
        wf_service = netsvc.LocalService("workflow")
        for order_l in lines:
            order_line = p_order_line.browse(cr, uid, order_l)
            if not order_line.product_id:
                continue
            if order_line.product_id.type in ('product', 'consu'):
                move = stock_move.create(cr, uid, self._prepare_order_line_move(cr, uid, order, order_line, picking_id, context=context))
                if order_line.move_dest_id:
                    order_line.move_dest_id.write({'location_id': order.location_id.id})
                todo_moves.append(move)
        stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.force_assign(cr, uid, todo_moves)
        wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        return [picking_id]

    def _get_vals(self, vals):
        new_invoice_line = []
        invoice_line_list = vals.get('order_line', [])
        for line in invoice_line_list:
            if line[0] in (0, 1):
                if (line[2].get('product_id', False) and line[2].get('name', False)):
                    new_invoice_line.append(line)
            elif line[0] == 2:
                new_invoice_line.append(line)
            else:
                new_invoice_line.append(line)
        if invoice_line_list:
            vals.update({'order_line': new_invoice_line})
        return vals

    def action_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        c = 0
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                c = c+1
            for pick in purchase.picking_ids:
                if pick.state in ('assigned'):
                    self.pool.get('stock.picking').action_drafted(cr, uid, [pick.id], context)
                    self.pool.get('stock.picking').write(cr, uid, [pick.id], {'state': 'draft'})
                    self.pool.get('stock.picking').unlink(cr, uid, [pick.id], context)
                elif pick.state not in ('draft', 'cancel') and c == 1:
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order!'),
                        _('You must first cancel all receptions related to this purchase order.'))
#             for pick in purchase.picking_ids:
#                 wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            for inv in purchase.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order!'),
                        _('You must first cancel all invoices related to this purchase order.'))
                if inv:
                    wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_cancel', cr)
        self.write(cr, uid, ids, {'state': 'cancel'})

        for (id, name) in self.name_get(cr, uid, ids):
            wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)
            message = _("Purchase order '%s' is cancelled.") % name
            self.log(cr, uid, id, message)
        return True

    def generate_email_approve(self, cr, uid, template_id, res_id, context=None):
        if context is None:
            context = {}
        error = context.get('error', None)
        model = context.get('model', None)
        email_it = context.get('email_it', None)
        values = {'subject': False,
                  'body_text': False,
                  'body_html': False,
                  'email_from': False,
                  'email_to': False,
                  'email_cc': False,
                  'email_bcc': False,
                  'reply_to': False,
                  'auto_delete': False,
                  'model': False,
                  'res_id': False,
                  'mail_server_id': False,
                  'attachments': False,
                  'attachment_ids': False,
                  'message_id': False,
                  'state': 'outgoing',
                  'subtype': 'plain',
                  }
        if not template_id:
            return values

        attachments = {}
        purchase_obj = self.pool.get('purchase.order')
        report_xml_pool = self.pool.get('ir.actions.report.xml')
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')
        email_template_obj = self.pool.get('email.template')
        template = email_template_obj.get_email_template(cr, uid, template_id, res_id, context)
        template_context = email_template_obj._prepare_render_template_context(cr, uid, template.model, res_id, context)

        for field in ['subject', 'body_text', 'body_html', 'email_from',
                      'email_to', 'email_cc', 'email_bcc', 'reply_to',
                      'message_id']:
            values[field] = email_template_obj.render_template(cr, uid, getattr(template, field),
                                                               template.model, res_id, context=template_context) or False
        if values['body_html']:
            values.update(subtype='html')

        values.update(mail_server_id=template.mail_server_id.id,
                      auto_delete=template.auto_delete,
                      model=template.model,
                      res_id=res_id or False)
        purchase_id = purchase_obj.browse(cr, uid, res_id)

        add_email = ''
        if purchase_id and purchase_id.order_line:
            for line in purchase_id.order_line:
                if line.department_id.id != purchase_id.department_id.id:
                    if line.department_id.manager_id.work_email:
                        if len(add_email) > 0:
                                add_email = add_email + ',' + line.department_id.manager_id.work_email
                        else:
                            add_email = line.department_id.manager_id.work_email

        if add_email:
            values['email_cc'] = add_email

#         if template.report_template:
#             report_name = email_template_obj.render_template(cr, uid, template.report_name, template.model, res_id, context=context)
#             report_service = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
#             ctx = context.copy()
#             if template.lang:
#                 ctx['lang'] = email_template_obj.render_template(cr, uid, template.lang, template.model, res_id, context)
#             service = netsvc.LocalService(report_service)
#             (result, format) = service.create(cr, uid, [res_id], {'model': template.model}, ctx)
#             result = base64.b64encode(result)
#             if not report_name:
#                 report_name = report_service
#             ext = "." + format
#             if not report_name.endswith(ext):
#                 report_name += ext
#             attachments[report_name] = result

#             for attach in template.attachment_ids:
#                 attachments[attach.datas_fname] = attach.datas
#
#             values['attachments'] = attachments
#             if values['attachments']:
#                 attachment = values.pop('attachments')
#                 attachment_obj = self.pool.get('ir.attachment')
#                 att_ids = []
#                 for fname, fcontent in attachment.iteritems():
#                     data_attach = {
#                         'name': fname,
#                         'datas': fcontent,
#                         'datas_fname': fname,
#                         'description': fname,
#                         'res_model' : self._name,
#                         'res_id' : res_id
#                     }
#                     att_ids.append(attachment_obj.create(cr, uid, data_attach))
#                 values['attachment_ids'] = att_ids
        msg_id = mail_message.create(cr, uid, values, context=context)
        proof = mail_message.send(cr, uid, [msg_id], context=context)
        return True

purchase_order()


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def get_shop_id(self, cursor, user, picking):
        if picking.purchase_id:
            return picking.purchase_id.shop_id.id
        else:
            return super(stock_picking, self).get_shop_id(cursor, user, picking)
stock_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
