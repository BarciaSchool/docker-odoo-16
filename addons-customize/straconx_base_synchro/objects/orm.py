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
from openerp.osv.orm import TransientModel,BaseModel, except_orm, fields, Query
import psycopg2
import os
import calendar
import copy
import datetime
import itertools
import logging
import operator
import pickle
import re
import simplejson
import time
import types
import threading
from lxml import etree
import threading
import openerp.sql_db as sql_db
import openerp
import openerp.netsvc as netsvc
import openerp.tools as tools
from openerp.tools.config import config
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import openerp.pooler as pooler
import xmlrpclib
import base64


_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')




from openerp import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)
 
black_list=['base.synchro.server','ir.ui.menu','ir.model.data','ir.ui.view','ir.actions.act_window','ir.module.module',
            'ir.actions.report.xml','ir.model.access','ir.actions.act_window.view','res.groups']

def table_exist(self, cr):
    cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
    prefix = cr.dbname[-3:]        
    try:
        prefix = int(filter(str.isdigit, prefix))
    except:
        return cr.rowcount
    
    if cr.rowcount <> 0:
        if prefix:
            seq = prefix * 1e8
            table_name = self._table + "_id_seq"
            cr.execute("""SELECT nextval(%s)""",(table_name,))    
            last_value = cr.fetchone()
            last_value = int(last_value[0])
            if last_value and last_value >0:
                if last_value < seq:
                    new_value = last_value + seq        
                    cr.execute("SELECT setval(%s, %s)",(table_name,int(new_value)))
    return cr.rowcount


def create_table(self, cr):
    cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
    if not cr.rowcount:
        cr.execute('CREATE TABLE "%s" (id SERIAL NOT NULL, PRIMARY KEY(id)) WITHOUT OIDS' % (self._table,))
        cr.execute(("COMMENT ON TABLE \"%s\" IS %%s" % self._table), (self._description,))
        _schema.debug("Table '%s': created", self._table)
    prefix = cr.dbname[-3:]
    try:
        prefix = int(filter(str.isdigit, prefix))
        if prefix:
            seq = prefix * 1e8
            table_name = self._table + "_id_seq"
            cr.execute("""SELECT nextval(%s)""",(table_name,))    
            last_value = cr.fetchone()
            last_value = int(last_value[0])
            if last_value and last_value >0:
                new_value = last_value + seq
                cr.execute("SELECT setval(%s, %s)",(table_name,int(new_value)))
    except:
        return True
    return True

