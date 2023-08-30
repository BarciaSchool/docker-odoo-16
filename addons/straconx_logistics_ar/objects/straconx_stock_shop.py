# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A (Carlos Zambrano Salazar) 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import psycopg2

class straconx_stock_shop(osv.osv):    
    _name = "stock.shop"
    _columns = {
    'only_stock':fields.boolean('Solo con Inventario'),
    'new_products': fields.datetime('Productos que llegaron desde'),
    'categ_id': fields.many2one('product.category', 'Category'),
    'clas_id': fields.many2one('product.clasification','Clasification'),
    'default_code': fields.char('Código',size=20),
    'initial':fields.char('Inicial',size=10,required=False,help="Inicio de la secuencia"),
    'final':fields.char('Final',size=10,required=False,help="Final de la secuencia"),
    'product_id': fields.char('Producto',size=30),
    'product_lines_ids':fields.one2many('stock.shop.lines','wizard_id','Product Lines' )
    }        

    
    def order_list(self, position, element, list_location):
        if element in list_location:
            list_location.remove(element)
            list_location.insert(position, element)
        return list_location
    
    def __similar_to(self,initial,final,code):
        similar=""
        range_list=range(initial,final+1)
        for each in range_list:
            similar+=code+str(each)+"|"
        similar="("+similar[0:len(similar)-1]+"%)"
        return similar
            
    def do_search_products(self, cr, uid, ids, context=None):
        sql = "select pp.id from product_product pp left join product_template pt on pt.id = pp.product_tmpl_id left join product_category pc on pc.id = pt.categ_id left join product_clasification pcl on pcl.id = pp.clasification_cat"
        where =" where "
        wiz_id = "select id from stock_shop_lines where wizard_id =%s"%(ids[0],)
        cr.execute(wiz_id)
        del_wizard = cr.fetchall()
        cr.execute("""select count(wizard_id) from stock_shop_lines_names where wizard_id =%s""",(ids[0],))
        old_wizard = cr.fetchall()
        if int(old_wizard[0][0]):
            cr.execute("""delete from stock_shop_lines_names where wizard_id =%s""",(ids[0],))        
        if del_wizard:
            cr.execute("delete from stock_shop_lines where wizard_id =%s"%(ids[0]))
        w_obj = self.pool.get('ubication').search(cr,uid,[])
        list_location=[]
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
#         shop_id = user_id.printer_point_ids and user_id.printer_point_ids[0].shop_id.id or None
        shop_id = user_id.shop_id.id or None
        try:
            central_w = self.pool.get('sale.shop').search(cr,uid,[('central_warehouse','=',True)],limit=1)[0]
            location_w=self.pool.get('sale.shop').browse(cr,uid,central_w).warehouse_id.lot_stock_id
            location_wdel = location_w.location_id.id,location_w.location_id.name
        except:
            location_wdel = None
        if not shop_id:
            raise osv.except_osv(_('Invalid Action!'), _('Debe definir una Tienda predeterminada para su usuario.'))
        else:
            location_s = self.pool.get('sale.shop').browse(cr,uid,shop_id).warehouse_id.lot_stock_id
            location_del = location_s.location_id.id, location_s.location_id.name
        wareh=None
        for w in w_obj:
            location_shop = self.pool.get('ubication').browse(cr,uid,w).shop_ubication_id
            shop_n = self.pool.get('ubication').browse(cr,uid,w).location_id.id
            if not self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',shop_n)]) and not wareh:
                wareh=(location_shop.id,location_shop.name)
            if location_shop and (location_shop.id,location_shop.name) not in list_location:
                list_location.append((location_shop.id,location_shop.name))
            else:
                continue
        list_location=self.order_list(0, location_del, list_location)
        list_location=self.order_list(1, location_wdel, list_location)
        list_location=self.order_list(2, wareh, list_location)
        sql_t = ""
        sql1="DROP TABLE IF EXISTS resultados;create table resultados as SELECT pu.product_id,pp.default_code as default_code, pp.p_qty as qty_purchase, pp.create_date as create_date_product, "
        sql2=" SUM(qty) AS TOTAL, %s as wizard_id FROM product_ubication pu JOIN stock_location sl ON sl.id = pu.shop_ubication_id join product_product pp on pp.id= pu.product_id "%(ids[0])
