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
import netsvc
import psycopg2
import datetime as dt 
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    _columns = {
        'confirm_transfer':fields.boolean('Confirmar Transferencia', required=False),
        }

    def confirm_resposition(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        result =  super(stock_picking, self).confirm_resposition(cr, uid, ids, context) 
        for pick in self.browse(cr, uid, ids, context=context):            
            # BASE DE DATOS DE ORIGEN
            shop_id_database = pick.shop_id.server_db
            shop_id_user = pick.shop_id.login
            shop_id_password = pick.shop_id.password
            shop_id_host=pick.shop_id.server_url
            shop_id_port=pick.shop_id.server_port
            # BASE DE DATOS DESTINO
            shop_dest_id_database = pick.shop_id_dest.server_db
            shop_dest_id_user = pick.shop_id_dest.login
            shop_dest_id_password = pick.shop_id_dest.password
            shop_dest_id_host = pick.shop_id_dest.server_url
            shop_dest_id_port=pick.shop_id_dest.server_port

            if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database:
                if not shop_id_database or not shop_dest_id_database:
                    raise osv.except_osv('Error!', _("Please, select a database."))
                if shop_id_database <> shop_dest_id_database:
                    try:
                        source_or= psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port, options='-c statement_timeout=15s')
                        source = source_or.cursor()
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_id_database,shop_id_host))

                    try:
                        conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                        conect = conection.cursor()  
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_dest_id_database,shop_dest_id_host))

                    if conect:
                        model_objs=['stock_picking','wkf_instance','wkf_workitem','stock_move']
                        for model_ids in model_objs:
                            model = model_ids
                            tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                            conect.execute(tables)
                            fields_sri_remote = conect.fetchall()
                            fields_app = ""
                            nuevo = ids[0]
                            for f in fields_sri_remote:
                                fields_app=fields_app +'"' +(f[0]) +'",'
                            fields_app = fields_app[:-1]
                            if fields_app:
                                if model == 'stock_picking':
                                    sql_fields_app = ("""select %s from %s where id='%s'"""%(fields_app,model,nuevo))                                
                                elif model== 'wkf_instance':    
                                    sql_fields_app = ("""select %s from %s where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')"""%(fields_app,model,nuevo))
                                elif model== 'wkf_workitem': 
                                    sql_fields_app = ("""select %s from %s where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')) """%(fields_app,model,nuevo))                            
                                else:
                                    sql_fields_app = ("""select %s from %s where picking_id='%s'"""%(fields_app,model,nuevo))
                                conect.execute(sql_fields_app)
                                selection_f = conect.fetchall()
                            for ins in selection_f:
                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                sql = sql.replace("None", "Null")
                                sql = sql.replace(", u'",",'")
                                source.execute(sql)
                                osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',nuevo, model, shop_id_database)
                        source_or.commit()
                    else:
                        raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))
        context.update({'active_id':ids[0],'active_model':'stock.picking','state':'draft'})
        xml_id = 'email_template_edi_picking_internal_request'
        template_ids = mod_obj.get_object_reference(cr, uid, 'stock', xml_id)
        self.pool.get('email.template').send_mail(cr,uid,template_ids[1],pick.id,False,context)                                    
        return True

