# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - 20011 STRACONX S.A. (<http://openerp.straconx.com>).
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



import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from osv import osv, fields

class account_report_ledger_statement(osv.osv_memory): 
    _name = 'wizard.stock.shop'
    
    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr,uid, uid).company_id.id
        return company or False

    def _get_location_id(self, cr, uid, context=None):
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        location = user_id.printer_point_ids and user_id.printer_point_ids[0].shop_id.warehouse_id.lot_stock_id.location_id.id
        return location or False

    _columns = {
            'category_id': fields.many2one('product.category','Category'),
            'location_id': fields.many2one('stock.location','Location'),
            'company_id': fields.many2one('res.company', 'Company', required=True, change_default=True),
            'date_from': fields.date('Start date'),
            'date_to': fields.date('End date'),
        }

    _defaults = { 
        'location_id': _get_location_id,
        'company_id': _get_company_id,
        'date_from':time.strftime("%Y-%m-%d %H:%M:%S"),
        'date_to':time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    def check_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'stock.move',
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock.shop.report',
            'datas': datas,
        }

    def check_report_excel(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'stock.move',
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock.shop.report.excel',
            'datas': datas,
        }

account_report_ledger_statement()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
