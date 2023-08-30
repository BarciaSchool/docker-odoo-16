# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2013-2014 Jorge Valdiviezo (jorgito2006@gmail.com) All Rights Reserved     
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
 
from openerp.osv.orm import BaseModel, except_orm
from osv import osv
import os
from sql_db_remote import get_connect_server
 
import psycopg2
from openerp.osv import fields
import openerp.netsvc as netsvc
import operator
import threading
 
from openerp import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)
 
#black_list=['base.synchro.server']
 

black_list=['base.synchro.server','ir.ui.menu','ir.model.data','ir.ui.view','ir.actions.act_window','ir.module.module',
            'ir.actions.report.xml','ir.model.access','ir.actions.act_window.view','res.groups']


def get_directory(self, cr, uid):
    full_path = False
    local_media_repository = self.pool.get('res.company').get_local_file_synchronize_repository(cr, 1)
    if local_media_repository:
        full_path = os.path.join(local_media_repository,'sql_synchronize.txt')
    return full_path
     
def check_filestore(self, filestore):
    """check if the filestore is created, if not it create it automatically"""
    try:
        dir_path = os.path.dirname(filestore)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    except OSError, e:
        raise osv.except_osv(_('Error'), _('The filestore can not be created, %s'%e))
    return True

def create_document(self, cr, uid, sql):
    full_path=get_directory(self ,cr, uid)
    check_filestore(self, full_path)
    with open(full_path, 'a') as ofile:
        ofile.write(sql)
    return True

def synchronize_unlink(self, sentence_unlink_list):
    if self._name in black_list:
        return True
    if not sentence_unlink_list:
        return True
    try:
        db = self.pool.db
        cr = db.cursor()
        servers_obj = self.pool.get('base.synchro.server')
        servers_ids = servers_obj.search(cr, 1, [])
        for server in servers_obj.browse(cr, 1, servers_ids):
            sql_pend=''
            try:
                cr.execute("select ir_model.model from rel_synchro_model, ir_model  where synchro_server_id = %s and model_id = ir_model.id",(server.id,))
                result=cr.fetchall()
                res=[r[0] for r in result if r]
                if self._name in res:
                    return True
                cr_remote=get_connect_server(server).get_cursor()
                for sentence in sentence_unlink_list:
                    cr_remote.execute(sentence[0],sentence[1])
                cr_remote.commit()
                cr_remote.close()
            except psycopg2.Error, e:
                osv._logger.warning("Error in operation %s",e)
                for sentence in sentence_unlink_list:
                    sql_pend+= str(server.id)+':$'+str(sentence[0])+':$'+str(sentence[1])+'\n'
            except:
                osv._logger.warning("Could not establish the connection to server %s",server.server_url)
            finally:
                if sql_pend:
                    create_document(self, cr, 1, sql_pend)
        cr.close()
    except:
        _logger.warning('Exception in open cursor')
    return True
 
 
