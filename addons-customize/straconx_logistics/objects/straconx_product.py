    # -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 - present STRACONX S.A. 
#
#
##############################################################################


from osv import fields, osv
from tools.translate import _
import time
import decimal_precision as dp
import string

class product_product(osv.osv):
    _inherit = 'product.product'
    
    def _calcule_volume(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids):
            res[product.id] = 0
            if product.height > 0  and product.width > 0 and product.long > 0:
                res[product.id] = product.height * product.width * product.long
        return res
    
    def _check_length(self,cr,uid,ids):
        b=True
        for product in self.browse(cr, uid, ids):
            if (product['height'] < 0 or product['width'] < 0 or product['long'] < 0):
                b=False
        return b
    
#    def write(self, cr, uid, ids, values, context):
#        try:
#            for product in self.browse(cr, uid, ids, context):
#                if product.ubication_ids:
#                    for ubication in product.ubication_ids:
#                        self.pool.get('product.ubication').write(cr, uid, [ubication.id,], {}, context)
#            return super(product_product, self).write(cr, uid, ids, values, context) 
#        except:
#            return super(product_product, self).write(cr, uid, ids, values, context)

    #@profile
    def _product_qty_location_available(self, cr, uid, ids, name, arg, context=None):        
        res = {}
        user_shop = self.pool.get('res.users').browse(cr,uid,uid)
        if not user_shop.shop_id:
            raise osv.except_osv('Error!', _("El usuario %s no esta autorizado para ver el inventario de los productos ")%(user_shop.login))
        
        if user_shop.shop_id.shop_ubication_id:
            location_id = user_shop.shop_id.shop_ubication_id            
        else:            
            raise osv.except_osv('Error!', _("La tienda %s no tiene definida una ubicación principal de productos ")%(user_shop.shop_id.name,))        
        for product in self.browse(cr, uid, ids):
            cr.execute("""select (select sum(qty) from product_ubication where product_id =%s) as qty_total,
            (select sum(qty) from product_ubication where product_id =%s and shop_ubication_id = %s) as qty_shop""",(product.id,product.id,location_id.id))   
            res[product.id] = {'qty_available_shop':0.00,
                   'qty_available_location': 0.00
                   }
            result = cr.fetchall()
            if result and result[0]:
                qty_shop =result[0][1]
                qty_total = result[0][0]
                res[product.id] = {'qty_available_shop':qty_shop,
                   'qty_available_location': qty_total
                   }
        return res 
    
    _columns = {
        #'ubications_ids': fields.many2many('product.ubication', 'product_ubication_rel', 'product_id', 'ubication_id', 'Ubications')
        'qty_available_shop': fields.function(_product_qty_location_available, method=True, digits_compute=dp.get_precision('Product UoM'), string='Inventario en Tienda', multi='qty'),
        'qty_available_location': fields.function(_product_qty_location_available, method=True, digits_compute=dp.get_precision('Product UoM'), string='Inventario Total', multi='qty'),
        'date_purchase': fields.date('Last Purchase'),
        'ubication_ids':fields.one2many('product.ubication', 'product_id', 'Ubications', required=False),
        'height': fields.float('Height', digits=(16,2), help='Define the height of product to occupy on the ubication of the Location'),
        'width': fields.float('Width', digits=(16,2), help='Define the width of product to occupy on the ubication of the Location'),
        'long': fields.float('Long', digits=(16,2), help='Define the long of product to occupy on the ubication of the Location'),
        'volume': fields.function(_calcule_volume, method=True, type='float', string='Volume', 
                                store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['height','width','long'], 1),}),
        'inventory_ids': fields.one2many('stock.inventory.line', 'product_id', 'Inventarios'),                
    }
    _constraints = [(_check_length,'The dimensions of the product can not be less than 0',['height','width','long'])]
    
