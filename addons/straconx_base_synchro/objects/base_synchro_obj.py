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

_logger = logging.getLogger(__name__)


def compare_listcomp(x, y):
    return set(x).intersection(y)


def compare_unique(x, y):
    return list(set(x) & set(set(x) ^ set(y)))


def merge_unique(x, y):
    return list(set(x + y))


def eliminarAcentos(cadena):

    d = {'\xc1': 'A',
         '\xc9': 'E',
         '\xcd': 'I',
         '\xd3': 'O',
         '\xda': 'U',
         '\xdc': 'U',
         '\xd1': 'N',
         '\xc7': 'C',
         '\xed': 'i',
         '\xf3': 'o',
         '\xf1': 'n',
         '\xe7': 'c',
         '\xba': '',
         '\xb0': '',
         '\x3a': '',
         '\xe1': 'a',
         '\xe2': 'a',
         '\xe3': 'a',
         '\xe4': 'a',
         '\xe5': 'a',
         '\xe8': 'e',
         '\xe9': 'e',
         '\xea': 'e',
         '\xeb': 'e',
         '\xec': 'i',
         '\xed': 'i',
         '\xee': 'i',
         '\xef': 'i',
         '\xf2': 'o',
         '\xf3': 'o',
         '\xf4': 'o',
         '\xf5': 'o',
         '\xf0': 'o',
         '\xf9': 'u',
         '\xfa': 'u',
         '\xfb': 'u',
         '\xfc': 'u',
         '\xe5': 'a'}

    nueva_cadena = cadena
    for c in d.keys():
        nueva_cadena = nueva_cadena.replace(c, d[c])

    auxiliar = nueva_cadena.encode('utf-8')
    return auxiliar