def unlink_new(self, cr, uid, ids, context=None):
    if not ids:
        return True
    if not context:
        context = {}
    sentence_unlink_list=[]
    if isinstance(ids, (int, long)):
        ids = [ids]
 
    result_store = self._store_get_values(cr, uid, ids, self._all_columns.keys(), context)
 
    self._check_concurrency(cr, ids, context)
 
    self.check_unlink(cr, uid)
 
    ir_property = self.pool.get('ir.property')
     
    # Check if the records are used as default properties.
    domain = [('res_id', '=', False),
              ('value_reference', 'in', ['%s,%s' % (self._name, i) for i in ids]),
             ]
    if ir_property.search(cr, uid, domain, context=context):
        raise except_orm(_('Error'), _('Unable to delete this document because it is used as a default property'))
 
    # Delete the records' properties.
    property_ids = ir_property.search(cr, uid, [('res_id', 'in', ['%s,%s' % (self._name, i) for i in ids])], context=context)
    ir_property.unlink(cr, uid, property_ids, context=context)
 
    wf_service = netsvc.LocalService("workflow")
    for oid in ids:
        wf_service.trg_delete(uid, self._name, oid, cr)
 
 
    self.check_access_rule(cr, uid, ids, 'unlink', context=context)
    pool_model_data = self.pool.get('ir.model.data')
    ir_values_obj = self.pool.get('ir.values')
    for sub_ids in cr.split_for_in_conditions(ids):
        sentence='delete from ' + self._table + ' where id IN %s', (sub_ids,)
        cr.execute(sentence[0],sentence[1])
        sentence_unlink_list.append(sentence)
        # Removing the ir_model_data reference if the record being deleted is a record created by xml/csv file,
        # as these are not connected with real database foreign keys, and would be dangling references.
        # Note: following steps performed as admin to avoid access rights restrictions, and with no context
        #       to avoid possible side-effects during admin calls.
        # Step 1. Calling unlink of ir_model_data only for the affected IDS
        reference_ids = pool_model_data.search(cr, SUPERUSER_ID, [('res_id','in',list(sub_ids)),('model','=',self._name)])
        # Step 2. Marching towards the real deletion of referenced records
        if reference_ids:
            pool_model_data.unlink(cr, SUPERUSER_ID, reference_ids, context=context)
 
        # For the same reason, removing the record relevant to ir_values
        ir_value_ids = ir_values_obj.search(cr, uid,
                ['|',('value','in',['%s,%s' % (self._name, sid) for sid in sub_ids]),'&',('res_id','in',list(sub_ids)),('model','=',self._name)],
                context=context)
        if ir_value_ids:
            ir_values_obj.unlink(cr, uid, ir_value_ids, context=context)
 
    for order, object, store_ids, fields in result_store:
        if object != self._name:
            obj = self.pool.get(object)
            cr.execute('select id from '+obj._table+' where id IN %s', (tuple(store_ids),))
            rids = map(lambda x: x[0], cr.fetchall())
            if rids:
                obj._store_set_values(cr, uid, rids, fields, context)
    threading.Thread(target=synchronize_unlink, args=(self, sentence_unlink_list)).start()
    return True
 
BaseModel.unlink= unlink_new
 
def synchronize_write(self, sentence_write_list):
    if self._name in black_list:
        return True
    if not sentence_write_list:
        return True
    try:
        db = self.pool.db
        cr = db.cursor()
        servers_obj = self.pool.get('base.synchro.server')
        servers_ids = servers_obj.search(cr, 1, [])
        for server in servers_obj.browse(cr, 1, servers_ids):
            sql_pend=''
            try:
                cr.execute("select ir_model.model from rel_synchro_model, ir_model  where synchro_server_id = %s and model_id = ir_model.id",(server.id,))
                result=cr.fetchall()
                res=[r[0] for r in result if r]
                if self._name in res:
                    return True
                cr_remote=get_connect_server(server).get_cursor()
                for sentence in sentence_write_list:
                    cr_remote.execute(sentence[0],sentence[1])
                cr_remote.commit()
                cr_remote.close()
            except psycopg2.Error, e:
                osv._logger.warning("Error in operation %s",e)
                for sentence in sentence_write_list:
                    sql_pend+= str(server.id)+':$'+str(sentence[0])+':$'+str(sentence[1])+'\n'
            except:
                osv._logger.warning("Could not establish the connection to server %s",server.server_url)
            finally:
                if sql_pend:
                    create_document(self, cr, 1, sql_pend)
        cr.close()
    except:
        _logger.warning('Exception in open cursor')
    return True
 
