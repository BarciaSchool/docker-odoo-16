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

from osv import fields,osv

class tax_duty(osv.osv):
    _name = "tax.duty"
    _columns = {
        'code' : fields.char('Code', size=32, select=True),
        'name': fields.char('Description', size=64, select=True),
        'debit_account_id':fields.many2one('account.account', 'Debit Account', required=False),
        'credit_account_id':fields.many2one('account.account', 'Credit Account', required=False),
        'applicability':fields.selection([('cost_only','Cost more Expenses'),('cost_duty','Cost more Expenses more Duty'),], 'Applicability'),
        }
    
    _defaults={
        "applicability": lambda *a: "cost_only",
    }

    _sql_constraints = [
         ('code_id_uniq', 'unique (code)','The code of Duty must be unique')]

tax_duty()