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
import re

import openerp.tiny_socket as tiny_socket

_logger = logging.getLogger(__name__)


class wizard_change_password(osv.osv_memory):
    _name = 'wizard.change.password'
    _columns = {'user_id': fields.many2one('res.users', 'Users'),
                'old_password': fields.char('Old Password', size=24),
                'new_password': fields.char('New Password', size=24),
                'confirm_pwd': fields.char('Confirm Password', size=24),
                'date': fields.datetime('Date')}
    _defaults = {'date': time.strftime('%Y-%m-%d %H:%M:%S')}

    def change_password(self, cr, uid, ids, context=None):
        warning = {}
        patron = re.compile("(^(?=.*[a-z])(?=.*[A-Z])(?=.*\d){6,20}.+$)")
        for cp in self.browse(cr, uid, ids):
            old_password = cp.old_password
            new_password = cp.new_password
            confirm_password = cp.confirm_pwd
            if not (old_password.strip() and new_password.strip() and confirm_password.strip()):
                raise osv.except_osv(_('¡Error!'), _("Se debe completar todos los campos para continuar"))
            if new_password == old_password:
                raise osv.except_osv(_('¡Error!'), _("La nueva contraseña y su confirmación no coinciden"))
            if new_password != confirm_password:
                raise osv.except_osv(_('¡Error!'), _("La nueva contraseña y su confirmación no coinciden"))
            if len(new_password) <= 8:
                raise osv.except_osv(_('¡Error!'), _("Se requiere una contraseña mayor de 8 caracteres combinados en letras o números."))
            check_pass = patron.match(new_password)
            if not check_pass:
                raise osv.except_osv(_('¡Error!'), _("La nueva contraseña debe contener letras mayúsculas, minúsculas y números."))
            new_pass = self.pool.get('res.users').change_password(cr, uid, old_password, new_password, context=None)
            if new_pass:
                return {'type': 'ir.actions.act_window_close'}
            else:
                raise osv.except_osv(_('¡Error!'), _("La contraseña no ha sido cambiada"))

    def change_password_cancel(self, cr, uid, ids, context=None):
        return netsvc.disconnect()

wizard_change_password()