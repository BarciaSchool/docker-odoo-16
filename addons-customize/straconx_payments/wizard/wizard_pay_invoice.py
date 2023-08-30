# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################



from osv import fields, osv
from tools.translate import _
import time
import decimal_precision as dp
import netsvc

class wizard_pay_invoice(osv.osv_memory):
    _name = "wizard.invoice.pay"
    
    _columns = {
                'partner_id':fields.many2one('res.partner', 'partner', required=False),
                'journal_id':fields.many2one('account.journal', 'Journal', required=False),
                'payment_ids':fields.one2many('wizard.invoice.pay.lines', 'wizard_id', 'payments', required=False),
                'amount': fields.float('Total amount', digits=(16,2)),
                'company_id': fields.many2one('res.company','Company'),
                'beneficary': fields.char('Beneficiary', size=200),
                'type':fields.selection([('payment','Payment'),('receipt','Receipt'),],'Default Type')
                }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        if 'value' not in context.keys():
            for obj in objs:
                journal_ids=self.pool.get('account.journal').search(cr, uid, [('type','=','moves')], limit=1)
                res['partner_id']=obj.partner_id.id
                res['amount']=obj.amount_total
                res['journal_id']=journal_ids and journal_ids[0] or None
        else:
            res = context['value']
        return res
    
    def create_voucher(self, cr, uid, invoice, wizard, context={}):
        line_ids=[]
        line_cr_ids=[]
        line_dr_ids=[]
        voucher_obj=self.pool.get('account.voucher')
        vals_onchange=voucher_obj.on_change_receipt(cr, uid, [],None, 'receipt', context)
        values=vals_onchange['value']
        vals_onchange=voucher_obj.onchange_partner_id(cr, uid, [],wizard.partner_id.id, wizard.journal_id.id,wizard.amount,None,'receipt',time.strftime('%Y-%m-%d'),{'invoice_id':invoice.id})
        values.update(vals_onchange['value'])
        for line in values.get('line_ids',[]):
            line.update({'reconcile':True,
                         'amount':line.get('amount_unreconciled',0.0)})
            line_ids.append((0,0,line))
        for line in values.get('line_dr_ids',[]):
            line.update({'reconcile':True,
                         'amount':line.get('amount_unreconciled',0.0)})
            line_dr_ids.append((0,0,line))
        for line in values.get('line_cr_ids',[]):
            line.update({'reconcile':True,
                         'amount':line.get('amount_unreconciled',0.0)})
            line_cr_ids.append((0,0,line))
        values.update({'partner_id':wizard.partner_id.id,
                       'line_ids':line_ids,
                       'line_dr_ids':line_dr_ids,
                       'line_cr_ids':line_cr_ids,
                       'amount':wizard.amount,
                       'journal_id':wizard.journal_id.id,
                       'name':invoice.origin or invoice.name or None,
                       'reference':invoice.number or None,})
        context['type']='receipt'
        voucher_id=voucher_obj.create(cr, uid, values, context)
        return voucher_id
        
    
    def pay(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        wf_service = netsvc.LocalService("workflow")
        invoice = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
        wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_open', cr)
        for wizard in self.browse(cr, uid, ids, context):
            if not wizard.payment_ids:
                raise osv.except_osv(_('Error!'),_('You must entered at least one payment'))
            voucher_id=self.create_voucher(cr, uid, invoice, wizard, context)
            for pay in wizard.payment_ids:
                self.pool.get('account.payments').create(cr, uid, {
                   'mode_id':pay.mode_id.id,
                   'type':pay.type,
                   'name':pay.name,
                   'beneficiary':pay.beneficiary,
                   'received_date':pay.received_date,
                   'deposit_date':pay.deposit_date,
                   'partner_id':pay.partner_id.id,
                   'amount':pay.amount,
                   'amount_received':pay.amount_received,
                   'authorization_credit':pay.authorization_credit,
                   'bank_account_id':pay.bank_account_id.id,
                   'bank_id':pay.bank_id.id,
                   'required_bank':pay.required_bank,
                   'required_document':pay.required_document,
                   'vouch_id':voucher_id,
               })
            res=self.pool.get('account.voucher').proforma_voucher_1(cr, uid, [voucher_id],context)
        return res    
wizard_pay_invoice()

class payment(osv.osv_memory):
    _name = "wizard.invoice.pay.lines"
    _inherit="account.payments"
    _columns = {
                'wizard_id':fields.many2one('wizard.invoice.pay', 'wizard', required=False),
                }
    _defaults={'type':'receipt'}

payment()
