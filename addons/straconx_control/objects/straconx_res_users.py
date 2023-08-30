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

import logging
from functools import partial

import pytz

import netsvc
import pooler
import tools
from osv import fields,osv
from osv.orm import browse_record
from service import security
from tools.translate import _
import openerp
import openerp.exceptions
from lxml import etree
from lxml.builder import E
import socket
import threading
import time

import openerp.tiny_socket as tiny_socket

from openerp.addons.web import common
openerpweb = common.http

import datetime
import babel
import dateutil.relativedelta
from openerp.addons.web.common import openerplib
from openerp.addons.web.controllers.main import Session

_logger = logging.getLogger(__name__)


class users(osv.osv):
    _inherit = "res.users"

    def login(self, db, login, password):
        if not password:
            return False
        cr = pooler.get_db(db).cursor()
        try:
            # autocommit: our single request will be performed atomically.
            # (In this way, there is no opportunity to have two transactions
            # interleaving their cr.execute()..cr.commit() calls and have one
            # of them rolled back due to a concurrent access.)
            # We effectively unconditionally write the res_users line.
            cr.autocommit(True)
            # Even w/ autocommit there's a chance the user row will be locked,
            # in which case we can't delay the login just for the purpose of
            # update the last login date - hence we use FOR UPDATE NOWAIT to
            # try to get the lock - fail-fast
            cr.execute("""select value from ir_config_parameter where key='credit_state'""")
            data = cr.fetchone()
            if data and data[0] == 'Bloqueado':
                cr.execute("""UPDATE res_users
                             set action_id = (select id from ir_act_window where name = 'Cuenta Suspendida')""")
            else:
                cr.execute("""UPDATE res_users set action_id = Null""")
            cr.execute("""SELECT id from res_users
                          WHERE login=%s AND password=%s
                                AND active FOR UPDATE NOWAIT""",
                       (tools.ustr(login), tools.ustr(password)), log_exceptions=False)
            cr.execute("""UPDATE res_users
                            SET date = now() AT TIME ZONE 'UTC'
                            WHERE login=%s AND password=%s AND active
                            RETURNING id""",
                       (tools.ustr(login), tools.ustr(password)))
        except Exception:
            # Failing to acquire the lock on the res_users row probably means
            # another request is holding it - no big deal, we skip the update
            # for this time, and let the user login anyway.
            cr.rollback()
            cr.execute("""SELECT id from res_users
                          WHERE login=%s AND password=%s
                                AND active""",
                       (tools.ustr(login), tools.ustr(password)))
        finally:
            res = cr.fetchone()
            cr.close()
            if res:
                return res[0]
        return False


users()


class ir_ui_menu(osv.osv):
    _inherit = 'ir.ui.menu'

    def _filter_visible_menus(self, cr, uid, ids, context=None):
        cr.execute("""select value from ir_config_parameter where key='credit_state'""")
        data = cr.fetchone()
        if data and data[0] == 'Bloqueado':
            result = []
            return result
        else:
            with self.cache_lock:
                modelaccess = self.pool.get('ir.model.access')
                user_groups = set(self.pool.get('res.users').read(cr, 1, uid, ['groups_id'])['groups_id'])
                result = []
                for menu in self.browse(cr, uid, ids, context=context):
                    # this key works because user access rights are all based on user's groups (cfr ir_model_access.check)
                    key = (cr.dbname, menu.id, tuple(user_groups))
                    if key in self._cache:
                        if self._cache[key]:
                            result.append(menu.id)
                        continue
                    self._cache[key] = False
                    if menu.groups_id:
                        restrict_to_groups = [g.id for g in menu.groups_id]
                        if not user_groups.intersection(restrict_to_groups):
                            continue
                    if menu.action:
                        data = menu.action
                        if data:
                            model_field = {'ir.actions.act_window':    'res_model',
                                           'ir.actions.report.xml':    'model',
                                           'ir.actions.wizard':        'model',
                                           'ir.actions.server':        'model_id',
                                           }
                            field = model_field.get(menu.action._name)
                            if field and data[field]:
                                if not modelaccess.check(cr, uid, data[field], 'read', False):
                                    continue
                    else:
                        if not menu.child_id:
                            continue
                    result.append(menu.id)
                    self._cache[key] = True
                return result

ir_ui_menu()


class view_sc(osv.osv):
    _inherit = 'ir.ui.view_sc'

    def get_sc(self, cr, uid, user_id, model='ir.ui.menu', context=None):
        cr.execute("""select value from ir_config_parameter where key='credit_state'""")
        data = cr.fetchone()
        if data and data[0] == 'Bloqueado':
            filtered_results = []
            return filtered_results
        else:
            ids = self.search(cr, uid, [('user_id', '=', user_id), ('resource', '=', model)], context=context)
            results = self.read(cr, uid, ids, ['res_id'], context=context)
            name_map = dict(self.pool.get(model).name_get(cr, uid, [x['res_id'] for x in results], context=context))
            # Make sure to return only shortcuts pointing to exisintg menu items.
            filtered_results = filter(lambda result: result['res_id'] in name_map, results)
            for result in filtered_results:
                result.update(name=name_map[result['res_id']])
            return filtered_results
