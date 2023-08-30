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
from tools.translate import _
import time
from xml.etree.ElementTree import Element, SubElement, tostring
import base64

class sri_contingency(osv.osv):
    
    _name = 'sri.contingency'
                
    _columns = {
                'key_data':fields.char('Clave Usada', size=37),
                'res_id': fields.integer('Resource'),
                'name': fields.selection([('invoice','Facturas'),
                                              ('credit_note','Nota de Crédito'),
                                              ('debit_note','Nota de Débito'),
                                              ('withhold','Retenciones'),
                                              ('delivery_guide','Guía de Remisión'),
                                              ],'Nombre Recurso', select=True),
                'state': fields.selection([('draft','Pendiente'),('done','Usado')], 'Estado', select=True),
                'date':fields.datetime('Fecha'),
                'number': fields.char('# Documento', size=17)
                 }
    _defaults = {'state': 'draft',
                 'res_id':False,
                 }

    
sri_contingency()
