# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
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

class account_invoice(osv.osv):
    

    _inherit = 'account.invoice'
        
    #@profile
    def action_number(self, cr, uid, ids, context=None):
        authorization_obj=self.pool.get('sri.authorization')
        for invoice in self.browse(cr, uid, ids, context):
            if not invoice.partner_id.vat:
                raise osv.except_osv(_('Error!'), _("Partner %s doesn't have CEDULA/RUC, you must input for validate.") % invoice.partner_id.name)
            if (invoice.type in ('out_invoice','out_refund') or (invoice.type == 'in_invoice' and invoice.journal_id.type == 'purchase_liquidation') or self.validate(invoice.type, invoice.journal_id.type)):                
                type_journal = invoice.journal_id.type
                if not (invoice.automatic or invoice.pre_printer):
                    if not invoice.invoice_number_out:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                    auth = authorization_obj.get_auth(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, invoice.invoice_number_out, invoice.company_id.id, invoice.date_invoice2, uid, context)
                    if not auth['auth']:
                        raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization for this number of sequence, please check'))
                    line_id=authorization_obj.get_line_id(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, auth['auth'], context)
                    self.pool.get('sri.authorization.line').add_document(cr, uid, line_id, context)
                    self.write(cr, uid, [invoice.id], {
                                                       'invoice_number': auth['sequence'],
                                                       'invoice_number_out': auth['sequence'],
                                                       'authorization_sales':auth['auth'],
                                                       'flag':True,
                                                       #'authorization':authorization_obj.browse(cr, uid, auth['auth'], context).name,
                                                       }, context)
                else:
                    if not invoice.authorization_sales:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
                    line_id=authorization_obj.get_line_id(cr, uid, type_journal, invoice.shop_id.id, invoice.printer_id.id, invoice.authorization_sales.id, context)
                    if not invoice.invoice_number_out:
                        b = True
                        while b :
                            number_out = authorization_obj.get_number(cr, uid, [invoice.authorization_sales.id], type_journal,invoice.shop_id.id,invoice.printer_id.id, invoice.company_id.id)
                            self.pool.get('sri.authorization.line').add_sequence(cr, uid,line_id,{})
                            if not self.pool.get('account.invoice').search(cr, uid, [('type','=',invoice.type),('invoice_number','=',number_out), ('shop_id','=',invoice.shop_id.id), ('printer_id','=',invoice.printer_id.id),('id','not in',tuple(ids))],):
                                b=False
                    else:
                        number_out = invoice.invoice_number_out
                    self.pool.get('sri.authorization.line').add_document(cr,uid,line_id,{})
                    self.write(cr, uid, [invoice.id], {
                                                       'invoice_number': number_out,
                                                       'invoice_number_out': number_out,
                                                       'flag':True,
                                                       #'authorization':invoice.authorization_sales.name,
                                                       }, context)
            elif invoice.type in ('in_invoice','in_refund'):
                vals=[]
                if invoice.origin_transaction == 'local':
                    if not invoice.tax_sustent:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist tax sustent for the document, please check'))
                    if invoice.journal_id.type=='other_moves':
                        if not invoice.invoice_number_in:
                            raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                        else:
                            invoice_number_in = invoice.invoice_number_in
                    if invoice.document_type.code not in ('TI','19'):                        
                        if not invoice.invoice_number_in:
                            raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                        if invoice.document_type.code in ('01','02','03','04','05','06','07'):
                            if not invoice.authorization_purchase:
                                raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
                        vals=self.pool.get('sri.authorization').get_id_supplier(cr, uid, invoice.address_invoice_id.id, invoice.invoice_number_in, invoice.journal_id.type, invoice.authorization_purchase.id, False,False, context)
                        if not vals:
                            raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization for this number of sequence, please check'))
                        if self.search(cr, uid, [('partner_id', '=', invoice.partner_id.id), ('type','=',invoice.type), ('invoice_number_in','=',vals[-1]['number']) , ('id','not in',tuple(ids)),('state','in',['open','paid'])]):
                            raise osv.except_osv(_('Error!'), _("There is an invoice with number %s for supplier %s") % (vals[-1]['number'], invoice.partner_id.name))                        
                        self.write(cr, uid, [invoice.id], {'invoice_number': vals[-1]['number'],'invoice_number_in': vals[-1]['number'],'authorization_purchase': vals[-1]['auth']}, context)
                    else:
                        if not invoice.invoice_number_in:
                            invoice_number_in = self.pool.get('ir.sequence').next_by_code(cr, uid, 'internal.transaction')
                        else:
                            invoice_number_in = invoice.invoice_number_in
                        self.write(cr, uid, [invoice.id], {'invoice_number': invoice_number_in,'invoice_number_in': invoice_number_in}, context)
                else:
                    self.write(cr, uid, [invoice.id], {'invoice_number': invoice.invoice_number_in}, context)
        res= super(account_invoice, self).action_number(cr, uid, ids, context)
        self.write(cr, uid, ids, {'internal_number':None})
        return res
    
