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
                 'level': _get_level,
                 'only_data': True,
                 'debit_credit': True,
                 'filter': 'filter_date'
                 }

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

            type_data = '%%'
            if data.only_data:
                type_data = 'MOV'

            if account_report_id.name=='Balance Sheet':
                account_sql = "(aa.code like '1%%' or aa.code like '2%%' or aa.code like '3%%')"
                date_from = "(date_trunc('year','"+data.date_from+"'::timestamp))"
            elif account_report_id.name=='Profit and Loss':
                account_sql = "(aa.code like '4%%' or aa.code like '5%%' or aa.code like '6%%')"
                date_from = "'%s'" % data.date_from
            elif account_report_id.name=='Trial Balance':
                account_sql = "(aa.code like '1%%' or aa.code like '2%%' or aa.code like '3%%' and aa.code like '4%%' or aa.code like '5%%' or aa.code like '6%%')"
                date_from = "(date_trunc('year','" + data.date_from + "'::timestamp))"
            else:
                raise osv.except_osv(_('¡Error!'),
                                     _('No existe el informe financiero definido.'))

            sql = """select
                        ledger.code,
                        ledger.name,
                        lev as level,
                        debit,
                        credit,
                        balance,
                        aa.type,
                        aa.id as account_id,
                        status
                        from
                        (
                        ((select
                        aa.level as lev,
                        aa.code,
                        aa.name,
                        sum(debit) as debit,
                        sum(credit) as credit,
                        sum(balance) as balance,
                        (case when sum(debit)!= 0 or sum(credit) != 0 then 'MOV' else 'SM' end) as status  
                        from
                        (
                        select 
                        t.id,
                        coalesce(sum(round(t.debit,2)),0) as debit,
                        coalesce(sum(round(t.credit,2)),0) as credit,
                        coalesce(sum(round(t.balance,2)),0) as balance
                        from 
                        ((select aa.id as id,
                        aa.code,
                        sum(aml.debit) as debit,
                        sum(aml.credit) as credit,
                        sum(aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        right join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        where aa.type != 'view' and aa.level in (6,7)
                        and """ + account_sql + """
                        group by aa.id, aa.code, aml.date
                        order by aa.code
                        ) 
                        UNION ALL
                        (select aa2.id as id,
                        aa2.code as code,
                        aml.debit as debit,
                        aml.credit as credit,
                        (aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        left join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        left join account_account aa2 on aa2.id = aa.parent_id				
                        where aa2.level in (5,6) and aa2.type = 'view' 
                        and """ + account_sql + """
                        )
                        UNION ALL
                        (select aa3.id as id,
                        aa3.code as code,
                        aml.debit as debit,
                        aml.credit as credit,
                        (aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        left join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        left join account_account aa2 on aa2.id = aa.parent_id				
                        left join account_account aa3 on aa3.id = aa2.parent_id				
                        where aa3.level in (4,5) and aa3.type = 'view'
                        and """ + account_sql + """
                        ) 
                        UNION ALL
                        (select aa4.id as id,
                        aa4.code as code,
                        aml.debit as debit,
                        aml.credit as credit,
                        (aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        left join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        left join account_account aa2 on aa2.id = aa.parent_id				
                        left join account_account aa3 on aa3.id = aa2.parent_id				
                        left join account_account aa4 on aa4.id = aa3.parent_id				
                        where aa4.level in (3,4) and aa4.type = 'view'
                        and """ + account_sql + """
                        )
                        UNION ALL
                        (select aa5.id as id,
                        aa5.code as code,
                        aml.debit as debit,
                        aml.credit as credit,
                        (aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        left join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        left join account_account aa2 on aa2.id = aa.parent_id				
                        left join account_account aa3 on aa3.id = aa2.parent_id				
                        left join account_account aa4 on aa4.id = aa3.parent_id				
                        left join account_account aa5 on aa5.id = aa4.parent_id				
                        where aa5.level in (2,3) and aa5.type = 'view'
                        and """ + account_sql + """
                        )
                        UNION ALL
                        (select aa6.id as id,
                        aa6.code as code,
                        aml.debit as debit,
                        aml.credit as credit,
                        (aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        left join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        left join account_account aa2 on aa2.id = aa.parent_id				
                        left join account_account aa3 on aa3.id = aa2.parent_id				
                        left join account_account aa4 on aa4.id = aa3.parent_id				
                        left join account_account aa5 on aa5.id = aa4.parent_id				
                        left join account_account aa6 on aa6.id = aa5.parent_id
                        where aa6.level in (1,2) and aa6.type = 'view'
                        and """ + account_sql + """
                        )
                        UNION ALL
                        (select aa7.id as id,
                        aa7.code as code,
                        aml.debit as debit,
                        aml.credit as credit,
                        (aml.debit - aml.credit) as balance,
                        aa.parent_id 
                        from account_account aa
                        left join account_move_line aml on aml.account_id = aa.id 
                                        and aml.state = 'valid' 
                                        and aml.active = True
                                        and date between """ + date_from + """ and %s 
                        left join account_account aa2 on aa2.id = aa.parent_id				
                        left join account_account aa3 on aa3.id = aa2.parent_id				
                        left join account_account aa4 on aa4.id = aa3.parent_id				
                        left join account_account aa5 on aa5.id = aa4.parent_id				
                        left join account_account aa6 on aa6.id = aa5.parent_id
                        left join account_account aa7 on aa7.id = aa6.parent_id
                        where aa7.level in (1) and aa7.type = 'view'
                        and """ + account_sql + """
                        )
                        )  
                        as t
                        group by t.id
                        ) as data
                        left join account_account aa on aa.id = data.id
                        group by aa.parent_id, aa.code, aa.level, aa.name
                        order by aa.code)
                        union all
                        (select 
                        t.lev,
                        '99999999999999' as code,
                        'RESULTADO DEL EJERCICIO' as name,
                        coalesce(sum(round(t.debit,2)),0) as debit,
                        coalesce(sum(round(t.credit,2)),0) as credit,
                        coalesce(sum(round(t.balance,2)),0)*(-1) as balance,
                        'MOV' as status
                        from 
                        (
                        (select 
                        1 as lev,
                        0 as id,
                        sum(aml.debit) as debit,
                        sum(aml.credit) as credit,
                        sum(aml.debit - aml.credit) as balance,
                        0 as parent_id 
                        from account_move_line aml 
                        left join account_account aa on aa.id = aml.account_id
                        where aa.type != 'view' and aa.level in (6,7)
                        and aml.state = 'valid' 
                        and aml.active = True
                        and date between """ + date_from + """ and %s 
                        and (aa.code like '4%%' or aa.code like '5%%'  or aa.code like '6%%')  
                        group by aml.date) 
                        ) as t
                        group by t.id, t.lev)) 
                        )as ledger
                        left join account_account aa on aa.code = ledger.code
                        where status like %s
                        and lev <= %s"""
#            print sql
            cr.execute(sql,(
                       data.date_to, data.date_to,
                       data.date_to, data.date_to,
                       data.date_to, data.date_to,
                       data.date_to, data.date_to,
                       type_data, data.level))
            balance_data = cr.fetchall()

            if balance_data:
                for account in balance_data:
                    vals = {'code': account[0],
                            'name': account[1],
                            'level': account[2],
                            'debit': account[3],
                            'credit': account[4],
                            'balance': account[5],
                            'account_type': account[6],
                            'wizard_id': ids[0],
                            'account_id': account[7],
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
