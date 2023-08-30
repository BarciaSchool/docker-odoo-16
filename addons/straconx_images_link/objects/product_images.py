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
from osv import osv,fields
import os,base64,urllib
import Image
from tools.translate import _

exts='*.bmp,*.png,*.jpg,*.jpeg,*.gif'
 
class product_images(osv.osv):
    _inherit="product.images"
    
    def get_img(self,url):
        if not os.path.isfile(url):
            return False
        image=False        
        (filename, header) = urllib.urlretrieve(url)        
        with open(filename , 'rb') as f:
            image = base64.b64encode(f.read())
        return image
    
    def get_image(self, cr, uid, ids, context=None):
        image = self.browse(cr, uid, ids, context=context)
        img=False
        if image.link:
            img=self.get_img(image.url)
        return img
    
    def _get_image(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for each in ids:
            res[each] = self.get_image(cr, uid, each, context=context)
        return res
        
    _columns={
			  'main':fields.boolean("Main",help="if the value is true then the image will be the main image."),
              'file':fields.function(_get_image,string="Image",type="binary",filters=exts),
              'file_db_store':fields.binary('Image', filters=exts),
              }
    
    def onchange_file_db_store(self,cr,uid,ids,file_db_store,filename,extention,url,link,context=None):        
        return {"extention":False}
    
    def get_url(self, cr, uid,name,extention,brw_product,context=None):
        local_media_repository = self.pool.get('res.company').get_local_media_repository(cr, uid, context=context)
        if local_media_repository:
            return os.path.join(local_media_repository,brw_product.default_code,'%s%s' % (name or '', extention or ''))
        raise osv.except_osv(_("Validation Error!"),_("You have not set the path for saving product images"))
    
    def rename(self,old_full_path,new_full_path):
        try:
            if os.path.isfile(old_full_path):
                os.rename(old_full_path,new_full_path)
                return True
            return False
        except:
            raise osv.except_osv(_("Error!"),_("Error while writing the file"))
        
    def overwrite(self,old_full_path,new_full_path,image):
        try:
            if os.path.isfile(old_full_path):
                os.remove(old_full_path)
                self._save_file(new_full_path,image)
                return True
            self._save_file(new_full_path,image)
            return False
        except:
            raise osv.except_osv(_("Error!"),_("Error while writing the file"))
        
    def create_without_validation(self,cr,uid,vals,context=None):
        return super(osv.osv,self).create(cr,uid,vals,context=context)
    
    def write_without_validation(self,cr,uid,ids,vals,context=None):
        return super(osv.osv,self).write(cr,uid,ids,vals,context=context)
        
    def create(self,cr,uid,vals,context=None):
        brw_product=self.pool.get("product.product") .browse(cr,uid,vals["product_id"],context=context)
        if vals.get('name', False) and not vals.get('extention', False): 
            vals['name'], vals['extention'] = os.path.splitext(vals['name'])
            vals["link"]=1
            vals["url"]=self.get_url(cr, uid, vals["name"], vals["extention"],brw_product, context=context)
            self.overwrite(vals["url"],vals["url"],vals["file_db_store"])            
            vals["file_db_store"]=False
            if vals["url"]:
#                 img=Image.open(vals["url"])
                size = os.path.getsize(vals["url"])
#                 if img.size and img.size[0]> 640:
#                     raise osv.except_osv(_("Error de validación!"),_("El ancho máximo de una imagen debe ser 640 px"))
#                 if img.size and img[1].size> 640:
#                     raise osv.except_osv(_("Error de validación!"),_("El alto máximo de una imagen debe ser 640 px"))
                if size > 1048576:
                    raise osv.except_osv(_("Error de validación!"),_("El tamaño máximo de la imagen debe ser 1 Mb"))
            return super(osv.osv,self).create(cr,uid,vals,context=context)
        
    def write(self,cr,uid,ids,vals,context=None):
        if(context is None):
            context={}
        if not isinstance(ids, list):
            ids = [ids]
        image=vals.get("file_db_store",False)
        extention=False
        vals["link"]=1
        if vals.get('name', False):
            vals['name'], extention = os.path.splitext(vals['name'])
        brwl_self=self.browse(cr,uid,ids,context=context)
        for brw_self in brwl_self:
            vals['extention']=extention and (extention!='') and extention or vals.get("extention",brw_self.extention) 
            vals["url"]=self.get_url(cr, uid, vals["name"], vals["extention"],brw_self.product_id, context=context)
            if vals["url"]:
                size = os.path.getsize(vals["url"])
                if size > 1048576:
                    raise osv.except_osv(_("Error de validación!"),_("El tamaño máximo de la imagen debe ser 1 Mb"))
            old_full_path=brw_self.url
            img_temp=self.get_img(old_full_path)
            if(image and image!=img_temp):                    
                self.overwrite(old_full_path, vals["url"],image)
            else:
                self.rename(old_full_path,vals["url"])
            self.write_without_validation(cr,uid,ids,vals,context=context)
        return True

product_images()