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

import os, time
#from datetime import datetime
import datetime as dt 
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc
import psycopg2
from account_voucher import account_voucher
import logging
_logger = logging.getLogger(__name__)


class account_invoice(osv.osv):

    _inherit = 'account.invoice'
    _order = "invoice_number, date_invoice2 desc"

    def action_move_invoice(self, cr, uid, ids, context=None):
        if context:
            shop_dest = context.get('shop_dest_id',False)
            if shop_dest:
                invoice_shop_id_dest = self.pool.get('sale.shop').browse(cr,uid,shop_dest) 
        for invoice in self.browse(cr, uid, ids, context=context):            
            # BASE DE DATOS DE ORIGEN
            if invoice:
                shop_id_database = invoice.shop_id.server_db
                shop_id_user = invoice.shop_id.login
                shop_id_password = invoice.shop_id.password
                shop_id_host=invoice.shop_id.server_url
                shop_id_port=invoice.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = invoice_shop_id_dest.server_db
                shop_dest_id_user = invoice_shop_id_dest.login
                shop_dest_id_password = invoice_shop_id_dest.password
                shop_dest_id_host = invoice_shop_id_dest.server_url
                shop_dest_id_port=invoice_shop_id_dest.server_port

                if (shop_id_host and shop_id_database) and (shop_dest_id_host and shop_dest_id_database) and (shop_id_database != shop_dest_id_database):
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
                    source.execute("""select id from account_invoice where id=%s""",(define_record,))
                    is_true = source.fetchone()
                    if is_true:
                        source.execute("""delete from wkf_workitem where inst_id = (select id from wkf_instance where res_id=%s and wkf_id = (SELECT ID FROM WKF WHERE NAME='account.invoice.basic' AND OSV='stock.picking')) """,(define_record,))
                        source.execute("""delete from wkf_instance where res_id=%s and wkf_id =(SELECT ID FROM WKF WHERE NAME='account.invoice.basic' AND OSV='stock.picking')""",(define_record,))
                        source.execute("""delete from account_move_line where move_id=(select move_id from account_invoice where id =%s)""",(define_record,))
                        source.execute("""delete from account_move where id=(select move_id from account_invoice where id =%s)""",(define_record,))
                        source.execute("""delete from account_invoice_line where invoice_id=%s""",(define_record,))
                        source.execute("""delete from account_invoice where id=%s""",(define_record,))
                        source_or.commit()

                    if source:
                        model_objs=['account_invoice','account_invoice_line','account_move', 'account_move_line']
                        for model_ids in model_objs:
                            model = model_ids
                            tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(model,))
                            source.execute(tables)
                            fields_sri_remote = source.fetchall()
                            fields_app = ""
                            for f in fields_sri_remote:
                                fields_app = fields_app + '"' + (f[0]) + '",'
                            fields_app = fields_app[:-1]
                            if fields_app:
                                if model == 'account_invoice':
                                    sql_fields_app = ("""select * from %s where id=%s""" % (model, define_record))
                                elif model == 'account_invoice_line':
                                    sql_fields_app = ("""select * from %s where invoice_id=%s""" % (model, define_record))
                                elif model == 'account_move':
                                    sql_fields_app = ("""select * from %s where id=(select move_id from account_invoice where id =%s)""" % (model,
                                                                                                                                            define_record))
                                elif model == 'account_move_line':
                                    sql_fields_app = ("""select * from %s where move_id=(select move_id from account_invoice where id =%s)""" % (model,
                                                                                                                                                 define_record))
                                conect.execute(sql_fields_app)
                                selection_f = conect.fetchall()
                            for ins in selection_f:
                                sql=("""insert into %s (%s) values %s"""%(model,fields_app,ins))
                                sql = sql.replace("None", "Null")
                                sql = sql.replace(", u'",",'")
                                osv._logger.warning(sql)
                                source.execute(sql)
                                osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',define_record, model, shop_id_database)
                        source_or.commit()
                    else:
                        raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))                
        return True
account_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

