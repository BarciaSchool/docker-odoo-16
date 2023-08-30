# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A
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
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc

sql="""SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo 
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
    }
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        res=super(account_invoice,self)._get_journal(cr,uid,context)
        if not res:
            jnl_id=[]
            if context.get('journal_type',False)=='debit_note':
                jnl_id=self.pool.get('account.journal').search(cr,uid,[('type','=','debit_note')])
                return jnl_id and jnl_id[0] or None
        else:
            return res
    
    def _document_type(self, cr, uid, context=None):
        if context is None:
            context={}
        jnl_id=[]
        res=super(account_invoice,self)._document_type(cr,uid,context)
        if context.get('journal_type',False)=='debit_note':
            jnl_id=self.pool.get('sri.document.type').search(cr,uid,[('code','=','05')])
            return jnl_id and jnl_id[0] or None
        return res

    def onchange_shop(self, cr, uid, ids, company=None, shop=None, type=None, context=None):
        if context is None:
            context = {}
        values={'value':{},'domain':{}}
        box_ids=[]
        shop_ids = []
        box_id=[]
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in user.printer_point_ids:
            box_ids.append(s.id)
            if s.shop_id:
                shop_ids.append(s.shop_id.id)
        
        if shop and company:
            shop_id = self.pool.get('sale.shop').browse(cr, uid, shop)        
            if shop_id.company_id.id != company:
                sh_ids = self.pool.get('sale.shop').search(cr, uid, [('company_id','=',company)])[0]
                shop_id = sh_ids
                shop = shop_id 
                values['value']['shop_id']=shop
        if shop:
            if type=='out_invoice':
                cr.execute(sql,(shop,'sale'))
            elif type=='in_invoice':
                if context.get('journal_type','purchase') == 'purchase_liquidation':
                    cr.execute(sql,(shop,'purchase_liquidation'))
                elif context.get('journal_type','purchase') == 'purchase':
                    cr.execute(sql,(shop,'purchase'))
                elif context.get('journal_type','purchase') == 'other_moves':
                    cr.execute(sql,(shop,'other_moves'))   
                elif context.get('journal_type','purchase') == 'sale_note':
                    cr.execute(sql,(shop,'sale_note'))                                     
            elif type=='out_refund':
                cr.execute(sql,(shop,'sale_refund'))
            elif type=='in_refund':
                if context.get('journal_type','purchase_refund') == 'debit_note':
                    cr.execute(sql,(shop,'debit_note'))
                else:
                    cr.execute(sql,(shop,'purchase_refund'))
            res=cr.fetchall()
            if not res:
                name=self.pool.get('sale.shop').browse(cr, uid, shop,context).name
                warning = {'title': _('Error!'),'message': _(('You must be selected in the shop %s the journal respective for this document.')%name)}
                return {'value': {'shop_id': None,'account_analytic_id':None}, 'warning':warning}
            values['value']['journal_id']=res[0][0]
            box_id=self.pool.get('printer.point').search(cr, uid, [('id', 'in', box_ids),('shop_id', '=', shop)])     
            if not box_id:
                values['value']['authorization']=None
                values['value']['authorization_sales']=None
                values['value']['account_analytic_id']=None
            else:
                cash=box_id[0]
                if context.get('printer_id',None):
                    cash=context.get('printer_id',None)
                result=self.onchange_cash(cr, uid, ids, company, shop, type, cash,values['value']['journal_id'], context)
                analytic = self.pool.get('sale.shop').browse(cr,uid,shop,context).project_id.id
                values['value'].update(result['value'])
                values['value']['printer_id']=cash
                values['value']['account_analytic_id']=analytic
        domain={'shop_id':[('company_id','=', company)], 'printer_id':[('id','in', box_id)]}
        values['domain']=domain
        return values
    
#    def onchange_cash(self, cr, uid, ids, company=None, shop=None, type=None, printer_id=None, journal=None, context=None):
#        authorization_obj=self.pool.get('sri.authorization')
#        values = {'value':{}}
#        if context is None:
#            context = {}
#        if not (journal and shop):
#            warning = {'title': _('Verify data!'),'message': _("you must select the shop and Journal.")}
#            return {'value': {'printer_id': None}, 'warning':warning}
#        if printer_id:
#            if type in ('out_invoice','out_refund') or (type == 'in_invoice' and context.get('journal_type',None) == 'purchase_liquidation') or (type == 'in_refund' and context.get('journal_type',None) == 'debit_note'):
#                values['value']['pre_printer']=False
#                values['value']['automatic']=False
#                if self.pool.get('printer.point').browse(cr, uid, printer_id, context).type_printer == 'pre':
#                    values['value']['pre_printer']=True
#                elif self.pool.get('printer.point').browse(cr, uid, printer_id, context).type_printer == 'auto':
#                    values['value']['automatic']=True
#                    values['value']['date_invoice2'] = time.strftime('%Y-%m-%d %H:%M:%S')
#                    values['value']['date_invoice'] = time.strftime('%Y-%m-%d')
#                type_journal=self.pool.get('account.journal').browse(cr, uid, journal, context).type
#                dic_auth = authorization_obj.get_auth_only(cr, uid, type_journal, company, shop, printer_id, context=context)
#                if dic_auth['authorization']:
#                    values['value']['authorization'] = authorization_obj.browse(cr, uid, dic_auth['authorization'],context).name
#                    values['value']['authorization_sales'] = dic_auth['authorization']
#                else:
#                    values['value']['authorization'] = None
#                    values['value']['authorization_sales'] = None
#                    values['value']['date_invoice'] = None
#                    values['value']['date_invoice2'] = None
#                values['value']['invoice_number_out'] = None
#        return values
    
    def onchange_type_document(self, cr, uid, ids, document=None, type=None, tpurchase=None, context = None):
        res = {}
        if context is None:
            context={}
        sustent=[]
        if document:
            cr.execute("SELECT sustent_id FROM document_support_rel WHERE document_id = %s",(document,))
            for tup in cr.fetchall():
                sustent+=[n for n in tup]
            if type == "in_invoice":
                if context.get('journal_type','purchase') in ('purchase','purchase_liquidation'):
                    if tpurchase == 'purchase':
                        s=self.pool.get('sri.tax.sustent').search(cr, uid, [('id','in',sustent),('code','=','03')]) 
                    else:
                        s=self.pool.get('sri.tax.sustent').search(cr, uid, [('id','in',sustent),('code','=','02')])
                    res['tax_sustent']=s and s[0] or None
                elif context.get('journal_type','purchase') == 'other_moves':
                    s=self.pool.get('sri.tax.sustent').search(cr, uid, [('id','in',sustent),('code','=','00')])
                    res['tax_sustent']=s and s[0] or None
            elif type == "in_refund":
                if context.get('journal_type',None) == 'debit_note':
                    if tpurchase == 'purchase':
                        s=self.pool.get('sri.tax.sustent').search(cr, uid, [('id','in',sustent),('code','=','03')]) 
                    else:
                        s=self.pool.get('sri.tax.sustent').search(cr, uid, [('id','in',sustent),('code','=','02')])
                    res['tax_sustent']=s and s[0] or None
        return {'value':res, 'domain':{'tax_sustent':[('id','in',sustent)]}}

    def onchange_number(self, cr, uid, ids, number, type=None, shop=None, printer_id=None, journal=None, company=None, date=None, context=None):        
        result = {}
        warning= {}
        if context is None:
            context = {}
        if number:
            if (type in ('out_invoice','out_refund')) or (type == 'in_invoice' and context.get('journal_type',False)=='purchase_liquidation') or (type == 'in_refund' and context.get('journal_type',False)=='debit_note'):
                if not (shop and printer_id and journal):
                    warning = {'title': _('Verify data!'),'message': _("you must select the shop, cash, and Journal.")}
                    return {'value': {'invoice_number_out': ''}, 'warning':warning}
                type_journal=self.pool.get('account.journal').browse(cr, uid, journal, context).type                
                info = self.pool.get('sri.authorization').get_auth(cr, uid, type_journal, shop, printer_id, number, company, date, uid, context)
                if not info['auth']:
                    result['authorization'] = None
                    result['authorization_sales'] = None
                    result['invoice_number_out'] = info['sequence']
                    warning = {
                        'title': _('Warning!'),
                        'message': _('¡No existe autorización para el número de documento ingresado!')
                        }
                else:
                    result['authorization_sales'] = info['auth']
                    result['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, info['auth'],context).name
                    result['invoice_number_out'] = info['sequence']
        return {'value':result, 'warning':warning}
    
    def validate(self,type,journalType):
        res= super(account_invoice, self).validate(type,journalType)
        if(type=="in_refund" or journalType=="debit_note"):
            return True
        return res
    
    
account_invoice()