#    @profile

    def action_drafted(self, cr, uid, ids, context=None):  
        mod_obj = self.pool.get('ir.model.data')
        old_pick_id = False
        if not context:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):            
            old_pick_name = 'DESP: '+ pick.name
            # BASE DE DATOS DE ORIGEN
            if pick.type=="internal":
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port     
                if shop_id_database <> shop_dest_id_database:
                    if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database:
                        if not shop_id_database or not shop_dest_id_database:
                            raise osv.except_osv('Error!', _("Please, select a database."))
                        try:
                            conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                            conect = conection.cursor()                          
                        except psycopg2.Error: 
                            _logger.exception('Connection to the database failed')
                            raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_id_database,shop_dest_id_host))
                        
                        if not old_pick_id:
                            conect.execute("""select id,state from stock_picking where name=%s and state !='cancel'""",(old_pick_name,))
                            old_pick_id = conect.fetchall()
                            
                        if old_pick_id:
                            for old in old_pick_id: 
                                conect.execute("""select id,state from stock_picking where id=%s""",(old[0],))
                                is_true = conect.fetchone()
                                if is_true:
                                    state = is_true[1]
                                    if state != 'done':
                                        conect.execute("""delete from stock_move where picking_id=%s""",(old[0],))
                                        conect.execute("""delete from stock_picking where id=%s""",(old[0],))
                                        conect.execute("""delete from wkf_workitem where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')) """,(old[0],))
                                        conect.execute("""delete from wkf_instance where res_id=%s and wkf_id =(SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')""",(old[0],))
                                        conection.commit()                            
                                    else:
                                        raise osv.except_osv('¡Error!', _("Por favor, solicitar a la tienda de destino que cambie el estado de picking de despacho a borrador"))

            pick.write({'confirm_transfer':False})  
        return super(stock_picking, self).action_drafted(cr, uid, ids, context)


    def action_drafted_transfer_in(self, cr, uid, ids, context=None):  
        mod_obj = self.pool.get('ir.model.data')
        synchro_obj = self.pool.get('base.synchro.server')
        if not context:
            context = {}
        super(stock_picking, self).action_drafted_transfer_in(cr, uid, ids, context)
        cr.commit()
        for pick in self.browse(cr, uid, ids, context=context):            
            # BASE DE DATOS DE ORIGEN
            if pick.type=="internal":
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port     
                if shop_id_database <> shop_dest_id_database:
                    if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database and cr.dbname  <>shop_dest_id_database:
                        if not shop_id_database or not shop_dest_id_database:
                            raise osv.except_osv('Error!', _("Please, select a database."))
                        source_or= psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port, options='-c statement_timeout=15s')
                        try:
                            conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                            conect = conection.cursor()
                        except psycopg2.Error: 
                            _logger.exception('Connection to the database failed')
                            raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_id_database,shop_dest_id_host))                                                  
                        if conect:
                            model_objs=['stock_picking','stock_move']
                            for model in model_objs:
                                if model =='stock_picking':                                    
                                    synchro_obj.data_upload(model, source_or, shop_id_database, conection, shop_dest_id_database, pick.id,context)
                                elif model == 'stock_move':
                                    for m in pick.move_lines: 
                                        synchro_obj.data_upload(model, source_or, shop_id_database, conection, shop_dest_id_database, m.id,context)
                        else:
                            raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))  
        return True

    def draft_validate(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        shop_obj = self.pool.get('sale.shop')
        database_local = cr.dbname
        for pick in self.browse(cr, uid, ids, context=context):
            # BASE DE DATOS DE ORIGEN
            if pick.type == 'in' and pick.international:
                if not pick.shop_id.headquarter:
                    shop_ids = shop_obj.search(cr, uid, [('headquarter', '=', True)])
                    if shop_ids:
                        shop_id_dest = shop_obj.browse(cr, uid, shop_ids[0])
                        if shop_id_dest and shop_id_dest.server_db and shop_id_dest.server_url:
                            shop_dest_id_database = shop_id_dest.server_db
                            shop_dest_id_user = shop_id_dest.login
                            shop_dest_id_password = shop_id_dest.password
                            shop_dest_id_host = shop_id_dest.server_url
                            shop_dest_id_port = shop_id_dest.server_port
                            if shop_dest_id_database != database_local:
                                try:
                                    conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password,
                                                                 host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                                    conect = conection.cursor()
                                    for m in pick.move_lines:
                                        if m.product_id:
                                            conect.execute("""update product_template set write_date = now(), standard_price=%s , state ='sellable' where"
                                            " id = (select product_tmpl_id from product_product where id =%s)""", (m.product_id.standard_price,
                                                                                                                   m.product_id.id))
                                    conection.commit()
                                except psycopg2.Error:
                                    _logger.exception('Connection to the database failed')
                                    raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.") %
                                                         (shop_dest_id_database, shop_dest_id_database))
        return super(stock_picking, self).draft_validate(cr, uid, ids, context=context)

    def action_move(self, cr, uid, ids, context=None):
        result = super(stock_picking, self).action_move(cr, uid, ids, context)
        for pick in self.browse(cr, uid, ids, context=context):
            # BASE DE DATOS DE ORIGEN
            if pick.type == "internal":
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host = pick.shop_id.server_url
                shop_id_port = pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port
     
                if shop_id_database <> shop_dest_id_database and cr.dbname <> shop_dest_id_database:
                    if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database:
                        if not shop_id_database or not shop_dest_id_database:
                            raise osv.except_osv('Error!', _("Please, select a database."))
                        source_or= psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port, options='-c statement_timeout=15s')
                        source = source_or.cursor()

                        try:
                            conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                            conect = conection.cursor()  

                        except psycopg2.Error: 
                            _logger.exception('Connection to the database failed')
                            raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_dest_id_database,shop_dest_id_host))
                            
                        define_record = ids[0]
                        nuevo_local = []
                        conect.execute("""select id from stock_picking where id=%s""",(define_record,))
                        is_true = conect.fetchone()
                        if is_true:
                            conect.execute("""delete from stock_move where picking_id=%s""",(define_record,))
                            conect.execute("""delete from stock_picking where id=%s""",(define_record,))
                            conect.execute("""delete from wkf_workitem where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')) """,(define_record,))
                            conect.execute("""delete from wkf_instance where res_id=%s and wkf_id =(SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')""",(define_record,))
                            conection.commit()                            
                        if source:
                            model_objs=['stock_move','stock_picking','wkf_instance','wkf_workitem']
                            for model_ids in model_objs:
                                model = model_ids
                                tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                                if model == 'stock_picking':
                                    sql_ex = ("""select id from %s where id='%s'"""%(model,define_record))                                
                                elif model== 'wkf_instance':    
                                    sql_ex = ("""select id from %s where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')"""%(model,define_record))
                                elif model== 'wkf_workitem': 
                                    sql_ex = ("""select id from %s where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')) """%(model,define_record))                            
                                else:
                                    sql_ex = ("""select id from %s where picking_id='%s'"""%(model,define_record))
                                source.execute(sql_ex)
                                change_local = source.fetchall()                    
                                if change_local:
                                    for clr in change_local:
                                        nuevo_local.append(clr[0])
                                if nuevo_local:
                                    for nuevo in nuevo_local:
                                        source.execute("""select * from %s where id=%s"""%(model, nuevo))
                                        old_d = source.fetchall()
                                        if old_d:
                                            new_sql = ""
                                            if old_d:
                                                fields_app = ""                                    
                                                val_update = old_d[0]                                   
                                                source.execute(tables)
                                                tables_data = source.fetchall()
                                                if tables_data:
                                                    fields_app = []
                                                    for f in tables_data:
                                                        fields_app.append(f[0]) 
                                                    for t in fields_app:
                                                        ind = fields_app.index(t)
                                                        old_d = val_update[ind]                                                
                                                        conect.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s'"""%(model,t))
                                                        type_data=conect.fetchall()
                                                        if type_data and type_data[0][0] in ('varchar','timestamp','date','text'):
                                                            update_ind = "'"+str(old_d)+"'"
                                                        else:
                                                            update_ind = str(old_d)
                                                        new_sql = new_sql +'"' +t+'"' +"=" + update_ind + ","
                                                new_sql = new_sql[:-1]
                                                new_sql = new_sql.replace("None","Null")
                                                new_sql = new_sql.replace("'Null'","Null")
                                                a = "write_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"'"
                                                b = "write_uid='1'"
                                                new_sql = new_sql.replace("write_date='Null'",a)
                                                new_sql = new_sql.replace("write_uid='Null'",b)                                                                                                                             
                                                execut_sql = ("""update %s set %s where id = %s """%(model,new_sql,nuevo)) 
                                                conect.execute(execut_sql)
                                            conection.commit()
                                    if model == 'stock_picking':
                                        update_sql = ("""update %s set write_date=now(),state='done' where id = %s """%(model,nuevo)) 
                                        conect.execute(update_sql)
                                        conection.commit()
                                        source_or.commit()
                                    elif model == 'stock_move':
                                        update_sql = ("""update %s set write_date=now(), state='done' where picking_id = %s """%(model,nuevo)) 
                                        conect.execute(update_sql)
                                    conection.commit()
                    elif shop_id_database and not shop_dest_id_database:
                        continue                    
                    else:
                        raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))                
        return True

    def action_move_in(self, cr, uid, ids, context=None):
        for pick in self.browse(cr, uid, ids, context=context):            
            # BASE DE DATOS DE ORIGEN
            if pick.type=="in":
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port    
                if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database:
                    if not shop_id_database or not shop_dest_id_database:
                        raise osv.except_osv('Error!', _("Please, select a database."))
                    try:
                        conection = psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port, options='-c statement_timeout=15s')
                        conect = conection.cursor()
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_id_database,shop_id_host))
                    try:                    
                        source_or = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                        source = source_or.cursor()
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_dest_id_database,shop_dest_id_host))
  
                    define_record = ids[0]
                    conect.execute("""select id from stock_picking where id=%s""",(define_record,))
                    is_true = conect.fetchone()
                    if is_true:
                        conect.execute("""delete from stock_move where picking_id=%s""",(define_record,))
                        conect.execute("""delete from stock_picking where id=%s""",(define_record,))
                        conect.execute("""delete from wkf_workitem where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')) """,(define_record,))
                        conect.execute("""delete from wkf_instance where res_id=%s and wkf_id =(SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')""",(define_record,))
                        conection.commit()                                                
                    if source:
                        model_objs=['stock_picking', 'stock_move','wkf_instance','wkf_workitem']
                        for model_ids in model_objs:
                            model = model_ids
                            tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                            source.execute(tables)
                            fields_sri_remote = source.fetchall()
                            fields_app = ""
                            for f in fields_sri_remote:
                                fields_app=fields_app +'"' +(f[0]) +'",'
                            fields_app = fields_app[:-1]
                            if fields_app:
                                if model == 'stock_picking':
                                    sql_fields_app = ("""select * from %s where id='%s'"""%(model,define_record))                                
                                elif model== 'wkf_instance':    
                                    sql_fields_app = ("""select * from %s where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')"""%(model,define_record))
                                elif model== 'wkf_workitem': 
                                    sql_fields_app = ("""select * from %s where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='stock.picking.basic' AND OSV='stock.picking')) """%(model,define_record))                            
                                else:
                                    sql_fields_app = ("""select * from %s where picking_id='%s'"""%(model,define_record))
                                source.execute(sql_fields_app)
                                selection_f = source.fetchall()
                            for ins in selection_f:
                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                sql = sql.replace("None", "Null")
                                sql = sql.replace(", u'",",'")
                                conect.execute(sql)
                                osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',define_record, model, shop_id_database)
                        conection.commit()
                    else:
                        raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))                
        return True

    def action_done(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        self.write(cr, uid, ids, {'state': 'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
        cr.commit()
        self.action_send_new(cr, uid, ids, context)
        context.update({'remote_db':False})
        return True

    def action_send_new(self, cr, uid, ids, context=None):
#        result =  super(stock_picking, self).action_move(cr, uid, ids, context)
        mod_obj = self.pool.get('ir.model.data')
        picking_obj = self.pool.get('stock.picking')
        synchro_obj = self.pool.get('base.synchro.server')
        act_dabase = cr.dbname
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.type == 'internal':
                # BASE DE DATOS DE ORIGEN
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port
    
                if shop_id_database <> shop_dest_id_database:
                    if not shop_id_database or not shop_dest_id_database:
                        raise osv.except_osv('Error!', _("Please, select a database."))
                    
                    try:
                        source_or= psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port, options='-c statement_timeout=15s')
                        source = source_or.cursor()
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_id_database,shop_id_host))
                    
                    try:
                        conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                        conect = conection.cursor()  
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_dest_id_database,shop_dest_id_host))
                    
                    if (pick.type=="internal" and pick.internal_out) :
                        pick = picking_obj.browse(cr,uid,ids[0])
                        if pick:
                            new_name = 'DESP: '+ pick.name
                            if new_name:
                                new_ids = picking_obj.search(cr,uid,[('name','=',new_name)])
                            if new_ids and conect:
                                nuevo = new_ids[0]                                
                                self.write(cr, uid, [nuevo], {'state':'assigned'}, context)
                                cr.commit()                               
                                pick_nuevo = picking_obj.browse(cr,uid,nuevo)                            
                                model_objs=['stock_picking','stock_move']
                                for model in model_objs:
                                    if model =='stock_picking':
                                        if shop_id_database == shop_dest_id_database:                             
                                            synchro_obj.data_download(model, source_or, shop_id_database, conection, shop_dest_id_database, pick_nuevo.id,context)
                                        else:                                        
                                            synchro_obj.data_upload(model, source_or, shop_id_database, conection, shop_dest_id_database, pick_nuevo.id,context)
                                    elif model == 'stock_move':
                                        for m in pick_nuevo.move_lines: 
                                            if shop_id_database == shop_dest_id_database:
                                                synchro_obj.data_download(model, source_or, shop_id_database, conection, shop_dest_id_database, m.id,context)                                            
                                            else:
                                                synchro_obj.data_upload(model, source_or, shop_id_database, conection, shop_dest_id_database, m.id,context)
                if pick.internal_out:
                    xml_id = 'email_template_edi_picking_internal_done'
                elif pick.internal_in:
                    xml_id = 'email_template_edi_picking_internal_receipt'
                template_ids = mod_obj.get_object_reference(cr, uid, 'stock', xml_id)
                self.pool.get('email.template').send_mail(cr,uid,template_ids[1],pick.id,False,context)                                          
            self.write(cr,uid,ids,{'confirm_transfer':True})
        return True