##        sql2=" SUM(qty) AS TOTAL, %s as wizard_id FROM stock_move sm JOIN stock_location sl ON sl.id = pu.shop_ubication_id join product_product pp on pp.id= pu.product_id "%(ids[0])
        for location_name in list_location:
            wareh = "warehouse_%s"%str(list_location.index(location_name)+1)
            cr.execute("""insert into stock_shop_lines_names (wizard_id, warehouse,name) values (%s,%s,%s)""",(ids[0],wareh,location_name[1]))
            sql_w ="array_to_string(array_append('{}', SUM(CASE shop_ubication_id  WHEN %s THEN qty ELSE 0 END)),',')::float AS %s,"%(location_name[0],wareh)
            sql_t +=sql_w    
        param=[True]   
        for wizard in self.browse(cr, uid, ids, context):
            initial=wizard.initial and int(wizard.initial) or False
            final=wizard.final and int(wizard.final) or False       
            list_filter=""
            if(wizard.default_code):
                list_filter=" and pp.default_code ilike (%s) "
                param.append(wizard.default_code+"%")
                similar_to=""
                if((final and initial)):
                    if(final>initial):
                        similar_to=" and upper(pp.default_code) similar to %s "
                        param.append(self.__similar_to(initial, final, wizard.default_code.upper()))
                    if(final==initial):
                        param[1]=wizard.defaul_code+str(initial)+"%"
                    if(initial>final):
                        raise osv.except_osv(_("Validation Error!"),_("Range initial value should not be higher at the end of the range."))
                if((final and not initial or initial==0)):
                    initial=initial and 0
                    if(final>initial):
                        similar_to=" and upper(pp.default_code) similar to %s "
                        param.append(self.__similar_to(initial, final, wizard.default_code.upper()))   
                if(not final and initial):
                    similar_to=" and upper(pp.default_code) not similar to %s "
                    param.append(self.__similar_to(0,initial, wizard.default_code.upper()))          
                list_filter=list_filter+similar_to
            if(wizard.categ_id):
                param.append(wizard.categ_id.id)
                list_filter=list_filter+" and pt.categ_id=%s"
            if(wizard.clas_id):
                param.append(wizard.clas_id.id)
                list_filter=list_filter+" and pp.clasification_cat=%s"
            if wizard.only_stock:
                only_stock=True
            else:
                only_stock=False
            if wizard.product_id:
                param.append("%"+wizard.product_id+"%")
                product_id = " and pt.name like %s"
                list_filter=list_filter+product_id
            if wizard.new_products:
                param.append(wizard.new_products)
                list_filter=list_filter+" and pp.date_purchase<%s"
            cr.execute("select pp.id,pp.id from product_product pp inner join product_template pt on pp.product_tmpl_id=pt.id where pp.active=%s "+list_filter+" order by pp.default_code asc",tuple(param))
            prt_ids=cr.fetchall()            
        product_ids = [] 
        if prt_ids:
            for p in prt_ids:
                product_ids.append(p[0])
            if len(product_ids)>1:
                sql_end = sql1 + sql_t  +sql2+" where product_id in %s "%(tuple(product_ids),)+" GROUP BY product_id, pp.default_code, pp.create_date, pp.p_qty order by pp.default_code "
            elif len(product_ids)==1:
                sql_end = sql1 + sql_t  +sql2+" where product_id = %s "%(tuple(product_ids))+" GROUP BY product_id, pp.default_code, pp.create_date, pp.p_qty order by pp.default_code "
            else:
                sql_end = sql1 + sql_t  +sql2+" GROUP BY product_id, pp.default_code, pp.create_date, pp.p_qty order by pp.default_code "
            cr.execute(sql_end)
        cr.execute("INSERT INTO stock_shop_lines (product_id,default_code,total,wizard_id,qty_purchase,create_date_product,warehouse_1, warehouse_2, warehouse_3, warehouse_4,warehouse_5,warehouse_6,warehouse_7,warehouse_8) SELECT product_id,default_code,total,wizard_id,qty_purchase,create_date_product,warehouse_1, warehouse_2, warehouse_3 , warehouse_4,warehouse_5,warehouse_6,warehouse_7,warehouse_8 FROM resultados")            
        if only_stock:
            cr.execute("delete from stock_shop_lines where total <=0")
        return True      

    def onchange_code(self,cr,uid,ids,default_code,initial,final,context=None):
        if(not default_code):
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
straconx_stock_shop()

