# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A. (Lajonner A. Crespín Moran)   
#              (<http://openerp.straconx.com>). All Rights Reserved
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
from osv import osv,fields
from openerp.addons.straconx_images_link.objects.product_images import exts

class product_product(osv.osv):
    _inherit="product.product"
    
    def get_image(self, cr, uid, product_id, context=None):
        obj_product_image=self.pool.get("product.images")
        srch_product_image=obj_product_image.search(cr,uid,[('main','=',True),('product_id','=',product_id),('link','=',True),('url','!=',False)])
        if(srch_product_image):
            brw_product_image_main=obj_product_image.browse(cr,uid,srch_product_image[0],context)
            return obj_product_image.get_img(brw_product_image_main.url)
        srch_product_image=obj_product_image.search(cr,uid,[('product_id','=',product_id),('link','=',True),('url','!=',False)])        
        if(srch_product_image):
            brw_product_image_main=obj_product_image.browse(cr,uid,srch_product_image[0],context)
            return obj_product_image.get_img(brw_product_image_main.url)
        return False
        
    def _get_image(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for each in ids:
            res[each] = self.get_image(cr, uid, each, context=context)
        return res
        
    _columns={
              'product_image':fields.function(_get_image,string="Image",type="binary", filters=exts),
              }

product_product()