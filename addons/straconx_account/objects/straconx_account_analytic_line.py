# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#
##############################################################################


from osv import fields
from osv import osv
from tools.translate import _

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'
    _columns = {
        'state': fields.selection([('valid','Válido'), ('cancel','Anulado')], 'State', readonly=True),
        }

    _defaults = {
        'state': 'valid',
    }

account_analytic_line()

class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"

    _order = "code,name"
account_analytic_account()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
