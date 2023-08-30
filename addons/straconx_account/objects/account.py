# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import netsvc
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
import sys
import os

from openerp.addons.account import account


def _code_get_type(self, cr, uid, context={}):
    cr.execute('select code, name from account_account_type_internal')
    return cr.fetchall()

class account_account_template(osv.osv):
    _order = "code"
    _inherit = "account.account.template"
    _columns = {
            'company_id':fields.many2one('res.company', 'Company', required=False),
            'type': fields.selection(_code_get_type, 'Internal Type',size=32, required=True,
                                     help="This type is used to differentiate types with "\
                                    "special effects in OpenERP: view can not have entries, consolidation are accounts that "\
                                    "can have children accounts for multi-company consolidations, payable/receivable are for "\
                                    "partners accounts (for debit/credit computations), closed for depreciated accounts."),
            }
    
    _defaults={
               'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account.template', context=c),
               }
    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')]
account_account_template()


class account_account(osv.osv):
    _order = "code"
    _inherit = "account.account"

    _columns = {'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
                'department_id': fields.many2one('hr.department', 'Department'),
                'type': fields.selection(_code_get_type, 'Internal Type', size=32, required=True,
                                         help="This type is used to differentiate types with "
                                         "special effects in OpenERP: view can not have entries, consolidation are accounts that "
                                         "can have children accounts for multi-company consolidations, payable/receivable are for "
                                         "partners accounts (for debit/credit computations), closed for depreciated accounts."),
                }

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]

    def copy(self, cr, uid, id, default={}, context=None, done_list=[], local=False):
        account = self.browse(cr, uid, id, context=context)
        new_child_ids = []
        if not default:
            default = {}
        default = default.copy()
        if account['code']:
            ld = account['code'][-1]
            ld = int(ld) + 1
            nw = account['code'][:-1]+str(ld)
        default['code'] = nw
        if not local:
            done_list = []
        if account.id in done_list:
            return False
        done_list.append(account.id)
        if account:
            for child in account.child_id:
                child_ids = self.copy(cr, uid, child.id, default, context=context, done_list=done_list, local=True)
                if child_ids:
                    new_child_ids.append(child_ids)
            default['child_parent_ids'] = [(6, 0, new_child_ids)]
        else:
            default['child_parent_ids'] = False
        return super(osv.osv, self).copy(cr, uid, id, default, context=context)

    def write(self, cr, uid, ids, vals, context=None):

        if context is None:
            context = {}
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        # Dont allow changing the company_id when account_move_line already exist
        if 'company_id' in vals:
            move_lines = self.pool.get('account.move.line').search(cr, uid, [('account_id', 'in', ids)])
            if move_lines:
                # Allow the write if the value is the same
                for i in [i['company_id'][0] for i in self.read(cr, uid, ids, ['company_id'])]:
                    if vals['company_id'] != i:
                        raise osv.except_osv(_('Warning !'),
                                             _('You cannot change the owner company of an account that already contains journal items.'))
        if 'code' in vals:
            move_lines = self.pool.get('account.move.line').search(cr, uid, [('account_id', 'in', ids)])
            if move_lines:
                for i in [i['code'][0] for i in self.read(cr, uid, ids, ['code'])]:
                    if vals['code'] != i:
                        raise osv.except_osv(_('¡Aviso!'), _('No se puede cambiar el código de una cuenta contable que ha tenido movimientos.'))
        if 'active' in vals and not vals['active']:
            self._check_moves(cr, uid, ids, "write", context=context)
        if 'type' in vals.keys():
            self._check_allow_type_change(cr, uid, ids, vals['type'], context=context)
        return super(osv.osv, self).write(cr, uid, ids, vals, context=context)

account_account()