def write_new(self, cr, user, ids, vals, context=None):
    if not context:
        context = {}
    sentence_write_list=[]
    sentence_write_list1=[]
    readonly = None
    for field in vals.copy():
        fobj = None
        if field in self._columns:
            fobj = self._columns[field]
        elif field in self._inherit_fields:
            fobj = self._inherit_fields[field][2]
        if not fobj:
            continue
        groups = fobj.write
 
        if groups:
            edit = False
            for group in groups:
                module = group.split(".")[0]
                grp = group.split(".")[1]
                cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name=%s and module=%s and model=%s) and uid=%s", \
                           (grp, module, 'res.groups', user))
                readonly = cr.fetchall()
                if readonly[0][0] >= 1:
                    edit = True
                    break
 
            if not edit:
                vals.pop(field)
 
    if not ids:
        return True
    if isinstance(ids, (int, long)):
        ids = [ids]
 
    self._check_concurrency(cr, ids, context)
    self.check_write(cr, user)
 
    result = self._store_get_values(cr, user, ids, vals.keys(), context) or []
 
    # No direct update of parent_left/right
    vals.pop('parent_left', None)
    vals.pop('parent_right', None)
 
    parents_changed = []
    parent_order = self._parent_order or self._order
    if self._parent_store and (self._parent_name in vals):
        # The parent_left/right computation may take up to
        # 5 seconds. No need to recompute the values if the
        # parent is the same.
        # Note: to respect parent_order, nodes must be processed in
        # order, so ``parents_changed`` must be ordered properly.
        parent_val = vals[self._parent_name]
        if parent_val:
            query = "SELECT id FROM %s WHERE id IN %%s AND (%s != %%s OR %s IS NULL) ORDER BY %s" % \
                            (self._table, self._parent_name, self._parent_name, parent_order)
            cr.execute(query, (tuple(ids), parent_val))
        else:
            query = "SELECT id FROM %s WHERE id IN %%s AND (%s IS NOT NULL) ORDER BY %s" % \
                            (self._table, self._parent_name, parent_order)
            cr.execute(query, (tuple(ids),))
        parents_changed = map(operator.itemgetter(0), cr.fetchall())
 
    upd0 = []
    upd1 = []
    upd_todo = []
    updend = []
    direct = []
    totranslate = context.get('lang', False) and (context['lang'] != 'en_US')
    for field in vals:
        if field in self._columns:
            if self._columns[field]._classic_write and not (hasattr(self._columns[field], '_fnct_inv')):
                if (not totranslate) or not self._columns[field].translate:
                    upd0.append('"'+field+'"='+self._columns[field]._symbol_set[0])
                    upd1.append(self._columns[field]._symbol_set[1](vals[field]))
                direct.append(field)
            else:
                upd_todo.append(field)
        else:
            updend.append(field)
        if field in self._columns \
                and hasattr(self._columns[field], 'selection') \
                and vals[field]:
            self._check_selection_field_value(cr, user, field, vals[field], context=context)
 
    if self._log_access:
        upd0.append('write_uid=%s')
        upd0.append("write_date=(now() at time zone 'UTC')")
        upd1.append(user)
 
    if len(upd0):
        self.check_access_rule(cr, user, ids, 'write', context=context)
        for sub_ids in cr.split_for_in_conditions(ids):
            sentence='update ' + self._table + ' set ' + ','.join(upd0) + 'where id IN %s', upd1 + [sub_ids]
            cr.execute(sentence[0],sentence[1])
            sentence_write_list.append(sentence)
            if cr.rowcount != len(sub_ids):
                raise except_orm(_('AccessError'),
                                 _('One of the records you are trying to modify has already been deleted (Document type: %s).') % self._description)
 
        if totranslate:
            # TODO: optimize
            for f in direct:
                if self._columns[f].translate:
                    src_trans = self.pool.get(self._name).read(cr, user, ids, [f])[0][f]
                    if not src_trans:
                        src_trans = vals[f]
                        # Inserting value to DB
                        self.write(cr, user, ids, {f: vals[f]})
                    self.pool.get('ir.translation')._set_ids(cr, user, self._name+','+f, 'model', context['lang'], ids, vals[f], src_trans)
 
 
    # call the 'set' method of fields which are not classic_write
    upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)
 
    # default element in context must be removed when call a one2many or many2many
    rel_context = context.copy()
    for c in context.items():
        if c[0].startswith('default_'):
            del rel_context[c[0]]
    threading.Thread(target=synchronize_write, args=(self, sentence_write_list)).start()
    for field in upd_todo:
        for id in ids:
            result += self._columns[field].set(cr, self, id, field, vals[field], user, context=rel_context) or []
 
    unknown_fields = updend[:]
    for table in self._inherits:
        col = self._inherits[table]
        nids = []
        for sub_ids in cr.split_for_in_conditions(ids):
            cr.execute('select distinct "'+col+'" from "'+self._table+'" ' \
                       'where id IN %s', (sub_ids,))
            nids.extend([x[0] for x in cr.fetchall()])
 
        v = {}
        for val in updend:
            if self._inherit_fields[val][0] == table:
                v[val] = vals[val]
                unknown_fields.remove(val)
        if v:
            self.pool.get(table).write(cr, user, nids, v, context)
 
    if unknown_fields:
        _logger.warning(
            'No such field(s) in model %s: %s.',
            self._name, ', '.join(unknown_fields))
    self._validate(cr, user, ids, context)
    if parents_changed:
        if self.pool._init:
            self.pool._init_parent[self._name] = True
        else:
            order = self._parent_order or self._order
            parent_val = vals[self._parent_name]
            if parent_val:
                clause, params = '%s=%%s' % (self._parent_name,), (parent_val,)
            else:
                clause, params = '%s IS NULL' % (self._parent_name,), ()
 
            for id in parents_changed:
                cr.execute('SELECT parent_left, parent_right FROM %s WHERE id=%%s' % (self._table,), (id,))
                pleft, pright = cr.fetchone()
                distance = pright - pleft + 1
 
                # Positions of current siblings, to locate proper insertion point;
                # this can _not_ be fetched outside the loop, as it needs to be refreshed
                # after each update, in case several nodes are sequentially inserted one
                # next to the other (i.e computed incrementally)
                cr.execute('SELECT parent_right, id FROM %s WHERE %s ORDER BY %s' % (self._table, clause, parent_order), params)
                parents = cr.fetchall()
 
                # Find Position of the element
                position = None
                for (parent_pright, parent_id) in parents:
                    if parent_id == id:
                        break
                    position = parent_pright + 1
 
                # It's the first node of the parent
                if not position:
                    if not parent_val:
                        position = 1
                    else:
                        cr.execute('select parent_left from '+self._table+' where id=%s', (parent_val,))
                        position = cr.fetchone()[0] + 1
 
                if pleft < position <= pright:
                    raise except_orm(_('UserError'), _('Recursivity Detected.'))
 
                if pleft < position:
                    sentence1='update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position)
                    cr.execute(sentence1[0],sentence1[1])
                    sentence2='update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position)
                    cr.execute(sentence2[0],sentence2[1])
                    sentence3='update '+self._table+' set parent_left=parent_left+%s, parent_right=parent_right+%s where parent_left>=%s and parent_left<%s', (position-pleft, position-pleft, pleft, pright)
                    cr.execute(sentence3[0],sentence3[1])
                    sentence_write_list1.append(sentence1)
                    sentence_write_list1.append(sentence2)
                    sentence_write_list1.append(sentence3)
                else:
                    sentence1='update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position)
                    cr.execute(sentence1[0],sentence1[1])
                    sentence2='update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position)
                    cr.execute(sentence2[0],sentence2[1])
                    sentence3='update '+self._table+' set parent_left=parent_left-%s, parent_right=parent_right-%s where parent_left>=%s and parent_left<%s', (pleft-position+distance, pleft-position+distance, pleft+distance, pright+distance)
                    cr.execute(sentence3[0],sentence3[1])
                    sentence_write_list1.append(sentence1)
                    sentence_write_list1.append(sentence2)
                    sentence_write_list1.append(sentence3)

    result += self._store_get_values(cr, user, ids, vals.keys(), context)
    result.sort()
 
    done = {}
    for order, object, ids_to_update, fields_to_recompute in result:
        key = (object, tuple(fields_to_recompute))
        done.setdefault(key, {})
        # avoid to do several times the same computation
        todo = []
        for id in ids_to_update:
            if id not in done[key]:
                done[key][id] = True
                todo.append(id)
        self.pool.get(object)._store_set_values(cr, user, todo, fields_to_recompute, context)
 
    wf_service = netsvc.LocalService("workflow")
    for id in ids:
        wf_service.trg_write(user, self._name, id, cr)
    threading.Thread(target=synchronize_write, args=(self, sentence_write_list1)).start()
    return True
 
