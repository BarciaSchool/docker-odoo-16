# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
from tools.translate import _

class reopen_statement_wizard(osv.osv_memory):
    _name = 'reopen.statement.wizard'
    _description = 'Re-Open Statements with permission of a supervisor'
    _columns = {
                'supervisor_id':fields.many2one('res.users', 'Supervisor', required=False),
                'code':fields.char('Authorization', size=20, required=False),
                }
        
    def reopen_statement(self, cr, uid, ids, context=None):
        browse_reopen_statement_wizard_list = self.browse(cr, uid, ids, context)
        pool_res_users = self.pool.get("res.users")
        for browse_reopen_statement_wizard in browse_reopen_statement_wizard_list:
            if not browse_reopen_statement_wizard.code:
                raise osv.except_osv(_('Error!'), _("Don't exist code of Supervisor for validate, enter a code"))
            supervisor_ids=pool_res_users.search(cr, uid, [('is_supervisor', '=', True),('authorization', '=', browse_reopen_statement_wizard.code)])
            if not supervisor_ids:
                raise osv.except_osv(_('Error!'), _("Code of authorization invalid"))
            self.pool.get("account.bank.statement").button_re_open(cr, uid, context['active_ids'], context)
        return {'type': 'ir.actions.act_window_close'}
    
    def onchange_code(self, cr, uid, ids, code, context=None):
        res = {}
        if code:
            supervisor_ids = self.pool.get('res.users').search(cr, uid, [('is_supervisor', '=', True), ('authorization', '=', code)])
            res['supervisor_id'] = supervisor_ids and supervisor_ids[0] or None
        return {'value': res}
            
reopen_statement_wizard()
