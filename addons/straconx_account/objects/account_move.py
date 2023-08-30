# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
#
##############################################################################

from osv import fields, osv, orm
from tools.translate import _
from lxml import etree
from operator import itemgetter
from datetime import datetime
import time
import tools
import netsvc


class account_move(osv.osv):
    _inherit = "account.move"

    _columns = {'create_uid': fields.many2one('res.users', 'Responsible', readonly=True,
                                              states={'draft': [('readonly', False)]}),
                'address_id': fields.many2one('res.partner.address', 'Address', readonly=True, states={'draft': [('readonly', False)]}),
                'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft': [('readonly', False)]}),
                'partner_id': fields.many2one('res.partner', 'Partner', readonly=True, states={'draft': [('readonly', False)]}),
                'details': fields.char('Name', size=256, readonly=True, states={'draft': [('readonly', False)]}),
                'ref': fields.char('Reference', size=256, readonly=True, states={'draft': [('readonly', False)]}),
                'name': fields.char('Number', size=256, required=True),
                'department_id': fields.many2one('hr.department', 'Department'),
                'state': fields.selection([('draft', 'Unposted'), ('posted', 'Posted'), ('cancel', 'Cancel')],
                                          'State', required=True, readonly=True,
                                          help='All manually created new journal entries are usually in the state \'Unposted\', but you can set the '
                                          'option to skip that state on the related journal. In that case, they will be behave as journal entries '
                                          'automatically created by the system on document validation (invoices, bank statements...) and will be '
                                          'created in \'Posted\' state.'),
                }

    def post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice = context.get('invoice', False)
        obj_sequence = self.pool.get('ir.sequence')
        movesPool = self.pool.get('account.move.line')  # obtener movimientos de linea
        res_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        valid_moves = self.validate(cr, uid, ids, context)
        new_name = '/'
        if not valid_moves:
            raise osv.except_osv(_('Integrity Error !'),
                                 _('You can not validate a non-balanced entry !\nMake sure you have configured payment terms properly !\nThe latest payment term line should be of the type "Balance" !'))
        for move in self.browse(cr, uid, valid_moves, context=context):
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                        new_name = obj_sequence.next_by_id(cr, uid, journal.sequence_id.id, c)
                    else:
                        raise osv.except_osv(_('Error'), _('No sequence defined on the journal !'))
                if new_name:
                    new_name = new_name
                else:
                    new_name = move.name
