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

from tools.translate import _
from osv import fields, osv
import time
import netsvc

class deposit(osv.osv_memory):
    
    _name = 'deposit'
    _columns = {
                'number_deposit':fields.char('Number of Deposit', size=32),
                'date_deposit':fields.date('Date Deposit', help="La fecha que el Emisor depositó los valores a la cuenta de la compañía"),
                'credit_card':fields.boolean('credit_card', required=False),
                'account_commission_id':fields.many2one('account.account', 'Account Commission Credit Card'),
                'amount_commission': fields.float('amount', digits=(16,2), help="El valor de la comisión sin Impuestos"),
                'generate_invoice': fields.boolean('¿Generar Factura?'),
                'generate_withhold': fields.boolean('¿Generar Retención?'),                
                'electronic_invoice': fields.boolean('¿Factura Electrónica?'),
                'electronic_withhold': fields.boolean('¿Retención Electrónica?'),
                'invoice_number_in': fields.char('Número de Factura', size=25, help="Número de factura emitido por el Emisor de T/C."),
                'authorization_in':fields.char('Autorización', size=49),
                'date_invoice': fields.date('Fecha de Factura', help="Fecha de factura"),                
                'withhold_number': fields.char('Número de Retención', size=25, help="Número de factura emitido por el Emisor de T/C."),
                'withhold_authorization':fields.char('Autorización', size=49),
                'date_withhold': fields.date('Fecha de Retención', help="Fecha de retención"),
                'base_tc_paid': fields.float('Base Pagos', digits=(16,2), help="Base del Pago efectuado sin Impuestos y menos la comisión cobrada por la T/C. Usado para el cálculo de las retenciones."),
                'amount_withhold_tax': fields.float('Retención Fuente', digits=(16,2)),
                'amount_withhold_iva_tax': fields.float('Retención IVA', digits=(16,2)), 
                'other_commission': fields.float('Otras Comisiones', digits=(16,2)),                               
               }
    
    def button_deposit(self, cr, uid, ids, context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        wf_service = netsvc.LocalService("workflow")
        line_invoice = {}
        il = []
        for wizard in self.browse(cr,uid,ids):
            obj = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
            user_id = obj.user_id
            partner_id = obj.bank_id.partner_id or obj.company_id.partner_id
            amount = wizard.amount_commission
            addr = self.pool.get('res.partner').address_get(cr, uid, [partner_id.id], ['default'])
            journal_obj = self.pool.get('account.journal')
            inv_line_obj = self.pool.get('account.invoice.line')
            number_invoice = wizard.invoice_number_in 
            company=obj.company_id
            date_today = time.strftime('%Y-%m-%d')
            date_time_today = time.strftime('%Y-%m-%d %H:%M:%S')
            cur_obj = self.pool.get('res.currency')
            inv_id = False
            context.update({'amount_deposit':wizard.base_tc_paid})
            if wizard.credit_card and wizard.generate_invoice:
                if not company.property_tax_withhold_credit_card or not company.property_tax_withhold_vat_credit_card or not company.property_tax_vat_credit_card or not company.property_account_active_credit_card:
                    raise osv.except_osv(_('¡Acción Inválida!'), _('Debe definir las cuentas y los tipos de impuestos para Tarjeta de Crédito desde el menú Compañía!'))
                if not partner_id:
                    raise osv.except_osv(_('Invalid action !'), _('You must define a partner in the bank selected!'))
                if wizard.amount_commission>0.00 and not obj.invoice_id:
                    if wizard.account_commission_id:
                        account_id = wizard.account_commission_id.id
                        tax_id = company.property_tax_vat_credit_card
                        price_iva = 0.00
                        iva_value = 0.00
                    if tax_id:
                        if tax_id.tax_type == 'vat':
                            price_iva = round(amount * (1 + tax_id.amount),2)
                            iva_value = round((amount*tax_id.amount),2) 
                    line_invoice = {
                        'name': 'LIQUIDACIÓN DE COMISIONES DE VOUCHER #' + obj.receipt,
                        'account_id': account_id,
                        'price_unit': amount,
                        'price_iva': price_iva,
                        'iva_value': iva_value,
                        'quantity': 1,
                        'price_product':amount,
                        'price_subtotal':amount,
                        'discount' : 0.0,
                        'offer' :  0.0,
                        'invoice_line_tax_id': [(6, 0, [tax_id.id])],
                        'account_analytic_id': obj.user_id.shop_id.project_id.id,
                        }
                    inv_line_id = inv_line_obj.create(cr, uid, line_invoice, context=context)
                    il.append(inv_line_id)       
                    pay_acc_id = company.partner_id.property_account_payable.id
                    if not pay_acc_id: 
                        raise osv.except_osv(_('¡Acción Inválida!'), _('No existe una cuenta contable para Proveedores por Pagar'))
                    if not partner_id.property_account_position:
                        raise osv.except_osv(_('¡Acción Inválida!'), _('Debe definir una posición fiscal para el Proveedor')) 
                    else:
                        fpos = partner_id.property_account_position               
                    pay_acc_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, pay_acc_id)
                    journal_ids = journal_obj.search(cr, uid, [('type', '=','purchase'),('company_id', '=', company.id)], limit=1)
                    if not journal_ids:
                        raise osv.except_osv(_('Error !'),
                            _('There is no purchase journal defined for this company: "%s" (id:%d)') % (company.name, company.id))
                    source='local'
                    tax_documents=self.pool.get('sri.document.type').search(cr,uid,[('code','=','01')])
                    if not partner_id.tax_sustent:
                        raise osv.except_osv(_('¡Acción Inválida!'), _('Debe definir un sustento Tributario para el Proveedor')) 
                    else:                
                        tax_sustent=partner_id.tax_sustent.id
                    authorization_purchase = False
                    authorization = wizard.authorization_in 
                  
                    inv = {
                        'shop_id': user_id.shop_id.id,
                        'name': 'LIQUIDACIÓN DE COMISIONES DE VOUCHER #' + obj.receipt,
                        'reference': 'LIQUIDACIÓN DE COMISIONES DE VOUCHER #' + obj.receipt,
                        'description': 'LIQUIDACIÓN DE COMISIONES DE VOUCHER #' + obj.receipt,
                        'account_id': pay_acc_id,
                        'type': 'in_invoice',
                        'partner_id': partner_id.id,
                        'currency_id': company.currency_id.id,
                        'address_invoice_id': addr['default'],
                        'address_contact_id': addr['default'],
                        'country_id': company.country_id.id,
                        'journal_id': len(journal_ids) and journal_ids[0],
                        'origin': 'LIQUIDACIÓN DE COMISIONES DE VOUCHER #' + obj.receipt,
                        'invoice_line': [(6, 0, il)],
                        'fiscal_position': fpos.id,
                        'payment_term': partner_id.property_payment_term and partner_id.property_payment_term.id,
                        'company_id': company.id,
                        'tpurchase': 'expense',
                        'origin_transaction': source,
                        'date_invoice': wizard.date_invoice,
                        'document_type':tax_documents and tax_documents[0],
                        'tax_sustent':tax_sustent,
                        'segmento_id':partner_id.segmento_id.id,
                        'electronic': wizard.electronic_invoice,
                        'number' : number_invoice,
                        'invoice_number' : number_invoice,
                        'invoice_number_in' : number_invoice,
                        'authorization': authorization,
                        'authorization_purchase': authorization_purchase,
                        'migrate': True
                    }
                    context['type']='in_invoice'
                    inv_id = self.pool.get('account.invoice').create(cr, uid, inv, context)
                    self.pool.get('account.invoice').button_compute(cr, uid, [inv_id], context=context, set_total=True)
                    wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)
                    context.update({'invoice_tc':inv_id})
                                
            if wizard.credit_card and not obj.withhold_ids and wizard.generate_withhold:
                withhold=None                
                journal=self.pool.get('account.journal').search(cr, uid,[('type','=','withhold'),('company_id','=',company.id)])
                if not journal:
                    raise osv.except_osv('Error!', _("No existen Diarios Contables tipo Retenciones creados"))
                else:
                    journal_id = journal[0]
                
                if wizard.electronic_withhold: 
                    number_withhold = wizard.withhold_number
                    authorization = wizard.withhold_authorization
                    authorization_sale_wht = False
                else:
                    vals=self.pool.get('sri.authorization').get_id_supplier(cr, uid, addr['default'], wizard.withhold_number, 'withhold', None, wizard.date_withhold, None, context)
                    if not vals:
                        raise osv.except_osv(_('¡Acción Inválida!'), _('No existe autorización del SRI para esta factura. Por favor, crear una desde el formulario de Proveedores'))
                    else:
                        number_withhold = vals[-1]['number']
                        authorization_sale_wht = vals[-1]['auth']
                        authorization = self.pool.get('sri.authorization').browse(cr, uid, vals[-1]['auth'], context).name                    
                vals_ret={
                  'transaction_type':'sale',
                  'partner_id':partner_id.id,
                  'address_id':addr['default'],
                  'authorization_sale': authorization_sale_wht,
                  'authorization': authorization,
                  'date': wizard.date_withhold,
                  'electronic': wizard.electronic_withhold,
                  'number': number_withhold,
                  'number_purchase': number_withhold,
                  'number_sale': number_withhold,
                  'invoice_id': inv_id,
                  'shop_id': user_id.shop_id.id,
                  'printer_id': user_id.cash_box_default_id.id,
                  'journal_id':journal_id
                  }
                withhold = self.pool.get('account.withhold').create(cr, uid, vals_ret, context) 
                if wizard.amount_withhold_tax >0:
                    line_vals={'tax_id': company.property_tax_withhold_credit_card.id,
                               'tax_base':wizard.base_tc_paid,
                               'transaction_type':'sale',
                               'percentage': company.property_tax_withhold_credit_card.amount,
                               'retained_value': wizard.amount_withhold_tax,
                               'invoice_id': inv_id, 
                               'withhold_id':withhold,}
                    line_id=self.pool.get('account.withhold.line').create(cr, uid, line_vals, context)
                if wizard.amount_withhold_iva_tax >0:
                    line_vals1={'tax_id': company.property_tax_withhold_vat_credit_card.id,
                               'tax_base':round(obj.amount - wizard.base_tc_paid - wizard.amount_commission,2),
                               'transaction_type':'sale',
                               'invoice_id': inv_id,
                               'percentage':company.property_tax_withhold_vat_credit_card.amount,
                               'retained_value': wizard.amount_withhold_iva_tax,
                               'withhold_id':withhold,} 
                    line_id1=self.pool.get('account.withhold.line').create(cr, uid, line_vals1, context)
                if withhold:
                    withhold=self.pool.get('account.withhold').browse(cr,uid,withhold)                    
