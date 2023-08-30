# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved     
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

class shop_id_data(osv.osv):
    _inherit = 'sale.shop'
    
    def _check_utility_margin(self,cr,uid,ids):
        b=True
        for shop in self.browse(cr, uid, ids):
            if (shop['min_utility_margen'] <= 0):
                b=False
        return b
    
    _columns = {
                'point_of_sale': fields.boolean('Is Point of Sale'),
                'wholesale': fields.boolean('Is Wholesale Store'),
                'headquarter': fields.boolean('Is Headquarter'),                                     
                'consignment': fields.boolean('Is Consignment'),
                'central_warehouse': fields.boolean('Is Central Warehouse'),
                'min_utility_margen': fields.float('% Minimum Utility Margen', digits=(16,2)),
                'limits_line_invoice': fields.integer('Limits line invoice'),
                'shop_ubication_id': fields.many2one('stock.location','Shop location')                                                  
            }
    
    _defaults = {
         'limits_line_invoice': lambda *a: 1,
         'min_utility_margen':lambda *a: 1,
    }
    _order = 'name asc'
    
    _constraints = [(_check_utility_margin,'The percentage utility margin must be a positive number',['min_utility_margen'])]

shop_id_data()
