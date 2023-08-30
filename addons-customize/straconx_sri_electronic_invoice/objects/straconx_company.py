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

import itertools

from osv import fields,osv
from osv.orm import except_orm
import tools
from tools.translate import _
# import nodes

class ir_company(osv.osv):
    _inherit = 'res.company'
    _columns = {    
            'electronic_path':fields.char(
                        'Ubicación del programa de Facturación Electrónica', 
                        size=256,
                        help='Ubicación del programa de Facturación Electrónica'
                    ),
            'files_path':fields.char(
                        'Ubicación de los archivos de Facturación Electrónica', 
                        size=256,
                        help='Ubicación de los archivos de Facturación Electrónica'
                    ),
            'sri_url':fields.char(
                        'Servidor de Autorización', 
                        size=256,
                        help='El servidor de autorización de documentos electrónicos'
                    ),

            'document_email':fields.char(
                        'Correo Electrónico', 
                        size=256,
                        help='Correo desde donde se enviará los documentos validados por el SRI'
                    ),
            'image_email':fields.char(
                        'Imagen', 
                        size=256,
                        help='Ubicación de la Imagen de la cabecera del correo de los documentos electrónicos'
                    ),
            'color_head':fields.char(
                        'Color Encabezado', 
                        size=256,
                        help='Color del Encabezado del correo electrónico'
                    ),
            'only_principal_shop': fields.boolean('Solo tienda de la base', help='Si marca esta casilla, solo revisará la tienda que corresponda a la base de datos')
            }
ir_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

