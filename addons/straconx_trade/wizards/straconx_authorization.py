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

from tools.translate import _
from osv import fields, osv
import time

class authorization(osv.osv_memory):
    
    _inherit = 'wizard.authorization'
    
    def button_validate(self, cr, uid, ids, context=None):
        res = super(authorization,self).button_validate(cr,uid,ids,context)
        if res:
            if context.get('active_model',None) == 'stock.picking' and context.get('active_id',False):
                picking__obj = self.pool.get('stock.picking')
                pick_id = context.get('active_id',False)
                pick_auth = picking__obj.validate_authorized(cr,uid,[pick_id],context)
                if pick_auth:
                    return {'type': 'ir.actions.act_window_close'}
                else:
                    raise osv.except_osv(_('¡Acción Inválida!'), _('No tiene permisos para autorizar este picking'))
            else:
                return {'type': 'ir.actions.act_window_close'}

authorization()
