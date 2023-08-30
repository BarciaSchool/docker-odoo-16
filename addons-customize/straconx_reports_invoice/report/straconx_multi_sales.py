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
        partner = False
        segmento = False
        salesman = False
        category = False
        zone = False
        printer = False
        date_to=False
        date_from=False
        self.localcontext.update({
            'time': time,
            'shop_id': shop,
            'out_invoices': self.out_invoices,
            'user': user,
            'date_to':date_to,
            'date_from':date_from,
            'partner':partner,
            'segmento':segmento,
            'salesman':salesman,
            'category':category,
            'zone':zone,
            'user':user,
            'shop_printer': printer,
        })


    def set_context(self, objects, data, ids, report_type = None):
        invoice_obj = self.pool.get('account.invoice')
        invoice_lin = self.pool.get('account.invoice.line')
        g={}
        date_from=data['form']['date_from']
        date_to=data['form']['date_to']
        datap_ids=[]
        datan_ids=[]        
        if data['form']['order_by'] == 'partner':
            p_ids = self.pool.get('res.partner').search(self.cr,self.uid,[('customer','=',True)])
            partner_id = self.pool.get('res.partner').browse(self.cr,self.uid,p_ids)
        elif data['form']['order_by'] == 'segmento':
            p_ids = self.pool.get('res.partner.segmento').search(self.cr, self.uid,[])
            segmento_id = self.pool.get('res.partner.segmento').browse(self.cr, self.uid, p_ids)        
        elif data['form']['order_by'] == 'salesman':
            p_ids = self.pool.get('salesman.salesman').search(self.cr, self.uid,[])
            salesman_id = self.pool.get('salesman.salesman').browse(self.cr, self.uid, p_ids)
        elif data['form']['order_by'] == 'shop':
            p_ids = self.pool.get('sale.shop').search(self.cr, self.uid,[])
            shop_id = self.pool.get('sale.shop').browse(self.cr, self.uid, p_ids)
            inp_ids = invoice_obj.search(self.cr,self.uid,[('shop_id','in',p_ids),('date_invoice','>=',date_from),('date_invoice','<=',date_to),('state','in',('open','cancel','paid')),('type','in',('out_invoice',))],order='shop_id')
            if inp_ids:
                invoicp = invoice_obj.browse(self.cr, self.uid, inp_ids)
            else:
                invoicp = []                
            inn_ids = invoice_obj.search(self.cr,self.uid,[('shop_id','in',p_ids),('date_invoice','>=',date_from),('date_invoice','<=',date_to),('state','in',('open','cancel','paid')),('type','in',('out_refund',))],order='shop_id')
            if inn_ids:
                invoicn = invoice_obj.browse(self.cr, self.uid, inn_ids)
            else:
                invoicn = []
            inv_ids = invoice_obj.search(self.cr,self.uid,[('shop_id','in',p_ids),('date_invoice','>=',date_from),('date_invoice','<=',date_to),('state','in',('open','cancel','paid')),('type','in',('out_invoice','out_refund'))],order='shop_id')
            invoice = invoice_obj.browse(self.cr, self.uid, inv_ids)
            for i in invoicp:
                if not g.has_key(i.shop_id):
                    g[i.shop_id]=[i]
                else:
                    g[i.shop_id]+=[i]
            for f in g.keys():
                datap_ids.append((f,g[f]))
            g={}
            for i in invoicn:
                if not g.has_key(i.shop_id):
                    g[i.shop_id]=[i]
                else:
                    g[i.shop_id]+=[i]
            for f in g.keys():
                datan_ids.append((f,g[f]))
            shop_id_e = True
            self.localcontext.update({
                'invoices': datap_ids,
                'refund': datan_ids,
                'date_to':date_to,
                'date_from':date_from,
                'shop_ids': shop_id_e,
                'invoice': invoice
            })                
        elif data['form']['order_by'] == 'category':
            p_ids = self.pool.get('product.category').search(self.cr, self.uid,[])
            categ_id = self.pool.get('product.category').browse(self.cr, self.uid, p_ids)
        elif data['form']['order_by'] == 'zone':
            p_ids = self.pool.get('res.region.zone').search(self.cr, self.uid,[])
            zone_id = self.pool.get('res.region.zone').browse(self.cr, self.uid, p_ids)            
        elif data['form']['order_by'] == 'user':
            p_ids = self.pool.get('res.users').search(self.cr, self.uid,[])
            user_id = self.pool.get('res.users').browse(self.cr, self.uid, p_ids)
        elif data['form']['order_by'] == 'shop_printer':
            p_ids = self.pool.get('sale.shop').search(self.cr, self.uid,[])
            shop_id = self.pool.get('sale.shop').browse(self.cr, self.uid, p_ids)
            pr_ids = self.pool.get('printer.point').search(self.cr, self.uid, [('shop_id','in',shop_id)])
            printer_id = self.pool.get('printer.point').browse(self.cr, self.uid, pr_ids)
        else:
            raise (_('Error'), _('Need a selection for continue'))                
        super(Parser, self).set_context(objects, data, ids, report_type)