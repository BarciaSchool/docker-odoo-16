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

from osv import fields,osv
from tools.translate import _
#from sql_db_remote import get_connect_server
import psycopg2
import time
import logging
import datetime as dt 
from datetime import timedelta
import base64
import subprocess
import straconx_base_synchro as bso


class verified_data_info(osv.osv):
    _name = 'verified.data'
    
    _columns = {'doc_id': fields.integer('Documento'),
                'model': fields.char('Modelo', size=40),
                'partner_id': fields.many2one('res.partner','Empresa'),
                'data_id': fields.integer('Documento Electrónico'),
                'email_send': fields.boolean('Enviado Correo'),
                'state': fields.selection([('done','Listo'),('review','Revisar')],'Estado')                
                }

    def verified_data(self, cr, uid, context=None):
        if not context:
            context = {}
        base_synchro = self.pool.get('base.synchro.server')
        ir_attachment = self.pool.get('ir.attachment')
        ids = base_synchro.search(cr,uid,[]) 
        if ids:
            pool = cr.dbname
            host_pool = 'localhost'
            db = base_synchro.browse(cr,uid,ids[0])
            database = db.server_db
            if not database:
                raise osv.except_osv('Error!', _("Please, select a database."))
            user = db.login
            password = db.password
            host=db.server_url
            port=db.server_port                
        try:            
            source_or= psycopg2.connect(database=pool, user=user, password=password, host=host_pool, port=port, options='-c statement_timeout=15s')           
            conection = psycopg2.connect(database=database, user=user, password=password, host=host, port=port, options='-c statement_timeout=15s')           

            source = source_or.cursor()
            conect = conection.cursor()    
                        
            conect.execute("""select id, res_model, partner_id from ir_attachment where electronic =True order by id""")
            conect_ids = conect.fetchall()
            if conect_ids:
                for data in conect_ids:
                    # VERIFICA SI EXISTE EN EL IR_ATTACHMENT DE LA BASE DE CLIENTES 
                    if data[2]==114948:
                        print "revisa"
                    source.execute("""select data_id from verified_data where state ='done' and data_id =%s""",(data[0],))
                    se = source.fetchone()
                    if se is None: 
                        source.execute("""select id from ir_attachment where electronic =True and id =%s""",(data[0],)) 
                        vd = source.fetchone()
                        if vd:
                            vd_id = ir_attachment.browse(cr,uid,vd[0])
                            model = vd_id.res_model
                            model_send = model.replace('.','_')  
                            define_record = vd_id.id
                            if vd_id and len(vd_id.number_auth)==37:
                                doc_id = self.pool.get(vd_id.res_model).browse(cr,uid,vd_id.res_id)
                                if not doc_id:
                                    if model == 'account.invoice':                                        
                                        conect.execute("""select id, move_id, picking_id from account_invoice where id =%s""",(vd_id.res_id,))
                                        ai_id = cr.fetchone()
                                        self.data_download(model_send,source_or,pool,conection,database,define_record,context)
                                        partner_id = vd[2]
                                        vals = {
                                            'data_id': vd_id.id,
                                            'doc_id': doc_id.id ,
                                            'model': vd_id.model,
                                            'partner_id': partner_id,
                                            'email_send': False,
                                            'state': 'review'
                                                }
                                source.execute("""select data_id from verified_data where state ='done' and data_id =%s""",(vd_id.id,))
                                verd = source.fetchone()
                                if verd is None:
                                    self.data_download('ir_attachment',source_or,pool,conection,database,define_record,context)
                                    print "Ok"