#    @profile
    def action_move_create(self, cr, uid, ids, *args):
        #TODO Este método es sobreescrito para cambiar la referencia con la que se crean los asientos contables
        #     Se debe asignar el numero de la factura o de nota de credito  en la referencia del movimiento contable
        """Creates invoice related analytics and financial move lines"""
        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        context = {}
        for inv in self.browse(cr, uid, ids):
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error !'), _('Please define sequence on invoice journal'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice':time.strftime('%Y-%m-%d')})
            company_currency = inv.company_id.currency_id.id
            # create the analytical lines
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id)
            # check if taxes are all computed
            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

            if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0):
                raise osv.except_osv(_('Bad total !'), _('Please verify the price of the invoice !\nThe real total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error !'), _("Cannot create the invoice !\nThe payment term defined gives a computed amount greater than the total invoiced amount."))

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            entry_type = ''
            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
                entry_type = 'journal_pur_voucher'
                if inv.type == 'in_refund':
                    entry_type = 'cont_voucher'
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                entry_type = 'journal_sale_vou'
                if inv.type == 'out_refund':
                    entry_type = 'cont_voucher'

            diff_currency_p = inv.currency_id.id <> company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml)
            acc_id = inv.account_id.id

            name = inv['number'] or '/'
            totlines = False
            if inv.payment_term:
                totlines = self.pool.get('account.payment.term').compute(cr,
                        uid, inv.payment_term.id, total, inv.date_invoice or False)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid,
                                company_currency, inv.currency_id.id, t[1])
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency_p \
                                and  amount_currency or False,
                        'currency_id': diff_currency_p \
                                and inv.currency_id.id or False,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity': inv.date_due or False,
                    'amount_currency': diff_currency_p \
                            and total_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref
            })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')
            part = inv.partner_id.id

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part, date, context={})),iml)

            line = self.group_lines(cr, uid, iml, line, inv)

            journal_id = inv.journal_id.id
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
            if journal.centralisation:
                raise osv.except_osv(_('UserError'),
                        _('Cannot create invoice move on centralised journal'))

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move = {
                'ref': inv.number and inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'type': entry_type,
                'narration':inv.comment
            }
            period_id = inv.period_id and inv.period_id.id or False
            if not period_id:
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',inv.date_invoice or time.strftime('%Y-%m-%d')),('date_stop','>=',inv.date_invoice or time.strftime('%Y-%m-%d')), ('company_id', '=', inv.company_id.id)])
                if period_ids:
                    period_id = period_ids[0]
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
            new_move_name = self.pool.get('account.move').browse(cr, uid, move_id).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {'move_id': move_id,'period_id':period_id, 'move_name':new_move_name})
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            self.pool.get('account.move').post(cr, uid, [move_id], context={'invoice':inv})
        self._log_event(cr, uid, ids)
        return True
    
        
account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

