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

import time
from datetime import datetime
from dateutil import relativedelta
import base64
import StringIO
from time import strftime
from string import upper
from string import join
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp


class hr_payslip_run(osv.osv):
    _inherit = 'hr.payslip.run'

    def _calculate_total(self, cr, uid, ids, name, args, context):
        if not ids:
            return {}
        result = {}
        bank_obj = self.pool.get('res.partner.bank')
        for payslip in self.browse(cr, uid, ids, context=context):
            result[payslip.id] = {'total': 0,
                                  'total_bank': 0,
                                  }
            for line in payslip.slip_ids:
                bank_id = bank_obj.search(cr, uid, [('partner_id', '=', line.employee_id.partner_id.id), ('default_bank', '=', True)])
                result[payslip.id]['total'] += line.total_payslip_lines
                if bank_id:
                    result[payslip.id]['total_bank'] += line.total_payslip_lines
        return result

    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}

        journal = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'discount_employee')])

        return journal and journal[0] or None

    _columns = {'reference': fields.many2one('hr.period', 'Slip Period', readonly=True, states={'draft': [('readonly', False)]}),
                'days': fields.float('Work Days', digits=(16, 2), readonly=True, states={'draft': [('readonly', False)]}),
                'data': fields.binary('File', readonly=True),
                'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
                'total': fields.function(_calculate_total, method=True, type='float', string='Total of Payslip',
                                         digits_compute = dp.get_precision('Payroll'), multi='total', store=True),
                'total_bank': fields.function(_calculate_total, method=True, type='float', string='Total of Payslip of Bank',
                                              digits_compute=dp.get_precision('Payroll'), multi='total_bank', store=True),
                'name': fields.char('Name', size=64, required=False, readonly=True,
                                    states={'draft': [('readonly', False)]}),
                'company_id': fields.many2one('res.company', 'Company', required=True,
                                              readonly=True, states={'draft': [('readonly', False)]}),
                'em': fields.boolean('End Month'),
                'payment': fields.boolean('pagos', required=False),
                'moves_ids':fields.one2many('account.move', 'pays_run_id', 'Movimientos', required=False),
                'debit_note_ids':fields.one2many('account.debit.note', 'payslip_run_id', 'Egresos', required=False),
                'mode_id':fields.many2one('payment.mode', 'Modo de Pago', required=False), 
                }

    _rec_name = 'reference'
    _order = 'date_end desc'

    _defaults = {'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.payslip.run', context=c),
                 'journal_id': _get_journal,
                 'em': False
                 }

    _sql_constraints = [
        ('reference_uniq', 'unique (reference,state,company_id)',
            'Slip period must be unique. Please check !'),
    ]

    def onchange_journal(self, cr, uid, ids, company_id=False, context=None):
        if context is None:
            context = {}
        if company_id:
            company_id = company_id
        else:
            raise osv.except_osv(_('Need a company!'), _('You must defined a company for this payslip'))
            company_id = False
        res = {}

        journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id', '=', company_id), ('type', '=', 'discount_employee')])
        if not journal_ids:
            raise osv.except_osv(_('Invalid action!'), _('You must defined a journal by discount of employee'))
        else:
            journal_id = journal_ids[0]

        res['journal_id'] = journal_id
        return {'value': res}

    def onchange_days_pay_id(self, cr, uid, ids, period_payment, context=None):
        days = 0.00
        date_from = False
        date_to = False
        period_obj = self.pool.get('hr.period')
        if context is None:
            context = {}
        res = {}

        if period_payment:
            date_from = period_obj.browse(cr, uid, period_payment).date_start
            date_to = period_obj.browse(cr, uid, period_payment).date_stop
            payment_id = period_obj.search(cr, uid, [('id', '=', period_payment)])
            for payment in period_obj.browse(cr, uid, payment_id):
                payments = payment.payment
        else:
            return None
        if not date_from and date_to:
            raise osv.except_osv(_('Error'), _('Need a generate hr payment periods for fiscal year.'))
        if date_from and date_to:
            if date_from > date_to:
                raise osv.except_osv(_('Error'), _('Date from is greater then Date to'))
            else:
                day_from = datetime.strptime(date_from, "%Y-%m-%d")
                day_to = datetime.strptime(date_to, "%Y-%m-%d")
                days = (day_to - day_from).days + 1

                if days >= 31:
                    days = 30
                elif str(day_to)[5:7] == '02':
                    if str(day_to)[8:10] in ('28', '29') and str(day_from)[8:10] in ('01') and days in (28, 29):
                        days = 30
                    elif str(day_to)[8:10] in ('28', '29') and str(day_from)[8:10] in ('01', '15') and days == 14:
                        days = 15
                    else:
                        days = (day_to - day_from).days + 1
                else:
                    days = days
                if str(day_from)[8:10] == '01':
                    em = True
                elif str(day_from)[8:10] == '16':
                    em = False
                else:
                    raise osv.except_osv(_('Error'), _('Only accepts 01 or 16 in payslip days'))
            res['date_start'] = date_from
            res['date_end'] = date_to
            res['days'] = days
            res['em'] = em
            res['payment'] = payments
        return {'value': res}

    def get_employee_ids(self, cr, uid, ids, context=None):
        pays_run = self.browse(cr, uid, ids[0])
        contract_object = self.pool.get('hr.contract')
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        credit_note = False
        slip_ids = []
        if pays_run.company_id and pays_run.reference:
            company_id = pays_run.company_id.id
            period_payment = pays_run.reference.id
        if pays_run.date_start and pays_run.date_end:
            from_date = pays_run.date_start
            to_date = pays_run.date_end
            period_id = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', from_date), ('date_stop', '>=', to_date),
                                                                         ('company_id', '=', company_id)])[0]
            if not period_id:
                raise osv.except_osv(_('Need a account period!'), _('You must defined a account period for this payslip'))
        else:
            raise osv.except_osv(_('Invalid action!'), _('you must defined dates from calc wage'))

        journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id', '=', company_id), ('type', '=', 'discount_employee')])
        if not journal_ids:
            raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by payslip'))
        else:
            journal_id = journal_ids[0]
        employee_ids = emp_pool.search(cr, uid, [('company_id', '=', company_id), ('unemployee', '=', False)])
        if employee_ids:
            for empl_id in employee_ids:
                emp = emp_pool.browse(cr, uid, empl_id, context=context)
                cont_active = contract_object.search(cr, uid, [('employee_id', '=', emp.id), ('contract_active', '=', True)])
                if cont_active:
                    cont_date = contract_object.browse(cr, uid, cont_active[0]).date_start
                    if cont_date and cont_date <= to_date:
                        slip_ant_ids = slip_pool.search(cr, uid, [('payslip_run_id', '=', ids[0]), ('employee_id', '=', emp.id)])
                        if slip_ant_ids:
                            continue
                        slip_data = slip_pool.onchange_employee_id(cr, uid, [], emp.id, emp.contract_id.id, period_payment, company_id,
                                                                   period_id, context=context)
                        datos = slip_pool.onchange_days_id(cr, uid, [], period_payment, emp.id, emp.contract_id.id, company_id, period_id,
                                                           context=context)
                        if emp.department_id.area_id:
                            area = emp.department_id.area_id.id
                        else:
                            raise osv.except_osv(_('¡Acción Inválida!'),
                                                 _('El empleado %s no tiene asignado un departamento o el area por favor revisar') % (emp.name))
                        res = {
                            'period_payment': period_payment,
                            'employee_id': emp.id,
                            'name': slip_data['value'].get('name', False),
                            'company_id': slip_data['value'].get('company_id', False),
                            'struct_id': slip_data['value'].get('struct_id', False),
                            'contract_id': slip_data['value'].get('contract_id', False),
                            'journal_id': journal_id,
                            'payslip_run_id': ids[0],
                            'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                            'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
                            'discount_lines_ids': [(0, 0, x) for x in slip_data['value'].get('discount_lines_ids', False)],
                            'leaves_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('leaves_days_line_ids', False)],
                            'date_from': from_date,
                            'date_to': to_date,
                            'period_id': period_id,
                            'credit_note': credit_note,
                            'area_id': area,
                            'wk_days': datos['value'].get('wk_days', 0)
                        }
                        slip_ids.append(slip_pool.create(cr, uid, res, context=context))
                else:
                    continue
        if slip_ids:
            slip_pool.compute_sheet(cr, uid, slip_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        unlink_ids = []
        payslip_obj = self.pool.get('hr.payslip')
        payslip_run_id = ids[0]
        if payslip_run_id:
            payslip_ids = payslip_obj.search(cr, uid, [('payslip_run_id', '=', payslip_run_id)])
        if payslip_ids:
            for p in payslip_ids:
                datas = payslip_obj.browse(cr, uid, p)
                if datas.state == 'draft':
                    unlink_ids.append(datas.id)
                else:
                    raise osv.except_osv(_('Invalid action !'), _('Cannot delete payslip(s) that are done state !'))
        if unlink_ids:
            payslip_obj.unlink(cr, uid, unlink_ids, context=context)
        osv.osv.unlink(self, cr, uid, ids, context=context)
        return True

    def create_move_of_document(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        rule_obj = self.pool.get('hr.salary.rule')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        bank_obj = self.pool.get('res.partner.bank')
        context['search_shop'] = True
        user = self.pool.get('res.users').browse(cr, uid,uid)
        for payslip in self.browse(cr, uid, ids, context):
            move_id = None
            if payslip.total_bank > 0:
                if not payslip.journal_id:
                    raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by payslip'))
                name = self.pool.get('ir.sequence').next_by_id(cr, uid, payslip.journal_id.sequence_id.id)
                if not payslip.reference:
                    ref = name
                else:
                    ref = payslip.reference.name
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', payslip.date_end),
                                                                              ('date_stop', '>=', payslip.date_end), ])
                rule_id = rule_obj.search(cr, uid, [('calculate_wage', '=', True), ('account_debit', '!=', None),
                                                    ('account_credit', '!=', None), ('company_id', '=', payslip.company_id.id)])
                if not rule_id:
                    raise osv.except_osv(_('Invalid action!'), _('you must defined a rule default of calculate wage'))
                account_debit = rule_obj.browse(cr, uid, rule_id[0], context).account_credit.id
                company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
                bank_id = bank_obj.search(cr, uid, [('partner_id', '=', company.partner_id.id), ('default_bank', '=', True)])
                if not bank_id:
                    raise osv.except_osv(_('Error'), _('You must have a account bank by default'))
                account_credit = bank_obj.browse(cr, uid, bank_id[0], context).account_id.id or False
                if not account_credit:
                    raise osv.except_osv(_('Error'), _('You must defined a account of payroll in the account bank by default'))
                move = {'name': name,
                        'journal_id': payslip.journal_id.id,
                        'date': payslip.date_end,
                        'partner_id':company.partner_id.id,
                        'ref': ref,
                        'details':ref,
                        'shop_id': user.shop_id.id,
                        'period_id': period_ids and period_ids[0] or None,
                        'pays_run_id':ids[0]
                        }
                move_id = move_pool.create(cr, uid, move, context=context)
                move_line_pool.create(cr, uid, {
                    'name': ref or '/',
                    'debit': payslip.total_bank,
                    'credit': 0,
                    'account_id': account_debit,
                    'move_id': move_id,
                    'journal_id': payslip.journal_id.id,
                    'period_id': period_ids and period_ids[0] or None,
                    'partner_id': company.partner_id.id,
                    'date': payslip.date_end,
                    }, context=context)
                move_line_pool.create(cr, uid, {
                    'name': ref or '/',
                    'debit': 0,
                    'credit': payslip.total_bank,
                    'account_id': account_credit,
                    'move_id': move_id,
                    'journal_id': payslip.journal_id.id,
                    'period_id': period_ids and period_ids[0] or None,
                    'partner_id': company.partner_id.id,
                    'date': payslip.date_end,
                    }, context=context)
            #self.write(cr, uid, [payslip.id], {'move_id': move_id})
        return True

    def close_payslip_run(self, cr, uid, ids, context=None):
        slip_ids = []
        bank_obj = self.pool.get('res.partner.bank')
        rule_obj = self.pool.get('hr.salary.rule')
        debit_note_pool=self.pool.get('account.debit.note')
        debit_note_line_pool=self.pool.get('account.debit.note.line')
        debit_note=[]
        for payslip in self.browse(cr, uid, ids, context):
            if not payslip.slip_ids:
                raise osv.except_osv(_('Error'), _('You can not close a Pay-slip Run without payroll generated'))
            for slip in payslip.slip_ids:
                if slip.state != 'done':
                    slip_ids.append(slip.id)
                    bank_id = bank_obj.search(cr, uid, [('partner_id', '=', slip.employee_id.partner_id.id), ('default_bank', '=', True)])
                    if not bank_id:
                        rule_id = rule_obj.search(cr, uid, [('calculate_wage', '=', True), ('account_debit', '!=', None),
                                                            ('account_credit', '!=', None), ('company_id', '=', payslip.company_id.id)])
                        if not rule_id:
                            raise osv.except_osv(_('Invalid action!'), _('you must defined a rule default of calculate wage'))
                        account_debit = rule_obj.browse(cr, uid, rule_id[0], context).account_credit.id
                        if slip.employee_id:
                            debit_note_id = debit_note_pool.create(cr, uid, {
                                                                 'partner_id':slip.employee_id.partner_id.id,
                                                                 'beneficiary':slip.employee_id.partner_id.name,
                                                                 'account_id':account_debit,
                                                                 'user_id':uid,
                                                                 'journal_id':slip.journal_id.id,
                                                                 'date':time.strftime('%Y-%m-%d'),
                                                                 'name': 'Nómina de '+slip.employee_id.name1+' '+slip.number,
                                                                 'reference': slip.period_payment.name,
                                                                 'payslip_run_id':payslip.id,
                                                                 'type':'advance_supplier',
                                                                 'total_amount': slip.total_payslip_lines
                                                                 
                                                                })
                            debit_note_line_pool.create(cr, uid,{
                                                                 'account_id':slip.journal_id.default_credit_account_id.id,
                                                                 'name':'Nómina de '+slip.employee_id.name1+' '+slip.number,
                                                                 'amount':slip.total_payslip_lines,
                                                                 'debit_note_id':debit_note_id,
                                                                 })
                            debit_note.append(debit_note_id)