#                     wf_service.trg_validate(uid, 'account.withhold', withhold.id, 'button_approve', cr)
                    move_line_obj = self.pool.get('account.move.line')
                    move_pool = self.pool.get('account.move')
                    if context is None:
                        context={}
                    name=self.pool.get('ir.sequence').next_by_id(cr, uid, withhold.journal_id.sequence_id.id)
                    if withhold.number:
                        ref=withhold.number
                    else:
                        ref=name
                    period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',withhold.date),('date_stop','>=',withhold.date),])
                    move = {'name': name,
                            'partner_id': partner_id.id,
                            'journal_id': withhold.journal_id.id,
                            'date': withhold.date,
                            'details': 'RETENCION POR PAGO DE T/C VOUCHER ' + obj.receipt,
                            'ref': ref,
                            'period_id': period_ids[0],
                            'shop_id': obj.user_id.shop_id.id,
                            }                    
                    move_id = move_pool.create(cr, uid, move)
                    move_line_ids=[]
                    suma=wizard.amount_withhold_iva_tax + wizard.amount_withhold_tax
                    rec_list_ids=[]
                    ctx={'credit_card':True}
                    total_ret_value = 0.00
                    if obj.cheks_ids:
                        for paid in obj.cheks_ids:
                            account=company.property_account_active_credit_card.id
                            ret_value = round(suma * paid.amount/obj.amount,2)
                            total_ret_value += ret_value
                            move_line=self.pool.get('account.withhold').create_move_line(cr, uid, None, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, number_withhold, account, ret_value, move_id, withhold.date,ctx)
                            move_line_ids.append(move_line_obj.create(cr, uid, move_line))
                            line_statement_id= self.pool.get('account.bank.statement.line').search(cr, uid, [('payment_id','=',paid.id)])
                            if line_statement_id:
                                line_statement_id=line_statement_id[0]
                                line_statement=self.pool.get('account.bank.statement.line').browse(cr, uid,line_statement_id,context)
                            rec_ids = [move_line_ids[-1], line_statement.move_line_id.id]
                            rec_list_ids.append(rec_ids)
                        amout_wt = 0.00
                        for line in withhold.withhold_line_ids:
                            amout_wt += line.retained_value
                            if withhold.transaction_type == 'sale':
                                ctx={'sale':True}
                                account = line.tax_id.account_paid_id.id
                            move_line=self.pool.get('account.withhold').create_move_line(cr, uid, line, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, number_withhold, account, line.retained_value, move_id, withhold.date,ctx)
                            move_line_id=move_line_obj.create(cr, uid, move_line) if line.retained_value > 0 else None
                            self.pool.get('account.withhold.line').write(cr, uid, [line.id], {'move_line_id':move_line_id, 'state':'approved'})
                            move_line_id and move_line_ids.append(move_line_id)
                        if abs(round(total_ret_value,2) - round(amout_wt,2)) <0.02:
                            cd = cur_obj.browse(cr, uid, line.withhold_id.company_id.currency_id.id).rate
                            difference = round(abs(total_ret_value - amout_wt),2)
                            difference_currency = round(difference * cd,2)
                            acc_dis_id = line.withhold_id.company_id.property_rounding_difference.id
                            if not acc_dis_id:
                                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                            reference = 'AJUSTE POR REDONDEO'
                            if round(total_ret_value,2) > round(amout_wt,2):
                                credit = 0.00 
                                debit = difference
                            else:
                                debit = 0.00
                                credit = difference
                                move_line = {
                                        'reference' : reference, 
                                        'journal_id' : line.withhold_id.journal_id.id,  
                                        'partner_id': line.withhold_id.partner_id.id, 
                                        'name': name, 
                                        'date': date_today, 
                                        'debit': debit, 
                                        'credit': credit, 
                                        'account_id': acc_dis_id,  
                                        'currency_id': line.withhold_id.company_id.currency_id.id, 
                                        'ref':   name, 
                                        'quantity': 1,
                                        'state': 'valid', 
                                        'period_id': line.withhold_id.period_id.id, 
                                        'move_id': move_id,  
                                        'company_id': line.withhold_id.company_id.id,
                                        'shop_id': line.withhold_id.shop_id.id,
                                        'active': True}                 
                                move_round_id = move_line_obj.create(cr,uid,move_line)
                                context.update({'move_round_id':move_round_id})
                        else:
                            raise osv.except_osv(_('!Aviso!'), _('El valor ingresado de retención %s difiere del valor calculado %s. Por favor, revise los datos.')%(total_ret_value, amout_wt))
                        if move_line_ids:
                            move_pool.post(cr, uid, [move_id], context={})
                        for rec_ids in rec_list_ids:
                            if len(rec_ids) >= 2:
                                move_line_obj.reconcile_partial(cr, uid, rec_ids)