#                    self.write(cr, uid, [move.id], {'name':new_name})
            else:
                new_name = move.name
            shop = move.shop_id and move.shop_id.id or None
            if not move.shop_id:
                if context.get('search_shop', False):
                    shop_ids = self.pool.get('sale.shop').search(cr, uid, [], limit=1)
                    shop = res_user.printer_point_ids and res_user.printer_point_ids[0].shop_id.id or shop_ids and shop_ids[0] or None
            if not shop:
                raise osv.except_osv(_('Shop required !'), _('You need a shop for continue!'))
            cr.execute('UPDATE account_move SET shop_id=%s, name=%s WHERE id=%s', (shop, new_name, move.id))
            partner = move.partner_id.id or None
            if not move.partner_id:
                partner = move.company_id and move.company_id.partner_id.id or None
            name = move.details
            moves = movesPool.search(cr, uid, [('move_id', '=', move.id), ('credit', '=', 0), ('debit', '=', 0)])
            if moves:
                cr.execute('DELETE FROM account_move_line where id in %s', (tuple(moves),))
            cr.execute('UPDATE account_move_line SET  write_date =now(), active=True, partner_id=%s WHERE move_id=%s AND partner_id is null',
                       (partner, move.id))
            cr.execute('UPDATE account_move_line SET  write_date =now(), active=True, name=%s WHERE move_id=%s AND name is null', (name, move.id))
        cr.execute('UPDATE account_move SET  write_date =now(), state=%s WHERE id IN %s', ('posted', tuple(valid_moves),))
        #  actualiza los movimientos
        return super(account_move, self).post(cr, uid, ids, context)

    def onchange_period(self, cr, uid, ids, date, context=None):
        values = {}
        account_period = self.pool.get('account.period')
        if date:
            period_ids = account_period.search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)])

            for period_id in period_ids:
                period_id = account_period.browse(cr, uid, period_id)
                if period_id.state != 'draft':
                    raise osv.except_osv(_('¡Período cerrado!'),
                                         _('¡El período que usted ha elegido ya ha sido cerrado y no se pueden agregar más movimientos!'))
                else:
                    values['period_id'] = period_id.id
            if not period_ids:
                raise osv.except_osv(_('Period required !'), _('Input date no have a defined period.Check period state or create fiscal year!'))
        return {'value': values}

    def trans_unreconcile(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        reconcile_pool = self.pool.get('account.move.reconcile')
        if ids:
            recs = []
            for id in ids:
                if self.browse(cr, uid, id):
                    for line in self.browse(cr, uid, id).line_id:
                        if line.reconcile_id:
                            recs += [line.reconcile_id.id]
                            cr.execute("""update account_move_line set reconcile_id = Null where reconcile_id = %s""", (line.reconcile_id.id,))
                        if line.reconcile_partial_id:
                            recs += [line.reconcile_partial_id.id]
                            self.pool.get('account.move.line').write(cr, uid, [line.id], {'reconcile_partial_id': False})
            if recs:
                reconcile_pool.unlink(cr, uid, recs)
        return True

    #
    # Validate a balanced move. If it is a centralised journal, create a move.
    #
    def validate(self, cr, uid, ids, context=None):
        if context and ('__last_update' in context):
            del context['__last_update']

        # Maintains a list of moves which can be responsible to create analytic entries
        valid_moves = []
        obj_move_line = self.pool.get('account.move.line')
        for move in self.browse(cr, uid, ids, context):
            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id = None
            for line in move.line_id:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state == 'draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise osv.except_osv(_('Error'), _("Couldn't create move between different companies"))

                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id !=
                                                                                  line.account_id.company_id.currency_id.id):
                        raise osv.except_osv(_('Error'), _("""Couldn't create move with currency different from the secondary currency of the account "%s - %s". Clear the secondary currency field of the account definition if you want to accept all currencies.""") % (line.account_id.code, line.account_id.name))

            if abs(amount) < 10 ** -4:
                valid_moves.append(move)
                if not line_draft_ids:
                    continue
#                obj_move_line.write(cr, uid, line_draft_ids, {'state': 'valid'}, context, check=False)
                cr.execute("""update account_move_line set active=True, state='valid' where id in %s """,(tuple(line_draft_ids),))
                account = {}
                account2 = {}

                if journal.type in ('purchase','sale'):
                    for line in move.line_id:
                        code = amount = 0
                        key = (line.account_id.id, line.tax_code_id.id)
                        if key in account2:
                            code = account2[key][0]
                            amount = account2[key][1] * (line.debit + line.credit)
                        elif line.account_id.id in account:
                            code = account[line.account_id.id][0]
                            amount = account[line.account_id.id][1] * (line.debit + line.credit)
                        if (code or amount) and not (line.tax_code_id or line.tax_amount):
                            obj_move_line.write(cr, uid, [line.id], {
                                'tax_code_id': code,
                                'tax_amount': amount
                            }, context, check=False)
            elif journal.centralisation:
                # If the move is not balanced, it must be centralised...

                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                #
                # Update the move lines (set them as valid)
                #
                self._centralise(cr, uid, move, 'debit', context=context)
                self._centralise(cr, uid, move, 'credit', context=context)
                obj_move_line.write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)
            else:
                # We can't validate it (it's unbalanced)
                # Setting the lines as draft
                obj_move_line.write(cr, uid, line_ids, {
                    'state': 'draft'
                }, context, check=False)
        # Create analytic lines for the valid moves
