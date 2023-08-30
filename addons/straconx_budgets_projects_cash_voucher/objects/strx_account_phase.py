# -*- coding: utf-8 -*-

import datetime
import time
from osv import osv, fields
from tools.translate import _
import decimal_precision as dp


class straconx_cash_vouchers_wizard_line(osv.osv_memory):

    _inherit = 'straconx.cash.vouchers.wizard.line'
    _columns = {'wbs_phase': fields.many2one('account.analytic.phase', 'Subfase/Tarea')}

straconx_cash_vouchers_wizard_line()