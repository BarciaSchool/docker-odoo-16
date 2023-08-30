# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
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
from osv import osv

class bonus_move(osv.osv_memory):
    _name="bonus.move"
    _inherit = "res.config.installer"
 
    def execute(self, cr, uid, ids, context=None):        
        if(context is None):
            context={}
        cr.execute("update account_invoice_line set qty=quantity,bonus_qty=0 where (qty=0 or qty is null) and (bonus_qty=0 or bonus_qty is null) and quantity<>0")
        cr.execute("update stock_move set qty=product_qty,bonus_qty=0 where (qty=0 or qty is null) and (bonus_qty=0 or bonus_qty is null) and product_qty<>0")
        cr.execute("update sale_order_line set qty=product_uom_qty,bonus_qty=0 where (qty=0 or qty is null) and (bonus_qty=0 or bonus_qty is null) and product_uom_qty<>0")

bonus_move()