#         for record in valid_moves:
#             obj_move_line.create_analytic_lines(cr, uid, [line.id for line in record.line_id], context)

        valid_moves = [move.id for move in valid_moves]
        return len(valid_moves) > 0 and valid_moves or False

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        toremove = []
        obj_move_line = self.pool.get('account.move.line')
        for move in self.browse(cr, uid, ids, context=context):
            line_ids = map(lambda x: x.id, move.line_id)
            context['journal_id'] = move.journal_id.id
            context['period_id'] = move.period_id.id
            obj_move_line._update_check(cr, uid, line_ids, context)
            obj_move_line.unlink(cr, uid, line_ids, context=context)
            toremove.append(move.id)
        if toremove:
            cr.execute("""update account_move set write_date = now(), state='cancel' where id in %s """, (tuple(toremove),))
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        rc_id = False
        for line in self.browse(cr, uid, ids, context=context):
            if line.period_id.state == 'done':
                raise osv.except_osv(_('Error !'), _('You can not modify a posted entry of closed periods'))
            elif not line.journal_id.update_posted:
                raise osv.except_osv(_('Error !'), _('You can not modify a posted entry of this journal !\nYou should set the journal to allow cancelling entries if you want to do that.'))
            for move_line in line.line_id:
                if move_line.reconcile_id:
                    rc_id = move_line.reconcile_id.id
                    cr.execute("""update account_move_line set write_date=now(), reconcile_id=Null where reconcile_id = %s and id=%s""",
                               (move_line.reconcile_id.id, move_line.id))
                    cr.execute("""update account_move_line set write_date=now(), reconcile_id=Null, reconcile_partial_id=%s where reconcile_id = %s and id!=%s""",
                               (move_line.reconcile_id.id, move_line.reconcile_id.id, move_line.id))
        if ids:
            cr.execute("UPDATE account_move_line "
                       "SET state=%s "
                       "WHERE move_id IN %s and state !='cancel' ", ('draft', tuple(ids),))

            cr.execute('UPDATE account_move '
                       'SET state=%s '
                       'WHERE id IN %s', ('draft', tuple(ids),))
        if rc_id:
            cr.execute("""select id from account_move_line where reconcile_partial_id=%s""", (rc_id,))
            data = cr.fetchall()

            if not data or data[0] == 'None':
                cr.execute("""delete from account_move_reconcile where id = %s""", (move_line.reconcile_id.id,))
        return True

#     def copy(self, cr, uid, id, default={}, context=None):
#         move = super(account_move, self).copy(cr, uid, id, default, context)
#         if move:
#             move = self.browse(cr, uid, move, context=None)
#             if move.line_id:
#                 for line in move.line_id:
#                     line.write({'state': 'draft'})
#         return move.id

#
    # TODO: Check if period is closed !
    #
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'line_id' in vals and context.get('copy'):
            for l in vals['line_id']:
                if not l[0]:
                    l[2].update({'reconcile_id': False,
                                 'reconcile_partial_id': False,
                                 'analytic_lines': False,
                                 'invoice': False,
                                 'ref': False,
                                 'balance': False,
                                 'account_tax_id': False,
                                 'state': 'draft'
                                 })

            if 'journal_id' in vals and vals.get('journal_id', False):
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['journal_id'] = vals['journal_id']
                context['journal_id'] = vals['journal_id']
            if 'period_id' in vals:
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = vals['period_id']
                context['period_id'] = vals['period_id']
            else:
                default_period = self._get_period(cr, uid, context)
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = default_period
                context['period_id'] = default_period

        if 'line_id' in vals:
            c = context.copy()
            c['novalidate'] = True
            result = super(osv.osv, self).create(cr, uid, vals, c)
        else:
            result = super(osv.osv, self).create(cr, uid, vals, context)
        return result


account_move()


class account_move_line(osv.osv):
    _inherit = "account.move.line"

    _rec_name = 'ref'

    def _amount_residual(self, cr, uid, ids, field_names, args, context=None):
        """
           This function returns the residual amount on a receivable or payable account.move.line.
           By default, it returns an amount in the currency of this journal entry (maybe different
           of the company currency), but if you pass 'residual_in_company_currency' = True in the
           context then the returned amount will be in company currency.
        """
        res = {}
        if context is None:
            context = {}
        cur_obj = self.pool.get('res.currency')
        mv_l_ids = self.search(cr, uid, [('id', 'in', ids), '|', ('reconcile_id', '=', False), ('account_id.type', 'in', ('payable', 'receivable'))])
        move_line_ids = self.browse(cr, uid, mv_l_ids)
