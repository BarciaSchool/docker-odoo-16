# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from tools.translate import _
from osv import fields, osv
import time

class authorization_refund(osv.osv_memory):
    
    _name = 'authorization.refund'
    _columns = {
                'supervisor_id':fields.many2one('res.users', 'Supervisor', required=False),
                'code':fields.char('Authorization', size=20, required=False),
               }
    
    def button_validate(self, cr, uid, ids, context=None):
        res_obj = self.pool.get('res.users')
        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.code:
                raise osv.except_osv(_('Error!'), _("Don't exist code of Supervisor for validate, enter a code"))
            supervisor_ids=res_obj.search(cr, uid, [('is_supervisor', '=', True),('authorization', '=', wizard.code)])
            if not supervisor_ids:
                raise osv.except_osv(_('Error!'), _("Code of authorization invalid"))
            self.pool.get(context['active_model']).write(cr, uid, context['active_id'],{'required_auth':False,'user_authorized':supervisor_ids[0]},context)
        return {'type': 'ir.actions.act_window_close'}
    
    def onchange_code(self, cr, uid, ids, code, context=None):
        res = {}
        if code:
            supervisor_ids=self.pool.get('res.users').search(cr, uid, [('is_supervisor', '=', True),('authorization', '=', code)])
            res['supervisor_id']=supervisor_ids and supervisor_ids[0] or None
        return {'value': res}
authorization_refund()
