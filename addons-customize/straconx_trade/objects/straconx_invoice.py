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


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    
    def _amount_tax_duty(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id]=0.0
            neto = (line.price_unit+line.cost_expense_unit)
            if line.tradetax:
                if line.tradetax.line_ids:
                    for duties in line.tradetax.line_ids:
                        if duties.applicability == 'cost_only':
                            res[line.id]+=(neto*duties.tax_percentage)/100
        return res
    
    def _amount_tax_vat(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id]=0.0
            neto = (line.price_unit+line.cost_expense_unit+line.amount_tax_duty)
            if line.tradetax:
                if line.tradetax.line_ids:
                    for duties in line.tradetax.line_ids:
                        if duties.applicability == 'cost_duty':
                            res[line.id]+=(neto*duties.tax_percentage)/100
        return res
    
    def _amount_total_unit(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id]=line.price_unit+line.cost_expense_unit+line.amount_tax_duty+line.amount_others
        return res
    
    def _amount_total_unit_quantity(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id]=(line.price_unit+line.cost_expense_unit+line.amount_tax_duty+line.amount_others)*line.quantity
        return res

    def _amount_total(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id]=line.amount_total_unit*line.quantity
        return res
    
    _columns = {
                'tradetax': fields.many2one('product.tradetax','Tradetax'),
                'international':fields.boolean('International', required=False),
                "cost_expense_unit": fields.float("Cost Expense Unit",digits_compute=dp.get_precision('Trade')),
                "amount_others": fields.float("Others Costs"),
                "amount_tax_duty": fields.function(_amount_tax_duty, method=True, type="float",digits_compute=dp.get_precision('Trade'),string="Amount Tax Duty"),
                "amount_tax_vat": fields.function(_amount_tax_vat, method=True, type="float",digits_compute=dp.get_precision('Trade'),string="Amount Tax Vat"),
                "amount_total_unit": fields.function(_amount_total_unit, method=True, type="float",digits_compute=dp.get_precision('Trade'),string="Amount total unit"),
                "amount_total_unit_quantity": fields.function(_amount_total_unit_quantity, method=True, type="float",digits_compute=dp.get_precision('Trade'),string="Amount total unit"),
                "amount_total": fields.function(_amount_total, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Amount total"),
                'tpurchase':fields.selection([('purchase','Purchase'),('expense','Expense'),('trade_expense','Trade Expense')],'Purchase type', select=True, readonly=True, states={'draft':[('readonly',False)]}),
                'trade_id1':fields.many2one('purchase.trade', 'Trade Order Purchase'),
                }
    
    _rec_name="invoice_id"
    
    _defaults={
        "trade_id1": lambda *a: False,        
    }    
    
    def name_get(self, cr, uid, ids, context=None):
        account_obj = self.pool.get('account.invoice')
        res = []
        name=""
        if not len(ids):
            return []
        for line in self.browse(cr, uid, ids, context):
            if line.invoice_id and line.invoice_id:
                if account_obj.browse(cr,uid,line.invoice_id.id):
                    name=name+"%s"%(line.invoice_id.number)
                res.append((line.id, name))
        return res

    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        default.update({
            'trade_id1':None,
            })
        return super(account_invoice, self).copy(cr, uid, id, default, context)

    #@profile
    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, currency_id=False, context=None, company_id=None, discount=0, offer=0, shop_id = False, order_id = False, order_line=False):
        if context is None:
            context={}
        result=super(account_invoice_line,self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id, context, company_id, discount, offer, shop_id, order_id, order_line)
        company_id = company_id or context.get('company_id',False) or self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        tpurchase = context.get('tpurchase',False)
        if product:
            if tpurchase == 'trade':
                res = self.pool.get('product.product').browse(cr, uid, product, context=context)    
                if company_id:
                    fpos = fposition_id and self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id, context=context) or False
                    company = self.pool.get('res.company').browse(cr,uid,company_id,context=context)
                    if not company.property_account_move_duty:
                        raise osv.except_osv(_('Invalid action!'), _('Need a account for trade account moves. Please configure in company.'))
                    a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, company.property_account_move_duty.id)
                    result['value']['account_id'] = a
                    taxes = res.supplier_taxes_id and res.supplier_taxes_id or (a and self.pool.get('account.account').browse(cr, uid, a, context=context).tax_ids or False)
                    if taxes:
                        tax_id = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
                        result['value']['invoice_line_tax_id'] = tax_id
        return result
account_invoice_line()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
                'trade_id1':fields.many2one('purchase.trade', 'Trade Order Purchase'),
                'trade_id2':fields.many2one('purchase.trade', 'Trade Order delivery'),
                'trade_id3':fields.many2one('purchase.trade', 'Trade Order insurance'),
                'trade_id4':fields.many2one('purchase.trade', 'Trade Order others'),
                'liquidated':fields.boolean('liquidated'),
                }
    
    _defaults={
        "liquidated": lambda *a: False,        
    }
    
    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        default.update({
            'trade_id1':None,
            'trade_id2':None,
            'trade_id3':None,
            'trade_id4':None,
            'liquidated':False,
            })
        return super(account_invoice, self).copy(cr, uid, id, default, context)
    
    def action_cancel(self, cr, uid, ids, *args):
        context={}
        trade=[]
        invoices = self.pool.get('account.invoice').browse(cr, uid, ids, context)
        for inv in invoices:
            if inv.trade_id1:
                trade.append(inv.trade_id1)
            elif inv.trade_id2:
                trade.append(inv.trade_id2)
            elif inv.trade_id3:
                trade.append(inv.trade_id3)
            elif inv.trade_id4:
                trade.append(inv.trade_id4)
            for trad in trade:
                if trad.state not in ('draft','cancel'):
                    raise osv.except_osv(_('Error!'), _(("You can not cancel the invoice because already exist trade order %s in state confirm")%(trad.name)))
        return super(account_invoice, self).action_cancel(cr, uid, ids, context)
    
    def action_cancel_invoice_draft(self, cr, uid, ids, *args):
        context={}
        trade=[]
        invoices = self.pool.get('account.invoice').browse(cr, uid, ids, context)
        for inv in invoices:
            if inv.trade_id1:
                trade.append(inv.trade_id1)
            elif inv.trade_id2:
                trade.append(inv.trade_id2)
            elif inv.trade_id3:
                trade.append(inv.trade_id3)
            elif inv.trade_id4:
                trade.append(inv.trade_id4)
            for trad in trade:
                if trad.state not in ('draft','cancel'):
                    raise osv.except_osv(_('Error!'), _(("You can not re-open the invoice because already exist trade order %s in state confirm")%(trad.dui)))
        return super(account_invoice, self).action_cancel_invoice_draft(cr, uid, ids, context)
account_invoice()