#                             self.pool.get('account.invoice').write(cr, uid, [inv_id], {'withhold_id':withhold.id, 'withhold':True})
                        self.pool.get('account.withhold').write(cr, uid, [withhold.id], {'move_id':move_id,'state':'approved'})
                self.pool.get('deposit.register').write(cr,uid, [obj.id], {'invoice_id': inv_id,'withhold_ids':withhold.id, 'amount_commission':wizard.amount_commission, 'other_commission': wizard.other_commission})        
            number_deposit = wizard.number_deposit or obj.receipt
            self.pool.get('deposit.register').write(cr,uid, [obj.id], {'date':wizard.date_deposit, 'process_date': date_today, 'number_deposit':number_deposit})
            self.pool.get('deposit.register').action_deposit(cr, uid, [obj.id], context)
        return {'type': 'ir.actions.act_window_close'}
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        if 'value' not in context.keys():
            for obj in objs:
                if obj.deposit_credit_card:
                    res['credit_card']=obj.deposit_credit_card
                    res['account_commission_id']=self.pool.get('res.users').browse(cr, uid, uid).company_id.property_account_commission_credit_card.id or None
#                     res['amount_commission']=8.14
#                     res['electronic_invoice']= True
#                     res['electronic_withhold']= True
#                     res['invoice_number_in']= '001-003-001474565'
#                     res['authorization_in']= '0506201515114109900494590016027938054'
#                     res['date_invoice']= '2015-06-03'
#                     res['withhold_number']='001-002-001392732'
#                     res['withhold_authorization']= '0506201510252609900494590016017137014'
#                     res['date_withhold']= '2015-06-01'
#                     res['amount_withhold_tax']= 3.05
#                     res['other_commission']= 0.25
#                     res['amount_withhold_iva_tax']= 1.92
#                     res['base_tc_paid']=152.49     
#                     res['date_deposit']='2015-06-03'                
        else:
            res = context['value']
        return res

    def onchange_invoice_number_in(self, cr, uid, ids,number,context=None):
        result = {}
        if number and len(number)<>17:
            raise osv.except_osv(_('!Aviso!'), _('Por favor ingrese los 17 dígitos de la factura con los guiones correspondientes. Son 3 que corresponden a punto de emisión (001), tres para punto de impresión (001) y nueve para la secuencia (123456789).'))            
        else:
            result['invoice_number_in'] = number
        return {'value':result}
        
    def onchange_withhold_number(self, cr, uid, ids,number_withhold,context=None):
        result = {}
        if number_withhold and len(number_withhold)<>17:
            raise osv.except_osv(_('!Aviso!'), _('Por favor ingrese los 17 dígitos de la retención con los guiones correspondientes. Son 3 que corresponden a punto de emisión (001), tres para punto de impresión (001) y nueve para la secuencia (123456789).'))            
        else:
            result['withhold_number'] = number_withhold
        return {'value':result}
    
    def onchange_authorization_in(self,cr,uid,ids,authorization_in,electronic_invoice,context=None):
        result = {}
        if electronic_invoice:
            if authorization_in and len(authorization_in)<>37:
                raise osv.except_osv(_('!Aviso!'), _('Por favor ingrese los 37 dígitos de la autorización electrónica'))
        else:
            if authorization_in and len(authorization_in)<>10:
                raise osv.except_osv(_('!Aviso!'), _('Por favor ingrese los 10 dígitos de la autorización manual o preimpresa'))
        result['authorization_in'] = authorization_in
        return {'value':result}
    
    def onchange_withhold_authorization(self,cr,uid,ids,withhold_authorization,electronic_withhold,context=None):
        result = {}
        if electronic_withhold:
            if withhold_authorization and len(withhold_authorization)<>37:
                raise osv.except_osv(_('!Aviso!'), _('Por favor ingrese los 37 dígitos de la autorización electrónica'))
        else:
            if withhold_authorization and len(withhold_authorization)<>10:
                raise osv.except_osv(_('!Aviso!'), _('Por favor ingrese los 10 dígitos de la autorización manual o preimpresa'))
        result['withhold_authorization'] = withhold_authorization
        return {'value':result}

deposit()
