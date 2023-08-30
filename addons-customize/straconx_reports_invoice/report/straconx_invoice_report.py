# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
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

from report import report_sxw
from osv import fields, osv
import time
from operator import itemgetter, attrgetter

class Parser(report_sxw.rml_parse):    

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.out_invoices = []
        user=self.pool.get('res.users').browse(cr,uid,uid).name
        shop=self.pool.get('sale.shop')
        date_to=False
        date_from=False
        self.localcontext.update({
            'time': time,
            'shop_id': shop,
            'out_invoices': self.out_invoices,
            'user': user,
            'date_to':date_to,
            'date_from':date_from,
        })


    def set_context(self, objects, data, ids, report_type = None):
        invoice_obj = self.pool.get('account.invoice')
        lista=[]
        order_by=[]
        if ids:
#        if data['model'] == 'ir.ui.menu':
#            sql="""select id, number, shop_id, printer_id, salesman_id, type, state, user_id, amount_untaxed, 
#                            amount_base_vat_00, amount_base_vat_12,amount_total_vat_12, amount_total_vat, 
#                            residual from account_invoice where"""
            sql="""select id from account_invoice where"""
            shop = []
            invoice_types = []
            if data['form']['out_invoice']:
                invoice_types.append('out_invoice')
            if data['form']['out_refund']:
                invoice_types.append('out_refund')
            if data['form']['in_invoice']:
                invoice_types.append('in_invoice')
            if data['form']['in_refund']:
                invoice_types.append('in_refund')
            if invoice_types:
                sql+=""" type in %s"""
                lista.append(tuple(invoice_types))
            invoice_states = []
            if data['form']['draft']:
                invoice_states.append('draft')
            if data['form']['proforma']:
                invoice_states.append('proforma')
                invoice_states.append('proforma2')
            if data['form']['open']:
                invoice_states.append('open')
            if data['form']['paid']:
                invoice_states.append('paid')
            if data['form']['cancel']:
                invoice_states.append('cancel')
            if invoice_states:
                sql+=""" AND state in %s"""
                lista.append(tuple(invoice_states))
            if data['form']['shop_id']:
                shop_id = data['form']['shop_id']
                if not shop:
                    shop = self.poo.get('sale.shop').search(self.cr,self.uid,[])    
                shop= self.pool.get('sale.shop').browse(self.cr,self.uid,shop_id)
                sql+=""" AND shop_id = %s"""
                lista.append(data['form']['shop_id'])
            if data['form']['company_id']:
                sql+=""" AND company_id = %s"""
                lista.append(data['form']['company_id'])
            if data['form']['state'] in ['byperiod','all']:
                period_ids = data['form']['periods'][0][2]
                periods = ','.join([str(id) for id in period_ids])
                sql+=""" AND period_id = %s"""
                lista.append(data['form']['period_id'])
            if data['form']['state'] in ['bydate','all','none']:
                date_from=data['form']['date_from']
                sql+=""" AND date_invoice >= %s"""
                lista.append(date_from)
                date_to=data['form']['date_to']
                sql+=""" AND date_invoice <= %s"""
                lista.append(date_to)
            order_by = data.get('form') and data.get('form').get('order_by') or None
            if order_by=='date':
                sql+=""" order by date_invoice, number, partner_id"""
            elif order_by=='partner':
                sql+=""" order by vat, number, date_invoice """
            elif order_by=='number':
                sql+=""" order by number, date_invoice, partner_id"""
            elif order_by=='segmento':
                sql+=""" order by segmento_id, number, date_invoice, partner_id"""
            elif order_by=='salesman':
                sql+=""" order by salesman_id, number, date_invoice, partner_id"""
            elif order_by=='user':
                sql+=""" order by user_id, salesman_id, segmento_id, number, date_invoice, partner_id"""
            elif order_by=='printer_point':
                sql+=""" order by printer_point, number, date_invoice, partner_id"""
            self.cr.execute(sql,lista)
            ids = map(lambda x: x[0], self.cr.fetchall())
            objects = invoice_obj.browse(self.cr, self.uid, ids)
            if objects:
                self.out_invoices = objects        
            self.localcontext.update({
                'out_invoices': self.out_invoices,
                'date_to':date_to,
                'date_from':date_from,
                'shop': shop,
            })
        super(Parser, self).set_context(objects, data, ids, report_type)