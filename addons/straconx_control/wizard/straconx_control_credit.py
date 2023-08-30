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


class wizard_control_credit(osv.osv_memory):
    _name = 'wizard.control.credit'

wizard_control_credit()