BaseModel.write= write_new
 
def synchronize_create(self, sentence_create_list):
    if self._name in black_list:
        return True
    if not sentence_create_list:
        return True
    try:
        db = self.pool.db
        cr = db.cursor()
        servers_obj = self.pool.get('base.synchro.server')
        servers_ids = servers_obj.search(cr, 1, [])
        for server in servers_obj.browse(cr, 1, servers_ids):
            sql_pend=''
            try:
                cr.execute("select ir_model.model from rel_synchro_model, ir_model  where synchro_server_id = %s and model_id = ir_model.id",(server.id,))
                result=cr.fetchall()
                res=[r[0] for r in result if r]
                if self._name in res:
                    return True
                cr_remote=get_connect_server(server).get_cursor()
                for sentence in sentence_create_list:
                    cr_remote.execute(sentence[0],sentence[1])
                cr_remote.commit()
                cr_remote.close()
            except psycopg2.Error, e:
                osv._logger.warning("Error in operation %s",e)
                for sentence in sentence_create_list:
                    sql_pend+= str(server.id)+':$'+str(sentence[0])+':$'+str(sentence[1])+'\n'
            except:
                osv._logger.warning("Could not establish the connection to server %s",server.server_url)
            finally:
                if sql_pend:
                    create_document(self, cr, 1, sql_pend)
        cr.close()
    except:
        _logger.warning('Exception in open cursor')
    return True
 
