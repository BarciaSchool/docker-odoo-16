# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#
##############################################################################

from osv import fields, osv, orm
from tools.translate import _
from lxml import etree
from operator import itemgetter
from datetime import datetime
import time
import tools
import netsvc

# class account_move(osv.osv):
#     _inherit = "account.move"
#     
# account_move()

class account_move_line(osv.osv):
    _inherit = "account.move.line"
    
    _rec_name = 'ref'
    
    def _check_currency(self, cr, uid, ids, context=None):
        return True

    _constraints = [
        (_check_currency, 'The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account or select a multi-currency view on the journal.', ['currency_id']),
    ]

    
    def onchange_lines_move_id(self, cr, uid, ids, date, company_id=False, partner_id=False, period_id=False, journal_id=False, ref='', context=None):
        result={}
        if partner_id:
            result['partner_id'] = partner_id
        if period_id:
            result['period_id'] = period_id
        else:
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date), ('state', '=', 'draft')])
            result['period_id'] = period_ids[0]
        if journal_id:
            result['journal_id'] = journal_id
        if ref:
            result['reference'] = ref
        if date: 
            result['date'] = date
            result['date_create'] = date
        return {'value': result}

account_move_line()

class account_tax (osv.osv):
    _inherit = 'account.tax'
    
    def _unit_compute(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None, quantity=0):
        taxes = self._applicable(cr, uid, taxes, price_unit, address_id, product, partner)
        res = []
        cur_price_unit=price_unit
        obj_partener_address = self.pool.get('res.partner.address')
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            data = {'id':tax.id,
                    'name':tax.description and tax.description + " - " + tax.name or tax.name,
                    'account_collected_id':tax.account_collected_id.id,
                    'account_paid_id':tax.account_paid_id.id,
                    'base_code_id': tax.base_code_id.id,
                    'ref_base_code_id': tax.ref_base_code_id.id,
                    'sequence': tax.sequence,
                    'base_sign': tax.base_sign,
                    'tax_sign': tax.tax_sign,
                    'ref_base_sign': tax.ref_base_sign,
                    'ref_tax_sign': tax.ref_tax_sign,
                    'price_unit': cur_price_unit,
                    'tax_code_id': tax.tax_code_id.id,
                    'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
            if tax.type=='percent':
                if tax.tax_type == 'perception':
                    amount = cur_price_unit * tax.amount_variable
                else:
                    amount = cur_price_unit * tax.amount
                data['amount'] = amount

            elif tax.type=='fixed':
                if tax.tax_type == 'perception':
                    data['amount'] = tax.amount_varialbe
                else:
                    data['amount'] = tax.amount
                data['tax_amount']=quantity
               # data['amount'] = quantity
            elif tax.type=='code':
                address = address_id and obj_partener_address.browse(cr, uid, address_id) or None
                localdict = {'price_unit':cur_price_unit, 'address':address, 'product':product, 'partner':partner}
                exec tax.python_compute in localdict
                amount = localdict['result']
                data['amount'] = amount
            elif tax.type=='balance':
                data['amount'] = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
                data['balance'] = cur_price_unit

            amount2 = data.get('amount', 0.0)
            if tax.child_ids:
                if tax.child_depend:
                    latest = res.pop()
                amount = amount2
                child_tax = self._unit_compute(cr, uid, tax.child_ids, amount, address_id, product, partner, quantity)
                res.extend(child_tax)
                if tax.child_depend:
                    for r in res:
                        for name in ('base','ref_base'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['price_unit'] = latest['price_unit']
                                latest[name+'_code_id'] = False
                        for name in ('tax','ref_tax'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['amount'] = data['amount']
                                latest[name+'_code_id'] = False
            if tax.include_base_amount:
                cur_price_unit+=amount2
        return res
account_tax()    