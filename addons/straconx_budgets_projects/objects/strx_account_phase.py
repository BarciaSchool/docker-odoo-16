# -*- coding: utf-8 -*-

import datetime
import time
from osv import osv, fields
from tools.translate import _
import decimal_precision as dp
import netsvc
from account_voucher import account_voucher
from tools.translate import _
import tools
from openerp.osv.fields import _column

class account_analytic_phase(osv.osv):
    _name = "account.analytic.phase"

    _columns = {
        'sequence': fields.integer('Sequence'),
        'code': fields.char('Code', size=30),
        'name': fields.char('Name', size=200),
        'parent_id': fields.many2one('account.analytic.phase', 'Parent'),
        'type_phase': fields.selection([('cost', 'Cost'),
                                        ('phase', 'Phase'),
                                        ('subphase', 'Subphase'),
                                        ('work', 'Work'),
                                        ],
                                       'Phase Type')
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []

        for account in self.browse(cr, uid, ids, context=context):
            data = []
            acc = account
            while acc:
                if not acc.parent_id:
                    data.insert(0, acc.code)
                elif acc.parent_id and not acc.parent_id.parent_id:
                    new_data = acc.code
                    data.insert(0, new_data)
                else:
                    data.insert(0, acc.code + ' - ' + acc.name)
                acc = acc.parent_id
            if data and data[0]:
                data = ' / '.join(data)
                res.append((account.id, data))
        return res

    _order = "sequence, parent_id, code, name"

    def onchange_type_phase(self, cr, uid, ids, type_phase, parent_id, context=None):
        if parent_id:
            parent_id = self.browse(cr, uid, parent_id, context)
            if type_phase == 'cost' and parent_id.type_phase:
                    raise osv.except_osv(_('Error'), _('The account type cost can not a parent_id'))
            elif parent_id.type_phase == 'cost' and type_phase != 'phase':
                    raise osv.except_osv(_('Error'), _('The account type phase only can a type cost as parent_id'))
            elif parent_id.type_phase == 'phase' and type_phase != 'subphase':
                    raise osv.except_osv(_('Error'), _('The account type subphase only can a type phase as parent_id'))
            elif parent_id.type_phase == 'subphase' and type_phase != 'task':
                    raise osv.except_osv(_('Error'), _('The account type task only can a type subphase as parent_id'))
            elif ids[0] == parent_id.id:
                    raise osv.except_osv(_('Error'), _('The account can not recursive parent_id'))

    def write(self, cr, uid, ids, vals, context):
        for par_id in self.browse(cr, uid, ids, context):
            parent_id = vals.get('parent_id', False)
            type_phase = vals.get('type_phase', False)
            if parent_id:
                parent_id = self.browse(cr, uid, parent_id, context)
                if not type_phase:
                    type_phase = self.browse(cr, uid, par_id.id, context).type_phase
                if type_phase and type_phase == 'cost' and parent_id.type_phase:
                        raise osv.except_osv(_('Error'), _('The account type cost can not a parent_id'))
                elif parent_id.type_phase == 'cost' and type_phase and type_phase != 'phase':
                        raise osv.except_osv(_('Error'), _('The account type phase only can a type cost as parent_id'))
                elif parent_id.type_phase == 'phase' and type_phase and type_phase != 'subphase':
                        raise osv.except_osv(_('Error'), _('The account type subphase only can a type phase as parent_id'))
                elif parent_id.type_phase == 'subphase' and type_phase and type_phase != 'work':
                        raise osv.except_osv(_('Error'), _('The account type task only can a type subphase as parent_id'))
                elif parent_id.id == par_id.id:
                        raise osv.except_osv(_('Error'), _('The account can not recursive parent_id'))
        return super(account_analytic_phase, self).write(cr, uid, ids, vals)

account_analytic_phase()

# ACCOUNT ANALYTIC JOURNAL


class account_analytic_journal(osv.osv):
    _inherit = 'account.analytic.journal'
    _columns = {'partner_id': fields.many2one('res.partner', 'Partner'),
                'country_id': fields.many2one('res.country', 'Country'),
                'type': fields.selection([('sale', 'Sale'),
                                          ('purchase', 'Purchase'),
                                          ('general', 'General'),
                                          ('project', 'Project')], 'Type', size=32, required=True),
                'location_id': fields.many2one('stock.location', 'Location'),
                'address_id': fields.many2one('res.partner.address', 'Address'),
                'purchase_sequence': fields.many2one('ir.sequence', 'Sequence')
                }

account_analytic_journal()

# ACCOUNT BUDGET


class crossovered_budget(osv.osv):
    _inherit = "crossovered.budget"

    _columns = {'project_id': fields.many2one('account.analytic.journal', 'Offer/Project'),
                'partner_id': fields.many2one('res.partner', 'Partner')
                }

    def onchange_project_id(self, cr, uid, ids, project_id, context=None):
        project_id = self.pool.get('account.analytic.journal').browse(cr, uid, project_id, context)
        res = {}
        if project_id:
            name = project_id.name
            code = project_id.code
            partner_id = project_id.partner_id.id
            res = {'partner_id': partner_id,
                   'name': name,
                   'code': code
                   }
            return {'value': res}

    def write(self, cr, uid, ids, vals, context=None):
        proj_id = vals.get('project_id', False)
        project_id = self.pool.get('account.analytic.journal').browse(cr, uid, proj_id, context)
        if project_id:
            name = project_id.name
            code = project_id.code
            partner_id = project_id.partner_id.id
            vals['partner_id'] = partner_id
            vals['name'] = name
            vals['code'] = code
        return super(crossovered_budget, self).write(cr, uid, ids, vals)


crossovered_budget()

# ACCOUNT BUDGET LINE


class crossovered_budget_lines(osv.osv):
    _inherit = "crossovered.budget.lines"
    _columns = {'wbs_phase': fields.many2one('account.analytic.phase', 'Subphase/Work')}

    def _prac_amt(self, cr, uid, ids, context=None):
        res = {}
        result = 0.0
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id and line.crossovered_budget_id.project_id:
                cr.execute("SELECT SUM(debit-credit) FROM account_move_line WHERE analytic_account_id=%s AND (date "
                           "between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) AND state='valid' AND "
                           "cost_journal = %s AND wbs_phase = %s ",
                           (line.analytic_account_id.id, date_from, date_to, line.crossovered_budget_id.project_id.id, line.wbs_phase.id))
            else:
                if line.department_id:
                    department_id = line.department_id.id
                else:
                    department_id = None
                cr.execute("SELECT SUM(debit-credit) FROM account_move_line WHERE analytic_account_id=%s AND (date "
                           "between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) AND state='valid' AND "
                           "department_id = %s and shop_id =%s",
                           (line.analytic_account_id.id, date_from, date_to, department_id, line.shop_id.id))
            result = cr.fetchone()[0]
            if result is None:
                result = 0.00
            res[line.id] = result
        return res


crossovered_budget_lines()

# ACCOUNT BUDGET POST


class account_budget_post(osv.osv):
    _inherit = "account.budget.post"
    _description = "Budgetary Position"
    _columns = {'req_dep': fields.boolean('Req. Depart.')}

    def onchange_required(self, cr, uid, ids, crossovered_budget_id, context=None):
        req_dep = True
        crossovered_budget_id = self.pool.get('crossovered.budget').browse(cr, uid, crossovered_budget_id, context)
        res = {}
        if crossovered_budget_id:
            project_id = crossovered_budget_id.project_id.id
            if project_id:
                req_dep = False
            res = {'req_dep': req_dep}
            return {'value': res}

    def create(self, cr, uid, vals, context=None):
        req_dep = True
        budget_id = vals.get('crossovered_budget_id', False)
        crossovered_budget_id = self.pool.get('crossovered.budget').browse(cr, uid, budget_id, context)
        if crossovered_budget_id:
            project_id = crossovered_budget_id.project_id.id
            if project_id:
                req_dep = False
            vals['req_dep'] = req_dep
        return super(account_budget_post, self).create(cr, uid, vals)

    def write(self, cr, uid, ids, vals, context=None):
        req_dep = True
        budget_id = vals.get('crossovered_budget_id', False)
        crossovered_budget_id = self.pool.get('crossovered.budget').browse(cr, uid, budget_id, context)
        if crossovered_budget_id:
            project_id = crossovered_budget_id.project_id.id
            if project_id:
                req_dep = False
            vals['req_dep'] = req_dep
        return super(account_budget_post, self).write(cr, uid, ids, vals)

account_budget_post()

# ACCOUNT_MOVE


class account_move_line(osv.osv):
    _inherit = "account.move.line"
    _columns = {'wbs_phase': fields.many2one('account.analytic.phase', 'Subphase/Work', required=False)}
    
    def reconcile_partial(self, cr, uid, ids, type='auto', context=None, writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        move_rec_obj = self.pool.get('account.move.reconcile')
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        company_list = []

        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning !'), _('To reconcile the entries company should be the same for all entries'))
            company_list.append(line.company_id.id)

        for line in self.browse(cr, uid, ids, context=context):
            if line.account_id.currency_id:
                currency_id = line.account_id.currency_id
            else:
                currency_id = line.company_id.currency_id
            if line.reconcile_id:
                raise osv.except_osv(_('Warning'), _('Already Reconciled!'))
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2.id)
                        if line2.account_id.currency_id:
                            total += line2.amount_currency
                        else:
                            total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id.id)
            else:
                unmerge.append(line.id)
                total += (line.debit or 0.0) - (line.credit or 0.0)
        if self.pool.get('res.currency').is_zero(cr, uid, currency_id, total):
            res = self.reconcile(cr, uid, merges+unmerge, context=context, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
            return res
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        })
        move_rec_obj.reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=context)
        return True
    
    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None):
        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_rec_obj = self.pool.get('account.move.reconcile')
        partner_obj = self.pool.get('res.partner')
        currency_obj = self.pool.get('res.currency')
        lines = self.browse(cr, uid, ids, context=context)
        unrec_lines = filter(lambda x: not x['reconcile_id'], lines)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        if context is None:
            context = {}
        company_list = []
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning !'), _('To reconcile the entries company should be the same for all entries'))
            company_list.append(line.company_id.id)
        for line in unrec_lines:
            if line.state <> 'valid':
                raise osv.except_osv(_('Error'),
                        _('Entry "%s" is not valid !') % line.name)
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit

        # Ifdate_p in context => take this date
        date = context.get('date_p') or time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(ids), ))
        r = cr.fetchall()
        #TODO: move this check to a constraint in the account_move_reconcile object
        if len(r) != 1:
            raise osv.except_osv(_('Error'), _('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise osv.except_osv(_('Error'), _('Entry is already reconciled'))
        account = account_obj.browse(cr, uid, account_id, context=context)
        if account.currency_id:
            currency = 0.00
        if not account.reconcile:
            raise osv.except_osv(_('Error'), _('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise osv.except_osv(_('Error'), _('Some entries are already reconciled !'))

        if (not currency_obj.is_zero(cr, uid, account.company_id.currency_id, writeoff)) or \
           (account.currency_id and (not currency_obj.is_zero(cr, uid, account.currency_id, currency))):
            if not writeoff_acc_id:
                raise osv.except_osv(_('Warning'), _('You have to provide an account for the write off/exchange difference entry !'))
            if writeoff > 0:
                debit = writeoff
                credit = 0.0
                self_credit = writeoff
                self_debit = 0.0
            else:
                debit = 0.0
                credit = -writeoff
                self_credit = 0.0
                self_debit = -writeoff
            # If comment exist in context, take it
            if 'comment' in context and context['comment']:
                libelle = context['comment']
            else:
                libelle = _('Write-Off')

            cur_obj = self.pool.get('res.currency')
            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = cur_obj.compute(cr, uid, line.account_id.company_id.currency_id.id, context.get('currency_id',False), abs(line.debit-line.credit), context={'date': line.date})
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name': libelle,
                    'debit': self_debit,
                    'credit': self_credit,
                    'account_id': account_id,
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name': libelle,
                    'debit': debit,
                    'credit': credit,
                    'account_id': writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]

            writeoff_move_id = move_obj.create(cr, uid, {
                'period_id': writeoff_period_id,
                'journal_id': writeoff_journal_id,
                'date':date,
                'state': 'draft',
                'line_id': writeoff_lines
            })

            writeoff_line_ids = self.search(cr, uid, [('move_id', '=', writeoff_move_id), ('account_id', '=', account_id)])
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_id': map(lambda x: (4, x, False), ids),
            'line_partial_ids': map(lambda x: (3, x, False), ids)
        })
        wf_service = netsvc.LocalService("workflow")
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            wf_service.trg_trigger(uid, 'account.move.line', id, cr)

        if lines and lines[0]:
            partner_id = lines[0].partner_id and lines[0].partner_id.id or False
            if partner_id and context and context.get('stop_reconcile', False):
                partner_obj.write(cr, uid, [partner_id], {'last_reconciliation_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        return r_id
    

account_move_line()


# ACCOUNT INVOICE


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
        'wbs_phase': fields.many2one('account.analytic.phase', 'Subfase/Tarea')
        }
account_invoice_line()


class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def action_move_create(self, cr, uid, ids, *args):
        self.button_reset_taxes(cr, uid, ids, context=None)
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        obj_sequence = self.pool.get('ir.sequence')
        mod_obj = self.pool.get('ir.model.data')
        mail_message = self.pool.get('email.template')
        cost_obj = self.pool.get('account.analytic.journal')
        total_invoice = 0.00
        amount_tax = 0.00
        amount_tax2 = 0.00
        amount_tax2_p = 0.00
        amount_currency = 0.00
        amount_currency_tax2 = 0.00
        amount_currency_tax2_p = 0.00
        total_invoice_ac = 0.00
        amount2 = 0.00
        department_id = None
        wbs_phase = None
        cost_journal = None
        context = {}
        for inv in self.browse(cr, uid, ids):
            if inv.account_id:
                if inv.invoice_line:
                    for line in inv.invoice_line:
                        if line.account_id.id == inv.account_id.id:
                            raise osv.except_osv(_('¡Aviso!'),
                                                 _('¡La cuenta contable de la factura debe ser diferente de la cuenta contable de la línea %s ') %
                                                 (line.name))
            if not inv.partner_id.email and (inv.printer_id.type_printer == 'electronic' or inv.electronic) and inv.type == "out_invoice":
                raise osv.except_osv(_('¡Advertencia!'), _('¡El cliente no tiene una dirección E-mail configurada! Abra el cliente e ingrese una.'))
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error !'), _('Please define sequence on invoice journal'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
            if not inv.shop_id:
                raise osv.except_osv(_('No Shop select !'), _('Please select a shop for continue.'))
            if inv.move_id and inv.move_id.state != 'cancel':
                continue
            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice': time.strftime('%Y-%m-%d')})
            company_currency = inv.company_id.currency_id.id
            
            ctx = context.copy()
            if inv.type in ('in_invoice') and abs(inv.check_total - inv.amount_total) > 0:
                raise osv.except_osv(_('Bad total !'),
                                     _('Please verify the price of the invoice !\nThe real total does not match the computed total.'))

            if inv.type in ('in_invoice', 'in_refund'):
                self.button_reset_taxes(cr, uid, [inv.id], context)
                if inv.invoice_number_in:
                    inv.write({'reference': inv.invoice_number_in})
                else:
                    inv.write({'reference': ''})
                ref = inv.reference
            else:
                ref = self._convert_ref(cr, uid, inv.invoice_number_out)
            diff_currency_p = inv.currency_id.id != company_currency
            if diff_currency_p:
                cd = inv.company_id.currency_id.rate
            else:
                cd = 1.0
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
#            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml)
            if inv.account_id.company_id.id != inv.company_id.id:
                acc_id = self.pool.get('account.account').search(cr, uid, [('code', '=', inv.account_id.code),
                                                                           ('company_id', '=', inv.company_id.id)])
                self.write(cr, uid, ids, {'account_id': acc_id}, context)
            else:
                acc_id = inv.account_id.id
            name = None
            self.action_number(cr, uid, ids, context)
            new_name = obj_sequence.next_by_id(cr, uid, inv.journal_id.sequence_id.id)
            if inv.journal_id.type == 'purchase_liquidation':
                name = 'LIQUIDACIÓN DE COMPRAS '+ new_name 
                ref = inv.invoice_number_out
            elif inv.type == 'in_invoice':
                name = 'FACTURAS DE PROVEEDORES ' + new_name
                ref = inv.invoice_number_in
            elif inv.type == 'in_refund':
                name = 'NOTA DE CRÉDITO DE PROVEEDORES ' + new_name
                ref = inv.invoice_number_in
            elif inv.type == 'out_invoice':
                name = 'FACTURAS DE CLIENTES ' + new_name
                ref = inv.invoice_number_out
            elif inv.type == 'out_refund':
                name = 'NOTA DE CRÉDITO DE CLIENTES ' + new_name
                ref = inv.invoice_number_out
            else:
                name = inv['number'] or inv.reference or '/'
            #number_move = self.pool.get('ir.sequence').next_by_code(cr, uid, 'account.move')
            date = inv.date_invoice or time.strftime('%Y-%m-%d')
            part = inv.partner_id.id
            period_id = inv.period_id and inv.period_id.id or False
            if not period_id:
                if not inv.date_invoice:
                    date_invoice = inv.date_invoice2[0:10]
                else:
                    date_invoice = inv.date_invoice
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date_invoice or time.strftime('%Y-%m-%d')),
                                                                              ('date_stop', '>=', date_invoice or time.strftime('%Y-%m-%d')),
                                                                              ('company_id', '=', inv.company_id.id)])
                if period_ids:
                    period_id = period_ids[0]

            if inv.shop_id:
                shop_id = inv.shop_id.id
            else:
                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una tienda en el documento para continuar'))
            if inv.journal_id.centralisation:
                raise osv.except_osv(_('UserError'),
                                     _('Cannot create invoice move on centralised journal'))
            move = {
                'ref': ref,
                'journal_id': inv.journal_id.id,
                'date': date,
                'shop_id': shop_id,
                'period_id': period_id,
                'narration': inv.comment,
                'details': name,
                'partner_id': part,
                'name': name,
            }
            move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
            reference = inv.number or inv.reference or inv.invoice_number_out or inv.invoice_number_in

            create_uid = uid
            create_date = time.strftime('%Y-%m-%d %H:%M:%S')

            if inv.type in ('in_invoice', 'out_refund'):
                sql = """insert into account_move_line (create_date, create_uid, reference,journal_id,date_maturity,partner_id,name,date,debit,credit,
                    account_id,amount_currency,currency_id,ref,quantity,product_id,product_uom_id,analytic_account_id,period_id,move_id,state,
                    company_id,shop_id,department_id,cost_journal,wbs_phase,active) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,True)"""
            else:
                sql = """insert into account_move_line (create_date, create_uid, reference,journal_id,date_maturity,partner_id,name,date,credit,debit,
                    account_id,amount_currency,currency_id,ref,quantity,product_id,product_uom_id,analytic_account_id,period_id,move_id,state,
                    company_id,shop_id,department_id,cost_journal,wbs_phase,active) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,True)"""
            state_move = 'valid'

            if inv.period_id:
                period_id = inv.period_id.id
            else:
                period_id = period_id

            if inv.invoice_line:
                sum_sub = sum_sub2 = 0
                for line in inv.invoice_line:
                    if line.shop_id:
                        line_shop_id = line.shop_id.id         
                    else:
                        line_shop_id = shop_id
                    if line.account_analytic_id.id:
                        account_analytic_id = line.account_analytic_id.id
                    ref = line.name[0:64]
                    if inv.type in ('in_invoice'):
                        price_subtotal = round(line.price_subtotal, di)
                        iva_value = round(line.iva_value, di)
                        perception_value = round(line.perception_value, di)
                    elif inv.type in ('out_refund'):
                        if len(inv.invoice_line) == 1:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                            perception_value = round(line.perception_value, di)
                        else:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                            perception_value = round(line.perception_value, di)
                    else:
                        if len(inv.invoice_line) == 1:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                            perception_value = round(line.perception_value, di)
                        else:
                            price_subtotal = round(line.price_subtotal, di)
                            iva_value = round(line.iva_value, di)
                            perception_value = round(line.perception_value, di)
                    sum_sub += price_subtotal
                    sum_sub2 += price_subtotal
                    amount_tax += iva_value
                    
                    price_subtotal_currency = round(price_subtotal * cd, di)
                    amount_currency_tax = round(amount_tax*cd, di)
                    if line.product_id.id:
                        product_id = line.product_id.id
                        product_uom = line.uos_id.id
                        if not line.uos_id.id:
                            product_uom = line.product_id.uom_id.id
                    else:
                        product_id = None
                        product_uom = None
                    if line.quantity <= 0:
                        raise osv.except_osv(_('Error !'), _("Cannot create the invoice !\nQuantity in invoice must be greater than 0."))
                    if line.department_id:
                        department_id = line.department_id.id
                    else:
                        department_id = None
                    if line.cost_journal.id:
                        cost_journal = line.cost_journal.id
                    else:
                        cost_journal = cost_obj.search(cr, uid, [('default', '=', True)])
                        if cost_journal:
                            cost_journal = cost_journal[0]
                        else:
                            cost_journal = None
                    if line.account_analytic_id:
                        account_analytic_id = line.account_analytic_id.id
                    else:
                        if line.account_id.analytic_account_id:
                            account_analytic_id = line.account_id.analytic_account_id.id
                        else:
                            account_analytic_id = None
                    if line.wbs_phase.id:
                        wbs_phase = line.wbs_phase.id
                    else:
                        wbs_phase = None

                    cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, ref, date, price_subtotal, 0.00,
                                     line.account_id.id, price_subtotal_currency, inv.currency_id.id, reference, line.quantity, product_id, product_uom,
                                     account_analytic_id, period_id, move_id, state_move, inv.company_id.id, line_shop_id, department_id,
                                     cost_journal, wbs_phase))

            if inv.type in ('out_invoice', 'out_refund'):
                compute_taxes = inv.tax_line
                if compute_taxes:
                    for t in compute_taxes:
                        t_obj = self.pool.get('account.invoice.tax').browse(cr, uid, t.id)
                        if t_obj.tax_code_id.tax_type == 'vat':
                            amount_tax = round(t_obj.amount, di)
                            name_tax = t_obj.name
                            acc_id_tax = t_obj.account_id.id
                            amount_currency_tax = round(amount_tax * cd, di)
                            amount_tax2 += amount_tax
                            amount_currency_tax2 += amount_currency_tax
                        
                        if t_obj.tax_code_id.tax_type == 'perception':
                            amount_tax = round(t_obj.amount, di)
                            name_tax = t_obj.name
                            acc_id_tax = t_obj.account_id.id
                            amount_currency_tax = round(amount_tax * cd, di)
                            amount_tax2 += amount_tax
                            amount_currency_tax2 += amount_currency_tax

                        if amount_tax2 > 0 and t_obj.tax_code_id.tax_type in ('vat','perception') and t_obj.amount > 0.00:
                            if inv.type in ('in_invoice', 'out_refund'):
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax2, 0.00,
                                                 acc_id_tax, amount_currency_tax2, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id, None, None, None))
                            else:
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax2, 0.00,
                                                 acc_id_tax, amount_currency_tax2, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id, None, None, None))

            else:
                compute_taxes = inv.tax_line
                if compute_taxes:
                    for t in compute_taxes:
                        t_obj = self.pool.get('account.invoice.tax').browse(cr, uid, t.id)
                        if t_obj.tax_code_id.tax_type == 'vat':
                            amount_tax = round(t_obj.amount, di)
                            name_tax = t_obj.name
                            acc_id_tax = t_obj.account_id.id
                            amount_currency_tax = round(amount_tax * cd, di)
                            amount_tax2 += amount_tax
                            amount_currency_tax2 += amount_currency_tax
                        
                        if t_obj.tax_code_id.tax_type == 'perception':
                            amount_tax = round(t_obj.amount, di)
                            name_tax = t_obj.name
                            acc_id_tax = t_obj.account_id.id
                            amount_currency_tax = round(amount_tax * cd, di)
                            amount_tax2 += amount_tax
                            amount_currency_tax2 += amount_currency_tax                            

                        if amount_tax2 > 0 and t_obj.tax_code_id.tax_type in ('vat','perception') and t_obj.amount > 0.00:
                            if inv.type in ('in_invoice', 'out_refund'):
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax, 0.00,
                                                 acc_id_tax, amount_currency_tax, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id, None, None, wbs_phase))
                            else:
                                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name_tax, date, amount_tax2, 0.00,
                                                 acc_id_tax, amount_currency_tax2, inv.currency_id.id, name_tax, 1, None, None, None,
                                                 period_id, move_id, state_move, inv.company_id.id, shop_id,  None, None, None))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'porcent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error !'),
                                         _("Cannot create the invoice !\nThe payment term defined gives a computed amount greater than the "
                                           "total invoiced amount."))

            if inv.amount_total:
                sum = inv.amount_untaxed
                for line in inv.invoice_line:
                    sum_sub2 = round(sum_sub2, di) - round(line.price_subtotal, di)
                    sum = round(sum, di) - round(line.price_subtotal, di)
                if sum_sub2 == 0:
                    total_invoice = round(inv.amount_total, di)
                    total_currency = round((inv.amount_total * cd), di)

            totlines = False
            if inv.payment_term:
                totlines = self.pool.get('account.payment.term').compute(cr, uid, inv.payment_term.id, inv.amount_total, inv.date_invoice or False)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, t[1])
                    else:
                        amount_currency = res_amount_currency

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency
                        total_invoice_ac += abs(round(t[1], di))

                    if total_invoice_ac != inv.amount_total and len(totlines) == 1:
                        amount = abs(round(t[1], di)) - round((total_invoice_ac - inv.amount_total), di)
                        amount2 = round((total_invoice_ac - inv.amount_total), di)
                    else:
                        amount = abs(round(t[1], di))

                    if inv.type in ('in_invoice', 'in_refund'):
                        amount = amount
                        cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, t[0], part, name, date, 0.00, amount, acc_id,
                                         amount_currency, inv.currency_id.id, reference, 1, None, None, None, period_id, move_id, state_move,
                                         inv.company_id.id, shop_id, None, None, wbs_phase))
                    else:
                        amount = amount
                        cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, t[0], part, name, date, 0.00, amount, acc_id,
                                         amount_currency, inv.currency_id.id, reference, 1, None, None, None, period_id, move_id, state_move,
                                         inv.company_id.id, shop_id, None, None, None))
            else:
                cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, inv.date_due, part, name, date, 0.00, total, acc_id,
                                 amount_currency, inv.currency_id.id, reference, 1, None, None, None, period_id, move_id, state_move, inv.company_id.id,
                                 shop_id, None, None, None))
            new_move_name = self.pool.get('account.move').browse(cr, uid, move_id).name
            self.write(cr, uid, [inv.id], {'move_id': move_id, 'period_id': period_id, 'move_name': new_move_name})
            validate_moves_line = self.pool.get('account.move').browse(cr, uid, move_id).line_id
            debit = 0
            credit = 0
            if validate_moves_line:
                for line in validate_moves_line:
                    if not line.shop_id:
                        cr.execute("""update account_move_line set write_date = now(), shop_id = %s where id=%s """, (inv.shop_id.id, line.id))
                    debit += line.debit
                    credit += line.credit
                amount_new = round((debit - credit), di)
                if abs(amount_new) > 0:
                    if debit > credit:
                        acc_dis_id = inv.company_id.property_rounding_difference.id
                        if not acc_dis_id:
                            raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                        if inv.type in ('out_invoice', 'in_refund'):
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name, date, amount_new, 0.00,
                                             acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id,
                                             state_move, inv.company_id.id, shop_id, None, None, None))
                        else:
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name, date, 0.00,
                                             amount_new, acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id,
                                             move_id, state_move, inv.company_id.id, shop_id, None, None, None))
                    elif debit < credit:
                        if inv.type in ('in_invoice', 'out_refund'):
                            amount_new = abs(amount_new)
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            acc_dis_id = self.pool.get('account.account').search(cr, uid, [('name', '=', 'OTROS INGRESOS DE ACTIVIDADES ORDINARIAS'),
                                                                                           ('type', '!=', 'view'),
                                                                                           ('company_id', '=', inv.company_id.id)], limit=1)[0]
                            if not acc_dis_id:
                                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                            cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name, date, amount_new, 0.00,
                                             acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id,
                                             state_move, inv.company_id.id, shop_id, None, None, None))
                        else:
                            amount_new = abs(amount_new)
                            discount_currency = round(amount_new * cd, di)
                            name = 'AJUSTE POR REDONDEO'
                            acc_dis_id = self.pool.get('account.account').search(cr, uid, [('name', '=', 'OTROS INGRESOS DE ACTIVIDADES ORDINARIAS'),
                                                                                           ('type', '!=', 'view'),
                                                                                           ('company_id', '=', inv.company_id.id)], limit=1)[0]
                            if not acc_dis_id:
                                raise osv.except_osv(_('Acción Requerida!'), _('Necesita definir una cuenta para diferencias de redondeo'))
                            cr.execute(sql, (create_date, create_uid, reference, inv.journal_id.id, None, part, name, date, 0.00, amount_new,
                                             acc_dis_id, discount_currency, inv.currency_id.id, name, 1, None, None, None, period_id, move_id,
                                             state_move, inv.company_id.id, shop_id, None, None, None))
                            self._log_event(cr, uid, ids)
                if abs(amount_new) >= 0.05:
                    xml_id = 'email_differences_account_move'
                    template_ids = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
                    if not template_ids:
                        raise osv.except_osv(_('Error!'),
                                             _('No existe una plantilla para el envío del correo electrónico de errores de diferencias de '
                                               'valores en movimientos contables.'))
                    else:
                        template_id = template_ids[1]
                    send_id = mail_message.send_mail(cr, uid, template_id, ids[0], context)
        return True

