#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2011-2012 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved
#
#    This program is private software.
#
##############################################################################


import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import netsvc
import pooler
from osv import fields, osv
import openerp.osv.orm 
from tools.translate import _ 


class account_chart(osv.osv_memory):
    _inherit = "account.chart"
    _columns = {'company_id': fields.many2one('res.company', 'Compañía')}

    def _get_fiscalyear(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('company_id', '=', company_id)])
        if fiscalyear_ids:
            return fiscalyear_ids and fiscalyear_ids[-1]

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear_id=False, company_id=False, context=None):
        res = {}
        if not company_id:
            raise osv.except_osv(_('Error'), _("Debe seleccionar una compañía para continuar."))

        if not fiscalyear_id:
            fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('company_id', '=', company_id)])
            if not fiscalyear_ids:
                raise osv.except_osv(_('Error'), _("No existen períodos fiscales para la compañía seleccionada."))
            else:
                fiscalyear_id = fiscalyear_ids[-1]

        if fiscalyear_id and company_id:
            start_period = end_period = False
            cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               and f.company_id =%s
                               ORDER BY p.date_start ASC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               and f.company_id =%s
                               AND p.date_start < NOW()
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (fiscalyear_id, company_id, fiscalyear_id, company_id))
            periods = [i[0] for i in cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            res['value'] = {'period_from': start_period, 'period_to': end_period, 'company_id': company_id, 'fiscalyear': fiscalyear_id}
        else:
            res['value'] = {'company_id': False, 'fiscalyear': False, 'period_from': False, 'period_to': False}
        return res

    def account_chart_open_window(self, cr, uid, ids, context=None):
        """
        Opens chart of Accounts
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of account chart’s IDs
        @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        period_obj = self.pool.get('account.period')
        fy_obj = self.pool.get('account.fiscalyear')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context=context)[0]
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_account_tree')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        fiscalyear_id = data.get('fiscalyear', False) and data['fiscalyear'][0] or False
        result['periods'] = []
        if data['period_from'] and data['period_to']:
            period_from = data.get('period_from', False) and data['period_from'][0] or False
            period_to = data.get('period_to', False) and data['period_to'][0] or False
            result['periods'] = period_obj.build_ctx_periods(cr, uid, period_from, period_to)
        result['context'] = str({'fiscalyear': fiscalyear_id, 'periods': result['periods'],
                                'state': data['target_move']})
        if fiscalyear_id:
            result['name'] += ':' + fy_obj.read(cr, uid, [fiscalyear_id], context=context)[0]['code']
        return result

    _defaults = {
        'target_move': 'posted',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.fiscalyear', context=c),
        'fiscalyear': _get_fiscalyear,
        }

account_chart()


class wizard_multi_charts_accounts(osv.osv_memory):

    _inherit = 'wizard.multi.charts.accounts'

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = {}
        tax_templ_obj = self.pool.get('account.tax.template')
        res['value'] = {'complete_tax_set': False, 'sale_tax': False, 'purchase_tax': False}
        if chart_template_id:
            data = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
            res['value'].update({'complete_tax_set': data.complete_tax_set})
            if data.complete_tax_set:
                sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id", "=", chart_template_id),
                                                              ('description', '=', '421'), ('type_tax_use', '=', ('sale'))],
                                                    order="description asc, sequence")
                purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id", "=", chart_template_id),
                                                                  ('description', '=', '520'),
                                                                  ('type_tax_use', '=', ('purchase'))],
                                                        order="description asc, sequence")
                res['value'].update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False, 'purchase_tax': purchase_tax_ids and purchase_tax_ids[0]
                                     or False})
            if data.code_digits:
                res['value'].update({'code_digits': data.code_digits})
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_multi_charts_accounts, self).default_get(cr, uid, fields, context=context)
        tax_templ_obj = self.pool.get('account.tax.template')
        res.update({'sale_tax': [], 'purchase_tax': []})
        if 'bank_accounts_id' in fields:
            res.update({'bank_accounts_id': []})
        if 'company_id' in fields:
            res.update({'company_id': self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0].company_id.id})
        if 'seq_journal' in fields:
            res.update({'seq_journal': True})

        ids = self.pool.get('account.chart.template').search(cr, uid, [('visible', '=', True)], context=context)
        if ids:
            if 'chart_template_id' in fields:
                res.update({'chart_template_id': ids[0]})
            if 'sale_tax' in fields:
                sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id", "=", ids[0]),
                                                              ('description', '=', '421'),
                                                              ('type_tax_use', '=', ('sale'))], order="sequence")
                if sale_tax_ids:
                    sale_tax_rate = tax_templ_obj.browse(cr, uid, sale_tax_ids[0]).amount
                    res.update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False, 'sale_tax_rate': sale_tax_rate})
            if 'purchase_tax' in fields:
                purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id", "=", ids[0]),
                                                                  ('description', '=', '520'),
                                                                  ('type_tax_use', '=', ('purchase'))], order="sequence")
                if purchase_tax_ids:
                    purchase_tax_rate = tax_templ_obj.browse(cr, uid, purchase_tax_ids[0]).amount
                    res.update({'purchase_tax': purchase_tax_ids and purchase_tax_ids[0] or False, 'purchase_tax_rate': purchase_tax_rate})
        return res

wizard_multi_charts_accounts()