def alterate_sequence(self, cr, id_new):
    try:
        cr.execute("select ir_model.model from base_synchro_object, ir_model where model_id = ir_model.id")
        result=cr.fetchall()
        res=[r[0] for r in result if r]
        if self._name in res:
            return id_new
        prefix = cr.dbname[-1]
        id_new = prefix + '%%0%sd' % 8 % id_new
        id_new = int(id_new)
        return id_new
    except ValueError:
        raise except_orm(_('Error'),_('Can not create register because name database is not correct.'))
 
def create_new(self, cr, user, vals, context=None):
    if not context:
        context = {}
    sentence_create_list=[]
 
    if self.is_transient():
        self._transient_vacuum(cr, user)
 
    self.check_create(cr, user)
 
    vals = self._add_missing_default_values(cr, user, vals, context)
 
    tocreate = {}
    for v in self._inherits:
        if self._inherits[v] not in vals:
            tocreate[v] = {}
        else:
            tocreate[v] = {'id': vals[self._inherits[v]]}
    (upd0, upd1, upd2) = ('', '', [])
    upd_todo = []
    unknown_fields = []
    for v in vals.keys():
        if v in self._inherit_fields and v not in self._columns:
            (table, col, col_detail, original_parent) = self._inherit_fields[v]
            tocreate[table][v] = vals[v]
            del vals[v]
        else:
            if (v not in self._inherit_fields) and (v not in self._columns):
                del vals[v]
                unknown_fields.append(v)
    if unknown_fields:
        _logger.warning(
            'No such field(s) in model %s: %s.',
            self._name, ', '.join(unknown_fields))
 
    # Try-except added to filter the creation of those records whose filds are readonly.
    # Example : any dashboard which has all the fields readonly.(due to Views(database views))
    try:
        cr.execute("SELECT nextval('"+self._sequence+"')")
    except:
        raise except_orm(_('UserError'),
                    _('You cannot perform this operation. New Record Creation is not allowed for this object as this object is for reporting purpose.'))
 
    id_new = cr.fetchone()[0]
    for table in tocreate:
        if self._inherits[table] in vals:
            del vals[self._inherits[table]]
 
        record_id = tocreate[table].pop('id', None)
         
        # When linking/creating parent records, force context without 'no_store_function' key that
        # defers stored functions computing, as these won't be computed in batch at the end of create(). 
        parent_context = dict(context)
        parent_context.pop('no_store_function', None)
         
        if record_id is None or not record_id:
            record_id = self.pool.get(table).create(cr, user, tocreate[table], context=parent_context)
        else:
            self.pool.get(table).write(cr, user, [record_id], tocreate[table], context=parent_context)
 
        upd0 += ',' + self._inherits[table]
        upd1 += ',%s'
        upd2.append(record_id)
 
    #Start : Set bool fields to be False if they are not touched(to make search more powerful)
    bool_fields = [x for x in self._columns.keys() if self._columns[x]._type=='boolean']
 
    for bool_field in bool_fields:
        if bool_field not in vals:
            vals[bool_field] = False
    #End
    for field in vals.copy():
        fobj = None
        if field in self._columns:
            fobj = self._columns[field]
        else:
            fobj = self._inherit_fields[field][2]
        if not fobj:
            continue
        groups = fobj.write
        if groups:
            edit = False
            for group in groups:
                module = group.split(".")[0]
                grp = group.split(".")[1]
                cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name='%s' and module='%s' and model='%s') and uid=%s" % \
                           (grp, module, 'res.groups', user))
                readonly = cr.fetchall()
                if readonly[0][0] >= 1:
                    edit = True
                    break
                elif readonly[0][0] == 0:
                    edit = False
                else:
                    edit = False
 
            if not edit:
                vals.pop(field)
    for field in vals:
        if self._columns[field]._classic_write:
            upd0 = upd0 + ',"' + field + '"'
            upd1 = upd1 + ',' + self._columns[field]._symbol_set[0]
            upd2.append(self._columns[field]._symbol_set[1](vals[field]))
        else:
            if not isinstance(self._columns[field], fields.related):
                upd_todo.append(field)
        if field in self._columns \
                and hasattr(self._columns[field], 'selection') \
                and vals[field]:
            self._check_selection_field_value(cr, user, field, vals[field], context=context)
    if self._log_access:
        upd0 += ',create_uid,create_date'
        upd1 += ",%s,(now() at time zone 'UTC')"
        upd2.append(user)
    id_new=alterate_sequence(self, cr, id_new)
