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
        trade_obj = self.pool.get('purchase.trade')
        ids = context['active_id']
        trade = trade_obj.browse(cr, uid, [ids,], context)[0]
        trade_lines = trade.purchase_ids
        trade_insurance = trade.insurance_expenses_ids
        trade_delivery = trade.delivery_expenses_ids
        trade_others = trade.others_expenses_ids
        trade_product_lines = trade.purchase_line_ids
        self.localcontext.update({
            'trade': trade,
            'trade_lines': trade_lines,
            'trade_insurance': trade_insurance,
            'trade_delivery': trade_delivery,
            'trade_others': trade_others,
            'trade_product_lines': trade_product_lines,
        })
