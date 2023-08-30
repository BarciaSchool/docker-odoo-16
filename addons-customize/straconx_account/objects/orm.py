# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A  
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

from openerp.osv.orm import BaseModel, browse_record_list,browse_record,browse_null

#MODIFY METHOD BROWSE OF CLASS ORM

def value_element(self, cr, element):
    cr.execute('SELECT true FROM '+self._table+' WHERE id = %s',(element,))
    res=cr.fetchall()
    if res:
        return element
    else:
        False

def browse_new(self, cr, uid, select, context=None, list_class=None, fields_process=None):
    """Fetch records as objects allowing to use dot notation to browse fields and relations

    :param cr: database cursor
    :param uid: current user id
    :param select: id or list of ids.
    :param context: context arguments, like lang, time zone
    :rtype: object or list of objects requested
    """
    self._list_class = list_class or browse_record_list
    cache = {}
    # need to accepts ints and longs because ids coming from a method
    # launched by button in the interface have a type long...
    if isinstance(select, bool):
        return browse_null()
    elif isinstance(select, (int, long)):
        select = value_element(self, cr, select)
        if not select:
            return browse_null()
        return browse_record(cr, uid, select, self, cache, context=context, list_class=self._list_class, fields_process=fields_process)
    elif isinstance(select, list):
        select = [element for element in select if isinstance(element, (int, long)) and value_element(self, cr, element)]
        return self._list_class([browse_record(cr, uid, id, self, cache, context=context, list_class=self._list_class, fields_process=fields_process) for id in select], context=context)
    else:
        return browse_null()
    
BaseModel.browse= browse_new


def _check_concurrency(self, cr, ids, context):
    if not context:
        return
    if not (context.get(self.CONCURRENCY_CHECK_FIELD) and self._log_access):
        return
    check_clause = "(id = %s AND %s < COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp)"
    for sub_ids in cr.split_for_in_conditions(ids):
        ids_to_check = []
        for id in sub_ids:
            id_ref = "%s,%s" % (self._name, id)
            update_date = context[self.CONCURRENCY_CHECK_FIELD].pop(id_ref, None)
            if update_date:
                ids_to_check.extend([id, update_date])
        if not ids_to_check:
            continue
        cr.execute("SELECT id FROM %s WHERE %s" % (self._table, " OR ".join([check_clause]*(len(ids_to_check)/2))), tuple(ids_to_check))
        res = cr.fetchone()
#             if res:
#                 # mention the first one only to keep the error message readable
#                 raise except_orm('ConcurrencyException', _('A document was modified since you last viewed it (%s:%d)') % (self._description, res[0]))

BaseModel._check_concurrency= _check_concurrency