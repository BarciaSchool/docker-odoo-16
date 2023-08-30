# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
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

class stock_move_scrap(osv.osv_memory):
    _inherit = "stock.move.scrap"

    _columns = {
         'type_lost':fields.selection([
             ('no_stock','No Stock'),
             ('another_warehouse','Another Warehouse'),
             ('catalog','Product in catalog'),
             ('other','Other')],'Type Lost', select=True, readonly=False),
        'note': fields.text('Motive'),
    }
    
    def move_scrap(self, cr, uid, ids, context=None):
        """ To move scrapped products
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        move_ids = context['active_ids']
        for data in self.read(cr, uid, ids):
            move_obj.action_scrap(cr, uid, move_ids,
                             data['product_qty'], data['location_id'],data['note'],
#                             data['product_qty'], data['note'],data['type_lost'],
                             context=context)
        return {'type': 'ir.actions.act_window_close'}
    
stock_move_scrap()
