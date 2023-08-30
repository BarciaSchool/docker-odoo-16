    # -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 20011 STRACONX S.A. 
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
from osv import osv,fields

class product_product(osv.osv):
    _inherit = "product.product"

    def get_ubication_lines(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        browse_res_user=self.pool.get("res.users").browse(cr,1,uid,context)
        location_list=[]
        for browse_printer_point in browse_res_user.printer_point_ids:
            location_list.append(browse_printer_point.shop_id.warehouse_id.lot_stock_id.id)
        for browse_product_product in self.browse(cr, uid, ids,context):
            list_line=[]
            if browse_product_product.ubication_ids:
                for browse_product_ubication in browse_product_product.ubication_ids:
                    if(browse_product_ubication.ubication_id.location_id.id in location_list):
                        list_line.append(browse_product_ubication.id)
            res[browse_product_product.id]=list_line
        return res
    
    def _get_ubication_lines(self, cr, uid, ids, field_name, arg, context=None):
        return self.get_ubication_lines(cr, uid, ids, field_name, arg, context)
    
    def get_ubication_total_amount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        browse_res_user=self.pool.get("res.users").browse(cr,1,uid,context)
        location_list={}
        search_ubication=[]
        for browse_printer_point in browse_res_user.printer_point_ids:#stock.location-parent
            location_list[browse_printer_point.shop_id.warehouse_id.lot_stock_id.location_id.id]=False       
        location_list=location_list.keys()
        if(location_list):
            expression=(len(location_list)==1) and [('shop_ubication_id','=',location_list[0])] or [('shop_ubication_id','in',tuple(location_list))]
            search_ubication=self.pool.get("ubication").search(cr,uid,expression)
        for browse_product_product in self.browse(cr, uid, ids,context):
            total=0            
            if browse_product_product.ubication_ids:                
                for browse_product_ubication in browse_product_product.ubication_ids:
                    if(browse_product_ubication.ubication_id.id in search_ubication):
                        total+=browse_product_ubication.qty
            res[browse_product_product.id]=total
        return res
    
    def _get_ubication_total_amount(self, cr, uid, ids, field_name, arg, context=None):
        return self.get_ubication_total_amount(cr, uid, ids, field_name, arg, context)
    
    _columns={
              'ubication_line_ids': fields.function(_get_ubication_lines, method=True, type='one2many', obj='product.ubication', string='Product Ubication',readonly=True),
              'ubication_total_amount': fields.function(_get_ubication_total_amount, method=True, type='integer', string='Total Local'),
              }
    
product_product()


class product_category(osv.osv):

    _inherit = 'product.category'
    _columns = {
        'property_stock_transit_account_id': fields.property('account.account',
            type='many2one',
            relation='account.account',
            string="Transit Valuation Account",
            view_load=True,
            help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",),
        'property_stock_transit_account_categ': fields.property('account.account',
            type='many2one',
            relation='account.account',
            string="Transit Valuation Account",
            view_load=True,
            help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",),
    }

product_category()