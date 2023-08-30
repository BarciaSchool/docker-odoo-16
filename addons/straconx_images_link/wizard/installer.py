# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.  
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
from osv import osv, fields
from tools.translate import _
from openerp.addons.straconx_images_link.objects.product_images import exts

def get_exts():
    exts_str=","+exts
    exts_list=exts_str.split(",*")
    i=0
    nlist=[]
    for each in exts_list:
        if(i):
            nlist.append((each,each))
        i=i+1
    return tuple(nlist)

class product_images_migrate(osv.osv_memory):
    _name = "product.images.migrate"
    _inherit = "res.config.installer"
    _columns = {
              "sufix":fields.char("Sufix", size=6),
              "migrate":fields.boolean("Migrate", help="If TRUE then the main image also will be migrated"),
              "extention":fields.selection(get_exts(), "Extention", help="The extention in which the main images will be migrated.All should be equal.")
              }
    _default = {
              "migrate":True,
              }
        
    def execute(self, cr, uid, ids, context=None):
        if(context is None):
            context = {}
        local_media_repository = self.pool.get('res.company').get_local_media_repository(cr, uid, context=context)
        if not local_media_repository:
            raise osv.except_osv(_("Validation Error!"), _("You have not set the path for saving product images"))
        obj_product_image = self.pool.get("product.images")
        srch_product_image = obj_product_image.search(cr, uid, [('file_db_store', '!=', False), ("name", "!=", False), ("extention", "!=", False)])
        if(srch_product_image):
            brwl_product_image = obj_product_image.browse(cr, uid, srch_product_image, context)
            for brw_product_image in brwl_product_image:
                vals = {"main":False, "file_db_store":False, "link":True,"name":brw_product_image.name,"extention":brw_product_image.extention,
                      "url":obj_product_image.get_url(cr, uid, brw_product_image.name, brw_product_image.extention, brw_product_image.product_id, context=context)}
                obj_product_image.overwrite(vals["url"], vals["url"], brw_product_image.file_db_store)
                if(obj_product_image.write_without_validation(cr, uid, brw_product_image.id, vals, context=context)):
                    cr.commit()
        brw_self = self.browse(cr, uid, ids[0], context)
        if(brw_self.migrate):
            self.create_main_images(cr, uid,brw_self.sufix, brw_self.extention, [], context=context)
        
    def create_main_images(self,cr,uid,sufix,extention,create_main_images,context=None):
        obj_product_product = self.pool.get("product.product")
        obj_product_image = self.pool.get("product.images")
        arguments=not create_main_images and [('product_image','!=',False)] or (len(create_main_images)>1) and [('product_image','!=',False),('id','not in',tuple(create_main_images))] or [('product_image','!=',False),('id','!=',create_main_images[0])]
        srch_product_product = obj_product_product.search(cr, uid, arguments,limit=10)
        if(srch_product_product):
            brwl_product_product = obj_product_product.browse(cr, uid, srch_product_product, context)
            for brw_product_product in brwl_product_product:
                sufix=sufix or ""
                main_vals = {
                    "product_id":brw_product_product.id,
                    "file_db_store":brw_product_product.product_image,
                    "name":brw_product_product.default_code + extention,
                    "extention":False,"main":True,"link":True,                          
                    "url":obj_product_image.get_url(cr, uid, brw_product_product.default_code + sufix, extention, brw_product_product, context=context)}
                obj_product_image.create(cr, uid, main_vals,context=context)
                if(obj_product_product.write(cr, uid, brw_product_product.id, {"product_image":False}, context=context)):
                    cr.commit()
                create_main_images.append(brw_product_product.id)
            return self.create_main_images(cr, uid,  sufix, extention, create_main_images, context=context)      
        return []
product_images_migrate()