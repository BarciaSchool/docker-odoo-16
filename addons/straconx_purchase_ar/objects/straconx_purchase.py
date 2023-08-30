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

class purchase_order(osv.osv):
    _inherit = "purchase.order"

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

   
    def onchange_line_id(self, cr, uid, ids, line_dr_ids, price_with_tax=False,context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        context = context or {}
        if not line_dr_ids:
            return {'value': {}}
        line_osv = self.pool.get("purchase.order.line")
        line_dr_ids2 = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['price_subtotal', 'price_unit', 'product_qty',
                                                                                              'discount_order_total', 'offer_order_total'], context)                                                                                               
        res = super(purchase_order, self).onchange_line_id(cr, uid, ids, line_dr_ids, price_with_tax, context)
        amount_tax2 = 0.00
        for line in line_dr_ids2:
            amount = line.get('price_subtotal', 0.0)
            for ab in line.get('taxes_id', []):
                tax = ab[2]
                for l in tax:
                    t = self.pool.get('account.tax').browse(cr, uid, l)
                    if t.tax_code_id.tax_type == 'perception':
                        if t.amount_variable != 0:
                            amount_tax2 += amount * t.amount_variable
                        else:
                            amount_tax2 += 0
        amount_total = res['value']['amount_total'] 
        amount_total += amount_tax2
        res['value']['amount_total'] = amount_total
        res['value']['amount_total_perception'] = amount_tax2        
        return res
    

purchase_order()


