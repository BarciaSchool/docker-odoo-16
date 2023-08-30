# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved     
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
import time
from datetime import date 
from report import report_sxw
from tools import amount_to_text_es 

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=  None):
        super(Parser, self).__init__(cr, uid, name, context)
        ids = context.get("active_id")
        user = self.pool.get('res.users').browse(cr,uid,uid,context).name
        cash = self.pool.get("cash.consolidation").browse(cr, uid, ids, context)
        self.localcontext.update({
            'cash': cash,
            'user': user,
            'time':time
        })