# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons,  Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A
#    (<http: //openerp.straconx.com>). All Rights Reserved
#
##############################################################################

from osv import osv, fields
from tools.translate import _
import time


class res_user(osv.osv):

    _inherit = "res.users"
    _columns = {"maximun_cash_voucher_amount": fields.float("Maximun Cash Voucher", help="maximum amount for a cash voucher")}

    def onchange_maximun_cash_voucher_amount(self,  cr,  uid,  ids,  maximun_cash_voucher_amount,  is_cashier,  context=None):

        if(not is_cashier):
            return{"value": {"maximun_cash_voucher_amount": 0.00}}

        if(maximun_cash_voucher_amount < 0.00):
            return {"value": {"maximun_cash_voucher_amount": 0.00},
                    "warning": {"title": _("Validation Error !"),  "message": _("The field MAXIMUM CASH VOUCHER AMOUNT cannot be less than 0.00")}}

        pool_account_bank_st = self.pool.get("account.bank.statement")
        search_account_bank_st = pool_account_bank_st.search(cr, uid, [("user_id",  "=", ids[0]), ("state", "=", "open"),
                                                                       ("journal_id.type", "in", ['pcash', 'moves'])])
        if(search_account_bank_st):
            for account_bank_st_id in search_account_bank_st:
                browse_account_bank_st = pool_account_bank_st.browse(cr, uid, account_bank_st_id, context)
                type_name = browse_account_bank_st.journal_id.type == 'pcash' and _("PETTY CASH") or _("CASH REGISTER")
                total_expense = 0
                for statement_lines in browse_account_bank_st.line_ids:
                    if(statement_lines.payment_id.is_cash_voucher):
                        total_expense = total_expense+statement_lines.amount
                if(maximun_cash_voucher_amount < total_expense):
                    return {"value": {"maximun_cash_voucher_amount": total_expense},
                            "warning": {"title": _("Validation Error !"), "message":
                                        _("There vouchers paid cash at a " + type_name + ". The total value of the payments is " + str(total_expense)
                                          + ",  if you want to change this value should be greater than or equal to " + str(total_expense) + "")}}
        return {}
res_user()


class account_expense_cash(osv.osv):

    _name = "account.expense.cash"
    _columns = {'name': fields.char('Name', size=100),
                'account_id': fields.many2one("account.account",  "Credit Account",  required=False,  ondelete="cascade",
                                              domain=[("type", "!=", "view"), ("type",  "<>",  "closed")], select=2),
                'product_id': fields.many2one('product.product', 'Servicio'),
                'tax_line': fields.many2many('account.tax',  'rel_purchase_account_expense', 'expense_id',  'tax_id',  'Purchase Taxes',
                                             domain=[('parent_id',  '=',  False), ('type_tax_use', 'in', ['purchase', 'all'])]),
                }

account_expense_cash()


class account_input_cash(osv.osv):
    _name = "account.input.cash"
    _columns = {'name': fields.char('Name', size=100),
                'account_id': fields.many2one("account.account",  "Credit Account",  required=False, ondelete="cascade",
                                              domain=[("type", "<>", "view"),  ("type",  "<>",  "closed")],  select=2),
                'product_id': fields.many2one('product.product', 'Servicio'),
                'tax_line': fields.many2many('account.tax',  'rel_purchase_account_income',  'income_id',  'tax_id',  'Purchase Taxes',
                                             domain=[('parent_id',  '=',  False), ('type_tax_use', 'in', ['sale', 'all'])]),
                }

account_input_cash()


