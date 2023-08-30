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


class deposit_statement_wizard(osv.osv_memory):
    _name = "deposit.statement.wizard"

    _columns = {'statement_id': fields.many2one('account.bank.statement', 'Cash Registrer', required=False),
                'line_ids': fields.one2many('deposit.statement.wizard.line', 'wizard_id', 'wizard lines', required=False)}

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        objs = self.pool.get(context['active_model']).browse(cr, uid, context['active_ids'])
        res = {}
        if 'value' not in context.keys():
            for obj in objs:
                res['statement_id'] = obj.id
        return res

    def action_deposit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        objs = self.pool.get(context['active_model']).browse(cr, uid, context['active_ids'])
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        statement_obj = self.pool.get('account.bank.statement')
        vouch_obj = self.pool.get('account.voucher')
        seq_obj = self.pool.get('ir.sequence')
        obj = self.browse(cr, uid, ids)[0]
        for inv in objs:
            moves = []
            rec_list_ids = []
            if not inv.line_ids:
                continue
            if inv.name:
                name = inv.name
            elif inv.journal_id.sequence_id:
                name = seq_obj.next_by_id(cr, uid, inv.journal_id.sequence_id.id)
            else:
                raise osv.except_osv(_('Error !'), _('Please define a sequence on the journal !'))
            ref = name.replace('/', '')
            statement_id = statement_obj.browse(cr, uid, inv.id)
            if statement_id.deposit:
                raise osv.except_osv(_('Error !'), _('Esta caja ya tiene depósitos realizados'))

            payments_obj = self.pool.get('account.payments')

            vouch_ids = vouch_obj.search(cr, uid, [('bank_statement', '=', statement_id.id)])

            move = {
                'name': name,
                'journal_id': inv.journal_id.id,
                'shop_id': inv.printer_id.shop_id.id,
                'date': inv.closing_date,
                'ref': ref,
                'partner_id': inv.company_id.id,
                'period_id': inv.period_id and inv.period_id.id or False
            }
            move_id = move_pool.create(cr, uid, move)
            if not obj.line_ids:
                raise osv.except_osv(_('Error !'), _('Debe definir por lo menos una línea de depósito !'))
            else:
                suma = 0
                mode = None
                for total in obj.line_ids:
                    receipts_ids = self.pool.get('deposit.register').search(cr, uid, [('receipt', '=', total.receipt)])
                    if receipts_ids:
                        raise osv.except_osv(_('Error !'), _('Ya existe una papeleta con el mismo número.'))
                    suma += total.amount
                    if not mode:
                        mode = total.mode_id

                        if mode.check and 'DIA' in mode.name:
                            cheques_ids = payments_obj.search(cr, uid, [('vouch_id', 'in', vouch_ids), ('type', '=', 'receipt'),
                                                                        ('mode_id.check', '=', True), ('mode_id.to_deposit', '=', True)])
                            if cheques_ids:
                                for cheque in cheques_ids:
                                    payments_obj.write(cr, uid, cheque, {'state': 'paid', 'deposit_id': inv.id})

                    ref_move = total.mode_id.name+' / '+inv.name+' / PAPELETA: '+total.receipt
                    move_line = {'name': 'Depósito de ' + total.mode_id.name + ' ' + total.receipt,
                                 'reference': ref_move,
                                 'debit': total.amount,
                                 'credit': 0,
                                 'account_id': total.account_id.id,
                                 'move_id': move_id,
                                 'journal_id': inv.journal_id.id,
                                 'period_id': inv.period_id.id,
                                 'currency_id': total.mode_id.company_id.currency_id.id,
                                 'partner_id': inv.company_id.id,
                                 'date': inv.closing_date,
                                 'statement_id': inv.id,
                                 }
                    id_move = move_line_pool.create(cr, uid, move_line)
                    moves.append(id_move)
                    self.pool.get('deposit.register').create(cr, uid, {'printer_id': inv.printer_id.id,
                                                                       'mode_id': total.mode_id.id,
                                                                       'amount_cash': total.amount,
                                                                       'date': total.receipt_date,
                                                                       'cash_id': inv.id,
                                                                       'receipt': total.receipt,
                                                                       'deposit_checks': False,
                                                                       'state': 'deposit',
                                                                       'account_deposit_id': total.account_id.id,
                                                                       'journal_id': inv.journal_id.id,
                                                                       })
                move_line = {'name': 'Depósito de ' + total.mode_id.name + ' ' + inv.name,
                             'reference': ref_move,
                             'debit': 0,
                             'credit': suma,
                             'account_id': mode.debit_account_id.id,
                             'move_id': move_id,
                             'journal_id': inv.journal_id.id,
                             'period_id': inv.period_id.id,
                             'partner_id': inv.company_id.id,
                             'currency_id': total.mode_id.company_id.currency_id.id,
                             'date': inv.closing_date,
                             'statement_id': inv.id,
                             }
                id_move = move_line_pool.create(cr, uid, move_line)
                moves.append(id_move)
            if not moves:
                move_pool.unlink(cr, uid, [move_id], context)
            else:
                move_pool.post(cr, uid, [move_id], context)
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, rec_ids)
            statement_obj.write(cr, uid, [inv.id], {'deposit': True, 'move_id': move_id})
        return {'type': 'ir.actions.act_window_close'}

deposit_statement_wizard()


class deposit_statement_wizard_line(osv.osv_memory):
    _name = "deposit.statement.wizard.line"

    _columns = {'wizard_id': fields.many2one('deposit.statement.wizard', 'wizard', required=False),
                'account_id': fields.many2one('account.account', 'Account to Deposit', required=False),
                'receipt': fields.char('Deposit Receipt Number', size=32, required=False, readonly=False),
                'receipt_date': fields.date('Cash Date Deposit', readonly=False),
                'amount': fields.float('amount', digits=(16, 2)),
                'mode_id': fields.many2one('payment.mode', 'mode', required=False)}

    _defaults = {'receipt_date': time.strftime('%Y-%m-%d'),
                 'mode_id': None}

    def onchange_mode_id(self, cr, uid, ids, statement, mode_id, context=None):
        res = {}
        amount_in = 0.00
        if statement:
            statement_browse = self.pool.get('account.bank.statement').browse(cr, uid, statement)
            if not mode_id:
                res['mode_id'] = []
                res['account_id'] = []
            elif mode_id:
                modes_ids = self.pool.get('account.total.line').search(cr, uid, [('mode_id', '=', mode_id),
                                                                                 ('cash_id', '=', statement_browse.id)])
                if modes_ids:
                    total_ids = self.pool.get('account.total.line').browse(cr, uid, modes_ids)
                    for total_id in total_ids:
                        if total_id and total_id.type in ('customer', 'changed'):
                            amount_in += total_id.amount
                        if total_id and total_id.type in ('supplier') and total_id.mode_id.cash:
                            amount_in -= total_id.amount
                    res['mode_id'] = self.pool.get('payment.mode').browse(cr, uid, mode_id).id
                    res['amount'] = amount_in
                else:
                    raise osv.except_osv(_('Error !'), _('Solo puede depositar Modos de Pago que esten incluidos en la Caja Registradora !'))
        return {'value': res}
        return True

deposit_statement_wizard_line()