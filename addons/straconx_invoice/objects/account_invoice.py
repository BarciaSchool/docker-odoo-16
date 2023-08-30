# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#
#    This program is private software.
#
#
##############################################################################

import os, time
#from datetime import datetime
import datetime as dt 
from dateutil.relativedelta import relativedelta
from datetime import datetime
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc
from account_voucher import account_voucher

sql = """SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo 
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""


class account_invoice_line(osv.osv):

    def _get_categ_id(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for obj in self.browse(cr, uid, ids):
            if obj.product_id.categ_id:
                res[obj.id] = obj.product_id.categ_id.id
            else:
                ids = self.pool.get('product.category').search(cr, uid, [('name', '=', 'SIN CATEGORIA')], context=context)
                res[obj.id] = ids and ids[0] or None
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

    def get_amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        price_unit = 0
        price_subtotal = 0
        account_tax_obj = self.pool.get('account.tax')
        margin = 0.00
        for line in self.browse(cr, uid, ids, context=context):
            if line.type in ('out_invoice', 'out_refund'):
                price_unit = ((line.price_product * line.invoice_id.currency_id.rate) * (1 - (line.discount / 100))) * (1 - (line.offer / 100))
                price_unit = float('%.4f' % price_unit)
                price_subtotal = line.price_subtotal
            elif line.type in ('in_invoice', 'in_refund'):
                if line.purchase_line_id.price_with_tax and line.product_id or line.invoice_id.tpurchase == 'expense':
                        taxes = line.invoice_line_tax_id
                        amount_iva = 0.00
                        if taxes:
                            for t in taxes:
                                tax_ids = t.id
                                if tax_ids:
                                    tax_code = account_tax_obj.browse(cr, uid, tax_ids)
                                    if tax_code.ref_base_code_id.tax_type == 'vat':
                                        tax_amount = tax_code.amount
                                    else:
                                        tax_amount = 0.00
                        price_unit = line.price_product * line.invoice_id.currency_id.rate * (1 - (line.discount / 100)) * (1 - (line.offer / 100))
#                         price_unit = float( price_unit)
                        price_subtotal = ((price_unit * line.quantity))
            if line.product_id:
                product = line.product_id
            else:
                product = []
            if line.product_id and price_unit > 0 and line.type in ('out_invoice'):
                cost_price = float('%.4f' % (product.standard_price))
                if cost_price > 0:
                    margin = float('%.4f' % (((price_unit - cost_price) / price_unit) * 100))
            else:
                cost_price = 0.00
                margin = 0.00

            res[line.id]['cost_price'] = cost_price
            res[line.id]['cost_subtotal'] = cost_price * line.quantity
            res[line.id]['margin'] = margin
        return res

    def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        return self.pool.get('account.invoice.line').get_amount_line_all(cr, uid, ids, field_names, arg, context)

    def get_calculate_discount(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = {'offer_value_total': round((line.price_product * (1 - line.discount / 100)) * line.offer / 100 * line.quantity, 2),
                            'discount_value_total': round((line.price_product * line.discount / 100 * line.quantity) or 0.00, 2)}
        return res

    def _calculate_discount(self, cr, uid, ids, field_names, arg, context=None):
        return self.get_calculate_discount(cr, uid, ids, field_names, arg, context)

    def _get_invoice(self, cr, uid, ids, context=None):
        result = {}
        try:
            for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
                for line in invoice.invoice_line:
                    result[line.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()

    def get_value_attrs(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        for brw_line in self.browse(cr, uid, ids, context=context):
            res[brw_line.id]["discount_read"] = brw_line.discount or 0
            res[brw_line.id]["price_product_read"] = brw_line.price_product or 0
            res[brw_line.id]["price_unit_read"] = brw_line.price_unit or 0
            res[brw_line.id]["price_subtotal_read"] = brw_line.price_subtotal or 0
        return res

    def _get_value_attrs(self, cr, uid, ids, field_names, arg, context=None):
        return self.get_value_attrs(cr, uid, ids, field_names, arg, context=context)

    _inherit = "account.invoice.line"
    _columns = {
        'ref_product': fields.related('product_id', 'default_code', type='char', size=64, string='Reference Product', readonly=True),
        'price_iva': fields.float('PVP', digits_compute=dp.get_precision('Account'),),
        'price_product': fields.float('Precio Bruto', digits_compute=dp.get_precision('AccountInvoice'),),
        'cost_price': fields.float('Costo', digits_compute=dp.get_precision('AccountInvoice'),),
        'discount': fields.float('Discount', digits_compute=dp.get_precision('Account'),),
        'offer': fields.float('Offer', digits_compute=dp.get_precision('Account'),),
        'margin': fields.function(_amount_line_all, multi='account_invoice_line_amount', string='Margin', store=True, digits_compute=dp.get_precision('AccountInvoice')),
        'cost_subtotal': fields.function(_amount_line_all, multi='account_invoice_line_amount', string='Costs', store=True, digits_compute=dp.get_precision('AccountInvoice')),
        'offer_value_total': fields.function(_calculate_discount, method=True, string='Offer Value Total', digits_compute=dp.get_precision('AccountInvoice'), multi="offer"),
        'discount_value_total': fields.function(_calculate_discount, method=True, string='Discount Value Total', digits_compute=dp.get_precision('AccountInvoice'), multi="offer"),
        'categ_id': fields.function(_get_categ_id, fnct_search=_categ_id_search, obj="product.category", method=True, type="many2one", string='Category', store=True,readonly='0'),
        'discount_order': fields.float('$ Discount', digits_compute=dp.get_precision('AccountInvoice'),),
        'offer_value': fields.float('Line Offer', digits_compute=dp.get_precision('AccountInvoice'),),
        'price_subtotal': fields.float('Subtotal', digits_compute=dp.get_precision('AccountInvoice'),),
        'price_subtotal_t': fields.related('price_subtotal',string="Subtotal",type="float",store=False),
        'price_unit_t': fields.related('price_unit', string="Precio Unitario",type="float",store=False),        
        'price_unit': fields.float('Price Unit', digits_compute=dp.get_precision('AccountInvoice'),),
        'iva_value': fields.float('Iva', digits_compute=dp.get_precision('AccountInvoice'),),
        'salesman_id': fields.related('invoice_id', 'salesman_id', type="many2one", relation="salesman.salesman", string="Salesman", store=True),
        'shop_id': fields.related('invoice_id', 'shop_id', type="many2one", relation="sale.shop", string="Shop"),
        'segmento_id':fields.related('invoice_id', 'segmento_id', type="many2one", relation="res.partner.segmento", string="Segmento"),
        'digiter_id':fields.related('invoice_id', 'user_id', type="many2one", relation="res.users", string="User"),
        'date_invoice':fields.related('invoice_id', 'date_invoice', string="Date", type="date"),
        'address_invoice_id':fields.related('invoice_id', 'address_invoice_id', type="many2one", relation="res.partner.address", string="Agency"),
        'agency':fields.related('address_invoice_id', 'name', type="char", size=256, relation="res.partner.address", string="Agency"),
        'street':fields.related('address_invoice_id', 'street', type="char", size=256, relation="res.partner.address", string="Street"),
        'city':fields.related('address_invoice_id', 'city', type="char", size=256, relation="res.partner.address", string="City"),
        'city_state':fields.related('address_invoice_id', 'state_id', type="many2one", relation="res.country.state", string="States"),
        'state':fields.related('invoice_id', 'state', type='selection',
                               selection=[('draft', 'Draft'),
                                        ('proforma', 'Pro-forma'),
                                        ('open', 'Open'),
                                        ('paid', 'Paid'),
                                        ('cancel', 'Cancelled')], string="State",
                            store={
                             'account.invoice.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_id'], 5),
                             'account.invoice': (_get_invoice, ['state'], 4),
                             },
                               ),
        'type':fields.related('invoice_id', 'type', type='selection',
                               selection=[
                                        ('out_invoice', 'Customer Invoice'),
                                        ('in_invoice', 'Supplier Invoice'),
                                        ('out_refund', 'Customer Refund'),
                                        ('in_refund', 'Supplier Refund'),
                                        ], string="Type"),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=False),
        'active': fields.boolean('Active'),        
        'price_iva_read': fields.related('price_iva', string="PVP"),
        'discount_read': fields.related('discount', string="Discount"),
        'price_product_read': fields.related('price_product', string="Price Product"),
        'price_unit_read':fields.related('price_unit', string="Price Unit"),
        'price_subtotal_read':fields.related('price_subtotal', string="Subtotal"),  
        'department_id': fields.many2one('hr.department','Department'),   
        'cost_journal': fields.many2one('account.analytic.journal', 'Cost Journal'),
    }

    _defaults = {'quantity': 1,
                 'offer': 0,
                 'discount': 0,
                 'active': True}

    def onchange_read(self, cr, uid, ids, discount_read=0.00, price_unit_read=0.00, price_subtotal_read=0.00, discount=0.00,
                      price_unit=0.00, price_subtotal=0.00, context=None):
        result = {}
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'AccountInvoice')
        if context:
            changed = context.get('changed', False)
        result['discount_read'] = discount
        result['price_unit_read'] = round(price_unit, di)
        result['price_subtotal_read'] = round(price_subtotal, di)
        return {'value': result}

    def onchange_offer(self, cr, uid, ids, product=False, offer=0.0, qty=0, price_unit=0.0, margin=0.0, price_product=0.0, discount=0, taxes=False,
                       price_iva=0.0, fiscal_position=False, context=False):
        warning = {}
        permit_offer = True
        permit_discount = True
        authorized = True
        change_price_net = False
        change_price_product = False
        amount_iva = 0.00
        price_subtotal = 0.00
        discount_tc = 0.00
        price_bonus = 0.00
        discount_product = 0.00
        tc_discount = False
        line_vat = False
        value_vat = 0.00
        if not discount:
            discount = 0.00

        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'AccountInvoice')
        if not context:
            change_price_product = True
            inv_type = 'out_invoice'
            tc_discount = False
            bonus = False
        else:
            change_price_product = context.get('change_price_product',False)
            inv_type = context.get('type','out_invoice')
            change_price_net = context.get('change_price_net',False)
            tc_discount = context.get('tc_discount',False)
            bonus = context.get('bonus',False)
            if tc_discount:
                discount_tc = context.get('discount_tc',0.00) 
                permit_discount = True
            if bonus:
                new_price = context.get('new_price',0.00)
                price_product = new_price/qty 
                price_bonus = context.get('price_bonus',0.00)
        if not change_price_net:
            change_price_product = True

        fpos = self.pool.get('account.fiscal.position')
        p = False
        if context:
            active_id = context.get('active_id', False)
        else:
            active_id = False
        if active_id:
            invoice_id = self.pool.get('account.invoice').browse(cr, uid, active_id)
            p = invoice_id.partner_id
        if fiscal_position:
            fiscal_position = fpos.browse(cr, uid, fiscal_position)
        elif p:
            fiscal_position = fpos.browse(cr, uid, p.property_account_position.id)
        else:
            fiscal_position = []

        result = {}

        account_tax_obj = self.pool.get('account.tax')
        if taxes:
            if type(taxes) is tuple:
                if taxes[0][2]:
                    taxes = self.pool.get('account.tax').browse(cr,uid,taxes[0][2])
            elif type(taxes) is list:
                if taxes[0][2]:
                    taxes = self.pool.get('account.tax').browse(cr,uid,taxes[0][2])
                else:
                    taxes = []            
            else:
                taxes = taxes

        if (offer>=0 or discount>=0) and inv_type in ('out_invoice', 'out_refund') :
            attr_user = self.pool.get('res.users').browse(cr, uid, uid, context=None)
            percent_minum= attr_user.max_offer
            percent_discount= attr_user.max_discount
            permit_offer = attr_user.changed_offer
            permit_discount = attr_user.changed_discount
            permit_price = attr_user.changed_prices

        if context:
            tc_discount = context.get('tc_discount', False)
            if tc_discount:
                discount_tc = context.get('discount_tc', 0.00)
                permit_discount = True

        if product:
            res = self.pool.get('product.product').browse(cr, uid, product)
            discount_product = res.discount_percent

        if product and inv_type in ('out_invoice', 'out_refund'):
            res = self.pool.get('product.product').browse(cr, uid, product)
            if price_iva == 0:
                price_iva = self.pool.get('product.product').browse(cr,uid,product).p_net
            compare_data = abs(round(price_iva,3) - round(self.pool.get('product.product').browse(cr,uid,product).p_net,3))
            if  compare_data > 0.01:
                if not permit_price:
                    price_iva = self.pool.get('product.product').browse(cr,uid,product).p_net
                    warning = {'title': _('Error!'),'message': _(('Usted no esta autorizado a cambiar precios de los productos'))}
                    authorized = False
                else:
                    discount = 0.00

        if (not permit_offer and offer > 0) and inv_type in ('out_invoice', 'out_refund') :
            warning = {'title': _('Error!'),'message': _(('Usted no esta autorizado a dar ofertas'))}
            offer = 0.00
            authorized = False
        else:
            offer = float(offer)
        if (not permit_discount and discount > discount_product) and inv_type in ('out_invoice', 'out_refund') :
            discount = res.discount_percent
            authorized = False
            warning = {'title': _('Error!'),'message': _(('Usted no esta autorizado a dar descuentos'))}
        elif tc_discount:
            discount = abs(res.discount_percent - discount_tc)
        else:
            discount = float(discount)

        if inv_type in ('out_invoice', 'out_refund'):
            if offer <= percent_minum and (discount <= discount_product) and authorized:
                authorized = True
            else:
                if not warning:
                    authorized = False
                    warning = {'title': _('¡Requiere Authorización !'),
                               'message': _(('Se ha realizado un cambio de precio o el descuento/oferta es mayor al autorizado a su usuario.'
                                             'Por favor, solicite que su Supervisor apruebe la transacción ingresado'
                                             ' la autorización correspondiente.'))}

        price_unit = round(((price_product * (1 - (discount or 0.0) / 100.0) * (1 - (offer or 0.0) / 100.0))), di)
        price_product = round(price_product, di)
        price_unit = round(price_unit, di)
        price_iva = round(price_iva, di)

        if not product and not taxes:
            taxes = []
            if change_price_net:
                price_product = price_iva
            elif change_price_product:
                price_iva = price_product
            else:
                if price_product >= price_iva:
                    price_iva = price_product
                else:
                    price_product = price_iva

            price_unit = round(price_product * (1 - (discount*0.01))*(1-(offer*.01)), di)
            price_subtotal = round(price_unit * qty, di)
            amount_iva = 0.00

        elif taxes:
            if taxes:
                taxes_id_search = fpos.map_tax(cr, uid, fiscal_position, taxes)
                if taxes_id_search:
                    for t in taxes_id_search:
                        tax_code = account_tax_obj.browse(cr, uid, t)
                        if tax_code and tax_code.ref_base_code_id.tax_type == 'vat':
                            line_vat = True
                            if tax_code and change_price_product:
                                price_unit = round(price_product * (1 - (discount*0.01))*(1-(offer*.01)), di)
                                price_iva = price_product * (1 + tax_code.amount)
                                amount_iva = round(((price_unit * qty) * tax_code.amount), di)
                                price_subtotal = round(price_unit * qty, di)
                            elif tax_code and change_price_net:
                                price_product = price_iva / (1 + tax_code.amount)
                                price_unit = round(price_product * (1 - (discount*0.01))*(1-(offer*.01)), di)
                                amount_iva = round(((price_unit * qty) * tax_code.amount), di)
                                price_subtotal = round(price_unit * qty, di)
                            else:
                                amount_iva = 0.0
                                price_subtotal = round(price_unit * qty, di)
                            value_vat = tax_code.amount
                else:
                    if change_price_net:
                        price_product = price_iva
                    elif change_price_product:
                        price_iva = price_product
                    else:
                        if price_product >= price_iva:
                            price_iva = price_product
                        else:
                            price_product = price_iva

                    price_unit = round(price_product * (1 - (discount*0.01))*(1-(offer*.01)), di)
                    price_subtotal = round(price_unit * qty, di)
                    amount_iva = 0.00
        else:
            price_iva = price_product
            price_unit = round(price_product * (1 - (discount*0.01))*(1-(offer*.01)), di)
            price_subtotal = round(price_unit * qty, di)
            amount_iva = 0.00

        result['authorized'] = authorized
        result['discount'] = discount
        result['offer'] = offer
        result['price_unit'] = round(price_unit, di)
        result['price_product'] = round(price_product, di)
        result['price_iva'] = round(price_iva, di)
        result['iva_value'] = round(amount_iva, di)
        result['price_subtotal'] = round(price_subtotal, di)
        result['discount_read'] = discount
        result['price_product_read'] = round(price_product, di)
        result['price_iva_read'] = round(price_iva, di)
        result['price_unit_read'] = round(price_unit, di)
        result['price_bonus'] = round(price_bonus, di)
        result['price_subtotal_read'] = round(price_subtotal, di)
        result.update({'warning': warning})
        return {'value': result, 'warning': warning}

    def product_id_change(self, cr, uid, ids, product=False, uom=False, qty=0, name=False, type='out_invoice', partner_id=False,
                          fposition_id=False, price_unit=0, address_invoice_id=False, currency_id=False, context=False, company_id=False,
                          discount=0, offer=0, shop_id=False, order_id=False, order_line=False):
        if context is None:
            context = {}
        result = {}
        account_tax_obj = self.pool.get('account.tax')
        product_obj = self.pool.get('product.product')
        account_obj = self.pool.get('account.account')
        uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        segmento_obj = self.pool.get('res.partner.segmento')
        price_segmento_obj = self.pool.get('price.segmento')
        department_obj = self.pool.get('hr.department')
        cost_obj = self.pool.get('account.analytic.journal')
        taxes = []
        tax_id = []
        margin = 0.00
        tax_percent = 0.00
        amount_iva = 0.00
        price_iva = 0.00
        price_subtotal = 0.00
        cost_price = 0.00
        product_category = []
        analytic = False
        product_name = name
        if not type:
            type = "in_invoice"
        if qty == 0:
            qty = 1
        uos_id = uom
        uom_init = uom
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'AccountInvoice')
        if order_id:
            if len(self.pool.get('purchase.order').browse(cr, uid, order_id).order_line) == 1:
                result['purchase_line_id'] = self.pool.get('purchase.order').browse(cr, uid, order_id).order_line[0].id
            elif not order_line:
                raise osv.except_osv(_('Advertencia !'), _("Debe seleccionar la línea de orden de compra !"))
        if not product and not name:
            price_product = 0.00
            price_unit = 0.00
            price_subtotal = 0.00
            discount = 0.00
            offer = 0.00
            cost_price = 0.00
            subtotal_cost = 0.00

            if type in ('in_invoice', 'in_refund'):
                return {'value': result, 'domain': {'product_uom': []}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain': {'product_uom': []}}
        domain = {}

        # OBJETIVOS
        # a) Que lea los siguientes datos del producto: Precio Original, descuento, oferta, precio bruto y precio final
        # b) Que diferencie si es compra o venta
        # c) Que lea del cliente el id, el segmento y la tienda desde donde se encuetra facturando
        # d) Que determine que tipo de precios se encuentra usando: producto o lista
        # e) Que haga la conversión de unidades
        # f) Que tome los impuestos correctos y los calcule

        res_final = {'value': result, 'domain': domain}

        if not partner_id:
            raise osv.except_osv(_('No Partner Defined !'), _("You must first select a partner !"))
        part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        fpos_obj = self.pool.get('account.fiscal.position')
        fpos = fposition_id and fpos_obj.browse(cr, uid, fposition_id, context=context)

        cr.execute("""select lang from res_partner where id=%s""", (part.id,))
        lang = cr.commit()
        if lang:
            lang = lang[0][0]
        else:
            lang = 'es_EC'
        context.update({'company_id': company_id, 'lang': lang})
        if company_id:
            comp_id = company_id
        else:
            comp_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        company_id = self.pool.get('res.company').browse(cr, uid, comp_id)
        cr.execute("""select currency_id, pricelist from res_company where id=%s""", (company_id.id,))
        comp_res = cr.fetchall()
        if comp_res:
            currency = self.pool.get('res.currency').browse(cr, uid, comp_res[0][0])
            c_pricelist = comp_res[0][1]

        shop_id = shop_id or context.get('shop_id', False)
        context.update({'shop_id': shop_id})
        if c_pricelist:
            type_list = 'list_price'
        else:
            type_list = 'product'

        product_uom_pool = self.pool.get('product.uom')
        price_product = context.get('price_product', 0.00)
        if product:
            res = self.pool.get('product.product').browse(cr, uid, product, context=context)
            cr.execute("""select default_code, pt.name, pt.categ_id, pt.uom_id, pp.discount_percent, pt.list_price,
                            pp.p_net, pt.type,
                            pt.fob, pt.standard_price, pp.total_price, pu.category_id
                            from product_product pp
                            left join product_template pt on pt.id = pp.product_tmpl_id
                            left join product_uom pu on pu.id = pt.uom_id
                            where pp.id =%s """, (product,))
            p_name = cr.fetchall()
            if p_name:
                name = p_name[0][1]
                product_category = p_name[0][2]
                uom_id = p_name[0][3]
                discount_percent = p_name[0][4]
                lprice_product = p_name[0][5]
                lprice_net = p_name[0][6]
                pt_type = p_name[0][7]
                pt_fob = p_name[0][8]
                pt_standard = p_name[0][9]
                pt_total_price = p_name[0][10]
                pu_category = p_name[0][11]
            else:
                name = res.partner_ref
                product_category = res.categ_id.id

            if product and type in ('out_invoice') and pt_total_price == 0.00:
                raise osv.except_osv(_('¡Producto sin precio!'), _('El producto seleccionado no tiene un PVP definido.'))
            if product_name:
                name = product_name
            elif p_name[0][1]:
                name = p_name[0][1]
            else:
                name = res.partner_ref

            if not uom:
                uom = uom_id

            if discount == 0.00:
                if discount_percent:
                    discount = discount_percent
            # SE AGREGO PARA MANEJAR LAS CUENTAS PREDETERMINADAS

            a = False
            if type in ('out_invoice', 'out_refund'):
                if res.property_account_income:
                    a = res.property_account_income.id
                elif res.categ_id.property_account_income_categ.id:
                    a = res.categ_id.property_account_income_categ.id
                else:
                    cr.execute("""select value_reference from ir_property where name ='property_account_income'
                    and company_id =%s and res_id like 'product.template,%s'""", (company_id.id, res.product_tmpl_id.id))
                    property_account_income = cr.fetchall()
                    if len(property_account_income) > 0:
                        a = int(property_account_income[0][0].split(',')[1])
                    if not a:
                        cr.execute("""select value_reference from ir_property where name ='property_account_income_categ'
                        and company_id =%s and res_id like 'product.category,%s'""", (company_id.id, product_category))
                        property_account_income = cr.fetchall()
                        if len(property_account_income) > 0:
                            a = int(property_account_income[0][0].split(',')[1])
                        if not a:
                            cr.execute("""select value_reference from ir_property where name ='property_account_income' and company_id =%s""",
                                       (company_id.id,))
                            property_account_income = cr.fetchall()
                            if len(property_account_income) > 0:
                                a = int(property_account_income[0][0].split(',')[1])
            else:
                if res.property_account_income:
                    a = res.property_account_expense.id
                elif res.categ_id.property_account_expense_categ.id:
                    a = res.categ_id.property_account_expense_categ.id
                else:
                    cr.execute("""select value_reference from ir_property where name ='property_account_expense'
                    and company_id =%s and res_id like 'product.template,%s'""", (company_id.id, res.product_tmpl_id.id))
                    property_account_expense = cr.fetchall()
                    if len(property_account_expense) > 0:
                        a = int(property_account_expense[0][0].split(',')[1])
                    if not a:
                        cr.execute("""select value_reference from ir_property where name ='property_account_expense_categ'
                        and company_id =%s and res_id like 'product.category,%s'""", (company_id.id, product_category))
                        property_account_expense = cr.fetchall()
                        if len(property_account_expense) > 0:
                            a = int(property_account_expense[0][0].split(',')[1])
                        if not a:
                            cr.execute("""select value_reference from ir_property where name ='property_account_expense' and company_id =%s""",
                                       (company_id.id,))
                            property_account_expense = cr.fetchall()
                            if len(property_account_expense) > 0:
                                a = int(property_account_expense[0][0].split(',')[1])

            if context.get('account_id', False):
                a = context['account_id']
            if a:
                aa = account_obj.browse(cr, uid, a)
                if aa.company_id.id != company_id.id:
                    new_a = account_obj.search(cr, uid, [('code', '=', aa.code), ('company_id', '=', company_id.id)])
                    if new_a:
                        a = new_a[0]
            # SE AGREGO PARA MANEJAR LOS SEGMENTOS
            segmento_id = False
            segmento_id = partner_obj.browse(cr, uid, part.id).segmento_id

            if not segmento_id:
                segmento_ids = segmento_obj.search(cr, uid, [('is_default', '=', True)])
                if segmento_ids:
                    segmento_id = segmento_obj.browse(cr, uid, segmento_ids[-1])
                else:
                    raise osv.except_osv(_('Acción Inválida!'),
                                         _('Necesita especificar por lo menos un segmento predeterminado o asignar un segmento al cliente'))

            price_product_ids = False
            try:
                if not segmento_id.is_default:
                    price_product_ids = price_segmento_obj.search(cr, uid, [('product_id', '=', product), ('segmento_id', '=', segmento_id.id)])
                if price_product_ids:
                    sprice = price_segmento_obj.browse(cr, uid, price_product_ids[0]).lst_price_s
                    if sprice and sprice > 0.00:
                        price_product = price_segmento_obj.browse(cr, uid, price_product_ids[0]).p_net
                        cost_price = pt_standard
            except:
                raise osv.except_osv(_('Acción Inválida!'),
                                     _('Necesita especificar por lo menos un segmento predeterminado o asignar un segmento al cliente'))

            if type_list == 'list_price' and price_product == 0.00 and type in ('in_invoice', 'in_refund'):
                if part.property_product_pricelist_purchase:
                    pricelist = part.property_product_pricelist_purchase and part.property_product_pricelist_purchase.id
                else:
                    pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
                for s in res.seller_ids:
                    if s.name.id == partner_id:
                        seller_delay = s.delay
                        if s.product_uom:
                            temp_qty = product_uom_pool._compute_qty(cr, uid, s.product_uom.id, s.min_qty, to_uom_id=res.uom_id.id)
                            uom = s.product_uom.id  # prod_uom_po
                        temp_qty = s.min_qty  # supplier _qty assigned to temp
                        if qty < temp_qty:  # If the supplier quantity is greater than entered from user, set minimal.
                            qty = temp_qty
                            result.update({'warning': {'title': _('Warning'), 'message':
                                                       _('The selected supplier has a minimal quantity set to %s, you cannot purchase less.') % qty}})
                qty_in_product_uom = product_uom_pool._compute_qty(cr, uid, uom, qty, to_uom_id=res.uom_id.id)
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                                                                     product, qty_in_product_uom or 1.0, partner_id,
                                                                     {'uom': uom,
                                                                      'date': time.strftime('%Y-%m-%d'),
                                                                      'type': 'in_invoice'
                                                                      })[pricelist]
                price_unit = price
                cost_price = 0.00

            elif type_list == 'list_price' and price_product == 0.00 and type in ('out_invoice', 'out_refund'):
                if part.property_product_pricelist:
                    pricelist = part.property_product_pricelist and part.property_product_pricelist.id
                qty_in_product_uom = product_uom_pool._compute_qty(cr, uid, uom, qty, to_uom_id=res.uom_id.id)
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                                                                     product, qty_in_product_uom or 1.0, partner_id,
                                                                     {'uom': uom,
                                                                      'date': time.strftime('%Y-%m-%d'),
                                                                      'type': 'in_invoice'
                                                                      })[pricelist]
                price_unit = price
                cost_price = pt_standard

            elif pt_type in ('product', 'service'):
                if part.origin == 'international' and type in ('in_invoice', 'in_refund'):
                    price_product = pt_fob
                    price_iva = pt_fob
                elif part.origin == 'local' and type in ('in_invoice', 'in_refund'):
                    price_product = pt_standard
                else:
                    price_product = lprice_product
                    price_iva = lprice_net
                fob_price = pt_fob
                if fob_price:
                    if fob_price != price_unit and type == 'in_invoice':
                        self.pool.get('product.product').write(cr, uid, product, {'fob': fob_price}, context)
                cost_price = pt_standard
                subtotal_cost = cost_price * qty

            a = fpos_obj.map_account(cr, uid, fpos, a)
            if a:
                acc_id = account_obj.browse(cr, uid, a)
                if acc_id:
                    result['account_id'] = acc_id.id

            if type in ('out_invoice', 'out_refund'):
                cr.execute("""select tax_id from product_taxes_rel where prod_id = (select product_tmpl_id from product_product where id=%s)""",
                           (res.id,))
                tax_imp = []
                tax_ids = cr.fetchall()
                if tax_ids:
                    for t in tax_ids:
                        cr.execute("""select id from account_tax where id=%s and company_id=%s""",
                                   (t[0], company_id.id))
                        p = cr.fetchone()
                        if p and p[0]:
                            tax_imp.append(t[0])
                        else:
                            t = self.pool.get('account.tax').browse(cr, uid, t[0])
                            cr.execute("""select id from account_tax where description=%s and company_id=%s and type_tax_use=%s""",
                                       (t.description, company_id.id, t.type_tax_use))
                            new_t = cr.fetchone()
                            if new_t and new_t[0]:
                                tax_imp.append(new_t[0])

                if tax_ids:
                    taxes = self.pool.get('account.tax').browse(cr, uid, tax_imp)
                else:
                    at = self.pool.get('account.account').browse(cr, uid, a, context=context).tax_ids
                    if at:
                        taxes = at
                    else:
                        taxes = False
            else:
                cr.execute("select tax_id from product_supplier_taxes_rel where prod_id =(select product_tmpl_id from product_product where id=%s)",
                           (res.id,))
                tax_imp = []
                tax_ids = cr.fetchall()
                if tax_ids:
                    for t in tax_ids:
                        tax_imp.append(t[0])
                if tax_ids:
                    taxes = self.pool.get('account.tax').browse(cr, uid, tax_imp)
                else:
                    at = self.pool.get('account.account').browse(cr, uid, a, context=context).tax_ids
                    if at:
                        taxes = at
                    else:
                        taxes = False

            # Verifica el tipo de UOM

            if uom:
                uom_id = uom_obj.browse(cr, uid, uom)
                categ_uom_id = uom_id.category_id.id
                if categ_uom_id:
                    pt_uom = product_obj.browse(cr, uid, product).uos_id.id or product_obj.browse(cr, uid, product).uom_id.id
                    if pu_category != categ_uom_id or pt_uom != uom_id.id:
                        uom_type = uom_obj.browse(cr, uid, uom_id.id).uom_type
                        if uom_type == 'bigger':
                            price_product = price_product / uom_id.factor_inv
                        else:
                            price_product = price_product * uom_id.factor_inv

            price_unit = (price_product * (1 - discount * 0.01)) * (1 - offer * 0.01)

            if taxes:
                tax_id = fpos_obj.map_tax(cr, uid, fpos, taxes)
                for t in tax_id:
                    tax_code = account_tax_obj.browse(cr, uid, t)
                    cr.execute("""select atc.tax_type, at.amount from account_tax at
                                left join account_tax_code atc on atc.id = at.ref_base_code_id
                                where at.id = %s """, (t,))
                    tax_code_type = cr.fetchall()
                    if tax_code:
                        tax_type = tax_code_type[0][0]
                        tax_amount = tax_code_type[0][1]
                        if tax_type == 'vat':
                            if tax_amount != 0:
                                amount_iva = round((price_unit * tax_amount * qty), di)
                                if type in ('in_invoice', 'in_refund') and part.origin == 'local':
                                    price_iva = round((price_unit * (1+tax_amount)), di)
                        else:
                            amount_iva += 0.0
                    amount_iva = amount_iva
            else:
                tax_id = []
                amount_iva = 0.00

        if company_id.currency_id.id != currency.id:
            cd = self.pool.get('res.currency').browse(cr, uid, currency.id)
            price_product = price_product * cd.rate
            price_unit = round(((price_product * (1 - discount * 0.01)) * (1 - offer * 0.01)), di)
            price_subtotal = round((price_unit * qty), di)
            discount = discount
            offer = offer
            cost_price = cost_price * cd.rate
            subtotal_cost = cost_price * qty
            if price_unit > 0:
                margin = (price_unit - cost_price) / price_unit * 100
            else:
                margin = 0.00

        if price_unit > 0 and cost_price:
            margin = ((price_unit - cost_price) / price_unit) * 100
            price_subtotal = price_unit * qty
            subtotal_cost = cost_price * qty
        else:
            margin = 0.00
            price_subtotal = price_unit * qty
            subtotal_cost = 0.00

        result['price_product'] = price_product
        result['price_iva'] = price_iva
        result['categ_id'] = product_category
        result['price_unit'] = price_unit
        result['product_id'] = product
        result['iva_value'] = amount_iva
        result['offer'] = offer
        result['quantity'] = qty
        result['uos_id'] = uom
        result['invoice_line_tax_id'] = tax_id
        result['name'] = name
        result['discount'] = discount
        result['cost_price'] = cost_price
        result['price_subtotal'] = price_subtotal
        result['cost_subtotal'] = subtotal_cost
        result['margin'] = margin
        result['company_id'] = company_id.id
        result['shop_id'] = shop_id
        result['discount_read'] = discount
        result['price_product_read'] = price_product
        result['price_iva_read'] = price_iva
        result['price_unit_read'] = price_unit
        result['price_subtotal_read'] = price_subtotal
        return res_final

    def onchange_account_id(self, cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id, name, company_id, shop_id, currency_id):
        cost_obj = self.pool.get('account.analytic.journal')
        acc_acc_obj = self.pool.get('account.account')
        result = {}
        if not (name or product_id):
            raise osv.except_osv(_('Error!'), _("You need select a product or write a description before select a account."))
        if account_id:
            account_ids = acc_acc_obj.browse(cr, uid, account_id)
            if account_ids:
                if account_ids.analytic_account_id:
                    result['account_analytic_id'] = account_ids.analytic_account_id.id
                if account_ids.department_id:
                    result['department_id'] = account_ids.department_id.id
        cost_journal = cost_obj.search(cr, uid, [('default', '=', True)])
        if cost_journal:
            result['cost_journal'] = cost_journal[0]
        return {'value': result}

    def uos_id_change(self, cr, uid, ids, product, uom, qty=0, name=False, type='out_invoice', partner_id=False, fposition_id=False, price_unit=0,
                      address_invoice_id=False, currency_id=False, context=None, company_id=False, shop_id=False):
        if context is None:
            context = {}
        company_id = company_id if company_id != None else context.get('company_id', False)
        context = dict(context)
        context.update({'company_id': company_id})
        warning = {}
        res = self.product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id,
                                     currency_id, context=context, company_id=company_id, shop_id=shop_id)
        if res:
            if 'uos_id' in res['value']:
                del res['value']['uos_id']
            if not uom:
                res['value']['price_unit'] = 0.0
            if product and uom:
                prod = self.pool.get('product.product').browse(cr, uid, product, context=context)
                prod_uom = self.pool.get('product.uom').browse(cr, uid, uom, context=context)
                if prod.uom_id.category_id.id != prod_uom.category_id.id:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('You selected an Unit of Measure which is not compatible with the product.')
                }
                return {'value': res['value'], 'warning': warning}
        return res

    def move_line_get_item(self, cr, uid, line, context=None):
        if line.invoice_id.type in ('out_invoice', 'out_refund'):
            offer_total = line.offer_value_total
        else:
            offer_total = 0
        return {
            'type':'src',
            'name': line.name[:64],
            'price_unit':line.price_unit,
            'quantity':line.quantity,
            'offer_value_total':offer_total,
            'price':line.price_subtotal,
            'account_id':line.account_id.id,
            'product_id':line.product_id.id,
            'uos_id':line.uos_id.id,
            'account_analytic_id':line.account_analytic_id.id,
            'taxes':line.invoice_line_tax_id,
        }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for line in self.browse(cr,uid,ids):
            if line.invoice_id.state in ('open','paid'):
                raise osv.except_osv(_('¡Acción Inválida!'), _('Solo puede borrar líneas de facturas que no han sido aprobadas o pagadas.'))
            else:
                cr.execute("""UPDATE account_invoice_line set quantity = 0.0, cost_price = 0.0, discount = 0.0, price_unit = 0.0, iva_value = 0.00, margin = 0.00, write_date =now(),
                        cost_subtotal_s = 0.00, price_subtotal_s= 0.00 ,price_product = 0.00, price_subtotal = 0.0, offer=0.0, active= False, state='cancel' WHERE id = %s""", (line.id,))
        return True
account_invoice_line()

class account_invoice(osv.osv):
   
    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            checked_partial_rec_ids = []
            result[invoice.id] = 0.0
            if invoice.move_id and invoice.move_id.line_id:
                for move_line in invoice.move_id.line_id:
                    if invoice.type in ('out_invoice','out_refund'):
                        if move_line.account_id.type in ('receivable'):
                            if move_line.reconcile_partial_id:
                                partial_reconcile_id = move_line.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                result[invoice.id] += move_line.amount_residual_currency
                            elif move_line.reconcile_id:
                                result[invoice.id] = 0.00
                            else:
                                result[invoice.id] += move_line.amount_residual_currency                                
                    elif invoice.type in ('in_invoice','in_refund'):
                        if move_line.account_id.type in ('payable'):
                            if move_line.reconcile_partial_id:
                                partial_reconcile_id = move_line.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                result[invoice.id] += move_line.amount_residual_currency
                            elif move_line.reconcile_id:
                                result[invoice.id] = 0.00
                            else:
                                result[invoice.id] += move_line.amount_residual_currency                                
        return result

    
    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    def _get_invoice_from_line(self, cr, uid, ids, context=None):
        return super(account_invoice, self.pool.get('account.invoice'))._get_invoice_from_line(cr, uid, ids, context=context)

    def _get_invoice_from_reconcile(self, cr, uid, ids, context=None):
        return super(account_invoice, self.pool.get('account.invoice'))._get_invoice_from_reconcile(cr, uid, ids, context=context)

    def get_amount_tax_invoice(self, cr, uid, ids, name, args, context=None):
        res = {}
        account_tax_code_obj = self.pool.get('account.tax.code')
        account_tax = self.pool.get('account.tax')
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_base_vat_12': 0.0,
                'amount_base_vat_00': 0.0,
                'amount_base_vat_untaxes': 0.0,
                'amount_tax_withhold_vat': 0.0,
                'amount_tax_withhold': 0.0,
                'amount_tax_other': 0.0,
            }
            if invoice.origin_transaction == 'international' and invoice.journal_id.type in ('in_invoice', 'in_refund'):
                res[invoice.id]['amount_base_vat_00'] += invoice.amount_untaxed
            else:
                for line in invoice.invoice_line:
                    if line.iva_value==0:
                            res[invoice.id]['amount_base_vat_00'] += round(line.price_subtotal,6)
                    else:
                        res[invoice.id]['amount_base_vat_12'] += round(line.price_subtotal, 3)
            res[invoice.id]['amount_base_vat_untaxes'] = invoice.amount_untaxed - \
                res[invoice.id]['amount_base_vat_12'] - res[invoice.id]['amount_base_vat_00']
        return res

    def _amount_tax_invoice(self, cr, uid, ids, name, args, context=None):
        return self.get_amount_tax_invoice(cr, uid, ids, name, args, context)


    def get_amount_total_invoice(self, cr, uid, ids, name, args, context=None):
        res = {}
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'AccountInvoice')
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'pretotal':0.0,
                'amount_untaxed':0.0,
                'amount_total_vat': 0.0,
                'amount_total': 0.0,
                'amount_total_discount': 0.00,
                'amount_total_offer': 0.00
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_total_vat'] += round((line.iva_value), di) 
                res[invoice.id]['amount_untaxed'] += round((line.price_subtotal), di)                
                res[invoice.id]['amount_total_discount'] += round((line.discount_value_total), di)                 
                res[invoice.id]['amount_total_offer'] += round((line.offer_value_total), di)                 
                res[invoice.id]['pretotal'] += round(line.price_product * line.quantity, di)                                                 
                res[invoice.id]['amount_total'] = round(res[invoice.id]['amount_untaxed']+ (res[invoice.id]['amount_total_vat']), di)
        return res

    def _amount_total_invoice(self, cr, uid, ids, name, args, context=None):
        return self.get_amount_total_invoice(cr, uid, ids, name, args, context)
    
    def _number(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, args):
            result[invoice.id] = invoice.invoice_number
        return result

    def _get_shop(self, cr, uid, context=None):
        statement_obj = self.pool.get('account.bank.statement')
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        type = False
        pos = context.get('default_pos',False)
        if context is None:
            context = {}
        if context.get('type',False):
            type = context.get('type',False)
        if type and type == 'out_invoice':
            statement_id = statement_obj.search(cr,uid,[('state','=','open'),('user_id','=',uid)])
            if user_id.is_supervisor:
                shop_id = self.pool.get('res.users').browse(cr,uid,uid).shop_id.id
            elif (not statement_id and pos):
                raise osv.except_osv(_('! Error !'),
                        _('Necesita abrir una caja registradora para proceder a facturar.'))
            elif not pos:
                shop_id = self.pool.get('res.users').browse(cr,uid,uid).shop_id.id
            else:
                statement_id = statement_obj.browse(cr, uid, statement_id[0])
                shop_id = statement_id.shop_id.id
            return shop_id
        return None

    def _get_info(self, cr, uid, context=None):
        info = False
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        info = False
        if curr_user.old_auth:
            info = True
        else:
            for s in curr_user.printer_point_ids:
                if s.shop_id:
                    auth_lines = self.pool.get('sri.authorization.line')
                    if not auth_lines.search(cr, uid, [('shop_id', '=', s.shop_id.id), ('authorization_id.state', '=', True), ('state', '=', True)]):
                        info = False
                    else:
                        info = True 
        return info

    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = super(account_invoice, self)._get_journal(cr, uid, context)
        journal = self.pool.get('account.journal').browse(cr, uid, res, context).type
        if not res or context.get('journal_type', False) != journal:
            jnl_id = []
            if context.get('journal_type', False) == 'purchase_liquidation':
                jnl_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase_liquidation')])
                return jnl_id and jnl_id[0] or None
            elif context.get('journal_type', False) == 'other_moves':
                jnl_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'other_moves')])
                return jnl_id and jnl_id[0] or None
            elif context.get('journal_type', False) == 'sale_note':
                jnl_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale_note')])
                return jnl_id and jnl_id[0] or None

        else:
            return res

    def _account_quantity(self, cr, uid, ids, field_name, arg, context=None):
            result = {}
            for account in self.browse(cr, uid, ids, context=context):
                result[account.id] = 0.0
                for line in account.invoice_line:
                    result[account.id] += (line.quantity) or 0.0
            return result
    
    def _document_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        jnl_id = []
        if context.get('journal_type', False) == 'purchase':
            jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '01')])
        elif context.get('journal_type', False) == 'sale' or context.get('type', False) == 'out_invoice':
            jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '18')])
        elif context.get('journal_type', False) in ('sale_refund', 'purchase_refund'):
            jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '04')])
        elif context.get('journal_type', False) == 'purchase_liquidation':
            jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '03')])
        elif context.get('journal_type', False) == 'other_moves':
            jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', 'TI')])
        elif context.get('journal_type', False) == 'sale_note':
            jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '02')])

        return jnl_id and jnl_id[0] or None
        
    def _amount_to_pay(self, cr, uid, ids, name, args, context=None):
        if not ids:
            return {}
        res = {}
        move_line_obj = self.pool.get('account.move.line')
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = 0.0
            if invoice.move_id:
                line_ids = move_line_obj.search(cr,uid,[('move_id','=',invoice.move_id.id),('state','=','valid'),('date_maturity','!=',False)])
                move_line_ids = move_line_obj.browse(cr,uid,line_ids)
                if move_line_ids:
                    for line in move_line_ids:
                            if datetime.strptime(line.date_maturity, '%Y-%m-%d') < datetime.today():
                                res[invoice.id] += line.amount_to_pay
        return res  

    _inherit = 'account.invoice'
    _order = "invoice_number, date_invoice2 desc"
    _columns = {
        'country_id':fields.many2one('res.country', 'Country', readonly=True, states={'draft':[('readonly', False)]}),
        'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft':[('readonly', False)]}),
        'printer_id':fields.many2one('printer.point', 'Printer Point', readonly=True, states={'draft':[('readonly', False)]}, domain="[('shop_id', '=', shop_id)]"),
        'document_type': fields.many2one('sri.document.type', 'Document Type', readonly=True, states={'draft':[('readonly', False)]}),
        'tax_sustent': fields.many2one('sri.tax.sustent', 'Tax Sustent'),
        'vat': fields.related('partner_id', 'vat', string='R.U.C / CI', type='char', size=32, readonly=True, store=True),
        'origin_transaction':fields.selection([('local', 'local'), ('international', 'International'), ], 'Origin', select=True, readonly=True, states={'draft':[('readonly', False)]}),
        'tpurchase':fields.selection([('purchase', 'Purchase'), ('expense', 'Expense'), ('trade', 'Trade Liquidation'),('other_refund','Reembolso de Gastos')], 'Purchase type', select=True, readonly=True, states={'draft':[('readonly', False)]}),
        'date_invoice2': fields.datetime('Invoice Date', readonly=True, states={'draft':[('readonly', False)]}, select=True, help="Keep empty to use the current date"),
        'cancel_date': fields.datetime('Cancel Date', readonly=True),
        'cancel_user_id':fields.many2one('res.users', 'Cancel User', readonly=True),
        'number': fields.function(_number, method=True, type='char', size=25, string='Invoice Number', store={'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_number'], 3)}),
        'invoice_number': fields.char('Invoice Number', size=25, readonly=True, help="Unique number of the invoice, computed automatically when the invoice is created."),
        'invoice_number_in': fields.char('Invoice Number', size=25, readonly=True, states={'draft':[('readonly', False)]}, help="Unique number of the invoice."),
        'invoice_number_out': fields.char('Invoice Number', size=25, readonly=True, states={'draft':[('readonly', False)]}, help="Unique number of the invoice."),
        'authorization_sales':fields.many2one('sri.authorization', 'Authorization', readonly=True, states={'draft':[('readonly', False)]}),
        'authorization_purchase':fields.many2one('sri.authorization', 'Authorization', readonly=True, states={'draft':[('readonly', False)]}),
        'authorization':fields.char('Authorization', size=10, readonly=True),
        'automatic':fields.boolean('automatic'),
        'pre_printer':fields.boolean('Pre-printer'),
        'flag':fields.boolean('flag', required=False),
        'pretotal': fields.function(_amount_total_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Pretotal', multi='vat_amount', store=True),
        'amount_untaxed': fields.function(_amount_total_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Untaxed', multi='vat_amount', store=True),
        'amount_total_vat': fields.function(_amount_total_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Vat', multi='vat_amount', store=True),
        'amount_total': fields.function(_amount_total_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Total', multi='vat_amount', store=True),
        'amount_total_offer': fields.function(_amount_total_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Total Offer', multi="vat_amount"),
        'amount_total_discount': fields.function(_amount_total_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Total Discount', multi="vat_amount"),
        'amount_base_vat_12': fields.function(_amount_tax_invoice, method=True, digits_compute=dp.get_precision('Account'), string='BASE 12%', multi='tax_amount', store=True),
        'amount_base_vat_00': fields.function(_amount_tax_invoice, method=True, digits_compute=dp.get_precision('Account'), string='BASE 0%', multi='tax_amount', store=True),
        'amount_base_vat_untaxes': fields.function(_amount_tax_invoice, method=True, digits_compute=dp.get_precision('Account'), string='BASE Untaxes', multi='tax_amount', store=True),
        'amount_tax_withhold_vat': fields.function(_amount_tax_invoice, method=True, digits_compute=dp.get_precision('Account'), string='VAT Withhold', multi='tax_amount', store=True),
        'amount_tax_withhold': fields.function(_amount_tax_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Withhold Tax', multi='tax_amount', store=True),
        'amount_tax_other': fields.function(_amount_tax_invoice, method=True, digits_compute=dp.get_precision('Account'), string='Other Tax', multi='tax_amount', store=True),
        'migrate': fields.boolean('Migrate', required=False),
        'account_quantity': fields.function(_account_quantity, method=True, string='Quantity', store=True),
        'salesman_id': fields.many2one('salesman.salesman', 'Salesman', readonly=True, states={'draft':[('readonly', False)]}),
        'segmento_id':fields.many2one('res.partner.segmento', 'Segmento', readonly=True, states={'draft':[('readonly', False)]}),
        'check_total': fields.float('Verification Total', digits_compute=dp.get_precision('Account'), states={'open':[('readonly', True)], 'close':[('readonly', True)], 'draft':[('readonly', False)]}),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'draft':[('readonly', False)]}),
        'residual': fields.function(_amount_residual, digits_compute=dp.get_precision('Account'), string='Residual',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line','move_id'], 50),
                'account.invoice.tax': (_get_invoice_tax, None, 50),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','offer','invoice_id'], 50),
                'account.move.line': (_get_invoice_from_line, None, 50),
                'account.move.reconcile': (_get_invoice_from_reconcile, None, 50),
            },
            help="Remaining amount due."),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'print_status': fields.char('Print Status', size=32),
        'proforma': fields.char('Proforma', size=32),
        'is_paid':fields.boolean('Payments in migration?'),
        'info':fields.boolean('Permited sales'),
        'quantity': fields.float('Quantity'),
        'amount_to_pay': fields.function(_amount_to_pay,type='float', string='Amount to be paid', help='The amount which should be paid at the current date minus the amount which is already in payment order'),
        'history_document': fields.text('Información Histórica de la factura'),
        'check_total': fields.float('Verification Total', digits_compute=dp.get_precision('Account'),readonly=True, states={'draft':[('readonly', False)]}),
        'description': fields.char('Descripción', size=256, select=True),
        'name': fields.char('Nombre', size=64, select=True, readonly=True, states={'draft':[('readonly',False)]}),        
        'electronic':fields.boolean('electronic'),
        'authorization':fields.char('Authorization', size=50),
        'access_key':fields.char('Clave de Acceso', size=50),
        'sri_date':fields.datetime('Fecha Autorización'),
        'credit':fields.boolean('credit', required=False), 
                'liquidated':fields.boolean('liquidated', required=False),        
    }

    _defaults = {
                 'shop_id': _get_shop,
                 'document_type': _document_type,
                 'origin_transaction': 'local',
                 'journal_id': _get_journal,
                 'info': _get_info,
                 'automatic': True,
                 'proforma': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'sale.order'),
                 }
    
    _sql_constraints = [                        
                        ('number_uniq', 'unique(invoice_number, company_id,partner_id,journal_id, type, state)', 'Invoice Number must be unique per Company!'),
                        ('number_out_uniq', 'unique(invoice_number_out,invoice_number,partner_id,journal_id, type, company_id, state)', 'There is another invoice in the shop and shop with this number, please verify'),
                        ('number_in_uniq', 'unique(invoice_number_in,invoice_number,partner_id,journal_id,type, tax_sustent,state, company_id)', 'There is another invoice for this supplier with this number, please verify'),
                        ]
    
    def onchange_company_id(self, cr, uid, ids, company_id=False, part_id=False, type=False, invoice_line=False, date=False, currency_id=False,context=None):
        val = {}
        dom = {}
        shop_id = False
        month_id = False
        if context:
            journal_type =context.get('journal_type',False)
            shop_id = context.get('shop_id',False)
        obj_journal = self.pool.get('account.journal')
        account_obj = self.pool.get('account.account')
        inv_line_obj = self.pool.get('account.invoice.line')
        if company_id and part_id and type:
            acc_id = False
            partner_obj = self.pool.get('res.partner').browse(cr,uid,part_id)
            if partner_obj.property_account_payable and partner_obj.property_account_receivable:
                if partner_obj.property_account_payable.company_id.id != company_id and partner_obj.property_account_receivable.company_id.id != company_id:
                    property_obj = self.pool.get('ir.property')
                    rec_pro_id = property_obj.search(cr, uid, [('name','=','property_account_receivable'),('res_id','=','res.partner,'+str(part_id)+''),('company_id','=',company_id)])
                    pay_pro_id = property_obj.search(cr, uid, [('name','=','property_account_payable'),('res_id','=','res.partner,'+str(part_id)+''),('company_id','=',company_id)])
                    if not rec_pro_id:
                        rec_pro_id = property_obj.search(cr, uid, [('name','=','property_account_receivable'),('company_id','=',company_id)])
                    if not pay_pro_id:
                        pay_pro_id = property_obj.search(cr, uid, [('name','=','property_account_payable'),('company_id','=',company_id)])
                    rec_line_data = property_obj.read(cr, uid, rec_pro_id, ['name','value_reference','res_id'])
                    pay_line_data = property_obj.read(cr, uid, pay_pro_id, ['name','value_reference','res_id'])
                    rec_res_id = rec_line_data and rec_line_data[0].get('value_reference',False) and int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                    pay_res_id = pay_line_data and pay_line_data[0].get('value_reference',False) and int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                    if not rec_res_id and not pay_res_id:
                        raise osv.except_osv(_('Configuration Error !'),
                            _('Can not find a chart of account, you should create one from the configuration of the accounting menu.'))
                    if type in ('out_invoice', 'out_refund'):
                        acc_id = rec_res_id
                    else:
                        acc_id = pay_res_id
                    val= {'account_id': acc_id}
            if ids:
                if company_id:
                    inv_obj = self.browse(cr,uid,ids)
                    for line in inv_obj[0].invoice_line:
                        if line.account_id:
                            if line.account_id.company_id.id != company_id:
                                result_id = account_obj.search(cr, uid, [('name','=',line.account_id.name),('company_id','=',company_id)])
                                if not result_id:
                                    raise osv.except_osv(_('Configuration Error !'),
                                        _('Can not find a chart of account, you should create one from the configuration of the accounting menu.'))
                                inv_line_obj.write(cr, uid, [line.id], {'account_id': result_id[-1]})
            else:
                if invoice_line:
                    for inv_line in invoice_line:
                        obj_l = account_obj.browse(cr, uid, inv_line[2]['account_id'])
                        if obj_l.company_id.id != company_id:
                            raise osv.except_osv(_('Configuration Error !'),
                                _('Invoice line account company does not match with invoice company.'))
                        else:
                            continue
        if company_id and type:
            if type in ('out_invoice'):
                journal_type = 'sale'
            elif type in ('out_refund'):
                journal_type = 'sale_refund'
            elif type in ('in_refund'):
                journal_type = 'purchase_refund'
            elif type in ('in_refund'):
                if journal_type=='purchase_liquidation':
                    journal_type = journal_type
                else:
                    journal_type = 'purchase'
            journal_ids = obj_journal.search(cr, uid, [('company_id','=',company_id), ('type', '=', journal_type)])
            if journal_ids:
                val['journal_id'] = journal_ids[0]
            ir_values_obj = self.pool.get('ir.values')
            res_journal_default = ir_values_obj.get(cr, uid, 'default', 'type=%s' % (type), ['account.invoice'])
            for r in res_journal_default:
                if r[1] == 'journal_id' and r[2] in journal_ids:
                    val['journal_id'] = r[2]
            if not val.get('journal_id', False):
                raise osv.except_osv(_('Configuration Error !'), (_('Can\'t find any account journal of %s type for this company.\n\nYou can create one in the menu: \nConfiguration\Financial Accounting\Accounts\Journals.') % (journal_type)))
            dom = {'journal_id':  [('id', 'in', journal_ids),('company_id','=',company_id)]}
        else:
            journal_ids = obj_journal.search(cr, uid, [])
        if not date:
            date = time.strftime('%Y-%m-%d')
        else:
            date = date[:10]            
        
        month_id = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date),('company_id','=',company_id)])
        
        if month_id:            
            val['period_id']= month_id[0]
        else:
            raise osv.except_osv(_('! Error !'), _('No existen períodos activos para las fechas indicadas. Por favor revisar.'))
        if uid:
            user_id = self.pool.get('res.users').browse(cr,uid,uid)        
#        shop_id = self.pool.get('sale.shop').search(cr,uid,[('company_id','=',company_id)])

        if not shop_id:
            shop_id = user_id.shop_id.id
        if shop_id:
            val['shop_id'] = shop_id
#        analytic = self.pool.get('sale.shop').browse(cr, uid, shop_id, context).project_id.id
#        val['account_analytic_id'] = analytic
        dom = {'period_id':  [('company_id','=',company_id)], 'shop_id':  [('company_id','=',company_id)]}
        return {'value': val, 'domain': dom}
        
    def onchange_shop(self, cr, uid, ids, company=None, shop=None, type=None, context=None):
        statement_obj = self.pool.get('account.bank.statement')
        printer_obj = self.pool.get('printer.point')
        if context is None:
            context = {}
        values = {'value':{}, 'domain':{}}
        box_ids = []
        shop_ids = []
        box_id = []
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
#         for s in user.printer_point_ids:
#             box_ids.append(s.id)
#             if s.shop_id:
#                 shop_ids.append(s.shop_id.id)
        statement_id = statement_obj.search(cr,uid,[('state','=','open'),('user_id','=',uid)])
        if not statement_id:
            raise osv.except_osv(_('! Error !'), _('Necesita abrir una caja registradora para proceder a facturar.'))
        else:
            statement_id = statement_obj.browse(cr,uid,statement_id[0]) 
            shop= statement_id.shop_id.id
            printer_point_ids =  printer_obj.search(cr,uid,[('shop_id','=',shop)])
            if not printer_point_ids:
                raise osv.except_osv(_('! Error !'), _('No existen Cajas para la Tienda seleccionada.'))
        for x in printer_point_ids:
            s = printer_obj.browse(cr, uid, x)
            box_ids.append(s.id)
            if s.shop_id:
                shop_ids.append(s.shop_id.id)
        if shop:
            if type == 'out_invoice':
                cr.execute(sql, (shop, 'sale'))
            elif type == 'in_invoice':
                if context.get('journal_type', 'purchase') == 'purchase_liquidation':
                    cr.execute(sql, (shop, 'purchase_liquidation'))
                elif context.get('journal_type','purchase') == 'sale_note':
                    cr.execute(sql,(shop,'sale_note'))  
                elif context.get('journal_type','purchase') == 'other_moves':
                    cr.execute(sql,(shop,'other_moves'))                                                
                else:
                    cr.execute(sql, (shop, 'purchase'))
            elif type == 'out_refund':
                cr.execute(sql, (shop, 'sale_refund'))
            elif type == 'in_refund':
                cr.execute(sql, (shop, 'purchase_refund'))
            res = cr.fetchall()            
            if not res:
                name = self.pool.get('sale.shop').browse(cr, uid, shop, context).name
                warning = {'title': _('Error!'), 'message': _(('You must be selected in the shop %s the journal respective for this document.') % name)}
                return {'value': {'shop_id': None}, 'warning':warning}
            values['value']['journal_id'] = res[0][0]
            box_id = printer_obj.search(cr, uid, [('id', 'in', box_ids), ('shop_id', '=', shop)])
            if not box_id:
                values['value']['authorization'] = None
                values['value']['authorization_sales'] = None
                values['value']['account_analytic_id'] = None
            else:
                cash = box_id[0]
                if context.get('printer_id', None):
                    cash = context.get('printer_id', None)
                result = self.onchange_cash(cr, uid, ids, company, shop, type, cash, values['value']['journal_id'], context)
                analytic = self.pool.get('sale.shop').browse(cr, uid, shop, context).project_id.id
                values['value'].update(result['value'])
                values['value']['printer_id'] = cash
                values['value']['account_analytic_id'] = analytic
        domain = {'shop_id':[('id', 'in', shop_ids)], 'printer_id':[('id', 'in', box_id)], 'account_analytic_id':[('id', 'in', [analytic])]}
        values['domain'] = domain
        return values
    
    def onchange_cash(self, cr, uid, ids, company=None, shop=None, type=None, printer_id=None, journal=None, context=None):
        authorization_obj = self.pool.get('sri.authorization')
        values = {'value':{}}
        user = None
        user = self.browse(cr, uid, uid)
        refund_mode = context.get('refund_mode', None)
        if context is None:
            context = {}
        if not (journal and shop):
            warning = {'title': _('Verify data!'), 'message': _("you must select the shop and Journal.")}
            return {'value': {'printer_id': None}, 'warning':warning}
        if printer_id:
            if type in ('in_refund'):
                    values['value']['authorization'] = None
                    values['value']['authorization_sales'] = None
                    values['value']['date_invoice'] = None
                    values['value']['date_invoice2'] = None                                            
            elif type in ('out_invoice', 'out_refund') or (type == 'in_invoice' and context.get('journal_type', False) == 'purchase_liquidation') or self.validate(type, context.get('journal_type', None)):
                values['value']['pre_printer'] = False
                values['value']['automatic'] = False
                type_journal = self.pool.get('account.journal').browse(cr, uid, journal, context).type
                dic_auth = authorization_obj.get_auth_only(cr, uid, type_journal, company, shop, printer_id, context=context)
                if refund_mode == 'internal':
                    values['value']['authorization'] = None
                    values['value']['authorization_sales'] = None
                    return values

                if dic_auth['type_printer']: 
                    if dic_auth['type_printer'] == 'auto':
                        values['value']['pre_printer'] = False
                        values['value']['automatic'] = True
                        values['value']['date_invoice2'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        values['value']['date_invoice'] = time.strftime('%Y-%m-%d')                        
                    elif dic_auth['type_printer'] == 'pre':
                        values['value']['pre_printer'] = True
                        values['value']['automatic'] = False                    
                    else:
                        values['value']['pre_printer'] = False
                        values['value']['automatic'] = False
                else:
                    curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
                    if curr_user.old_auth and printer_id:
                        values['value']['printer_id'] = printer_id
                        values['value']['pre_printer'] = False
                    else:
                        raise osv.except_osv(_('No Authorization!'), _('Shop not have authorization for invoice! Please, create before continue.'))    

                if dic_auth['authorization']:
                    values['value']['authorization'] = authorization_obj.browse(cr, uid, dic_auth['authorization'], context).name
                    values['value']['authorization_sales'] = dic_auth['authorization']
                else:
                    values['value']['authorization'] = None
                    values['value']['authorization_sales'] = None
                    values['value']['date_invoice'] = None
                    values['value']['date_invoice2'] = None
                values['value']['invoice_number_out'] = None
        return values

    def onchange_date2(self, cr, uid, ids, date=None, company_id=False, context=None):
        default = {}
        changed_date = False
        if context:
            changed_date = context.get('change_date',True)
        if changed_date:
            date_invoice = context.get('date_invoice',False)
            if not date_invoice:
                date_invoice = time.strftime('%Y-%m-%d')
            date = date_invoice +' '+ time.strftime('%H:%M:%S')
        elif not date:
            date = time.strftime('%Y-%m-%d %H:%M:%S')        
        if not company_id:
            period_ids = False
        else:
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date or time.strftime('%Y-%m-%d')), ('date_stop', '>=', date or time.strftime('%Y-%m-%d')), ('company_id', '=', company_id)])
        if period_ids:
            default['date_invoice2'] = date
            default['date_invoice'] = date[:10]
            default['period_id'] = period_ids[0]
        else:
            raise osv.except_osv(_('! Error !'), _('No existen períodos activos para las fechas indicadas. Por favor revisar.'))
        return {'value':default}
    
    def onchange_type_document(self, cr, uid, ids, document=None, type=None, tpurchase=None, context=None):
        res = {}
        if context is None:
            context = {}
        sustent = []
        if document:
            cr.execute("SELECT sustent_id FROM document_support_rel WHERE document_id = %s", (document,))
            for tup in cr.fetchall():
                sustent += [n for n in tup]
            if type == "in_invoice":
                if context.get('journal_type', 'purchase') in ('purchase', 'purchase_liquidation'):
                    if tpurchase == 'purchase':
                        s = self.pool.get('sri.tax.sustent').search(cr, uid, [('id', 'in', sustent), ('code', '=', '03')]) 
                    else:
                        s = self.pool.get('sri.tax.sustent').search(cr, uid, [('id', 'in', sustent), ('code', '=', '02')])
                    res['tax_sustent'] = s and s[0] or None
                elif context.get('journal_type', 'purchase') == 'other_moves':
                    s = self.pool.get('sri.tax.sustent').search(cr, uid, [('id', 'in', sustent), ('code', '=', '00')])
                    res['tax_sustent'] = s and s[0] or None
        return {'value':res, 'domain':{'tax_sustent':[('id', 'in', sustent)]}}
       
    def onchange_number(self, cr, uid, ids, number, type=None, shop=None, printer_id=None, journal=None, company=None, date=None, context=None):
        result = {}
        warning = {}
        if context is None:
            context = {}
        user = None
        user = self.browse(cr, uid, uid)
        if number:
            if (type in ('out_invoice', 'out_refund')) or (type == 'in_invoice' and context.get('journal_type', False) == 'purchase_liquidation'):
                if not (shop and printer_id and journal):
                    warning = {'title': _('Verify data!'), 'message': _("you must select the shop, cash, and Journal.")}
                    return {'value': {'invoice_number_out': ''}, 'warning':warning}
                type_journal = self.pool.get('account.journal').browse(cr, uid, journal, context).type                
                info = self.pool.get('sri.authorization').get_auth(cr, uid, type_journal, shop, printer_id, number, company, date, uid, context)
                if not info['auth']:
                    result['authorization'] = None
                    result['authorization_sales'] = None
                    result['invoice_number_out'] = info['sequence']
                    warning = {
                        'title': _('Warning!'),
                        'message': _('¡No existe autorización para el número de documento ingresado!')
                        }
                else:
                    result['authorization_sales'] = info['auth']
                    result['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, info['auth'], context).name
                    result['invoice_number_out'] = info['sequence']
        return {'value':result, 'warning':warning}
    
    def onchange_auth_purchase(self, cr, uid, ids, auth=None, number=None, address=None, journal=None, date=None, electronic= False, context=None):
        values = {}
        vals = []
        if date:
            date = date
        else:
            date = time.strftime('%Y-%m-%d')

        if auth:
            if not (address and journal and number):
                warning = {'title': _('Verify data!'), 'message': _("you must select the address, Journal and number.")}
                return {'value': {'invoice_number_in': ''}, 'warning':warning}
            type_journal = self.pool.get('account.journal').browse(cr, uid, journal, context).type
            if electronic:
                    if auth:
                        if len(auth) not in (37,49) or not int(float(auth)):
                            raise osv.except_osv(_('Error !'), _('La autorización electrónica debe constar de 37 o 49 dígitos. Usted ha ingresado %s dígitos')%(len(auth)))
            else:
                num = number.split('-')
                if len(num) > 1:
                    if len(num) != 3:
                        raise osv.except_osv(_('Invalid action!'), _('The format number is incorrect'))
                    vals = self.pool.get('sri.authorization').get_id_supplier(cr, uid, address, num[2], type_journal, auth, date,False, context)
                else:
                    vals = self.pool.get('sri.authorization').get_id_supplier(cr, uid, address, num[0], type_journal, auth, date,False,context)
                if vals:
                    values['invoice_number_in'] = vals[-1]['number']
        return {'value':values}
    
    def onchange_number_in(self, cr, uid, ids,number, type=None, address=None, journal=None, origin='local', date=None, printer_id=None,shop_id=None, electronic=False,context=None):
        result = {}
        warning = {}
        if context is None:
            context = {}
            type_refund = False
        else:
            type_refund = context.get('refund_type',False)
        au = []
        if date:
            date = date
        else:
            date = time.strftime('%Y-%m-%d')
#             result['authorization_purchase'] = None
#             result['invoice_number_in'] = None
#             result['authorization'] = None

        if number:
            if type in ('in_invoice', 'in_refund'):
                if origin == 'local': 
                    if electronic:
                        if len(number) != 17:
                            warning = {
                            'title': _('Aviso!'),
                            'message': _('Por favor ingrese los 17 dígitos de la factura y los guiones. Son 3 que corresponden a punto de emisión (001), tres para punto de impresión (001) y nueve para la secuencia (123456789).')
                            }
                            result['authorization_purchase'] = None
                            result['invoice_number_in'] = number
                            result['authorization'] = None
                            return {'value':result, 'warning':warning}
                        else:
                            result['authorization_purchase'] = None
                            result['invoice_number_in'] = number
                            result['authorization'] = None
                            return {'value':result, 'warning':warning}
                    if type_refund == 'internal':
                        result['invoice_number_in'] = number                    
                    elif not type_refund or type_refund != 'internal':
                        if not (address and journal):
                            warning = {'title': _('Verify data!'), 'message': _("you must select the address and Journal.")}
                            return {'value': {'invoice_number_in': '', 'authorization_purchase':'', }, 'warning':warning}
                        type_journal = self.pool.get('account.journal').browse(cr, uid, journal, context).type
                        vals = self.pool.get('sri.authorization').get_id_supplier(cr, uid, address, number, type_journal, False, date=date, context=context)
                        if not vals:
                            result['authorization_purchase'] = None
                            result['invoice_number_in'] = None
                            result['authorization'] = None
                            warning = {
                                'title': _('Warning!'),
                                'message': _('¡No existe autorización para el número de documento ingresado!')
                                }
                        else:
                            for a in vals:
                                au.append(a['auth'])
                            result['invoice_number_in'] = vals[-1]['number']
                            result['authorization_purchase'] = vals[-1]['auth']
                            result['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, vals[-1]['auth'], context).name
                            if len(vals) > 1:
                                warning = {
                                'title': _('Warning!'),
                                'message': _('This number of invoice can correspond to more than one authorization by supplier!')
                                }
        return {'value':result, 'warning':warning, 'domain':{'authorization_purchase':[('id', 'in', au)]}}

    def onchange_partner_id(self, cr, uid, ids, type, partner_id, electronic=False, printer=False, date_invoice=False, payment_term=False,
                            partner_bank_id=False, company_id=False, context=None):
        invoice_addr_id = False
        contact_addr_id = False
        partner_payment_term = False
        acc_id = False
        bank_id = False
        fiscal_position = False
        segmento_id = False
        country_id = False
        salesman_id = None
        origin_transaction = None
        tax_sustent = None
        vat = None
        opt = [('uid', str(uid))]
        p = False
        result = {}
        warning = {}
        if partner_id:
            if not context:
                context = {}
            opt.insert(0, ('id', partner_id))
            res = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['contact', 'invoice'])
            contact_addr_id = res['contact']
            invoice_addr_id = res['invoice']
            printer_id = self.pool.get('printer.point').browse(cr, uid, printer)
            if not contact_addr_id:
                raise osv.except_osv(_('A contact or invoice address is required !'), _('Partner need a address for continue'))
            if not invoice_addr_id:
                invoice_addr_id = contact_addr_id
            p = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if p.vat:
                confirm_vat = self.pool.get('res.partner').check_vat(cr, uid, [p.id])
                if confirm_vat:
                    vat = p.vat
                else:
                    raise osv.except_osv(_('¡Error de Identificación!'), _('El Cliente/Proveedor necesita ser creado nuevamente, por cuanto la identificación ingresada no es válida. Por favor, solicite los datos al cliente.'))
            if company_id:
                if p.property_account_receivable.company_id.id != company_id and p.property_account_payable.company_id.id != company_id:
                    property_obj = self.pool.get('ir.property')
                    rec_pro_id = property_obj.search(cr, uid, [('name', '=', 'property_account_receivable'), ('res_id', '=', 'res.partner,' + str(partner_id) + ''), ('company_id', '=', company_id)])
                    pay_pro_id = property_obj.search(cr, uid, [('name', '=', 'property_account_payable'), ('res_id', '=', 'res.partner,' + str(partner_id) + ''), ('company_id', '=', company_id)])
                    if not rec_pro_id:
                        rec_pro_id = property_obj.search(cr, uid, [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)])
                    if not pay_pro_id:
                        pay_pro_id = property_obj.search(cr, uid, [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)])
                    rec_line_data = property_obj.read(cr, uid, rec_pro_id, ['name', 'value_reference', 'res_id'])
                    pay_line_data = property_obj.read(cr, uid, pay_pro_id, ['name', 'value_reference', 'res_id'])
                    rec_res_id = rec_line_data and rec_line_data[0].get('value_reference', False) and int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                    pay_res_id = pay_line_data and pay_line_data[0].get('value_reference', False) and int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                    if not rec_res_id and not pay_res_id:
                        raise osv.except_osv(_('Configuration Error !'),
                            _('Can not find a chart of accounts for this company, you should create one.'))

                    account_obj = self.pool.get('account.account')
                    rec_obj_acc = account_obj.browse(cr, uid, [rec_res_id])
                    pay_obj_acc = account_obj.browse(cr, uid, [pay_res_id])
                    p.property_account_receivable = rec_obj_acc[0]
                    p.property_account_payable = pay_obj_acc[0]

            if type in ('out_invoice', 'out_refund'):
                acc_id = p.property_account_receivable.id
                salesman_id = invoice_addr_id and self.onchange_address(cr, uid, ids, invoice_addr_id, {})['value']['salesman_id']
            else:
                acc_id = p.property_account_payable.id
            if not salesman_id:
                search_salesman = self.pool.get('salesman.salesman').search(cr, uid, [('user_id', '=', uid)])
                if search_salesman:
                    salesman_id = self.pool.get('salesman.salesman').browse(cr, uid, search_salesman[0]).id
                else:
                    raise osv.except_osv(_('Error!'), _("Your user no have authorization for comercial transactions."))                
            if p.segmento_id:
                segmento_id = p.segmento_id.id
            else:
                segmento_ids = self.pool.get('res.partner.segmento').search(cr, uid, [('is_default', '=', True)])
                segmento_id = segmento_ids and segmento_ids[0] or None
            if p.tax_sustent:
                tax_sustent = p.tax_sustent.id
            location_id = self.pool.get('res.partner.address').browse(cr, uid, invoice_addr_id, context=None).location_id
            if not location_id:
                raise osv.except_osv(_('Country Error !'), _('Necesita definir una ciudad para la Empresa.'))
            else:
                country_id = location_id.state_id.country_id.id
            if p.type_vat == 'passport' and type in ('in_invoice', 'in_refund'):
                journal_type = context.get('journal_type', False)
                if not journal_type or journal_type != 'purchase_liquidation':
                    origin_transaction = 'international'
                else:
                    origin_transaction = 'local'
            else:
                origin_transaction = 'local'
            fiscal_position = p.property_account_position and p.property_account_position.id or False
            partner_payment_term = p.property_payment_term and p.property_payment_term.id or False
            if type in ('in_invoice', 'in_refund'):
                partner_payment_term = p.property_payment_term_supplier and p.property_payment_term_supplier.id or False
            acc_id = self.pool.get('account.fiscal.position').map_account(cr, uid, p.property_account_position, acc_id)
            if p.bank_ids:
                bank_id = p.bank_ids[0].id
            result = {'value': {
                'address_contact_id': contact_addr_id,
                'address_invoice_id': invoice_addr_id,
                'account_id': acc_id,
                'payment_term': partner_payment_term,
                'fiscal_position': fiscal_position,
                'segmento_id': segmento_id,
                'origin_transaction': origin_transaction,
                'tax_sustent': tax_sustent,
                'salesman_id': salesman_id,
                'vat': vat,
                'country_id': country_id
                }
            }

        if p:
            if not p.email and (printer_id.type_printer == 'electronic' or electronic == True) and type == "out_invoice":
                result = {'value': {
                    'address_contact_id': False,
                    'address_invoice_id': False,
                    'account_id': False,
                    'payment_term': False,
                    'fiscal_position': False,
                    'segmento_id': False,
                    'origin_transaction': False,
                    'tax_sustent':False,
                    'salesman_id':False,
                    'vat':False,
                    'country_id':False
                },
                'warning' : {
                'title': _('¡Advertencia!'),
                'message': _('¡El cliente no tiene una dirección E-mail configurada! Abra el cliente e ingrese una.')
                    }
                    }                          
                return result

            if type in ('in_invoice', 'in_refund'):
                result['value']['partner_bank_id'] = bank_id
    
            if payment_term != partner_payment_term:
                if partner_payment_term:
                    to_update = self.onchange_payment_term_date_invoice(cr, uid, ids, partner_payment_term, date_invoice)
                    result['value'].update(to_update['value'])
                else:
                    result['value']['date_due'] = False
    
            if partner_bank_id != bank_id:
                to_update = self.onchange_partner_bank(cr, uid, ids, bank_id)
                result['value'].update(to_update['value'])
        return result
    
    def onchange_address(self, cr, uid, ids, address=None, context={}):
        res = {}
        if address:
            res['salesman_id'] = self.pool.get('res.partner.address').browse(cr, uid, address, context).salesman_assigned.id or None
        return {'value':res}

    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('authorization_sales', False):
            vals['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, vals['authorization_sales'], context).name
        if vals.get('authorization_purchase', False):
            vals['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, vals['authorization_purchase'], context).name
        for invoice in self.browse(cr, uid, ids, context):
            residual = 0.00
            reconciled = False
            checked_partial_rec_ids = []
            if invoice.move_id and invoice.state not in ('draft', 'cancel', 'proforma', 'proforma1'):
                for move_line in invoice.move_id.line_id:
                    if invoice.type in ('out_invoice', 'out_refund'):
                        if move_line.account_id.type in ('receivable'):
                            if move_line.reconcile_partial_id:
                                partial_reconcile_id = move_line.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                residual += move_line.amount_residual_currency
                            elif move_line.reconcile_id:
                                residual = 0.00
                                reconciled = True
                            else:
                                residual += move_line.amount_residual_currency
                    elif invoice.type in ('in_invoice', 'in_refund'):
                        if move_line.account_id.type in ('payable'):
                            if move_line.reconcile_partial_id:
                                partial_reconcile_id = move_line.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                residual += move_line.amount_residual_currency
                            elif move_line.reconcile_id:
                                residual = 0.00
                                reconciled = True
                            else:
                                residual += move_line.amount_residual_currency
                if invoice.move_id:
                    if invoice.move_id.state == 'posted' and reconciled and residual == 0.00:
                        cr.execute("""update account_invoice set write_date = now(), residual = %s, state='paid', reconciled = True where id=%s""",
                                   (residual, invoice.id))
                    else:
                        cr.execute("""update account_invoice set write_date = now(), residual = %s , state='open', reconciled = False where id=%s""",
                                   (residual, invoice.id))
                else:
                    raise osv.except_osv(_('¡Error!'), _('El movimiento contable de la factura %s con número %s no existe.') %
                                         (invoice.id, invoice.invoice_number))
        return super(account_invoice, self).write(cr, uid, ids, vals, context)

    def create(self, cr, uid, vals, context={}):
        if vals.get('authorization_sales', False):
            vals['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, vals['authorization_sales'], context).name
        if vals.get('authorization_purchase', False):
            vals['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, vals['authorization_purchase'], context).name
        return super(account_invoice, self).create(cr, uid, vals, context)

    def validate(self, type, journalType):
        return False

    def action_number(self, cr, uid, ids, context=None):
#         self.button_reset_taxes(cr, uid, ids, context)
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
#        self.write(cr, uid, ids, {})
#        cr.commit()

        authorization_obj = self.pool.get('sri.authorization')
        auth_line_obj = self.pool.get('sri.authorization.line')
        move_obj=self.pool.get('account.move')
        number_out = ''
        for invoice in self.browse(cr, uid, ids, context):
            id = invoice.id
            invtype = invoice.type
            number = invoice.number
            move_id = invoice.move_id and invoice.move_id.id or False
            if invoice.amount_total == 0:
                raise osv.except_osv(_('Error!'), _("No se puede validar una factura sin valor. Revisar los impuestos en cada linea."))
            if not invoice.partner_id.vat:
                raise osv.except_osv(_('Error!'), _("Partner %s doesn't have CEDULA/RUC, you must input for validate.") % invoice.partner_id.name)
            if invoice.partner_id.type_vat == 'consumidor' and invoice.amount_total > invoice.company_id.amount_cc:
                raise osv.except_osv(_('Error!'), _("El consumidor final no puede exceder de $ %s en sus compras.") % invoice.company_id.amount_cc)
            if (invoice.type in ('out_invoice', 'out_refund')) or (invoice.type == 'in_invoice' and invoice.journal_id.type == 'purchase_liquidation') or (invoice.type == 'in_refund' and invoice.journal_id.type == 'debit_note'):
                if invoice.migrate:
                    self.write(cr, uid, [invoice.id], {'invoice_number': invoice.invoice_number_out, 'flag': True}, context)
                elif invoice.type in ('out_refund') and invoice.refund_type in ('internal'):
                    if invoice.old_invoice_id:
                        number = invoice.old_invoice_id.invoice_number_out
                        number = 'NCI-' + number
                        verify = self.pool.get('account.invoice').search(cr, uid, [('number', 'like', number)])
                        if verify: 
                            name = int(len(verify)) + 1
                            number = number + '-' + str(name)
                        else:
                            number = number

                        self.write(cr, uid, [invoice.id], {                                                                                    
                                                           'invoice_number': number,
                                                           'internal_number': number,
                                                           'number': number,
                                                           'invoice_number_out': number,
                                                           'flag': True,
                                                           }, context)
                else:
                    type_journal = invoice.journal_id.type
                    if not (invoice.automatic or invoice.pre_printer or invoice.electronic):
                        if not invoice.invoice_number_out:
                            raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                        auth = authorization_obj.get_auth(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, invoice.invoice_number_out, invoice.company_id.id, invoice.date_invoice2,uid,context)
                        if not auth['auth']:
                            raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization for this number of sequence, please check'))
                        line_id = authorization_obj.get_line_id(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, auth['auth'], context)
                        self.pool.get('sri.authorization.line').add_document(cr, uid, line_id, context)
                        number=auth['sequence']
                        cr.execute("""update account_invoice set write_date =now(),  internal_number=%s, number=%s,  invoice_number=%s,invoice_number_out=%s, authorization_sales=%s, flag=True where id=%s""",(number,number,number,number,auth['auth'],invoice.id))
                    elif (invoice.automatic or invoice.electronic):
                        if not invoice.number:
                            auth = authorization_obj.get_auth_only(cr, uid, type_journal,invoice.company_id.id, invoice.shop_id.id, invoice.printer_id.id, invoice.date_invoice2, context)
                            if auth:
                                auth_id = auth['authorization']
                            else:
                                raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
                            line_id = authorization_obj.get_line_id(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, auth['authorization'], context)
                            self.pool.get('sri.authorization.line').add_document(cr, uid, line_id, context)
                            number=auth['sequence']
                            cr.execute("""update account_invoice set write_date =now(),  internal_number=%s, number=%s,  invoice_number=%s,invoice_number_out=%s, authorization_sales=%s, flag=True where id=%s""",(number,number,number,number,auth_id,invoice.id))
                        else:
                            number = invoice.number
                            cr.execute("""update account_invoice set write_date =now(),  internal_number=%s, number=%s,  invoice_number=%s,invoice_number_out=%s, flag=True where id=%s""",(number,number,number,number,invoice.id))                        
                    else:
                        if (not invoice.migrate):
                            if not invoice.authorization_sales:
                                raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))                            
                        line_id = authorization_obj.get_line_id(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, invoice.authorization_sales.id, context)
                        if not invoice.invoice_number_out:
                            b = True
                            while b :
                                number_out = authorization_obj.get_number(cr, uid, [invoice.authorization_sales.id], type_journal, invoice.shop_id.id, invoice.printer_id.id, invoice.company_id.id)
                                number = number_out
                                self.pool.get('sri.authorization.line').add_sequence(cr, uid, line_id, {})
                                if not self.pool.get('account.invoice').search(cr, uid, [('type', '=', invoice.type), ('invoice_number', '=', number_out), ('shop_id', '=', invoice.shop_id.id), ('printer_id', '=', invoice.printer_id.id), ('id', 'not in', tuple(ids))],):
                                    b = False
                        else:
                            number_out = invoice.invoice_number_out
                        if not invoice.pre_printer:    
                            self.pool.get('sri.authorization.line').add_document(cr, uid, line_id, {})
#                         self.write(cr, uid, [invoice.id], {
#                                                            'invoice_number': number_out,
#                                                            'invoice_number_out': number_out,
#                                                            'flag':True,
#                                                            # 'authorization':invoice.authorization_sales.name,
#                                                            }, context)
                        cr.execute("""update account_invoice set  write_date =now(), internal_number=%s, number=%s, invoice_number=%s,invoice_number_out=%s,flag=True where id=%s""",(number_out,number_out,number_out,number_out,invoice.id))
            elif invoice.type in ('in_invoice', 'in_refund'):
                vals = []
                if (invoice.origin_transaction == 'local' and not invoice.refund_type=='internal' and invoice.type!='in_refund'):
                    if invoice.electronic:
                        if  invoice.authorization:
                            if len(invoice.authorization) not in (37,49) or not int(float(invoice.authorization)):
                                raise osv.except_osv(_('Error !'), _('La autorización electrónica debe constar de 37 o 49 dígitos. Usted ha ingresado %s dígitos')%(len(invoice.authorization)))
                        if invoice.invoice_number_in:
                            invoice_number_in = invoice.invoice_number_in 
                            self.write(cr, uid, [invoice.id], {'internal_number':invoice_number_in, 'number':invoice_number_in,'invoice_number': invoice.invoice_number_in, 'invoice_number_in': invoice_number_in, 'currency_id': invoice.company_id.currency_id.id}, context)                    
                    if not invoice.tax_sustent:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist tax sustent for the document, please check'))
                    if invoice.journal_id.type == 'other_moves':
                        if not invoice.invoice_number_in:
                            raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                        else:
                            invoice_number_in = invoice.invoice_number_in
                    if invoice.document_type.code not in ('TI', '19') and invoice.journal_id.type != 'other_moves':
                        if not invoice.invoice_number_in:
                            raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                        if invoice.document_type.code in ('01', '02', '03', '04', '05', '06', '07'):
                            if not invoice.migrate and not invoice.electronic:
                                if not invoice.authorization_purchase:
                                    raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
                        if(not invoice.migrate) and not invoice.electronic:
                            vals = self.pool.get('sri.authorization').get_id_supplier(cr, uid, invoice.address_invoice_id.id, invoice.invoice_number_in, invoice.journal_id.type, invoice.authorization_purchase.id, invoice.date_invoice,False,context)
                            if not vals:
                                raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization for this number of sequence, please check'))
                            if self.search(cr, uid, [('partner_id', '=', invoice.partner_id.id), ('type', '=', invoice.type), ('invoice_number_in', '=', vals[-1]['number']) , ('id', 'not in', tuple(ids)), ('state', 'in', ['open', 'paid'])]):
                                raise osv.except_osv(_('Error!'), _("There is an invoice with number %s for supplier %s") % (vals[-1]['number'], invoice.partner_id.name))                        
                            self.write(cr, uid, [invoice.id], {'invoice_number': vals[-1]['number'], 'invoice_number_in': vals[-1]['number'], 'authorization_purchase': vals[-1]['auth']}, context)
                    else:
                        if not invoice.invoice_number_in:
                            invoice_number_in = self.pool.get('ir.sequence').next_by_code(cr, uid, 'internal.transaction')
                        else:
                            invoice_number_in = invoice.invoice_number_in
                        self.write(cr, uid, [invoice.id], {'number':invoice_number_in,'invoice_number': invoice_number_in, 'invoice_number_in': invoice_number_in, 'internal_number':invoice_number_in}, context)
                elif invoice.origin_transaction == 'international' or invoice.electronic:
                    if invoice.electronic and invoice.authorization:
                        if len(invoice.authorization) not in (37,49) or not int(float(invoice.authorization)):
                            raise osv.except_osv(_('Error !'), _('La autorización electrónica debe constar de 37 o 49 dígitos. Usted ha ingresado %s dígitos')%(len(invoice.authorization)))
                    if invoice.invoice_number_in:
                        invoice_number_in = invoice.invoice_number_in 
                        self.write(cr, uid, [invoice.id], {'internal_number':invoice_number_in, 'number':invoice_number_in,'invoice_number': invoice.invoice_number_in, 'invoice_number_in': invoice_number_in, 'currency_id': invoice.company_id.currency_id.id}, context)
                    else:
                        raise osv.except_osv(_('Error !'), _('Necesita ingresar manualmente el número de factura para las compras internacionales'))
            for inv_id, name in self.name_get(cr, uid, [id]):
                ctx = context.copy()
                if invoice.type in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _("Invoice  '%s' is validated.") % name
                self.log(cr, uid, inv_id, message, context=ctx)
        num = number or invoice.invoice_number
        reference = num or invoice.reference or invoice.invoice_number or invoice.invoice_number_out or invoice.invoice_number_in or '/'
        if invtype in ('in_invoice', 'in_refund'):
            if not reference or reference == '/':
                ref = self._convert_ref(cr, uid, num)
            else:
                ref = reference
        elif invtype in ('out_invoice', 'out_refund'):
            ref = self._convert_ref(cr, uid, num)
        else:
            ref = self._convert_ref(cr, uid, number_out)
        if move_id:
            cr.execute('UPDATE account_move SET ref=%s WHERE id=%s',(ref, move_id))
            cr.execute('UPDATE account_move_line SET active=True, reference=%s, ref=%s WHERE move_id=%s', (ref, ref, move_id))
            cr.execute('UPDATE account_analytic_line SET ref=%s FROM account_move_line WHERE account_move_line.move_id = %s AND account_analytic_line.move_id = account_move_line.id',(ref, move_id))        
            self.pool.get('account.move').post(cr, uid, [move_id])
        return True
#        return res

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        if context is None:
            context = {}
        move_line = {
            'date_maturity': x.get('date_maturity', False),
            'partner_id': part,
            'name': x['name'][:64],
            'date': date,
            'debit': x['price'] > 0 and x['price'] + x.get('offer_value_total', 0.0),
            'credit': x['price'] < 0 and -x['price'] + x.get('offer_value_total', 0.0),
            'account_id': x['account_id'],
            'analytic_lines': x.get('analytic_lines', []),
            'amount_currency': x['price'] > 0 and abs(x.get('amount_currency', False)) or -abs(x.get('amount_currency', False)),
            'currency_id': x.get('currency_id', False),
            'tax_code_id': x.get('tax_code_id', False),
            'tax_amount': x.get('tax_amount', False),
            'ref': x.get('ref', False),
            'quantity': x.get('quantity', 1.00),
            'product_id': x.get('product_id', False),
            'product_uom_id': x.get('uos_id', False),
            'analytic_account_id': x.get('account_analytic_id', False),
            'period_id': context.get('period_id', None),
            'move_id': x,
        }
        line = self.pool.get('account.move.line').create(cr, uid, move_line)
        return line

    # @profile
    def action_move_create(self, cr, uid, ids, *args):
        # TODO Este método es sobreescrito para cambiar la referencia con la que se crean los asientos contables
        #     Se debe asignar el numero de la factura o de nota de credito  en la referencia del movimiento contable
        """Creates invoice related analytics and financial move lines"""
        self.button_reset_taxes(cr, uid, ids, context=None)
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
#         self.button_compute(cr, uid, ids, context=None)
        ait_obj = self.pool.get('account.invoice.tax')
        obj_sequence = self.pool.get('ir.sequence')
        cur_obj = self.pool.get('res.currency')
        mod_obj = self.pool.get('ir.model.data')
        mail_message = self.pool.get('email.template')
        cost_obj = self.pool.get('account.analytic.journal')
        total_invoice = 0.00
        amount_tax = 0.00
        amount_tax2 = 0.00
        amount_currency = 0.00
        amount_currency_tax2 = 0.00
        total_invoice_ac = 0.00
        amount2 = 0.00
        new_name = ''
        department_id = None
        cost_journal = None
        context = {}
        for inv in self.browse(cr, uid, ids):
            if inv.account_id:
                if inv.invoice_line:
                    for line in inv.invoice_line:
                        if line.account_id.id == inv.account_id.id:
                            raise osv.except_osv(_('¡Aviso!'), _('¡La cuenta contable de la factura debe ser diferente de la cuenta contable de la línea %s ')%(line.name))
            if not inv.partner_id.email and (inv.printer_id.type_printer == 'electronic' or inv.electronic == True) and type == "out_invoice":
                raise osv.except_osv(_('¡Advertencia!'), _('¡El cliente no tiene una dirección E-mail configurada! Abra el cliente e ingrese una.'))
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error !'), _('Please define sequence on invoice journal'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
            if not inv.shop_id:
                raise osv.except_osv(_('No Shop select !'), _('Please select a shop for continue.'))
            if inv.move_id and inv.move_id.state !='cancel':
                continue
            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice':time.strftime('%Y-%m-%d')})
            company_currency = inv.company_id.currency_id.id
            cd = cur_obj.browse(cr, uid, company_currency).rate
            # create the analytical lines
            # one move line per invoice line
#             iml = self._get_analytic_lines(cr, uid, inv.id)
            # check if taxes are all computed
            ctx = context.copy()
#            ctx.update({'lang': inv.partner_id.lang})
#             compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
#             self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

#            if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) > 0 :
            if inv.type in ('in_invoice') and abs(inv.check_total - inv.amount_total) > 0 :                
                raise osv.except_osv(_('Bad total !'), _('Please verify the price of the invoice !\nThe real total does not match the computed total.'))

            if inv.type in ('in_invoice', 'in_refund'):
                self.button_reset_taxes(cr, uid, [inv.id], context)
                if inv.invoice_number_in:
                    inv.write({'reference':inv.invoice_number_in})
                else:
                    inv.write({'reference':''})
                ref = inv.reference
            else:
                ref = self._convert_ref(cr, uid, inv.invoice_number_out)
            diff_currency_p = inv.currency_id.id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
#            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml)
            if inv.account_id.company_id.id != inv.company_id.id:
                acc_id = self.pool.get('account.account').search(cr,uid,[('code','=',inv.account_id.code),('company_id','=',inv.company_id.id)])
                self.write(cr, uid, ids, {'account_id':acc_id}, context)
            else:
                acc_id = inv.account_id.id
            name = None
            self.action_number(cr, uid, ids, context)
#Se agregó secuencial para los asientos de diarios de los siguientes documentos sin afectar la estructura de los demás asientos.            
            new_name = obj_sequence.next_by_id(cr, uid, inv.journal_id.sequence_id.id)
            if inv.journal_id.type == 'purchase_liquidation':
                name = 'LIQUIDACIÓN DE COMPRAS '+ new_name 
                ref = inv.invoice_number_out
            elif inv.type == 'in_invoice':
                name = 'FACTURAS DE PROVEEDORES ' + new_name
                ref = inv.invoice_number_in
            elif inv.type == 'in_refund':
                name = 'NOTA DE CRÉDITO DE PROVEEDORES ' + new_name
                ref = inv.invoice_number_in
            elif inv.type == 'out_invoice':
                name = 'FACTURAS DE CLIENTES ' + new_name
                ref = inv.invoice_number_out
            elif inv.type == 'out_refund':
                name = 'NOTA DE CRÉDITO DE CLIENTES ' + new_name
                ref = inv.invoice_number_out
            else:
                name = inv['number'] or inv.reference or '/'
            date = inv.date_invoice or time.strftime('%Y-%m-%d')
            part = inv.partner_id.id
            period_id = inv.period_id and inv.period_id.id or False
            if not period_id:
                if not inv.date_invoice:
                    date_invoice = inv.date_invoice2[0:10]
                else:
                    date_invoice = inv.date_invoice
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date_invoice or time.strftime('%Y-%m-%d')), ('date_stop', '>=', date_invoice or time.strftime('%Y-%m-%d')), ('company_id', '=', inv.company_id.id)])
                if period_ids:
                    period_id = period_ids[0]

            if inv.shop_id:
                shop_id = inv.shop_id.id
            else:
                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una tienda en el documento para continuar'))
            if inv.journal_id.centralisation:
                raise osv.except_osv(_('UserError'),
                        _('Cannot create invoice move on centralised journal'))
            move = {
                'ref': ref,
                'journal_id': inv.journal_id.id,
                'date': date,
                'shop_id':shop_id,
                'period_id':period_id,
                'narration':inv.comment,
                'details':name,
                'partner_id': part,
                'name': name,
            }
            move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
            reference = inv.number or inv.reference or inv.invoice_number_out or inv.invoice_number_in

            create_uid = uid
            create_date = time.strftime('%Y-%m-%d %H:%M:%S')

#             if inv.account_analytic_id.id:
#                 account_analytic_id = inv.account_analytic_id.id
#             else:
#                 account_analytic_id = None
            if inv.type in ('in_invoice', 'out_refund'):
                sql = """insert into account_move_line (create_date, create_uid, reference,journal_id,date_maturity,partner_id,name,date,debit,credit,account_id,amount_currency,currency_id,ref,quantity,product_id,product_uom_id,analytic_account_id,period_id,move_id,state,company_id,shop_id,department_id,cost_journal,active) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,True)"""
            else:
                sql = """insert into account_move_line (create_date, create_uid, reference,journal_id,date_maturity,partner_id,name,date,credit,debit,account_id,amount_currency,currency_id,ref,quantity,product_id,product_uom_id,analytic_account_id,period_id,move_id,state,company_id,shop_id,department_id,cost_journal,active) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,True)"""
            state_move = 'valid'

            if inv.period_id:
                period_id = inv.period_id.id
            else:
                period_id = period_id

            if inv.invoice_line:
                sum_sub = sum_sub2 = 0
                for line in inv.invoice_line:
                    if line.shop_id:
                        line_shop_id = line.shop_id.id
                    else:
                        line_shop_id = shop_id
                    if line.account_analytic_id.id:
                        account_analytic_id = line.account_analytic_id.id
                    ref = line.name[0:64]
                    if inv.type in ('in_invoice'):
                        price_subtotal = round(line.price_subtotal, di)
                        iva_value = round(line.iva_value, di)
                    elif inv.type in ('out_refund'):
                        if len(inv.invoice_line) == 1:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                        else:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                    else:
                        if len(inv.invoice_line) == 1:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                        else:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                    sum_sub += price_subtotal
                    sum_sub2 += price_subtotal
                    amount_tax += iva_value
                    price_subtotal_currency = round(price_subtotal * cd, di)
                    amount_currency_tax = round(amount_tax*cd, di)
                    if line.product_id.id:
                        product_id = line.product_id.id
                        product_uom = line.uos_id.id
                        if not line.uos_id.id:
                            product_uom = line.product_id.uom_id.id
                    else:
                        product_id = None
                        product_uom = None
                    if line.quantity <= 0:
                        raise osv.except_osv(_('Error !'), _("Cannot create the invoice !\nQuantity in invoice must be greater than 0."))
                    if line.department_id:
                        department_id = line.department_id.id
                    else:
                        department_id = None
                    if line.cost_journal.id:
                        cost_journal = line.cost_journal.id
                    else:
                        cost_journal = cost_obj.search(cr, uid, [('default', '=', True)])
                        if cost_journal:
                            cost_journal = cost_journal[0]
                        else:
                            cost_journal = None
                    if line.account_analytic_id:
                        account_analytic_id = line.account_analytic_id.id
                    else:
                        if line.account_id.analytic_account_id:
                            account_analytic_id = line.account_id.analytic_account_id.id
                        else:
                            account_analytic_id = None

                    cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, ref, date, price_subtotal, 0.00,
                                     line.account_id.id, round((price_subtotal_currency/cd),2), inv.currency_id.id, ref, line.quantity, product_id, product_uom,
                                     account_analytic_id, period_id, move_id, state_move, inv.company_id.id, line_shop_id, department_id,
                                     cost_journal))

            if inv.type in ('out_invoice', 'out_refund'):
                compute_taxes = inv.tax_line
                if compute_taxes:
                    for t in compute_taxes:
                        t_obj = self.pool.get('account.invoice.tax').browse(cr, uid, t.id)
                        if t_obj.tax_code_id.tax_type == 'vat':
                            amount_tax = round(t_obj.amount, di)
                            name_tax = t_obj.name
                            acc_id_tax = t_obj.account_id.id
                            amount_currency_tax = round(amount_tax * cd, di)
                            amount_tax2 += amount_tax
                            amount_currency_tax2 += amount_currency_tax

                        if amount_tax2 > 0 and t_obj.tax_code_id.tax_type == 'vat' and t_obj.amount > 0.00:
                            if inv.type in ('in_invoice', 'out_refund'):
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax2, 0.00,
                                                 acc_id_tax, amount_currency_tax2, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id, None, None))
                            else:
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax2, 0.00,
                                                 acc_id_tax, amount_currency_tax2, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id, None, None))

            else:
                compute_taxes = inv.tax_line
                if compute_taxes:
                    for t in compute_taxes:
                        t_obj = self.pool.get('account.invoice.tax').browse(cr, uid, t.id)
                        if t_obj.tax_code_id.tax_type == 'vat':
                            amount_tax = round(t_obj.amount, di)
                            name_tax = t_obj.name
                            acc_id_tax = t_obj.account_id.id
                            amount_currency_tax = round(amount_tax * cd, di)
                            amount_tax2 += amount_tax
                            amount_currency_tax2 += amount_currency_tax

                        if amount_tax2 > 0 and t_obj.tax_code_id.tax_type == 'vat' and t_obj.amount > 0.00:
                            if inv.type in ('in_invoice', 'out_refund'):
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax, 0.00,
                                                 acc_id_tax, amount_currency_tax, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id, None, None))
                            else:
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax2, 0.00,
                                                 acc_id_tax, amount_currency_tax2, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id,  None, None))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error !'), _("Cannot create the invoice !\nThe payment term defined gives a computed amount greater than the total invoiced amount."))

            if inv.amount_total:
                sum = inv.amount_untaxed
                for line in inv.invoice_line:
                    sum_sub2 = round(sum_sub2, di) - round(line.price_subtotal, di)
                    sum = round(sum, di) - round(line.price_subtotal, di)
#                if sum_sub2 == 0 and sum ==0:
                if sum_sub2 == 0:                    
#                     total_invoice = round(sum_sub + amount_tax2, di)
#                     total_currency = round((sum_sub + amount_tax2) * cd, di) 
#                 else: 
                    total_invoice = round(inv.amount_total, di)
                    total_currency = round((inv.amount_total * cd), di) 

            totlines = False
            if inv.payment_term:
                totlines = self.pool.get('account.payment.term').compute(cr,
                        uid, inv.payment_term.id, inv.amount_total, inv.date_invoice or False)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid,
                                company_currency, inv.currency_id.id, t[1])
                    else:
                        amount_currency = res_amount_currency 

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency
                        total_invoice_ac += abs(round(t[1], di))

                    if total_invoice_ac != inv.amount_total and len(totlines) == 1:
                        amount = abs(round(t[1], di)) - round((total_invoice_ac - inv.amount_total), di)
                        amount2 = round((total_invoice_ac - inv.amount_total), di)
                    else:
                        amount = abs(round(t[1], di))

                    if inv.type in ('in_invoice', 'in_refund'):
                        amount = amount
                        cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, t[0], part, name, date, 0.00, amount, acc_id, amount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id, None, None))
                    else:
                        amount = amount
                        cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, t[0], part, name, date, 0.00, amount, acc_id, amount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id, None, None))
            else:
                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, inv.date_due, part, name, date, 0.00, total, acc_id, amount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id, None, None))
            new_move_name = self.pool.get('account.move').browse(cr, uid, move_id).name
            self.write(cr, uid, [inv.id], {'move_id': move_id, 'period_id': period_id, 'move_name':new_move_name})
    #           Si por cuestiones de redondeo hay diferencias entre el asiento del debe y haber en los descuentos de ventas, se aplica una actualización del valor del descuento para cuadrar el movimiento contable.
            validate_moves_line = self.pool.get('account.move').browse(cr, uid, move_id).line_id
            debit = 0
            credit = 0
#            if validate_moves_line and acc_dis_id:
            if validate_moves_line:
                for line in validate_moves_line:
                    if not line.shop_id:
                        cr.execute("""update account_move_line set write_date = now(), shop_id = %s where id=%s """,(inv.shop_id.id, line.id))
                    debit += line.debit
                    credit += line.credit
                amount_new = round((debit - credit), di)
                if abs(amount_new) > 0:
                    if debit > credit:
                        acc_dis_id = inv.company_id.property_rounding_difference.id
                        if not acc_dis_id:
                            raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                        if inv.type in ('out_invoice', 'in_refund'):
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            cr.execute(sql, (create_date, create_uid,reference, inv.journal_id.id, None, part, name, date,amount_new, 0.00, acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id,None, None))
                        else:
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            cr.execute(sql, (create_date, create_uid,reference, inv.journal_id.id, None, part, name, date, 0.00,amount_new, acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id,None, None))
                    elif debit < credit:
                        if inv.type in ('in_invoice', 'out_refund'):
                            amount_new = abs(amount_new)
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            acc_dis_id = self.pool.get('account.account').search(cr,uid,[('name','=','OTROS INGRESOS DE ACTIVIDADES ORDINARIAS'),('type','!=','view'),('company_id','=',inv.company_id.id)], limit=1)[0]
                            if not acc_dis_id:
                                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                            cr.execute(sql, (create_date, create_uid,reference, inv.journal_id.id, None, part, name, date,amount_new, 0.00, acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id,None, None))
                        else:
                            amount_new = abs(amount_new)
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            acc_dis_id = self.pool.get('account.account').search(cr,uid,[('name','=','OTROS INGRESOS DE ACTIVIDADES ORDINARIAS'),('type','!=','view'),('company_id','=',inv.company_id.id)], limit=1)[0]
                            if not acc_dis_id:
                                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                            cr.execute(sql, (create_date, create_uid,reference, inv.journal_id.id, None, part, name, date, 0.00,amount_new, acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,shop_id,None,None))
                            self._log_event(cr, uid, ids)
                if abs(amount_new) >= 0.05:
                    xml_id = 'email_differences_account_move'
                    template_ids = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
                    if not template_ids:
                        raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico de errores de diferencias de valores en movimientos contables.'))
                    else:
                        template_id = template_ids[1]
                    send_id = mail_message.send_mail(cr,uid,template_id,ids[0],context)
                    #proof = mail_message.send(cr, uid, [send_id], context=context)
        return True

    def action_date_assign(self, cr, uid, ids, *args):
        res = {}
        auth_obj = self.pool.get('sri.authorization')
        pt_obj = self.pool.get('account.payment.term')        
#        res = super(account_invoice, self).action_date_assign(cr, uid, ids, args)
#         if uid:
#             context_tz = self.pool.get('res.users').browse(cr,uid,uid).context_tz or 'America/Guayaquil'
#         if context_tz:
#             os.environ['TZ'] = context_tz
#             time.tzset()
        for inv in self.browse(cr, uid, ids):
            if inv.printer_id.type == True:
                raise osv.except_osv(_('¡Aviso!'), _('No se puede facturar desde Cajas Internas'))
            date = time.strftime('%Y-%m-%d')
            if inv.date_invoice:
                date = inv.date_invoice or time.strftime('%Y-%m-%d')                
                if not inv.date_invoice2:
                    date2 = inv.date_invoice + ' 12:00:00'
                    inv.date_invoice2 = date2
                    self.write(cr, uid, [inv.id], {'date_invoice2':date2})
            if not inv.date_invoice2:               
                date2 = time.strftime('%Y-%m-%d %H:%M:%S')
                hora = time.strftime('%H')
#                if hora in ('00','01','02','03','04','05', '06', '07', '08', '09', '10'):
                if hora in ('00','01','02','03','04','05'):                    
                    date2 = time.strftime('%Y-%m-%d %H:%M:%S') 
                    date1 = (dt.date.today() - relativedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    date1 = inv.date_invoice or time.strftime('%Y-%m-%d')                    
                    date2 = time.strftime('%Y-%m-%d %H:%M:%S') 
                res['date_invoice'] = date1
                #self.write(cr, uid, [inv.id], {'date_invoice2':time.strftime('%Y-%m-%d %H:%M:%S')})
                self.write(cr, uid, [inv.id], {'date_invoice2':date2})
            if inv.date_invoice2:
                date1=inv.date_invoice2[:10]
                date2=inv.date_invoice2 
                date = date1
            if inv.authorization_sales:
                if not auth_obj.check_date_document(cr, uid, inv.authorization_sales.id, date,inv.user_id):
                    raise osv.except_osv(_('Invalid action!'), _('The date entered is not valid for the authorization'))
                
            pterm_list = pt_obj.compute(cr, uid, inv.payment_term.id, value=1, date_ref=date1)
            if pterm_list:
                pterm_list = [line[0] for line in pterm_list]
                pterm_list.sort()
                res['date_due']= pterm_list[-1]
            else:
                raise osv.except_osv(_('Data Insufficient !'), _('The payment term of supplier does not have a payment term line!'))
            self.write(cr, uid, [inv.id], {'date_invoice':date1,'date_invoice2':date2,'date_due':pterm_list[-1]})        
        return res
        
    def action_open_draft(self, cr, uid, ids, *args):
        context = {}  # TODO: Use context from arguments
        move_ids = []
        comment = ''
        authorization_obj = self.pool.get('sri.authorization')
        account_move_obj = self.pool.get('account.move')
        wf_service = netsvc.LocalService("workflow")
        # First, set the invoices as cancelled and detach the move ids
        self.write(cr, uid, ids, {'state':'draft'})
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for i in self.browse(cr, uid, ids, context=None):
#            if i.date_invoice < time.strftime('%Y-%m-%d'):
            if not (uid == 1 or user.is_supervisor):
#                raise osv.except_osv(_('Error !'), _('No puede anular una factura de una fecha anterior a la actual, por favor, solicite la aprobación de su supervisor!'))
                raise osv.except_osv(_('Error !'), _('Necesita la autorización de su supervisor para anular una factura!'))
            line_id = None
            if i.authorization_sales:
                line_id = authorization_obj.get_line_id(cr, uid, i.journal_id.type, i.shop_id.id, i.printer_id.id, i.authorization_sales.id, {})
            if i.authorization_purchase:
                line_id = authorization_obj.get_line_id(cr, uid, i.journal_id.type, i.shop_id.id, i.printer_id.id, i.authorization_purchase.id, {})
            if line_id:
                self.pool.get('sri.authorization.line').rest_document(cr, uid, line_id, {})
                self.pool.get('sri.authorization.line').rest_sequence(cr, uid, line_id, {})
            if i['payment_ids']:
                for move_line in i['payment_ids']:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        raise osv.except_osv(_('Error !'), _('No se puede cancelar un factura parcialmente pagada. Necesita eliminar los pagos realizados'))
            if i.comment:
                comment = i.comment + '\n'
            if i.move_id:
                move_ids.append(i.move_id.id)
                self.write(cr, uid, [i.id], {'move_id':False})
            wf_service.trg_delete(uid, 'account.invoice', i.id, cr)
            wf_service.trg_create(uid, 'account.invoice', i.id, cr)
        if move_ids:
            # second, invalidate the move(s)
            account_move_obj.button_cancel(cr, uid, move_ids, context=context)
            account_move_obj.unlink(cr, uid, move_ids, context=context)
        if context.get('supervisor_id',False):
            sup_id = context.get('supervisor_id',False)
            supervisor_id = self.pool.get('res.users').browse(cr,uid,sup_id).login
        else:
            supervisor_id = self.pool.get('res.users').browse(cr,uid,uid).login            
        comment = comment +'Factura anulada o reabierta por el/la supervisor(a) ' + supervisor_id + ' el ' + time.strftime('%Y-%m-%d %H:%M:%S')
        cr.execute("""update account_invoice set  write_date =now(), history_document=%s where id in %s """,(comment,tuple(ids)))
        return True
    
    def action_cancel_draft(self, cr, uid, ids, *args):
        authorization_obj = self.pool.get('sri.authorization')
        for invoice in self.browse(cr, uid, ids):
            if invoice.flag:
                line_id = None
                if invoice.authorization_sales:
                    line_id = authorization_obj.get_line_id(cr, uid, invoice.journal_id.type, invoice.shop_id.id, invoice.printer_id.id, invoice.authorization_sales.id, {})
                if invoice.authorization_purchase:
                    line_id = authorization_obj.get_line_id(cr, uid, invoice.journal_id.type, invoice.shop_id.id, invoice.printer_id.id, invoice.authorization_purchase.id, {})
                if line_id:
                    self.pool.get('sri.authorization.line').rest_document(cr, uid, line_id, {})
                    self.pool.get('sri.authorization.line').rest_sequence(cr, uid, line_id, {})
            self.write(cr, uid, [invoice.id], {'invoice_number': None, 'cancel_user_id':None, 'cancel_date':None, 'flag':False}, context=None)
        return super(account_invoice, self).action_cancel_draft(cr, uid, ids)
    
    def clean_values_invoice_cancel(self, cr, uid, ids, context):
        cr.execute("""UPDATE account_invoice_tax set base = 0.0, amount = 0.0, base_amount = 0.0,
                        tax_amount = 0.0 WHERE invoice_id in %s""", (tuple(ids),))
        cr.execute("""UPDATE account_invoice_line set quantity = 0.0, cost_price = 0.0, discount = 0.0, price_unit = 0.0, iva_value = 0.00, margin = 0.00,
                            price_product = 0.00, price_subtotal = 0.0, offer=0.0 WHERE invoice_id in %s""", (tuple(ids),))
        cr.execute("""UPDATE account_invoice set amount_tax_withhold_vat = 0.0, amount_tax_withhold = 0.0, amount_tax_other = 0.0, amount_untaxed = 0.0, amount_total = 0.0, amount_total_vat = 0.0, residual=0.0, amount_tax = 0.00, amount_base_vat_12 = 0.0 
                       WHERE id in %s""", (tuple(ids),))
        return True
        

    def action_cancel(self, cr, uid, ids, *args):
        context = {}  # TODO: Use context from arguments
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for i in ids:
            invoice = self.browse(cr, uid, i, context)
            if invoice.purchase_order_id.id:
                raise osv.except_osv(_('Error !'), _('No puede anular una factura que tiene órdenes de compras asociadas!'))
            self.write(cr, uid, [i], {'cancel_user_id':uid, 'cancel_date':time.strftime('%Y-%m-%d %H:%M:%S')})
            if invoice.type in ('out_invoice', 'out_refund'):
                if invoice.state == 'draft':
                    if invoice.invoice_number_out:
                        self.write(cr, uid, [invoice.id], {'invoice_number': invoice.invoice_number_out}, context)
                    if invoice.authorization_sales:
                        line_id = self.pool.get('sri.authorization').get_line_id(cr, uid, invoice.journal_id.type, invoice.shop_id.id, invoice.printer_id.id, invoice.authorization_sales.id, context)
#                         self.pool.get('sri.authorization.line').add_document(cr, uid, line_id, context)
                if invoice.date_invoice < time.strftime('%Y-%m-%d'):
                    if not (uid == 1 or user.is_supervisor):
                        raise osv.except_osv(_('Error !'), _('No puede anular una factura de una fecha anterior a la actual, por favor, solicite la aprobación de su supervisor!'))
            super(account_invoice, self).action_cancel(cr, uid, [invoice.id])
            if invoice.type == 'out_invoice':
                cr.execute("SELECT order_id FROM sale_order_invoice_rel WHERE invoice_id = %s", (i,))
                obj = 'sale.order'
            elif invoice.type == 'in_invoice':
                cr.execute("SELECT purchase_id FROM purchase_invoice_rel WHERE invoice_id = %s", (i,))
                obj = 'purchase.order'
            try:
                dt = cr.fetchall()
            except:
                dt = False
            if dt:
                for tup in cr.fetchall():
                    order_id = [n for n in tup]
                    for order in self.pool.get(obj).browse(cr, uid, order_id, context):
                        b = False
                        if order.state != 'cancel':
                            if order.invoice_ids:
                                for inv in order.invoice_ids:
                                    if inv.state not in ('draft', 'cancel'):
                                        b = True
                                for pick in order.picking_ids:
                                    if pick.state not in ('draft', 'cancel'):
                                        b = True
                        if not b:
                            self.pool.get(obj).action_cancel(cr, uid, [order.id], context)
        return self.clean_values_invoice_cancel(cr, uid, ids, context)

    def cancel_only_invoice(self, cr, uid, ids, *args):
        context = {}
        account_move_obj = self.pool.get('account.move')
        invoices = self.read(cr, uid, ids, ['move_id', 'payment_ids'])
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        move_ids = []  # ones that we will need to remove
        for i in invoices:
            inv = self.browse(cr, uid, i['id'], context)
            if inv.type in ('out_invoice', 'out_refund'):
                if inv.date_invoice < time.strftime('%Y-%m-%d'):
                    if not (uid == 1 or user.is_supervisor):
                        raise osv.except_osv(_('Error !'), _('No puede anular una factura de una fecha anterior a la actual, por favor, solicite la aprobación de su supervisor!'))
            if i['move_id']:
                move_ids.append(i['move_id'][0])
            if i['payment_ids']:
                account_move_line_obj = self.pool.get('account.move.line')
                pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        raise osv.except_osv(_('Error !'), _('No se puede cancelar un factura parcialmente pagada. Necesita eliminar los pagos realizados'))
        self.write(cr, uid, ids, {'state':'cancel', 'move_id':False, 'cancel_user_id':uid, 'cancel_date':time.strftime('%Y-%m-%d %H:%M:%S')})
        if move_ids:
            account_move_obj.button_cancel(cr, uid, move_ids, context=context)
            account_move_obj.unlink(cr, uid, move_ids, context=context)
        self._log_event(cr, uid, ids, -1.0, 'Cancel Invoice')
        return self.clean_values_invoice_cancel(cr, uid, ids, context)
    
    def unlink(self, cr, uid, ids, context=None):
        res_users = 'Factura anulada por usuario ' + self.pool.get('res.users').browse(cr,uid,uid).login
        for inv in self.browse(cr, uid, ids, context):
            if inv.purchase_order_id:
                raise osv.except_osv(_('Invalid action!'), _('No se pueden borrar facturas que tienes órdenes de compras asociadas!'))
            if not inv.state == 'draft':
                raise osv.except_osv(_('Invalid action!'), _('Solo puede inactivar facturas en estado de borrador'))
            if inv.move_id:
                move = inv.move_id
                if move.state != 'draft':
                    self.pool.get('account.move').button_cancel(cr, uid, [move.id], context)
                    self.pool.get('account.move').unlink(cr, uid, [move.id], context)
                else:
                    self.pool.get('account.move').unlink(cr, uid, [move.id], context)
        cr.execute("""update account_invoice_line set write_date =now(), state='cancel'where invoice_id in %s """,(tuple(ids),))            
        cr.execute("""update account_invoice set write_date =now(), invoice_number=Null, invoice_number_out=Null, number=Null, internal_number= Null, state='cancel', history_document=%s where id in %s """,(res_users, tuple(ids)))
        return True
#         return super(account_invoice, self).unlink(cr, uid, ids, context)


    def copy(self, cr, uid, ids, default={}, context=None):
        default = default or {}
        invoice = self.browse(cr, uid, ids, context)
#         default.update(self.onchange_cash(cr, uid, ids, invoice.company_id.id, invoice.shop_id.id, invoice.type, invoice.printer_id.id, invoice.journal_id.id, context)['value'])
        default.update({
            'fiscal_position':invoice.fiscal_position.id,
            'user_id': uid,
            'shop_id': False,
            'printer_id': False,
            'invoice_number': False,
            'invoice_number_in': False,
            'invoice_number_out': False,
            'internal_number':False,
            'number':False,
            'authorization_purchase': False,
            'authorization_sale': False,
            'cancel_date': False,
            'cancel_user_id': False,
            'digiter_id': None,
            'address_contact_id': False,
            'comment':None,
            'name':None,
            'nb_print':0,
            'date_invoice2': False,
            'date_invoice': False,
            'proforma': self.pool.get('ir.sequence').next_by_code(cr, uid, 'sale.order'),
                    })
        return super(account_invoice, self).copy(cr, uid, ids, default, context)

    #@profile
    def button_reset_taxes(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ait_obj = self.pool.get('account.invoice.tax')
        cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (tuple(ids),))
        for id in ids:
            for taxe in ait_obj.compute(cr, uid, id, context=ctx).values(): 
                if taxe:
                    tax_amount = taxe.get('tax_amount',False)
                    name = taxe.get('name',False)
                    sequence = taxe.get('sequence',None)
                    invoice_id = taxe.get('invoice_id', False)
                    base_amount = taxe.get('base_amount',False)
                    manual= taxe.get('manual',False)
                    base_code_id = taxe.get('base_code_id', False)
                    tax_code_id = taxe.get('tax_code_id',False) or base_code_id 
                    amount = taxe.get('amount',0.00)
                    base = taxe.get('base',0.00)
                    account_id = taxe.get('account_id',False)
                    company_id = self.browse(cr,uid,id).company_id.id
                    create_uid = uid
                    create_date = time.strftime('%Y-%m-%d %H:%M:%S')
                    sql = """INSERT INTO account_invoice_tax(create_uid, create_date,tax_amount, account_id, sequence, company_id, invoice_id, manual, base_amount, base_code_id, amount, base, tax_code_id, name)VALUES (%s,'%s',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'%s')"""%(create_uid, create_date,tax_amount, account_id, sequence, company_id, invoice_id, manual, base_amount, base_code_id, amount, base, tax_code_id, name)
                    cr.execute(sql)
        return True

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, context=None):
        context = context or {} 
        if not line_dr_ids:
            return {'value':{}}
        line_osv = self.pool.get('account.invoice.line')
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['price_iva','price_subtotal','price_product','offer','discount','price_unit','iva_value','quantity','invoice_line_tax_id'], context)
        total = 0.00
        amount_tax = 0.00
        total_quantity = 0.00
        total_discount = 0.00
        total_offer = 0.00
        pretotal = 0.00
        b=True
        for line in line_dr_ids:
            if not line.get('authorized',True):
                b=False
            amount = line.get('price_subtotal',0.0)
            price_iva = line.get('price_iva',0.0)
            iva_value = line.get('iva_value',0.0)
            price_product = line.get('price_product',0.0)
            discount = line.get('discount',0.0)
            offer = line.get('offer',0.0)
            quantity = line.get('quantity',0.0)            
            pretotal += price_product * quantity
            total_quantity += quantity
            total_discount += price_product * discount/100 * quantity
            total_offer += (price_product * (1 - discount/100)) * offer/100 * quantity             
            amount_tax += iva_value
            total += amount
        amount_total = total + amount_tax
        return {'value': {'authorized':b,'pretotal':pretotal,'amount_untaxed': total,'amount_total_vat':amount_tax,'amount_total':amount_total,'amount_total_discount':total_discount,'amount_total_offer':total_offer,'account_quantity':total_quantity}}



    def print_invoice(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.nb_print + 1
            self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'invoice_report_id',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 


    def print_liquidation(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.nb_print + 1
            self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'liquidacion_compras',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 

    def print_others(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.nb_print + 1
            self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'others_documents',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 


account_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: