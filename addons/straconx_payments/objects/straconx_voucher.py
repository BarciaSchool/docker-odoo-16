# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
##############################################################################

from osv import fields, osv
from lxml import etree
import time
from tools.translate import _
import netsvc
import decimal_precision as dp
from openerp.addons.straconx_account.wizard import option
import string

class account_voucher(osv.osv):

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}

        if view_type == 'form':
            if not view_id and context.get('invoice_type'):
                if context.get('invoice_type') in ('out_invoice', 'out_refund'):
                    result = mod_obj.get_object_reference(cr, uid, 'straconx_payments', 'view_vendor_receipt_pos_form_straconx')
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result
            if not view_id and context.get('line_type'):
                if context.get('line_type') == 'customer':
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result

        res = super(account_voucher, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])

        if context.get('type', 'sale') in ('purchase', 'payment'):
            nodes = doc.xpath("//field[@name='partner_id']")
            for node in nodes:
                node.set('domain', "[('supplier', '=', True)]")
        res['arch'] = etree.tostring(doc)
        return res
     
    def _payments(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            total_dr=0
            total_cr=0
            for payment_dr in voucher.line_dr_ids:
                total_dr += payment_dr.amount or 0.0
            for payment_cr in voucher.line_cr_ids:
                total_cr += payment_cr.amount or 0.0
#             diff_amount=total_cr-(voucher.amount+total_dr)
            diff_amount = 0.00
            if voucher.type=='receipt':
                result[voucher.id] = {'other_payments':total_dr or 0.0,
                                      'differ_payments':diff_amount or 0.0,
                                      'total_payments':total_cr,
                                      'amount':total_cr
                                      }
            if voucher.type=='payment':
                result[voucher.id] = {'other_payments':total_cr or 0.0,
                                      'differ_payments':diff_amount or 0.0,
                                      'total_payments':total_dr,
                                      'amount':total_dr
                                      }
        return result
    
    def _total_payments_mode(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            result[voucher.id] = 0.0
            if voucher.payments:
                for pay in voucher.payments:
                    result[voucher.id] += pay.amount or 0.0
        return result

    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.printer_point_ids:
            if s.shop_id:
                return s.shop_id.id 
        return None
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = {}
        jnl_id=[]
        jnl_id=self.pool.get('account.journal').search(cr,uid,[('type','=','moves')])
        res = jnl_id and jnl_id[0] or None
        return res        

    def _get_currency(self, cr, uid, context=None):
        if context is None: context = {}
        journal_pool = self.pool.get('account.journal')
        journal_id = context.get('journal_id', False)
        if journal_id:
            journal = journal_pool.browse(cr, uid, journal_id, context=context)
            if journal.currency:
                return journal.currency.id
        else:
            return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        
    _inherit="account.voucher"
    _columns={
        "invoice_id":fields.many2one('account.invoice','Invoice Reference',readonly=True,states={"draft":[("readonly",False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=False, readonly=True, states={'draft':[('readonly',False)]}),
        'receipt_id':fields.many2one('receipt.salesman', 'Receipt Collector', readonly=True,states={"draft":[("readonly",False)]}),
        "salesman_id":fields.many2one('salesman.salesman','Collector',readonly=True,states={"draft":[("readonly",False)]}),
        'number': fields.char('Number', size=256, readonly=True,),
        "bank_statement": fields.many2one('account.bank.statement','Cash Box',readonly=True,states={"draft":[("readonly",False)]}),
        "received_date": fields.date("Received Date",readonly=True,states={"draft":[("readonly",False)]}),
        "process_date": fields.date("Proccess Date", readonly=True),
        "payments": fields.one2many("account.payments","vouch_id","Payments", readonly=True,states={"draft":[("readonly",False)]}),        
        "beneficiary": fields.char("Beneficiary",size=120,),
        'amount_payment_mode': fields.function(_total_payments_mode, method=True, type='float', string='Amount Payments Mode'),        
        'other_payments': fields.function(_payments, method=True,type="float", string='Other Payments', store=False,multi="other_payments"),
        'differ_payments': fields.function(_payments, method=True,type="float", string='Differ Payments',store=False,multi="other_payments"),        
        'total_payments': fields.function(_payments, method=True,type="float", string='Total Payments', store=False,multi="other_payments"),
        'amount': fields.function(_payments, method=True,type="float", string='Amount', store=False,multi="other_payments"),
        'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft':[('readonly',False)]}),        
        "pay_vouch_id": fields.many2one('payments.voucher','Pagos',),
        "search_docs": fields.boolean('Buscar Documentos Pendientes'),
        'refund_id':fields.many2one('account.invoice', 'Pago en exceso', readonly=True, states={'draft':[('readonly',False)]}),
        'comment': fields.char('Counterpart Comment', size=256, required=False, readonly=True, states={'draft': [('readonly', False)]}),
    }
    
    _defaults={
        "received_date": lambda *a: time.strftime('%Y-%m-%d'),
        "receipt_id": lambda *a: None,
        'journal_id':_get_journal,
        'shop_id': _get_shop,
        'currency_id': _get_currency,
        'amount_payment_mode':0.00,
        'comment': lambda *a: None,
    }
    
    #@profile
    def proforma_voucher_1(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context={}
        invoice=[]
        for voucher in self.browse(cr, uid, ids, context=context):
            wf_service.trg_validate(uid, 'account.voucher', voucher.id, 'proforma_voucher', cr)
            if voucher.invoice_id:
                invoice.append(voucher.invoice_id.id)
        if invoice:
            data = {}
            data['model'] = 'account.invoice'
            data['ids'] = invoice
            context['active_id']=invoice[0]
            context['active_ids']=invoice
            return {
               'type': 'ir.actions.report.xml',
               'report_name': 'print_pos_invoice',
               'datas' : data,
               'context': context,
               'nodestroy': True,
               }
        return True

    #@profile        
    def proforma_voucher(self, cr, uid, ids, context=None):
        voucher_line_obj = self.pool.get('account.voucher.line')
        lines_ids=[]
        invoice_ids = []
        pay = False
        pay_amount = 0.00
        if context is None:
            context = {}
        rs = {'voucher_id': None, 'final_beneficiary':None, 'payment_id':None}
        for voucher in self.browse(cr, uid, ids, context=context):            
            rs = {'voucher_id':voucher.id,
                  'final_beneficiary': voucher.partner_id.id
                  }
            if not voucher.line_dr_ids and not voucher.line_cr_ids:
                raise osv.except_osv(_('Error!'), _('Debe agregar por lo menos un documento para pagar o cobrar!'))
            for payment in voucher.line_dr_ids:
                if payment.amount == 0:
                    lines_ids.append(payment.id)
                else:
                    pay_amount += payment.amount 
            for payment in voucher.line_cr_ids:
                if payment.amount == 0:
                    lines_ids.append(payment.id)
                else:
                    pay_amount += payment.amount
                    pay = self.pool.get('account.payments').search(cr, uid,[('move_id','=',payment.move_line_id.move_id.id)])
                    if pay:
                        rs = {'voucher_id':voucher.id,
                              'final_beneficiary': voucher.partner_id.id,
                              'payments_id': pay[0],
                              'amount': payment.amount
                              }
                        pv_id = self.pool.get('payments.voucher').create(cr, uid, rs, context = context)                        
                        self.write(cr, uid, voucher.id, {'pay_vouch_id':pv_id})
            voucher_line_obj.unlink(cr, uid, lines_ids)
            if pay_amount == 0.00:
                raise osv.except_osv(_('Error!'), _('Debe agregar por lo menos un valor en los documentos para pagar o cobrar!'))
            for line in voucher.line_cr_ids:
                if line.move_line_id.invoice:
                    invoice_ids.append(line.move_line_id.invoice.id)
                    context.update({'invoice_ids':invoice_ids})
            for line in voucher.line_dr_ids:
                if line.move_line_id.invoice:
                    invoice_ids.append(line.move_line_id.invoice.id)
                    context.update({'invoice_ids':invoice_ids})
#            self.pool.get('account.invoice').write(cr,uid,invoice_ids,{})
        return self.action_move_line_create(cr, uid, ids, context=context)

        
    #@profile
    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        if context is None:
            context = {}
        dom = []
        dom2 = []
        mov_li= []
        context_multi_currency = context.copy()
        if date:
            context_multi_currency.update({'date': date})
        if not journal_id:
            journal_id=self.pool.get('account.journal').search(cr, uid, [('type','=','moves')])
            journal_id=journal_id and journal_id[0] or None

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')

        #set default values
        default = {
            'value': {'line_ids': [] ,'line_dr_ids': [] ,'line_cr_ids': [] ,'pre_line': False,'journal_id':journal_id},
        }

        #drop existing lines
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        if line_ids:
            line_pool.unlink(cr, uid, line_ids)

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_aa_id = journal.company_id.property_account_advance_supplier.id
        if not account_aa_id:
            raise osv.except_osv(_('Error!'), _('Debe definir una cuenta contable de anticipo para proveedores!'))
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
#         currency_id = currency_id or journal.company_id.currency_id.id
        if currency_id:
            currency_id = currency_id
        else:
            currency_id = journal.company_id.currency_id.id
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        default['value']['account_id'] = account_id or None

        if journal.type not in ('moves'):
            return default

        total_credit = 0.0
        total_debit = 0.0
        account_type = 'receivable'
        if ttype == 'payment':
            account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            account_type = 'receivable'
            
        invoice_id = context.get('invoice_id', False)
        #Estas variables son asignadas por el módulo de sales para cuando se paga una factura pos por medio de una a varias notas de credito
        pos = context.get('pos', False)
        credit_notes_pos = context.get('credit_notes', [])
        if not context.get('move_line_ids', False):
            if pos:
                domain=[('account_id.type', '=', account_type), ('reconcile_id', '=', False),('partner_id','=',partner_id)]
                context.update({'pos':True})
            else:
                domain=[('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False),('partner_id','=',partner_id)]
            if invoice_id:
                # para aplicar este cambio, el modulo debe de depender de straconx_credit_notes
                # se realiza la busqueda de las notas de credito asociadas a la factura que se desea pagar
                if not pos:
                    if ttype == 'payment':
                        dom=[('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False),('account_id','=',account_aa_id),('partner_id','=',partner_id)]
                    else:
                        dom=[('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False),('account_id','=',account_aa_id),('partner_id','=',partner_id)]
                    if self.pool.get('account.invoice').browse(cr,uid,invoice_id).type == 'in_invoice':
                        dom2=[('state','=','valid'), ('account_id.type', '=', 'receivable'), ('reconcile_id', '=', False),('account_id','=',account_aa_id),('invoice','!=',invoice_id),('credit','=',0),('partner_id','=',partner_id)]
                    else:
                        dom2=[('state','=','valid'), ('account_id.type', '=', 'payable'), ('reconcile_id', '=', False),('account_id','!=',account_aa_id),('invoice','!=',invoice_id),('debit','=',0),('partner_id','=',partner_id)]
                    credit_notes=self.pool.get('account.invoice').search(cr, uid, [('old_invoice_id.id','=',invoice_id)])
                    if credit_notes:
                        credit_notes.append(invoice_id)
                        domain.append(('invoice', 'in', credit_notes))
                    else:
                        domain.append(('invoice','=',invoice_id))
                else:
                    credit_notes_pos.append(invoice_id)
                    domain.append(('invoice', 'in', credit_notes_pos))
                     
                # comento el codigo que debería de ir en el caso de que no este instalado el modulo straconx_credit_notes
                default['value']['invoice_id']=invoice_id
            ids = move_line_pool.search(cr, uid, domain, context=context)
            if dom:
                search_dom = move_line_pool.search(cr,uid,dom,context=context)
                for mov in search_dom:
                    ids.append(mov)
                    mov_li.append(mov) 
            if dom2 and not pos:
                search_dom2 = move_line_pool.search(cr,uid,dom2,context=context)
                for mov in search_dom2:
                    ids.append(mov)
                    mov_li.append(mov)
        else:
            ids = context['move_line_ids']
        company_currency = journal.company_id.currency_id.id
        move_line_found = False

        #order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

        for line in account_move_lines:
            if line.account_id.id == account_aa_id or line.partner_id.id == partner_id:
                if line.credit and line.reconcile_partial_id:
                    if ttype == 'payment' and line.amount_residual_currency <0: 
                        continue
                    elif ttype == 'receipt' and line.amount_residual_currency <0:
                        continue
                if line.debit and line.reconcile_partial_id:
                    if ttype == 'receipt' and line.amount_residual_currency <0:
                        continue
                    elif ttype == 'payment' and line.amount_residual_currency <0:
                        continue
                if invoice_id:
                    if line.invoice.id == invoice_id:
                        #if the invoice linked to the voucher line is equal to the invoice_id in context
                        #then we assign the amount on that line, whatever the other voucher lines
                        move_line_found = line.id
                        break
                elif currency_id == company_currency:
                    #otherwise treatments is the same but with other field names
                    if line.amount_residual == price:
                        #if the amount residual is equal the amount voucher, we assign it to that voucher
                        #line, whatever the other voucher lines
                        move_line_found = line.id
                        break
                    #otherwise we will split the voucher amount on each line (by most old first)
                    total_credit += line.credit or 0.0
                    total_debit += line.debit or 0.0
                elif currency_id == line.currency_id.id:
                    if line.amount_residual_currency == price:
                        move_line_found = line.id
                        break
                    total_credit += line.credit and line.amount_currency or 0.0
                    total_debit += line.debit and line.amount_currency or 0.0

        #voucher line creation
        for line in account_move_lines:
            if line.account_id.id == account_aa_id or line.partner_id.id == partner_id:
                if line.credit and line.reconcile_partial_id:
                    if ttype == 'payment' and line.amount_residual_currency <0: 
                        continue
                    elif ttype == 'receipt' and line.amount_residual_currency <0:
                        continue
                if line.debit and line.reconcile_partial_id:
                    if ttype == 'receipt' and line.amount_residual_currency <0:
                        continue
                    elif ttype == 'payment' and line.amount_residual_currency <0:
                        continue
                if line.currency_id and currency_id==line.currency_id.id:
                    amount_original = abs(line.amount_currency)
                    arc = line.amount_residual_currency
                    if arc <> 0:
                        amount_unreconciled = abs(arc)
                    else:
                        amount_unreconciled = 0
#                     amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual))
                else:
                    arc = line.amount_residual_currency
                    if arc <> 0:
                        amount_unreconciled = abs(arc)
                    else:
                        amount_unreconciled = 0
                    amount_original = currency_pool.compute(cr, uid, company_currency, currency_id, line.credit or line.debit or 0.0)
                    amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, arc)
                line_currency_id = line.currency_id and line.currency_id.id or company_currency
                if line.move_id.name:
                    v_name = line.move_id.name
                rs = {
                    'name':v_name,
                    'type': line.credit and 'dr' or 'cr',
                    'move_line_id_ref':line.id,
                    'move_line_id':line.id,
                    'reference': line.reference,
                    'account_id':line.account_id.id,
                    'amount_original': round(amount_original,2),
                    'amount': (move_line_found == line.id) and min(price, amount_unreconciled) or 0.0,
                    'date_original':line.date,
                    'date_due':line.date_maturity,
                    'amount_unreconciled': amount_unreconciled,
                    'currency_id': line_currency_id,
                }
    
                #split voucher amount by most old first, but only for lines in the same currency
                if not move_line_found:
                    if currency_id == line_currency_id:
                        if line.credit:
                            amount = min(amount_unreconciled, abs(total_debit))
                            rs['amount'] = amount
                            total_debit -= amount
                        else:
                            amount = min(amount_unreconciled, abs(total_credit))
                            rs['amount'] = amount
                            total_credit -= amount     
                if rs['amount_unreconciled'] == rs['amount']:
                    rs['reconcile'] = True
                if (mov_li or not dom) or not mov_li:
                    if (rs['type'] == 'cr' and line.date_maturity and rs['account_id'] == journal.company_id.property_account_advance_supplier.id):
                        if line.journal_id.type == 'advances':
                            if line.partner_id.id == partner_id or line.varios and line.date_maturity:
                                default['value']['line_cr_ids'].append(rs)
                        elif line.journal_id.type == 'pcash' and line.date_maturity:
                            default['value']['line_cr_ids'].append(rs)
                if ttype == 'receipt' and rs['type'] == 'cr' and line.date_maturity and line.journal_id.type != 'advances' and line.journal_id.type != 'pcash':
                    default['value']['line_cr_ids'].append(rs)
                    default['value']['line_dr_ids'] = []
                if ttype == 'payment' and rs['type'] == 'dr' and line.date_maturity and rs['account_id'] == journal.company_id.property_account_advance_customer.id and line.partner_id.id == partner_id:
                    default['value']['line_dr_ids'].append(rs)
                    default['value']['line_cr_ids']=[]
                else:
                    if ttype == 'payment' and rs['type'] == 'dr' and rs['account_id'] != journal.company_id.property_account_advance_supplier.id:
                        default['value']['line_dr_ids'].append(rs)
                        default['value']['line_cr_ids']=[]
                if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
                    default['value']['pre_line'] = 1
                elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
                    default['value']['pre_line'] = 1
                default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price)
        return default
    
    def on_change_receipt(self, cr, uid, ids, receipt=None, type=None, context=None):
        result = {}
        salesman_id=None
        cash_obj=self.pool.get('account.bank.statement')
        if type=='receipt':
            cash_id = cash_obj.search(cr, uid,[('user_id','=', uid),('state','=','open'),('collect','=',True)])
        elif type=='payment':
            cash_id = cash_obj.search(cr, uid,[('user_id','=', uid),('state','=','open'),('pay','=',True)])
        if not cash_id:
            raise osv.except_osv(_('Error!'), _('You must have an open box to generate a voucher!'))
        else:
            result['bank_statement'] = cash_id[0]
        if type=='receipt':
            if receipt:
                salesman_id= self.pool.get('receipt.salesman').browse(cr, uid, receipt, context).salesman_id.id
                result['salesman_id'] = salesman_id
            else:
#                if cash_obj.browse(cr, uid, cash_id[0], context).printer_id.shop_id.point_of_sale:
                    salesman_id= self.pool.get('salesman.salesman').search(cr, uid, [('user_id','=',uid)])
                    salesman_id= salesman_id and salesman_id[0] or None
                    result['salesman_id'] = salesman_id
                    receipt_ids=self.pool.get('receipt.salesman').search(cr, uid,[('salesman_id','=', salesman_id),('state','=','open'),('type','=','point_sale')], limit=1)
                    if receipt_ids: 
                        result['receipt_id']= receipt_ids[0]
        return {'value':result,'domain':{'salesman_id':[('id','=', salesman_id)]}}
    
    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, pay, context=None):
        '''
        Return a dict to be use to create the first account move line of given voucher.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param move_id: Id of account move where this line will be added.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :param pay: browse of pay entered by the user
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        voucher_brw = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        debit = credit = 0.0
        ref=''
        date= time.strftime('%Y-%m-%d')
        date_m= time.strftime('%Y-%m-%d')
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
        if voucher_brw.type in ('purchase', 'payment'):
            credit = pay.amount
            if(not pay.mode_id.credit_account_id):
                raise osv.except_osv(_("Information need!"),_("Please check,you need a credit account on payment mode"))
            account=pay.mode_id.credit_account_id.id
            name=pay.mode_id.name
        elif voucher_brw.type in ('sale', 'receipt'):
            debit = pay.amount
            if(not pay.mode_id.debit_account_id):
                raise osv.except_osv(_("Information need!"),_("Please check,you need a debit account on payment mode"))
            account=pay.mode_id.debit_account_id.id
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        if pay.mode_id.check or pay.mode_id.credit_card:
            if pay.mode_id.check and not (pay.bank_account_id and pay.name):
                raise osv.except_osv(_('Information need!'), _('Please, need information aditional for this payment mode'))
            elif pay.mode_id.credit_card and not (pay.bank_id and pay.name):
                raise osv.except_osv(_('Information need!'), _('Please, need information aditional for this payment mode'))
            ref = pay.name
            date = pay.deposit_date or pay.payment_date 
            date_m = pay.deposit_date or pay.payment_date
        elif pay.mode_id.credit_notes:
            if pay.credit_note_id.number:
                ref = pay.credit_note_id.number
                date = voucher_brw.date
                date_m = voucher_brw.date        
        else:
            ref = pay.mode_id.name or ''
            date = voucher_brw.date
            date_m = voucher_brw.date
        
        #set the first line of the voucher
        move_line = {
                'name': pay.mode_id.name + ' ' +  voucher_brw.comment or '/',
                'reference': ref + ' ' +  voucher_brw.comment,
                'debit': debit,
                'credit': credit,
                'account_id': account,
                'move_id': move_id,
                'statement_id':voucher_brw.bank_statement.id,
                'journal_id': voucher_brw.journal_id.id,
                'period_id': voucher_brw.period_id.id,
                'partner_id': voucher_brw.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                'amount_currency': company_currency <> current_currency and sign * voucher_brw.amount or 0.0,
                'state': 'valid',
                'date': date,
                'date': date_m,
            }
        return move_line
    
    def account_move_get(self, cr, uid, voucher_id, context=None):
        '''
        This method prepare the creation of the account move related to the given voucher.

        :param voucher_id: Id of voucher for which we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''
        seq_obj = self.pool.get('ir.sequence')
        voucher_brw = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        if voucher_brw.number:
            name = voucher_brw.number
        elif voucher_brw.journal_id.sequence_id:
            name = seq_obj.next_by_id(cr, uid, voucher_brw.journal_id.sequence_id.id, context=context)
        else:
            raise osv.except_osv(_('Error !'),
                        _('Please define a sequence on the journal !'))
        if not voucher_brw.reference:
            ref = name.replace('/','')
        else:
            ref = voucher_brw.reference
        if not voucher_brw.shop_id:
            raise osv.except_osv(_('Error !'),
                        _('Need a shop for continue !'))
        else:
            shop_id = voucher_brw.shop_id.id
        move = {
            'name': name,
            'journal_id': voucher_brw.journal_id.id,
            'narration': voucher_brw.narration,
            'date': voucher_brw.date,
            'ref': ref,
            'shop_id': shop_id,
            'partner_id':voucher_brw.partner_id.id,
            'period_id': voucher_brw.period_id and voucher_brw.period_id.id or False
        }
        return move
        
    #@profile
    def action_move_line_create(self, cr, uid, ids, context=None):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        if context is None:
            context = {}
        else:
            invoice_ids = context.get('invoice_ids',False)
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        debit_note_obj = self.pool.get('account.debit.note')
        debit_note_ids = False
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.move_id:
                continue
            process_date=time.strftime('%Y-%m-%d')
            if voucher.process_date:
                process_date=voucher.process_date
#             if round(voucher.differ_payments,3) > 0:
#                 raise osv.except_osv(_('Error !'), _('the sum of the payments is inconsistent with the amount entered!'))
#             if round(voucher.amount_payment_mode,2) != round(voucher.amount,2):
#                 raise osv.except_osv(_('Error !'), _('the sum of the payments mode is incorrect with the amount, please check!'))
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context), context=context)
            # Get the name of the account_move just created
            if voucher.number:
                name = voucher.number
            elif voucher.reference:
                name = voucher.reference
            else:
                name = move_pool.browse(cr, uid, move_id, context=context).name
            # Create the first line of the voucher for each payments
            line_total=0.0
            new_name = ''
            bank_account={}
            rec_list_ids = []
            rec_list_ids_nc = []
            rec_list_ids_nd = []
            for line in voucher.payments:
                if voucher.type in ('purchase', 'payment'):
                    if line.mode_id.check:
                        if line.partner_id.id == line.company_id.partner_id.id:
                            if not bank_account.has_key(line.bank_account_id.id):
                                bank_account[line.bank_account_id.id]=[int(line.name)]
                            else:
                                bank_account[line.bank_account_id.id].append(int(line.name))##error
                move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher.id, move_id, company_currency, current_currency, line, context), context)
                if line.credit_notes:
                    if line.credit_note_id.move_id.line_id:
                        for line_c in line.credit_note_id.move_id.line_id:
                            if line_c.date_maturity and line_c.invoice.residual>0:  
                                rec_list_ids_nc.append(line_c.id)
                    rec_list_ids_nc.append(move_line_id)                     
                if line.debit_notes:
                    if line.debit_note_id.move_id.line_id:
                        for line_c in line.debit_note_id.move_id.line_id:
                            if voucher.type == 'receipt':
                                if line_c.account_id.reconcile and line_c.account_id.credit > 0 and line.debit_note_id.residual > 0:  
                                    rec_list_ids_nd.append(line_c.id)
                            else:
                                if line_c.account_id.reconcile and line_c.account_id.debit > 0 and line.debit_note_id.residual > 0:  
                                    rec_list_ids_nd.append(line_c.id)
                        self.pool.get('account.payments').write(cr, uid, [line.id], {'debit_note_id':False})                                
                    rec_list_ids_nd.append(move_line_id)
                                         

                move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
                if len(voucher.line_cr_ids)>1: 
                    tp='customer'
#                     name = voucher.name
                    ref = name
                    amount = line.amount 
                    args = {
                        'amount': line.amount,
                        'date': time.strftime('%Y-%m-%d'),
                        'name': name,
                        'account_id':line.mode_id.debit_account_id.id,
                        'partner_id':voucher.partner_id.id,
                        'ref': ref,
                        'amount': amount,
                        'statement_id': voucher.bank_statement.id,
                        'type':tp,
                        'voucher_id':voucher.id,
                        'payment_id':line.id,
                        'move_line_id':move_line_id,
                        'bk_type':'credit'
                    }
                    for lines in voucher.line_cr_ids:
                        if lines.move_line_id.invoice:
                            new_name += str(lines.move_line_id.invoice.invoice_number) + ', '
                    line_id = statement_line_obj.create(cr, uid, args, context=context)
                    statement_line_obj.write(cr, uid,line_id, {'statement_id':voucher.bank_statement.id},context)
                    voucher.write({'reference':new_name})
                else:
                    if voucher.line_cr_ids and voucher.line_cr_ids[0].move_line_id.id:
                        context.update({'move_line_invoice_id':voucher.line_cr_ids[0].move_line_id.id})
                        new_name = voucher.line_cr_ids[0].move_line_id.invoice.invoice_number
                    line_id = statement_obj.add_line_cash_register(cr, uid, voucher.id, line.id, move_line_id, context)
                    statement_line_obj.write(cr, uid, line_id, {'statement_id':voucher.bank_statement.id},context)
                    voucher.write({'number': new_name, 'reference':new_name})
                if line.mode_id.cash or line.mode_id.credit_notes or (line.mode_id.others and not line.mode_id.to_deposit):
                    self.pool.get('account.payments').write(cr, uid, [line.id], {'state':'paid'})
                elif voucher.type in ('purchase', 'payment') and line.cheque_id:
                    if line.cheque_id.state not in ('cancel','annulled'):
                        if line.cheque_id.book_id.state <> 'open':
                            raise osv.except_osv(_('¡Acción Inválida !'), _('El talonario de cheques %s correspondiente al cheque %s no se encuentra en estado abierto')%(line.cheque_id.book_id.id, line.cheque_id.name))                                                
                        self.pool.get('check.receipt').write(cr, uid, line.cheque_id.id, {'state':'paid','beneficiary_id':line.beneficiary, 'amount':line.amount, 'voucher_id': voucher.id,'bank_statement':voucher.bank_statement.id,'process_date':process_date,'anulled_date':False})
                        self.pool.get('account.payments').write(cr, uid, [line.id], {'state':'paid'})
                    else:
                        raise osv.except_osv(_('Invalid action !'), _('Payments have cheques in anulled o cancel state, please change cheque number or cheques state !'))
                else:
                    self.pool.get('account.payments').write(cr, uid, [line.id], {'state':'hold'})

                line_total += move_line_brw.debit - move_line_brw.credit
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(cr, uid, voucher.id, line_total, move_id, company_currency, current_currency, context)

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, context)

            seq_obj = self.pool.get('ir.sequence')            

            if new_name:
                ref_voucher = new_name
            else:
                ref_voucher = name

#             if voucher.type == 'payment':
#                 name_voucher = voucher.journal_id.sequence_id.number_next_p
#                 seq_obj.write(cr,uid,voucher.journal_id.sequence_id.id,{'number_next_p':voucher.journal_id.sequence_id.number_next_p + 1})
#             else:
#                 name_voucher = voucher.journal_id.sequence_id.number_next_c
#                 seq_obj.write(cr,uid,voucher.journal_id.sequence_id.id,{'number_next_c':voucher.journal_id.sequence_id.number_next_c + 1})

            self.write(cr, uid, [voucher.id], {
                 'move_id': move_id,
                 'state': 'posted',
                 'number': ref_voucher,
                 'name': str(process_date[:4])+' - ' + str(voucher.id),
                 'process_date': process_date,
             })
            voucher.refresh()
            self.action_process_receipt(cr, uid, voucher, context)
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            # We automatically reconcile the account move lines.
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:                  
                    move_line_pool.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
            
            if len(rec_list_ids_nc) >= 2:                  
                move_line_pool.reconcile_partial(cr, uid, rec_list_ids_nc, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)

            if len(rec_list_ids_nd) >= 2:                  
                move_line_pool.reconcile_partial(cr, uid, rec_list_ids_nd, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)

        
        if invoice_ids:
            self.pool.get('account.invoice').write(cr,uid,invoice_ids,{},context) 
        if debit_note_ids:
            debit_note_obj.write(cr,uid,debit_note_ids,{},context)            
        return True

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):

        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []
        s=0.00

        voucher_brw = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context)
        ctx = context.copy()
        ctx.update({'date': voucher_brw.date})
        for line in voucher_brw.line_ids:
            s += line.amount
            type = voucher_brw.type
        if (round(s,2) > round(tot_line,2) and type == 'receipt') or (round(s,2) > round(abs(tot_line),2) and type =='payment'):
            raise osv.except_osv(_('!Aviso!'),_("El total a conciliar y el valor del pago son diferentes. Favor revisar!"))
        for line in voucher_brw.line_ids:
            #create one move line per voucher line where amount is not 0.0
            if not line.amount:
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher_brw.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if line.move_line_id and line.move_line_id.state <> 'valid':
                    raise osv.except_osv(_('!Aviso!'),_("La línea contable del asiento %s que desea aprobar se encuentra en estado inválido. Posiblemente, necesita que el asiento contable sea aprobado. Por favor revisar.")%(line.move_line_id))
                else:
                    currency_rate_difference = line.move_line_id.amount_residual - amount
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher_brw.journal_id.id,
                'period_id': voucher_brw.period_id.id,
                'name': line.move_line_id.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'statement_id':voucher_brw.bank_statement.id,
                'partner_id': voucher_brw.partner_id.id,
                'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                #'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'analytic_account_id':False,
                'quantity': 1,
                'credit': 0.0,
                'state': 'valid',
                'debit': 0.0,
                'date': voucher_brw.date,
                'reference': line.move_line_id.ref,
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher_brw.tax_id and voucher_brw.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher_brw.tax_id.id,
                })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv(_('No Account Base Code and Account Tax Code!'),_("You have to configure account base code and account tax code on the '%s' tax!") % (tax_data.name))

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = 0.00
            if line.move_line_id:
                voucher_currency = voucher_brw.currency_id and voucher_brw.currency_id.id or voucher_brw.journal_id.company_id.currency_id.id
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency. 
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    elif line.move_line_id.currency_id.id == voucher_brw.payment_rate_currency_id.id:
                        # if the rate is specified on the voucher, we must use it
                        voucher_rate = currency_obj.browse(cr, uid, voucher_currency, context=ctx).rate
                        amount_currency = (move_line['debit'] - move_line['credit']) * voucher_brw.payment_rate * voucher_rate
                    else:
                        # otherwise we use the rates of the system (giving the voucher date in the context)
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled and line.move_line_id.currency_id.id == voucher_currency:
                    sign = voucher_brw.type in ('payment', 'purchase') and -1 or 1
                    foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency

            move_line['amount_currency'] = amount_currency
            voucher_line = move_line_obj.create(cr, uid, move_line)
            move_line_obj.browse(cr, uid, voucher_line).state
            rec_ids = [voucher_line, line.move_line_id.id]

            if line.move_line_id and line.move_line_id.currency_id.id <> company_currency and foreign_currency_diff > 0.00:
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': -1 * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)

            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)

        return (tot_line, rec_lst_ids)
    
    def action_process_receipt(self,cr, uid, voucher, context={}):
        wf_service = netsvc.LocalService("workflow")
        receipt_obj = self.pool.get('receipt.salesman')
        if voucher.receipt_id:
            receipt_obj.write(cr, uid, [voucher.receipt_id.id],{'emission_date':voucher.received_date,
                                                               'process_date':voucher.process_date,
                                                               'partner_id':voucher.partner_id.id,
                                                               'bank_statement':voucher.bank_statement.id,
                                                               'voucher_id':voucher.id,
                                                           })
            wf_service.trg_validate(uid, 'receipt.salesman', voucher.receipt_id.id, 'button_process', cr)
        return True

    def unlink(self, cr, uid, ids, context=None):
        res_users = 'Recibo de Caja anulado por usuario ' + self.pool.get('res.users').browse(cr,uid,uid).login
        date=time.strftime('%Y-%m-%d %H:%M:%S')
        wf_service = netsvc.LocalService("workflow")
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.state != 'draft':
                raise osv.except_osv(_('Invalid action !'), _('Only Can delete Voucher(s) in state draft !'))
            if voucher.payments:
#                cr.execute("DELETE FROM account_payments WHERE vouch_id=%s", (voucher.id,))
                cr.execute("update account_payments set state ='cancel' WHERE vouch_id=%s", (voucher.id,)) 
            if voucher.receipt_id:
                wf_service.trg_validate(uid, 'receipt.salesman', voucher.receipt_id.id, 'process_annulled', cr)
#        return super(account_voucher, self).unlink(cr, uid, ids, context=context)
        cr.execute("""update account_voucher_line set write_date = %s, write_uid=%s, active=False where voucher_id in %s """,(date, uid, tuple(ids)))
        cr.execute("""update account_voucher set write_date = %s, write_uid=%s, state='cancel', comment=%s where id in %s """,(date, uid,res_users,tuple(ids)))
        return True
    
    def cancel_voucher(self, cr, uid, ids, context=None):
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        invoice_obj = self.pool.get('account.invoice')
        wf_service = netsvc.LocalService("workflow")
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.bank_statement.state=='confirm' and uid <> 1:
                raise osv.except_osv(_('Invalid Action!'),_("Can not Unreconcile because the box is closed already!"))
            for payment in voucher.payments:
                if payment.deposit_id:
                    if payment.deposit_id.state in ('confirmed','deposit'):
                        raise osv.except_osv(_('Invalid Action!'),_(("Can not Unreconcile because the payment No %s mode %s already deposit associated!") %(payment.name,payment.mode_id.name)))
                self.pool.get('account.payments').write(cr, uid, [payment.id], {'state':'cancel'})
                if payment.cheque_id:
                    date_a = time.strftime('%Y-%m-%d')
                    self.pool.get('check.receipt').write(cr, uid, [payment.cheque_id.id], {'state':'annulled', 'voucher_id': False,'bank_statement':False,'anulled_date':time.strftime('%Y-%m-%d')})
                    cr.execute("""update check_receipt set write_date = %s, write_uid=%s, state='annulled', voucher_id = Null, bank_statement = Null, anulled_date = %s where id = %s """,(date_a, uid, date_a, payment.cheque_id.id))
            for line in voucher.move_ids:
                move_lines=[]
                if line.reconcile_id: 
                    move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                    move_line_pool.write(cr, uid, move_lines,{'reconcile_id':False})
                    move_lines.remove(line.id)
                    reconcile_pool.unlink(cr, uid, line.reconcile_id.id)
                if line.reconcile_partial_id:
                    move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                    move_line_pool.write(cr, uid, move_lines,{'reconcile_partial_id':False})
                    move_lines.remove(line.id)
                    reconcile_pool.unlink(cr, uid, line.reconcile_partial_id.id)
                if len(move_lines) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)            
            if voucher.move_id:
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
                move_pool.unlink(cr, uid, [voucher.move_id.id])
            self.write(cr, uid, [voucher.id], {'state':'cancel','move_id':False,})
            if voucher.refund_id:
                invoice_obj.action_open_draft(cr,uid,[voucher.refund_id.id])                
                invoice_obj.unlink(cr,uid,[voucher.refund_id.id])
            self.write(cr, uid, [voucher.id], {'refund_id':False,}) 
            if voucher.pay_vouch_id:
                self.pool.get('payments.voucher').unlink(cr, uid, voucher.pay_vouch_id.id)
            if voucher.receipt_id:
                wf_service.trg_validate(uid, 'receipt.salesman', voucher.receipt_id.id, 'process_annulled', cr)
            cr.execute("""UPDATE account_bank_statement_line set active=False, amount= 0.00 where voucher_id=%s AND statement_id=%s""",(voucher.id,voucher.bank_statement.id))            