class base_synchro_server(osv.osv):
    '''Class to store the information regarding server'''
    _name = "base.synchro.server"
    _description = "Synchronized server"
    _columns = {
        'name': fields.char('Server name', size=64, required=True),
        'server_url': fields.char('Server URL', size=64, required=True),
        'server_port': fields.integer('Server Port', size=64, required=True),
        'server_db': fields.char('Server Database', size=64, required=True),
        'login': fields.char('User Name', size=50, required=True),
        'password': fields.char('Password', size=64, required=True),
        'last_synchro': fields.datetime('Process Date'),
        'active': fields.boolean('Active'),
        'obj_ids': fields.one2many('base.synchro.obj', 'server_id', 'Models', ondelete='cascade'),
        'obj_without_sync': fields.many2many('ir.model', 'rel_synchro_model', 'synchro_server_id', 'model_id', 'Objects without synchronize'),
    }
    _defaults = {
        'server_port': lambda *args: 5432,
        'active': True,
    }

    def init(self, cr):
        prefix = cr.dbname[-3:]
        try:
            prefix = int(filter(str.isdigit, prefix))
            seq = prefix * 1e8
            sql_exec = "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"
            cr.execute(sql_exec)
            tables_ids = cr.fetchall()
            if tables_ids and prefix:
                for table_name in tables_ids:
                    table_name = table_name[0]
                    cr.execute("""SELECT nextval(%s)""", (table_name,))
                    last_value = cr.fetchone()
                    last_value = int(last_value[0])
                    if last_value and last_value > 0:
                        if last_value < seq:
                            new_value = last_value + seq
                            cr.execute("SELECT setval(%s, %s)", (table_name, int(new_value)))
        except:
            return True
        return True

    def connection(self, cr, uid, ids, context=None):
        try:
            pool = cr.dbname
            db = self.browse(cr, uid, ids[0])
            database = db.server_db
            if not database:
                raise osv.except_osv('Error!', _("Please, select a database."))
            user = db.login
            password = db.password
            host = db.server_url
            port = db.server_port
            conection = psycopg2.connect(database=database, user=user, password=password, host=host, port=port, options='-c statement_timeout=15s')
            return conection
        except psycopg2.Error, e:
            raise osv.except_osv('Error!', _("Could not establish the connection : %s" % e))

    def check_connection(self, cr, uid, ids, context=None):
        for server in self.browse(cr, uid, ids, context):
            self.connection(cr, uid, ids, context)
        raise osv.except_osv(_("Message!"), _("Connection test succeeded!"))

    def data_upload(self, model, source_or, pool, conection, database, nuevo, context):
        source = source_or.cursor()
        conect = conection.cursor()
        tables = ("SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s'"
                  "AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid " % (model, ))
        # Verifica si existe, si hay algún cambio lo escribe mediante update
        # Importante, si la acción está definida como u, el remoto sobrescribirá la versión del base remota
        source.execute("""select * from %s where id=%s""" % (model, nuevo))
        conect.execute("""select * from %s where id=%s""" % (model, nuevo))
        old_d = source.fetchall()
        rep_update = conect.fetchall()
        osv._logger.warning('Revisado el registro %s del modelo %s', nuevo, model)
        if old_d != rep_update and rep_update:
            new_sql = ""
            if old_d:
                fields_app = ""
                if rep_update:
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
                        conect.execute("SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s'"
                                       "AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s'""" % (model, t))
                        type_data = conect.fetchall()
                        if type_data and type_data[0][0] in ('varchar', 'text'):
                            if old_d:
                                com = "'"
                                com2 = '"'
                                new_d = old_d.replace(com, com2)
                                old_d = new_d
                            update_ind = "'"+str(old_d).encode("utf-8")+"'"
                        elif type_data and type_data[0][0] in ('date', 'timestamp'):
                            update_ind = "'"+str(old_d)+"'"
                        elif type_data and type_data[0][0] == 'bytea':
                            if old_d:
                                try:
                                    old_d = base64.b64decode(old_d)
                                    old_d = base64.b64encode(old_d)
                                    update_ind = "'"+old_d+"'"
                                except:
                                    update_ind = "None"
                            else:
                                update_ind = "None"
                        else:
                            update_ind = str(old_d).encode("utf-8")
                        new_sql = new_sql + '"' + t + '"' + "=" + update_ind + ","
                new_sql = new_sql[:-1]
                new_sql = new_sql.replace("None", "Null")
                new_sql = new_sql.replace("'Null'", "Null")
                a = "write_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"'"
                b = "write_uid='1'"
                new_sql = new_sql.replace("write_date='Null'", a)
                new_sql = new_sql.replace("write_uid='Null'", b)
                execut_sql = ("""update %s set %s where id = %s """ % (model, new_sql, nuevo))
                conect.execute(execut_sql)
                source_or.commit()
                conection.commit()
            else:
                ins = []
                source.execute(tables)
                tables_data = source.fetchall()
                if tables_data:
                    fields_app = []
                    for f in tables_data:
                        t_id = f[0]
                        fields_app.append(t_id)
                    if fields_app:
                        sql_fields_app = ("""select * from %s where id='%s'""" % (model, nuevo))
                        source.execute(sql_fields_app)
                        selection_f = source.fetchall()
                    for t in fields_app:
                        ind = fields_app.index(t)
                        old_d = selection_f[0][ind]
                        source.execute("SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 "
                                       "AND a.attrelid=c.oid AND a.atttypid = t.oid and a.attname ='%s'" % (model, t))
                        type_data = source.fetchall()
                        if type_data and type_data[0][0] in ('varchar', 'text'):
                            if old_d:
                                com = "'"
                                com2 = '"'
                                new_d = old_d.replace(com, com2)
                                old_d = new_d
                            update_ind = str(old_d).encode("utf-8")
                        elif type_data and type_data[0][0] in ('date', 'timestamp'):
                            update_ind = str(old_d)
                        elif type_data and type_data[0][0] == 'bytea':
                            if old_d:
                                try:
                                    old_d = base64.b64decode(old_d)
                                    update_ind = base64.b64encode(old_d)
                                except:
                                    update_ind = "None"
                            else:
                                update_ind = "None"
                        else:
                            update_ind = str(old_d).encode("utf-8")
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
                    conect.execute(sql)     
                source_or.commit()
                conection.commit()
                osv._logger.warning('El registro %s del modelo %s ha sido modificado vía carga en la base de datos %s',nuevo, model, database)
        elif old_d and not rep_update:
            ins = []
            source.execute(tables)
            tables_data = source.fetchall()
            if tables_data:
                fields_app = []
                for f in tables_data:
                    t_id = f[0] 
                    fields_app.append(t_id)
                if fields_app:
                    sql_fields_app = ("""select * from %s where id='%s'"""%(model,nuevo))
                    source.execute(sql_fields_app)
                    selection_f = source.fetchall()
                for t in fields_app:
                    ind = fields_app.index(t)
                    old_d = selection_f[0][ind]                                                
                    source.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s'"""%(model,t))
                    type_data=source.fetchall()                    
                    if type_data and type_data[0][0] in ('varchar','text'):
                        if old_d:
                            com = "'"
                            com2 = '"'
                            new_d = old_d.replace(com,com2)
                            old_d = new_d
                        update_ind = str(old_d).encode("utf-8")
                    elif type_data and type_data[0][0] in ('date','timestamp'):
                        update_ind = str(old_d).encode("utf-8")
                    elif type_data and type_data[0][0] =='bytea':
                        if old_d:
                            try:
                                old_d = base64.b64decode(old_d)
                                update_ind = base64.b64encode(old_d)
                            except:
                                update_ind = "None"    
                        else:
                            update_ind = "None"
                    else:
                        update_ind = str(old_d).encode("utf-8")
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
                conect.execute(sql)     
            osv._logger.warning('El registro %s del modelo %s ha sido cargado en la base de datos %s',nuevo, model, database)                       
        source_or.commit()
        conection.commit()
        return True


    def data_download(self,model,source_or,pool,conection,database,define_record,context):
        source = source_or.cursor()
        conect = conection.cursor()            
        tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
        osv._logger.warning('El registro %s del modelo %s se esta evaluando',define_record, model)
        osv._logger.warning('Revisado el registro %s del modelo %s',define_record, model)
        try:
            if define_record: 
                source.execute("""select * from %s where id=%s order by id"""%(model, define_record))
                conect.execute("""select * from %s where id=%s order by id"""%(model, define_record))
                old_d = source.fetchall()
                rep_update = conect.fetchall()
                # Si no existe, lo crea mediante insert into.        
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
                        if selection_f:
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
                                    update_ind = str(old_d).encode("utf-8")
                                elif type_data and type_data[0][0] in ('date','timestamp'):
                                    update_ind = str(old_d)
                                elif type_data and type_data[0][0] =='bytea':
                                    if old_d:
                                        try:
                                            old_d = base64.b64decode(old_d)
                                            update_ind = base64.b64encode(old_d)
                                        except:
                                            update_ind = "None"
                                    else:
                                        update_ind = "None"
                                else:
                                    update_ind = str(old_d)
                                ins.append(update_ind)
                        fields_sri_remote = fields_app
                        fields_app = ""
                        for f in fields_sri_remote:
                            fields_app = fields_app+'"'+(f) + '",'
                        fields_app = fields_app[:-1]
                        if ins:
                            sql = ("""insert into %s (%s) values %s""" % (model, fields_app, tuple(ins)))
                            sql = sql.replace("'None'", "Null")
                            sql = sql.replace(", u'", ",'")
                            sql = sql.replace('""', '"')
                            source.execute(sql)
                        source_or.commit()
                        conection.commit()
                        osv._logger.warning('El registro %s del modelo %s ha sido descargado en la base de datos %s', define_record, model, pool)
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
                                fields_app.append('"' + f[0] + '"')
                            for t in fields_app:
                                ind = fields_app.index(t)
                                old_d = val_update[ind]
                                conect.execute("SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0"
                                               "AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s' " % (model, t.replace('"', "")))
                                type_data = conect.fetchall()
                                if type_data and type_data[0][0] in ('varchar', 'timestamp', 'date', 'text'):
                                    if old_d:
                                        com = "'"
                                        com2 = '"'
                                        new_d = old_d.replace(com, com2)
                                        old_d = new_d
                                    update_ind = "'"+str(old_d)+"'"
                                elif type_data and type_data[0][0] == 'bytea':
                                    if old_d:
                                        try:
                                            old_d = base64.b64decode(old_d)
                                            old_d = base64.b64encode(old_d)
                                            update_ind = "'"+old_d+"'"
                                        except:
                                            update_ind = "None"
                                    else:
                                        update_ind = "None"
                                else:
                                    update_ind = str(old_d).encode("utf-8")
                                new_sql = new_sql + t + "=" + str(update_ind) + ","
                        new_sql = new_sql[:-1]
                        new_sql = new_sql.replace("None", "Null")
                        new_sql = new_sql.replace("'Null'", "Null")
                        a = "write_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"'"
                        b = "write_uid='1'"
                        new_sql = new_sql.replace("write_date='Null'", a)
                        new_sql = new_sql.replace("write_uid='Null'", b)
                        execut_sql = ("""update %s set %s where id = %s """ % (model, new_sql, define_record))
                        source.execute(execut_sql)
                        source_or.commit()
                        conection.commit()
                        osv._logger.warning('El registro %s del modelo %s ha sido modificado vía descarga en la base de datos %s',
                                            define_record, model, pool)
            return True
        except psycopg2.Error, e:
            osv._logger.warning('Revisar error por id %s del modelo %s', define_record, model)
            raise osv.except_osv('Error!', _("Could not establish the connection : %s" % e))

    def data_both(self, model, source_or, pool, conection, database, review_ids, context):
        source = source_or.cursor()
        conect = conection.cursor()
        if review_ids:
            for nuevo in review_ids:
                source.execute("""select id,write_date,create_date from %s where id=%s""" % (model, nuevo))
                conect.execute("""select id,write_date,create_date from %s where id=%s""" % (model, nuevo))
                source_d = source.fetchone()
                conect_d = conect.fetchone()
                if not source_d:
                    self.data_download(model, source_or, pool, conection, database, nuevo, context)
                elif not conect_d:
                    self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                elif source_d and conect_d and source_d == conect_d:
                    continue
                elif source_d and conect_d and source_d != conect_d:
                    source_id = source_d[0]
                    conect_id = conect_d[0]
                    source_date = source_d[1]
                    conect_date = conect_d[1]
                    source_create_date = source_d[2]
                    conect_create_date = conect_d[2]
                    if source_id != conect_id:
                        if source_create_date and source_date and not conect_date:
                            self.data_download(model, source_or, pool, conection, database, nuevo, context)
                        elif source_create_date and not source_date and conect_create_date:
                            self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                        elif source_create_date and not source_date and conect_date:
                            self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                        elif not source_create_date and not conect_create_date:
                            if source_date > conect_date:
                                self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                            elif source_date < conect_date:
                                self.data_download(model, source_or, pool, conection, database, nuevo, context)
                        elif source_date > conect_date:
                            self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                        elif source_date < conect_date:
                            self.data_download(model, source_or, pool, conection, database, nuevo, context)
                    if source_id == conect_id and source_create_date == conect_create_date:
                        if source_date > conect_date:
                            self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                        elif source_date < conect_date:
                            self.data_download(model, source_or, pool, conection, database, nuevo, context)
            return True

    def change_partner_info(self, host_conection, database, old_id, new_id):

        if host_conection:
            host = host_conection.cursor()
            host.execute("UPDATE STOCK_PICKING SET WRITE_DATE = now(),PARTNER_ID = %s WHERE PARTNER_ID = %s", (old_id, new_id))
            host.execute("UPDATE STOCK_MOVE SET WRITE_DATE = now(),PARTNER_ID = %s WHERE PARTNER_ID = %s", (old_id, new_id))
            host.execute("UPDATE ACCOUNT_INVOICE SET WRITE_DATE = now(),PARTNER_ID = %s WHERE PARTNER_ID = %s", (old_id, new_id))
            host.execute("UPDATE ACCOUNT_INVOICE_LINE SET WRITE_DATE = now(),PARTNER_ID = %s WHERE PARTNER_ID = %s", (old_id, new_id))
            host.execute("UPDATE ACCOUNT_VOUCHER SET WRITE_DATE = now(), PARTNER_ID = %s WHERE PARTNER_ID= %s", (old_id, new_id))
            host.execute("UPDATE ACCOUNT_PAYMENTS SET WRITE_DATE = now(), PARTNER_ID = %s WHERE PARTNER_ID= %s", (old_id, new_id))
            host.execute("UPDATE IR_ATTACHMENT SET WRITE_DATE = now(), PARTNER_ID = %s WHERE PARTNER_ID= %s", (old_id, new_id))
            host.execute("UPDATE ACCOUNT_MOVE SET WRITE_DATE = now(),PARTNER_ID = %s WHERE PARTNER_ID = %s", (old_id, new_id))
            host.execute("UPDATE ACCOUNT_MOVE_LINE SET WRITE_DATE = now(),PARTNER_ID = %s WHERE PARTNER_ID = %s", (old_id, new_id))
            host.execute("UPDATE RES_PARTNER_ADDRESS SET WRITE_DATE = now(), PARTNER_ID = %s WHERE PARTNER_ID= %s", (old_id, new_id))
            host.execute("UPDATE RES_PARTNER SET WRITE_DATE = now(), ID = %s WHERE ID= %s", (old_id, new_id))
        return True

    def compare_partner(self, model, source_or, pool, conection, database, review_ids, context):

        source = source_or.cursor()
        conect = conection.cursor()

        if review_ids:
            for nuevo in review_ids:
                osv._logger.warning('Revisando el id %s de res_parter', nuevo)
                source.execute("""select vat,id,write_date from %s where id =%s""" % (model, nuevo))
                conect.execute("""select vat,id,write_date from %s where id =%s""" % (model, nuevo))
                source_d = source.fetchone()
                conect_d = conect.fetchone()

                if not source_d and conect_d:
                    vat = conect_d[0]
                    new_id = conect_d[1]
                    source.execute("""select id from %s where vat='%s'""" % (model, vat))
                    old_id = source.fetchone()
                    if old_id:
                        self.change_partner_info(source_or, pool, old_id[0], new_id)
                    else:
                        self.data_download(model, source_or, pool, conection, database, nuevo, context)

                elif not conect_d and source_d:
                    vat = source_d[0]
                    new_id = source_d[1]
                    conect.execute("""select id from %s where vat='%s'""" % (model, vat))
                    old_id = conect.fetchone()
                    if old_id:
                        self.change_partner_info(conection, database, old_id[0], new_id)
                    else:
                        self.data_upload(model, source_or, pool, conection, database, nuevo, context)

                elif source_d != conect_d:
                    source_id = source_d[1]
                    conect_id = conect_d[1]
                    source_date = source_d[2]
                    conect_date = conect_d[2]

                    if source_id != conect_id:
                        if source_date > conect_date:
                            self.change_partner_info(source_or, pool, conect_id, source_id)
                        elif source_date < conect_date:
                            self.change_partner_info(source_or, pool, source_id, conect_id)

                    if source_id == conect_id and source_date != conect_date:
                        if source_date > conect_date:
                            self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                        elif source_date < conect_date:
                            self.data_download(model, source_or, pool, conection, database, nuevo, context)
            return True

    def write_sql_servers(self, cr, uid, ids, context=None):
        pool = cr.dbname
        host_pool = 'localhost'
        db = self.browse(cr, uid, ids[0])
        database = db.server_db
        mod_obj = self.pool.get('ir.model.data')
        if not database:
            raise osv.except_osv('Error!', _("Please, select a database."))
        user = db.login
        password = db.password
        host = db.server_url
        port = db.server_port
        mistakes = []
        if not context:
            context = {}
        date_synchro = dt.datetime.strptime(db.last_synchro, '%Y-%m-%d %H:%M:%S') - timedelta(hours=1)
