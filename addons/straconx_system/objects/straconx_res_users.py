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

import datetime
import babel
import dateutil.relativedelta

_logger = logging.getLogger(__name__)


class users(osv.osv):
    _inherit = "res.users"

    _columns = {
        'first_login': fields.boolean('First login'),
    }

    _defaults = {'first_login': True}

    def change_password(self, cr, uid, old_passwd, new_passwd, context=None):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: openerp.exceptions.AccessDenied when old password is wrong
        :raise: except_osv when new password is not set or empty
        """
        #  self.check(cr.dbname, uid, old_passwd)
        if new_passwd:
            osv._logger.warning('La contraseña del usuario %s ha sido cambiada con éxito a las %s', uid,
                                time.strftime('%Y-%m-%d %H:%M:%S'))
            self.write(cr, 1, uid, {'password': new_passwd, 'first_login': False, 'action_id': 1, 'menu_id': 1})
            return True
        raise osv.except_osv(_('Warning!'), _("Setting empty passwords is not allowed for security reasons!"))

users()