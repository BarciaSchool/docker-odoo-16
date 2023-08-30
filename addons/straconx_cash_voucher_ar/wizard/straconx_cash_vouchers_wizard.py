# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons,  Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A
#    (<http://openerp.straconx.com > ). All Rights Reserved
#
##############################################################################
from osv import osv,  fields
from tools.translate import _
import netsvc
import time
import re
import decimal_precision as dp
from account_voucher import account_voucher


class straconx_cash_vouchers_wizard(osv.osv_memory):

    def get_shop_id(self, cr, uid, context=None):
        shop_id = {}
        if uid:
            cash = self.pool.get('account.bank.statement').search(cr, uid, [('user_id', '=', uid), ('state', '=', 'open')])
            if cash:
                shop_id = self.pool.get('account.bank.statement').browse(cr, uid, cash)[0].shop_id.id
            else:
                shop_id = False
        return shop_id

    _name = 'straconx.cash.vouchers.wizard'
    _inherit = 'account.payments'
    _columns = {'type_doc': fields.selection([('cash', 'Generar Vale de Caja'),
                                             ('invoice', 'Pago de Factura de Proveedor'),
                                             ('purchase_liquidation', 'Pago de Liquidación de Compras'),
                                             ('sale_note', 'Pago de Notas de Venta de Proveedores'),
                                             ('withhold', 'Devolución de Retención a Cliente')],
                                             'Tipo de Documento'),
                'approve':  fields.boolean('Approve',
                                           help='if TRUE create a payment line in PAID state also creates lines at the cash register,'
                                           '  the movement in accounting and her lines in VALID state .'
                                           'If FALSE only make the payment line in DRAFT state.'),
                'approve_account_entry': fields.boolean('Account Entry', help='if TRUE , approves the account entries'),
                'is_electronic': fields.boolean('¿Es un documento electrónico?', help='Indicar si el documento a ingresar es tiene autorización'
                                                ' electrónica'),
                'authorization_credit': fields.char('authorization', size=49, readonly=True, states={'draft': [('readonly', False)]}),
                'invoice_id':  fields.many2one('account.invoice', 'Factura',  help='Si es una devolución de retención:'
                                               ' la factura debe estar en estado pagada para proceder a la devolución por retención; '
                                               'Si es un Pago de Factura a Proveedor:  La factura debe estar en estado abierto para continuar'),
                'authorization_id': fields.many2one('sri.authorization',  'Authorization', help='La autorización de la factura ingresada'),
                'gen_withhold': fields.boolean('¿Generar Retención al Proveedor?', help='Indica si debe generarse una retención al proveedor'),
                'printer_id':  fields.many2one('printer.point', 'Punto de Emisión'),
                'name_withhold':  fields.char('Retención', size=17, readonly=True, states={'draft': [('readonly', False)]},
                                              help='Esta retención no puede ser electrónica'),
                'date_withhold':  fields.date('Fecha', readonly=True, states={'draft': [('readonly', False)]}),
                'auth_withhold_id': fields.many2one('sri.authorization',  'Autorización Retención', help='La autorización de la retención ingresada'),
                'wizard_line':  fields.one2many('straconx.cash.vouchers.wizard.line', 'wizard_id', 'Líneas de Vale'),
                'budgets': fields.boolean('¿Presupuesto Instalado?'),
                }

    _defaults = {'approve': True,
                 'approve_account_entry': True,
                 }

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, context=None):
        context = context or {}
        if not line_dr_ids:
            return {'value': {}}
        line_osv = self.pool.get('straconx.cash.vouchers.wizard.line')
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['amount'], context)
        total = 0.00
        for line in line_dr_ids:
            total += line.get('amount')
        return {'value': {'amount': total}}

    def default_get(self,  cr,  uid,  fields,  context=None):
        if context is None:
            context = {}
        objs = False
        active_model = context.get('active_model', 'account.bank.statement')
        if active_model != 'account.bank.statement':
            active_model = 'account.bank.statement'
            active_ids = False
            objs_search = self.pool.get(active_model).search(cr, uid, [('user_id', '=', uid), ('state', '=', 'open')])
            if objs_search:
                statement_id = self.pool.get('account.bank.statement').browse(cr, uid, objs_search[0])
                shop_id = statement_id.shop_id
        else:
            active_ids = context.get('active_ids', False)
            objs = self.pool.get(active_model).browse(cr, uid, active_ids)
        pcash = context.get('journal_type', False)
        mode = context.get('default_type', 'payment')
        shop_id = False
        res = {}

        budgets = False
        modules_obj = self.pool.get('ir.module.module')
        module_name = modules_obj.search(cr, uid, [('name', '=', 'straconx_budgets')], limit=1)
        if module_name:
            if modules_obj.browse(cr, uid, module_name[0]).state == 'installed':
                budgets = True

        if objs:
            if 'value' not in context.keys():
                for obj in objs:
                    statement_id = self.pool.get('account.bank.statement').browse(cr, uid, obj.id)
                    shop_id = statement_id.shop_id
        else:
            pool_account_bank_st = self.pool.get(active_model)
            if pcash:
                search_account_bank_st = pool_account_bank_st.search(cr, uid, [('user_id',  '=', uid), ('state', '=', 'open'),
                                                                               ('journal_id.type', '=', 'pcash')])
            else:
                search_account_bank_st = pool_account_bank_st.search(cr, uid, [('user_id',  '=', uid), ('state', '=', 'open'),
                                                                               ('journal_id.type', '=', 'moves')])

            if search_account_bank_st:
                if len(search_account_bank_st) > 1:
                    raise osv.except_osv(_('!Error!'),  _('Tiene más de una CAJA ABIERTA. Debe tener solo UNA abierta para continuar.'))
                else:
                    statement_id = pool_account_bank_st.browse(cr, uid, search_account_bank_st[-1])
                    shop_id = statement_id.shop_id
            else:
                if pcash:
                    raise osv.except_osv(_('!Error!'),  _('No tiene ninguna CAJA CHICA abierta. Cree una para continuar.'))
                else:
                    raise osv.except_osv(_('!Error!'),  _('No tiene ninguna CAJA GENERAL abierta. Cree una para continuar.'))

        if shop_id:
            if pcash:
                cr.execute('select payment_id from rel_shop_payment rsp left join payment_mode pm on pm.id = rsp.payment_id where shop_id = %s and'
                           ' pm.cash = True and pm.petty =True', [shop_id.id, ])
            else:
                cr.execute('select payment_id from rel_shop_payment rsp left join payment_mode pm on pm.id = rsp.payment_id where shop_id = %s and'
                           ' pm.cash = True and pm.default =True and (pm.petty =False or pm.petty is null)', [shop_id.id, ])
            paids = cr.fetchall()
            if len(paids) >= 1:
                mode_id = paids[0][0]
            else:
                if pcash:
                    raise osv.except_osv(_('!Aviso!'), _('No existe ningún modo de Pago predeterminado para CAJA CHICA.'
                                                         ' Solicite al área Financiera que cree una y/o añádalo a su Tienda para continuar.'))
                else:
                    raise osv.except_osv(_('!Aviso!'), _('No existe ningún modo de Pago predeterminado para CAJA GENERAL.'
                                                         'Solicite al área Financiera que cree una y/o añádalo a su Tienda para continuar.'))
            res['company_id'] = statement_id.company_id.id
            res['mode_id'] = mode_id
            res['shop_id'] = shop_id.id
            res['printer_id'] = statement_id.printer_id.id
            res['statement_id'] = statement_id.id
            res['state'] = 'draft'
            res['supervisor_id'] = shop_id.shop_manager.id
            res['user_id'] = uid
            res['type'] = mode
            res['approve'] = True
            res['approve_account_entry'] = True
            res['type_doc'] = False
            res['budgets'] = budgets
        return res

    def onchange_mode_id(self,  cr,  uid,  ids,  shop_id,  statement_id,  mode_id,  context=None):
        result = {}
        paid_ids = []
        if shop_id and statement_id:
            statement_id = self.pool.get('account.bank.statement').browse(cr, uid, statement_id)
            shop_id = statement_id.shop_id

            if statement_id.journal_id and shop_id:
                if statement_id.journal_id.type == 'pcash':
                    cr.execute('select payment_id from rel_shop_payment rsp left join payment_mode pm on pm.id = rsp.payment_id where shop_id = %s'
                               ' and pm.cash = True and pm.petty =True', [shop_id.id, ])
                else:
                    cr.execute('select payment_id from rel_shop_payment rsp left join payment_mode pm on pm.id = rsp.payment_id where shop_id = %s'
                               ' and pm.cash = True and pm.default =True and (pm.petty =False or pm.petty is null)', [shop_id.id, ])
                paids = cr.fetchall()
                if len(paids) >= 1:
                    for paid in paids:
                        paid_ids.append(paid[0])
                    if mode_id not in paid_ids:
                        mode_id = paids[0][0]
                    else:
                        mode_id = mode_id
                    result['mode_id'] = mode_id
                else:
                    result['mode_id'] = False
        return {'value': result}

    def onchange_type_doc(self,  cr,  uid,  ids,  type_doc, name, is_electronic, gen_withhold, date, partner_id, shop_id,
                          printer_id, name_withhold, date_withhold, context=None):
        result = {}
        warning = {}
        invoice_obj = self.pool.get('account.invoice')
        shop_obj = self.pool.get('sale.shop')
        warning = {}
        invoice_id = False
        tp = partner_id
        tj = 'purchase'
        number = None
        if context:
            new_data = context.get('new_data', False)
            if new_data:
                result['invoice_id'] = None
                result['total_base_00'] = 0.00
                result['total_base_12'] = 0.00
                result['amount'] = 0.00
                result['name'] = None
                return {'value': result,  'warning': warning}
        if type_doc == 'purchase_liquidation':
            tj = 'purchase_liquidation'
            tp = shop_obj.browse(cr, uid, shop_id).company_id.id
        elif type_doc == 'sale_note':
            tj = 'sale_note'
        journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', tj)])
        journal_with = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'withhold')])
        if journal_id:
            journal_id = journal_id[0]
        else:
            raise osv.except_osv(_('!Aviso!'),  _('No existe Diarios del tipo Compra creados. Por favor,  cree uno.'))
        addr = self.pool.get('res.partner').address_get(cr,  uid,  [partner_id],  ['default'])
        if addr:
            address_id = addr['default']

        if type_doc and type_doc in ('invoice', 'purchase_liquidation', 'sale_note'):
            if name:
                numero = name.split('-')
                if not date:
                    date = time.strftime('%Y-%m-%d')
                number = name 
        if name:
            old_invoice = False
            if type_doc in ('invoice', 'purchase_liquidation'):
                if is_electronic:
                    old_invoice = invoice_obj.search(cr, uid, [('invoice_number_in', '=', name), ('partner_id', '=', partner_id),
                                                               ('state', 'in', ('open', 'paid'))])
                elif number:
                    old_invoice = invoice_obj.search(cr, uid, [('invoice_number_in', '=', number),
                                                               ('state', 'in', ('open', 'paid'))])
                if old_invoice:
                    invoice_id = invoice_obj.browse(cr, uid, old_invoice[0])
                    result['name'] = number or name
                    result['invoice_id'] = invoice_id.id
                    result['total_base_00'] = invoice_id.amount_base_vat_00
                    result['total_base_12'] = invoice_id.amount_base_vat_12
                    result['amount'] = invoice_id.amount_total          
        result.update({'warning': warning})
        return {'value':  result,  'warning': warning}

    def onchange_ret(self, cr, uid, ids, gen_ret, context=None):
        result = {}
        if gen_ret:
            result['name_withhold'] = None
            result['date_withhold'] = False
            result['auth_withhold_id'] = False
            result['printer_id'] = False
        return {'value': result}

    def action_save_and_process(self, cr, uid, ids, context=None):
        if(not context):
            context = {}
        vals = {}
        paid = False
        il = []
        tax = []
        approve_account_entry = False
        rec_list_ids = []
        amount_voucher = False
        motive = False
        inv_id = False
        generate_withhold = False
        move_inv = False
        move_wth = False
        partner_id = False
        dc = self.pool.get('decimal.precision').precision_get(cr,  1,  'Purchase Price')
        invoice_obj = self.pool.get('account.invoice')
        #withhold_obj = self.pool.get('account.withhold')
        #withhold_line_obj = self.pool.get('account.withhold.line')
        move_line_pool = self.pool.get('account.move.line')
        wf_service = netsvc.LocalService('workflow')
        pool_account_payments = self.pool.get('account.payments')
        inv_line_obj = self.pool.get('account.invoice.line')
        browse_cash_voucher = self.browse(cr, uid, ids, context)
        inv_obj = False
        for obj in browse_cash_voucher:
            if obj.type_doc in ('invoice', 'purchase_liquidation', 'sale_note'):
                total_base_00 = 0.00
                total_base_12 = 0.00
                if obj.name:
                    old_invoice = self.pool.get('account.invoice').search(cr, uid, [('invoice_number_in', '=', obj.name),
                                                                                    ('partner_id', '=', obj.partner_id.id),
                                                                                    ('state', '=', 'open')])
                    if old_invoice:
                        for inv_st in old_invoice:
                            inv_obj = self.pool.get('account.invoice').browse(cr,  uid,  inv_st,  context=context)
                            if inv_obj.state == 'open':
                                inv_obj = self.pool.get('account.invoice').browse(cr,  uid,  old_invoice[0],  context=context)
                                amount = inv_obj.residual
                                obj.write({'amount': amount})
                    if inv_obj and inv_obj.state == 'paid':
                        raise osv.except_osv(_('!Aviso!'),  _('El número de Factura ingresado se encuentra en estado Pagado. Por favor,  revisar'))
                    elif not old_invoice or inv_obj.state == 'cancel':
                        user_id = obj.user_id
                        partner_id = obj.partner_id
                        if partner_id.type_vat != 'ruc' and obj.type in ('invoice', 'sale_note'):
                            raise osv.except_osv(_('!Aviso!'),  _('Solo se puede crear una factura de proveedores para las Empresas que tengan RUC. '
                                                                  'Por favor,  revisar el proveedor seleccionado.'))
                        addr = self.pool.get('res.partner').address_get(cr,  uid,  [partner_id.id],  ['default'])
                        journal_obj = self.pool.get('account.journal')
                        number_invoice = obj.name
                        authorization = obj.authorization_credit
                        company = obj.company_id
                        if not partner_id:
                            raise osv.except_osv(_('Invalid action !'),  _('Debe seleccionar una Empresa!'))

                        for line in obj.wizard_line:
                            tax = []
                            if line.total_base_12 > 0.00:
                                total_base_12 += line.total_base_12
                                account_id = line.account_expense_cash_id.account_id.id
                                if line.account_expense_cash_id:
                                    product_id = line.account_expense_cash_id.product_id.id or False
                                    taxes_id = line.account_expense_cash_id.product_id.supplier_taxes_id or line.account_expense_cash_id.tax_line
                                else:
                                    product_id = False
                                    if line.company_id.property_tax_vat_product_12:
                                        taxes_id = [line.company_id.property_tax_vat_product_12, line.company_id.property_tax_withhold_product,
                                                    line.company_id.property_tax_withhold_vat_product]
                                    else:
                                        raise osv.except_osv(_('¡Acción Inválida!'),
                                                             _('Por favor, defina las cuentas de impuestos predeterminados desde la pantalla de'
                                                               ' configuración de compañías'))
                                price_iva = 0.00
                                iva_value = 0.00
                                perception_value = 0.00
                                price_product = 0.00
                                if taxes_id:
                                    for t in taxes_id:
                                        if t.tax_type == 'vat' and t.amount != 0.00:
                                            price_product = line.total_base_12
                                            price_iva = round(line.total_base_12 * (1 + t.amount), 6)
                                            iva_value = round((line.total_base_12 * t.amount), 6)
                                            tax.append(t.id)
                                        elif t.tax_type == 'perception':
                                            perception_value += round((line.total_base_12 * t.amount), 6)
                                            tax.append(t.id)
                                else:
                                    raise osv.except_osv(_('¡Acción Inválida!'),
                                                         _('Debe agregar por lo menos un tipo de Impuestos para las compras (IVA 0%,'
                                                           ' 12% o retención código 332'))
                                line_invoice = {
                                    'name': line.wizard_id.motive,
                                    'account_id': account_id,
                                    'price_unit': price_product,
                                    'price_iva': price_iva,
                                    'iva_value': iva_value,
                                    'perception_value': perception_value,
                                    'price_product': price_product,
                                    'price_subtotal': price_product,
                                    'quantity': 1,
                                    'product_id': product_id,
                                    'discount': 0.0,
                                    'offer':  0.0,
                                    'invoice_line_tax_id': [(6, 0, [x for x in tax])],
                                    'account_analytic_id': line.analytic_account_id.id or False,
                                    'department_id': line.department_id.id or False,
                                    'cost_journal': line.cost_journal.id or False,
                                    'type': 'in_invoice'
                                    }
                                inv_line_id = inv_line_obj.create(cr, uid, line_invoice, context=context)
                                il.append(inv_line_id)
                            tax = []
                            if line.total_base_00 > 0.00:
                                total_base_00 += line.total_base_00
                                account_id = line.account_expense_cash_id.account_id.id
                                if line.account_expense_cash_id.product_id:
                                    product_id = line.account_expense_cash_id.product_id.id
                                    taxes_id = line.account_expense_cash_id.product_id.supplier_taxes_id or line.account_expense_cash_id.tax_line
                                else:
                                    product_id = False
                                    taxes_id = [line.wizard_id.company_id.property_tax_vat_product_00]
                                    for tax_id in line.account_expense_cash_id.tax_line:
                                        if tax_id.tax_type not in ('vat', 'withhold_vat'):
                                            taxes_id.append(tax_id)
                                price_iva = line.total_base_00 or 0.00
                                iva_value = 0.00
                                perception_value = 0.00
                                if taxes_id:
                                    for t in taxes_id:
                                        if t.tax_type == 'vat' and t.amount == 0.00:
                                            price_product = line.total_base_00
                                            price_iva = round(line.total_base_00 * (1 + t.amount), 6)
                                            iva_value = 0.00
                                            tax.append(t.id)
                                        elif t.tax_type == 'withhold':
                                            tax.append(t.id)
                                line_invoice = {
                                    'name': line.wizard_id.motive,
                                    'account_id': account_id,
                                    'price_unit': price_product,
                                    'price_iva': price_iva,
                                    'iva_value': 0.00,
                                    'perception_value': 0.00,
                                    'price_product': price_product,
                                    'price_subtotal': price_product,
                                    'quantity': 1,
                                    'product_id': product_id,
                                    'discount': 0.0,
                                    'offer':  0.0,
                                    'invoice_line_tax_id': [(6, 0, [x for x in tax])],
                                    'account_analytic_id': line.analytic_account_id.id or False,
                                    'department_id': line.department_id.id or False,
                                    'cost_journal': line.cost_journal.id or False,
                                    'type': 'in_invoice'
                                    }
                                inv_line_id = inv_line_obj.create(cr, uid, line_invoice, context=context)
                                il.append(inv_line_id)

                        pay_acc_id = obj.company_id.partner_id.property_account_payable.id
                        if not pay_acc_id:
                            raise osv.except_osv(_('¡Acción Inválida!'),  _('No existe una cuenta contable para Proveedores por Pagar'))
                        if not partner_id.property_account_position:
                            raise osv.except_osv(_('¡Acción Inválida!'),
                                                 _('Debe definir una posición fiscal para el Proveedor'))
                        else:
                            fpos = partner_id.property_account_position
                        pay_acc_id = self.pool.get('account.fiscal.position').map_account(cr,  uid,  fpos,  pay_acc_id)
                        if obj.type_doc == 'invoice':
                            tj = 'purchase'
                            td = 'FACTURA'
                        elif obj.type_doc == 'purchase_liquidation':
                            tj = 'purchase_liquidation'
                            td = 'LIQUIDACION DE COMPRAS'
                        elif obj.type_doc == 'sale_note':
                            tj = 'sale_note'
                            td = 'NOTA DE VENTA'
                        journal_ids = journal_obj.search(cr,  uid,  [('type',  '=', tj), ('company_id',  '=',  company.id)],  limit=1)
                        if not journal_ids:
                            raise osv.except_osv(_('Error !'),
                                                 _('There is no purchase journal defined for this company: %s (id:%d)') %
                                                 (company.name, company.id))
                        source = 'local'
                        if td == 'FACTURA':
                            tax_documents = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '01')])
                        elif td == 'LIQUIDACION DE COMPRAS':
                            tax_documents = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '03')])
                        elif td == 'NOTA DE VENTA':
                            tax_documents = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '02')])
        #                     if obj.is_electronic:
                        authorization_purchase = obj.authorization_id.id
                        authorization = obj.authorization_credit
                        inv = {'shop_id': user_id.shop_id.id,
                               'name': obj.name,
                               'reference': 'PAGO DE ' + td + ' #' + obj.name + ' POR CAJA CHICA',
                               'description': obj.motive,
                               'account_id': pay_acc_id,
                               'type': 'in_invoice',
                               'partner_id': partner_id.id,
                               'currency_id': company.currency_id.id,
                               'address_invoice_id': addr['default'],
                               'address_contact_id': addr['default'],
                               'country_id': company.country_id.id,
                               'journal_id': len(journal_ids) and journal_ids[0],
                               'origin': obj.motive,
                               'invoice_line': [(6,  0,  il)],
                               'fiscal_position': fpos.id,
                               'payment_term': partner_id.property_payment_term and partner_id.property_payment_term.id,
                               'company_id': company.id,
                               'tpurchase': 'expense',
                               'origin_transaction': source,
                               'date_invoice': obj.payment_date,
                               'date_due': obj.payment_date,
                               'document_type': tax_documents and tax_documents[0],
                               'segmento_id': partner_id.segmento_id.id,
                               'electronic': obj.is_electronic,
                               'number': number_invoice,
                               'invoice_number': number_invoice,
                               'invoice_number_in': number_invoice,
                               'invoice_number_out': number_invoice,
                               'internal_number': number_invoice,
                               'authorization': authorization,
                               'authorization_purchase': authorization_purchase,
                               'migrate': True
                               }
                        context['type'] = 'in_invoice'

                        motive = obj.motive
                        generate_withhold = False
                        inv_id = invoice_obj.create(cr,  uid,  inv,  context)
                        invoice_obj.button_reset_taxes(cr,  uid,  [inv_id],  context=context)
                        invoice_obj.button_compute(cr,  uid,  [inv_id],  context=context,  set_total=True)
                        wf_service.trg_validate(uid,  'account.invoice',  inv_id,  'invoice_open',  cr)
                        inv_obj = invoice_obj.browse(cr,  uid,  inv_id,  context=context)
                if inv_obj:
                    if not inv_id:
                        inv_id = inv_obj.id
                    amount_voucher = inv_obj.residual
                    for move_line in inv_obj.move_id.line_id:
                        if move_line.credit > 0.00:
                            move_inv = move_line.id
                            context.update({'move_inv': move_inv, 'invoiced': True})
            account_expense_cash_id = False
            if not amount_voucher:
                for data in obj.wizard_line:
                    amount_voucher += data.amount
            if obj.wizard_line[0].account_expense_cash_id:
                account_expense_cash_id = obj.wizard_line[0].account_expense_cash_id.id
            if not motive:
                motive = obj.motive
            if obj.is_cash_receipts:
                vals['partner_id'] = obj.company_id.partner_id.id
            else:
                vals['partner_id'] = obj.partner_id.id
            vals['company_id'] = obj.company_id.id
            vals['is_cash_voucher'] = True
            vals['user_id'] = obj.user_id.id
            vals['mode_id'] = obj.mode_id.id
            vals['type'] = obj.type
            vals['amount'] = amount_voucher
            vals['motive'] = motive
            vals['name'] = obj.name
            vals['authorization_credit'] = obj.authorization_credit
            vals['payment_date'] = obj.payment_date
            vals['state'] = obj.state
            vals['invoice_id'] = inv_id
            vals['shop_id'] = obj.statement_id.shop_id.id
            vals['account_expense_cash_id'] = account_expense_cash_id  # cuenta de credito para contrapartida
            vals['statement_id'] = obj.statement_id.id
            vals['withhold'] = generate_withhold
            paid = obj.approve
            approve_account_entry = obj.approve_account_entry
            account_payment_id = pool_account_payments.create(cr, uid, vals, context)
            if obj.wizard_line:
                context['lines'] = True
        if(paid and account_payment_id):
            if(approve_account_entry):
                context['approve_account_entry'] = approve_account_entry
            move_payment_id = pool_account_payments.action_change_state_paid(cr, uid, [account_payment_id], context)
            statement_line_id = context.get("statement_line_id", False)
            obj.write({'statement_line_id':statement_line_id})
            move_id = self.pool.get('account.move').browse(cr, uid, move_payment_id)
            for move_line in move_id.line_id:
                if move_line.debit > 0.00:
                    move_payment = move_line.id
            if move_inv:
                rec_ids = [move_payment,  move_inv]
                rec_list_ids.append(rec_ids)
            if move_wth:
                rec_ids = [move_payment,  move_wth]
                rec_list_ids.append(rec_ids)

        for rec_ids in rec_list_ids:
            if len(rec_ids) >= 2:
                move_line_pool.reconcile_partial(cr,  uid,  rec_ids)
        p_id = self.pool.get('account.bank.statement').browse(cr, uid, obj.statement_id.id)
        p_id.refresh()
        return {'type': 'ir.actions.act_window_close'}

