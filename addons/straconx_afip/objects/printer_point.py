# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields,osv
import method


class printer_point(osv.osv):

    def _check_number(self, cr, uid, ids):
        for printer in self.browse(cr, uid, ids):
            cadena = printer['number_sri']
            return method.check_only_number(cadena)

    _inherit = 'printer.point'
    _columns = {'number_sri': fields.char('SRI Number', size=3, help='This number is assigned by the SRI by each printer point'),
                'type_printer': fields.selection([('auto', 'Auto Impresor'),
                                                  ('pre', 'Preimpresos'),
                                                  ('electronic', 'Facturación Electrónica')],
                                                 'Type Printer', select=True,
                                                 help="defines how it will generate documents"),
                }

    _defaults = {
        'type_printer': 'pre',
    }

    _sql_constraints = [('number_printer_uniq', 'unique (number_sri,shop_id)',
                         'The number of point printer must be unique for each shop!')]

    def create(self, cr, uid, values, context=None):
        if values.has_key('number_sri'):
            number = values['number_sri']
            values['number_sri'] = method.crear_sufijo(number)
        return super(printer_point, self).create(cr, uid, values, context)

    def write(self, cr, uid, ids, values, context=None):
        if values.has_key('number_sri'):
            number = values['number_sri']
            values['number_sri'] = method.crear_sufijo(number)
        return super(printer_point, self).write(cr, uid, ids, values, context)

printer_point()