class account_payments(osv.osv):

    def get_shop_id(self, cr, uid, context=None):
        shop_id = {}
        if uid:
            cash = self.pool.get('account.bank.statement').search(cr, uid, [('user_id', '=', uid), ('state', '=', 'open'),
                                                                            ('journal_id.type', '=', 'pcash')])
            if cash:
                shop_id = self.pool.get('account.bank.statement').browse(cr, uid, cash)[0].shop_id.id
            else:
                shop_id = False
        return shop_id

    _inherit = "account.payments"
    _columns = {"is_cash_voucher": fields.boolean("Cash Voucher"),
                "is_cash_receipts": fields.boolean("Ingreso de Caja"),
                "account_expense_cash_id": fields.many2one("account.expense.cash",  "Expense"),
                "account_input_cash_id": fields.many2one("account.input.cash",  "Ingreso"),
                "statement_id": fields.many2one("account.bank.statement", "CashBox"),
                "supervisor_id": fields.many2one("res.users", "Supervisor")
                }

    def _check_doc(self,  cr,  uid,  ids, context=None):
        browse_payments = self.browse(cr, uid, ids, context)
        search_doc = []
        for payments in browse_payments:
            if payments.account_expense_cash_id:
                search_doc = self.search(cr, uid, [("id",  "<>", payments.id), ("company_id", "<>", payments.company_id.id), ("name",  "!=", False),
                                                   ("name",  "=", payments.name), ("is_cash_voucher", "=", True)])
            elif payments.account_input_cash_id:
                search_doc = self.search(cr, uid, [("id",  "<>", payments.id), ("company_id", "<>", payments.company_id.id), ("name",  "!=", False),
                                                   ("name",  "=", payments.name), ("is_cash_receipts", "=", True)])
            if(search_doc):
                return False
        return True

    _constraints = [(_check_doc, "Document number already exists",  ["name"])]

    def get_default_supervisor_id(self, cr, uid, context=None):
        manager = {}
        if uid:
            shop = self.pool.get('res.users').browse(cr, uid, uid).shop_id.id
            if shop:
                manager = self.pool.get('sale.shop').browse(cr, uid, shop).shop_manager.id
                if manager:
                    manager = manager
                else:
                    manager = False
        return manager

    def get_default_user_id(self, cr, uid, context=None):
        user = {}
        if uid:
            user = self.pool.get('res.users').browse(cr, uid, uid).id
        else:
            user = False
        return user

    def get_default_cash_id(self, cr, uid, context=None):
        box = {}
        if uid:
            cash = self.pool.get('account.bank.statement').search(cr, uid, [('user_id', '=', uid), ('state', '=', 'open'),
                                                                            ('journal_id.type', '=', 'pcash')])
            if cash:
                box = self.pool.get('account.bank.statement').browse(cr, uid, cash)[0].id
            else:
                box = False
        return box

    def get_default_mode_id(self, cr, uid, context=None):
        mode = {}
        if uid:
            shop = self.pool.get('res.users').browse(cr, uid, uid).shop_id.id
            cr.execute('select p.id from payment_mode p left join rel_shop_payment rl on rl.payment_id=p.id where p.petty=True and rl.shop_id=%s',
                       [shop, ])
            paids = cr.fetchall()
            paids = [i[0] for i in paids]
            if paids:
                mode = self.pool.get('payment.mode').browse(cr, uid, paids)[0].id
            else:
                mode = False
        return mode

    _defaults = {
        "user_id": get_default_user_id,
        "supervisor_id": get_default_supervisor_id,
        "payment_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "statement_id": get_default_cash_id,
        "mode_id": get_default_mode_id,
        "shop_id": get_shop_id,
        "amount": 0.00
        }

    def get_range_amount(self, cr, uid, user_id, statement_id, context=None):

        range_amount = {"minimun_cash_voucher_amount": 0.00, "maximun_cash_voucher_amount": 0.00}

        pool_users = self.pool.get("res.users")

        if(not user_id):
            range_amount["warning"] = {"title": _("Validation Error!"), "message": _("Please select an AUTHORIZED user")}
            return range_amount

        search_users = pool_users.search(cr, uid, [('id',  '=', uid), ('is_cashier', '=', True)])

        if(not search_users):
            range_amount["warning"] = {"title": _("Validation Error!"), "message": _("You aren't a CASHIER")}
            return range_amount

        if(not statement_id):
            range_amount["warning"] = {"title": _("Validation Error!"), "message": _("You should choose a PETTY CASH or a CASH REGISTER")}
            return range_amount

        browse_users = pool_users.browse(cr, uid, search_users, context)
        if(browse_users):
            pool_account_bank_st = self.pool.get("account.bank.statement")
            for user in browse_users:
                if(user.maximun_cash_voucher_amount):
                    statement = pool_account_bank_st.browse(cr, uid, statement_id, context)
                    if(not statement.balance_end):
                        type_name = statement.journal_id.type == 'pcash' and _("PETTY CASH") or _("CASH REGISTER")
                        range_amount["warning"] = {"title": _("Validation Error!"), "message": _("The "+type_name+" has not CASH")}
                        return range_amount
                    maximun_cash_voucher_amount = statement.balance_end
                    if(statement.journal_id.type == 'moves'):
                        total_expense = 0
                        for statement_lines in statement.line_ids:
                            if(statement_lines.payment_id.is_cash_voucher):
                                total_expense = total_expense+statement_lines.amount
                        maximun_cash_voucher_amount = (user.maximun_cash_voucher_amount-total_expense)
                        if(maximun_cash_voucher_amount <= 0):
                            range_amount["maximun_cash_voucher_amount"] = 0
                            range_amount["warning"] = {"title": _("¡Aviso!"), "message":
                                                       _("La Caja Registradora no tiene efectivo para realizar pagos")}
                            return range_amount
                        else:
                            if(maximun_cash_voucher_amount > statement.balance_end):
                                maximun_cash_voucher_amount = statement.balance_end
                                range_amount["warning"] = {"title": _("¡Aviso!"), "message":
                                                           _("La Caja Registradora tiene solo " + str(statement.balance_end) + " en efectivo")}
                    range_amount["minimun_cash_voucher_amount"] = 0.00
                    range_amount["maximun_cash_voucher_amount"] = maximun_cash_voucher_amount
                    return range_amount
                else:
                    range_amount["warning"] = {"title": _("¡Aviso!"), "message":
                                               _("Usted es un cajero,  pero no han definido el valor que debe tener en caja")}

        return range_amount

    def onchange_user_id(self, cr, uid, ids, user_id, context=None):
        pcash = False
        if not context:
            context = {}
        else:
            journal_type = context.get('journal_type', None)
        if journal_type == 'pcash':
            pcash = True
        pool_account_bank_st = self.pool.get("account.bank.statement")
        if pcash:
            search_account_bank_st = pool_account_bank_st.search(cr, uid, [("user_id",  "=", user_id),
                                                                           ("state", "=", "open"), ("journal_id.type", "=", 'pcash')])
        else:
            search_account_bank_st = pool_account_bank_st.search(cr, uid, [("user_id",  "=", user_id),
                                                                           ("state", "=", "open"), ("journal_id.type", "=", 'moves')])
        if(not search_account_bank_st):
            return {"value": {"statement_id": False, "amount": 0}}
        range_amount = self.get_range_amount(cr, uid, user_id, search_account_bank_st[0], context)
        amount = 0.00
        return {"value": {"statement_id": search_account_bank_st[0], "amount": amount}}

    def onchange_statement_id(self, cr, uid, ids, user_id, statement_id, context=None):
        if(not statement_id):
            return {"value": {"amount": 0}}
        range_amount = self.get_range_amount(cr, uid, user_id, statement_id, context)
        amount = range_amount.get("maximun_cash_voucher_amount", 0)
        if amount >= 0:
            amount = 0.00
        return {"value": {"amount": amount}}

    def onchange_amount(self, cr, uid, ids, amount, user_id, statement_id, context=None):
        range_amount = self.get_range_amount(cr, uid, user_id, statement_id, context)

        min_amount = range_amount.get("minimun_cash_voucher_amount")
        max_amount = range_amount.get("maximun_cash_voucher_amount")

        if(amount < min_amount):
            return {"value": {"amount": amount},
                    "warning": {"title":
                                _("Validation Error"), "message": _("El monto a entregar debe ser mayor a "+str(min_amount))}}

        elif(amount > max_amount):
            return {"value": {"amount": amount},
                    "warning": {"title":
                                _("Validation Error"), "message": _("El monto a entregar debe ser menor a "+str(max_amount))}}
        else:
            return {"value": {"amount": amount}}