#    if context.get('synchronize',True):
#        threading.Thread(target=synchronize_create, args=(self, user, id_new, vals, context)).start()
    sentence='insert into "'+self._table+'" (id'+upd0+") values ("+str(id_new)+upd1+')', tuple(upd2)
    cr.execute(sentence[0],sentence[1])
    sentence_create_list.append(sentence)
    self.check_access_rule(cr, user, [id_new], 'create', context=context)
    upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)
 
    if self._parent_store and not context.get('defer_parent_store_computation'):
        if self.pool._init:
            self.pool._init_parent[self._name] = True
        else:
            parent = vals.get(self._parent_name, False)
            if parent:
                cr.execute('select parent_right from '+self._table+' where '+self._parent_name+'=%s order by '+(self._parent_order or self._order), (parent,))
                pleft_old = None
                result_p = cr.fetchall()
                for (pleft,) in result_p:
                    if not pleft:
                        break
                    pleft_old = pleft
                if not pleft_old:
                    cr.execute('select parent_left from '+self._table+' where id=%s', (parent,))
                    pleft_old = cr.fetchone()[0]
                pleft = pleft_old
            else:
                cr.execute('select max(parent_right) from '+self._table)
                pleft = cr.fetchone()[0] or 0
            sentence1='update '+self._table+' set parent_left=parent_left+2 where parent_left>%s', (pleft,)
            cr.execute(sentence1[0],sentence1[1])
            sentence2='update '+self._table+' set parent_right=parent_right+2 where parent_right>%s', (pleft,)
            cr.execute(sentence2[0],sentence2[1])
            sentence3='update '+self._table+' set parent_left=%s,parent_right=%s where id=%s', (pleft+1, pleft+2, id_new)
            cr.execute(sentence3[0],sentence3[1])
            sentence_create_list.append(sentence1)
            sentence_create_list.append(sentence2)
            sentence_create_list.append(sentence3)
    # default element in context must be remove when call a one2many or many2many
    rel_context = context.copy()
    for c in context.items():
        if c[0].startswith('default_'):
            del rel_context[c[0]]
    threading.Thread(target=synchronize_create, args=(self, sentence_create_list)).start()
    result = []
    for field in upd_todo:
        result += self._columns[field].set(cr, self, id_new, field, vals[field], user, rel_context) or []
    self._validate(cr, user, [id_new], context)
 
    if not context.get('no_store_function', False):
        result += self._store_get_values(cr, user, [id_new], vals.keys(), context)
        result.sort()
        done = []
        for order, object, ids, fields2 in result:
            if not (object, ids, fields2) in done:
                self.pool.get(object)._store_set_values(cr, user, ids, fields2, context)
                done.append((object, ids, fields2))
 
    if self._log_create and not (context and context.get('no_store_function', False)):
        message = self._description + \
            " '" + \
            self.name_get(cr, user, [id_new], context=context)[0][1] + \
            "' " + _("created.")
        self.log(cr, user, id_new, message, True, context=context)
    wf_service = netsvc.LocalService("workflow")
    wf_service.trg_create(user, self._name, id_new, cr)
    return id_new
 
BaseModel.create= create_new