# def write(self, cr, user, ids, vals, context=None):
#     import thread
#     readonly = None
# 
#     migrate = True
#     
#     for field in vals.copy():
#         fobj = None
#         if field in self._columns:
#             fobj = self._columns[field]
#         elif field in self._inherit_fields:
#             fobj = self._inherit_fields[field][2]
#         if not fobj:
#             continue
#         groups = fobj.write
# 
#         if groups:
#             edit = False
#             for group in groups:
#                 module = group.split(".")[0]
#                 grp = group.split(".")[1]
#                 cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name=%s and module=%s and model=%s) and uid=%s", \
#                            (grp, module, 'res.groups', user))
#                 readonly = cr.fetchall()
#                 if readonly[0][0] >= 1:
#                     edit = True
#                     break
# 
#             if not edit:
#                 vals.pop(field)
# 
#     if not context:
#         context = {}
#     if not ids:
#         return True
#     if isinstance(ids, (int, long)):
#         ids = [ids]
# 
#     self._check_concurrency(cr, ids, context)
#     self.check_write(cr, user)
# 
#     result = self._store_get_values(cr, user, ids, vals.keys(), context) or []
# 
#     # No direct update of parent_left/right
#     vals.pop('parent_left', None)
#     vals.pop('parent_right', None)
# 
#     parents_changed = []
#     parent_order = self._parent_order or self._order
#     if self._parent_store and (self._parent_name in vals):
#         # The parent_left/right computation may take up to
#         # 5 seconds. No need to recompute the values if the
#         # parent is the same.
#         # Note: to respect parent_order, nodes must be processed in
#         # order, so ``parents_changed`` must be ordered properly.
#         parent_val = vals[self._parent_name]
#         if parent_val:
#             query = "SELECT id FROM %s WHERE id IN %%s AND (%s != %%s OR %s IS NULL) ORDER BY %s" % \
#                             (self._table, self._parent_name, self._parent_name, parent_order)
#             cr.execute(query, (tuple(ids), parent_val))
#         else:
#             query = "SELECT id FROM %s WHERE id IN %%s AND (%s IS NOT NULL) ORDER BY %s" % \
#                             (self._table, self._parent_name, parent_order)
#             cr.execute(query, (tuple(ids),))
#         parents_changed = map(operator.itemgetter(0), cr.fetchall())
# 
#     upd0 = []
#     upd1 = []
#     upd_todo = []
#     updend = []
#     direct = []
#     totranslate = context.get('lang', False) and (context['lang'] != 'en_US')
#     for field in vals:
#         if field in self._columns:
#             if self._columns[field]._classic_write and not (hasattr(self._columns[field], '_fnct_inv')):
#                 if (not totranslate) or not self._columns[field].translate:
#                     upd0.append('"'+field+'"='+self._columns[field]._symbol_set[0])
#                     upd1.append(self._columns[field]._symbol_set[1](vals[field]))
#                 direct.append(field)
#             else:
#                 upd_todo.append(field)
#         else:
#             updend.append(field)
#         if field in self._columns \
#                 and hasattr(self._columns[field], 'selection') \
#                 and vals[field]:
#             self._check_selection_field_value(cr, user, field, vals[field], context=context)
# 
#     if self._log_access:
#         upd0.append('write_uid=%s')
#         upd0.append("write_date=(now() at time zone 'UTC')")
#         upd1.append(user)
# 
#     if len(upd0):
#         self.check_access_rule(cr, user, ids, 'write', context=context)
#         for sub_ids in cr.split_for_in_conditions(ids):
#             cr.execute('update ' + self._table + ' set ' + ','.join(upd0) + ' ' \
#                        'where id IN %s', upd1 + [sub_ids])
#             if cr.rowcount != len(sub_ids):
#                 raise except_orm(_('AccessError'),
#                                  _('One of the records you are trying to modify has already been deleted (Document type: %s).') % self._description)
# 
#         if totranslate:
#             # TODO: optimize
#             for f in direct:
#                 if self._columns[f].translate:
#                     src_trans = self.pool.get(self._name).read(cr, user, ids, [f])[0][f]
#                     if not src_trans:
#                         src_trans = vals[f]
#                         # Inserting value to DB
#                         self.write(cr, user, ids, {f: vals[f]})
#                     self.pool.get('ir.translation')._set_ids(cr, user, self._name+','+f, 'model', context['lang'], ids, vals[f], src_trans)
# 
# 
#     # call the 'set' method of fields which are not classic_write
#     upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)
# 
#     # default element in context must be removed when call a one2many or many2many
#     rel_context = context.copy()
#     for c in context.items():
#         if c[0].startswith('default_'):
#             del rel_context[c[0]]
# 
#     for field in upd_todo:
#         for id in ids:
#             result += self._columns[field].set(cr, self, id, field, vals[field], user, context=rel_context) or []
# 
#     unknown_fields = updend[:]
#     for table in self._inherits:
#         col = self._inherits[table]
#         nids = []
#         for sub_ids in cr.split_for_in_conditions(ids):
#             cr.execute('select distinct "'+col+'" from "'+self._table+'" ' \
#                        'where id IN %s', (sub_ids,))
#             nids.extend([x[0] for x in cr.fetchall()])
# 
#         v = {}
#         for val in updend:
#             if self._inherit_fields[val][0] == table:
#                 v[val] = vals[val]
#                 unknown_fields.remove(val)
#         if v:
#             self.pool.get(table).write(cr, user, nids, v, context)
# 
#     if unknown_fields:
#         _logger.warning(
#             'No such field(s) in model %s: %s.',
#             self._name, ', '.join(unknown_fields))
#     self._validate(cr, user, ids, context)
# 
#     # TODO: use _order to set dest at the right position and not first node of parent
#     # We can't defer parent_store computation because the stored function
#     # fields that are computer may refer (directly or indirectly) to
#     # parent_left/right (via a child_of domain)
#     if parents_changed:
#         if self.pool._init:
#             self.pool._init_parent[self._name] = True
#         else:
#             order = self._parent_order or self._order
#             parent_val = vals[self._parent_name]
#             if parent_val:
#                 clause, params = '%s=%%s' % (self._parent_name,), (parent_val,)
#             else:
#                 clause, params = '%s IS NULL' % (self._parent_name,), ()
# 
#             for id in parents_changed:
#                 cr.execute('SELECT parent_left, parent_right FROM %s WHERE id=%%s' % (self._table,), (id,))
#                 pleft, pright = cr.fetchone()
#                 distance = pright - pleft + 1
# 
#                 # Positions of current siblings, to locate proper insertion point;
#                 # this can _not_ be fetched outside the loop, as it needs to be refreshed
#                 # after each update, in case several nodes are sequentially inserted one
#                 # next to the other (i.e computed incrementally)
#                 cr.execute('SELECT parent_right, id FROM %s WHERE %s ORDER BY %s' % (self._table, clause, parent_order), params)
#                 parents = cr.fetchall()
# 
#                 # Find Position of the element
#                 position = None
#                 for (parent_pright, parent_id) in parents:
#                     if parent_id == id:
#                         break
#                     position = parent_pright + 1
# 
#                 # It's the first node of the parent
#                 if not position:
#                     if not parent_val:
#                         position = 1
#                     else:
#                         cr.execute('select parent_left from '+self._table+' where id=%s', (parent_val,))
#                         position = cr.fetchone()[0] + 1
# 
#                 if pleft < position <= pright:
#                     raise except_orm(_('UserError'), _('Recursivity Detected.'))
# 
#                 if pleft < position:
#                     cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
#                     cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
#                     cr.execute('update '+self._table+' set parent_left=parent_left+%s, parent_right=parent_right+%s where parent_left>=%s and parent_left<%s', (position-pleft, position-pleft, pleft, pright))
#                 else:
#                     cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
#                     cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
#                     cr.execute('update '+self._table+' set parent_left=parent_left-%s, parent_right=parent_right-%s where parent_left>=%s and parent_left<%s', (pleft-position+distance, pleft-position+distance, pleft+distance, pright+distance))
# 
#     result += self._store_get_values(cr, user, ids, vals.keys(), context)
#     result.sort()
# 
#     done = {}
#     for order, object, ids_to_update, fields_to_recompute in result:
#         key = (object, tuple(fields_to_recompute))
#         done.setdefault(key, {})
#         # avoid to do several times the same computation
#         todo = []
#         for id in ids_to_update:
#             if id not in done[key]:
#                 done[key][id] = True
#                 todo.append(id)
#         self.pool.get(object)._store_set_values(cr, user, todo, fields_to_recompute, context)
# 
#     wf_service = netsvc.LocalService("workflow")
#     for id in ids:
#         wf_service.trg_write(user, self._name, id, cr)
#     if migrate:
#         context.update({'table': self._table, 'execute_write':True})
#         new_cr = pooler.get_db(cr.dbname).cursor()       
#         threaded_migrate = threading.Thread(target=migrate_info, args=(self, new_cr, user, ids,vals,context))        
#         threaded_migrate.start()
#     return True
# 
# 
# def create(self, cr, user, vals, context=None):
# 
#     migrate = True
#     
#     if not context:
#         context = {}
# 
#     if self.is_transient():
#         self._transient_vacuum(cr, user)
# 
#     self.check_create(cr, user)
# 
#     vals = self._add_missing_default_values(cr, user, vals, context)
# 
#     tocreate = {}
#     for v in self._inherits:
#         if self._inherits[v] not in vals:
#             tocreate[v] = {}
#         else:
#             tocreate[v] = {'id': vals[self._inherits[v]]}
#     (upd0, upd1, upd2) = ('', '', [])
#     upd_todo = []
#     unknown_fields = []
#     for v in vals.keys():
#         if v in self._inherit_fields and v not in self._columns:
#             (table, col, col_detail, original_parent) = self._inherit_fields[v]
#             tocreate[table][v] = vals[v]
#             del vals[v]
#         else:
#             if (v not in self._inherit_fields) and (v not in self._columns):
#                 del vals[v]
#                 unknown_fields.append(v)
#     if unknown_fields:
#         _logger.warning(
#             'No such field(s) in model %s: %s.',
#             self._name, ', '.join(unknown_fields))
# 
#     # Try-except added to filter the creation of those records whose filds are readonly.
#     # Example : any dashboard which has all the fields readonly.(due to Views(database views))
#     try:
#         cr.execute("SELECT nextval('"+self._sequence+"')")
#     except:
#         raise except_orm(_('UserError'),
#                     _('You cannot perform this operation. New Record Creation is not allowed for this object as this object is for reporting purpose.'))
# 
#     id_new = cr.fetchone()[0]
#     for table in tocreate:
#         if self._inherits[table] in vals:
#             del vals[self._inherits[table]]
# 
#         record_id = tocreate[table].pop('id', None)
#         
#         # When linking/creating parent records, force context without 'no_store_function' key that
#         # defers stored functions computing, as these won't be computed in batch at the end of create(). 
#         parent_context = dict(context)
#         parent_context.pop('no_store_function', None)
#         
#         if record_id is None or not record_id:
#             record_id = self.pool.get(table).create(cr, user, tocreate[table], context=parent_context)
#         else:
#             self.pool.get(table).write(cr, user, [record_id], tocreate[table], context=parent_context)
# 
#         upd0 += ',' + self._inherits[table]
#         upd1 += ',%s'
#         upd2.append(record_id)
# 
#     #Start : Set bool fields to be False if they are not touched(to make search more powerful)
#     bool_fields = [x for x in self._columns.keys() if self._columns[x]._type=='boolean']
# 
#     for bool_field in bool_fields:
#         if bool_field not in vals:
#             vals[bool_field] = False
#     #End
#     for field in vals.copy():
#         fobj = None
#         if field in self._columns:
#             fobj = self._columns[field]
#         else:
#             fobj = self._inherit_fields[field][2]
#         if not fobj:
#             continue
#         groups = fobj.write
#         if groups:
#             edit = False
#             for group in groups:
#                 module = group.split(".")[0]
#                 grp = group.split(".")[1]
#                 cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name='%s' and module='%s' and model='%s') and uid=%s" % \
#                            (grp, module, 'res.groups', user))
#                 readonly = cr.fetchall()
#                 if readonly[0][0] >= 1:
#                     edit = True
#                     break
#                 elif readonly[0][0] == 0:
#                     edit = False
#                 else:
#                     edit = False
# 
#             if not edit:
#                 vals.pop(field)
#     for field in vals:
#         if self._columns[field]._classic_write:
#             upd0 = upd0 + ',"' + field + '"'
#             upd1 = upd1 + ',' + self._columns[field]._symbol_set[0]
#             upd2.append(self._columns[field]._symbol_set[1](vals[field]))
#         else:
#             if not isinstance(self._columns[field], fields.related):
#                 upd_todo.append(field)
#         if field in self._columns \
#                 and hasattr(self._columns[field], 'selection') \
#                 and vals[field]:
#             self._check_selection_field_value(cr, user, field, vals[field], context=context)
#     if self._log_access:
#         upd0 += ',create_uid,create_date'
#         upd1 += ",%s,(now() at time zone 'UTC')"
#         upd2.append(user)
#     cr.execute('insert into "'+self._table+'" (id'+upd0+") values ("+str(id_new)+upd1+')', tuple(upd2))
#     self.check_access_rule(cr, user, [id_new], 'create', context=context)
#     upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)
# 
#     if self._parent_store and not context.get('defer_parent_store_computation'):
#         if self.pool._init:
#             self.pool._init_parent[self._name] = True
#         else:
#             parent = vals.get(self._parent_name, False)
#             if parent:
#                 cr.execute('select parent_right from '+self._table+' where '+self._parent_name+'=%s order by '+(self._parent_order or self._order), (parent,))
#                 pleft_old = None
#                 result_p = cr.fetchall()
#                 for (pleft,) in result_p:
#                     if not pleft:
#                         break
#                     pleft_old = pleft
#                 if not pleft_old:
#                     cr.execute('select parent_left from '+self._table+' where id=%s', (parent,))
#                     pleft_old = cr.fetchone()[0]
#                 pleft = pleft_old
#             else:
#                 cr.execute('select max(parent_right) from '+self._table)
#                 pleft = cr.fetchone()[0] or 0
#             cr.execute('update '+self._table+' set parent_left=parent_left+2 where parent_left>%s', (pleft,))
#             cr.execute('update '+self._table+' set parent_right=parent_right+2 where parent_right>%s', (pleft,))
#             cr.execute('update '+self._table+' set parent_left=%s,parent_right=%s where id=%s', (pleft+1, pleft+2, id_new))
# 
#     # default element in context must be remove when call a one2many or many2many
#     rel_context = context.copy()
#     for c in context.items():
#         if c[0].startswith('default_'):
#             del rel_context[c[0]]
# 
#     result = []
#     for field in upd_todo:
#         result += self._columns[field].set(cr, self, id_new, field, vals[field], user, rel_context) or []
#     self._validate(cr, user, [id_new], context)
# 
#     if not context.get('no_store_function', False):
#         result += self._store_get_values(cr, user, [id_new], vals.keys(), context)
#         result.sort()
#         done = []
#         for order, object, ids, fields2 in result:
#             if not (object, ids, fields2) in done:
#                 self.pool.get(object)._store_set_values(cr, user, ids, fields2, context)
#                 done.append((object, ids, fields2))
# 
#     if self._log_create and not (context and context.get('no_store_function', False)):
#         message = self._description + \
#             " '" + \
#             self.name_get(cr, user, [id_new], context=context)[0][1] + \
#             "' " + _("created.")
#         self.log(cr, user, id_new, message, True, context=context)
#     wf_service = netsvc.LocalService("workflow")
#     if migrate:    
#         wf_service.trg_create(user, self._name, id_new, cr)
#         new_cr = pooler.get_db(cr.dbname).cursor()
#         context.update({'execute_create':True, 'migrate_vals':vals })       
#         threaded_migrate = threading.Thread(target=migrate_info, args=(self, new_cr, user, id_new ,vals,context))        
#         threaded_migrate.start()        
#     return id_new
# 
# 
# 
# def migrate_info(self, cr, user, ids, vals, context=None):
#     synchro_obj = self.pool.get('base.synchro.obj')
#     shop_obj = self.pool.get('sale.shop')
#     server_obj = self.pool.get('base.synchro.server')
#     headquarter = False
#     action = False
#     pool = cr.dbname
#     if not context:
#         return True
#     else:
#         table = context.get('table',False)
#         create_new = context.get('create_new',False)
#     if table:
#         table_ids = synchro_obj.search(cr,user,[('name','=',table)])
#         if table_ids:
#             table_data = synchro_obj.browse(cr,user,table_ids[0])
#             headquarter = table_data.headquarter
#             action = table_data.action
#             if headquarter:
#                 shop_ids = shop_obj.search(cr,user,[('headquarter','=', True)])
#                 context.update({'shop_ids':shop_ids[0]})
#                 # REMOTE CONECTION
#             else:
#                 shop_migrates = shop_obj.search(cr,user,[('server_db','!=', pool)])
#                 shop_migrates = sorted(shop_migrates, reverse=False)
#                 context.update({'shop_ids':shop_migrates})            
#             if action:
#                 context.update({'action':action})
#                 migrate_shops(self,cr,user,ids,vals,context)
#         else:
#             return True
#     cr.close()
#     return True
# 
# def migrate_shops(self, cr, user, ids, vals, context=None):
#     pool = cr.dbname
#     shop_obj = self.pool.get('sale.shop')
#     shop_ids = False
#     conection = False
#     source_or = False
#     if not context:
#         return True
#     else:
#         #shop_ids = context.get('shop_ids',False)
#         shop_ids = [1] 
#         action = context.get('action',False)
#         table = context.get('table',False)
#         model = table.replace('_','.')
#         execute_write = context.get('execute_write',False)
#         execute_create = context.get('execute_create',False)
#         execute_unlink = context.get('execute_unlink',False)
#         migrate_vals = context.get('migrate_vals',False)
# 
#     if user:
#         user_id = self.pool.get('res.users').browse(cr,user,user)
#     if model:
#         data_migrate = self.pool.get(model).read(cr, user, ids)
#         print data_migrate
# 
#         
#     if shop_ids:
#         for shop_id in shop_ids:                 
#             # REMOTE CONECTION
#             shop_head = shop_obj.browse(cr,user,shop_id,context)
#             shop_head_host = shop_head.server_url
#             shop_head_database = shop_head.server_db
#             shop_head_user = shop_head.login
#             shop_head_password = shop_head.password
#             shop_head_port = shop_head.server_port
#             if pool <> shop_head_database:
#                 username = user_id.login
#                 pwd = user_id.password                
#                 try:
#                     sock_common = xmlrpclib.ServerProxy ('http://'+shop_head_host+':8069/xmlrpc/common')
#                     uid = sock_common.login(shop_head_database, username, pwd)
#                     sock = xmlrpclib.ServerProxy('http://'+shop_head_host+':8069/xmlrpc/object')
#                     data = sock.execute(shop_head_database, uid, pwd, model, 'read', ids)
#                     if not data and (execute_create or execute_write):
#                         conection = psycopg2.connect(database=shop_head_database, user=shop_head_user, password=shop_head_password, host=shop_head_host, port=shop_head_port, options='-c statement_timeout=10s')           
#                         conect = conection.cursor()
#                         # Añadir el código de creación de registro de acuerdo al sql 
# 
#                         conect = conection.cursor()            
#                         tables = ("""SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid """%(table,))
#                         try:
#                             if ids: 
#                                 cr.execute("""select * from %s where id=%s order by id"""%(table, ids[0]))
#                                 conect.execute("""select * from %s where id=%s order by id"""%(table, ids[0]))
#                                 old_d = cr.fetchall()
#                                 rep_update = conect.fetchall()
#                                 # Si no existe, lo crea mediante insert into.        
#                                 if not rep_update:
#                                     ins = []
#                                     cr.execute(tables)
#                                     tables_data = cr.fetchall()
#                                     if tables_data:
#                                         fields_app = []
#                                         for f in tables_data:
#                                             t_id = f[0] 
#                                             fields_app.append('"'+t_id+'"')
#                                         if fields_app:
#                                             sql_fields_app = ("""select * from %s where id='%s'"""%(table,ids[0]))
#                                             cr.execute(sql_fields_app)
#                                             selection_f = cr.fetchall()
#                                         if selection_f:
#                                             for t in fields_app:
#                                                 ind = fields_app.index(t)
#                                                 old_d = selection_f[0][ind]                                                
#                                                 cr.execute("""SELECT typname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = '%s' AND a.attnum > 0 AND a.attrelid = c.oid AND a.atttypid = t.oid and a.attname ='%s' """%(table,t.replace('"',"")))
#                                                 type_data=conect.fetchall()                    
#                                                 if type_data and type_data[0][0] in ('varchar','text'):
#                                                     if old_d:
#                                                         com = "'"
#                                                         com2 = '"'
#                                                         new_d = old_d.replace(com,com2)
#                                                         old_d = new_d                                                             
#                                                     update_ind = str(old_d).encode("utf-8")
#                                                 elif type_data and type_data[0][0] in ('date','timestamp'):
#                                                     update_ind = str(old_d)
#                                                 elif type_data and type_data[0][0] =='bytea':
#                                                     if old_d:
#                                                         old_d = base64.b64decode(old_d)
#                                                         old_d = base64.b64encode(old_d)
#                                                     else:
#                                                         update_ind = "None"                                
#                                                 else:
#                                                     update_ind = str(old_d)
#                                                 ins.append(update_ind)
#                                         fields_sri_remote = fields_app
#                                         fields_app = ""
#                                         for f in fields_sri_remote:
#                                             fields_app=fields_app+'"'+(f) +'",'
#                                         fields_app = fields_app[:-1]
#                                         if ins:
#                                             sql=("""insert into %s (%s) values %s"""%(table,fields_app,tuple(ins)))
#                                             sql = sql.replace("'None'", "Null")
#                                             sql = sql.replace(", u'",",'")
#                                             sql = sql.replace('""','"')
#                                             conect.execute(sql)     
#                                         conection.commit()
#                                         osv._logger.warning('El registro %s del modelo %s ha sido creado en la base de datos %s',ids[0], table, shop_head_database)
#                                         if migrate_vals:
#                                             sock.execute(shop_head_database, uid, pwd, model, 'write', ids, migrate_vals)
#                         except psycopg2.Error, e:
#                             osv._logger.warning('Revisar error por id %s del modelo %s',ids[0], table)
#                     elif data and execute_write:
#                         sock.execute(shop_head_database, uid, pwd, model, 'write', ids, vals)
#                     elif data and execute_unlink:
#                         pass
# 
# #                             context.update({'id_new':ids,'remote_db':True})
# #                             sock = xmlrpclib.ServerProxy('http://'+shop_head_host+':8069/xmlrpc/object')       
# #                             new_id = sock.execute(shop_head_database, uid, pwd, model, 'create', vals)
# #                             correct_id = "update "+model+"set id="+ ids[0] +"where id="+new_id
# #                             conect.execute(correct_id)
# #                             conection.commit()
#                         
#                 except:
#                     pass
#                     osv._logger.warning('El registro %s del modelo %s no ha podido ser migrado en la base de datos %s',ids, model, shop_head_database)
#                 conection.close()
#     return True
# 
# 
# BaseModel.write = write
# BaseModel.create = create
TransientModel._create_table = create_table
TransientModel._table_exist = table_exist