#         return {}

    def action_change_state_draft(self, cr, uid, ids, context=None):

        if context is None:
            context = {}

        #  caja registradora
        pool_account_bank_st = self.pool.get("account.bank.statement")
        #  linea caja registradora
        pool_account_bank_st_line = self.pool.get("account.bank.statement.line")
        #  movimiento contable
        pool_account_move = self.pool.get("account.move")

        #  obtener datos de vale de caja
        browse_payments = self.browse(cr, uid, ids, context)

        #  caja registradora caja chica
        account_bank_st_id = []
        #  movimiento contable ids
        account_move_ids = []
        #  linea de caja registradora ids
        account_bank_st_line_ids = []

        for payment in browse_payments:
            #  obtener lineas de caja registradora
            if(payment.statement_line_id):
                #  id de caja registradora
                account_bank_st_id.append(payment.statement_line_id.statement_id.id)
                account_bank_st_line_ids.append(payment.statement_line_id.id)

            #  borrar lineas de caja registradora
            if(account_bank_st_line_ids):
                pool_account_bank_st_line.unlink(cr, uid, account_bank_st_line_ids, context)

            if payment.pay_vouch_ids:
                raise osv.except_osv(_("Error !"),  _("No se puede cambiar el estado de un Vale de Caja asociado a un pago"))

            #  obtener movimientos contables ids
            if(payment.move_id):
                account_move_ids.append(payment.move_id.id)

            #  borrar lineas de movimientos contable
            if(account_move_ids):
                pool_account_move.button_cancel(cr, uid, account_move_ids, context)
                pool_account_move.unlink(cr, uid, account_move_ids, context)

            if payment.invoice_id and payment.is_cash_voucher and payment.type == "payment":
                if payment.move_id:
                    for moves_lines in payment.move_id.line_id:
                        if moves_lines.reconcile_id:
                            cr.execute("""update account_move_line set write_date = now(),  reconcile_id = Null where reconcile_id = %s""",
                                       (moves_lines.reconcile_id.id,))
                            cr.execute("""delete from account_move_reconcile where id = %s""",
                                       (moves_lines.reconcile_id.id,))
                if payment.invoice_id and not payment.withhold:
                    #  self.pool.get('account.invoice').cancel_only_invoice(cr,  uid,  [payment.invoice_id.id],  context)
                    self.pool.get('account.invoice').write(cr,  uid,  [payment.invoice_id.id], {}, context)
        self.write(cr,  uid,  payment.id,  {"state": "cancel", "move_id": None, "statement_line_id": None})
        if(account_bank_st_id):
            pool_account_bank_st.write(cr, uid, account_bank_st_id, {})
        #  account-move_line
        #  account move
        return True

    def action_change_state_post(self, cr, uid, ids, context=None):
        browse_payments = self.browse(cr, uid, ids, context)
        for payments in browse_payments:
            if(payments.move_id):
                pool_account_move = self.pool.get("account.move")
                pool_account_move.post(cr, uid, [payments.move_id.id], context)
            else:
                if(context is None):
                    context = {}
                context["approve_account_entry"] = True
                self.action_change_state_paid(cr,  uid,  ids,  context)
        return True

    def action_change_state_paid(self, cr, uid, ids, context=None):
        vals = {}
        if not context:
            context = {}
        account_expense_cash_id = False
        approve_account_entry = context.get("approve_account_entry", True)
        withhold = context.get('withhold',  False)
        invoiced = context.get('invoiced',  False)
        #  caja registradora
        pool_account_bank_st = self.pool.get("account.bank.statement")
        #  linea caja registradora
        pool_account_bank_st_line = self.pool.get("account.bank.statement.line")
        #  movimiento contable
        pool_account_move = self.pool.get("account.move")
        #  lineas de movimientos contables
        pool_account_move_line = self.pool.get("account.move.line")

        browse_payments = self.browse(cr, uid, ids, context)
        statement_id = False
        absl_type = 'supplier'

        for payment in browse_payments:
            if withhold:
                details = 'RETENCIONES DE CLIENTES'
                name = 'PAGO DE RETENCION DE CLIENTE # '
                name_ref = "RET # " + payment.name
            elif invoiced and payment.invoice_id.journal_id.type == 'purchase':
                details = 'FACTURA DE PROVEEDORES'
                name = 'PAGO DE FACTURA DE PROVEEDOR # '
                name_ref = "FACT # " + payment.name
            elif invoiced and payment.invoice_id.journal_id.type == 'purchase_liquidation':
                details = 'LIQUIDACIÓN DE COMPRAS'
                name = 'PAGO DE LIQUIDACIÓN DE COMPRAS # '
                name_ref = "LIQ # " + payment.name
            elif invoiced and payment.invoice_id.journal_id.type == 'sale_note':
                details = 'NOTA DE CRÉDITO DE PROVEEDORES'
                name = 'NOTA DE CRÉDITO DE PROVEEDORES # '
                name_ref = "NV # " + payment.name
            else:
                if payment.type == 'payment':
                    details = 'VALE DE CAJA'
                    name = 'PAGO DE VALE # '
                    name_ref = "VALE # " + payment.name
                else:
                    details = 'RECIBO DE CAJA'
                    name = 'PAGO DE RECIBO # '
                    name_ref = "RECIBO # " + payment.name

            if not payment.partner_id:
                vals["partner_id"] = payment.company_id.partner_id.id
            else:
                vals["partner_id"] = payment.partner_id.id

            if payment.account_expense_cash_id or payment.account_input_cash_id:
                account_expense_cash_id = payment.account_expense_cash_id
                if invoiced:
                    account_haber = payment.mode_id.debit_account_id
                else:
                    account_haber = payment.account_expense_cash_id.account_id
                account_input_cash_id = payment.account_input_cash_id

            elif(not payment.account_expense_cash_id and not payment.account_input_cash_id):
                if context.get('lines',  False):
                    if context.get('withhold',  False):
                        account_haber = payment.partner_id.property_account_receivable
                    else:
                        account_haber = payment.mode_id.debit_account_id
                elif withhold:
                    account_expense_cash_id = payment.company_id.property_account_customer_withhold
                    account_input_cash_id = False
                    account_haber = payment.invoice_id.account_id
                else:
                    raise osv.except_osv(_("Integrity Error !"),
                                         _("Campo DETALLE no puede estar vacio, cuenta para CREDITO o DEBITO debe ser definido!"))
            statement_id = payment.statement_id.id

        browse_account_bank_st = pool_account_bank_st.browse(cr, uid, statement_id, context)

        shop_id = browse_account_bank_st.printer_id.shop_id.id
        balance_end = browse_account_bank_st.balance_end
        period_id = browse_account_bank_st.period_id.id
        journal_id = browse_account_bank_st.journal_id.id
        context['journal'] = journal_id

        for payment in browse_payments:

            if payment.type == 'payment':
                if((balance_end-payment.amount) < 0):
                    raise osv.except_osv(_("!Error de Validación !"),
                                         _("No se puede realizar el vale de caja,"
                                           " ya que existiría un déficit de "+str((balance_end-payment.amount))+"en la Caja."))

            #  detalle o concepto
            vals["ref"] = payment.motive
            #  id caja
            vals["statement_id"] = statement_id
            vals["company_id"] = payment.company_id.id
            #  numero de documento
            vals["name"] = name_ref
            vals["date"] = payment.payment_date
            vals["payment_id"] = payment.id

            #  creacion de movimiento contable
            if account_expense_cash_id or context.get('lines', False):
                debe = payment.mode_id.debit_account_id.id
                haber = account_haber.id
                debit = 0.0
                credit = payment.amount
                debit2 = payment.amount
                credit2 = 0.0
                vals["type"] = "supplier"
                vals["amount"] = payment.amount
            elif payment.account_input_cash_id:
                name = "INGRESO DE CAJA #"
                haber = payment.account_input_cash_id.account_id.id
                debe = payment.mode_id.debit_account_id.id
                debit = payment.amount_credit
                credit = 0.0
                debit2 = 0.0
                credit2 = payment.amount_credit
                vals["type"] = "customer"
                vals["amount"] = payment.amount_credit
                absl_type = 'customer'
                name_ref = "INGRESO # " + payment.name
            move_id = pool_account_move.create(cr,  uid,  {"name": str(payment.name),
                                                           "journal_id": journal_id,
                                                           "date": payment.payment_date,
                                                           "ref": _(name) + str(payment.name) or "/",
                                                           "period_id": period_id,
                                                           "partner_id": payment.partner_id.id,
                                                           "shop_id": shop_id,
                                                           "details": details,
                                                           "company_id": payment.company_id.id,
                                                           })

            #  linea de movimiento contable -debe
            move_inv = context.get('move_inv', False)
            if move_inv:
                move_line_inv = pool_account_move_line.browse(cr, uid, move_inv)
                debit = move_line_inv.amount_residual_currency
                credit = 0.00
                debe = move_line_inv.account_id.id
                debit2 = 0.00
                credit2 = payment.amount

            debit_move_line_id = pool_account_move_line.create(cr,  uid,  {"name": _(name) + str(payment.name) or "/",
                                                                           "debit": debit,
                                                                           "credit": credit,
                                                                           "move_id": move_id,
                                                                           "journal_id": journal_id,
                                                                           "period_id": period_id or False,
                                                                           "partner_id": payment.partner_id.id or payment.company_id.partner_id.id,
                                                                           "date": payment.payment_date,
                                                                           "statement_id": statement_id,
                                                                           "account_id": debe,
                                                                           "reference": payment.name,
                                                                           "company_id": payment.company_id.id
                                                                           },  context)

            #  linea de movimiento contable -haber
            credit_move_line_id = pool_account_move_line.create(cr,  uid,  {"name":  _(name)+str(payment.name) or "/",
                                                                            "debit": debit2,
                                                                            "credit": credit2,
                                                                            "move_id": move_id,
                                                                            "journal_id": journal_id,
                                                                            "period_id": period_id or False,
                                                                            "partner_id": payment.partner_id.id or payment.company_id.partner_id.id,
                                                                            "date": payment.payment_date,
                                                                            "statement_id": statement_id,
                                                                            "account_id": haber,
                                                                            "reference": payment.name,
                                                                            "company_id": payment.company_id.id
                                                                            }, context)

            vals["move_line_id"] = debit_move_line_id
            vals["account_id"] = payment.mode_id.debit_account_id.id
            vals["bk_type"] = 'supplier'
            vals["type"] = absl_type

            #  creacion de linea en caja registradora
            statement_line_id = pool_account_bank_st_line.create(cr, uid, vals, context)
            self.write(cr,  uid, payment.id,  {"state": "paid", "move_id": move_id, "statement_line_id": statement_line_id})
            if browse_account_bank_st.journal_id.type == 'pcash':
                if payment.account_expense_cash_id:
                    self.write(cr, uid, payment.id, {"is_cash_voucher": True})
                elif payment.account_input_cash_id:
                    self.write(cr, uid, payment.id, {"is_cash_receipts": True})

            #  actualizacion de account.payments
            pool_account_bank_st.write(cr, uid, [statement_id], {})
            if(approve_account_entry):
                pool_account_move.post(cr, uid, [move_id], context)

            if payment.account_expense_cash_id and \
               payment.account_expense_cash_id.account_id.id == payment.company_id.property_account_employee_receivable.id:
                discount_obj = self.pool.get('hr.discount')
                lines_obj = self.pool.get('hr.discount.lines')
                types = self.pool.get('hr.transaction.type')
                tt = types.search(cr,  uid,  [('type_expense', '=', 'advance')])[0]
                employee = self.pool.get('hr.employee').search(cr,  uid,  [('partner_id', '=', payment.partner_id.id)])
                if employee:
                    employee = employee[0]
                else:
                    raise osv.except_osv(_("Error !"),
                                         _("No existen empleados con la razón social indicada."
                                           "Por favor crear el empleado y el contrato correspondiente para continuar."))
                journal = self.pool.get('account.journal').search(cr,  uid,  [('type', '=', 'discount_employee'),
                                                                              ('company_id', '=', payment.company_id.id)])[0]
                discount_id = discount_obj.create(cr,  uid,
                                                  {'company_id': payment.company_id.id,
                                                   'name': tt,
                                                   'employee_id': employee,
                                                   'contract_id': self.pool.get('hr.contract').search(cr, uid, [('employee_id', '=', employee)])[0],
                                                   'ref': payment.motive,
                                                   'date': payment.payment_date,
                                                   'collection_form': 'end_month',
                                                   'date_from': payment.payment_date,
                                                   'amount': payment.amount,
                                                   'number_of_quotas': 1,
                                                   'payment_form': 'payment',
                                                   'mode_id': payment.mode_id.id,
                                                   'user_id': payment.user_id.id,
                                                   'period_id': payment.period_id.id,
                                                   'payment_id': payment.id,
                                                   'journal_id': journal,
                                                   'move_id': move_id,
                                                   'type': 'advance',
                                                   'state': 'approve'
                                                   })

                lines_id = lines_obj.create(cr,  uid,
                                            {'employee_id': employee,
                                             'name': _(types.browse(cr,  uid,  tt).name) + '-' + (payment.motive) + '(1 cuota)',
                                             'total': payment.amount,
                                             'amount': payment.amount,
                                             'amount2': 0.00,
                                             'date': payment.payment_date,
                                             'number_quota': 1,
                                             'discount_id': discount_id,
                                             'state': 'draft',
                                             'move_line_id': debit_move_line_id
                                             })
        return move_id

account_payments()


class payment_mode(osv.osv):

    _inherit = "payment.mode"
    _columns = {'petty': fields.boolean('Caja Chica', required=False)}

payment_mode()
