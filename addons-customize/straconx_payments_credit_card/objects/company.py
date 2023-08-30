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
            'property_tax_withhold_credit_card': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de Retención en la Fuente',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'withhold'),('type_tax_use','=','sale')]",),
            'property_tax_withhold_vat_credit_card': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de Retención de IVA',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'withhold_vat'),('type_tax_use','=','sale')]",),
            'property_tax_vat_credit_card': fields.property( 
                'account.tax',
                type='many2one',
                relation='account.tax',
                string='Impuesto de IVA',
                method=True,
                view_load=True,
                domain="[('tax_type', '=', 'vat'),('type_tax_use','=','purchase')]",),  
            'property_account_active_credit_card': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Cuenta por Cobrar a T/C',
                method=True,
                view_load=True,
                domain="[('type', '=', 'receivable')]",),                              
                }
res_company()