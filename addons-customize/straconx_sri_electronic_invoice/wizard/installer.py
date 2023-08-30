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

from osv import osv,fields
from tools.translate import _
import netsvc
from datetime import datetime

class electronic_installer(osv.osv_memory):
    _name="ei.installer"
    _inherit = "res.config.installer"
    _columns={
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
            'document_email':fields.char(
                        'Correo Electrónico', 
                        size=256,
                        help='Correo desde donde se enviará los documentos validados por el SRI'
                    ),
            'only_principal_shop': fields.boolean('Solo tienda de la base', help='Si marca esta casilla, solo revisará la tienda que corresponda a la base de datos')
              }
    
    def execute(self, cr, uid, ids, context=None):
        for data in self.browse(cr, uid, ids, context=context):
            self.pool.get('res.company').write(cr, uid, [data.company_id.id] ,{'electronic_path':data.electronic_path,
                                                                               'files_path':data.files_path,
                                                                               'document_email':data.document_email,
                                                                               'only_principal_shop':data.only_principal_shop,                                                                               
                                                                               }, context=context)

electronic_installer()