# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

from osv import fields,osv
from tools.translate import _

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
#from datetime import *
from dateutil import *
import decimal_precision as dp
import base64
import StringIO
from string import upper
from string import join

class hr_discount(osv.osv):
    
    def _amount_to_paid(self, cr, uid, ids, name, args, context=None):
        result = {}
        for discount in self.browse(cr, uid, ids, context=context):
            result[discount.id]={}
            amount_to_paid=0
            if discount.payment_form == 'invoiced':
                if discount.invoice_line_id.price_product:
                    if discount.invoice_line_id.price_product == discount.amount:
                        amount_to_paid += discount.invoice_line_id.price_product
                    else:
                        amount_to_paid += (discount.invoice_line_id.price_product + discount.invoice_line_id.iva_value)
            else:
                if discount.name.generate_lines_employee:
                    for line in discount.lines_ids:
                        amount_to_paid += (line.amount +line.amount2)
                else:
                    amount_to_paid= discount.amount*(1+discount.interest/100)
            quota=0
            if amount_to_paid >0 and discount.number_of_quotas >0:
                quota= amount_to_paid/discount.number_of_quotas
            result[discount.id]={'amount_to_paid':amount_to_paid,
                                 'value_quota':quota,
                                 }
        return result
    
    def _compute_values_discount(self, cr, uid, ids, name, args, context):
        result = {}
        for discount in self.browse(cr, uid, ids, context=context):
            result[discount.id] = {'amount_paid':0.0,
                                   'amount_remain':0.0,
                                   'quotas_paid':0,
                                   'quotas_remain':0,
                                   }
            for lines in discount.lines_ids:
                if lines.state == 'approve':
                    result[discount.id]['amount_paid'] += (lines.amount + lines.amount2) 
                    result[discount.id]['quotas_paid'] += 1
            result[discount.id]['amount_remain'] = discount.amount_to_paid - result[discount.id]['amount_paid']
            result[discount.id]['quotas_remain'] = discount.number_of_quotas - result[discount.id]['quotas_paid']
        return result
    
    def _paid(self, cr, uid, ids, name, args, context=None):
        result = {}
        for discount in self.browse(cr, uid, ids, context=context):
            if round(discount.amount_paid,2) >= round(discount.amount_to_paid,2):
                result[discount.id] = True
            else:
                result[discount.id] = False
        return result
    
    def _check_amount_quotas(self,cr,uid,ids):
        b=True
        for discount in self.browse(cr, uid, ids):
            if discount.state == 'approve':
                if discount.amount <0 or discount.number_of_quotas <0:
                    b=False
            else:
                b=True
        return b
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal=self.pool.get('account.journal').search(cr, uid, [('type','=','discount_employee')])
        return journal and journal[0] or None
    
    _name = 'hr.discount' 
    _columns = { 
                'name':fields.many2one('hr.transaction.type', 'Name', required=False,readonly=True,states={'draft': [('readonly', False)]}),
                'type':fields.selection([('discount','Discount'),('advance','Advance'),('loans','Loans')],'type', readonly=True),
                'generate_lines_employee':fields.related('name', 'generate_lines_employee', type='boolean', string='Generate Lines of all employee', readonly=True),
                'ref':fields.char('Ref',size=256,required=True,readonly=True,states={'draft': [('readonly', False)]}),
                'employee_id':fields.many2one('hr.employee', 'Employee',readonly=True,states={'draft': [('readonly', False)]}),
                'contract_id':fields.many2one('hr.contract', 'Contract',readonly=True,states={'draft': [('readonly', False)]}, domain="[('employee_id', '=', employee_id)]"),
                'period_id': fields.many2one('account.period', 'Force Period',states={'draft': [('readonly', False)]}, readonly=True, domain=[('state','<>','done')], help="Keep empty to use the period of the validation date."),
                'journal_id': fields.many2one('account.journal', 'Expense Journal',states={'draft': [('readonly', False)]}, readonly=True, required=True),
                'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
                'user_id': fields.many2one('res.users', 'User', readonly=True, states={'draft': [('readonly', False)]}, select=True),
                'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}),
                'partner_id': fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]}),
                'collection_form':fields.selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', select=True),
                'date': fields.date('Date register',readonly=True,states={'draft': [('readonly', False)]}),
                'date_from': fields.date('Date From',readonly=True,states={'draft': [('readonly', False)]}),
                'date_to': fields.date('Date to',readonly=True,states={'draft': [('readonly', False)]}),
                'amount': fields.float('Amount', digits_compute=dp.get_precision('Payroll'), readonly=True,states={'draft': [('readonly', False)]}),
                'amount2': fields.float('Amount', digits_compute=dp.get_precision('Payroll'), readonly=True,states={'draft': [('readonly', False)]}),
                'total': fields.float('Total', digits_compute=dp.get_precision('Payroll'), readonly=True,states={'draft': [('readonly', False)]}),
                'interest': fields.float('% Interest', digits_compute=dp.get_precision('Payroll'), readonly=True,states={'draft': [('readonly', False)]}),
                'number_of_quotas': fields.integer('Number of quotas',readonly=True,states={'draft': [('readonly', False)]}),
                'payment_form':fields.selection([('payment','Payment'),('invoiced','Invoiced'),('statement','Partner Statement'),('none','Not Apply'),],'Payment form',readonly=True, states={'draft': [('readonly', False)]}),
                'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True, states={'draft': [('readonly', False)]}),
                "mode_id": fields.many2one("payment.mode","Mode",readonly=True,states={"draft":[("readonly",False)]}),
                'lines_ids':fields.one2many('hr.discount.lines', 'discount_id', 'Pays', required=False),
                'lines_ids2':fields.one2many('hr.discount.lines', 'discount_id', 'Pays', required=False),
                'amount_to_paid': fields.function(_amount_to_paid, type='float', method=True, string='Amount to Paid', store=True, multi="amount_to_paid"),
                'value_quota': fields.function(_amount_to_paid, type='float', method=True, string='Value Quota', store=True, multi="amount_to_paid"),
                'amount_paid': fields.function(_compute_values_discount, type='float', method=True, string='Amount Paid',multi="values_discount"),
                'amount_remain': fields.function(_compute_values_discount, type='float', method=True, string='Amount Remain',multi="values_discount"),
                'quotas_paid': fields.function(_compute_values_discount, type='integer', method=True, string='Paid Quotas',multi="values_discount"),
                'quotas_remain': fields.function(_compute_values_discount, type='integer', method=True, string='Remain Quotas',multi="values_discount"),
                'paid': fields.function(_paid, type='boolean', method=True, string='Paid?',),
                'payment_id':fields.many2one('account.payments', 'Payment', readonly=True),
                'debit_note_id': fields.many2one('account.debit.note','Egreso', readonly=True),
                'debit_move_line':fields.many2one('account.move.line', 'debit Move line', readonly=True),
                #'pay_id':fields.many2one('account.invoice', 'Cash Ticket', readonly=True),
                #'document_id': fields.many2one('hr.discount.document', 'Reference Document Generate'),
                "state": fields.selection([("draft","Draft"),("generate","Generado"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True),                
                'internal': fields.boolean('internal'),
                'is_paid': fields.boolean('is_paid'),
                'comment':fields.text('Comentarios', required=False),
                }
    
    _defaults={
        "state": "draft",
        "number_of_quotas": 1,
        'user_id': lambda obj, cr, uid, context: uid,
        'date_from': time.strftime('%Y-%m-%d'),
        'date': time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.discount', context=c),
        'type': lambda obj, cr, uid, context: context.get('type','discount'),
        "journal_id": _get_journal,
        'payment_form':'payment'
    }
       
    def test_state(self, cr, uid, ids, context=None):
        for discount in self.browse(cr, uid, ids, context):
            if discount.paid:
                discount.write({'state':'paid'})
            else:
                discount.write({'state':'approve'})
        return True
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not len(ids):
            return []
        for discount in self.browse(cr, uid, ids, context):
            name=""
            if discount.name:
                name=name+"%s"%(discount.name.name)
            res.append((discount.id, name))
        return res
    
    def get_employee_ids(self, cr, uid, ids, context=None):
        hce = self.pool.get('hr.contract.expense')
        lines = self.pool.get('hr.discount.lines')
        types = self.pool.get('hr.transaction.type')
        contract = self.pool.get('hr.contract')
        d_name = self.browse(cr,uid,ids[0])   
        if d_name.name:
            htt = d_name.name.id
            company_id = d_name.company_id.id
            period_id = d_name.period_id.id
            collection_form = d_name.collection_form
#            search_id = self.pool.get('hr.discount').search(cr,uid,[('company_id','=',company_id),('period_id','=',period_id),('name','=',htt),('generate_lines_employee','=',True)])
            datas = hce.search(cr,uid,[('name','=',htt),('company_id','=',company_id)])
            if datas:
                contador = 0
                for d in datas:
                    hce_coll = hce.browse(cr,uid,d)
                    contract_ids  = hce.browse(cr,uid,d).contract_id.id or None
                    hce_amount = hce.browse(cr,uid,d).amount or 0.00
                    hce_ref = hce.browse(cr,uid,d).ref or None
                    empl = self.pool.get('hr.contract').search(cr,uid,[('id','=',contract_ids),('company_id','=',company_id)])
                    if empl:
                        for cont_ids in contract.browse(cr, uid, empl):
                                emp = cont_ids.employee_id.id
                        empl_ids = self.pool.get('hr.employee').search(cr,uid,[('id','=',emp),('company_id','=',company_id),('unemployee','=',False)])
                        id_s = ids[0]
                        if empl_ids:
                            empl_id = self.pool.get('hr.contract').browse(cr, uid, empl[0]).employee_id.id
                            if empl_id:
                                old_lines = lines.search(cr,uid,[('employee_id','=',empl_id),('discount_id','=',id_s),('date','=',d_name.date_from),('ref','=',hce_ref)])
                                if not old_lines:
                                    if hce_coll.collection_form == 'middle_end_month' and hce_coll.collection_form <> d_name.collection_form:
                                        lines.create(cr,uid,{'employee_id':empl_id, 
                                                'name':types.browse(cr,uid,htt).name,
                                                'total':hce_amount,
                                                'amount':hce_amount/2,
                                                'amount2':hce_amount/2,
                                                'date':d_name.date_from,
                                                'ref':hce_ref,
                                                'number_quota':1,
                                                'discount_id':d_name.id,
                                                'state':'draft'})
                                    elif hce_coll.collection_form == d_name.collection_form:
                                        lines.create(cr,uid,{'employee_id':empl_id, 
                                                'name':types.browse(cr,uid,htt).name,
                                                'total':hce_amount,
                                                'amount':hce_amount,
                                                'amount2':0.0,
                                                'date':d_name.date_from,
                                                'ref':hce_ref,
                                                'number_quota':1,
                                                'discount_id':d_name.id,
                                                'state':'draft'})
                                    
        return True
                 
    def onchange_type_trans_id(self, cr, uid, ids, type_id=False, partner_id=False, context=None):
        res={}
        pt_id = None
        transaction_obj = self.pool.get('hr.transaction.type')
        partner_obj = self.pool.get('res.partner') 
        if context is None:
            context = {}
        if not transaction_obj:
            return {'value':{'partner_id':None}}
        else:
            ttype = transaction_obj.browse(cr,uid,type_id)
            if ttype.collection_form:
                res['collection_form']=ttype.collection_form
            else:
                res['collection_form']=None
            if ttype.is_paid:
                partner_id = ttype.partner_id.id
                if partner_id:
                    pt_id = partner_obj.browse(cr,uid,partner_id)
                res['partner_id']=pt_id and pt_id.id or None
                res['is_paid']=ttype.is_paid                
            else:
                res['partner_id']=None
            if ttype.internal:
                res['internal']=ttype.internal
        return {'value':res}

    def onchange_type_discount(self, cr, uid, ids, name=False, contract_id=False, context=None):
        res = {}
        valor = 0.00
        dias = 0
        total = 0.00
        contract_obj = self.pool.get('hr.contract')
        type_obj = self.pool.get('hr.transaction.type')
        type = type_obj.browse(cr, uid, name)
        if contract_id:
            contract = self.pool.get('hr.contract').browse(cr, uid, contract_id)
            if type.code == 'SOLIDARIDAD':                
                dis = self.pool.get('hr.discount').search(cr, uid, [('employee_id','=',contract.employee_id.id),('name','=',name)]) 
                if len(dis) > 0:
                    raise osv.except_osv(_('Error!'), _('El descuento %s ya fue aplicado al empleado %s') % (type.name,contract.employee_id.name))
                sueldo = contract_obj.browse(cr, uid, contract_id, context=context).wage
                valor = sueldo*0.0333
                if sueldo >= 1000 and sueldo < 2000:
                    dias = 1
                elif sueldo >= 2000 and sueldo < 3000:
                    dias = 2
                elif sueldo >= 3000 and sueldo < 4000:
                    dias = 3
                elif sueldo >= 4000 and sueldo < 5000:
                    dias = 4
                elif sueldo >= 5000 and sueldo < 7500:
                    dias = 5
                elif sueldo >= 7500 and sueldo < 12000:
                    dias = 6
                elif sueldo >= 12000 and sueldo < 20000:
                    dias = 7
                elif sueldo >= 20000:
                    dias = 8
                total = valor * float(dias)
                res['ref']= 'Sueldo ' + str(sueldo)
                res['amount']=total
                res['number_of_quotas']=dias
        return {'value':res}
    
    
    def onchange_employee_id(self, cr, uid, ids, employee_id=False, date_from=False, company_id=False, context=None):
        res={}
        employee_obj = self.pool.get('hr.employee')
        discount_obj = self.pool.get('hr.discount') 
        if context is None:
            context = {}
        if not company_id: 
            return {'value':{'contract_id':False,'employee_id':False, 'journal_id':False,'period_id':False}}
        if employee_id:
            if company_id == employee_obj.browse(cr, uid, employee_id, context=context).company_id.id:
                employee = employee_obj.browse(cr, uid, employee_id, context=context)
                contract_id = self.pool.get('hr.payslip').get_contract(cr, uid, employee, date_from, date_from, context=context)
                journal_ids= self.pool.get('account.journal').search(cr,uid,[('company_id','=',company_id),('type','=','discount_employee')])
                if not journal_ids:
                    raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
                else:
                    journal_id= journal_ids[0]
                period_ids=self.pool.get('account.period').search(cr,uid,[('company_id','=',company_id),('date_start','<=',date_from),('date_stop','>=',date_from)])
                if not period_ids:
                    raise osv.except_osv(_('Invalid action!'), _('You must defined an account period for this company'))
                else:
                    period_id= period_ids[0]
                res['contract_id']=contract_id and contract_id[0] or False
                res['journal_id']=journal_id
                res['period_id']=period_id  
            else:
                return {'value':{'contract_id':False,'employee_id':False,'journal_id':False,'period_id':False},'warning' : {'title' : _('Invalid action!'), 'message' : _('Employee have not contract with this company')}}
        else:
            return {'value':{'contract_id':False,'employee_id':False,'journal_id':False,'period_id':False}}        
        return {'value':res}
    
    def onchange_date(self, cr, uid, ids, date=False, company_id=None, context=None):
        res={}
        if context is None:
            context = {}
        if not (date and company_id):
            return {'value':{'period_id':False,'journal_id':False}}
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date), ('company_id', '=', company_id)])
        journal_ids= self.pool.get('account.journal').search(cr,uid,[('company_id','=',company_id),('type','=','discount_employee')])
        if not journal_ids:
            raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
        else:
            journal_id= journal_ids[0]
        res['period_id']=period_ids and period_ids[0] or None
        res['journal_id']=journal_id
        return {'value':res}
    
    def create_lines_discount(self, cr, uid, discount, context=None):
        diff = 0.00
        value_quota = 0.00
        if discount.number_of_quotas > 0:
            b = discount.quotas_paid
            day_from=datetime.strptime(discount.date_from,'%Y-%m-%d')
            flag=True
            if day_from.day >15:
                flag=False
            while b < discount.number_of_quotas:            
                b += 1
                if discount.collection_form == 'middle_month':
                    if not flag:
                        day_from = day_from + relativedelta.relativedelta(months=int(1), day=15)
                    else:
                        day_from = day_from + relativedelta.relativedelta(day=15)
                        flag=False
                    discount_date = day_from.strftime('%Y-%m-%d')
                elif discount.collection_form == 'end_month':
                    day_from = day_from + relativedelta.relativedelta(months=int(1), day=1, days=-1)
                    discount_date = day_from.strftime('%Y-%m-%d')
                    day_from= day_from + relativedelta.relativedelta(months=1)
                else:
                    if not flag:
                        flag=True
                        day_from = day_from + relativedelta.relativedelta(months=int(1), day=1, days=-1)
                        discount_date = day_from.strftime('%Y-%m-%d')
                        day_from= day_from + relativedelta.relativedelta(months=1)
                    else:
                        flag=False
                        day_from = day_from + relativedelta.relativedelta(day=15)
                        discount_date = day_from.strftime('%Y-%m-%d')
                if b == discount.number_of_quotas and round((discount.value_quota * discount.number_of_quotas),2) != round(discount.amount,2):
                    diff = round(discount.amount,2) - round((discount.value_quota * discount.number_of_quotas),2)
                    value_quota = discount.value_quota + diff
                else:
                    value_quota = discount.value_quota
                self.pool.get('hr.discount.lines').create(cr, uid, {
                                                'state':'draft',
                                                'name': _('%s - %s (%s quota)') % (discount.name.name, discount.ref, b),
#                                                'name':discount.name.name +' - '+discount.ref+' ()',
                                                'date':discount_date,                                                       
                                                'amount':value_quota,
                                                'discount_id':discount.id,
                                                'employee_id': discount.employee_id.id,
                                                'number_quota':b,
                                                })
        return True
    
    def create_move_line(self, cr, uid, discount, partner, account, debit, credit, move_id, period_id, reference, context):
        date = self.pool.get('account.move').browse(cr, uid, move_id).date
        return self.pool.get('account.move.line').create(cr, uid, {
                'name': discount.name.name or '/',
                'debit': debit,
                'credit': credit,
                'reference': reference,
                'account_id': account,
                'move_id': move_id,
                'journal_id': discount.journal_id.id,
                'period_id': period_id,
                'partner_id': partner,
                'date': date,
                'company_id': discount.company_id.id
                }, context)

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({'lines_ids' : []})
        default.update({'lines_ids2' : []})
        return super(hr_discount, self).copy(cr, uid, id, default, context)        
    
    def button_create_discount(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        move_line_reconcile=[]
        warning={}
        amount = 0.00
        debit_note_pool=self.pool.get('account.debit.note')
        debit_note_line_pool=self.pool.get('account.debit.note.line')
        partner_move = None
        for discount in self.browse(cr, uid, ids, context):
            move_line_rec=[]
            debit_note=[]
            move_id=None
            credit_account=None
            if discount.name.code == 'SOLIDARIDAD' and discount.collection_form == 'middle_end_month':
                raise osv.except_osv(_('Acción Inválida!'), _('Este descuento solo se puede pagar en Quincena o Fin de mes.'))
            if not discount.generate_lines_employee:
                if discount.amount==0:
                    return {"warning":{"title":_("Validation Error!"), "message":_("Amount  of employee discount must be greater than 0")}}    
            if not discount.journal_id:
                raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
            if not discount.period_id:
                period=self.pool.get('account.period').search(cr, uid, [('date_start','<=',discount.date_from),('date_stop','>=',discount.date_from),('company_id','=',discount.company_id.id)])
                period_id = period and period[0] or False
            else:
                period_id = discount.period_id.id
            if not discount.generate_lines_employee:
                self.create_lines_discount(cr, uid, discount, context)
            discount.write({'state':'generate','move_id':move_id, 'period_id':period_id})                
        return True


    def button_approve(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        move_line_reconcile=[]
        warning={}
        amount = 0.00
        debit_note_pool=self.pool.get('account.debit.note')
        debit_note_line_pool=self.pool.get('account.debit.note.line')
        partner_move = None
        total_discount=0.00
        for discount in self.browse(cr, uid, ids, context):
            if context.get('account_id'):
                account_id = context.get('account_id')
                state = 'paid'
            else:
                account_id = discount.name.debit_account_id.id
                state ='approve'
            move_line_rec=[]
            debit_note=[]
            check_amount = 0.00
            move_id=False
            credit_account=None
            if discount.amount>0.00:
                total_discount= discount.amount
            else:
                total_discount= discount.amount_to_paid           
            if discount.lines_ids:
                for line in discount.lines_ids:
                    check_amount += line.amount
                if round(total_discount,2) <> round(check_amount,2):
                    raise osv.except_osv(_('Error'), _(('La suma de las cuotas a pagar ($ %s) son menores que el monto original del descuento ($ %s). Por favor, revisar.')% (check_amount, discount.amount)))            
            if not discount.employee_id.name:
                if not discount.name:
                    raise osv.except_osv(_('Error'), _(('El empleado %s no tiene una Empresa creada')% (discount.employee_id.name)))
            if discount.payment_form == 'payment':
                if not discount.mode_id:
                    raise osv.except_osv(_('Invalid action!'), _('Usted debe seleccionar un modo de pago'))
                credit_account=discount.name.credit_account_id.id
                if discount.debit_move_line: move_line_rec.append(discount.debit_move_line.id)
                if discount.amount_to_paid >0:
                    amount_d = discount.amount_to_paid
                else:
                    amount_d = discount.amount
                if discount.mode_id and discount.employee_id:
                    debit_note_id = debit_note_pool.create(cr, uid, {
                                                         'partner_id':discount.employee_id.partner_id.id,
                                                         'beneficiary':discount.employee_id.partner_id.id,
                                                         'account_id':discount.name.debit_account_id.id,
                                                         'user_id':uid,
                                                         'journal_id':discount.journal_id.id,
                                                         'date':time.strftime('%Y-%m-%d'),
                                                         'name': 'Anticipo a Colaboradores '+discount.ref,
                                                         'reference': discount.ref,
                                                         'type':'advance_supplier',
                                                         
                                                        })
                    debit_note_line_pool.create(cr, 1,{
                                                         'account_id':discount.name.credit_account_id.id,
                                                         'name':'Anticipo a Colaboradores '+discount.ref+ ''+discount.employee_id.partner_id.name,
                                                         'amount':discount.amount,
                                                         'debit_note_id':debit_note_id,
                                                         })
                    debit_note.append(debit_note_id)
                    self.write(cr, uid, [discount.id], {'debit_note_id':debit_note_id})
                        
            elif discount.payment_form == 'invoiced':
                if not discount.invoice_line_id:
                    raise osv.except_osv(_('Invalid action!'), _('you must selected a line invoiced by discount'))
                if discount.lines_ids: 
                    amount = 0.00
                    for l in discount.lines_ids:
                        amount += l.amount                
                    if round(amount,2) != round((discount.invoice_line_id.price_subtotal+discount.invoice_line_id.iva_value),2):
                        raise osv.except_osv(_('Invalid action!'), _('The values amount of discount must be equals to subtotal invoice line selected'))
                elif round(discount.amount_to_paid,2) != round((discount.invoice_line_id.price_subtotal+discount.invoice_line_id.iva_value),2) and round(discount.amount,2) != round((discount.invoice_line_id.price_subtotal),2):
                    raise osv.except_osv(_('Invalid action!'), _('The values amount of discount must be equals to subtotal invoice line selected'))
                credit_account=discount.invoice_line_id.account_id.id
                if discount.employee_id:
                    move_line=move_line_pool.search(cr, uid, [('account_id','=',credit_account),('partner_id','=',discount.employee_id.partner_id.id), ('move_id','=',discount.invoice_line_id.invoice_id.move_id.id)])
                    if move_line: move_line_rec.append(move_line[0])
                    discount.invoice_line_id.write({'discount_employee':True})            
            elif discount.payment_form == 'statement':
                if not discount.name.credit_account_id:
                    raise osv.except_osv(_('Invalid action!'), _('You must selected a credit account in the type discount'))                
            else:
                if not discount.name.credit_account_id:
                    raise osv.except_osv(_('Invalid action!'), _('You must selected a credit account in the type discount'))
                credit_account=discount.name.credit_account_id.id

            if not discount.generate_lines_employee:
                if discount.amount==0:
                    return {"warning":{"title":_("Validation Error!"), "message":_("Amount  of employee discount must be greater than 0")}}    
            if not discount.journal_id:
                raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
            if not discount.period_id:
                period=self.pool.get('account.period').search(cr, uid, [('date_start','<=',discount.date_from),('date_stop','>=',discount.date_from),('company_id','=',discount.company_id.id)])
                period_id = period and period[0] or False
            else:
                period_id = discount.period_id.id
            if not discount.generate_lines_employee:
                if not discount.employee_id.partner_id:
                    raise osv.except_osv(_('Error'), _(('the employee %s does not have a partner created')% (discount.employee_id.name)))
            if discount.payment_form == 'payment':
                if not discount.mode_id:
                    raise osv.except_osv(_('Invalid action!'), _('you must selected a mode of payment by discount'))
                credit_account=discount.name.credit_account_id.id
                if discount.debit_move_line: move_line_rec.append(discount.debit_move_line.id)
                if discount.amount_to_paid >0:
                    amount_d = discount.amount_to_paid
                else:
                    amount_d = discount.amount            
            name=self.pool.get('ir.sequence').next_by_id(cr, uid, discount.journal_id.sequence_id.id)
            if context.get('ref'):
                ref = context.get('ref')
            else:
                ref=discount.name.name +' -'+ discount.ref
#            context['search_shop']=Truemove_line_rec=[]
            
            if discount.partner_id:
                partner_move = discount.partner_id
                shop_id = self.pool.get('sale.shop').search(cr,uid,[('headquarter','=',True)])                
                if not shop_id:
                    raise osv.except_osv(_('Invalid action!'), _('You must selected a shop type headquarter for continue'))
                else:
                    shop_id=shop_id[0]
            elif discount.employee_id:
                partner_move = discount.employee_id.partner_id
                shop_id = discount.employee_id.shop_id.id
            else:
                partner_move = discount.company_id.partner_id
                shop_id = self.pool.get('sale.shop').search(cr,uid,[('headquarter','=',True)])[0]
            if discount.name.code!='SOLIDARIDAD':
                move_id = move_pool.create(cr, uid, {'name': name,
                        'journal_id': discount.journal_id.id,
                        'date': discount.date_from,
                        'partner_id':partner_move.id,
                        'ref': ref,
                        'period_id': period_id,
                        'company_id': discount.company_id.id,
                        'shop_id': shop_id
                        })
                if not discount.generate_lines_employee:
                    line_m_id = self.create_move_line(cr, uid, discount, partner_move.id, account_id,  discount.amount_to_paid, 0, move_id, period_id, ref, context)
                    move_line_id= self.create_move_line(cr, uid, discount, partner_move.id, credit_account, 0, discount.amount_to_paid, move_id, period_id, ref, context)
                    for line in discount.lines_ids:
                        self.pool.get('hr.discount.lines').write(cr,uid,line.id,{'move_line_id':line_m_id})
                else:
                    for line in discount.lines_ids:
                        if line.amount == 0.00:
                            self.pool.get('hr.discount.lines').unlink(cr, uid, [line.id])
                        else:
                            partner = line.employee_id.partner_id.id
                            line_m_id = self.create_move_line(cr, uid, discount, partner, discount.name.debit_account_id.id, line.amount+line.amount2, 0, move_id, period_id, ref, context)
                            self.pool.get('hr.discount.lines').write(cr,uid,line.id,{'move_line_id':line_m_id})
                    move_line_id = self.create_move_line(cr, uid, discount, partner_move.id, credit_account, 0, discount.amount_to_paid, move_id, period_id, ref, context)                
            if move_id:
                move_pool.post(cr, uid, [move_id], context)
            if move_line_rec:
                move_line_rec.append(move_line_id)
                move_line_reconcile.append(move_line_rec)
            discount.write({'state':state,'move_id':move_id, 'period_id':period_id})
        for reconcile in move_line_reconcile:
            if len(reconcile) >=2:
                move_line_pool.reconcile_partial(cr, uid, reconcile, context=context)
        return True
    
    def create_move_discount(self, cr, uid, ids, line_id, context=None):
        move_id = False
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        move_line_reconcile=[]
        move_line_rec=[]
        credit_account=None
        date = datetime.strptime(line_id.date, "%Y-%m-%d")
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date), ('state', '=', 'draft')])
        for discount in self.browse(cr, uid, ids):
            name=self.pool.get('ir.sequence').next_by_id(cr, uid, discount.journal_id.sequence_id.id)
            ref=line_id.name
            move_id = move_pool.create(cr, uid, {'name': name,
                'journal_id': discount.journal_id.id,
                'date': date,
                'partner_id':discount.employee_id.partner_id.id,
                'ref': ref,
                'period_id': period_ids[0],
                'company_id': discount.company_id.id,
                'shop_id': discount.employee_id.shop_id.id
                })
            if discount.payment_form == 'payment':
                credit_account=discount.name.credit_account_id.id
                if discount.debit_move_line: move_line_rec.append(discount.debit_move_line.id)
            elif discount.payment_form == 'invoiced':
                credit_account=discount.invoice_line_id.account_id.id
                if discount.employee_id:
                    move_line=move_line_pool.search(cr, uid, [('account_id','=',credit_account),('partner_id','=',discount.employee_id.partner_id.id), ('move_id','=',discount.invoice_line_id.invoice_id.move_id.id)])
                    if move_line: move_line_rec.append(move_line[0])
                    discount.invoice_line_id.write({'discount_employee':True})  
            elif discount.payment_form != 'statement':
                credit_account=discount.name.credit_account_id.id                
            line_m_id = self.create_move_line(cr, uid, discount, discount.employee_id.partner_id.id, discount.name.debit_account_id.id,  line_id.amount, 0, move_id, period_ids[0], ref, context)
            move_line_id= self.create_move_line(cr, uid, discount, discount.employee_id.partner_id.id, credit_account, 0, line_id.amount, move_id, period_ids[0], ref, context)
            self.pool.get('hr.discount.lines').write(cr,uid,line_id.id,{'move_line_id':line_m_id})
            if move_id:
                move_pool.post(cr, uid, [move_id], context)
            if move_line_rec:
                move_line_rec.append(move_line_id)
                move_line_reconcile.append(move_line_rec)
            discount.write({'move_id':move_id})
        for reconcile in move_line_reconcile:
            if len(reconcile) >=2:
                move_line_pool.reconcile_partial(cr, uid, reconcile, context=context)
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        l_obj = self.pool.get('hr.discount.lines')
        lines = l_obj.search(cr,uid,[('discount_id','in',ids)])        
        for l in self.browse(cr,uid,ids,context):
            if l.state <> 'draft':
                raise osv.except_osv(_('Invalid action !'), _('Only Can delete Discount(s) in state draft !'))            
        for l_id in lines:
            l = l_obj.browse(cr,uid,l_id)            
            if l.state in ('draft'):
                unlink_ids.append(l['id'])                
            else:
                raise osv.except_osv(_('Invalid action !'), _('Only Can delete Discount(s) in state draft !'))
        if unlink_ids:
            l_obj.unlink(cr,uid,unlink_ids)    
        return super(hr_discount,self).unlink(cr, uid, ids, context=context)
        
        
    def button_canceled(self, cr, uid, ids, context=None):
        for discount in self.browse(cr, uid, ids, context):
            for lines in discount.lines_ids:
                if lines.state=='approve' and not lines.payslip_id:
                    raise osv.except_osv(_('Invalid action!'), _('you can not canceled the discount because already generate a payment'))
                elif discount.generate_lines_employee==True:
                    self.pool.get('hr.discount.lines').write(cr,uid,lines.id,{'state':'cancel'})
                else:
                    self.pool.get('hr.discount.lines').unlink(cr,uid,lines.id,{'state':'cancel'})                    
