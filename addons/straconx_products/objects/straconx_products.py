# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
##############################################################################


import time
from osv import fields, osv,expression 
from tools.translate import _
import netsvc
import decimal_precision as dp
from operator import itemgetter
from itertools import groupby
import tools
import logging
from openerp import SUPERUSER_ID


class product_color(osv.osv):
    _name = "product.color"
    _columns = {
        'name': fields.char('Color', size=64, required=True),
    }
product_color()

# Product clasifications
class clasification(osv.osv):
    _name = 'product.clasification'
    _description = "Product clasification"
    _columns = {
        'name': fields.char('Clasification',size=64, required=True, help='Name of the clasification'),
        'code': fields.char('Code', size=6,),
        'parent_id': fields.many2one('product.clasification','Parent Clasification', help='Name of the parent clasification'),
#        'active': fields.boolean('Active'),
    }

#_defaults = {'active': lambda *a: 1}
    _sql_constraints = [
        ('code_uniq', 'unique (name)','The code of the clasification must be unique !')
    ]
clasification()

# Product Template modifications
class product_template(osv.osv):
       
    def _calculate_factor(self, cr, uid, ids, field_name, arg, context=None):
        factor = 0
        res = {}
        for product in self.browse(cr, uid, ids, context):
            if product.fob >0 and product.standard_price>0:
                if product.fob <= product.standard_price:
                    factor = product.standard_price/product.fob
                else:
                    factor = 0
            res[product.id] = factor
        return res

    
    _inherit = "product.template"
    _columns = {
        'name': fields.char('Name', size=256, required=True, select=True),
        'type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('admin_service','Servicio Administrativo'),('service','Service'),('catalog','Catálogo')], 'Product Type', required=True, help="Will change the way procurements are processed. Consumables are stockable products with infinite stock, or for use when you have no stock management in the system."),
        'codant':fields.char('Former Code', size=256, select=True, readonly=True),
        'fob': fields.float('FOB',digits_compute=dp.get_precision('Purchase Price')),
        'categ_id': fields.many2one('product.category','Category', required=True, change_default=True, domain="[('type','!=','view')]" ,help="Select category for the current product"),
        'factor': fields.function(_calculate_factor, method=True, string='Factor', store=True, digits_compute=dp.get_precision('Purchase Price')),
        }
         
    _sql_constraints = [('costo_negativo', 'check(standard_price > 0)','El costo debe ser mayor a 0!')]        
            
    _defaults = {
        'type': lambda *a: 'product',
        'cost_method': lambda *a: 'average',
        'supply_method': lambda *a: 'buy',
        'sale_ok': lambda *a: 1,
        'sale_delay': lambda *a: 15,
        'purchase_ok': lambda *a: 1,
        'procure_method': lambda *a: 'make_to_stock',
    }

product_template()


# Product Material
class material(osv.osv):
    _name = 'product.material'
    _description = 'Product Material'
    _columns = {
        'code': fields.char('Code', size=10, select=False),
        'name': fields.char('Name', required=True, size=30, translate=True),
        'description': fields.char('Description', required=False, size=60),
    }
    _order = 'name'
material()

class res_manufacturer(osv.osv):
    _name = "res.manufacturer"
    _columns = {
        'name': fields.char('Manufacturer', size=256),
        'manufacturer_country': fields.many2one('res.country', string='Country', traslate="True"),
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='cascade'),        
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)','The name of the manufacturer must be unique !')
    ]
res_manufacturer()


class product_product(osv.osv):
    _inherit = 'product.product'
    _name = 'product.product'

    def name_get(self, cr, user, ids, context={}):
        if not len(ids):
            return []

        def _name_get(d):
            #name = self._product_partner_ref(cr, user, [d['id']], '', '', context)[d['id']]
            #code = self._product_code(cr, user, [d['id']], '', '', context)[d['id']]
            name = d.get('name', '')
#            ean = d.get('ean13', False)
            code = d.get('default_code', False)
#            if ean:
#                name = '[%s] %s' % (ean, name)
            if code:
                name = '%s - %s' % (code, name)
            return (d['id'], name)

