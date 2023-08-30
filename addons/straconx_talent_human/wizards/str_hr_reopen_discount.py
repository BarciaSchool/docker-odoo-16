# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

from osv import fields,osv
from tools.translate import _

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
#from datetime import *
from dateutil import *
import decimal_precision as dp
import base64
import StringIO
from string import upper
from string import join

class wizard_hr_discount(osv.osv_memory):
    
    _name = 'wizard.modified.discount'
    
    def back_discount(self, cr, uid, ids, context=None):
        t_ids = self.pool.get('hr.discount').search(cr,uid,[('state','!=','draft')])
        for discount in t_ids:
            self.pool.get('hr.discount').button_canceled(cr,uid,[discount])
            self.pool.get('hr.discount').button_set_draft(cr,uid,[discount])
        return True

    def approve_mass_discount(self, cr, uid, ids, context=None):
        t_ids = self.pool.get('hr.discount').search(cr,uid,[('state','=','draft')])
        for discount in t_ids:
            self.pool.get('hr.discount').button_approve(cr,uid,[discount])
        return True
wizard_hr_discount()