#                cr.execute('delete from hr_discount_lines where id =%s',(lines.id,))
            if discount.invoice_line_id:
                discount.invoice_line_id.write({'discount_employee':False})
            if discount.move_id:
                self.pool.get('account.move').button_cancel(cr, uid, [discount.move_id.id], context={})
                self.pool.get('account.move').unlink(cr, uid, [discount.move_id.id], context={})
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
    def button_set_draft(self, cr, uid, ids, context=None):
        for discount in self.browse(cr, uid, ids, context):
            for lines in discount.lines_ids:
                if lines.state=='approve':
                    raise osv.except_osv(_('Invalid action!'), _('you can not canceled the discount because already generate a payment'))
                else:
                    self.pool.get('hr.discount.lines').write(cr,uid,lines.id,{'state':'draft'})
            if discount.debit_note_id:
                if discount.debit_note_id.state == 'draft':
                    self.pool.get('account.debit.note').unlink(cr,uid,[discount.debit_note_id.id])
                else:
                    raise osv.except_osv(_('Acción Inválida!'), _('El Egreso de este descuento esta aprobado. Debe reversarlo para continuar'))
        self.write(cr, uid, ids, {'state':'draft', 'debit_note_id':False})
        return True

    def approve_to_draft(self, cr, uid, ids, slip, context = None):
	#         if isinstance (ids, (int, long)): 
    #      
        for discount in self.browse(cr, uid, ids, context):
            for lines in discount.lines_ids:
                if lines.state == 'approve' and lines.payslip_id.id == slip:
                    self.pool.get('hr.discount.lines').write(cr, uid, lines.id,{'state':'draft','payslip_id':False})
                if lines.state == 'approve' and lines.payslip_id2.id == slip:
                    self.pool.get('hr.discount.lines').write(cr, uid, lines.id,{'state':'draft','payslip_id2':False})
            if discount.move_id and discount.name.code == 'SOLIDARIDAD':
                self.pool.get('account.move').button_cancel(cr, uid, [discount.move_id.id], context={})
                self.pool.get('account.move').unlink(cr, uid, [discount.move_id.id], context={})
        self.write(cr, uid, ids, {'state':'approve'})
        return True    

    def back_discount(self, cr, uid, ids, context=None):
        t_ids = self.search(cr,uid,[('state','!=','draft')])
        for discount in t_ids:
            self.pool.get('hr.discount').button_canceled(cr,uid,[discount])
            self.pool.get('hr.discount').button_set_draft(cr,uid,[discount])
        return True

    def approve_mass_discount(self, cr, uid, ids, context=None):
        t_ids = self.search(cr,uid,[('state','=','draft')])
        for discount in t_ids:
            self.pool.get('hr.discount').button_approve(cr,uid,[discount])
        return True


