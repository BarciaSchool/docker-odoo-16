# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import psycopg2

class straconx_stock_shop(osv.osv):    
    _inherit = "stock.shop"

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
        user_database = user_id.shop_id.server_url
        shop_obj = self.pool.get('sale.shop')
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
        location_obj = self.pool.get('stock.location')
        location_ids = location_obj.search(cr,uid,[('usage','=','internal'),('company_id','=',user_id.shop_id.company_id.id),('active','=',True),('location_id','<>',None)])
        if prt_ids:
            for p in prt_ids:
                product_ids.append(p[0])
        if not product_ids:
            raise osv.except_osv('Error!', _("No existen productos para los códigos que usted selecciono."))
        for location in location_ids:
#             shop_ubication_id = location_obj.browse(cr,uid,location).location_id.id
#             shop_ids = shop_obj.search(cr,uid,[('shop_ubication_id','=',shop_ubication_id)])        
            cr.execute("""select id from sale_shop where shop_ubication_id = (select location_id from stock_location where id = %s)""",(location,))
            shop_ids =cr.fetchone()
            if shop_ids:
                shop = shop_obj.browse(cr,uid,shop_ids[0])                    
                if shop:          
                    database = shop_obj.browse(cr,uid,shop.id).server_db
                    port = shop_obj.browse(cr,uid,shop.id).server_port
                    host = shop_obj.browse(cr,uid,shop.id).server_url
                    user = shop_obj.browse(cr,uid,shop.id).login
                    password= shop_obj.browse(cr,uid,shop.id).password
                    date = time.strftime('%Y-%m-%d %H:%M:%S')
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

straconx_stock_shop()