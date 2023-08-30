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

class account_multi_invoice(osv.osv_memory): 
    _name = 'wizard.multi.sales'
    
    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr,uid, uid).company_id.id
        return company or False

    _columns = {            
            'company_id': fields.many2one('res.company', 'Company', required=True, change_default=True),
            'date_from': fields.date('Start date'),
            'date_to': fields.date('End date'),
            'order_by': fields.selection( [
                           ('partner','Partner'),
                           ('segmento','Segmento'),
                           ('salesman','Salesman'),
                           ('shop','shop'),
                           ('category','category'),
                           ('zone','Zone'),
                           ('user','User'),
                           ('shop_printer','Shop and Printer Point')],'Order by', required=True),
        }

    _defaults = { 
        'company_id': _get_company_id,
        'date_from':lambda *a:time.strftime("%Y-%m-01"),
        'date_to':lambda *a:time.strftime("%Y-%m-%d"),
        'order_by':'shop'
    }

    def check_report(self, cr, uid, ids, context=None):
        model = 'account.invoice'
        report_name = 'report.invoice.shop'        
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': model,
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }

    def check_report_excel(self, cr, uid, ids, context=None):
        model = 'account.invoice'
        report_excel = 'report.invoice.shop.excel'
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': model,
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_excel,
            'datas': datas,
        }

account_multi_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