hr_discount()

class hr_discount_document(osv.osv):
    
    def _calculate_total(self, cr, uid, ids, name, args, context):
        if not ids: return {}
        result = {}
        for doc in self.browse(cr, uid, ids, context=context):
            result[doc.id] = 0.0
            for line in doc.discount_ids:
                result[doc.id]+= line.amount
        return result
    
    _name = 'hr.discount.document' 
    _columns = {
                'name':fields.char('Name', size=64, required=False, readonly=True, states={"draft":[("readonly",False)]}),
                'data':fields.binary('File', readonly=True),
                'date': fields.date('Date',readonly=True, states={"draft":[("readonly",False)]}),
                #'discount_ids':fields.one2many('hr.discount', 'document_id', 'Discounts', readonly=True, states={"draft":[("readonly",False)]}),
                'reference':fields.char('Reference', size=64, required=False, readonly=True, states={"draft":[("readonly",False)]}),
                'amount': fields.function(_calculate_total, method=True, type='float', string='Amount', digits_compute=dp.get_precision('Payroll'), store=True),
                "state": fields.selection([("draft","Draft"),("done","Done")],"State",readonly=True),
                }
    
    _defaults={
        "state": lambda *a: 'draft',
        }
    
    def draft_discount_generate(self, cr, uid, ids, context=None):
        for doc in self.browse(cr, uid, ids, context):
            for discount in doc.discount_ids:
                self.pool.get('hr.discount').write(cr, uid, [discount.id], {'document_id':None})
        return self.write(cr, uid, ids, {'state': 'draft', 'data':None, 'name':None}, context=context)
    
    def formato_numero(self, valor):
        tup = valor.split('.')
        valor = ''.join(tup)
        if len(tup[1])== 1:
            return valor+"0"
        return valor
    
    def create_file(self, cr, uid, ids, context=None):
        for doc in self.browse(cr, uid, ids, context):
            buf = StringIO.StringIO()
            if not doc.discount_ids:
                raise osv.except_osv(_('Error'), _('You can not generate the file without Discount'))
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            date = datetime.strptime(doc.date, "%Y-%m-%d")
            if doc.amount > 0:
                datenow = doc.date
                datenow = datenow.split('-')
                bank_id = self.pool.get('res.partner.bank').search(cr, uid, [('partner_id', '=', company.partner_id.id), ('default_bank', '=', True)])
                if not bank_id:
                    raise osv.except_osv(_('Error'), _('You must have a account bank by default'))
                bank = self.pool.get('res.partner.bank').browse(cr, uid, bank_id[0], context)
                mount = self.formato_numero(str(round(doc.amount, 2)))
                #cadena= "D"+company.name+'\t\t'+bank.acc_number+mount+datenow[0][-2:]+datenow[1]+datenow[2]+'N1'+'\n'
                #prueba= "D"+company.name+bank.acc_number+'0'*space+mount+datenow[0][-2:]+datenow[1]+datenow[2]+'N1'+'\n'
                prueba = bank.acc_number + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1'
                space = 33 - len(prueba)
                prueba = bank.acc_number + '0' * space + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1' + '\n'
                space = 80 - len("D" + company.name + prueba)
                cadena = "D" + company.name + ' ' * space + prueba
                buf.write(upper(cadena))
                for discount in doc.discount_ids:
                    if discount.employee_id.bank_account_id:
                        cadena = ''
                        employee = discount.employee_id
                        bank = discount.employee_id.bank_account_id
                        mount = self.formato_numero(str(round(discount.amount,2)))
                        #cadena= "C"+employee.name+'\t\t'+bank.acc_number+mount+datenow[0][-2]+datenow[1]+datenow[2]+'N1'+'\n'
                        prueba = bank.acc_number + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1'
                        space = 33 - len(prueba)
                        prueba = bank.acc_number + '0' * space + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1' + '\n'
                        space = 80 - len("C" + employee.name + prueba)
                        cadena = "C" + employee.name + ' ' * space + prueba
                        buf.write(upper(cadena))
        out = base64.encodestring(buf.getvalue())
        buf.close()
        name = "%s_%s_%s.TXT" % ("Anticipo", company.name[:16], date.strftime('%Y-%m-%d'))
        #print "nombre del archivo %s" % name
        return self.write(cr, uid, ids, {'data':out, 'name':name, 'state':'done'}, context=context)
    
