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

class stock_fill_inventory(osv.osv_memory):
    _inherit = "stock.fill.inventory"
    _columns = {
        #'location_id': fields.many2one('stock.location', 'Location', required=True),
        'categ_id': fields.many2one('product.category', 'Category'),
        'code':fields.char('Código',size=20,required=False,help="El código base de los productos"),
        'initial':fields.char('Inicial',size=5,required=False,help="El valor inicial de la secuencia"),
        'final':fields.char('Final',size=5,required=False,help="El valor final de la secuencia"),
        'recursive': fields.boolean("Include children",help="If checked, products contained in child locations of selected location will be included as well."),
        #'set_stock_zero': fields.boolean("Set to zero",help="If checked, all product quantities will be set to zero to help ensure a real physical inventory is done"),
    }

    _defaults = {
        'recursive':True,            
                 }
    
    def __similar_to(self,initial,final,code):
        similar=""
        range_list=range(initial,final+1)
        for each in range_list:
            similar+=code+str(each)+"|"
        similar="("+similar[0:len(similar)-1]+"%)"
        return similar

    def __get_product_ids(self,cr,uid,ids,context=None):
        param=[True]
        for wizard in self.browse(cr,uid,ids):        
            initial=wizard.initial and int(wizard.initial) or False
            final=wizard.final and int(wizard.final) or False       
            list_filter=""
            if(wizard.code):
                list_filter=" and pp.default_code ilike (%s) "
                param.append(wizard.code+"%")
                similar_to=""
                if((final and initial)):
                    if(final>initial):
                        similar_to=" and upper(pp.default_code) similar to %s "
                        param.append(self.__similar_to(initial, final, wizard.code.upper()))
                    if(final==initial):
                        param[1]=wizard.code+str(initial)+"%"
                    if(initial>final):
                        raise osv.except_osv(_("Validation Error!"),_("Range initial value should not be higher at the end of the range."))
                if((final and not initial or initial==0)):
                    initial=initial and 0
                    if(final>initial):
                        similar_to=" and upper(pp.default_code) similar to %s "
                        param.append(self.__similar_to(initial, final, wizard.code.upper()))   
                if(not final and initial):
                    similar_to=" and upper(pp.default_code) not similar to %s "
                    param.append(self.__similar_to(0,initial, wizard.code.upper()))          
                list_filter=list_filter+similar_to
            if(wizard.categ_id):
                param.append(wizard.categ_id.id)
                list_filter=list_filter+" and pt.categ_id=%s"
            cr.execute("select pp.id,pp.id from product_product pp inner join product_template pt on pp.product_tmpl_id=pt.id where pp.active=%s "+list_filter+" order by pp.default_code asc",tuple(param))
            products=cr.fetchall()
        return products and (dict(products).keys()) or []

    
    
    def fill_inventory(self, cr, uid, ids, context=None):
        """ To Import stock inventory according to products available in the selected locations.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.template')
#        product_category_obj = self.pool.get('product.category')
        pd_id = self.pool.get('product.product')
        fill_inventory = self.browse(cr, uid, ids[0], context=context)
#        res = {}
        res_location = []
        inventory_id = int(context['active_ids'][0])
        if inventory_obj.browse(cr,uid,inventory_id).state <> 'draft':
            raise osv.except_osv(_('¡Error!'), _('Solo se puede rellenar inventarios en Borrador'))
        if fill_inventory.categ_id:
            context.update({'fill_categ_id': fill_inventory.categ_id.id})
        if fill_inventory.recursive:
            location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', fill_inventory.location_id.id)])
        else:
            location_ids = location_obj.search(cr, uid, [('id', '=', fill_inventory.location_id.id)])
        for location in location_ids :
            res_location.append(location)
        context.update(location=res_location,compute_child=fill_inventory.recursive)
#         product_list = product_obj.search(cr,uid,[('categ_id','=',fill_inventory.categ_id.id)])
        product_list=self.__get_product_ids(cr, uid, ids, context=context)
        product_ids =[]        
        for product_id in product_list:
            if context is None:
                context = {}            
            prod_id = pd_id.browse(cr, uid, product_id, context=context)
            prod = product_obj.browse(cr, uid, prod_id.product_tmpl_id.id, context=context)
            default_code = prod_id.default_code 
            categ_id=prod.categ_id.id
            uom = prod.uom_id.id
            context.update(uom=uom)
            location_ids = fill_inventory.location_id.id
            ubication_list = self.pool.get('product.ubication').search(cr,uid,[('location_ubication_id','=',location_ids),('product_id','=',prod_id.id)])
            ubication_ids = self.pool.get('product.ubication').browse(cr,uid,ubication_list,context)    
            if ubication_ids:                    
                for ubication in ubication_ids:
                    inventory_line = {
                        'inventory_id': context['active_ids'][0],
                        'ubication_id':ubication.ubication_id.id,
                        'location_id': location,
                        'default_code': default_code,
                        'product_id': product_id,
                        'categ_id' : categ_id,
                        'product_uom': uom,
                        'product_qty': 0
                    }
                    inventory_line_obj.create(cr, uid, inventory_line)
                    product_ids.append(product_id)
        if(len(product_ids) == 0):
            raise osv.except_osv(_('Message !'), _('No product in this location.'))
        else:        
            inventory_obj.write(cr,uid,inventory_id,{'categ_id':fill_inventory.categ_id.id})
        return {'type': 'ir.actions.act_window_close'}
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        if 'value' not in context.keys():
            for obj in objs:
                if obj.categ_id:
                    res['categ_id']=obj.categ_id.id
                if obj.location_id:
                    res['location_id'] = obj.location_id.id
        else:
            res = context['value']
        return res

    def onchange_code(self,cr,uid,ids,code,initial,final,context=None):
        if(not code):
            return {"value":{"initial":None,"final":None}}
        return {}
        
    def onchange_final(self,cr,uids,ids,initial,final,context=None):
        if(final):
            str_final=""
            for each in final:
                if(each in ('0','1','2','3','4','5','6','7','8','9')):
                    str_final+=each
            return {'value':{'final':str_final}}
        return {}
    
    def onchange_initial(self,cr,uids,ids,initial,final,context=None):
        if(initial):
            str_initial=""
            for each in initial:
                if(each in ('0','1','2','3','4','5','6','7','8','9')):
                    str_initial+=each
            return {'value':{'initial':str_initial}}
        return {}


stock_fill_inventory()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
