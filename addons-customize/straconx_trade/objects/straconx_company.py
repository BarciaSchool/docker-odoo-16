# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

from osv import fields, osv

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
            'property_account_duty': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Payable Account Duty',
                method=True,
                view_load=True,
                domain="[('type', '=', 'payable')]",),
            'property_account_move_duty': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Account Move Duty',
                method=True,
                view_load=True,
                domain="[('type', '=', 'stock')]",),
            'property_account_tax_duty': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Account Tax VAT Duty',
                method=True,
                view_load=True,
                domain="[('type', '=', 'other')]",),
            'property_account_duty_account': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Account Duty',
                method=True,
                view_load=True,
                domain="[('type', '=', 'stock')]",),
                #domain="[('type', '=', 'other')]",),
            'partner_id_trade': fields.many2one('res.partner','Partner'),
            'review_qty':fields.boolean('review Qty Produts', required=False, help="this field indicate if the company reviews the quantity products when receive the trade"),
            'one_step':fields.boolean('Un solo proceso', required=False, help="Si activa este campo, todos los procesos de aprobación se ejecutarán simultáneamente."),
            }
    _defaults={'review_qty':True}

res_company()