hr_discount_document()


class hr_discount_line(osv.osv):
    
    def _number_quota(self,cr,uid,ids):
        b=True
        for line in self.browse(cr, uid, ids):
            if line.discount_id:
                lines_discount=self.search(cr, uid, [('discount_id','=',line.discount_id.id),('employee_id','=',line.employee_id.id),('id','not in',tuple(ids))])
                for line_1 in lines_discount:
                    if line.number_quota == self.browse(cr, uid, line_1).number_quota and line.ref==self.browse(cr, uid, line_1).ref and line.state <> 'draft':
                        raise osv.except_osv(_('Invalid action!'), _(('The number of quotas must be unique by discount %s of employee %s') %(line.discount_id.name.name,line.employee_id.name)))
        return b

    def line_button_set_draft(self, cr, uid, ids, context=None):
        move_line_pool = self.pool.get('account.move.line')
        reconcile_pool = self.pool.get('account.move.reconcile')
        for lines in self.browse(cr, uid, ids, context):
            if lines.state == 'approve':
                if lines.move_line_id:
                    move_lines = []
                    if lines.move_line_id.reconcile_id:
                        move_lines = [move_line.id for move_line in lines.move_line_id.reconcile_id.line_id]
                        move_lines.remove(lines.move_line_id.id)
                        reconcile_pool.unlink(cr, uid, lines.move_line_id.reconcile_id.id)
                    if lines.move_line_id.reconcile_partial_id:
                        move_lines = [move_line.id for move_line in lines.move_line_id.reconcile_partial_id.line_partial_ids]
                        move_lines.remove(lines.move_line_id.id)
                        reconcile_pool.unlink(cr, uid, lines.move_line_id.reconcile_partial_id.id)
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto', context=context)
                self.write(cr, uid, [lines.id], {'state': 'draft', 'payslip_id': None})
                self.pool.get('hr.discount').test_state(cr, uid, [lines.discount_id.id], {})
            else:
                self.pool.get('hr.discount.lines').write(cr, uid, [lines.id], {'state': 'draft'})
        return True

    _name = 'hr.discount.lines'
    _columns = {'name': fields.char('Name', size=128, required=False, readonly=False),
                'ref': fields.char('Reference', size=128, required=False, readonly=False),
                'payslip_id': fields.many2one('hr.payslip', 'Payslip', required=False),
                'payslip_id2': fields.many2one('hr.payslip', 'Nómina', required=False),
                'employee_id': fields.many2one('hr.employee', 'Employee', readonly=False),
                'date': fields.date('Date'),
                'date_paid': fields.related('payslip_id', 'date_to', type='date', relation='hr.payslip', string='Date Paid'),
                'amount': fields.float('Amount', digits_compute=dp.get_precision('Payroll'), readonly=False),
                'amount2': fields.float('Monto', digits_compute=dp.get_precision('Payroll'), readonly=False),
                'total': fields.float('Total', digits_compute=dp.get_precision('Payroll'), readonly=False),
                'discount_id': fields.many2one('hr.discount', 'Discount',  required=False),
                'move_line_id': fields.many2one('account.move.line', 'Accounting Entry Line', readonly=True),
                'number_quota': fields.integer('Number Quota'),
                "state": fields.selection([("draft", "Pendiente"), ("approve", "Approve"), ("cancel", "Cancel")], "State", readonly=True),
                }

    _constraints = [(_number_quota, 'The number of quotas must be unique for each discount', ['number_quota', 'discount_id'])]

    def onchange_amount_cuota(self, cr, uid, ids, total, context=None):
        amount1 = amount2 = 0
        dis = self.browse(cr, uid, ids)[0]
        if dis.discount_id.collection_form == 'middle_end_month':
            amount1 = amount2 = float(total)/2
        else:
            amount1 = total
        self.write(cr, uid, ids, {'amount': amount1, 'amount2': amount2, 'total': total})
        return {'value': {'amount': amount1, 'amount2': amount2, 'total': total}}
hr_discount_line()