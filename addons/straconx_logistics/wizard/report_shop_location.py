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

class straconx_stock_location_shop(osv.osv):    
    _name = "stock.shop.location"
    _columns = {
    'only_stock':fields.boolean('Solo con Inventario'),
    'new_products': fields.datetime('Productos que llegaron desde'), 
    'categ_id': fields.many2one('product.category', 'Category'),
    'clas_id': fields.many2one('product.clasification','Clasification'),
    'shop_id':fields.many2one('sale.shop', 'Tienda'),   
    'default_code': fields.char('Código',size=20),
    'initial':fields.char('Inicial',size=10,required=False,help="Inicio de la secuencia"),
    'final':fields.char('Final',size=10,required=False,help="Final de la secuencia"),
    'product_id': fields.char('Producto',size=30),
    'product_lines_ids':fields.one2many('stock.shop.location.lines','wizard_id','Product Lines' )
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
        wiz_id = "select id from stock_shop_location_lines where wizard_id =%s"%(ids[0],)
        cr.execute(wiz_id)
        del_wizard = cr.fetchall()
        cr.execute("""select count(wizard_id) from stock_shop_lines_location_names where wizard_id =%s""",(ids[0],))
        old_wizard = cr.fetchall()
        if int(old_wizard[0][0]):
            cr.execute("""delete from stock_shop_lines_location_names where wizard_id =%s""",(ids[0],))
        if del_wizard:
            cr.execute("delete from stock_shop_location_lines where wizard_id =%s"%(ids[0]))
        w_obj = self.pool.get('ubication').search(cr,uid,[])
        list_location=[]
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        shop_id = self.browse(cr, uid,ids[0]).shop_id.id or user_id.shop_id.id
        shop = self.pool.get('sale.shop').browse(cr,uid,shop_id)
        user_database = user_id.shop_id.server_url
        shop_obj = self.pool.get('sale.shop')
        try:
            central_w = self.pool.get('sale.shop').search(cr,uid,[('central_warehouse','=',True)],limit=1)[0]
            location_w=self.pool.get('sale.shop').browse(cr,uid,central_w).warehouse_id.lot_stock_id
            location_wdel = location_w.id,location_w.name
        except:
            location_wdel = None
        if not shop_id:
            raise osv.except_osv(_('Invalid Action!'), _('Debe definir una Tienda predeterminada para su usuario.'))
        else:
            location_s = self.pool.get('sale.shop').browse(cr,uid,shop_id).warehouse_id.lot_stock_id
            location_del = location_s.location_id.id, location_s.location_id.name
        wareh=None
        for w in w_obj:
            location_shop = self.pool.get('ubication').browse(cr,uid,w).location_id
            shop_n = self.pool.get('ubication').browse(cr,uid,w).location_id.id
            if not self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',shop_n)]) and not wareh:
                wareh=(location_shop.id,location_shop.name)
            if location_shop and (location_shop.id,location_shop.name) not in list_location and (location_shop.location_id.id == shop.warehouse_id.lot_stock_id.location_id.id):
                list_location.append((location_shop.id,location_shop.name))
            else:
                continue
        list_location=self.order_list(0, location_del, list_location)
        list_location=self.order_list(1, location_wdel, list_location)
        list_location=self.order_list(2, wareh, list_location)
        sql_t = ""
        sql1="DROP TABLE IF EXISTS resultados;create table resultados as SELECT pu.product_id,pp.default_code as default_code, pp.p_qty as qty_purchase, pp.create_date as create_date_product, "
        sql2=" SUM(qty) AS TOTAL, %s as wizard_id FROM product_ubication pu JOIN stock_location sl ON sl.id = pu.location_ubication_id join product_product pp on pp.id= pu.product_id "%(ids[0])
##        sql2=" SUM(qty) AS TOTAL, %s as wizard_id FROM stock_move sm JOIN stock_location sl ON sl.id = pu.shop_ubication_id join product_product pp on pp.id= pu.product_id "%(ids[0])
        WARE_IDS=''
        c=0
        for location_name in list_location:
            wareh = "warehouse_%s"%str(list_location.index(location_name)+1)
            cr.execute("""insert into stock_shop_lines_location_names (wizard_id, warehouse,name) values (%s,%s,%s)""",(ids[0],wareh,location_name[1]))
            sql_w ="array_to_string(array_append('{}', SUM(CASE location_ubication_id  WHEN %s THEN qty ELSE 0 END)),',')::float AS %s,"%(location_name[0],wareh)
            sql_t +=sql_w 
            c = c+1
            if len(list_location) > c:   
                WARE_IDS=WARE_IDS+wareh+','
        WARE_IDS=WARE_IDS+wareh
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
        location_obj = self.pool.get('stock.location')
        location_ids = location_obj.search(cr,uid,[('usage','=','internal'),('company_id','=',user_id.shop_id.company_id.id),('active','=',True),('location_id','=',shop.warehouse_id.lot_stock_id.location_id.id)])
        if prt_ids:
            for p in prt_ids:
                product_ids.append(p[0])
        if not product_ids:
            raise osv.except_osv('Error!', _("No existen productos para los códigos que usted selecciono."))

#             shop_ubication_id = location_obj.browse(cr,uid,location).location_id.id
#             shop_ids = shop_obj.search(cr,uid,[('shop_ubication_id','=',shop_ubication_id)])        

        if shop_id:  
                
            shop = shop_obj.browse(cr,uid,shop_id)
            database = shop_obj.browse(cr,uid,shop.id).server_db
            port = shop_obj.browse(cr,uid,shop.id).server_port
            host = shop_obj.browse(cr,uid,shop.id).server_url
            user = shop_obj.browse(cr,uid,shop.id).login
            password= shop_obj.browse(cr,uid,shop.id).password
            date = time.strftime('%Y-%m-%d %H:%M:%S')
            for location in location_ids:
                cr.execute("""select id from sale_shop where shop_ubication_id = (select location_id from stock_location where id = %s)""",(location,))
                shop_ids =cr.fetchone()
                if shop_id:
                        sql_update = """SELECT SUM(x.coeff * x.product_qty) as product_qty,product_id,%s as location_id FROM
                                        (SELECT product_id,1.0 as coeff, location_dest_id as loc_id, sum(product_qty) AS product_qty 
                                        FROM stock_move sm WHERE location_dest_id =%s AND location_id != location_dest_id AND state = 'done'
                                        and sm.product_id in %s
                                        GROUP BY product_id,location_dest_id, product_uom 
                                        UNION 
                                        SELECT product_id,-1.0 as coeff, location_id as loc_id,sum(product_qty) AS product_qty 
                                        FROM stock_move sm WHERE location_id =%s AND location_id != location_dest_id AND state = 'done'
                                        and sm.product_id in %s
                                        GROUP BY product_id,location_id, product_uom) 
                                        AS x GROUP BY product_id,x.loc_id order by product_id"""
                        
                        if not database or not port or not host or not user or not password:
                            raise osv.except_osv('Error!', _("La tienda %s no tiene configurada toda la información de conexión.")%(shop.name))
                        try:
                            conection = psycopg2.connect(database=database, user=user, password=password, host=host, port=port, options='-c statement_timeout=15s')
                            if conection:
                                conect = conection.cursor()
                                conect.execute(sql_update,(location, location, tuple(product_ids), location, tuple(product_ids)))                                
                                ils = conect.fetchall()
                                if ils:
                                    cr.executemany("""UPDATE product_ubication SET WRITE_DATE = now(), qty =%s where product_id = %s and location_ubication_id = %s""",ils)
                        except psycopg2.Error, e:
                            continue
        #                    return True
                if len(location_ids)>1:
                    loc = "and location_ubication_id in %s"%(tuple(location_ids),)
                else:
                    loc = "and location_ubication_id = %s"%(tuple(location_ids))
                if len(product_ids)>1:
                    sql_end = sql1 + sql_t  +sql2+" where product_id in %s "%(tuple(product_ids),)+loc+" GROUP BY product_id, pp.default_code, pp.create_date, pp.p_qty order by pp.default_code "
                elif len(product_ids)==1:
                    sql_end = sql1 + sql_t  +sql2+" where product_id = %s "%(tuple(product_ids))+loc+" GROUP BY product_id, pp.default_code, pp.create_date, pp.p_qty order by pp.default_code "
                else:
                    sql_end = sql1 + sql_t  +sql2+" GROUP BY product_id, pp.default_code, pp.create_date, pp.p_qty order by pp.default_code "
                cr.execute(sql_end)
            sql_in=("""INSERT INTO stock_shop_location_lines (product_id,default_code,total,wizard_id,qty_purchase,create_date_product,%s) 
            SELECT product_id,default_code,total,wizard_id,qty_purchase,create_date_product,%s FROM resultados"""%(WARE_IDS,WARE_IDS))           
            cr.execute(sql_in)
            if only_stock:
                cr.execute("delete from stock_shop_location_lines where total <=0")
            #view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name','=','Shop Location Form')])[0]
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
    
    def location_search(self, cr, uid, ids, context=None):
        if not ids: return []
        lines=[]
        self.do_search_products(cr,uid,ids)
        loc = self.browse(cr, uid, ids[0], context=context)
        for line in loc.product_lines_ids:
            lines.append(line.id)
        return {
            'name':_("Stock Shop Location Form"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'stock.shop.location',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': {},
            'context': {
                'default_product_lines_ids': [(6, 0, [x for x in lines])],
                #'default_id':loc.id,
                'default_default_code': loc.default_code,
                'default_initial': loc.initial,
                'default_final': loc.final,
                'default_shop_id': loc.shop_id.id,
                'default_product_id':loc.product_id,
                'default_new_products':loc.new_products or None,
                'default_categ_id': loc.categ_id.id,
                'default_class_id': loc.clas_id.id,
                'default_only_stock': loc.only_stock,
                'close_after_process': True,
                }
        }
straconx_stock_location_shop()

class straconx_stock_shop_location_lines(osv.osv):
    def _get_stock(self, object, cr, uid, ids, field_names, arg, context=None):        
        res = {}
        return res
    
    _name = "stock.shop.location.lines"
    _columns = {
    'wizard_id': fields.many2one('stock.shop.location', 'Stock Shop Wizard'),                
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
        result = super(straconx_stock_shop_location_lines, self).fields_view_get(cr, uid, None, view_type, context, toolbar,submenu)
        print(result)
        cr.execute("""select id from ir_actions where name='Make Procurement'""")
        bids = cr.fetchall()
        bids = bids and bids[0][0] or None
        if result['type'] in ('tree') :
            w_obj = self.pool.get('ubication').search(cr,uid,[])
            label = "<%s string='Inventario por Tienda/Bodega'><field name='product_id'/><field name='qty_purchase' sum='qty' groups='base.group_document_manager'/>"%result['type']
            list_location=[]
            user_id = self.pool.get('res.users').browse(cr,uid,uid)
            shop_id = context.get('shop_id', False) or user_id.shop_id.id or None
            shop = self.pool.get('sale.shop').browse(cr,uid,shop_id)
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
                location_shop = self.pool.get('ubication').browse(cr,uid,w).location_id
                shop_n = self.pool.get('ubication').browse(cr,uid,w).location_id.id
                if not self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',shop_n)]) and not wareh:
                    wareh=(location_shop.id,location_shop.name)
                if location_shop and (location_shop.id,location_shop.name) not in list_location and (location_shop.location_id.id == shop.warehouse_id.lot_stock_id.location_id.id):
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
straconx_stock_shop_location_lines()


class straconx_stock_shop_location_names(osv.osv):    
    _name = "stock.shop.lines.location.names"
    _columns = {
                'wizard_id': fields.many2one('stock.shop.location', 'Stock Shop Wizard'),
                'warehouse': fields.char('Bodega', size=50),
                'name': fields.char('Nombre', size=50),
                }
straconx_stock_shop_location_names()

class stock_location_shop_parameters(osv.osv):    
    _name = "stock.shop.location.parameters"
    _columns = {
    'only_stock':fields.boolean('Solo con Inventario'),
    'new_products': fields.datetime('Productos que llegaron desde'), 
    'categ_id': fields.many2one('product.category', 'Category'),
    'clas_id': fields.many2one('product.clasification','Clasification'),
    'default_code': fields.char('Código',size=20),
    'initial':fields.char('Inicial',size=10,required=False,help="Inicio de la secuencia"),
    'final':fields.char('Final',size=10,required=False,help="Final de la secuencia"),
    'product_id': fields.char('Producto',size=30),
    } 
    
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
stock_location_shop_parameters()

# class straconx_stock_location_shop_parameters(osv.osv):    
#     _name = "stock.shop.location.parameters"
#     _columns = {
#     'only_stock':fields.boolean('Solo con Inventario'),
#     'new_products': fields.datetime('Productos que llegaron desde'), 
#     'categ_id': fields.many2one('product.category', 'Category'),
#     'clas_id': fields.many2one('product.clasification','Clasification'),
#     'shop_id':fields.many2one('sale.shop', 'Tienda'),   
#     'default_code': fields.char('Código',size=20),
#     'initial':fields.char('Inicial',size=10,required=False,help="Inicio de la secuencia"),
#     'final':fields.char('Final',size=10,required=False,help="Final de la secuencia"),
#     'product_id': fields.char('Producto',size=30)
#     } 
#     
#     def location_search(self, cr, uid, ids, context=None):
#         if not ids: return []
#         loc = self.browse(cr, uid, ids[0], context=context)
#         return {
#             'name':_("Inventario por Tienda/Bodega"),
#             'view_mode': 'form',
#             'view_id': False,
#             'view_type': 'form',
#             'res_model': 'stock.shop.location',
#             'type': 'ir.actions.act_window',
#             'nodestroy': True,
#             'target': 'new',
#             'domain': {},
#             'context': {
#                 'default_default_code': loc.default_code,
#                 'default_initial': loc.initial,
#                 'default_final': loc.final,
#                 'default_shop_id': loc.shop_id.id,
#                 'default_product_id':loc.product_id,
#                 'default_new_products':loc.new_products or None,
#                 'default_categ_id': loc.categ_id.id,
#                 'default_class_id': loc.clas_id.id,
#                 'default_only_stock': loc.only_stock,
#                 'close_after_process': True,
#                 }
#         }
#         
#     def onchange_code(self,cr,uid,ids,default_code,initial,final,context=None):
#         if(not default_code):
#             return {"value":{"initial":None,"final":None}}
#         return {}
#     
#     def onchange_final(self,cr,uids,ids,initial,final,context=None):
#         if(final):
#             str_final=""
#             for each in final:
#                 if(each in ('0','1','2','3','4','5','6','7','8','9')):
#                     str_final+=each
#             return {'value':{'final':str_final}}
#         return {}
#     
#     def onchange_initial(self,cr,uids,ids,initial,final,context=None):
#         if(initial):
#             str_initial=""
#             for each in initial:
#                 if(each in ('0','1','2','3','4','5','6','7','8','9')):
#                     str_initial+=each
#             return {'value':{'initial':str_initial}}
#         return {}
# straconx_stock_location_shop_parameters()