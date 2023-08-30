# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
#
##############################################################################

import os, time
#from datetime import datetime
import datetime as dt 
from dateutil.relativedelta import relativedelta
from datetime import datetime
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc
from account_voucher import account_voucher

class account_invoice_line(osv.osv):

    _inherit = "account.invoice.line"
        
account_invoice_line()