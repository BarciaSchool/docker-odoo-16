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

from osv import fields, osv

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'property_reserve_and_surplus_account_profit': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Reserve and Profit/Loss Account for Profit/Loss Balance",
            view_load=True,
            domain="[('type', '=', 'other')]",
            help="This account is used for transferring Profit/Loss (If It is Profit: Amount will be added, Loss : Amount will be deducted.), as calculated in Profit & Loss Report"),
    }
res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
