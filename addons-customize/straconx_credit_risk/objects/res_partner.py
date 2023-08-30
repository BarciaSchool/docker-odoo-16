# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Albert Cervera i Areny (http://www.nan-tic.com). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from osv import osv, fields
#from DateTime import now
import datetime
from tools.translate import _

class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _calculate_accounts(self, partner, context={}):
        accounts = []
        tp = context.get('type', 'normal')
        accounts = []
        if tp == 'normal':
            accounts = partner.property_account_receivable and [partner.property_account_receivable.id] or []
            accounts += partner.property_account_payable and [partner.property_account_payable.id] or []
        elif tp == 'protested':
            for account_bank in partner.bank_ids:
                accounts = account_bank.bank.account_protested_id and [account_bank.bank.account_protested_id.id] or []
            accounts = list(set(accounts))
        elif tp == 'rejected':
            for account_bank in partner.bank_ids:
                accounts = account_bank.bank.account_rejected_id and [account_bank.bank.account_rejected_id.id] or [] 
            accounts = list(set(accounts))
        return accounts

    def _unpayed_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        for partner in self.browse(cr, uid, ids, context):
            accounts = self._calculate_accounts(partner)
            line_ids = self.pool.get('account.move.line').search(cr, uid, [
                ('partner_id', '=', partner.id),
                ('account_id', 'in', accounts),
                ('reconcile_id', '=', False),
                ('date_maturity', '<', today),
            ], context=context)
            # Those that have amount_to_pay == 0, will mean that they're circulating. The payment request has been sent
            # to the bank but have not yet been reconciled (or the date_maturity has not been reached).
            amount = 0.0
            for line in self.pool.get('account.move.line').browse(cr, uid, line_ids, context):
                # amount += -line.amount_to_pay
                amount += line.debit - line.credit
            res[partner.id] = amount
        return res

    def _circulating_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        for partner in self.browse(cr, uid, ids, context):
            accounts = self._calculate_accounts(partner)
            line_ids = self.pool.get('account.move.line').search(cr, uid, [
                ('partner_id', '=', partner.id),
                ('account_id', 'in', accounts),
                ('reconcile_id', '=', False),
                '|', ('date_maturity', '>=', today), ('date_maturity', '=', False)
            ], context=context) 
            # Those that have amount_to_pay == 0, will mean that they're circulating. The payment request has been sent
            # to the bank but have not yet been reconciled (or the date_maturity has not been reached).
            amount = 0.0
            for line in self.pool.get('account.move.line').browse(cr, uid, line_ids, context):
                amount += line.debit - line.credit
            res[partner.id] = amount
        return res

    def _protested_cheques(self, cr, uid, ids, name, arg, context=None):
        res = {}
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        for partner in self.browse(cr, uid, ids, context):
            accounts = self._calculate_accounts(partner, {'type':'protested'})
            line_ids = self.pool.get('account.move.line').search(cr, uid, [
                ('partner_id', '=', partner.id),
                ('account_id', 'in', accounts),
                ('reconcile_id', '=', False),
                '|', ('date_maturity', '<=', today), ('date_maturity', '=', False)
            ], context=context) 
            # Those that have amount_to_pay == 0, will mean that they're circulating. The payment request has been sent
            # to the bank but have not yet been reconciled (or the date_maturity has not been reached).
            amount = 0.0
            for line in self.pool.get('account.move.line').browse(cr, uid, line_ids, context):
                amount += line.debit - line.credit
            res[partner.id] = amount
        return res
        
    def _rejected_cheques(self, cr, uid, ids, name, arg, context=None):
        res = {}
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        for partner in self.browse(cr, uid, ids, context):
            accounts = self._calculate_accounts(partner, {'type':'rejected'})
            line_ids = self.pool.get('account.move.line').search(cr, uid, [
                ('partner_id', '=', partner.id),
                ('account_id', 'in', accounts),
                ('reconcile_id', '=', False),
                '|', ('date_maturity', '<=', today), ('date_maturity', '=', False)
            ], context=context) 
            # Those that have amount_to_pay == 0, will mean that they're circulating. The payment request has been sent
            # to the bank but have not yet been reconciled (or the date_maturity has not been reached).
            amount = 0.0
            for line in self.pool.get('account.move.line').browse(cr, uid, line_ids, context):
                amount += line.debit - line.credit
            res[partner.id] = amount
        return res
        
    def _pending_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        for partner in self.browse(cr, uid, ids, context):
            accounts = self._calculate_accounts(partner,)
            line_ids = self.pool.get('account.move.line').search(cr, uid, [
                ('partner_id', '=', partner.id),
                ('account_id', 'in', accounts),
                ('reconcile_id', '=', False),
                '|', ('date_maturity', '>=', today), ('date_maturity', '=', False)
            ], context=context) 
            # Those that have amount_to_pay == 0, will mean that they're circulating. The payment request has been sent
            # to the bank but have not yet been reconciled (or the date_maturity has not been reached).
            amount = 0.0
            for line in self.pool.get('account.move.line').browse(cr, uid, line_ids, context):
                amount += line.debit - line.credit
            res[partner.id] = amount
        return res

    def _draft_invoices_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        for id in ids:
            invids = self.pool.get('account.invoice').search(cr, uid, [
                ('partner_id', '=', id),
                ('state', '=', 'draft'),
                '|', ('date_due', '>=', today), ('date_due', '=', False)
            ], context=context)
            val = 0.0
            for invoice in self.pool.get('account.invoice').browse(cr, uid, invids, context):
                # Note that even if the invoice is in 'draft' state it can have an account.move because it 
                # may have been validated and brought back to draft. Here we'll only consider invoices with 
                # NO account.move as thouse will be added in other fields.
                if invoice.move_id:
                    continue
                if invoice.type in ('out_invoice', 'in_refund'):
                    val += invoice.amount_total
                else:
                    val -= invoice.amount_total
            res[id] = val
        return res

    def _pending_orders_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for id in ids:
            sids = self.pool.get('sale.order').search(cr, uid, [
                ('partner_id', '=', id),
                ('state', 'not in', ['draft', 'cancel', 'wait_risk', 'expired'])
            ], context=context)
            total = 0.0
            for order in self.pool.get('sale.order').browse(cr, uid, sids, context):
                total += order.amount_total - order.amount_invoiced
            res[id] = total
        return res

    def _total_debt(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context):
            pending_orders = partner.pending_orders_amount or 0.0
            circulating = partner.circulating_amount or 0.0
            unpayed = partner.unpayed_amount or 0.0
            draft_invoices = partner.draft_invoices_amount or 0.0
            res[partner.id] = pending_orders + circulating + unpayed + draft_invoices
        return res

    def _available_risk(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context):
            res[partner.id] = partner.credit_limit - partner.total_debt
        return res

    def _total_risk_percent(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context):
            if partner.credit_limit:
                res[partner.id] = 100 * partner.total_debt / partner.credit_limit
            else:
                res[partner.id] = 100
        return res
    
    def get_partner_checks(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for res_partner in self.browse(cr, uid, ids, context):
            res[res_partner.id] = self.pool.get("account.payments").search(cr, uid, [('partner_id', '=', res_partner.id)])
        return res
    
    def _get_partner_checks(self, cr, uid, ids, field_name, arg, context=None):
        return self.get_partner_checks(cr, uid, ids, field_name, arg, context)


    _columns = {
        'unpayed_amount': fields.function(_unpayed_amount, method=True, store=True, string='Expired Unpaid Payments', type='float'),
        'pending_amount': fields.function(_pending_amount, method=True, store=True, string='Unexpired Pending Payments', type='float'),
        'draft_invoices_amount': fields.function(_draft_invoices_amount, method=True, store=True, string='Draft Invoices', type='float'),
        'pending_orders_amount': fields.function(_pending_orders_amount, method=True, store=True, string='Uninvoiced Orders', type='float'),
        'circulating_amount': fields.function(_circulating_amount, method=True, store=True, string='Payments Sent to Bank', type='float'),
        'rejected_cheques': fields.function(_rejected_cheques, method=True, store=True, string='Checks Rejected', type='float'),
        'protested_cheques': fields.function(_protested_cheques, method=True, store=True, string='Checks Protested', type='float'),
        # 'credit_limit': fields.float(string='Credit Limit'),
        'total_debt': fields.function(_total_debt, method=True, store=True, string='Total Debt', type='float'),
        'available_risk': fields.function(_available_risk, method=True, store=True, string='Available Credit', type='float'),
        'total_risk_percent': fields.function(_total_risk_percent, method=True, store=True, string='Credit Usage (%)', type='float'),
        'checks_ids': fields.function(_get_partner_checks, method=True, type='one2many', obj='account.payments', string='Checks', readonly=True),
    }
    
    def button_dummy(self, cr, uid, ids, context):
        self.write(cr, uid, ids, {}, context)
        return True
        
res_partner()