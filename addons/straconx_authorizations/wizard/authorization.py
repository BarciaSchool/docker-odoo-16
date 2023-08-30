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

    _name = 'wizard.authorization'
    _columns = {'supervisor_id': fields.many2one('res.users', 'Supervisor', required=False),
                'code': fields.char('Authorization', size=20, required=False),
                }

    def button_validate(self, cr, uid, ids, context=None):
        res_obj = self.pool.get('res.users')
        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.code:
                raise osv.except_osv(_('Error!'), _("Don't exist code of Supervisor for validate, enter a code"))
            supervisor_ids = res_obj.search(cr, uid, [('is_supervisor', '=', True), ('authorization', '=', wizard.code)])
            if not supervisor_ids:
                raise osv.except_osv(_('Error!'), _("Code of authorization invalid"))
            else:
                is_supervisor = res_obj.browse(cr, uid, supervisor_ids[0]).is_supervisor
                is_manager = res_obj.browse(cr, uid, supervisor_ids[0]).is_manager
            if (is_supervisor and not is_manager):
                raise osv.except_osv(_('¡Error!'), _("Autorización debe ser realizada por OTRO Supervisor o un Superior al supervisor actual."))
            context.update({'supervisor_id': supervisor_ids[0]})
        return True

    def onchange_code(self, cr, uid, ids, code, context=None):
        res = {}
        if code:
            supervisor_ids = self.pool.get('res.users').search(cr, uid, [('is_supervisor', '=', True), ('authorization', '=', code)])
            res['supervisor_id'] = supervisor_ids and supervisor_ids[0] or None
        return {'value': res}
authorization()
