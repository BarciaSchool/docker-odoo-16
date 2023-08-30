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

class account_move(osv.osv):
    _inherit = "account.move"
    
    _columns={'currency_move_id': fields.many2one('res.currency', 'Currency'),
              'type_currency': fields.selection([('fixed', 'Fixed'),
                                                 ('end', 'End of Month')],'Type of Currency')
              }
    
    _defaults = {'type_currency': 'end'}
    
account_move()

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    _columns={'amount_rated': fields.float('Amount Exchange')}              
              
    def on_change_amount_currency(self, cr, uid, ids, debit=0.00, credit=0.00, currency_id=False, company_id=False, context=None):
        result = {}
        amount_currency = 0.00
        dp = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
        cur_obj = self.pool.get('res.currency')
        company_obj = self.pool.get('res.company')
        if company_id:
            company_id = company_obj.browse(cr,uid,company_id)
            company_currency = company_id.currency_id.id
        if currency_id:
            currency_id = cur_obj.browse(cr,uid,currency_id)
        else:
            currency_id = cur_obj.browse(cr,uid,company_currency)
        if currency_id.id == company_currency:
            cd = cur_obj.browse(cr, uid, company_currency).rate
        if not cd:
            cd = 1
        if debit > 0:
            amount_currency = round(debit*cd, dp)
        elif credit > 0:
            amount_currency = round(debit*cd, dp)
        result['amount_currency'] = amount_currency
        return result

account_move_line()