#        for move_line in self.browse(cr, uid, ids, context=context):
        for move_line in move_line_ids:
            res[move_line.id] = {
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            }

            if move_line.currency_id:
                move_line_total = move_line.amount_currency
                sign = move_line.amount_currency < 0 and -1 or 1
            else:
                move_line_total = move_line.debit - move_line.credit
                sign = (move_line.debit - move_line.credit) < 0 and -1 or 1
            line_total_in_company_currency = move_line.debit - move_line.credit
            context_unreconciled = context.copy()
            if move_line.reconcile_partial_id:
                for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                    if payment_line.id == move_line.id:
                        continue
                    if payment_line.currency_id and move_line.currency_id and payment_line.currency_id.id == move_line.currency_id.id:
                            move_line_total += payment_line.amount_currency
                    else:
                        if move_line.currency_id:
                            context_unreconciled.update({'date': payment_line.date})
                            amount_in_foreign_currency = cur_obj.compute(cr, uid, move_line.company_id.currency_id.id, move_line.currency_id.id,
                                                                         (payment_line.debit - payment_line.credit), round=False,
                                                                         context=context_unreconciled)
                            move_line_total += amount_in_foreign_currency
                        else:
                            move_line_total += (payment_line.debit - payment_line.credit)
                    line_total_in_company_currency += (payment_line.debit - payment_line.credit)

            type = context.get('type', False)
            if type in ('in_invoice', 'out_refund') and line_total_in_company_currency < 0:
                sign = -1
            elif type in ('in_invoice', 'out_refund') and line_total_in_company_currency > 0:
                sign = 1
            elif type in ('out_invoice', 'in_refund') and line_total_in_company_currency > 0:
                sign = 1
            elif type in ('out_invoice', 'in_refund') and line_total_in_company_currency < 0:
                sign = -1
            else:
                if line_total_in_company_currency < 0:
                    sign = -1
                else:
                    sign = 1
            result = line_total_in_company_currency
            res[move_line.id]['amount_residual_currency'] = sign * (move_line.currency_id and
                                                                    self.pool.get('res.currency').round(cr, uid,
                                                                                                        move_line.currency_id,
                                                                                                        result) or result)
            res[move_line.id]['amount_residual'] = sign * line_total_in_company_currency
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.ref:
                result.append((line.id, (line.ref)))
            elif line.move_id:
                name = self.browse(cr, uid, line.move_id.id).browse
                if name:
                    name = line.move_id.name
                    result.append((line.id, line.move_id.name))
            else:
                return result
        return result

    def _ref(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.read(cr, uid, ids, ['reference']):
            if line['reference']:
                result[line['id']] = line['reference']
            else:
                result[line['id']] = self.browse(cr, uid, line['id']).move_id.ref
        return result

    def create_analytic_lines(self, cr, uid, ids, context=None):
        return True

#    @profile
    def create(self, cr, uid, vals, context=None, check=True):
        account_obj = self.pool.get('account.account')
        tax_obj = self.pool.get('account.tax')
        move_obj = self.pool.get('account.move')
        cur_obj = self.pool.get('res.currency')
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}
        vals['state'] = 'draft'
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad account!'), _('You can not use an inactive account!'))
        if 'journal_id' in vals:
            context['journal_id'] = vals['journal_id']
        else:
            context['journal_id'] = False
        if 'period_id' in vals:
            context['period_id'] = vals['period_id']
        else:
            if 'date' in vals:
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', vals['date']),
                                                                              ('date_stop', '>=', vals['date'])])
                if period_ids:
                    context['period_id'] = period_ids[-1]
        if not context['journal_id'] and ('move_id' in vals) and vals['move_id']:
            m = move_obj.browse(cr, uid, vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['period_id'] = m.period_id.id
        # we need to treat the case where a value is given in the context for period_id as a string
        if 'period_id' not in context or not isinstance(context.get('period_id', ''), (int, long)):
            period_candidate_ids = self.pool.get('account.period').name_search(cr, uid, name=context.get('period_id', ''))
            if len(period_candidate_ids) != 1:
                raise osv.except_osv(_('Encoding error'), _('No period found or more than one period found for the given date.'))
            context['period_id'] = period_candidate_ids[0][0]
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        self._update_journal_check(cr, uid, context['journal_id'], context['period_id'], context)
        move_id = vals.get('move_id', False)
        journal = journal_obj.browse(cr, uid, context['journal_id'], context=context)
        if not move_id:
            if journal.centralisation:
                # Check for centralisation
                res = self._check_moves(cr, uid, context)
                if res:
                    vals['move_id'] = res[0]
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'period_id': context['period_id'],
                        'journal_id': context['journal_id']
                    }
                    if vals.get('ref', ''):
                        v.update({'ref': vals['ref']})
                    move_id = move_obj.create(cr, uid, v, context)
                    vals['move_id'] = move_id
                else:
                    raise osv.except_osv(_('No piece number !'),
                                         _('Can not create an automatic sequence for this piece! \nPut a sequence in the journal definition for '
                                           'automatic numbering or create a sequence manually for this piece.'))
        if vals.get('ref', ''):
            vals['ref'] = vals.get('ref', '')
        ok = not (journal.type_control_ids or journal.account_control_ids)
        if ('account_id' in vals):
            account = account_obj.browse(cr, uid, vals['account_id'], context=context)
            if journal.type_control_ids:
                type = account.user_type
                for t in journal.type_control_ids:
                    if type.code == t.code:
                        ok = True
                        break
            if journal.account_control_ids and not ok:
                for a in journal.account_control_ids:
                    if a.id == vals['account_id']:
                        ok = True
                        break
            if not ('analytic_account_id' in vals):
                if account.analytic_account_id:
                    vals['analytic_account_id'] = account.analytic_account_id.id
            if not ('cost_journal' in vals):
                cost_obj = self.pool.get('account.analytic.journal')
                cost_journal = cost_obj.search(cr, uid, [('default', '=', True)])
                if cost_journal:
                    vals['cost_journal'] = cost_journal[0]
            if not ('department_id' in vals):
                if account.department_id:
                    vals['department_id'] = account.department_id.id
            # Automatically convert in the account's secondary currency if there is one and
            # the provided values were not already multi-currency
            if account.currency_id and (vals.get('amount_currency', False) is False) and account.currency_id.id != account.company_id.currency_id.id:
                vals['currency_id'] = account.currency_id.id
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                debit = float(vals.get('debit', 0.0))
                credit= float(vals.get('credit', 0.0))
                vals['amount_currency'] = cur_obj.compute(cr, uid, account.company_id.currency_id.id,
                                                          account.currency_id.id, debit-credit, context=ctx)
        if not ok:
            raise osv.except_osv(_('Bad account !'), _('You can not use this general account in this journal, check the tab \'Entry Controls\' on '
                                                       ' the related journal !'))

        result = super(osv.osv, self).create(cr, uid, vals, context=context)

        # CREATE Taxes
        if vals.get('account_tax_id', False):
            tax_id = tax_obj.browse(cr, uid, vals['account_tax_id'])
            total = vals['debit'] - vals['credit']
            if journal.type in ('purchase_refund', 'sale_refund'):
                base_code = 'ref_base_code_id'
                tax_code = 'ref_tax_code_id'
                account_id = 'account_paid_id'
                base_sign = 'ref_base_sign'
                tax_sign = 'ref_tax_sign'
            else:
                base_code = 'base_code_id'
                tax_code = 'tax_code_id'
                account_id = 'account_collected_id'
                base_sign = 'base_sign'
                tax_sign = 'tax_sign'
            tmp_cnt = 0
            for tax in tax_obj.compute_all(cr, uid, [tax_id], total, 1.00, force_excluded=True).get('taxes'):
                # create the base movement
                if tmp_cnt == 0:
                    if tax[base_code]:
                        tmp_cnt += 1
                        self.write(cr, uid, [result], {'tax_code_id': tax[base_code],
                                                       'tax_amount': tax[base_sign] * abs(total)})
                else:
                    data = {
                        'move_id': vals['move_id'],
                        'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                        'date': vals['date'],
                        'partner_id': vals.get('partner_id', False),
                        'ref': vals.get('ref', False),
                        'account_tax_id': False,
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                        'account_id': vals['account_id'],
                        'credit': 0.0,
                        'debit': 0.0,
                    }
                    if data['tax_code_id']:
                        self.create(cr, uid, data, context)
                # create the VAT movement
                data = {
                    'move_id': vals['move_id'],
                    'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id', False),
                    'ref': vals.get('ref', False),
                    'account_tax_id': False,
                    'tax_code_id': tax[tax_code],
                    'tax_amount': tax[tax_sign] * abs(tax['amount']),
                    'account_id': tax[account_id] or vals['account_id'],
                    'credit': tax['amount'] < 0 and -tax['amount'] or 0.0,
                    'debit': tax['amount'] > 0 and tax['amount'] or 0.0,
                }
                if data['tax_code_id']:
                    self.create(cr, uid, data, context)
            del vals['account_tax_id']

        return result

    def create2(self, cr, uid, vals, context=None, check=True):
        if vals:
            return super(osv.osv, self).create(cr, uid, vals, context=context)

    def _get_move_lines(self, cr, uid, ids, context=None):
        result = []
        for move in self.pool.get('account.move').browse(cr, uid, ids, context=context):
            for line in move.line_id:
                result.append(line.id)
        return result

    _columns = {'reference': fields.char('Reference', size=256, required=False, help="Transaction document reference as Chq # 27"),
                'ref': fields.function(_ref, method=True, type='char', size=256, string='Reference', store=True),
                'address_id': fields.related('move_id', 'address_id', type='many2one', relation='res.partner.address', string="Address", store=True),
                'name': fields.char('Name', size=256, required=False, help="Name of account move, ex:'Pay of Invoice'"),
                'journal_id': fields.related('move_id', 'journal_id', string='Journal', type='many2one', relation='account.journal', select=True,
                                             store={'account.move': (_get_move_lines, ['journal_id'], 20)}),
                'shop_id': fields.related('move_id', 'shop_id', string='Shop', type='many2one', relation='sale.shop', select=True, store=True),
                'department_id': fields.many2one('hr.department', 'Department'),
                'amount_residual': fields.function(_amount_residual, string='Residual Amount', multi="residual",
                                                   help="The residual amount on a receivable or payable of a journal entry expressed  "
                                                   "in the company currency."),
                'amount_residual_currency': fields.function(_amount_residual, string='Residual Amount', multi="residual",
                                                            help="The residual amount on a receivable or payable of a journal entry expressed in"
                                                            " its currency (maybe different of the company currency)."),
                'active': fields.boolean('Active'),
                'state': fields.selection([('draft', 'Unbalanced'), ('valid', 'Valid'), ('cancel', 'Cancel')], 'State', readonly=True,
                                          help='When new move line is created the state will be \'Draft\'.\n*'
                                          'When all the payments are done it will be in \'Valid\' state.'),
                'cost_journal': fields.many2one('account.analytic.journal', 'Cost Journal')
                }

    _defaults = {'active': True,
                 'period_id': lambda self, cr, uid, c: c.get('period_id', False)}

    def _update_check(self, cr, uid, ids, context=None):
        done = {}
        recs = []
        for line in self.browse(cr, uid, ids, context=context):
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft' and (not line.journal_id.entry_posted):
                return True
            if line.reconcile_id:
                reconcile_pool = self.pool.get('account.move.reconcile')
                if line.reconcile_id:
                    recs += [line.reconcile_id.id]
                if line.reconcile_partial_id:
                    recs += [line.reconcile_partial_id.id]
                reconcile_pool.unlink(cr, uid, recs)
            t = (line.journal_id.id, line.period_id.id)
            if t not in done:
                self._update_journal_check(cr, uid, line.journal_id.id, line.period_id.id, context)
                done[t] = True
        return True

    def on_change_amount_currency(self, cr, uid, ids, debit=0.00, credit=0.00, currency_id=False, company_id=False, context=None):
        result = {}
        amount_currency = 0.00
        dp = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
        cur_obj = self.pool.get('res.currency')
        company_obj = self.pool.get('res.company')
        if company_id:
            company_id = company_obj.browse(cr, uid, company_id)
            company_currency = company_id.currency_id.id
        if currency_id:
            currency_id = cur_obj.browse(cr, uid, currency_id)
        else:
            currency_id = cur_obj.browse(cr, uid, company_currency)
        if currency_id.id == company_currency:
            cd = cur_obj.browse(cr, uid, company_currency).rate
        if not cd:
            cd = 1
        if debit > 0:
            amount_currency = round(debit*cd, dp)
        elif credit > 0:
            amount_currency = round(debit*cd, dp)
        result['amount_currency'] = amount_currency
        return result

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
#         self._update_check(cr, uid, ids, context)
#         result = False
        move_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            move_ids.append(line.id)