#        return map(_name_get, self.read(cr, user, ids, ['name', 'ean13'], context))
        return map(_name_get, self.read(cr, user, ids, ['name', 'default_code'], context))

    def name_search(self, cr, user, name, args=[], operator='ilike', context={}, limit=80):
        ids = self.search(cr, user, [('default_code', '=', name)]+ args, limit=limit)
        if not len(ids):
            ids = self.search(cr, user, [('ean13', '=', name)]+ args, limit=limit)
        if not len(ids):
            categ=context.get('categ_id',False)
            if categ:
                args.append(('categ_id', '=', categ))
            ids = self.search(cr, user, [('default_code', operator, name)]+ args, limit=limit)
            ids += self.search(cr, user, [('name', operator, name)]+ args, limit=limit)
        return self.name_get(cr, user, ids, context)
    
    def _verified_price(self, cr, uid, ids, context=None):
        b = True
        for product in self.browse(cr, uid, ids, context):
            if product.list_price >0 and product.standard_price>0:
                if product.list_price < product.standard_price:
                    raise osv.except_osv(_('Error!'), _(("%s has a standard price = %s is greater than list Price = %s") %(product.name, product.standard_price, product.list_price)))
                    b = False
        return b

    def _calculate_margin(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context):
            margin = 0
            if product.list_price >0 and product.standard_price>0:
                if product.list_price > product.standard_price:
                    margin = (1 - (product.standard_price/product.list_price))*100
            res[product.id] = margin
        return res
    
    def _tax_incl(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for product in self.browse(cr, uid, ids):
            val = 0.0
            for c in self.pool.get('account.tax').compute(cr, uid, product.taxes_id, product.list_price, 1, False):
                val += round(c['amount'], 2)
            res[product.id] = round(val + product.list_price, 2)

        return res
        
    def onchange_country(self, cr, uid, ids, manufacturer=None, company=None, context={}):
        res={}
        if manufacturer:
            res['manufacturer_country'] = self.pool.get('res.manufacturer').browse(cr,uid,manufacturer,context).manufacturer_country.id
        else:
            res['manufacturer_country'] = self.pool.get('res.company').browse(cr,uid,company,context).country_id.id
        return {'value':res}
                
    def _calculate_nprice(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        account_tax_obj = self.pool.get('account.tax')
        tax_value = 0.00
        for product in self.browse(cr, uid, ids, context):
            prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'AccountInvoice')
            nprice=product.list_price
            if product.p_net > 0:
                if product.taxes_id:
                    for t in product.taxes_id:
                        tax_code = account_tax_obj.browse(cr, uid, t.id)
                        if tax_code.ref_base_code_id.tax_type == 'vat':
                            tax_value = tax_code.amount                    
                            nprice = round(product.p_net/(1+tax_value) ,prec)
                else:
                    nprice = round(product.p_net,prec) 
                cr.execute('UPDATE product_template SET list_price = %s WHERE id = %s',(nprice,product.product_tmpl_id.id))
            total= round(product.p_net * (1 - (product.discount_percent/100)), prec)
            iva = round((product.p_net/(1+tax_value) * (1 - (product.discount_percent/100))*tax_value),prec)
            subtotal = total -iva
            res[product.id]={'lst_price_1':nprice,
                             'discount_price':subtotal,
                             'iva_price':iva,
                             'total_price':total,
                             }
        return res

    def _get_discount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context):
            discount_price = product.list_price * (1 - (product.discount_percent/100))
            res[product.id] = discount_price
        return res
                
    _columns = {
		'create_date': fields.datetime('Creation date', readonly=True),
        'year': fields.char('Year', size=4,readonly=True),
        'online': fields.boolean('Visible on website'),
        'income_pdt': fields.boolean('Product for Input'),
        'expense_pdt': fields.boolean('Product for expenses'),
        'am_out': fields.boolean('Control for Output Operations'),
        'disc_controle': fields.boolean('Discount Control'),
        'clasification_cat': fields.many2one('product.clasification', "clasification Product"),     
        'timport' : fields.selection([('normal','Normal Importation'),('fast','Fast Importation')],'Types of Trade Import'),
        'material' : fields.many2one('product.material', 'Material'),
        'color' : fields.many2one('product.color', 'Color'),
        'manufacturer' : fields.many2one('res.manufacturer', 'Manufacturer', traslate="True"),
        'supplier_id' : fields.many2one('res.partner', 'Supplier', traslate="True"),
        'manufacturer_country': fields.many2one('res.country', string='Country', traslate="True"),
        'manufacturer_pname' : fields.char('Manufacturer product name', size=256,traslate="True"),
        'manufacturer_pref' : fields.char('Manufacturer product code', size=256,traslate="True"),
        'manufacturer_factory' : fields.char('Factory', size=256,traslate="True"),
        'calsale': fields.selection([('A','A'),('B','B'),('C','C'),('D','D'),('E','E')],'Cal Sales', traslate="True"),
        'calinv': fields.selection([('A','A'),('B','B'),('C','C'),('D','D'),('E','E')],'Cal Stock', traslate="True"),
        'datecom': fields.date('Comercial Life',traslate="True"),
        'material': fields.many2one('product.material','Material'),
        'product_image': fields.binary('Image'),
        'packing_q': fields.float('Packing', digits_compute=dp.get_precision('Purchase Price')),
        'packing_p': fields.float('Present', digits_compute=dp.get_precision('Purchase Price')),
        'name_template': fields.related('product_tmpl_id', 'name', string="Name", type='char', size=256, store=True, select=True),
        'margin_base': fields.function(_calculate_margin, method=True, string='% Margin', digits_compute=dp.get_precision('Purchase Price')),
        'valuation':fields.selection([('real_time','Real Time (automated)'),], 'Inventory Valuation',
                                        help="If real-time valuation is enabled for a product, the system will automatically write journal entries corresponding to stock moves." \
                                             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products."
                                        , required=True),
                
        'p_net': fields.float('PVP', digits_compute=dp.get_precision('Sale Price'), help="El precio incluído impuestos"),    
        'total_price': fields.function(_calculate_nprice, method=True, string='Precio Total', digits_compute=dp.get_precision('Purchase Price'), multi="list_price",
                                       store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['p_net','discount_percent'], 15),}),                
        'discount_percent':fields.float('% Discount'),
        'discount_price': fields.function(_get_discount, method=True, string='Discount Price',digits_compute=dp.get_precision('Purchase Price'),store=True),
        'iva_price': fields.function(_calculate_nprice, method=True, string='IVA', digits_compute=dp.get_precision('Purchase Price'), multi="list_price",
                                     store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['p_net','discount_percent'], 15),}),
        'lst_price_1': fields.function(_calculate_nprice, method=True, string='Price', digits_compute=dp.get_precision('Purchase Price'), multi="list_price",
                                     store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['p_net','list_price'], 10),}),

    }
    
    _defaults = {
        'cost_method': lambda *a: 'average',
        'type' : lambda *a: 'product',
        'valuation': lambda *a: 'real_time',
        'disc_controle': True,
        'am_out': True,
        'packing_q': 1,
        'year' : time.strftime('%Y'),
        'default_code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'product.product'),
    }

    _order = 'default_code'
        
    _constraints = [(_verified_price, 'has a standard price is greater than list Price', ['standard_price','list_price'])]

    _sql_constraints = [
        ('unique_ean13', 'unique(ean13)',  'The ean13 field must be unique across all the products'),
    ]


    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        account_invoice_line_obj= self.pool.get('account.invoice.line')
        stock_move_obj = self.pool.get('stock.move')
        for product in self.browse(cr,uid,ids): 
            inv_search = account_invoice_line_obj.search(cr,uid,[('product_id','=',product.id)])
            stk_search = stock_move_obj.search(cr,uid,[('product_id','=',product.id)])
            if not inv_search and not stk_search:                
                date = time.strftime('%Y-%m-%d')            
                default_code = 'P_ELIMINADO_'+str(product.id) 
                cr.execute("""update product_product set write_date = %s, default_code =%s,active = False where id = %s """,(date,default_code,product.id))
            else:
                raise osv.except_osv(_('Restricción!'), _(("El producto no puede ser eliminado porque tiene movimientos de inventario o facturación. Puede proceder a desactivarlo pero no borrarlo.")))            
        return super(product_product, self).unlink(cr, uid, unlink_ids, context=context) 
product_product()


class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'type': fields.selection([('view','View'), ('normal','Normal'), ('service','Servicio')], 'Category Type'),
        'is_comercial':fields.boolean('Is Comercial',help="If TRUE is Comercial else is Administrative"),
        'active': fields.boolean('Active'),
    }
    
    _defaults={
               'is_comercial':True,
               'active':True,
               }
    
product_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


