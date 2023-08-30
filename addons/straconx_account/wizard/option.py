# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv
from tools.translate import _

def get_action_option(message='', action=None,nodestroy=False,context=None):
    context_res={'warning':message,
                 'return':action or False,
                 'object':context.get('object',False),
                 'yes':context.get("yes",False),
                 'no':context.get("no",False),
                 'args_yes':context.get("args_yes",False),
                 'args_no':context.get("args_no",False),
                 }
    return{
        'name':_("Option Message"),
        'view_mode': 'form',
        'view_type': 'form',
        'res_model': 'message.option',
        'type': 'ir.actions.act_window',
        'nodestroy': nodestroy,
        'target': 'new',
        'context': context_res
    }

class message_option(osv.osv_memory):
    _name="message.option"
    _inherit='message.warning'
            
    def yes(self, cr, uid, ids, context):
        if(context is None):
            context={}
        method=context.get("yes",False)
        if(method):
            getattr(self.pool.get(context['object']), method)(cr,uid,context.get("args_yes",False))
        return self.done(cr, uid, ids, context)
    
    def no(self, cr, uid, ids, context):
        if(context is None):
            context={}
        method=context.get("no",False)
        if(method):
            getattr(self.pool.get(context['object']), method)(cr,uid,context.get("args_no",False))
        return {'type': 'ir.actions.act_window_close'}
    
message_option()