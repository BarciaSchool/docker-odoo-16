# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved
#
#
##############################################################################
from osv import fields,osv
import decimal_precision as dp
import re
import time
from tools.translate import _
import netsvc

class account_tax_comprobante(osv.osv):
    _name = 'tax.code.comprobante'
    _description = 'Codigo de Comprobante'
    _columns = {
         'code': fields.integer('Codigo',size=2, required=True),        
        'name':fields.char('Descripcion', size=150, required=True, readonly=False)
    }
    
    _sql_constraints = [
        ('code_uniq', 'unique (code)',
            'The code of document type must be unique!'),
    ]
    
    _order = "code"

account_tax_comprobante()
                        
class account_tax_operacion(osv.osv):
    _name = 'tax.code.operacion'
    _description = 'Codigo de Operación'
    _columns = {
         'code': fields.integer('Codigo',size=2, required=True),        
        'name':fields.char('Descripcion', size=150, required=True, readonly=False)
    }
        
    _sql_constraints = [
        ('code_uniq', 'unique (code)',
            'The code of document type must be unique!'),
    ]
    
    _order = "code"

account_tax_operacion()

class account_tax_condicion(osv.osv):
    _name = 'tax.code.condicion'
    _description = 'Codigo de Condición'
    _columns = {
         'code': fields.integer('Codigo',size=2, required=True),        
        'name':fields.char('Descripcion', size=150, required=True, readonly=False)
    }
    
    _sql_constraints = [
        ('code_uniq', 'unique (code)',
            'The code of document type must be unique!'),
    ]
    
    _order = "code"

account_tax_condicion()

class account_tax_retencion(osv.osv):
    _name = 'tax.code.retencion.aplicada'
    _description = 'Codigo Retención Aplicada a Sujetos Suspendidos según:'
    _columns = {
         'code': fields.integer('Codigo',size=2, required=True),        
        'name':fields.char('Descripcion', size=150, required=True, readonly=False)
    }
    
    _sql_constraints = [
        ('code_uniq', 'unique (code)',
            'The code of document type must be unique!'),
    ]
    
    _order = "code"

account_tax_retencion()

