# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from itertools import groupby
import tools
import logging
from account_voucher import account_voucher

class purchase_trade(osv.osv):
    
    def _invoiced_line(self, cr, uid, ids, field_name, arg, context=None):
        print field_name, arg
        res = {}
        for trade in self.browse(cr, uid, ids):
            list_line=[]
            if trade.purchase_ids:
                for in_purchase in trade.purchase_ids:
                    for line in in_purchase.invoice_line:
                        if line.product_id.type =='product':
                            line.write({'trade_id1': trade.id})
                            list_line.append(line.id)
            res[trade.id]=list_line
        return res

    def _amount_fob(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=0.0
            if trade.type_liquidation == 'total':
                if trade.purchase_ids:
                    for in_purchase in trade.purchase_ids:
                        for p in in_purchase.invoice_line:
                            if p.product_id.type =='product':
                                subtotal = p.price_subtotal
                                res[trade.id]+=subtotal
            elif trade.type_liquidation == 'partial':
                if trade.purchase_line_ids:
                    for in_purchase in trade.purchase_line_ids:
                        if in_purchase.product_id.type =='product':
                            subtotal = in_purchase.price_subtotal
                            res[trade.id]+=subtotal
        return res


    def _amount_factor(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=0.0
            if trade.amount_total>0 and trade.amount_fob>0:
                res[trade.id]=(trade.amount_total/trade.amount_fob)
            else:
                res[trade.id]=0.00
        return res

    def _amount_factor_iva(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=0.0
            if trade.amount_total>0 and trade.amount_fob>0:
                res[trade.id]=((trade.amount_total+trade.tax_1)/trade.amount_fob)
            else:
                res[trade.id]=0.00
        return res

    
    def _amount_delivery(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            t_ad=0.0
            delivery=0.0
            res[trade.id]=0.0
            if trade.delivery_expenses_ids:
                for in_delivery in trade.delivery_expenses_ids:
                    delivery +=in_delivery.amount_untaxed
            res[trade.id] +=delivery
        return res
    
    def _amount_insurance(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            insurance=0.0
            res[trade.id]=0.0
            if trade.insurance_expenses_ids:
                for in_insurance in trade.insurance_expenses_ids:
                    insurance +=in_insurance.amount_untaxed
            res[trade.id] =+ insurance
        return res

    def _amount_others(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=0.0
            if trade.others_expenses_ids:
                for in_others in trade.others_expenses_ids:
                    res[trade.id]+=in_others.amount_untaxed
        return res
    
    def _amount_cif(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=trade.amount_fob+trade.transport_ad+trade.insurance_ad+trade.adjustment
        return res
            
    def _amount_adjustment(self,cr,uid,ids,name,arg,context={}):

        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=0.0
            if trade.purchase_ids:
                for in_purchase in trade.purchase_ids:
                    for p in in_purchase.invoice_line:
                        if p.product_id.type !='product':
                            subtotal = p.price_subtotal
                            res[trade.id]+=subtotal
            if trade.others_expenses_ids:
                for in_others in trade.others_expenses_ids:
                    res[trade.id]+=in_others.amount_untaxed
        return res
    
    def _amount_dui(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=trade.total_cif+trade.amount_duty+trade.tax_1
        return res        
    
    def _total_dui(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=trade.amount_duty+trade.tax_1+trade.tax_2+trade.amount_safeguards
        return res        
        
    def _total_cif(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=res[trade.id]=trade.amount_fob+trade.transport_ad+trade.insurance_ad+trade.adjustment
        return res        

    def _amount_total(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=trade.total_cif+trade.amount_duty+trade.amount_adjustment+trade.amount_delivery+trade.amount_insurance+trade.tax_2+trade.tax_3+trade.amount_safeguards
        return res

    def _amount_total_liquidation(self,cr,uid,ids,name,arg,context={}):
        res = {}
        for trade in self.browse(cr, uid, ids):
            res[trade.id]=trade.amount_cif+trade.amount_duty+trade.amount_others
        return res
    
    def _check_adjustment(self,cr,uid,ids):
        b=True
        for trade in self.browse(cr, uid, ids):
            if (trade.adjustment < 0):
                b=False
        return b

    def _get_period(self, cr, uid, context={}):        
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid)
        if not periods:
            return None
        else:
            return periods and periods[0] or False

    def _get_journal(self, cr, uid, context={}):
        journal_pool = self.pool.get('account.journal')
        if context.get('journal_id', False):
            return context.get('journal_id')
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            return context.get('search_default_journal_id')
        
        ttype = context.get('type', 'trade_liquidation')
        res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)
        return res and res[0] or False

    def _get_one_step(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        one_step = False
        if curr_user.company_id.one_step:
                one_step =  curr_user.company_id.one_step
        return one_step


    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.printer_point_ids:
            if s.shop_id:
                return s.shop_id.id 
        return None
        
    _name = 'purchase.trade'
    _columns = {
        'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft':[('readonly',False)]}), 
        'country_id':fields.many2one('res.country', 'Origin Country',readonly=True, states={'draft':[('readonly',False)]}),
        'picking_id': fields.one2many('stock.picking', 'trade_id', 'Related Picking', readonly=True, states={'draft':[('readonly',False)]}),
        'delivery_partner': fields.many2one('res.partner','Broker',readonly=True, states={'draft':[('readonly',False)]}),
        'deposit_partner': fields.many2one('res.partner','Deposit Warehouse',readonly=True, states={'draft':[('readonly',False)]}),
        'origin_order': fields.datetime('Ordered Date',readonly=True, states={'draft':[('readonly',False)]}),
        'arrival_date': fields.datetime('Arrival Date',readonly=True, states={'draft':[('readonly',False)]}),
        'confirm_date': fields.datetime('Confirmation Date'),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, readonly=True,states={'draft':[('readonly',False)]},domain=[('type','=','trade_liquidation')]),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'dui':fields.char('DAO', size=30,readonly=True, states={'draft':[('readonly',False)]}, required=True),
        'endorsement':fields.char('Endorsement', size=40,readonly=True, states={'draft':[('readonly',False)]}),
        'fob': fields.float('FOB',readonly=True, states={'draft':[('readonly',False)]}),
        'tax_1': fields.float('IVA',readonly=True, states={'draft':[('readonly',False)]}),
        'tax_2': fields.float('FODINFA',readonly=True, states={'draft':[('readonly',False)]}),
        'total_dui': fields.function(_total_dui,method=True, type='float', digits_compute=dp.get_precision('Account'), string='Total DAO', store=True,readonly=True), 
        'total_cif': fields.function(_total_cif,method=True, type='float', digits_compute=dp.get_precision('Account'), string='Total CIF', store=True,readonly=True), 
        'user_id': fields.many2one('res.users', 'Buyer',readonly=True, states={'draft':[('readonly',False)]}),
        'transport_ad': fields.float("Delivery",readonly=True, states={'draft':[('readonly',False)]},help="Use this field if you no have a invoice for Delivery",digits_compute=dp.get_precision('Account')),
        'insurance_ad': fields.float("Insurance",readonly=True, states={'draft':[('readonly',False)]},help="Use this field if you no have a invoice for Insurance",digits_compute=dp.get_precision('Account')),
        'adjustment': fields.float("Adjustment",readonly=True, states={'draft':[('readonly',False)]},digits_compute=dp.get_precision('Account')),
        "amount_adjustment": fields.function(_amount_adjustment, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Amount adjustment",store=True,readonly=True, states={'draft':[('readonly',False)]}),
        'incoterm': fields.many2one('stock.incoterms', 'Incoterm', help="Incoterm which stands for 'International Commercial terms' implies its a series of sales terms which are used in the commercial transaction.", required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'purchase_ids': fields.one2many('account.invoice','trade_id1','Invoices', domain=[('tpurchase','=','trade'),('type','=','in_invoice')],readonly=True, states={'draft':[('readonly',False)]}),
        'delivery_expenses_ids': fields.one2many('account.invoice','trade_id2','Delivery Expenses', domain=[('tpurchase','=','trade'),('type','=','in_invoice')],readonly=True, states={'draft':[('readonly',False)]}),
        'insurance_expenses_ids': fields.one2many('account.invoice','trade_id3','Insurance Expenses', domain=[('tpurchase','=','trade'),('type','=','in_invoice')],readonly=True, states={'draft':[('readonly',False)]}),
        'others_expenses_ids': fields.one2many('account.invoice','trade_id4','Others Expenses', domain=[('tpurchase','=','trade'),('type','=','in_invoice')],readonly=True, states={'draft':[('readonly',False)]}),
        "method": fields.selection([("qty","Quantity"),("amount","Amount"),("weight","Weight"),("volume","Volume")],"Allocation Method",readonly=True, states={'draft':[('readonly',False)]}),
        "notes": fields.text("Notes"),
        "amount_fob": fields.function(_amount_fob, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Amount Fob",store=True,readonly=True),
        "amount_delivery": fields.function(_amount_delivery, method=True, type="float", digits_compute=dp.get_precision('Account'), string="Amount Delivery",store=True,readonly=True),
        "amount_insurance": fields.function(_amount_insurance, method=True, type="float",digits_compute=dp.get_precision('Account'), string="Amount Insurance",store=True,readonly=True),
        "amount_others": fields.function(_amount_others, method=True, type="float",digits_compute=dp.get_precision('Account'), string="Amount Others",store=True,readonly=True),        
        'amount_cif': fields.function(_amount_cif, method=True, type='float', digits_compute=dp.get_precision('Account'), string='Amount CIF', store=True,readonly=True), 
        "amount_duty":fields.float("Amount Duty",readonly=True, states={'draft':[('readonly',False)]},help="Amount Duty",digits_compute=dp.get_precision('Account')),
        "amount_safeguards":fields.float("Salvaguardas",readonly=True, states={'draft':[('readonly',False)]},help="Monto de Salvaguardas",digits_compute=dp.get_precision('Account')),        
        "amount_dui": fields.function(_amount_dui, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Amount DAO",store=True,readonly=True),
        "amount_total": fields.function(_amount_total, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Amount Total",store=True,readonly=True),
        "amount_total_liquidation": fields.function(_amount_total_liquidation, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Total Liquidation",store=True,readonly=True),
        'company_id': fields.many2one('res.company','Company',required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'landed_id': fields.many2one('landed.cost','Landed Cost',readonly=True),
        'location_id': fields.many2one('stock.location', 'Destination', domain=[('usage','<>','view')],readonly=True, states={'draft':[('readonly',False)]}),
        #'purchase_line_ids': fields.function(_invoiced_line, method=True, type='one2many', obj='account.invoice.line', string='Invoiced Line', readonly=True, states={'draft':[('readonly',False)]}),
        'purchase_line_ids': fields.one2many('account.invoice.line','trade_id1','Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'dui_id':fields.many2one('account.invoice','DAO id',readonly=True),
        'factor_trade': fields.function(_amount_factor, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Factor",store=True,readonly=True),
        'factor_iva': fields.function(_amount_factor_iva, method=True, type="float",digits_compute=dp.get_precision('Account'),string="Factor con IVA",store=True,readonly=True),        
        'tax_3': fields.float("Impuesto ISD",readonly=True, states={'draft':[('readonly',False)]},help="Ingresar el valor de Impuesto de Salida de Divisas, en caso de aplicar",digits_compute=dp.get_precision('Account')),
        'move_id': fields.many2one('account.move','Move',readonly=True),
        'one_step':fields.boolean('Un solo proceso', required=False, help="Si activa este campo, todos los procesos de aprobación se ejecutarán simultáneamente."),
        'type_liquidation': fields.selection([
            ('total', 'Total'),
            ('partial', 'Partial')], 'Type of Liquidation'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('waiting_date', 'Waiting Schedule'),
            ('paid_dui', 'Paid DAO'),
            ('progress', 'In Progress'),
            ('waiting_mail', 'Send Mail'),
            ('done', 'Done'),
            ('cancel', 'Canceled')], 'Trade Order State',readonly=True),
                    }
    
    _defaults={
        'shop_id': _get_shop,
        'state': lambda *a: 'draft',
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
        'incoterm': lambda *a: '4',
        'period_id': _get_period,
        'journal_id':_get_journal,
        'one_step':_get_one_step,
        'method':'amount',
        'delivery_partner':lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).company_id.partner_id_trade.id,
    }
    
    _order ="origin_order desc"
    _rec_name = 'dui'
    _constraints = [
        (_check_adjustment,'The adjustment must be a positive number',['adjustment']),
        ]
    
    def comprobate_invoice(self, cr, uid, invoice, context={}):
        name=context.get('name','')
        if invoice.amount_untaxed <= 0:
            raise osv.except_osv(_('Error!'), _("Amount of %s Invoice %s is 0.")%(name, invoice.number))
        elif invoice.state in ('draft','cancel'):
            raise osv.except_osv(_('Error!'), _("Invoice have invalid state : draft or cancel. Please Check"))
        return True

    def button_one_step(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        self.button_generate_pay(cr,uid,ids,context)
        self.button_approve(cr,uid,ids,context)
        self.button_done(cr,uid,ids,context)
        #self.button_send_mail(cr,uid,ids,context)
        return True
        
    def button_approve(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        invoice_obj = self.pool.get('account.invoice')
        invoice_ids=[]
        other_ids=[]
        sum = 0.00
        for trade in self.browse(cr, uid, ids, context):
            for trade_line in trade.purchase_line_ids:
                if trade_line.product_id.type =='product':
                    sum += trade_line.amount_total
            if round(sum,2) != round(trade.amount_fob,2):
                raise osv.except_osv(_('Error !'), _('Valor FOB difiere del total de productos.'))
            self.button_process(cr,uid,ids,context)
            for purchase in trade.purchase_ids:
                self.comprobate_invoice(cr, uid, purchase, {'name':'Purchase'})
                invoice_ids.append(purchase.id)
                if invoice_ids:
                    pending = invoice_obj.search(cr, uid, [('trade_id1', '=', False)])
                    if not pending:
                        self.pool.get('account.invoice').write(cr, uid, invoice_ids, {'liquidated':True})                
            for delivery in trade.delivery_expenses_ids:
                self.comprobate_invoice(cr, uid, delivery, {'name':'Delivery'})
                other_ids.append(delivery.id)
            for insurance in trade.insurance_expenses_ids:
                self.comprobate_invoice(cr, uid, insurance, {'name':'Insurance'})
                other_ids.append(insurance.id)
            for others in trade.others_expenses_ids:
                self.comprobate_invoice(cr, uid, others, {'name':'Other Expenses'})
                other_ids.append(others.id)                
        invoice_obj.write(cr, uid, other_ids, {'liquidated':True})
        self.write(cr, uid, ids, {'confirm_date':time.strftime('%Y-%m-%d %H:%M:%S'), 'state':'waiting_date'}, context)
        
        return True
    
    def onchange_line_ids(self, cr, uid, ids, line_dr_ids=False,type='', context=None):
        invoice_obj = self.pool.get('account.invoice')
        purchase_obj = self.pool.get('purchase.trade')
        res = {}
        lines_ids = []
        lines = []
        if type == 'total':
            if line_dr_ids[0][2]:
                for lines in line_dr_ids[0][2]:            
                    invoice = invoice_obj.browse(cr,uid,lines)
                    for invoice_line in invoice.invoice_line:
                        if invoice_line.product_id.type =='product':
                            lines_ids.append(invoice_line.id)               
                if lines_ids:
                        lines=[[6, 0, [c for c in lines_ids]]]    
                return {'value': {'purchase_line_ids':lines}}       
        return {'value': {'purchase_line_ids':lines}}
    
    
    def onchange_date(self, cr, user, ids, date, context={}):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        period_pool = self.pool.get('account.period')
        pids = period_pool.search(cr, user, [('date_start','<=',date), ('date_stop','>=',date)])
        if not pids:
            return {}
        return {
            'value':{
                'period_id':pids[0]
            }
        }
        
    def create_invoice_line(self,cr, uid, values):
        return self.pool.get('account.invoice.line').create(cr, uid, values)

    def button_generate_pay(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        journal_pool = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        move_obj_line = self.pool.get('account.move.line')
        wf_service = netsvc.LocalService('workflow')
        j_id = journal_pool.search(cr, uid, [('type', '=', 'trade_liquidation')], limit=1)
        journal_id =journal_pool.browse(cr,uid,j_id[0])
        move_id = []

        for trade in self.browse(cr, uid, ids, context):
            lines_invoice=[]
            check_total = 0.00
            context.update({'journal_type':'other_moves',
                            'type':'in_invoice'})
            if trade.origin_order:
                date=trade.origin_order
            else:
                date=time.strftime('%Y-%m-%d %H:%M:%S')
            payment_term=self.pool.get('account.payment.term').search(cr, uid, [('default','=',True)], limit=1)
            sustent_id=self.pool.get('sri.tax.sustent').search(cr, uid, [('code','=','00')])
            
            if not trade.company_id.property_account_duty:
                raise osv.except_osv(_('Acción Inválida!'), _('Configure las cuentas contables relacionadas con la liquidación de Importaciones '))
            if not trade.company_id.partner_id_trade:
                raise osv.except_osv(_('Acción Inválida!'), _('Configure la empresa relacionada para el pago de las tasas aduaneras'))
            values=self.pool.get('account.invoice').onchange_partner_id(cr, uid, uid, 'in_invoice', trade.delivery_partner.id, trade.origin_order, payment_term and payment_term[0] or None, False, trade.company_id.id,context)['value']
            values.update({
                         'shop_id':trade.shop_id.id,
                         'account_analytic_id':trade.shop_id.project_id.id,
                         'partner_id':trade.delivery_partner.id,
#                         'address_invoice_id': invoice_addr_id,
#                         'address_contact_id': contact_addr_id,
                         'tpurchase':'trade',
                         'journal_id': journal_id.id,
                         'tax_sustent': sustent_id and sustent_id[0] or None,
                         'invoice_number_in':'DAO-'+trade.shop_id.number_sri +'-'+ trade.dui,
                         'currency_id':trade.company_id.currency_id.id,
                         'date_invoice2':trade.origin_order or time.strftime('%Y-%m-%d %H:%M:%S'),
                         'date_invoice': trade.origin_order or time.strftime('%Y-%m-%d'),
                         'payment_term':payment_term and payment_term[0] or None,
                         'account_id':trade.company_id.property_account_duty.id,
                         'check_total':0.00,
                         'company_id':trade.company_id.id,
                         'fiscal_position':trade.delivery_partner.property_account_position.id,
                         'period_id':trade.period_id.id,
                         'origin':'Liquidación de ' + str(trade.dui),
                         'name':'Liquidación de ' + str(trade.dui),
                         'reference_type':'none',
                         })
            dui_id=self.pool.get('account.invoice').create(cr, uid, values,context)
            if not (trade.company_id.property_account_tax_duty and trade.company_id.property_account_duty_account):
                raise osv.except_osv(_('Invalid action!'), _('Configure payable, tax and dutty account for company'))
            if trade.tax_1 > 0:
                lines_invoice.append(self.create_invoice_line(cr, uid, {
                                                 'name': 'Liquidación de IVA de Importaciones',
                                                 'origin': 'Liquidación ' + str(trade.dui),
                                                 'account_id': trade.company_id.property_account_tax_duty.id,
                                                 'price_unit': trade.tax_1 or 0.00,
                                                 'quantity': 1,
                                                 'price_product': trade.tax_1 or 0.00,
                                                 'price_subtotal': trade.tax_1 or 0.00,
                                                 'account_analytic_id':trade.shop_id.project_id.id,
                                                 }))
                check_total += trade.tax_1
            if trade.amount_duty > 0:
                lines_invoice.append(self.create_invoice_line(cr, uid, {
                                                 'name': 'Liquidación de Aranceles pagados en Importaciones',
                                                 'origin': 'Liquidación' + str(trade.dui),
                                                 'account_id': trade.company_id.property_account_duty_account.id,
                                                 'price_unit': trade.amount_duty or 0.00,
                                                 'quantity': 1,
                                                 'price_subtotal': trade.amount_duty or 0.00,
                                                 'price_product': trade.amount_duty or 0.00,
                                                 'account_analytic_id':trade.shop_id.project_id.id,                                 
                                                 }))
                check_total += trade.amount_duty
            if trade.amount_safeguards > 0:
                lines_invoice.append(self.create_invoice_line(cr, uid, {
                                                 'name': 'Liquidación de Salvaguardas pagados en Importaciones',
                                                 'origin': 'Liquidación' + str(trade.dui),
                                                 'account_id': trade.company_id.property_account_duty_account.id,
                                                 'price_unit': trade.amount_safeguards or 0.00,
                                                 'quantity': 1,
                                                 'price_subtotal': trade.amount_safeguards or 0.00,
                                                 'price_product': trade.amount_safeguards or 0.00,
                                                 'account_analytic_id':trade.shop_id.project_id.id,                                 
                                                 }))
                check_total += trade.amount_safeguards
            if trade.tax_2 >0 :
                lines_invoice.append(self.create_invoice_line(cr, uid, {
                                                 'name': 'FODINFA',
                                                 'origin': 'Liquidación of' + str(trade.dui),
                                                 'account_id': trade.company_id.property_account_duty_account.id,
                                                 'price_unit': trade.tax_2,
                                                 'quantity': 1,
                                                 'price_product':trade.tax_2,
                                                 'price_subtotal':trade.tax_2,
                                                 'account_analytic_id':trade.shop_id.project_id.id,                                        
                                                 }))
                check_total += trade.tax_2
            if lines_invoice:
                self.pool.get('account.invoice').write(cr, uid, [dui_id], {'check_total':check_total, 'invoice_line':[[6, 0, lines_invoice]]},context)
                wf_service.trg_validate(uid, 'account.invoice', dui_id, 'invoice_open', cr)
                trade.write({'dui_id':dui_id})
            else:
                self.pool.get('account.invoice').unlink(cr, uid, [dui_id])
        
            if trade.tax_3 >0 :
                    if not trade.company_id.property_tax_payment_isd or not trade.company_id.partner_id_taxes:
                        raise osv.except_osv(_('¡Error!'), _("Por favor, defina al ente de control tributario y la cuenta por pagar del Impuesto de Salida de Divisas."))
                    move_id = move_obj.create(cr, uid,
                                            {'name': trade.dui, 
                                             'journal_id': trade.journal_id.id,
                                             'partner_id':trade.company_id.partner_id.id,
                                             'address_id':trade.shop_id.partner_address_id.id,
                                             'shop_id': trade.shop_id.id,
                                             'company_id':trade.company_id.id,
                                             'period_id': trade.period_id.id,
                                             'details': 'LIQUIDACIÓN DE IMPORTACIÓN #'+trade.dui,
                                             'ref': 'OTROS VALORES PAGADOS'})
                    move_obj_line.create(cr, uid,
                            {'journal_id': trade.journal_id.id,
                            'currency_id':trade.company_id.currency_id.id,
                            'company_id':trade.company_id.id,
                            'state': 'valid',
                            'debit': trade.tax_3,
                            'credit':0.00,
                            'account_id': trade.company_id.property_account_move_duty.id,
                            'period_id': trade.period_id.id,                                        
                            'date': time.strftime('%Y-%m-%d'),
                            'move_id':move_id,
                            'quantity': 1.00,
                            'reference': trade.dui,
                            'name': 'PROVISION DE ISD DE LIQUIDACIÓN DE IMPORTACIÓN',
                            'partner_id': trade.company_id.partner_id.id,
                            'shop_id': trade.shop_id.id,
                            'active':True
                            })
                    move_obj_line.create(cr, uid,
                            {'journal_id': trade.journal_id.id,
                            'currency_id':trade.company_id.currency_id.id,
                            'company_id':trade.company_id.partner_id.id,
                            'state': 'valid',
                            'debit': 0.00,
                            'credit':trade.tax_3,
                            'account_id': trade.company_id.property_tax_payment_isd.id,
                            'period_id': trade.period_id.id,                                        
                            'date': time.strftime('%Y-%m-%d'),
                            'move_id':move_id,
                            'quantity': 1.00,
                            'reference': trade.dui,
                            'name': 'PROVISION DE ISD DE LIQUIDACIÓN DE IMPORTACIÓN',
                            'partner_id': trade.company_id.partner_id_taxes.id,
                            'shop_id': trade.shop_id.id,
                            'active':True
                        })
                    move_obj.post(cr,uid,[move_id],context)
            
        self.write(cr, uid, ids, {'state':'paid_dui', 'origin_order': date, 'move_id':move_id}, context)
        return True

    def button_process(self, cr, uid, ids, context=None):
        landed_obj=self.pool.get('landed.cost')
        landed_id=None
        for trade in self.browse(cr, uid, ids, context):
            if trade.landed_id:
                pass
            amount_trade = trade.amount_delivery+trade.amount_insurance+trade.adjustment+trade.amount_duty+trade.transport_ad+trade.insurance_ad+trade.tax_2+trade.amount_safeguards
            amount_other = trade.amount_others+trade.tax_3
            landed_id=landed_obj.create(cr, uid, {'name': trade.dui,
                                                  'method':trade.method,
                                                  'date':time.strftime('%Y-%m-%d'),
                                                  'amount':amount_trade,
                                                  'other':amount_other,
                                                  })
            if not trade.purchase_line_ids:
                landed_obj.unlink(cr, uid,landed_id, context)
            else:
                for line in trade.purchase_line_ids:
#                    if line.amount_untaxed >0:
                    if line.price_subtotal >0 and line.quantity >0 and line.product_id.type =='product':                        
                        self.pool.get('landed.cost.line').create(cr, uid, {'cost_id':landed_id,
                                                                           'invoice_line_id':line.id,
                                                                           'cost':0.0,
                                                                           'other':0.0,
                                                                           })
                landed_obj.btn_post(cr, uid,[landed_id], context)
        self.write(cr, uid, ids, {'state':'progress', 'landed_id':landed_id}, context)
        return True

    def button_send_mail(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        for trade in self.browse(cr,uid,ids,context):
            for pick in trade.picking_id:
                if pick.state =='draft':
                    #self.pool.get('out.mail').send_mail(cr,uid,[],{'active_id':trade.picking_id.id,'active_model':'stock.picking','state':'done','name':'Trade Liquidation'})
                    xml_id = 'email_template_edi_picking_trade_request'
                    template_ids = mod_obj.get_object_reference(cr, uid, 'stock', xml_id)
                    self.pool.get('email.template').send_mail(cr,uid,template_ids[1],pick.id,False,context)                                    
            self.write(cr,uid,trade.id,{'state':'done'})
            return True
            
    def button_done(self, cr, uid, ids, context=None):
        picking_id=None
        for trade in self.browse(cr, uid, ids, context):
            if not trade.user_id:
                raise osv.except_osv(_('Error!'), _("You can define a account for tax VAT Duty Account in Company Properties"))
            if trade.location_id:
                location_search = trade.location_id.id                
                if location_search:
                    shop_location_id = self.pool.get('ubication').search(cr,uid,[('location_id','=',location_search)])[0]
                if shop_location_id:
                    location_ids = self.pool.get('ubication').browse(cr,uid,shop_location_id).shop_ubication_id.id
                    if location_ids:
                        shop_ids = self.pool.get('sale.shop').search(cr,uid,[('shop_ubication_id','=',location_ids)])
                        if shop_ids:
                            shop_ids = shop_ids[0]
                        else:
                            shop_ids = 1
                        if shop_ids:
                            shop_id = self.pool.get('sale.shop').browse(cr,uid,shop_ids).id
                    else:
                        raise osv.except_osv(_('Warning!'), _('No hay tienda definida para la ubicación elegida'))                
            pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.in')
            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                'name': pick_name,
                'origin': trade.dui+':'+trade.country_id.name,
                'type': 'in',
                'invoice_state': 'none',
                'move_type': 'one',
                'shop_id':shop_id,
                'date':trade.confirm_date,
                'company_id': trade.company_id.id,
                'digiter_id': trade.user_id.id,
                'partner_id':trade.company_id.partner_id.id,
                'address_id':trade.company_id.partner_id.address[0].id,
                'trade_id':trade.id,
                'international':True,
                'location_id':trade.location_id.id,
                'authorized':True,
                'move_lines' : [],                            
            })
            todo_moves = []
            for line in trade.purchase_line_ids:
                if not line.product_id:
                    continue
                if line.product_id.product_tmpl_id.type in ('product', 'consu','catalog'):
                    location=None
                    dest = trade.location_id.id
                    if line.purchase_line_id:
                        if line.purchase_line_id.order_id.state in ('draft','cancel'):
                            raise osv.except_osv(_('Error!'), _(("The purchase order %s is in state not validate")%(line.purchase_line_id.order_id.name)))
                        if line.purchase_line_id.order_id.location_id:
                            dest= line.purchase_line_id.order_id.location_id.id
                    price_total=line.price_unit+line.cost_expense_unit+line.amount_tax_duty+line.amount_others
                    if trade.confirm_date:
                        date_expected=trade.confirm_date
                    else:
                        date_expected=time.strftime('%Y-%m-%d %H:%M:%S')
                    if line.invoice_id.partner_id.property_stock_supplier:
                        location=line.invoice_id.partner_id.property_stock_supplier.id
                    ubication=None
                    ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',line.product_id.id),('location_ubication_id','=',dest)])
                    if ubication_ids:
                        ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
                    else:
                        ubica_id = self.pool.get('ubication').search(cr,uid,[('location_id','=',dest)])
                        if ubica_id:
                            ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',line.product_id.id),('ubication_id','=',ubica_id[0])])
                            if ubication_ids:
                                ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
                    move = self.pool.get('stock.move').create(cr, uid, {
                        'name': line.name + ': ' +(trade.dui or ''),
                        'product_id': line.product_id.id,
                        'product_qty': line.quantity,
                        'product_uos_qty': line.quantity,
                        'qty_receive': (not trade.company_id.review_qty) and line.quantity or 0.0,
                        'authorized': True,
                        'product_uom': line.uos_id.id,
                        'product_uos': line.uos_id.id,
                        'date': date_expected,
                        'date_expected': date_expected,
                        'location_id': location,
                        'location_dest_id': dest,
                        'partner_id': line.invoice_id.partner_id.id,
                        'note': line.invoice_id.number,
                        'picking_id': picking_id,
                        'state': 'draft',
                        'company_id': trade.company_id.id,
                        'price_unit': price_total,
                        'price_unit_trade': price_total,
                        'invoice_line_id': line.id,
                        'ubication_id':ubication
                    })
                todo_moves.append(move)
            if not todo_moves:
                self.pool.get('stock.picking').unlink(cr, uid, [picking_id],context)
            else:
                self.pool.get('stock.move').action_confirm(cr, uid, todo_moves)
        cr.commit()
        self.write(cr, uid, ids, {'state':'waiting_mail'})
        return True
    
    def button_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService('workflow')
        move_obj = self.pool.get('account.move')
        for trade in self.browse(cr, uid, ids, context):
            invoices_ids = []
            if trade.landed_id:
                landed_id = self.pool.get('landed.cost').browse(cr,uid,[trade.landed_id.id])
                if landed_id:
                    self.pool.get('landed.cost').btn_cancel(cr, uid,[trade.landed_id.id], context)
            if trade.dui_id:
                if trade.dui_id.state=='paid':
                    raise osv.except_osv(_('Error!'), _("El DAO %s de %s ya fue pagado.")%(trade.dui_id.invoice_number, trade.dui_id.partner_id.name))
                elif trade.dui_id.state=='open':
                    wf_service.trg_validate(uid, 'account.invoice', trade.dui_id.id, 'invoice_cancel', cr)
#                    raise osv.except_osv(_('Error!'), _("El DAO %s de %s ya fue pagado.")%(trade.dui_id.invoice_number, trade.dui_id.partner_id.name))
                else:
                    self.pool.get('account.invoice').unlink(cr,uid,[trade.dui_id.id],context)
            if trade.purchase_ids:
                for purchase in trade.purchase_ids:
                    self.pool.get('account.invoice').write(cr, uid, [purchase.id],{'liquidated':False})
                    invoices_ids.append(purchase.id)
            if trade.delivery_expenses_ids:
                for delivery in trade.delivery_expenses_ids:
                    self.pool.get('account.invoice').write(cr, uid, [delivery.id],{'liquidated':False})
                    invoices_ids.append(delivery.id)
            if trade.insurance_expenses_ids:
                for insurance in trade.insurance_expenses_ids:
                    self.pool.get('account.invoice').write(cr, uid, [insurance.id],{'liquidated':False})
                    invoices_ids.append(insurance.id) 
            if trade.others_expenses_ids:
                for others in trade.others_expenses_ids:
                    self.pool.get('account.invoice').write(cr, uid, [others.id],{'liquidated':False})
                    invoices_ids.append(others.id)                     
            if trade.picking_id:
                if invoices_ids:
                    context.update({'invoices_ids':invoices_ids})
                self.button_cancel_picking(cr,uid,ids,context)
            if trade.move_id:
                move_obj.button_cancel(cr, uid, [trade.move_id.id], context=context)
                move_obj.unlink(cr, uid, [trade.move_id.id], context=context)
        self.write(cr, uid, ids, {'state':'cancel','landed_id':False,'move_id':False}, context)
        return True

    def button_cancel_picking(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('account.move')
        journal_id = self.pool.get('account.journal').search(cr,uid,[('type','=','stock')])[0]
        wf_service = netsvc.LocalService("workflow")
        for trade in self.browse(cr, uid, ids, context):
            for pick in trade.picking_id :
                if pick.state=='cancel':
                    continue
                self.pool.get('stock.picking').action_drafted(cr, uid,[pick.id], context={})
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            move_ids = move_obj.search(cr,uid,[('ref','=',pick.name),('journal_id','=',journal_id),('state','!=','cancel')])
            if move_ids:
                move_obj.button_cancel(cr, uid, move_ids, context=context)
                move_obj.unlink(cr, uid, move_ids, context=context)            
            trade.write({'state':'progress'})
        return True
    
    def button_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'}, context)
        for trade in self.browse(cr, uid, ids, context):
            if trade.landed_id:
                self.pool.get('landed.cost').unlink(cr, uid,[trade.landed_id.id], context)
        return True
    
purchase_trade()