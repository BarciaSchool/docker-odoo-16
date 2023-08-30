# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

import time
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc
from account_voucher import account_voucher

class account_invoice_line(osv.osv):

    def get_amount_data_all(self,cr,uid,ids,name,args,context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id]={}
            if invoice.type in ('out_refund','in_refund'):
                res[invoice.id]['cost_subtotal_s'] = invoice.cost_subtotal * -1
                res[invoice.id]['price_subtotal_s'] = invoice.price_subtotal * -1
            else:
                res[invoice.id]['cost_subtotal_s'] = invoice.cost_subtotal * 1
                res[invoice.id]['price_subtotal_s'] = invoice.price_subtotal * 1
        return res

        
    def _amount_data_all(self, cr, uid, ids, field_names, arg, context=None):
        return self.get_amount_data_all(cr, uid, ids, field_names, arg, context)
    
    _inherit = "account.invoice.line"
    _columns = {
        'cost_subtotal_s': fields.function(_amount_data_all, multi='account_invoice_line_amount', string='Costs', store=True, digits_compute=dp.get_precision('Account')),
        'price_subtotal_s': fields.function(_amount_data_all, multi='account_invoice_line_amount', string='Subtotal', store=True, digits_compute=dp.get_precision('Account')),
        }
    
account_invoice_line()

class account_invoice(osv.osv):
    
    def get_amount_data_invoice(self,cr,uid,ids,name,args,context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id]={}
            if invoice.type in ('out_refund','in_refund'):
                res[invoice.id]['amount_untaxed_s'] = invoice.amount_untaxed * -1
                res[invoice.id]['amount_total_vat_s'] = invoice.amount_total_vat * -1
                res[invoice.id]['amount_total_s'] = invoice.amount_total * -1
                res[invoice.id]['residual_s'] = invoice.residual * -1
            else:
                res[invoice.id]['amount_untaxed_s'] = invoice.amount_untaxed * 1
                res[invoice.id]['amount_total_vat_s'] = invoice.amount_total_vat * 1
                res[invoice.id]['amount_total_s'] = invoice.amount_total * 1
                res[invoice.id]['residual_s'] = invoice.residual * 1
        return res

    def _amount_data_invoice(self, cr, uid, ids, name, args, context=None):
        return self.get_amount_data_invoice(cr, uid, ids, name, args, context)
    
    _inherit = 'account.invoice'        
    _columns = {
        'amount_untaxed_s': fields.function(_amount_data_invoice, method=True,type="float", digits_compute=dp.get_precision('Account'), string='Untaxed',store=True, multi='vat'),
        'amount_total_vat_s': fields.function(_amount_data_invoice, method=True,type="float", digits_compute=dp.get_precision('Account'), string='Vat',store=True, multi='vat'),
        'amount_total_s': fields.function(_amount_data_invoice, method=True,type="float", digits_compute=dp.get_precision('Account'), string='Total',store=True, multi='vat'),
        'residual_s': fields.function(_amount_data_invoice, method=True,type="float", digits_compute=dp.get_precision('Account'), string='Residual',store=True, multi='vat'),
    }

    def clean_values_invoice_cancel(self, cr, uid, ids, context):
        cr.execute("""UPDATE account_invoice_tax set base = 0.0, amount = 0.0, base_amount = 0.0, tax_amount = 0.0 WHERE invoice_id in %s""", (tuple(ids),))
        cr.execute("""UPDATE account_invoice_line set quantity = 0.0, cost_price = 0.0, discount = 0.0, price_unit = 0.0, iva_value = 0.00, margin = 0.00,
                        cost_subtotal_s = 0.00, price_subtotal_s= 0.00 ,price_product = 0.00, price_subtotal = 0.0, offer=0.0 WHERE invoice_id in %s""", (tuple(ids),))
        cr.execute("""UPDATE account_invoice set amount_tax_withhold_vat = 0.0, amount_tax_withhold = 0.0, amount_tax_other = 0.0, amount_untaxed = 0.0, amount_total = 0.0, amount_total_vat = 0.0, residual=0.0, amount_tax = 0.00, amount_base_vat_12 = 0.0, amount_untaxed_s = 0.00, amount_total_vat_s = 0.00,
                        amount_total_s = 0.00, residual_s = 0.00 WHERE id in %s""", (tuple(ids),))
        return True

account_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

