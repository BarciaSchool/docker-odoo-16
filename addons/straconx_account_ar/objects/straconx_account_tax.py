# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################

import time
from osv import fields, osv
import decimal_precision as dp


class account_tax_code_template(osv.osv):
    _inherit = "account.tax.code.template"
    _columns = {'tax_type': fields.selection([('vat', 'VAT'),
                                              ('withhold', 'Withhold'),
                                              ('withhold_vat', 'Withhold Vat'),
                                              ('perception', 'Perception'),
                                              ('other', 'Other'),
                                              ('duties', 'Duties')],
                                             'Tax Type', size=32,
                                             help="Select 'VAT' for VAT tax to be used at the time of making invoice."
                                             "Select 'Withhold' for Withhold and VAT's Withhold tax to be used at the time of making invoice."
                                             "Select 'Duties' for Duties tax to be used at the time of trade international liquidation."),
                }

account_tax_code_template()


class account_tax_code(osv.osv):
    _inherit = "account.tax.code"
    _columns = {'tax_type': fields.selection([('vat', 'VAT'),
                                              ('withhold', 'Withhold'),
                                              ('withhold_vat', 'Withhold Vat'),
                                              ('perception', 'Perception'),
                                              ('other', 'Other'),
                                              ('duties', 'Duties')],
                                             'Tax Type', size=32,
                                             help="Select 'VAT' for VAT tax to be used at the time of making invoice."
                                             "Select 'Withhold' for Withhold and VAT's Withhold tax to be used at the time of making invoice."
                                             "Select 'Duties' for Duties tax to be used at the time of trade international liquidation."),
                }

account_tax_code()


class account_tax_template(osv.osv):

    _inherit = 'account.tax.template'
    _columns = {'name': fields.char('Tax Name', size=256, required=True),
                'tax_type': fields.related('tax_code_id', 'tax_type', type='selection',
                                           selection=[('vat', 'IVA'),
                                                      ('withhold', 'Retención en la Fuente'),
                                                      ('withhold_vat', 'Retención del IVA'),
                                                      ('perception', 'Perception'),
                                                      ('other', 'Otros Impuestos'),
                                                      ('duties', 'Aranceles')],
                                           string="Tipo de Impuesto",
                                           store={'account.tax.code': (lambda self, cr, uid, ids, c={}: ids, ['tax_code_id'], 5)})}

    _order = 'type_tax_use desc, description asc'

account_tax_template()


class account_tax(osv.osv):

    _inherit = 'account.tax'
    _columns = {'name': fields.char('Tax Name', size=256, required=True),
                'tax_type': fields.related('tax_code_id', 'tax_type', type='selection',
                                           selection=[('vat', 'IVA'),
                                                      ('withhold', 'Retención en la Fuente'),
                                                      ('withhold_vat', 'Retención del IVA'),
                                                      ('perception', 'Perception'),
                                                      ('other', 'Otros Impuestos'),
                                                      ('duties', 'Aranceles')],
                                           string="Tipo de Impuesto",
                                           store={'account.tax.code': (lambda self, cr, uid, ids, c={}: ids, ['tax_code_id'], 5)}),
                'amount_variable': fields.float('Monto Variable', digits_compute=dp.get_precision('Purchase Price')),
                
                }

    _order = 'type_tax_use desc, description asc'
    _defaults = {'state': 'active'}
    
    def onchange_amount_variable (self, cr, uid, ids,monto=0.00, context=None):
        res = {}
        if monto > 100 or monto <= 0:
            raise osv.except_osv(_('¡Advertencia!'), _('El porcentaje no puede ser mayor a 100 ni menor a 0.'))
        else:
            monto = float (monto) / 100
        res['amount_variable'] = monto 
        return {'value': res}
account_tax()


class res_currency_rate(osv.osv):
    _inherit = "res.currency.rate"

    _columns = {'rate_sell': fields.float('Sell Rate', digits=(12, 6), help='The rate of the currency to the currency of rate 1'),
                'rate_avg': fields.float('Average Rate', digits=(12, 6), help='The rate of the currency to the currency of rate 1'),
                }

res_currency_rate()


class account_account(osv.osv):
    _order = "code"
    _inherit = "account.account"
    _columns = {'exchange_use': fields.selection([('rate', 'rate_purchase'),
                                                  ('rate_sell', 'rate_sell'),
                                                  ('rate_fixed', 'rate_fixed'),
                                                  ('rate_avg', 'rate_avg')],
                                                 'Exchange Rate')
                }

account_account()