#        date_synchro = (db.last_synchro - timedelta(hours=1)).strftime('%Y-%m-%d')
#        last_synchro = date_synchro
        try:
            source_or = psycopg2.connect(database=pool, user=user, password=password, host=host_pool, port=port, options='-c statement_timeout=600s')
            source = source_or.cursor()
            try:
                conection = psycopg2.connect(database=database, user=user, password=password, host=host,
                                             port=port, options='-c statement_timeout=600s')
                conect = conection.cursor()
            except psycopg2.Error:
                _logger.exception('Connection to the database failed')
                raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.") % (database, host))

            if conection:
                for model_ids in db.obj_ids:
                    model = model_ids.model_id
                    model = model.replace(".", "_")
                    try:
                        search_shop_id = False
                        if model_ids.synchronize_date:
                            last_synchro = dt.datetime.strptime(model_ids.synchronize_date, '%Y-%m-%d %H:%M:%S') - timedelta(minutes=30)
                        else:
                            last_synchro = dt.datetime.strptime(db.last_synchro, '%Y-%m-%d %H:%M:%S') - timedelta(minutes=30)

                        osv._logger.warning('Revisando el modelo %s en la base de datos %s', model, pool)
                        tables = ("SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0"
                                  " AND a.attrelid = c.oid AND a.atttypid = t.oid " % (model,))
                        source.execute(tables)
                        tables_sql = source.fetchall()
                        for campo in tables_sql:
                            if campo[0] == "shop_id":
                                search_shop_id = True
                        nuevo_remote = []
                        nuevo_local = []
                        if model_ids.action == 'd':
                            shop_obj = self.pool.get('sale.shop')
                            shop_id_local_ids = shop_obj.search(cr, uid, [('server_db', '=', pool)])
                            shop_id = shop_obj.browse(cr,uid,shop_id_local_ids[-1])
                            shop_id_remote_ids = self.pool.get('sale.shop').search(cr,uid,[('server_db','=',database)])
                            shop_id_remote = shop_obj.browse(cr,uid,shop_id_remote_ids[0])
                            if model in ('account_invoice','account_move','account_move_line','account_voucher','account_bank_statement','account_payments'):
                                sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and state != 'draft' and shop_id = %s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                            elif model in ('account_bank_statement_line'):
                                sql_ex = ("""select absl.id from %s absl left join account_bank_statement abs on abs.id = absl.statement_id where (absl.create_date >='%s' or absl.write_date >='%s') and abs.state != 'draft' and abs.shop_id = %s order by id"""%(model,last_synchro,last_synchro,shop_id.id))                            
                            elif model=='res_users':
                                sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            else:
                                if search_shop_id:
                                    sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                else:
                                    if model == 'account_invoice_line':
                                        sql_ex = ("""select ail.id from %s ail left join account_invoice ai on ai.id= ail.invoice_id where (ail.create_date >='%s' or ail.write_date >='%s') and ai.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model == 'account_move_line':
                                        sql_ex = ("""select aml.id from %s aml left join account_move am on am.id= aml.move_id where (aml.create_date >='%s' or aml.write_date >='%s') and am.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model == 'account_voucher_line':
                                        sql_ex = ("""select avl.id from %s avl left join account_voucher av on av.id= avl.voucher_id where (avl.create_date >='%s' or avl.write_date >='%s') and av.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model=='res_users':
                                        sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                                    else:
                                        sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            conect.execute(sql_ex)
                            change_remote = conect.fetchall()                    
                            if change_remote:
                                for clr in change_remote:
                                    nuevo_remote.append(clr[0])
                            if nuevo_remote:
                                nuevo_remote.sort()
                                for define_record in nuevo_remote:
                                    self.data_download(model, source_or, pool, conection, database, define_record, context)      
                                    source_or.commit()
                                    if model =='product_product':
                                        source.execute("""select tax_id from product_taxes_rel where prod_id = (select product_tmpl_id from product_product where id = %s)"""%(define_record))
                                        tax_sale = source.fetchall()
                                        if not tax_sale:
                                            conect.execute("""select tax_id from product_taxes_rel where prod_id  = (select product_tmpl_id from product_product where id = %s)"""%(define_record))
                                            taxes = conect.fetchall()
                                            for t in taxes:
                                                source.execute("""insert into product_taxes_rel (prod_id, tax_id) values ((select product_tmpl_id from product_product where id = %s),%s)"""%(define_record,t[0]))
                                        source.execute("""select tax_id from product_supplier_taxes_rel where prod_id = (select product_tmpl_id from product_product where id = %s)"""%(define_record))
                                        tax_purc = source.fetchall()
                                        if not tax_purc:
                                            conect.execute("""select tax_id from product_supplier_taxes_rel where prod_id  = (select product_tmpl_id from product_product where id = %s)"""%(define_record))
                                            taxes = conect.fetchall()
                                            for t in taxes:
                                                tax_purchase = """insert into product_supplier_taxes_rel (prod_id, tax_id) values ((select product_tmpl_id from product_product where id = %s),%s)"""%(define_record,t[0])
                                                source.execute(tax_purchase)
                                        source.execute("""select id from product_ubication where product_id = %s"""%(define_record))
                                        product_ubication = source.fetchall()
                                        if product_ubication:
                                            for p in product_ubication:
                                                self.data_download('product_ubication', source_or, pool, conection, database, p[0], context)

                                        source.execute("""SELECT product_id FROM product_images where product_id = %s"""%(define_record))                                
                                        images = source.fetchall()
                                        if not images:
                                            conect.execute("""SELECT id FROM product_images where product_id = %s"""%(define_record))
                                            images_link = conect.fetchall()
                                            images_pool = self.pool.get('product.images')
                                            for i in images_link:                        
                                                images = images_pool.browse(cr,uid,i[0])
                                                if images:
                                                    if images.file_db_store:                                            
                                                        picture = psycopg2.Binary(images.file_db_store)
                                                    else:
                                                        picture = "Null"                
                                                    source.execute("""INSERT INTO PRODUCT_IMAGES(id, file_db_store,name, url, extention, comments, link, product_id, main) VALUES(%s,%s,'%s','%s','%s','%s',%s,%s,%s )"""%(images.id, picture,images.name, images.url, images.extention, images.comments, images.link, define_record, images.main))                                      
                                source_or.commit()
                            self.pool.get('base.synchro.obj').write(cr,uid,model_ids.id,{'synchronize_date':time.strftime('%Y-%m-%d %H:%M:%S')})                    
                            cr.commit()

                        elif model_ids.action=='u':
                            shop_obj = self.pool.get('sale.shop')
                            shop_id_local_ids = shop_obj.search(cr,uid,[('server_db','=',pool)])
                            shop_id = shop_obj.browse(cr,uid,shop_id_local_ids[-1])
                            shop_id_remote_ids = self.pool.get('sale.shop').search(cr,uid,[('server_db','=',database)])
                            shop_id_remote = shop_obj.browse(cr,uid,shop_id_remote_ids[0])
                            if model in ('account_invoice','account_move','account_move_line','account_voucher','account_bank_statement','account_payments'):
                                sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and state != 'draft' and shop_id = %s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                            elif model in ('account_bank_statement_line'):
                                sql_ex = ("""select absl.id from %s absl left join account_bank_statement abs on abs.id = absl.statement_id where (absl.create_date >='%s' or absl.write_date >='%s') and abs.state != 'draft' and abs.shop_id = %s order by id"""%(model,last_synchro,last_synchro,shop_id.id))                            
                            elif model=='res_users':
                                sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            else:
                                if search_shop_id:
                                    sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                else:                                
                                    if model == 'account_invoice_line':
                                        sql_ex = ("""select ail.id from %s ail left join account_invoice ai on ai.id= ail.invoice_id where (ail.create_date >='%s' or ail.write_date >='%s') and ai.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model == 'account_move_line':
                                        sql_ex = ("""select aml.id from %s aml left join account_move am on am.id= aml.move_id where (aml.create_date >='%s' or aml.write_date >='%s') and am.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model == 'account_voucher_line':
                                        sql_ex = ("""select avl.id from %s avl left join account_voucher av on av.id= avl.voucher_id where (avl.create_date >='%s' or avl.write_date >='%s') and av.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    else:
                                        sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            source.execute(sql_ex)
                            conect.execute(sql_ex)
                            change_local = source.fetchall()
                            if change_local:
                                for clr in change_local:
                                    nuevo_local.append(clr[0])
                            if nuevo_local:
                                for nuevo in nuevo_local:
                                    self.data_upload(model, source_or, pool, conection, database, nuevo, context)
                                    conection.commit()
                            self.pool.get('base.synchro.obj').write(cr,uid,model_ids.id,{'synchronize_date':time.strftime('%Y-%m-%d %H:%M:%S')})
                            cr.commit()

                        elif model_ids.action=='b':
                            shop_obj = self.pool.get('sale.shop')
                            shop_id_local_ids = shop_obj.search(cr,uid,[('server_db','=',pool)])
                            shop_id = shop_obj.browse(cr,uid,shop_id_local_ids[-1])
                            shop_id_remote_ids = self.pool.get('sale.shop').search(cr,uid,[('server_db','=',database)])
                            shop_id_remote = shop_obj.browse(cr,uid,shop_id_remote_ids[0])
                            if model in ('account_invoice','account_move','account_move_line','account_voucher','account_bank_statement','account_payments'):
                                if shop_id.headquarter: 
                                    sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and state != 'draft' and shop_id = %s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                else:
                                    sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and state != 'draft' order by id"""%(model,last_synchro,last_synchro))
                            elif model in ('account_bank_statement_line'):
                                sql_ex = ("""select absl.id from %s absl left join account_bank_statement abs on abs.id = absl.statement_id where (absl.create_date >='%s' or absl.write_date >='%s') and abs.state != 'draft' and abs.shop_id = %s order by id"""%(model,last_synchro,last_synchro,shop_id.id))                            
                            elif model in ('product_ubication'):
                                sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            elif model=='res_users':
                                sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            else:
                                if search_shop_id:
                                    sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                else:
                                    if model == 'account_invoice_line':
                                        sql_ex = ("""select ail.id from %s ail left join account_invoice ai on ai.id= ail.invoice_id where (ail.create_date >='%s' or ail.write_date >='%s') and ai.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model == 'account_move_line':
                                        sql_ex = ("""select aml.id from %s aml left join account_move am on am.id= aml.move_id where (aml.create_date >='%s' or aml.write_date >='%s') and am.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    elif model == 'account_voucher_line':
                                        sql_ex = ("""select avl.id from %s avl left join account_voucher av on av.id= avl.voucher_id where (avl.create_date >='%s' or avl.write_date >='%s') and av.shop_id=%s order by id"""%(model,last_synchro,last_synchro,shop_id.id))
                                    else:
                                        sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') order by id"""%(model,last_synchro,last_synchro))
                            source.execute(sql_ex)
                            conect.execute(sql_ex)
                            if model in ('res_users','stock_picking','res_company_users_rel','res_groups_users_rel','rel_user_box'):
                                if model=='res_users':
                                    source.execute(sql_ex)
                                    conect.execute(sql_ex)
                                    change_local = source.fetchall() 
                                    change_remote = conect.fetchall()
                                    if change_local:
                                        for clr in change_local:
                                            nuevo_local.append(clr[0])
                                    if change_remote:
                                        for clr in change_remote:
                                            nuevo_remote.append(clr[0])
                                    if change_local or change_remote:
                                        review_ids = merge_unique(nuevo_local, nuevo_remote)
                                        self.data_both(model, source_or, pool, conection, database, review_ids, context)
                                        model = 'res_groups_users_rel'
                                        tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """ % (model,))                                                                
                                        if nuevo_local:
                                            source.execute("select uid from res_groups_users_rel where uid in %s",(tuple(nuevo_local),))
                                        if nuevo_remote:
                                            conect.execute("select uid from res_groups_users_rel where uid in %s",(tuple(nuevo_remote),))
                                        change_local_rg = source.fetchall()
                                        change_remote_rg = conect.fetchall()
                                        nuevo_local_rg = []
                                        nuevo_remote_rg = []
                                        if change_local_rg:
                                            for clr in change_local_rg:
                                                nuevo_local_rg.append(clr[0])
                                        if change_remote_rg:
                                            for clr in change_remote_rg:
                                                nuevo_remote_rg.append(clr[0])                        
                                        if change_local_rg or change_remote_rg:
                                            nuevo_remote_rg = compare_unique(nuevo_remote_rg, nuevo_local_rg)
                                            if nuevo_remote_rg:
                                                for define_record in nuevo_remote_rg:                                        
                                                    if define_record: 
                                                        source.execute("""select * from %s where uid=%s order by uid"""%(model, define_record))
                                                        conect.execute("""select * from %s where uid=%s order by uid"""%(model, define_record))
                                                        old_d = source.fetchall()
                                                        # Si no existe, lo inserta mediante insert into.        
                                                        if not old_d:
                                                            conect.execute(tables)
                                                            fields_sri_remote = conect.fetchall()
                                                            fields_app = ""
                                                            for f in fields_sri_remote:
                                                                fields_app=fields_app +'"' +(f[0]) +'",'
                                                            fields_app = fields_app[:-1]
                                                            if fields_app:
                                                                sql_fields_app = ("""select %s from %s where uid='%s'"""%(fields_app,model,define_record))
                                                                conect.execute(sql_fields_app)
                                                                selection_f = conect.fetchall()
                                                            for ins in selection_f:
                                                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                                sql = sql.replace("None", "Null")
                                                                sql = sql.replace(", u'",",'")
                                                                source.execute(sql) 
                                                            osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',define_record, model, database)                                
                                            nuevo_local= compare_unique(nuevo_local_rg,nuevo_remote_rg)
                                            if nuevo_local_rg:
                                                for define_record in nuevo_local_rg:
                                                    if define_record: 
                                                        source.execute("""select * from %s where uid=%s order by uid"""%(model, define_record))
                                                        conect.execute("""select * from %s where uid=%s order by uid"""%(model, define_record))
                                                        old_d = conect.fetchall()
                                                        # Si no existe, lo inserta mediante insert into.        
                                                        nuevo = define_record
                                                        if not old_d:
                                                            source.execute(tables)
                                                            fields_sri_remote = source.fetchall()
                                                            fields_app = ""
                                                            for f in fields_sri_remote:
                                                                fields_app=fields_app +'"' +(f[0]) +'",'
                                                            fields_app = fields_app[:-1]
                                                            if fields_app:
                                                                sql_fields_app = ("""select %s from %s where uid='%s'"""%(fields_app,model,nuevo))
                                                                source.execute(sql_fields_app)
                                                                selection_f = source.fetchall()
                                                            for ins in selection_f:
                                                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                                sql = sql.replace("None", "Null")
                                                                sql = sql.replace(", u'",",'")
                                                                conect.execute(sql)
                                                            osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',nuevo, model, pool)
                                        model = 'res_company_users_rel'
                                        tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                                        change_local_rc = []
                                        change_remote_rc = []
                                        if nuevo_local:
                                            source.execute("select cid from res_company_users_rel where user_id in %s",(tuple(nuevo_local),))
                                            change_local_rc = source.fetchall()
                                        if nuevo_remote:
                                            conect.execute("select cid from res_company_users_rel where user_id in %s",(tuple(nuevo_remote),))
                                            change_remote_rc = conect.fetchall()                                    
                                        nuevo_local_rc = []
                                        nuevo_remote_rc = []
                                        if change_local_rc:
                                            for clr in change_local_rc:
                                                nuevo_local_rc.append(clr[0])
                                        if change_remote_rc:
                                            for clr in change_remote_rc:
                                                nuevo_remote_rc.append(clr[0])                        
                                        if change_local_rc or change_remote_rc:
                                            nuevo_remote_rc = compare_unique(nuevo_remote_rc, nuevo_local_rc)
                                            if nuevo_remote_rc:
                                                for define_record in nuevo_remote_rc:
                                                    if define_record: 
                                                        source.execute("""select * from %s where cid=%s order by cid"""%(model, define_record))
                                                        conect.execute("""select * from %s where cid=%s order by cid"""%(model, define_record))
                                                        old_d = source.fetchall()
                                                        # Si no existe, lo inserta mediante insert into.        
                                                        if not old_d:
                                                            conect.execute(tables)
                                                            fields_sri_remote = conect.fetchall()
                                                            fields_app = ""
                                                            for f in fields_sri_remote:
                                                                fields_app=fields_app +'"' +(f[0]) +'",'
                                                            fields_apmistakesp = fields_app[:-1]
                                                            if fields_app:
                                                                sql_fields_app = ("""select %s from %s where cid='%s'"""%(fields_app,model,define_record))
                                                                conect.execute(sql_fields_app)
                                                                selection_f = conect.fetchall()
                                                            for ins in selection_f:
                                                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                                sql = sql.replace("None", "Null")
                                                                sql = sql.replace(", u'",",'")
                                                                source.execute(sql) 
                                                            osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',define_record, model, database)                                
                                            nuevo_local_rc= compare_unique(nuevo_local_rc,nuevo_remote_rc)
                                            if nuevo_local_rc:
                                                for define_record in nuevo_local_rc:
                                                    if define_record: 
                                                        source.execute("""select * from %s where cid=%s order by cid"""%(model, define_record))
                                                        conect.execute("""select * from %s where cid=%s order by cid"""%(model, define_record))
                                                        old_d = conect.fetchall()
                                                        # Si no existe, lo inserta mediante insert into.        
                                                        if not old_d:
                                                            source.execute(tables)
                                                            fields_sri_remote = source.fetchall()
                                                            fields_app = ""
                                                            for f in fields_sri_remote:
                                                                fields_app=fields_app +'"' +(f[0]) +'",'
                                                            fields_app = fields_app[:-1]
                                                            if fields_app:
                                                                sql_fields_app = ("""select %s from %s where oid='%s'"""%(fields_app,model,nuevo))
                                                                source.execute(sql_fields_app)
                                                                selection_f = source.fetchall()
                                                            for ins in selection_f:
                                                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                                sql = sql.replace("None", "Null")
                                                                sql = sql.replace(", u'",",'")
                                                                try:
                                                                    conect.execute(sql)
                                                                    osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',nuevo, model, pool)
                                                                except:
                                                                    osv._logger.warning('El registro %s del modelo %s tuvo problemas de creación en la base de datos %s',nuevo, model, pool)
                                        model = 'rel_user_box'
                                        tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                                        change_local_rcb = []
                                        if nuevo_local:
                                            source.execute("select box_id, user_id from rel_user_box where user_id in %s",(tuple(nuevo_local),))
                                            change_local_rcb = source.fetchall()
                                        change_remote_rcb = []
                                        if nuevo_remote:
                                            conect.execute("select box_id, user_id from rel_user_box where user_id in %s",(tuple(nuevo_remote),))
                                            change_remote_rcb = conect.fetchall()   
                                        nuevo_local_rcb = []
                                        nuevo_remote_rcb = []
                                        if change_local_rcb:
                                            for clr in change_local_rcb:
                                                nuevo_local_rcb.append(clr)
                                        if change_remote_rcb:
                                            for clr in change_remote_rcb:
                                                nuevo_remote_rcb.append(clr)                        
                                        if change_local_rcb or change_remote_rcb:
                                            nuevo_remote_rcbl = compare_unique(nuevo_remote_rcb, nuevo_local_rcb)
                                            if nuevo_remote_rcbl:
                                                for define_record in nuevo_remote_rcbl:
                                                    if define_record: 
                                                        source.execute("select oid from rel_user_box where user_id = %s"%(define_record[1],))
                                                        conect.execute("select oid from rel_user_box where user_id = %s"%(define_record[1],))
                                                        old_d = source.fetchall()
                                                        # Si no existe, lo inserta mediante insert into.        
                                                        if not old_d:
                                                            conect.execute(tables)
                                                            fields_sri_remote = conect.fetchall()
                                                            fields_app = ""
                                                            for f in fields_sri_remote:
                                                                fields_app=fields_app +'"' +(f[0]) +'",'
                                                            fields_app = fields_app[:-1]
                                                            if fields_app:
                                                                sql_fields_app = ("select %s from %s where oid = %s"%(fields_app,model,define_record[1]))
                                                                conect.execute(sql_fields_app)
                                                                selection_f = conect.fetchall()
                                                            for ins in selection_f:
                                                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                                sql = sql.replace("None", "Null")
                                                                sql = sql.replace(", u'",",'")
                                                                source.execute(sql) 
                                                            osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',define_record, model, database)                                
                                            nuevo_local_rcbl= compare_unique(nuevo_local_rcb,nuevo_remote_rcb)
                                            if nuevo_local_rcbl:
                                                for define_record in nuevo_local_rcbl:
                                                    if define_record: 
                                                        source.execute("select oid from rel_user_box where user_id = %s"%(define_record[1],))
                                                        conect.execute("select oid from rel_user_box where user_id = %s"%(define_record[1],))
                                                        old_d = conect.fetchall()
                                                        # Si no existe, lo inserta mediante insert into.        
                                                        if not old_d:
                                                            source.execute(tables)
                                                            fields_sri_remote = source.fetchall()
                                                            fields_app = ""
                                                            for f in fields_sri_remote:
                                                                fields_app=fields_app +'"' +(f[0]) +'",'
                                                            fields_app = fields_app[:-1]
                                                            if fields_app:
                                                                sql_fields_app = ("select %s from %s where oid = %s"%(fields_app,model,nuevo))
                                                                source.execute(sql_fields_app)
                                                                selection_f = source.fetchall()
                                                            for ins in selection_f:
                                                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                                                sql = sql.replace("None", "Null")
                                                                sql = sql.replace(", u'",",'")
                                                                try:
                                                                    conect.execute(sql)
                                                                    osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',nuevo, model, pool)
                                                                except:
                                                                    osv._logger.warning('El registro %s del modelo %s tuvo problemas de creación en la base de datos %s',nuevo, model, pool)
                                    source_or.commit()
                                    conection.commit()
                                    self.pool.get('base.synchro.obj').write(cr,uid,model_ids.id,{'synchronize_date':time.strftime('%Y-%m-%d %H:%M:%S')})
                                elif model== 'stock_picking':
                                    if shop_id.headquarter:
                                        sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and type in ('in','out','internal') and state not in ('draft') and (shop_id=%s or shop_id_dest=%s) order by id"""%(model,last_synchro,last_synchro,shop_id.id,shop_id.id))
                                    else:
                                        sql_ex = ("""select id from %s where (create_date >='%s' or write_date >='%s') and type in ('in','out','internal') and state not in ('draft') order by id"""%(model,last_synchro,last_synchro,))
                                    source.execute(sql_ex)
                                    conect.execute(sql_ex)
                                    change_local = source.fetchall()                    
                                    change_remote = conect.fetchall()
                                    if change_local:
                                        for clr in change_local:
                                            nuevo_local.append(clr[0])
                                    if change_remote:
                                        for clr in change_remote:
                                            nuevo_remote.append(clr[0])
                                    if nuevo_local or nuevo_remote:                         
                                        review_ids = merge_unique(nuevo_local,nuevo_remote)                   
                                        self.data_both(model, source_or, pool, conection, database, review_ids,context)
                                    model = 'stock_move'
                                    if nuevo_local:
                                        source.execute("""select id from stock_move where picking_id in %s """,(tuple(nuevo_local),))
                                    if nuevo_remote:
                                        conect.execute("""select id from stock_move where picking_id in %s """,(tuple(nuevo_remote),))
                                    change_local_m = source.fetchall()
                                    change_remote_m = conect.fetchall()
                                    nuevo_local_m= []
                                    nuevo_remote_m= []
                                    if change_local_m:
                                        for clr in change_local:
                                            nuevo_local_m.append(clr[0])
                                    if change_remote_m:
                                        for clr in change_remote:
                                            nuevo_remote_m.append(clr[0])
                                    if nuevo_local_m or nuevo_remote_m:
                                        review_ids = merge_unique(nuevo_local, nuevo_remote)
                                        self.data_both(model, source_or, pool, conection, database, review_ids, context)
                                    conection.commit()
                                    source_or.commit()
                            elif model == 'res_partner':
                                change_local = source.fetchall()
                                change_remote = conect.fetchall()
                                if change_local:
                                    for clr in change_local:
                                        nuevo_local.append(clr[0])
                                if change_remote:
                                    for clr in change_remote:
                                        nuevo_remote.append(clr[0])

                                review_ids = merge_unique(nuevo_local, nuevo_remote)
                                self.compare_partner(model, source_or, pool, conection, database, review_ids, context)

                            else:
                                change_local = source.fetchall()
                                change_remote = conect.fetchall()
                                if change_local:
                                    for clr in change_local:
                                        nuevo_local.append(clr[0])
                                if change_remote:
                                    for clr in change_remote:
                                        nuevo_remote.append(clr[0])                        
                                ##Primero, compara las fechas de escritura de los elementos recientes.                        
                                review_ids = merge_unique(nuevo_local,nuevo_remote)                   
                                self.data_both(model, source_or, pool, conection, database, review_ids,context)
                            conection.commit()
                            source_or.commit()
                            self.pool.get('base.synchro.obj').write(cr,uid,model_ids.id,{'synchronize_date':time.strftime('%Y-%m-%d %H:%M:%S')})
                            cr.commit()
                    except psycopg2.Error, e:
                        datas = model+": " +str(e)
                        mistakes.append(datas)
                        osv._logger.warning('El registro %s del modelo %s de la base de datos %s tiene un problema: %s',nuevo_local, model, database,e)
                        continue
                source_or.close()
                conection.close()
                self.write(cr,uid,ids,{'last_synchro':time.strftime('%Y-%m-%d %H:%M:%S')})            

                if mistakes:
                    xml_id = 'email_synchro_error'
                    template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_base_synchro', xml_id)
                    if not template_ids:
                        raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico de errores de sincronización.'))            
                    else:
                        template_id = template_ids[1]
                        context.update({'error':mistakes,'model':model,'email_it':shop_id_remote.it_manager.user_email})
                    self.generate_email_synchro(cr,uid,template_id,ids[0],context)

                return True

        except psycopg2.Error, e:
            raise osv.except_osv('Error!', _("Could not establish the connection : %s" %e))



    def generate_email_synchro(self, cr, uid, template_id, res_id, context=None):
        if context is None:
            context = {}
            
        error = context.get('error',None)
        model = context.get('model',None)
        email_it = context.get('email_it',None)
        values = {
                  'subject': False,
                  'body_text': False,
                  'body_html': False,
                  'email_from': False,
                  'email_to': False,
                  'email_cc': False,
                  'email_bcc': False,
                  'reply_to': False,
                  'auto_delete': False,
                  'model': False,
                  'res_id': False,
                  'mail_server_id': False,
                  'attachments': False,
                  'attachment_ids': False,
                  'message_id': False,
                  'state': 'outgoing',
                  'subtype': 'plain',
        }
        if not template_id:
            return values

        report_xml_pool = self.pool.get('ir.actions.report.xml')
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')
        email_template_obj = self.pool.get('email.template')
        template = email_template_obj.get_email_template(cr, uid, template_id, res_id, context)
        template_context = email_template_obj._prepare_render_template_context(cr, uid, template.model, res_id, context)

        for field in ['subject', 'body_text', 'body_html', 'email_from',
                      'email_to', 'email_cc', 'email_bcc', 'reply_to',
                      'message_id']:
            values[field] = email_template_obj.render_template(cr, uid, getattr(template, field),
                                                               template.model, res_id, context=template_context) or False

        body_text = "El/Lo siguiente(s) modelo(s) presenta(n) el(los) siguiente(s) error(es): " + str(error)
        values['body_text'] = body_text
        values['email_from'] = email_it
        values['email_to'] = email_it

        if values['body_html']:
            values.update(subtype='html')

        values.update(mail_server_id=template.mail_server_id.id,
                      auto_delete=template.auto_delete,
                      model=template.model,
                      res_id=res_id or False)

        msg_id = mail_message.create(cr, uid, values, context=context)
        mail_message.send(cr, uid, [msg_id], context=context)
        return True

base_synchro_server()


class base_synchro_obj(osv.osv):
    '''Class to store the operations done by wizard'''
    _name = "base.synchro.obj"
    _description = "Register Class"
    _columns = {
        'name':fields.char('Name', size=64, select=1, required=1),
        'domain':fields.char('Domain', size=64, select=1, required=1),
        'server_id':fields.many2one('base.synchro.server','Server', ondelete='cascade', select=1, required=1),
        'model_id': fields.char('Object to synchronize',size=100,required=True),
        'action':fields.selection([('d','Download'),('u','Upload'),('b','Both'),('r','Relationed Object')],'Synchronisation direction', required=True),
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'synchronize_date':fields.datetime('Latest Synchronization'),
        'line_id':fields.one2many('base.synchro.obj.line','obj_id','Ids Affected',ondelete='cascade'),
        'avoid_ids':fields.one2many('base.synchro.obj.avoid','obj_id','Fields Not Sync.'), 
    }
    _defaults = {
        'active': lambda *args: True,
        'action': lambda *args: 'd',
        'domain': lambda *args: '[]',
    }
    _order = 'sequence'

base_synchro_obj()


class base_synchro_object(osv.osv):
    _name = "base.synchro.object"
    _description = "objects that are not synchronized"
    _columns = {'model_id': fields.many2one('ir.model', 'Object not alter sequence', required=True)}
    _rec_name = 'model_id'
base_synchro_object()


class base_synchro_obj_avoid(osv.osv):
    _name = "base.synchro.obj.avoid"
    _description = "Fields to not synchronize"
    _columns = {
        'name': fields.char('Field Name', size=64, select=1, required=1),
        'obj_id': fields.many2one('base.synchro.obj', 'Object', required=1, ondelete='cascade'),
    }
base_synchro_obj_avoid()


class base_synchro_obj_line(osv.osv):
    '''Class to store the operations done by wizard'''
    _name = "base.synchro.obj.line"
    _description = "Synchronized instances"
    _columns = {
        'name': fields.datetime('Date', required=True),
        'obj_id': fields.many2one('base.synchro.obj', 'Object', ondelete='cascade', select=True),
        'local_id': fields.integer('Local Id', readonly=True),
        'remote_id': fields.integer('Remote Id', readonly=True)
    }
    _defaults = {
        'name': lambda *args: time.strftime('%Y-%m-%d %H:%M:%S')
    }
base_synchro_obj_line()


class sale_shop(osv.osv):

    _inherit = 'sale.shop'
    _columns = {'it_manager': fields.many2one('res.users', 'IT Manager')}

sale_shop()