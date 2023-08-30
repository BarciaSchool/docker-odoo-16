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


class account_debit_note(osv.osv):

    def _total_payment(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for note in self.browse(cr, uid, ids, context=context):
            result[note.id] = 0.0
            for pay in note.payments:
                result[note.id]+= pay.amount or 0.0
        return result

    def _payments(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        total_dr = 0.00
        for note in self.browse(cr, uid, ids, context=context):
            for payment_dr in note.line_ids:
                total_dr += payment_dr.amount or 0.0            
                result[note.id] = { 'total_payment':total_dr,
                                    'amount':total_dr
                                    }
        return result

    def _get_cashbox(self, cr, uid, context=None):
        statement_obj = self.pool.get('account.bank.statement')
        user_id = self.pool.get('res.users').browse(cr, uid, uid)
        type = False
        if context.get('module', False):
            return None
        if context is None:
            context = {}
        if context.get('default_type', 'advance_customer'):
            type = context.get('type', 'advance_customer')
        if type and type in ('debit_customer', 'advance_customer'):
            statement_id = statement_obj.search(cr, uid, [('state', '=', 'open'), ('user_id', '=', uid)])
            if not statement_id and not user_id.is_warehouse_user:
                raise osv.except_osv(_('! Error !'),
                                     _('Necesita abrir una caja registradora para proceder a facturar.'))
            elif statement_id:
                statement_id = statement_obj.browse(cr, uid, statement_id[0])
                if statement_id:
                    statement_id = statement_id.id
            return statement_id
        return None

    _inherit = "account.debit.note"
    _columns = {
        "payments": fields.one2many("account.payments", "debit_note_id", "Payments", readonly=True, states={"draft": [("readonly", False)]}),
        "beneficiary": fields.char("Beneficiary", size=120, readonly=True, states={"draft": [("readonly", False)]}),
        "statement_id": fields.many2one('account.bank.statement', 'Statement', readonly=True, states={'draft': [('readonly', False)]}),
        "total_payment": fields.function(_total_payment, method=True, type="float", string='Total Amount Payments'),
        'amount_payment_mode': fields.function(_total_payment, method=True, type='float', string='Amount Payments Mode'),
        'amount': fields.function(_payments, method=True, type="float", string='Amount', store=False, multi="other_payments"),
    }

    _defaults = {'statement_id': _get_cashbox}

    def create_line_statement(self, cr, uid, note, payment, name, tp, account_id, move_line_id, ref):
        if payment and payment.name:
            payment_name = payment.name
        else:
            payment_name = ""
        args = {
            'amount': payment.amount,
            'date': time.strftime('%Y-%m-%d'),
            'name': name,
            'account_id': account_id,
            'partner_id': note.partner_id.id,
            # 'ref': payment.mode_id.name + ' ' + payment_name,
            'ref': name,
            'statement_id': note.statement_id.id,
            'type': tp,
            'bk_type': 'pos',
            'payment_id': payment.id,
            'move_line_id': move_line_id
        }
        self.pool.get('account.bank.statement.line').create(cr, uid, args, context={})
        return True

    def confirm_debit_note(self, cr, uid, ids, context={}):
        if context is None:
            context = {}
        seq_obj = self.pool.get('ir.sequence')
        total = 0
        name = ''
        ref = ''
        move_line = []
        for note in self.browse(cr, uid, ids):
            if round(note.total_amount, 2) > round(note.total_payment, 2) and note.type in ('advance_supplier', 'advance_customer'):
                raise osv.except_osv(_('Invalid action!'), _('The amount payments is not equals to the values of lines debit note!'))
            if not note.number:
                number = seq_obj.next_by_id(cr, uid, note.journal_id.sequence_id.id)
            else:
                number = note.number
            if note.line_ids:
                reference = note.line_ids[0].name

            if note.type in ("debit_customer", "debit_supplier"):
                if note.type == 'debit_customer':
                    ref = 'N/D INT. CL. '+reference.upper()
                    name = 'N/D INT. CL. '+number
                else:
                    ref = 'N/D INT. PROV. '+reference.upper()
                    name = 'N/D INT. PROV. '+number
                move_id = self.create_move(cr, uid, note, name, note.reference or ref, context)
                total = 0
                for line in note.line_ids:
                    move_line.append(self.create_move_lines(cr, uid, note, move_id, line.name, note.partner_id, line.amount, 0.0, line.account_id,
                                                            line.account_id.company_id.id, context))
                    total += line.amount
                if total > 0:
                    move_line.append(self.create_move_lines(cr, uid, note, move_id, name, note.partner_id, 0.0, total, note.account_id,
                                                            note.account_id.company_id.id, context))
                self.pool.get('account.move').post(cr, uid, [move_id], context={})
                self.write(cr, uid, [note.id], {'move_id': move_id})
            if note.type in ("advance_customer", "advance_supplier"):
                if not note.statement_id:
                    raise osv.except_osv(_('Error!'), _('You must defined the cash register to confirm this document!'))
                if note.type == 'advance_customer':
                    ref = 'ANT. CL. POR  ' + reference.upper()
                    name = 'ANT. CL. ' + number
                    move_id = self.create_move(cr, uid, note, name, note.reference or ref, context)
                    for line in note.line_ids:
                        move_line.append(self.create_move_lines(cr, uid, note, move_id, line.name, note.partner_id, 0.0, line.amount, line.account_id,
                                                                line.account_id.company_id.id, context))
                    for pay in note.payments:
                        move = self.create_move_lines(cr, uid, note, move_id, pay.mode_id.name, note.partner_id, pay.amount, 0.0,
                                                      pay.mode_id.debit_account_id, pay.mode_id.debit_account_id.company_id.id, context)
                        move_line.append(move)
                        self.create_line_statement(cr, uid, note, pay, name, 'customer', pay.mode_id.debit_account_id.id, move, number)
                        #self.pool.get('account.move').post(cr, uid, [move_id], context={})
                        self.write(cr, uid, [note.id], {'move_id': move_id})
                        if pay.mode_id.cash or (pay.mode_id.others and not pay.mode_id.to_deposit):
                            self.pool.get('account.payments').write(cr, uid, [pay.id], {'state': 'paid'})
                        else:
                            self.pool.get('account.payments').write(cr, uid, [pay.id], {'state': 'hold'})
                    self.pool.get('account.move').post(cr, uid, [move_id], context={})
                else:
                    ref = 'ANT. PROV. POR  ' + reference.upper()
                    name = 'ANT. PROV. ' + number
                    move_id = self.create_move(cr, uid, note, name, note.reference or ref, context)
                    for line in note.line_ids:
                        lines = (self.create_move_lines(cr, uid, note, move_id, line.name, note.partner_id, line.amount, 0.0, line.account_id,
                                                        note.company_id.id, context))
                        self.pool.get('account.move.line').write(cr, uid, [lines], {'varios': note.varios, 'reference': line.name})
                        move_line.append(lines)
                    for pay in note.payments:
                        context.update({'is_payment': True})
                        move = self.create_move_lines(cr, uid, note, move_id, pay.mode_id.name, note.partner_id, 0.0, pay.amount,
                                                      pay.mode_id.credit_account_id, note.company_id.id, context)
                        move_line.append(move)
                        #self.pool.get('account.move').post(cr, uid, [move_id], context={})
                        self.write(cr, uid, [note.id], {'move_id': move_id})
                        st_l_id = self.create_line_statement(cr, uid, note, pay, name, 'supplier', pay.mode_id.credit_account_id.id, move, number)
                        self.pool.get('account.payments').write(cr, uid, [pay.id], {'state': 'paid', 'name': pay.cheque_id.name})
                        if pay.mode_id.account_bank_id and pay.mode_id.check:
                            self.pool.get('check.receipt').write(cr, uid, [pay.cheque_id.id], {'state': 'paid', 'beneficiary_id': pay.beneficiary,
                                                                                               'amount': pay.amount,
                                                                                               'bank_statement': note.statement_id.id,
                                                                                               'process_date': note.date, 'anulled_date': False})
                    self.pool.get('account.move').post(cr, uid, [move_id], context={})
            if not move_line:
                self.pool.get('account.move').unlink(cr, uid, [move_id], context={})
            self.write(cr, uid, [note.id], {'number': number, 'state': 'paid', 'name': name, 'reference': ref})
        return True

    def cancel_debit_note(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        for note in self.browse(cr, uid, ids, context=context):
            pay = []
            if note.move_id:
                move_pool.button_cancel(cr, uid, [note.move_id.id], context={})
                move_pool.unlink(cr, uid, [note.move_id.id], context={})
            if note.type in ("advance_customer","advance_supplier"):
                if note.statement_id.state=='confirm':
                    raise osv.except_osv(_('Invalid Action!'),_("Can not Unreconcile because the box is closed already!"))
                for payment in note.payments:
                    if payment.deposit_id:
                        if payment.deposit_id.state in ('confirmed','deposit'):
                            raise osv.except_osv(_('Invalid Action!'),_(("Can not Unreconcile because the payment No %s mode %s already deposit associated!") %(payment.name,payment.mode_id.name)))
                    if payment.cheque_id:
                        self.pool.get('check.receipt').write(cr, uid, [payment.cheque_id.id],{'state':'annulled','bank_statement':False,'anulled_date':time.strftime('%Y-%m-%d')})
                    self.pool.get('account.payments').write(cr, uid, [payment.id], {'state':'cancel'})
                    pay.append(payment.id)
                if pay:
                    cr.execute('SELECT id from account_bank_statement_line where statement_id=%s AND payment_id in %s',(note.statement_id.id,tuple(pay)))
                    res=cr.fetchall()
                    for r in res:
                        cr.execute("UPDATE account_bank_statement_line set active=False, amount=0.00 WHERE id in (%s)", (r))
        self.write(cr, uid, ids, {'state':'cancel'})
        return True

    def action_cancel_draft(self, cr, uid, ids, context=None):
        for note in self.browse(cr, uid, ids, context):
            for payment in note.payments:
                self.pool.get('account.payments').write(cr, uid, [payment.id], {'state':'draft'})
                if payment.cheque_id:
                        self.pool.get('check.receipt').write(cr, uid, [payment.cheque_id.id],{'state':'open'})
        return super(account_debit_note,self).action_cancel_draft(cr, uid, ids, context)


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
        return True

    def print_cheque_laser(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        value = {}
        for pay in self.browse(cr, uid, ids, context=context):
            if pay.payments:
                for cheque in pay.payments:
                    if cheque.check and cheque.cheque_id:
                        name_banco = cheque.cheque_id.book_id.bank.name
                        report_name = 'cheque_proveedor_laser_' + name_banco.lower()
                        if report_name:
                            report_ids = self.pool.get('ir.actions.report.xml').search(cr, uid, [('report_name', '=', report_name)])
                            if report_ids:
                                data = {}
                                data['model'] = 'account.payments'
                                data['ids'] = [cheque.id]
                                context['active_id'] = cheque.id
                                context['active_ids'] = [cheque.id]
                                return {'type': 'ir.actions.report.xml',
                                        'report_name': report_name,
                                        'datas': data,
                                        'context': context,
                                        'nodestroy': True,
                                        }
                            return True
                        else:
                            raise osv.except_osv(_('¡Error!'), _('No está definido el reporte de cheques para el Banco seleccionado'))
                    else:
                        raise osv.except_osv(_('¡Advertencia!'), _('El Documento seleccionado no ha sido cancelado con Cheques'))
        return True

account_debit_note()


class account_debit_note_line(osv.osv):

    _inherit = "account.debit.note.line"

    def onchange_line(self, cr, uid, ids, company=None, type=None, account=None, context=None):
        if context is None:
            context = {}
        values = {}
        if not account:
            if type == 'advance_supplier':
                values['account_id'] = self.pool.get('res.company').browse(cr, uid, company, context).property_account_advance_supplier.id or False
            elif type == 'advance_customer':
                values['account_id'] = self.pool.get('res.company').browse(cr, uid, company, context).property_account_advance_customer.id or False
        return {'value': values}

account_debit_note_line()