#     _defaults = {'qty_available_shop':_product_qty_location_available,
#                  'qty_available_location':_product_qty_location_available,}
    
    
    #@profile
    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        
        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        shop_obj = self.pool.get('sale.shop')
        
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        if not ids:
            return res

        if context.get('shop', False):
            warehouse_id = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                context['warehouse'] = warehouse_id

        if context.get('warehouse', False):
            lot_id = warehouse_obj.read(cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                context['location'] = lot_id

        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(cr, uid, [('name','ilike',context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = warehouse_obj.search(cr, uid, [], context=context)
            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = location_obj.search(cr, uid, [('location_id', 'in', location_ids)])
            location_ids = child_location_ids or location_ids

        # this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
        uoms_o = {}
        # this will be a dictionary of the product UoM by product id
        product2uom = {}
        for product in self.browse(cr, uid, ids, context=context):
            product2uom[product.id] = product.uom_id.id
            uoms_o[product.uom_id.id] = product.uom_id

        results = []
        results2 = []

        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
        if from_date and to_date:
            date_str = "date>=%s and date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "date>=%s"
            date_values = [from_date]
        elif to_date:
            date_str = "date<=%s"
            date_values = [to_date]

        prodlot_id = context.get('prodlot_id', False)
        fill_categ_id = context.get('fill_categ_id', False)
        ubication_id = context.get('ubication_id', False)

    # TODO: perhaps merge in one query.
        if date_values:
            where.append(tuple(date_values))
        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id NOT IN %s '\
                'and location_dest_id IN %s '\
                'and product_id IN %s '\
                '' + (prodlot_id and ('and prodlot_id = ' + str(prodlot_id)) or '') + ' '\
                '' + (ubication_id and ('and ubication_id = ' + str(ubication_id)) or '') + ' '\
                '' + (fill_categ_id and ('and categ_id = ' + str(fill_categ_id)) or '') + ' '\
                'and state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
                'group by product_id,product_uom',tuple(where))
            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id IN %s '\
                'and location_dest_id NOT IN %s '\
                'and product_id  IN %s '\
                '' + (prodlot_id and ('and prodlot_id = ' + str(prodlot_id)) or '') + ' '\
                '' + (fill_categ_id and ('and categ_id = ' + str(fill_categ_id)) or '') + ' '\
                'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
                'group by product_id,product_uom',tuple(where))
            results2 = cr.fetchall()
            
        # Get the missing UoM resources
        uom_obj = self.pool.get('product.uom')
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if context.get('uom', False):
            uoms += [context['uom']]
        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
            for o in uoms:
                uoms_o[o.id] = o
                
        #TOCHECK: before change uom of product, stock move line are in old uom.
        context.update({'raise-exception': False})
        # Count the incoming quantities
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                     uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] += amount
        # Count the outgoing quantities
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] -= amount
        return res

    def create(self, cr, uid, vals, context={}):
        res = super(product_product, self).create(cr, uid, vals, context)
        if res:
            date_c = time.strftime('%Y-%m-%d %H:%M:%S')
            categ_id = self.browse(cr,uid,res).product_tmpl_id.categ_id.id
            sql="""INSERT INTO product_ubication(product_id,
            ubication_id,create_uid, create_date,  
            location_ubication_id, shop_ubication_id, categ_id)
            SELECT  %s, id,%s,%s,location_id, shop_ubication_id,%s
            FROM ubication"""
            cr.execute(sql,(res,uid,date_c, categ_id))
            pd = self.browse(cr,uid,res)
            if pd.date_purchase:
                date_purchase=pd.date_purchase
            else:
                date_purchase = time.strftime('%Y-%m-%d %H:%M:%S')
                self.write(cr, uid, [res], {'date_purchase':date_purchase})
        return res
    
    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        default.update({
            'ubication_ids':[],
            })
        return super(product_product, self).copy(cr, uid, id, default, context)

    #@profile
    def get_product_accounts(self, cr, uid, product_id, context=None):
        """ To get the stock input account, stock output account and stock journal related to product.
        @param product_id: product id
        @return: dictionary which contains information regarding stock input account, stock output account and stock journal
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
#        categ_id = product_obj.categ_id.id
        cr.execute("""select categ_id from product_template where id = (select product_tmpl_id from product_product where id=%s)""",(product_id,))
        categ_id = cr.fetchall()
        categ_id = categ_id[0][0]
        company_id = product_obj.company_id.id or 1
        stock_output_acc = False
        stock_input_acc = False
        account_transit = False
        if not stock_input_acc:
            product_category = 'product.category,%s'%categ_id
            cr.execute("""select value_reference from ir_property where name = 'property_stock_account_input_categ' and company_id = %s and res_id =%s and value_reference is not null limit 1""",(company_id,product_category))            
            stock_input_acc = cr.fetchall()
            if len(stock_input_acc)>0:
                stock_input_acc = int(stock_input_acc[0][0].split(',')[1])
        if not stock_output_acc:
            product_category = 'product.category,%s'%categ_id
            cr.execute("""select value_reference from ir_property where name = 'property_stock_account_output_categ' and company_id = %s and res_id =%s and value_reference is not null limit 1""",(company_id,product_category))            
            stock_output_acc = cr.fetchall()
            if len(stock_output_acc)>0:
                stock_output_acc = int(stock_output_acc[0][0].split(',')[1])
        if not account_transit:
            product_category = 'product.category,%s'%categ_id
            cr.execute("""select value_reference from ir_property where name = 'property_stock_transit_account_categ' and company_id = %s and res_id =%s and value_reference is not null limit 1""",(company_id,product_category))            
            account_transit = cr.fetchall()
            if len(account_transit)>0:
                account_transit = int(account_transit[0][0].split(',')[1])
            else:    
                cr.execute("""select value_reference from ir_property where name = 'property_stock_transit_account_categ' and company_id = %s and value_reference is not null limit 1""",(company_id,))
                account_transit = cr.fetchall()
                if len(account_transit)>0:
                    account_transit = int(account_transit[0][0].split(',')[1])        
        journal_id = self.pool.get('account.journal').search(cr,uid,[('type','=','stock')])[0]
        if not journal_id:
            raise osv.except_osv(_('Error!'), _(("Necesita definir un diario tipo Inventario para continuar")))

        cr.execute("""select value_reference from ir_property where name = 'property_stock_valuation_account_id' and company_id = %s and value_reference is not null limit 1""",(company_id,))
        account_valuation = cr.fetchall()
        if len(account_valuation)>0:
            account_valuation = int(account_valuation[0][0].split(',')[1])        
                
        return {
            'stock_account_input': stock_input_acc,
            'stock_account_output': stock_output_acc,
            'stock_journal': journal_id,
            'property_stock_valuation_account_id': account_valuation,
            'property_stock_transit_account_id': account_transit
        }

product_product()


class product_uom_categ(osv.osv):
    _inherit = 'product.uom.categ'
    _columns = {
        'decimals': fields.boolean('Permitted decimals'),
    }
    
    _defaults = {
        'decimals': True,
                 }
product_uom_categ()