account_invoice()

# PURCHASE_ORDER


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'
    _columns = {
        'wbs_phase': fields.many2one('account.analytic.phase', 'Subfase/Tarea'),
        'account_id': fields.many2one('account.account', 'Cuenta')
        }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty, uom, partner_id, categ_id=False, date_order=False, fiscal_position=False,
                          date_planned=False, name=False, price_unit=False, notes=False, discount=False, offer=False, shop_id=False,
                          price_with_tax=False, context={}):
        cost_journal = None
        account_analytic_id = None
        account_id = None
        product_obj = self.pool.get('product.product')
        res = super(purchase_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, categ_id, date_order,
                                                                 fiscal_position, date_planned, name, price_unit, notes, discount, offer, shop_id,
                                                                 price_with_tax, context)
        if context:
            cost_journal = context.get('cost_journal', None)
            department_id = context.get('department_id', None)
        if cost_journal:
            res['value']['cost_journal'] = cost_journal
        if department_id:
            res['value']['department_id'] = department_id
        if product:
            product_id = product_obj.browse(cr, uid, product)
            if product_id:
                account_analytic_id = product_id.property_account_expense.analytic_account_id.id or False
                account_id = product_id.property_account_expense.id or False
        res['value']['account_analytic_id'] = account_analytic_id
        res['value']['account_id'] = account_id
        return res

