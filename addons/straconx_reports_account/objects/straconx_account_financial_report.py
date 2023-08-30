# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido.
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido y puede acarrear
#    inconvenientes legales.
#
##############################################################################

import time
from osv import fields, osv
from report import report_sxw
from tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import decimal_precision as dp


class accounting_financial_reports(osv.osv):

    _name = "accounting.financial.reports"

    def onchange_chart_id(self, cr, uid, ids, chart_account_id=False, context=None):
        if chart_account_id:
            company_id = self.pool.get('account.account').browse(cr, uid, chart_account_id, context=context).company_id.id
        return {'value': {'company_id': company_id}}

    def _get_level(self, cr, uid, ids, context=None):
        res = {}
        cr.execute("""select max(level) from account_account""")
        level = cr.fetchone()
        if int(level[0]):
            return level[0]
        else:
            level = (6)
            return level[0]

    _columns = {'chart_account_id': fields.many2one('account.account', 'Chart of Account', help='Select Charts of Accounts', required=True,
                                                    domain=[('parent_id', '=', False)]),
                'company_id': fields.related('chart_account_id', 'company_id', type='many2one', relation='res.company', string='Company',
                                             store=True, readonly=True),
                'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', help='Keep empty for all open fiscal year'),
                'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by",
                                           required=True),
                'period_from': fields.many2one('account.period', 'Start Period'),
                'period_to': fields.many2one('account.period', 'End Period'),
                'journal_ids': fields.many2many('account.journal', string='Journals', required=True),
                'date_from': fields.date("Start Date"),
                'date_to': fields.date("End Date"),
                'target_move': fields.selection([('posted', 'All Posted Entries'),
                                                 ('all', 'All Entries'),
                                                 ], 'Target Moves', required=True),
                'debit_credit': fields.boolean('Display Debit/Credit Columns',
                                               help="This option allow you to get more details about your the way your balances are computed."
                                               "Because it is space consumming, we do not allow to use it while doing a comparison"),
                'only_data': fields.boolean('Cuentas con Movimientos',
                                            help="Esta opción permite mostrar solo las cuentas que tienen movimientos en el debe o haber. "
                                            "No muestra las cuentas sin movimientos"),
                'enable_filter': fields.boolean('Enable Comparison'),
                'move_balance_lines': fields.one2many('accounting.financial.reports.lines', 'wizard_id', 'Movimientos Contables'),
                'account_report_id': fields.many2one('account.financial.report', 'Account Reports', required=True),
                'level': fields.integer('Level'),
                }

    def _get_fiscalyear(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<=', time.strftime('%Y-%m-%d')),
                                                                              ('date_stop', '>=', time.strftime('%Y-%m-%d')),
                                                                              ('company_id', '=', user.company_id.id),
                                                                              ('state', '=', 'draft')])
        return fiscalyear_ids[0]

    def _get_account(self, cr, uid, context=None):
        accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False)], limit=1)
        if accounts:
            return accounts[0]
        else:
            raise osv.except_osv(_('¡Error!'),
                                 _('Por favor, configurar un Plan de Cuentas para la compañía.'))

    def _get_period_from(self, cr, uid, context=None):
        init_month = time.strftime('%Y-01-01')
        last_month = time.strftime('%Y-01-31')
        company_id = self._get_company_id(cr, uid, context)
        period = self.pool.get('account.period').search(cr, uid, [('date_start', '=', init_month), ('date_stop', '=', last_month),
                                                                  ('company_id', '=', company_id)])
        return period and period[0] or False

    def _get_period_to(self, cr, uid, context=None):
        last_month = (datetime.now()-relativedelta(months=1)).strftime('%Y-%m-%d')
        company_id = self._get_company_id(cr, uid, context)
        period = self.pool.get('account.period').search(cr, uid, [('date_start', '<', last_month), ('date_stop', '>', last_month),
                                                                  ('company_id', '=', company_id)])
        return period and period[0] or False

    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        return company or False

    def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        res = {'value': {}}
        if filter == 'filter_no':
            res['value'] = {'period_from': False, 'period_to': False, 'date_from': False, 'date_to': False}
        if filter == 'filter_date':
            res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
        if filter == 'filter_period' and fiscalyear_id:
            start_period = end_period = False
            cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.special = false
                               ORDER BY p.date_start ASC, p.special ASC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               AND p.special = false
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
            periods = [i[0] for i in cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            res['value'] = {'period_from': start_period, 'period_to': end_period, 'date_from': False, 'date_to': False}
        return res

    _defaults = {'fiscalyear_id': _get_fiscalyear,
                 'company_id': _get_company_id,
                 'chart_account_id': _get_account,
                 'target_move': 'posted',
                 'filter': 'filter_no',
                 'level': _get_level,
                 'only_data': True,
                 'debit_credit': True,
                 'filter': 'filter_date'
                 }

    def _get_children_by_order(self, cr, uid, ids, context=None):
        res = []
        for id in ids:
            res.append(id)
            ids2 = self.search(cr, uid, [('parent_id', '=', id)], order='sequence DESC', context=context)
            res += self._get_children_by_order(cr, uid, ids2, context=context)
        return res

    def _get_balance(self, cr, uid, ids, field_names, args, context=None):
        account_obj = self.pool.get('account.account')
        res = {}
        for report in self.browse(cr, uid, ids, context=context):
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in field_names)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                for a in report.account_ids:
                    for field in field_names:
                        res[report.id][field] += getattr(a, field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                report_types = [x.id for x in report.account_type_ids]
                account_ids = account_obj.search(cr, uid, [('user_type', 'in', report_types), ('type', '!=', 'view')], context=context)
                for a in account_obj.browse(cr, uid, account_ids, context=context):
                    for field in field_names:
                        res[report.id][field] += getattr(a, field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._get_balance(cr, uid, [report.account_report_id.id], field_names, False, context=context)
                for key, value in res2.items():
                    for field in field_names:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._get_balance(cr, uid, [rec.id for rec in report.children_ids], field_names, False, context=context)
                for key, value in res2.items():
                    for field in field_names:
                        res[report.id][field] += value[field]
        return res

    def get_lines(self, cr, uid, ids, context=None):
        cr.execute("""delete from accounting_financial_reports_lines WHERE WIZARD_ID = %s""", (ids[0], ))
        lines = []
        if not context:
            context = {}
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        balance_amount = 0.00
        profit_amount = 0.00
        balance_report = False
        profit_report = False

        if self.browse(cr, uid, ids[0]):
            data = self.browse(cr, uid, ids[0])
            account_report_id = data.account_report_id
            debit_credit = data.debit_credit
            level = data.level
            filter = data.filter
            target_move = data.target_move
            only_data = data.only_data
            company_id = data.company_id
            account_balance = company_id.property_reserve_and_surplus_account
            if not account_balance:
                raise osv.except_osv(_('¡Error!'),
                                     _('Por favor, configurar la cuenta de pérdidas y ganancias para el Balance General en Configuración/Compañías.'))
            if filter == 'filter_date':
                context.update({'target_move': target_move, 'date_from': data.date_from, 'date_to': data.date_to})
            elif filter == 'filter_period':
                context.update({'target_move': target_move, 'period_from': data.period_from.id, 'period_to': data.period_to.id})
        ids2 = self.pool.get('account.financial.report')._get_children_by_order(cr, uid, [account_report_id.id], context=context)
        for report in self.pool.get('account.financial.report').browse(cr, uid, ids2, context=context):
            vals = {
                'name': report.name,
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type == 'sum' and 'view' or False,
                # used to underline the financial report balances
            }
            account_ids = []
            if report.display_detail == 'no_detail':
                #  the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(cr, uid, [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(cr, uid, [('user_type', 'in', [x.id for x in report.account_type_ids])])
            if account_ids:
                for account in account_obj.browse(cr, uid, account_ids, context=context):
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    if level >= account.level:
                        vals = {
                            'code': account.code,
                            'name': account.name,
                            'type': 'account',
                            'level': report.display_detail == 'detail_with_hierarchy' and min(account.level, 6) or 6,
                            'account_type': account.type,
                            'debit': account.debit,
                            'credit': account.credit,
                            'wizard_id': ids[0],
                            'account_id': account.id,
                            'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                        }
                        if account.code in ('1', '2', '3'):
                            balance_amount += account.balance
                            balance_report = True
                        elif account.code in ('4', '5', '6', '7', '8', '9'):
                            profit_amount += account.balance
                            profit_report = True

                        if only_data:
                            debit = vals.get('debit', 0.00)
                            credit = vals.get('credit', 0.00)
                            if debit != 0.00 or credit != 0.00:
                                self.pool.get('accounting.financial.reports.lines').create(cr, uid, vals)
                        else:
                            self.pool.get('accounting.financial.reports.lines').create(cr, uid, vals)

        if balance_report:
            new_balance = account.balance + balance_amount
            if new_balance < 0.00:
                debit = abs(account.debit + new_balance)
                credit = abs(account.credit)
                new_balance = debit - credit
                name_period = 'PERDIDA DEL EJERCICIO'
            else:
                debit = abs(account.debit)
                credit = abs(account.credit + new_balance)
                new_balance = debit - credit
                name_period = 'GANANCIA DEL EJERCICIO'
            vals = {'code': 'RES-EJE',
                    'name': 'RES-EJE | RESULTADO ACUMULADO DEL EJERCICIO',
                    'type': 'account',
                    'level': 1,
                    'account_type': False,
                    'wizard_id': ids[0],
                    'account_id': False,
                    'debit': debit,
                    'credit': credit,
                    'balance': new_balance,
                    }
            self.pool.get('accounting.financial.reports.lines').create(cr, uid, vals)

        elif profit_report:

            new_balance = account.balance + profit_amount
            if new_balance < 0.00:
                debit = abs(account.debit)
                credit = abs(account.credit + new_balance)
                new_balance = debit - credit
                name_period = 'GANANCIA DEL EJERCICIO'
            else:
                debit = abs(account.debit + new_balance)
                credit = abs(account.credit)
                new_balance = debit - credit
                name_period = 'PERDIDA DEL EJERCICIO'
#                    vals.update({'balance':new_balance, 'debit': debit, 'credit': credit})
            vals = {'code': 'RES-EJE',
                    'name': name_period,
                    'type': 'account',
                    'level': 1,
                    'account_type': False,
                    'wizard_id': ids[0],
                    'account_id': False,
                    'debit': debit,
                    'credit': credit,
                    'balance': new_balance,
                    }
            self.pool.get('accounting.financial.reports.lines').create(cr, uid, vals)

        return True

accounting_financial_reports()


class accounting_financial_reports_lines(osv.osv):

    _name = "accounting.financial.reports.lines"
    _columns = {'code': fields.char('Código', size=400),
                'name': fields.char('Cuenta', size=400),
                'level': fields.integer('Nivel'),
                'account_type': fields.char('Tipo de Cuenta', size=256),
                'type': fields.char('Tipo', size=256),
                'account_id': fields.many2one('account.account', 'Cuenta Contable'),
                'debit': fields.float('Débito', digits_compute=dp.get_precision('Account')),
                'credit': fields.float('Crédito', digits_compute=dp.get_precision('Account')),
                'balance': fields.float('Balance', digits_compute=dp.get_precision('Account')),
                'wizard_id': fields.many2one('accounting.financial.reports', 'Wizard')
                }
    _order = 'code asc'

accounting_financial_reports_lines()
