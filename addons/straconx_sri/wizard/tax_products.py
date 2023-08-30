# -*- encoding: utf-8 -*-
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

class multi_tax_accounts_products(osv.osv_memory):
    _name='account.multi.charts.tax'
    
    _columns = {
        'sale_taxes_ids':fields.many2many('account.tax', 'rel_sale_tax_wizard', 'wizard_id', 'tax_id', 'Sales Taxes', domain=[('parent_id','=',False),('type_tax_use','in',['sale','all'])]),
        'purchase_taxes_ids':fields.many2many('account.tax', 'rel_purchase_tax_wizard', 'wizard_id', 'tax_id', 'Purchase Taxes', domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])]),
        'company_id': fields.many2one('res.company', 'Company', required=False),
        'type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('admin_service','Servicio Administrativo'),('service','Service'),('catalog','Catálogo')], 'Product Type', required=True),
    }
    
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.multi.charts.tax', context=c),
    }   
         
    def execute(self, cr, uid, ids, context=None):
        obj_multi = self.browse(cr, uid, ids[0])
        ir_values = self.pool.get('ir.values')
        sale_tax_list=[]
        purchase_tax_list=[]
#        cr.execute("""DELETE FROM rel_sale_tax_wizard """)
#        cr.execute("""DELETE FROM rel_purchase_tax_wizard """)
        if not obj_multi.type:
            raise osv.except_osv(_('¡Campo requerido!'), _(("Necesita definir que tipo de producto va a cambiar los impuestos.")))
        else:
            type_product = obj_multi.type
        if obj_multi.sale_taxes_ids:
            cr.execute("""DELETE FROM product_taxes_rel ptr 
                        USING product_product pp, product_template pt 
                        WHERE ptr.prod_id = pt.id AND 
                        pp.product_tmpl_id=pt.id AND 
                        pt.type = %s""",(type_product,))
        if obj_multi.purchase_taxes_ids:
            cr.execute("""DELETE FROM product_supplier_taxes_rel ptr 
                        USING product_product pp, product_template pt 
                        WHERE ptr.prod_id = pt.id AND 
                        pp.product_tmpl_id=pt.id AND 
                        pt.type = %s""",(type_product,))
        for sale_tax in obj_multi.sale_taxes_ids:
            sql="""INSERT INTO product_taxes_rel (tax_id, prod_id) 
                SELECT %s,pt.id FROM product_product pp INNER JOIN 
                product_template pt on pp.product_tmpl_id = pt.id
                WHERE pt.type=%s"""
            cr.execute(sql,(sale_tax.id,type_product))
            sale_tax_list.append(sale_tax.id)
        for purchase_tax in obj_multi.purchase_taxes_ids:
            sql="""INSERT INTO product_supplier_taxes_rel (tax_id, prod_id) 
                SELECT %s,pt.id FROM product_product pp INNER JOIN 
                product_template pt on pp.product_tmpl_id = pt.id
                WHERE pt.type=%s"""
            cr.execute(sql,(purchase_tax.id,type_product))
            purchase_tax_list.append(purchase_tax.id)
        if sale_tax_list:
            ir_values.set(cr, uid, key='default', key2=False, name="taxes_id", company=obj_multi.company_id.id,
                            models =[('product.product',False)], value=sale_tax_list)
        if purchase_tax_list:
            ir_values.set(cr, uid, key='default', key2=False, name="supplier_taxes_id", company=obj_multi.company_id.id,
                            models =[('product.product',False)], value=purchase_tax_list)
        return {'type': 'ir.actions.act_window_close'}
        
multi_tax_accounts_products()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
