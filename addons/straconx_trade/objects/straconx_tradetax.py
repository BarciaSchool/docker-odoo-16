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

class product_tradetax(osv.osv):
    _name = "product.tradetax"
    _description = "Partner Product Series"
    _columns = {
        'code_id' : fields.char('Partida', size=64, select=True),
        'name': fields.char('Nombre Partida', size=64, select=True),
        'description': fields.char('Description', size=128, select=True),
        'line_ids':fields.one2many('product.tradetax.line', 'tradetax_id', 'Taxes Duties', required=False),
               }

_sql_constraints = [
         ('code_id_uniq', 'unique (code_id)','The code of the code_id must be unique')
                    ]

product_tradetax()


class product_tradetax_line(osv.osv):
    _name = "product.tradetax.line"
    _columns = {
        'duty_id':fields.many2one('tax.duty','Duty', required=False),
        'tax_percentage': fields.float('Percentage Tax %'),
        'tradetax_id':fields.many2one('product.tradetax', 'Tradetax', required=False),
        'applicability': fields.related('duty_id','applicability', type='selection', selection=[('cost_only','Cost more Expenses'),('cost_duty','Cost more Expenses more Duty')], string='applicability', readonly=True),
        }

product_tradetax_line()