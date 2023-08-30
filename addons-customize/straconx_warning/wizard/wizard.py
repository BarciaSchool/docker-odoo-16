# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools.translate import _

def get_action_warning(message='', action=None,nodestroy=False):
    context_res={'warning':message,
                 'return':action or False}
    return{
        'name':_("Warning Message"),
        'view_mode': 'form',
        'view_type': 'form',
        'res_model': 'message.warning',
        'type': 'ir.actions.act_window',
        'nodestroy': nodestroy,
        'target': 'new',
        'context': context_res
    }

class message_warning(osv.osv_memory):
    _name='message.warning'
    _columns = {
        'text': fields.text('Text'),
    }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        return {'text':context.get('warning','')}
    
    def done(self, cr, uid, ids, context):
        if context is None:
            context={}
        res={}
        if context.get('return',False):
            res= context['return']
            res['nodestroy']=False
        else:
            res= {'type': 'ir.actions.act_window_close'}
        return res
        
message_warning()