straconx_cash_vouchers_wizard()


class straconx_cash_vouchers_wizard_line(osv.osv_memory):

    _name = 'straconx.cash.vouchers.wizard.line'
    _columns = {'wizard_id': fields.many2one('straconx.cash.vouchers.wizard', 'Asistente'),
                'type_doc': fields.related('wizard_id', 'type_doc', type='selection',
                                           selection=[('cash', 'Generar Vale de Caja'),
                                                      ('invoice', 'Pago de Factura de Proveedor'),
                                                      ('purchase_liquidation', 'Pago de Liquidación de Compras'),
                                                      ('sale_note', 'Pago de Notas de Venta de Proveedores'),
                                                      ('withhold', 'Devolución de Retención a Cliente')],
                                           string='Tipo de Documento'),
                'account_expense_cash_id': fields.many2one('account.expense.cash', 'Expense'),
                'total_base_12': fields.float('BASE 12%'),
                'total_base_00': fields.float('BASE 0%'),
                'withhold_rent': fields.float('Retención en al Fuente'),
                'withhold_vat': fields.float('Retención de IVA'),
                'amount': fields.float('Amount'),
                'department_id': fields.many2one('hr.department', 'Department'),
                'cost_journal': fields.many2one('account.analytic.journal', 'Cost Journal'),
                'budgets': fields.boolean('¿Presupuesto Instalado?'),
                'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account')
                }

    def default_get(self,  cr,  uid,  fields,  context=None):
        res = {}
        if context is None:
            context = {}
        type_doc = context.get('type_doc', False)
        budgets = context.get('budgets', False)
        if not type_doc:
            raise osv.except_osv('Error!',  _('Por favor, elija un tipo de documento antes de continuar'))
        res['type_doc'] = type_doc
        res['budgets'] = budgets
        return res

    def onchange_account(self, cr, uid, ids, budgets, account_expense_cash_id, context=None):
        result = {}
        if budgets:
            acc_cash = self.pool.get('account.expense.cash').browse(cr, uid, account_expense_cash_id).account_id
            if acc_cash and acc_cash.type == 'other':
                result['analytic_account_id'] = acc_cash.analytic_account_id.id
                result['budgets'] = True
            else:
                result['budgets'] = False
        return {'value': result}

    def onchange_amount(self, cr, uid, ids, type_doc, amount, total_base_12, total_base_00, withhold_rent, withhold_vat, context=None):
        result = {}
        amount_total = 0.00
        if type_doc:
            if type_doc == 'cash':
                amount_total = amount
            elif type_doc == 'withhold':
                amount_total = withhold_rent + withhold_vat
            else:
                amount_total = total_base_12 + total_base_00
            result['amount'] = amount_total
        return {'value': result}

straconx_cash_vouchers_wizard_line()


class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns = {'vouchers_wizard_ids': fields.one2many('straconx.cash.vouchers.wizard',  'statement_id',
                                                       'Vales de Caja', states={'confirm': [('readonly', True)]})}

account_bank_statement()

class account_payments(osv.osv):
    _inherit = 'account.payments'
    _columns = {
                'invoice_id': fields.many2one('account.invoice', 'Asistente'),
                }

account_bank_statement()