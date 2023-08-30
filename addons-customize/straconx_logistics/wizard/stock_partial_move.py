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

from osv import fields, osv
from tools.translate import _
import time
import decimal_precision as dp

class stock_partial_move_memory_out(osv.osv_memory):
    _inherit = "stock.move.memory.out"
    _columns = {
        'cost' : fields.float("Cost", help="Unit Cost for this product line", digits_compute= dp.get_precision('Account')),
    }

stock_partial_move_memory_out()

class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"

    def _hide_tracking(self, cursor, user, ids, name, arg, context=None):
        res = {}
#        ids =  [ids[-1]]
#        for wizard in self.browse(cursor, user, ids, context=context):
#            res[wizard.id] = any([not(x.tracking) for x in wizard.move_ids])
        res[ids[-1]] = True
        return res
stock_partial_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