#                            else:
#                                if vd_id.active == True:
        except:
            print data



    def data_download(self,model,source_or,pool,conection,database,define_record,context):
        source = source_or.cursor()
        conect = conection.cursor()            
        tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
        try:
            if define_record: 
                source.execute("""select * from %s where id=%s order by id"""%(model, define_record))
                conect.execute("""select * from %s where id=%s order by id"""%(model, define_record))
                old_d = source.fetchall()
                rep_update = conect.fetchall()
                # Si no existe, lo inserta mediante insert into.        
                if not old_d:
                    ins = []
                    conect.execute(tables)
                    tables_data = conect.fetchall()
                    if tables_data:
                        fields_app = []
                        for f in tables_data:
                            t_id = f[0] 
                            fields_app.append('"'+t_id+'"')
                        if fields_app:
                            sql_fields_app = ("""select * from %s where id='%s'"""%(model,define_record))
                            conect.execute(sql_fields_app)
                            selection_f = conect.fetchall()
                        for t in fields_app:
                            ind = fields_app.index(t)
                            old_d = selection_f[0][ind]                                                
                            conect.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s' """%(model,t.replace('"',"")))
                            type_data=conect.fetchall()                    
                            if type_data and type_data[0][0] in ('varchar','text'):
                                if old_d:
                                    com = "'"
                                    com2 = '"'
                                    new_d = old_d.replace(com,com2)
                                    old_d = new_d                                                             
                                update_ind = str(old_d)
                            elif type_data and type_data[0][0] in ('date','timestamp'):
                                update_ind = str(old_d)
                            elif type_data and type_data[0][0] =='bytea':
                                if old_d:
                                    old_d = base64.b64decode(old_d)
                                    old_d = base64.b64encode(old_d)
                                else:
                                    update_ind = "None"                                
                            else:
                                update_ind = str(old_d)
                            ins.append(update_ind)
                    fields_sri_remote = fields_app
                    fields_app = ""
                    for f in fields_sri_remote:
                        fields_app=fields_app+'"'+(f) +'",'
                    fields_app = fields_app[:-1]
                    if ins:
                        sql=("""insert into %s (%s) values %s"""%(model,fields_app,tuple(ins)))
                        sql = sql.replace("'None'", "Null")
                        sql = sql.replace(", u'",",'")
                        sql = sql.replace('""','"')
                        source.execute(sql)     
                    source_or.commit()
                    conection.commit()
                    osv._logger.warning('El registro %s del modelo %s ha sido descargado en la base de datos %s',define_record, model, pool)
                # Si existe, actualiza los valores sobreescribiendo la base de destino.        
                elif old_d and rep_update and not old_d == rep_update:
                    new_sql = ""
                    if old_d:
                        fields_app = ""                                    
                        if rep_update:
                            val_update = rep_update[0]                                                        
                        conect.execute(tables)
                        tables_data = conect.fetchall()
                        if tables_data:
                            fields_app = []
                            for f in tables_data:
                                fields_app.append('"'+f[0]+'"') 
                            for t in fields_app:
                                ind = fields_app.index(t)
                                old_d = val_update[ind]                                                
                                conect.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s' """%(model,t.replace('"',"")))
                                type_data=conect.fetchall()
                                if type_data and type_data[0][0] in ('varchar','timestamp','date','text'):
                                    if old_d:
                                        com = "'"
                                        com2 = '"'
                                        new_d = old_d.replace(com,com2)
                                        old_d = new_d
                                    update_ind = "'"+str(old_d)+"'"
                                elif type_data and type_data[0][0] =='bytea':
                                    if old_d:
                                        old_d = base64.b64decode(old_d)
                                        old_d = base64.b64encode(old_d)
                                        update_ind = "'"+old_d+"'"
                                    else:
                                        update_ind = "None"
                                else:
                                    update_ind = str(old_d)
                                new_sql = new_sql + t +"=" + str(update_ind) + ","
                        new_sql = new_sql[:-1]
                        new_sql = new_sql.replace("None","Null")
                        new_sql = new_sql.replace("'Null'","Null")
                        a = "write_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"'"
                        b = "write_uid='1'"
                        new_sql = new_sql.replace("write_date='Null'",a)
                        new_sql = new_sql.replace("write_uid='Null'",b)                                                                                                                             
                        execut_sql = ("""update %s set %s where id = %s """%(model,new_sql,define_record))
                        source.execute(execut_sql)
                        source_or.commit()
                        conection.commit()
                        osv._logger.warning('El registro %s del modelo %s ha sido modificado vía descarga en la base de datos %s',define_record, model, pool)
            return True
        except psycopg2.Error, e:
            osv._logger.warning('Revisar error por id %s',define_record)
            raise osv.except_osv('Error!', _("Could not establish the connection : %s" %e))


verified_data_info()