#            self.pool.get('account.bank.statement').write(cr, uid, [voucher.bank_statement.id], {})
            for vouch_lines in voucher.line_cr_ids:
                if vouch_lines.move_line_id.invoice:
                    self.pool.get('account.invoice').write(cr,uid,[vouch_lines.move_line_id.invoice.id],{},context)
            for vouch_lines in voucher.line_dr_ids:
                if vouch_lines.move_line_id.invoice:
                    self.pool.get('account.invoice').write(cr,uid,[vouch_lines.move_line_id.invoice.id],{},context)
        return True
    
    def action_cancel_draft(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        receipt_obj = self.pool.get('receipt.salesman')
        for voucher in self.browse(cr, uid, ids, context):
            if voucher.receipt_id:
                receipt_obj.set_to_open(cr, uid, [voucher.receipt_id.id],context)
            for payment in voucher.payments:
#                if payment.deposit_id:
#                    if payment.deposit_id.state in ('confirmed','deposit'):
#                        raise osv.except_osv(_('Invalid Action!'),_(("Can not Unreconcile because the payment No %s mode %s already deposit associated!") %(payment.name,payment.mode_id.name)))
                self.pool.get('account.payments').write(cr, uid, [payment.id], {'state':'draft'})
                if payment.cheque_id:
                    self.pool.get('check.receipt').write(cr,uid,[payment.cheque_id.id],{'state':'open'})
        return super(account_voucher, self).action_cancel_draft(cr, uid, ids, context=context)

    def onchange_amount(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
        if context is None:
            context = {}
        res = self.recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
        ctx = context.copy()
        ctx.update({'date': date})
        vals = self.onchange_rate(cr, uid, ids, rate, amount, currency_id, payment_rate_currency_id, company_id, context=ctx)
        for key in vals.keys():
            res[key].update(vals[key])
        return res

    def resolve_o2m_operations2(self, cr, uid, target_osv, operations, fields, context):
        results = []
        for operation in operations:
            result = None
            if not isinstance(operation, (list, tuple)):
                result = target_osv.read(cr, uid, operation, fields, context=context)
            elif operation[0] == 0:
                # may be necessary to check if all the fields are here and get the default values?
                result = operation[2]
            elif operation[0] == 1:
                result = target_osv.read(cr, uid, operation[1], fields, context=context)
                if not result: result = {}
                result.update(operation[2])
            elif operation[0] == 4:
                result = target_osv.read(cr, uid, operation[1], fields, context=context)
            if result != None:
                results.append(result)
        return results

    def onchange_line_payments(self, cr, uid, ids, line_dr_ids, context=None):
        context = context or {} 
        amount = 0.00
        if not line_dr_ids:
            return {'value':{}}
        line_osv = self.pool.get('account.payments')
        line_dr_ids = self.resolve_o2m_operations2(cr, uid, line_osv, line_dr_ids, ['amount'], context)

        amount_total = 0.00
        for line in line_dr_ids:
            amount = line.get('amount', 0.0)
        amount_total += amount
        return {'value': {'amount_payment_mode':amount_total}}        

    def create_invoice_line(self,cr, uid, values):
        return self.pool.get('account.invoice.line').create(cr, uid, values)

    #@profile
    def writeoff_move_line_get(self, cr, uid, voucher_id, line_total, move_id, name, company_currency, current_currency, context=None):
        '''
        Set a dict to be use to create the writeoff move line.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param line_total: Amount remaining to be allocated on lines.
        :param move_id: Id of account move where this line will be added.
        :param name: Description of account move line.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        currency_obj = self.pool.get('res.currency')
        move_line = {}

        voucher_brw = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        current_currency_obj = voucher_brw.currency_id or voucher_brw.journal_id.company_id.currency_id
        move_line_obj = self.pool.get('account.move.line')
        move_obj = self.pool.get('account.move')
        invoice_obj = self.pool.get('account.invoice')
        if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
            diff = line_total
            account_id = False
            write_off_name = ''
            if voucher_brw.payment_option == 'with_writeoff':
                account_id = voucher_brw.writeoff_acc_id.id
                write_off_name = voucher_brw.comment
            elif voucher_brw.type in ('sale', 'receipt'):
                account_db_id = voucher_brw.company_id.property_account_advance_customer.id
                account_id = voucher_brw.partner_id.property_account_receivable.id
                type_invoice = 'out_refund'
                type_journal = 'sale_refund'
            else:
                account_db_id = voucher_brw.company_id.property_account_advance_supplier.id
                account_id = voucher_brw.partner_id.property_account_payable.id
                type_invoice = 'in_refund'
                type_journal = 'purchase_refund'                
            move_line = {
                'name': write_off_name or name,
                'account_id': account_id,
                'move_id': move_id,
                'partner_id': voucher_brw.partner_id.id,
                'date': voucher_brw.date,
                'ref':'Valores a favor',
                'reference':'Valores a favor',
                'credit': diff > 0 and diff or 0.0,
                'debit': diff < 0 and -diff or 0.0,
                'amount_currency': company_currency <> current_currency and voucher_brw.writeoff_amount or False,
                'currency_id': company_currency <> current_currency and current_currency or False,
#                'analytic_account_id': voucher_brw.analytic_id and voucher_brw.analytic_id.id or False,
                'analytic_account_id': False
            }

            move_line_obj.create(cr,uid,move_line)        
        return True
    
    def print_cheque(self, cr, uid, ids, context=None):        
        if context is None:
            context={}
        value = {}
        for pay in self.browse(cr, uid, ids, context=context): 
            if pay.payments:
                for cheque in pay.payments:
                    if cheque.check and cheque.cheque_id:
                        name_banco = cheque.cheque_id.book_id.bank.name                        
                        report_name ='cheque_proveedor_pdf_'+name_banco.lower()
                        if report_name:
                            report_ids = self.pool.get('ir.actions.report.xml').search(cr,uid,[('report_name','=',report_name)])
                            if report_ids:
                                data = {}
                                data['model'] = 'account.payments'
                                data['ids'] = [cheque.id]
                                context['active_id']=cheque.id
                                context['active_ids']=[cheque.id]
                                return {
                                   'type': 'ir.actions.report.xml',
                                   'report_name': report_name,
                                   'datas' : data,
                                   'context': context,
                                   'nodestroy': True,
                                   }
                            return True 
                        else:
                            raise osv.except_osv(_('Error!'), _('No está definido el reporte de cheques para el Banco seleccionado'))
                    else:
                        raise osv.except_osv(_('¡Advertencia!'), _('El Documento seleccionado no ha sido cancelado con Cheques'))
        return True

    def print_cheque_laser(self, cr, uid, ids, context=None):        
        if context is None:
            context={}
        value = {}
        for pay in self.browse(cr, uid, ids, context=context): 
            if pay.payments:
                for cheque in pay.payments:
                    if cheque.check and cheque.cheque_id:
                        name_banco = cheque.cheque_id.book_id.bank.name                        
                        report_name ='cheque_proveedor_laser_'+name_banco.lower()
                        if report_name:
                            report_ids = self.pool.get('ir.actions.report.xml').search(cr,uid,[('report_name','=',report_name)])
                            if report_ids:
                                data = {}
                                data['model'] = 'account.payments'
                                data['ids'] = [cheque.id]
                                context['active_id']=cheque.id
                                context['active_ids']=[cheque.id]
                                return {
                                   'type': 'ir.actions.report.xml',
                                   'report_name': report_name,
                                   'datas' : data,
                                   'context': context,
                                   'nodestroy': True,
                                   }
                            return True 
                        else:
                            raise osv.except_osv(_('¡Error!'), _('No está definido el reporte de cheques para el Banco seleccionado'))
                    else:
                        raise osv.except_osv(_('¡Advertencia!'), _('El Documento seleccionado no ha sido cancelado con Cheques'))
        return True

account_voucher()

class account_voucher_line(osv.osv):
    _inherit="account.voucher.line"

    _columns = {
        'move_line_id_ref': fields.many2one('account.move.line', 'Journal Item', readonly=True),
        'move_ref': fields.char('Reference',size=30),
        'active': fields.boolean('Active'),
    }

    _defaults ={
        'active': True,
                }

    def write(self, cr, uid, ids, values, context=None):
        try:
            move_line = values['move_line_id']
            values['move_line_id_ref'] = move_line
            return super(account_voucher_line, self).write(cr, uid, ids, values, context)
        except:
            return super(account_voucher_line, self).write(cr, uid, ids, values, context)
        
    def create(self, cr, uid, values, context=None):
        try:
            move_line = values['move_line_id']
            values['move_line_id_ref'] = move_line
            return super(account_voucher_line, self).create(cr, uid, values, context)
        except:
            return super(account_voucher_line, self).create(cr, uid, values, context)

    def onchange_move_line_id(self, cr, user, ids, move_line_id, context=None):
        """
        Returns a dict that contains new values and context

        @param move_line_id: latest value from user input for field move_line_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        res = {}
        move_line_pool = self.pool.get('account.move.line')
        if move_line_id:
            move_line = move_line_pool.browse(cr, user, move_line_id, context=context)
            if move_line.credit:
                ttype = 'dr'
                amount_credit = move_line.credit
            res.update({
                'account_id': move_line.account_id.id,
                'type': ttype,
                'currency_id': move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id,
                'date_original': move_line.date,
                'date_due': move_line.date_maturity,
                'amount_original':amount_credit,
                'amount_unreconciled':move_line.amount_residual_currency
            })
        return {
            'value':res,
        }

    def onchange_move_line_id_cr(self, cr, user, ids, move_line_id, context=None):
        """
        Returns a dict that contains new values and context

        @param move_line_id: latest value from user input for field move_line_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        res = {}
        move_line_pool = self.pool.get('account.move.line')
        if move_line_id:
            move_line = move_line_pool.browse(cr, user, move_line_id, context=context)
            if move_line.debit:
                ttype = 'cr'
                amount_debit = move_line.debit
            else:
                raise osv.except_osv(_('Error!'), _('Este documento es una Nota de Crédito, no una Factura o Nota de Débito'))                
            res.update({
                'account_id': move_line.account_id.id,
                'type': ttype,
                'currency_id': move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id,
                'date_original': move_line.date,
                'date_due': move_line.date_maturity,
                'amount_original':amount_debit,
                'amount_unreconciled':move_line.amount_residual_currency
            })
        return {
            'value':res,
        }

    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        if amount>0:
            vals['reconcile'] = (amount == amount_unreconciled)
        return {'value': vals}
    
    def unlink(self, cr, uid, ids, context=None):
        res_users = 'Recibo de Caja anulado por usuario ' + self.pool.get('res.users').browse(cr,uid,uid).login
        date=time.strftime('%Y-%m-%d %H:%M:%S')
        for line in self.browse(cr, uid, ids, context=context):
            cr.execute("""update account_voucher_line set write_date = %s, write_uid=%s, active=False where id = %s """,(date, uid, line.id))
        return True
       
account_voucher_line()


# class ir_sequence(osv.osv):
#     _inherit="ir.sequence"
#     _columns={
#               'number_next_c': fields.integer('Número Siguiente Clientes', required=True, help="Next number of this sequence"),
#               'number_next_p': fields.integer('Número Siguiente Proveedores', required=True, help="Next number of this sequence")
#                   }    
# ir_sequence()