class straconx_stock_shop_lines(osv.osv):
    def _get_stock(self, object, cr, uid, ids, field_names, arg, context=None):        
        res = {}
        return res
    
    _name = "stock.shop.lines"
    _columns = {
    'wizard_id': fields.many2one('stock.shop', 'Stock Shop Wizard'),                
    'default_code': fields.related('product_id','default_code',type='char',size=256, string='Código', relation='product.product',store=True),
    'product_id':fields.many2one('product.product', 'Producto'),                
    'categ_id': fields.related('product_id','categ_id',type='many2one', string='Categoría', relation='product.category'),
    'clas_id': fields.related('product_id','clasification_cat',type='many2one', string='Clasificación', relation='product.clasification'),
    'qty_purchase': fields.float('Unidades Compradas'),
    'create_date_product': fields.related('product_id','date_purchase',type='date', string='Create Date', relation='product.product', store=True),    
    'warehouse_1': fields.float('Warehouse_1'),
    'warehouse_2': fields.float('Warehouse_2'),
    'warehouse_3': fields.float('Warehouse_3'),
    'warehouse_4': fields.float('Warehouse_4'),
    'warehouse_5': fields.float('Warehouse_5'),
    'warehouse_6': fields.float('Warehouse_6'),
    'warehouse_7': fields.float('Warehouse_7'),
    'warehouse_8': fields.float('Warehouse_8'),
    'warehouse_9': fields.float('Warehouse_9'),
    'warehouse_10': fields.float('Warehouse_10'),
    'warehouse_11': fields.float('Warehouse_11'),
    'warehouse_12': fields.float('Warehouse_12'),
    'warehouse_13': fields.float('Warehouse_13'),
    'warehouse_14': fields.float('Warehouse_14'),
    'warehouse_15': fields.float('Warehouse_15'),
    'total':fields.float('Total Tiendas')    
    }

    _order = 'default_code asc'
    
    def order_list(self, position, element, list_location):
        if element in list_location:
            list_location.remove(element)
            list_location.insert(position, element)
        return list_location
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='tree', context=None, toolbar=False,submenu=False):
#         uid = 1
        result = super(straconx_stock_shop_lines, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar,submenu)
        cr.execute("""select id from ir_actions where name='Make Procurement'""")
        bids = cr.fetchall()
        bids = bids and bids[0][0] or None
        if result['type'] in ('tree') :
            w_obj = self.pool.get('ubication').search(cr,uid,[])
            label = "<%s string='Inventario por Tienda'><field name='product_id'/><field name='qty_purchase' sum='qty' groups='base.group_document_manager'/><label string=' '/>"%result['type']
            label = label + "<button name='%s' string='Pedido' icon='gtk-add' type='action'/>"%bids
            list_location=[]
            user_id = self.pool.get('res.users').browse(cr,uid,uid)
            shop_id = user_id.shop_id.id or None
            try:
                central_w = self.pool.get('sale.shop').search(cr,uid,[('central_warehouse','=',True)],limit=1)[0]
                location_w=self.pool.get('sale.shop').browse(cr,uid,central_w).warehouse_id.lot_stock_id
                location_wdel = location_w.location_id.id,location_w.location_id.name
            except:
                location_wdel = None
            if not shop_id:
                raise osv.except_osv(_('Invalid Action!'), _('Debe definir una Tienda predeterminada para su usuario.'))
            else:
                location_s = self.pool.get('sale.shop').browse(cr,uid,shop_id).warehouse_id.lot_stock_id
                location_del = location_s.location_id.id, location_s.location_id.name
            wareh=None
            for w in w_obj:
                location_shop = self.pool.get('ubication').browse(cr,uid,w).shop_ubication_id
                shop_n = self.pool.get('ubication').browse(cr,uid,w).location_id.id
                if not self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',shop_n)]) and not wareh:
                    wareh=(location_shop.id,location_shop.name)
                if location_shop and (location_shop.id,location_shop.name) not in list_location:
                    list_location.append((location_shop.id,location_shop.name))
                else:
                    continue
            list_location=self.order_list(0, location_del, list_location)
            list_location=self.order_list(1, location_wdel, list_location)
            list_location=self.order_list(2, wareh, list_location)
            for location_name in list_location:
                wareh = "warehouse_%s"%str(list_location.index(location_name)+1)
                result['fields'].update({wareh:{'type':'float', 'digits': (16, 2), 'store': True, 'string': location_name[1]}})
                label = label + """<field name='%s' sum='%s'/>"""%(wareh,wareh)            
            result['fields'].update({'total':{'type': 'float', 'digits': (16, 2), 'store': True, 'string': 'TOTAL'}})
            label = label + "<field name='total' string='TOTAL' invisible='0' sum='Total'/></%s>"%result['type']
            result['arch'] = label
        return result   
straconx_stock_shop_lines()


class straconx_stock_shop_names(osv.osv):    
    _name = "stock.shop.lines.names"
    _columns = {
                'wizard_id': fields.many2one('stock.shop', 'Stock Shop Wizard'),
                'warehouse': fields.char('Bodega', size=50),
                'name': fields.char('Nombre', size=50),
                }
straconx_stock_shop_names()