class account_model(osv.osv):
    _inherit = "account.model"
    _columns = {'shop_id': fields.many2one('sale.shop', 'Shop', required=True)}

    def generate(self, cr, uid, ids, datas={}, context=None):
        move_ids = []
        entry = {}
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        pt_obj = self.pool.get('account.payment.term')
        period_obj = self.pool.get('account.period')

        if context is None:
            context = {}

        if datas.get('date', False):
            context.update({'date': datas['date']})

        move_date = context.get('date', time.strftime('%Y-%m-%d'))
        move_date = datetime.strptime(move_date, "%Y-%m-%d")
        for model in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'company_id': model.company_id.id})
            period_ids = period_obj.find(cr, uid, dt=context.get('date', False), context=ctx)
            period_id = period_ids and period_ids[0] or False
            ctx.update({'journal_id': model.journal_id.id, 'period_id': period_id, 'shop_id': model.shop_id.id})
            try:
                entry['name'] = model.name % {'year': move_date.strftime('%Y'),
                                              'month': move_date.strftime('%m'),
                                              'date': move_date.strftime('%Y-%m')}
            except:
                raise osv.except_osv(_('Wrong model !'), _('You have a wrong expression "%(...)s" in your model !'))
            move_id = account_move_obj.create(cr, uid, {
                'ref': entry['name'],
                'period_id': period_id,
                'journal_id': model.journal_id.id,
                'shop_id': model.shop_id.id,
                'date': context.get('date', fields.date.context_today(self, cr, uid, context=context))
            })
            move_ids.append(move_id)
            for line in model.lines_id:
                analytic_account_id = False
                if line.analytic_account_id:
                    if not model.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal !'),
                                             _("You have to define an analytic journal on the '%s' journal!") % (model.journal_id.name,))
                    analytic_account_id = line.analytic_account_id.id
                val = {
                    'move_id': move_id,
                    'journal_id': model.journal_id.id,
                    'period_id': period_id,
                    'shop_id': model.shop_id.id,
                    'analytic_account_id': analytic_account_id
                }

                date_maturity = context.get('date', time.strftime('%Y-%m-%d'))
                if line.date_maturity == 'partner':
                    if not line.partner_id:
                        raise osv.except_osv(_('Error !'), _("Maturity date of entry line generated by model line '%s' of model '%s' is based on "
                                                             "partner payment term! \nPlease define partner on it!") % (line.name, model.name))
                    if line.partner_id.property_payment_term:
                        payment_term_id = line.partner_id.property_payment_term.id
                        pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=date_maturity)
                        if pterm_list:
                            pterm_list = [l[0] for l in pterm_list]
                            pterm_list.sort()
                            date_maturity = pterm_list[-1]

                val.update({
                    'name': line.name,
                    'quantity': line.quantity,
                    'debit': line.debit,
                    'credit': line.credit,
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.partner_id.id,
                    'date': context.get('date', fields.date.context_today(self, cr, uid, context=context)),
                    'date_maturity': date_maturity
                })
                account_move_line_obj.create(cr, uid, val, context=ctx)

        return move_ids


account_model()


class account_payment_term(osv.osv):
    _inherit = "account.payment.term"
    _order = "id, name"

    _columns = {
        'name': fields.char('Payment Term', size=64, translate=True, required=True),
        'active': fields.boolean('Active',
                                 help="If the active field is set to False, it will allow you to hide the payment term without removing it."),
        'note': fields.text('Description', translate=True),
        'line_ids': fields.one2many('account.payment.term.line', 'payment_id', 'Terms'),
    }
    _defaults = {
        'active': 1,
    }
    _order = "name"

    def compute(self, cr, uid, id, value, date_ref=False, context=None):
        if not date_ref:
            date_ref = datetime.now().strftime('%Y-%m-%d')
        pt = self.browse(cr, uid, id, context=context)
        amount = value
        result = []
        obj_precision = self.pool.get('decimal.precision')
        for line in pt.line_ids:
            prec = obj_precision.precision_get(cr, uid, 'AccountInvoice')
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'procent':
                amt = round(value * line.value_amount, prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result.append((next_date.strftime('%Y-%m-%d'), amt))
                amount -= amt
        return result

account_payment_term()


class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []

        for account in self.browse(cr, uid, ids, context=context):
            data = []
            acc = account
            while acc:
                if not acc.parent_id:
                    data.insert(0, acc.code)
                elif acc.parent_id and not acc.parent_id.parent_id:
                    new_data = acc.code + ' - ' + acc.name
                    data.insert(0, new_data)
                else:
                    data.insert(0, acc.code + ' - ' + acc.name)
                acc = acc.parent_id
            if data and data[0]:
                data = ' / '.join(data)
                res.append((account.id, data))
        return res

    _order = "code"
account_analytic_account()