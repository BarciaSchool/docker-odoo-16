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
from datetime import datetime
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
from osv import osv, fields
from tools.translate import _


class account_report_ledger_statement(osv.osv):
    _name = 'account.ledger.statement'
    _description = 'Ledger Account'

    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        return company or False

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
        period = self.pool.get('account.period').search(cr, uid, [('date_start', '<', last_month),
                                                                  ('date_stop', '>', last_month), ('company_id', '=', company_id)])
        return period and period[0] or False

    def _get_fiscalyear(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<=', time.strftime('%Y-%m-%d')),
                                                                              ('date_stop', '>=', time.strftime('%Y-%m-%d')),
                                                                              ('company_id', '=', user.company_id.id), ('state', '=', 'draft')])
        return fiscalyear_ids[0]

    def search_lines(self, cr, uid, ids, context):
        cr.execute("""delete from account_ledger_statement_lines WHERE WIZARD_ID = %s""", (ids[0], ))
        account_obj = self.pool.get('account.account')
        move_line_obj = self.pool.get('account.move.line')
        account = self.browse(cr, uid, ids[0]).account_list
        move_state = self.browse(cr, uid, ids[0]).move_state
        company_id = self.browse(cr, uid, ids[0]).company_id.id
        partner_id = self.browse(cr, uid, ids[0]).partner_id.id
        date_from = self.browse(cr, uid, ids[0]).date_from
        date_to = self.browse(cr, uid, ids[0]).date_to
        fiscalyear = self.browse(cr, uid, ids[0]).fiscalyear.code
        shop_id = self.browse(cr, uid, ids[0]).shop_id.id
        department_id = self.browse(cr, uid, ids[0]).department_id.id
        analytic_account_id = self.browse(cr, uid, ids[0]).analytic_account_id