#                    self.write(cr, uid, [discount.id], {'debit_note_id':debit_note_id})
        if slip_ids:
            self.pool.get('hr.payslip').process_sheet(cr, uid, slip_ids, context)
        reference = self.pool.get('hr.payslip.run').browse(cr, uid, ids[0], context).reference.id
        if reference:
            self.pool.get('hr.period').write(cr, uid, reference, {'state': 'done'})
        else:
            raise osv.except_osv(_('Error'), _('You can not generate payroll within period'))
        self.create_move_of_document(cr, uid, ids, context)
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)

    def draft_payslip_run(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        for payslip in self.browse(cr, uid, ids, context):
            if payslip.move_id:
                move_pool.button_cancel(cr, uid, [payslip.move_id.id], context={})
                move_pool.unlink(cr, uid, [payslip.move_id.id], context={})
        reference = self.pool.get('hr.payslip.run').browse(cr, uid, ids[0], context).reference.id
        if reference:
            self.pool.get('hr.period').write(cr, uid, reference, {'state': 'draft'})
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def draft_payslip_cancel_run(self, cr, uid, ids, context=None):
        payslip_ids = []
        for payslip in self.browse(cr, uid, ids, context):
            payslip.write({'state': 'draft'})
            payslip_ids = [slip.id for slip in payslip.slip_ids]
            if payslip.moves_ids:
                for move in payslip.moves_ids:
                    self.pool.get('account.move').button_cancel(cr, uid, [move.id], context={})
                    self.pool.get('account.move').write(cr, uid, [move.id], {'pays_run_id':False})
                    self.pool.get('account.move').unlink(cr, uid, [move.id], context={})
            if payslip.debit_note_ids:
                for debit in payslip.debit_note_ids:
                    if debit.state == 'draft':
                        if debit.move_id:
                            self.pool.get('account.move').write(cr, uid, [debit.move_id.id], {'pays_run_id':False})
                        self.pool.get('account.debit.note').unlink(cr,uid,[debit.id])
                    else:
                        raise osv.except_osv(_('Error'), _('No se puede cancelar una Nómina que tiene pagos asociados.'))         
        self.pool.get('hr.payslip').set_to_draft(cr, uid, payslip_ids, context=None)
        reference = self.pool.get('hr.payslip.run').browse(cr, uid, ids[0], context).reference.id
        if reference:
            self.pool.get('hr.period').write(cr, uid, reference, {'state': 'draft'})
        return True

    def formato_numero(self, valor):
        tup = valor.split('.')
        valor = ''.join(tup)
        if len(tup[1]) == 1:
            return valor+"0"
        return valor

    def create_payroll_file(self, cr, uid, ids, context):
        for payslip in self.browse(cr, uid, ids, context):
            buf = StringIO.StringIO()
            if not payslip.slip_ids:
                raise osv.except_osv(_('Error'), _('You can not generate the file without payroll'))
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            date = datetime.strptime(payslip.date_end, "%Y-%m-%d")
            if payslip.total_bank > 0:
                datenow = payslip.date_end
                datenow = datenow.split('-')
                bank_id = self.pool.get('res.partner.bank').search(cr, uid, [('partner_id', '=', company.partner_id.id), ('default_bank', '=', True)])
                if not bank_id:
                    raise osv.except_osv(_('Error'), _('You must have a account bank by default'))
                bank = self.pool.get('res.partner.bank').browse(cr, uid, bank_id[0], context)
                mount = self.formato_numero(str(round(payslip.total_bank, 2)))
                prueba = bank.acc_number + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1'
                space = 33 - len(prueba)
                prueba = bank.acc_number + '0' * space + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1' + '\n'
                space = 75 - len("D" + company.name + prueba)
                cadena = "D" + company.name + ' ' * space + prueba
                buf.write(upper(cadena))
                for slip in payslip.slip_ids:
                    if slip.employee_id.bank_account_id:
                        cadena = ''
                        employee = slip.employee_id
                        bank = slip.employee_id.bank_account_id
                        mount = self.formato_numero(str(round(slip.total_payslip_lines, 2)))
                        prueba = bank.acc_number + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1'
                        space = 33 - len(prueba)
                        prueba = bank.acc_number + '0' * space + mount + datenow[0][-2:] + datenow[1] + datenow[2] + 'N1' + '\n'
                        space = 75 - len("C" + employee.name + prueba)
                        cadena = "C" + employee.name + ' ' * space + prueba
                        buf.write(upper(cadena))
        out = base64.encodestring(buf.getvalue())
        buf.close()
        name = "%s_%s.TXT" % ("RP", date.strftime('%Y-%m-%d'))
        return self.write(cr, uid, ids, {'data': out, 'name': name}, context=context)
hr_payslip_run()

class account_move(osv.osv):
    _inherit = 'account.move'
    _columns = {
                'pays_run_id':fields.many2one('hr.payslip.run', 'Nomina', required=False) 
                    } 
    
account_move()

class account_debit_note(osv.osv):
    _inherit = 'account.debit.note'
    _columns = {
                'payslip_run_id':fields.many2one('hr.payslip.run', 'Nomina', required=False) 
                    } 
    def create_move(self, cr, uid, note, name, ref, context=None):
        res = super(account_debit_note, self).create_move(cr, uid, note, name, ref, context=context)
        self.pool.get('account.move').write(cr, uid, [res], {'pays_run_id': note.payslip_run_id.id or False})
        return res
account_debit_note()