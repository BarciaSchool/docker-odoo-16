# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 20011 STRACONX S.A. (<http://openerp.straconx.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from report import report_sxw
from lxml import etree
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        wth_obj = self.pool.get('stock.shop') 
#        inv_obj = self.pool.get('account.invoice')
#        model = context['active_model']
        ids = context['active_id']        
#        if model == 'account.withhold':
        stock = wth_obj.browse(cr, uid, [ids,], context)[0]
        self.localcontext.update({
            'stock': stock,

    })