purchase_order_line()


class purchase_order(osv.osv):
    _inherit = "purchase.order"
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = super(purchase_order, self)._amount_all(cr, uid, ids, field_name, arg, context=None) 
        return res
    
#     def _amount_all_perception(self, cr, uid, ids, name, args, context=None):
#         res = {}
#         amount_tax = 0.0
#         for order in self.browse(cr, uid, ids, context=context):
#             res[order.id] = 0.0
#             for line in order.order_line:
#                 for ab in line.taxes_id:
#                     if ab.tax_code_id.tax_type == 'perception':
#                         amount_tax += line.price_subtotal * ab.amount
#             res[order.id] = amount_tax
#         return res

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        dc = self.pool.get('decimal.precision').precision_get(cr, 1, 'Purchase Price')
        perc_value = 0.00
        res = super(purchase_order, self)._prepare_inv_line(cr, uid, account_id, order_line, context=None)
        if order_line.order_id.company_id.currency_id.id != order_line.order_id.currency_id.id:
            cd = order_line.order_id.company_id.currency_id.rate
        else:
            cd = 1.00
        if order_line.taxes_id:
                for tax_code in order_line.taxes_id:
                    if tax_code.ref_base_code_id.tax_type == 'perception':
                        perc_value += round(((order_line.product_qty*(order_line.final_price * cd))*tax_code.amount_variable), dc)
        else:
            perc_value = 0.00
        res.update({'wbs_phase': order_line.wbs_phase.id})
        res.update({'perception_value':perc_value})
        return res
    

    _columns = {'cronograma': fields.text('Cronograma de Fabricación'),
                'multas': fields.text('Multas'),
                'inspeccion': fields.text('Inspección'),
                'garantia': fields.text('Garantía'),
                'pay_term': fields.text('Términos de Pago'),
                'entrega': fields.text('Dirección de Entrega'),
                'amount_total_perception': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string="Percepción",
                                               store=True, multi="sums", help="The total amount"),
                'currency_id': fields.many2one('res.currency', 'Moneda')
                }
    
    _defaults={
              "currency_id": lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id,
              }

    def wkf_up_order(self, cr, uid, ids, context=None):
        todo = []
        xml_id = 'email_required_purchase'
        mod_obj = self.pool.get('ir.model.data')
        general_id = False
        analytic_obj = self.pool.get('account.analytic.journal')
        for po in self.browse(cr, uid, ids, context=context):
            if not po.cost_journal:
                general_ids = analytic_obj.search(cr,uid, [('type','=','general')])
                if general_ids:
                    general_id = analytic_obj.browse(cr,uid, general_ids[0])
            else:
                general_id = analytic_obj.browse(cr,uid, po.cost_journal.id)
            
            if general_id:
                if not general_id.purchase_sequence:
                    raise osv.except_osv(_('Error !'),
                                         _('You need define a Purchase Sequence in Analytic Journal.'))
                else:
                    if general_id.purchase_sequence:
                        purchase_sequence = general_id.purchase_sequence.id
                        if not po.name:                
                            name = self.pool.get('ir.sequence').next_by_id(cr, uid, purchase_sequence)
                        else:
                            name = po.name
                    else:
                        raise osv.except_osv(_('Error !'),
                                             _('You need define a Purchase Sequence in Analytic Journal.'))
            else:
                raise osv.except_osv(_('Error !'),
                                     _('You need define a Analytic Journal.'))

            if not po.order_line:
                raise osv.except_osv(_('Error !'),
                                     _('You cannot confirm a purchase order without any lines.'))
            if po.required_approval and uid != po.validator.id:
                state = 'wait'
                validator = po.validator.id
                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_purchase', xml_id)
                if not template_ids:
                    raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico'
                                                        ' para las Solicitudes de Compras.'))
                else:
                    template_id = template_ids[1]
                self._embed_url(cr, uid, ids, context=None)
                self.generate_email_approve(cr, uid, template_id, po.id, context)
            elif uid == po.validator.id:
                state = 'wait'
                validator = po.validator.id
            else:
                state = po.state
                validator = po.validator.id
            for id in ids:
                self.write(cr, uid, [id], {'state': state, 'validator': validator, 'name': name})
        return True
    
       
purchase_order()


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def get_prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
        vals_stock_picking = super(stock_picking, self).get_prepare_invoice_line(cr, uid, group, picking, move_line,
                                                                                 invoice_id, invoice_vals, context)
        vals_stock_picking['wbs_phase'] = move_line.purchase_line_id.wbs_phase.id
        return vals_stock_picking
    

stock_picking()