#             context['journal_id'] = line.journal_id.id
#             context['period_id'] = line.period_id.id
        if move_ids:
            cr.execute("update account_move_line set write_date=now(), state='cancel', active=False ,credit = 0.00, debit = 0.00,"
                       "amount_currency=0.00,reconcile_id = Null, reconcile_partial_id = Null where id in %s", (tuple(move_ids),))
            cr.execute("UPDATE account_analytic_line SET write_date=now(), state='cancel' FROM account_move_line"
                       " WHERE account_move_line.id in %s AND account_analytic_line.move_id = account_move_line.id", ((tuple(move_ids), )))
#         move_ids = set(list(move_ids))
#         if check and move_ids:
#             move_obj.validate(cr, uid, move_ids, context=context)
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        journal_pool = self.pool.get('account.journal')
        if context is None:
            context = {}
        result = super(osv.osv, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        return result

    def _query_get(self, cr, uid, obj='l', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        if context is None:
            context = {}
        query = ''
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        if context.get('company_id', False):
            company_clause = " AND " + obj + ".company_id = %s" % context.get('company_id', False)
        if not context.get('fiscalyear', False):
            if context.get('all_fiscalyear', False):
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            fiscalyear_ids = [context['fiscalyear']]

        fiscalyear_clause = (','.join([str(x) for x in fiscalyear_ids])) or '0'
        if not context.get('state', False):
            state = 'posted'
        elif context.get('target_move', 'posted'):
            state = context.get('target_move', 'posted')
        else:
            state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''
        target_move = context.get('target_move', 'posted')

        if context.get('date_from', False) and context.get('date_to', False):
            if initial_bal:
                where_move_lines_by_date = " AND " + obj + ".move_id IN (SELECT id FROM account_move WHERE date < '" + context['date_from'] + "')"
            else:
                where_move_lines_by_date = " AND " + obj + ".move_id IN (SELECT id FROM account_move WHERE date BETWEEN '" + context['date_from'] + "' AND '"+context['date_to']+"')"

        if state:
            if state.lower() not in ['all']:
                where_move_state = " AND " + obj + ".move_id IN (SELECT id FROM account_move WHERE account_move.state = '" + state + "')"
        if context.get('period_from', False) and context.get('period_to', False) and not context.get('periods', False):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods', False):
            if initial_bal:
                query = obj + ".state = 'valid' AND " + obj + ".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s)) %s %s" % (fiscalyear_clause,  where_move_state, where_move_lines_by_date)
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    ids = ','.join([str(x) for x in context['periods']])
                    query = obj + ".state = 'valid' AND " + obj + ".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s) AND date_start <= '%s' AND id NOT IN (%s)) %s %s" % (fiscalyear_clause, first_period.date_start, ids, where_move_state, where_move_lines_by_date)
            else:
                ids = ','.join([str(x) for x in context['periods']])
                query = obj + ".state = 'valid' AND " + obj + ".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s) AND id IN (%s)) %s %s" % (fiscalyear_clause, ids, where_move_state, where_move_lines_by_date)
        else:
            if context.get('date_from', False) and context.get('date_to', False):
                query = obj + ".state = 'valid' AND " + obj + ".date  between '" + context['date_from'] + "' AND '"+context['date_to']+"' %s" % (where_move_state)
            else:
                query = obj+".state = 'valid' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s)) %s %s" % (fiscalyear_clause, where_move_state, where_move_lines_by_date)

        if initial_bal and not context.get('periods', False) and not where_move_lines_by_date:
            raise osv.except_osv(_('Warning !'),
                                 _("You haven't supplied enough argument to compute the initial balance, please select a period and journal in the context."))
 
        if context.get('journal_ids', False):
            query += ' AND '+obj+'.journal_id IN (%s)' % ','.join(map(str, context['journal_ids']))
 
        if context.get('chart_account_id', False):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            query += ' AND '+obj+'.account_id IN (%s)' % ','.join(map(str, child_ids))
 
        query += company_clause
        return query
    
    def onchange_lines_move_id(self, cr, uid, ids, date, company_id=False, partner_id=False, period_id=False, journal_id=False, ref='', context=None):
        result={}
        if partner_id:
            result['partner_id'] = partner_id
        if period_id:
            result['period_id'] = period_id
        else:
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date), ('state', '=', 'draft')])
            result['period_id'] = period_ids[0]
        if journal_id:
            result['journal_id'] = journal_id
        if ref:
            result['reference'] = ref
        if date: 
            result['date'] = date
            result['date_create'] = date
        return {'value': result}

account_move_line()