#         if date_from[:4] != fiscalyear or date_to[:4] != fiscalyear:
#             raise osv.except_osv(_('¡Aviso!'), _('Las fechas ingresadas no se encuentran dentro del período fiscal %s') % (fiscalyear))
        if date_from > date_to:
            raise osv.except_osv(_('¡Error!'), _('La fecha final %s debe ser mayor a la fecha inicial %s') % (date_to, date_from))

        account_init = """SELECT sum(AML.DEBIT- AML.CREDIT) FROM ACCOUNT_MOVE_LINE AML
        LEFT JOIN ACCOUNT_ACCOUNT AA ON AA.ID = AML.ACCOUNT_ID
        LEFT JOIN ACCOUNT_MOVE AM ON AM.ID = AML.MOVE_ID
        LEFT JOIN RES_PARTNER RP ON RP.ID = AML.PARTNER_ID
        LEFT JOIN RES_COMPANY RC ON RC.ID = AM.COMPANY_ID"""

        account_sql = """SELECT AML.ID FROM ACCOUNT_MOVE_LINE AML
        LEFT JOIN ACCOUNT_ACCOUNT AA ON AA.ID = AML.ACCOUNT_ID
        LEFT JOIN ACCOUNT_MOVE AM ON AM.ID = AML.MOVE_ID
        LEFT JOIN RES_PARTNER RP ON RP.ID = AML.PARTNER_ID
        LEFT JOIN RES_COMPANY RC ON RC.ID = AM.COMPANY_ID"""

        if company_id:
            account_sql = account_sql + " WHERE AM.COMPANY_ID = %s " % company_id
            account_init = account_init + " WHERE AM.COMPANY_ID = %s " % company_id
        if partner_id:
            account_sql = account_sql + " AND AML.PARTNER_ID = %s " % partner_id
            account_init = account_init + " AND AML.PARTNER_ID = %s " % partner_id
        if shop_id:
            account_sql = account_sql + " AND AML.SHOP_ID = %s " % shop_id
            account_init = account_init + " AND AML.SHOP_ID = %s " % shop_id
        if department_id:
            account_sql = account_sql + " AND AML.DEPARTMENT_ID = %s " % department_id
            account_init = account_init + " AND AML.DEPARTMENT_ID = %s " % department_id
        if move_state == 'both':
            account_sql = account_sql + " AND am.state in ('draft','posted') "
            account_init = account_init + " AND am.state in ('draft','posted') "
        elif move_state == 'posted':
            account_sql = account_sql + " AND am.state ='posted' "
            account_init = account_init + " AND am.state ='posted' "
        else:
            account_sql = account_sql + " AND am.state = 'draft' "
            account_init = account_init + " AND am.state = 'draft' "
        if analytic_account_id:
            account_sql = account_sql + " AND aml.analytic_account_id = %s" % (analytic_account_id.id)
            account_init = account_init + " AND aml.analytic_account_id = %s" % (analytic_account_id.id)

        group_by = " group by aml.date, aml.id order by aml.date"

        if account:
            type_account = account_obj.browse(cr, uid, account.id).type
            account_ids = []
            if type_account == 'view':
                codes_account = account_obj.browse(cr, uid, account.id).code + "%"
                new_sql = "select id from account_account where code like '%s' and type <> 'view'" % (codes_account)
                cr.execute(new_sql)
                search_account = cr.fetchall()
                if search_account:
                    for a in search_account:
                        account_ids.append(a[0])
                    if len(account_ids) > 1:
                        account_sql = account_sql + " AND aml.account_id in " + str(tuple(account_ids))
                        account_init = account_init + " AND aml.account_id in " + str(tuple(account_ids))
                    else:
                        account_sql = account_sql + " AND aml.account_id = " + str(account_ids[0])
                        account_init = account_init + " AND aml.account_id = " + str(account_ids[0])
                else:
                    raise osv.except_osv(_('¡Aviso!'), _('La cuenta %s - %s no tiene subcuentas') % (account.code, account.name))
            else:
                account_sql = account_sql + " AND aml.account_id =%s" % account.id
                account_init = account_init + " AND aml.account_id =%s" % account.id

        if date_from and date_to:
            if date_from[:4] != date_to[:4]:
                account_init = account_init + "AND aml.journal_id not in (select id from account_journal where type = 'situation') "
                account_sql = account_sql + "AND aml.journal_id not in (select id from account_journal where type = 'situation') "
            init_date = date_from[:4] + '-01-01'
            if str(date_from) != init_date:
                date_end = datetime.strptime(date_from, '%Y-%m-%d') + relativedelta(days=-1)
            else:
                date_end = init_date
            account_initial = account_init + " AND aml.date between date(date_trunc('year', '%s'::date)) and '%s'" % (date_end, date_end)
            account_sql = account_sql + " AND AML.date BETWEEN '%s' AND '%s'" % (date_from, date_to) + group_by

        cr.execute(account_initial)
        initial_amount = cr.fetchone()
        if initial_amount == (None,) or not initial_amount:
            initial_amount = 0.00
        else:
            initial_amount = initial_amount[0]

        self.write(cr, uid, ids, {'initial_amount': initial_amount})
        cr.execute(account_sql)
        lines = cr.fetchall()
        sum_credit = 0.00
        sum_debit = 0.00
        if date_from == init_date:
            total_line = 0.00
        else:
            total_line = initial_amount
        date_c = time.strftime('%Y-%m-%d %H:%M:%S')
        if lines:
            for l in lines:
                line_id = move_line_obj.browse(cr, uid, l[0])
                move_id = line_id.move_id.id
                move_line_id = line_id.id
                date = line_id.date
                account_id = line_id.account_id.id
                reference = ''
                if line_id.reference == line_id.ref and line_id.reference != line_id.name:
                    if not line_id.move_id.ref:
                        move_ref = ''
                    else:
                        move_ref = line_id.move_id.ref
                    if line_id.reference:
                        reference = line_id.name + ' ' + line_id.reference + ' | ' + move_ref
                    else:
                        reference = line_id.name +  ' | ' + move_ref
                elif line_id.reference == 'False':
                    reference = line_id.name + ' ' + line_id.ref
                elif line_id.reference == line_id.ref and line_id.reference == line_id.name:
                    reference = line_id.name
                elif line_id.reference == line_id.name:
                    reference = line_id.name
                else:
                    reference = line_id.name
                debit = line_id.debit
                credit = line_id.credit
                sum_debit += line_id.debit
                sum_credit += line_id.credit
                total_line = (total_line + debit - credit)
                if line_id.partner_id.id:
                    verified_partner_id = self.pool.get('res.partner').browse(cr, uid, line_id.partner_id.id)
                    if not verified_partner_id:
                        raise osv.except_osv(_('¡Aviso!'),
                                             _('La información de la Empresa %s no se ecuentra, por favor, '
                                               'solicitar su migración al área de sistemas') % (line_id.partner_id.id,))
                    else:
                        partner_id = verified_partner_id.id
                cr.execute("""INSERT INTO account_ledger_statement_lines (create_uid, create_date,move_id, date, account_id, reference, debit, credit, total_debit, total_credit, subtotal_line, wizard_id, move_line_id, partner_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (uid, date_c, move_id, date, account_id, reference, debit, credit, sum_debit, sum_credit, total_line,ids[0], move_line_id, partner_id))

        final_amount = total_line or 0.00
        self.write(cr, uid, ids, {'final_amount': final_amount})
        return True

    def _get_sortby(self, data):
        if self.sortby == 'sort_date':
            return _('Date')
        elif self.sortby == 'sort_journal_partner':
            return _('Journal & Partner')
        return _('Date')
    _rec_name = 'account_list'

    _columns = {'company_id': fields.many2one('res.company', 'Company', required=True, change_default=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'department_id': fields.many2one('hr.department', 'Departamento'),
                'partner_id': fields.many2one('res.partner', 'Empresa'),
                'state': fields.selection([('bydate', 'By Date')], 'Select', select=True),
                'sortbydate': fields.selection([('sort_date', 'Date')], 'Sort by'),
                'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
                'display_account': fields.selection([('bal_mouvement', 'With movements'), ('bal_all', 'All'),
                                                     ('bal_solde', 'With balance is not equal to 0')], "Display accounts"),
                'initial_balance': fields.boolean('Show initial balances'),
                'amount_currency': fields.boolean('With Currency'),
                'period_from': fields.many2one('account.period', 'Start period'),
                'period_to': fields.many2one('account.period', 'End period'),
                'date_from': fields.date('Start date'),
                'date_to': fields.date('End date'),
                'account_list': fields.many2one('account.account', 'Account', required=True),
                'move_state': fields.selection([('draft', 'Draft'), ('posted', 'Posted'), ('both', 'Both')], 'Sort by'),
                'analytic_account_id': fields.many2one('account.analytic.account', 'Cost Center'),
                'initial_amount': fields.float('Saldo Inicial', digits_compute=dp.get_precision('Account')),
                'final_amount': fields.float('Saldo Final', digits_compute=dp.get_precision('Account')),
                'move_lines': fields.one2many('account.ledger.statement.lines', 'wizard_id', 'Movimientos')}

    _defaults = {'fiscalyear': _get_fiscalyear,
                 'company_id': _get_company_id,
                 'period_from': _get_period_from,
                 'period_to': _get_period_to,
                 'sortbydate': 'sort_date',
                 'state': 'bydate',
                 'initial_balance': True,
                 'display_account': 'bal_mouvement',
                 'move_state': 'posted'}

account_report_ledger_statement()


class account_report_ledger_statement_lines(osv.osv):

    _name = 'account.ledger.statement.lines'
    _order = "date asc"

    _columns = {'date': fields.date('Fecha'),
                'move_id': fields.many2one('account.move', 'Movimiento'),
                'move_line_id': fields.many2one('account.move.line', 'Línea del Movimiento'),
                'account_id': fields.many2one('account.account', 'Cuentas'),
                'partner_id': fields.many2one('res.partner', 'Empresa'),
                'reference': fields.char('Referencia', size=500),
                'debit': fields.float('Débito', digits_compute=dp.get_precision('Account')),
                'credit': fields.float('Crédito', digits_compute=dp.get_precision('Account')),
                'total_debit': fields.float('Total Débito', digits_compute=dp.get_precision('Account')),
                'total_credit': fields.float('Total Crédito', digits_compute=dp.get_precision('Account')),
                'subtotal_line': fields.float('Acumulado', digits_compute=dp.get_precision('Account')),
                'wizard_id': fields.many2one('account.ledger.statement', 'Asistente')}

account_report_ledger_statement_lines()