stock_picking()



class migrate_stock_picking(osv.osv_memory):
    _name = "migrate.stock.picking"
    _columns = {
                'picking_id': fields.many2one('stock.picking','Picking')
              }


    def action_migrate(self, cr, uid, ids, context=None):

        obj_stock_picking = self.pool.get("stock.picking")
        picking_ids_up = []
        for brw_self in self.browse(cr, uid, ids, context=context):
            picking_sql_down = ("""SELECT ID FROM STOCK_PICKING WHERE TYPE='internal' and id=%s"""%(brw_self.picking_id.id))
            picking_ids_down = cr.execute(picking_sql_down)
            picking_ids_down = cr.fetchall()
            picking_sql_up = ("""SELECT ID FROM STOCK_PICKING WHERE TYPE='internal' and state='done' and id=%s"""%(brw_self.picking_id.id))
            picking_ids_up = cr.execute(picking_sql_up)
            picking_ids_up = cr.fetchall()

            if picking_ids_down:
                picking_ids_down = picking_ids_down
            else:
                picking_ids_down =[]

            if picking_ids_up:
                picking_ids_up = picking_ids_up
            else:
                picking_ids_up =[]
                    
            ne = 0
            osv._logger.warning('Se procesarán %s transferencias hacia la tienda',len(picking_ids_up))
            for picking in picking_ids_up:
                ne = ne + 1            
                # BASE DE DATOS DE ORIGEN
                pick = obj_stock_picking.browse(cr,uid,picking[0])
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port
                if shop_id_database <> shop_dest_id_database:
                    if pick.type=="internal":
                        if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database:
                            if not shop_id_database or not shop_dest_id_database:
                                raise osv.except_osv('Error!', _("Please, select a database."))
                            source_or= psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port, options='-c statement_timeout=15s')
                            source = source_or.cursor()
                            try:
                                conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port, options='-c statement_timeout=15s')
                                conect = conection.cursor()
                            except:
                                osv._logger.warning('No hay conexión con la base de datos %s', shop_id_database)
                            define_record = pick.id
                            nuevo_local = []
                            if source:
                                model_objs=['stock_move','stock_picking']
                                for model_ids in model_objs:
                                    model = model_ids
                                    tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                                    if model == 'stock_picking':
                                        sql_ex = ("""select id from %s where id='%s'"""%(model,define_record))                                
                                    else:
                                        sql_ex = ("""select id from %s where picking_id='%s'"""%(model,define_record))
                                    source.execute(sql_ex)
                                    change_local = source.fetchall()                    
                                    if change_local:
                                        for clr in change_local:
                                            nuevo_local.append(clr[0])
                                    if nuevo_local:
                                        for nuevo in nuevo_local:
                                            source.execute("""select * from %s where id=%s"""%(model, nuevo))
                                            conect.execute("""select * from %s where id=%s"""%(model, nuevo))
                                            old_d = source.fetchall()
                                            rep_update = conect.fetchall()                                            
                                            if not rep_update:
                                                source.execute(tables)
                                                fields_sri_remote = source.fetchall()
                                                fields_app = ""
                                                for f in fields_sri_remote:
                                                    fields_app=fields_app +'"' +(f[0]) +'",'
                                                fields_app = fields_app[:-1]
                                                if fields_app:
                                                    sql_fields_app = ("""select %s from %s where id='%s'"""%(fields_app,model,nuevo))
                                                    source.execute(sql_fields_app)
                                                    selection_f = source.fetchall()
                                                for ins in selection_f:
                                                    sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                    sql = sql.replace("None", "Null")
                                                    sql = sql.replace(", u'",",'")
                                                    conect.execute(sql)     
                                                    conection.commit()
                                                    source_or.commit()                                                
                                                    osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',nuevo, model, shop_dest_id_database)            
                                            else:
                                                new_sql = ""
                                                if old_d:
                                                    fields_app = ""                                    
                                                    val_update = old_d[0]                                   
                                                    source.execute(tables)
                                                    tables_data = source.fetchall()
                                                    if tables_data:
                                                        fields_app = []
                                                        for f in tables_data:
                                                            fields_app.append(f[0]) 
                                                        for t in fields_app:
                                                            ind = fields_app.index(t)
                                                            old_d = val_update[ind]                                                
                                                            conect.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s'"""%(model,t))
                                                            type_data=conect.fetchall()
                                                            if type_data and type_data[0][0] in ('varchar','timestamp','date','text'):
                                                                update_ind = "'"+str(old_d)+"'"
                                                            else:
                                                                update_ind = str(old_d)
                                                            new_sql = new_sql +'"' +t+'"' +"=" + update_ind + ","
                                                    new_sql = new_sql[:-1]
                                                    new_sql = new_sql.replace("None","Null")
                                                    new_sql = new_sql.replace("'Null'","Null")
                                                    a = "write_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"'"
                                                    b = "write_uid='1'"
                                                    new_sql = new_sql.replace("write_date='Null'",a)
                                                    new_sql = new_sql.replace("write_uid='Null'",b)                                                                                                                             
                                                    execut_sql = ("""update %s set %s where id = %s """%(model,new_sql,nuevo)) 
                                                    conect.execute(execut_sql)
                                                    conection.commit()
                                                    source_or.commit()                                                
                                                    osv._logger.warning('El registro %s del modelo %s ha sido actualizado en la base de datos %s',nuevo, model, shop_dest_id_database)                                        
            osv._logger.warning('Se procesarán %s transferencias desde la tienda',len(picking_ids_down))
            for picking in picking_ids_down:
                ne = ne + 1            
                # BASE DE DATOS DE ORIGEN
                pick = obj_stock_picking.browse(cr,uid,picking[0])
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port
    
                if shop_id_database <> shop_dest_id_database:
                    if pick.type=="internal":
                        if shop_id_host and shop_id_database and shop_dest_id_host and shop_dest_id_database:
                            if not shop_id_database or not shop_dest_id_database:
                                raise osv.except_osv('Error!', _("Please, select a database."))
                            source_or = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port)
                            source = source_or.cursor()
                            try:
                                conection = psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port)
                                conect = conection.cursor()  
                            except:
                                osv._logger.warning('No hay conexión con la base de datos %s', shop_id_database)
                            define_record = pick.id
                            nuevo_local = []
                            if source:
                                model_objs=['stock_move','stock_picking']
                                for model_ids in model_objs:
                                    model = model_ids
                                    tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                                    if model == 'stock_picking':
                                        sql_ex = ("""select id from %s where id='%s'"""%(model,define_record))                                
                                    else:
                                        sql_ex = ("""select id from %s where picking_id='%s'"""%(model,define_record))
                                    source.execute(sql_ex)
                                    change_local = source.fetchall()                    
                                    if change_local:
                                        for clr in change_local:
                                            nuevo_local.append(clr[0])
                                    if nuevo_local:
                                        for nuevo in nuevo_local:
                                            source.execute("""select * from %s where id=%s""" % (model, nuevo))
                                            conect.execute("""select * from %s where id=%s""" % (model, nuevo))
                                            old_d = source.fetchall()
                                            rep_update = conect.fetchall()
                                            if old_d == rep_update:
                                                osv._logger.warning('El registro %s del modelo %s ya existe en la base de datos %s', nuevo, model,
                                                                    shop_id_database)
                                            elif not rep_update:
                                                source.execute(tables)
                                                fields_sri_remote = source.fetchall()
                                                fields_app = ""
                                                for f in fields_sri_remote:
                                                    fields_app = fields_app + '"' + (f[0]) + '",'
                                                fields_app = fields_app[:-1]
                                                if fields_app:
                                                    sql_fields_app = ("""select %s from %s where id='%s'""" % (fields_app, model, nuevo))
                                                    source.execute(sql_fields_app)
                                                    selection_f = source.fetchall()
                                                for ins in selection_f:
                                                    sql = ("""insert into %s (%s) values %s""" % (model, fields_app, ins))
                                                    sql = sql.replace("None", "Null")
                                                    sql = sql.replace(", u'", ",'")
                                                try:
                                                    conect.execute(sql)
                                                    osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s', nuevo,
                                                                        model, shop_id_database)
                                                    conection.commit()
                                                    source_or.commit()
                                                except:
                                                    osv._logger.warning('El registro %s del modelo %s ha tenido problema de creación'
                                                                        ' en la base de datos %s', nuevo, model, shop_id_database)
                                            else:
                                                new_sql = ""
                                                if old_d:
                                                    fields_app = ""
                                                    val_update = old_d[0]
                                                    source.execute(tables)
                                                    tables_data = source.fetchall()
                                                    if tables_data:
                                                        fields_app = []
                                                        for f in tables_data:
                                                            fields_app.append(f[0])
                                                        for t in fields_app:
                                                            ind = fields_app.index(t)
                                                            old_d = val_update[ind]
                                                            conect.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t "
                                                                            " WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid"
                                                                            " AND a.atttypid = t.oid and a.attname ='%s'""" % (model, t))
                                                            type_data = conect.fetchall()
                                                            if type_data and type_data[0][0] in ('varchar', 'timestamp', 'date', 'text'):
                                                                update_ind = "'"+str(old_d)+"'"
                                                            else:
                                                                update_ind = str(old_d)
                                                            new_sql = new_sql +'"' +t+'"' +"=" + update_ind + ","
                                                    new_sql = new_sql[:-1]
                                                    new_sql = new_sql.replace("None","Null")
                                                    new_sql = new_sql.replace("'Null'","Null")
                                                    a = "write_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"'"
                                                    b = "write_uid='1'"
                                                    new_sql = new_sql.replace("write_date='Null'",a)
                                                    new_sql = new_sql.replace("write_uid='Null'",b)                                                                                                                             
                                                    execut_sql = ("""update %s set %s where id = %s """%(model,new_sql,nuevo)) 
                                                    try:
                                                        conect.execute(execut_sql)
                                                        conection.commit()
                                                        source_or.commit()                                                
                                                        osv._logger.warning('El registro %s del modelo %s ha sido actualizado en la base de datos %s',nuevo, model, shop_id_database)
                                                    except:
                                                        osv._logger.warning('El registro %s del modelo %s ha tenido problema de actualización en la base de datos %s',nuevo, model, shop_id_database)
                    else:
                        raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))                
            source_or.commit()
            conection.commit()
            return {'type': 'ir.actions.act_window_close'}
migrate_stock_picking()
