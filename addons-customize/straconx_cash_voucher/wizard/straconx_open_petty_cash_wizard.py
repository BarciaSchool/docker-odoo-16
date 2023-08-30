# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-2013 STRACONX S.A 
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

from osv import osv
from tools.translate import _

class open_statement(osv.osv_memory):
    _inherit = 'open.statement'

    def open_statement(self, cr, uid, ids, context=None):
        result=super(open_statement, self).open_statement(cr, uid, ids, context)
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        if context.get('journal_type','moves') == 'pcash':
            tree_res = mod_obj.get_object_reference(cr, uid, 'straconx_cash_voucher', 'straconx_petty_cash_tree')
            tree_id = tree_res and tree_res[1] or False
            form_res = mod_obj.get_object_reference(cr, uid, 'straconx_cash_voucher', 'straconx_petty_cash_form')
            form_id = form_res and form_res[1] or False
            search_id = mod_obj.get_object_reference(cr, uid, 'straconx_cash_voucher', 'straconx_petty_cash_filter')
            result['search_view_id']=search_id and search_id[1] or False
            result['views']=[(tree_id, 'tree'), (form_id, 'form')]
            result['domain']="[('user_id', '=', "+ str(uid) +"),('journal_id.type', '=','pcash')]"
        return result
        
open_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
