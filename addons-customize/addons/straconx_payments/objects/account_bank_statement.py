# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>)
##############################################################################

from osv import fields, osv
import time
import decimal_precision as dp
from tools.translate import _
from account.account_bank_statement import account_bank_statement
from account_voucher import account_voucher

class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    
    def _check_amount(self, cr, uid, ids, context=None):
        amount = 0.00
        amount_voucher = 0.00
        amount_payment = 0.00
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.voucher_id:                
                if obj.voucher_id.type=='payment':                
                    for vouch in obj.voucher_id.line_dr_ids:
                        amount_voucher +=vouch.amount
                else:
                    for vouch in obj.voucher_id.line_cr_ids:
                        amount_voucher +=vouch.amount
            if obj.voucher_id.payments:
                for pay_id in obj.voucher_id.payments:
                    amount_payment += pay_id.amount 
                diff = amount_voucher - amount_payment
                if diff > abs(0.01):
#                    return False
                    continue
            else:
                return True
        return True
     
    _columns = {
        "payment_id": fields.many2one("account.payments","Payment"),
        'move_line_id': fields.many2one('account.move.line', 'Move Line'),
        'type': fields.selection([
            ('supplier','Supplier'),
            ('customer','Customer'),
            ('changed','Changed check'),
            ], 'Type', required=True),
        'bk_type': fields.selection([
            ('supplier','Pagos'),
            ('pos','Contado'),
            ('credit','Crédito'),
            ('changed','Canje Cheques'),
            ], 'Type', required=False),    
        'active':fields.boolean('Activo'),
        'ref': fields.char('Reference', size=256),        
                }
    
    _constraints = [
        (_check_amount, 'EL valor de los pagos debe ser igual al valor de los documentos pagados', ['amount']),
    ]
      
    _defaults = {'active': True,
                 }
    
    def unlink(self, cr, uid, ids, context=None):
        date=time.strftime('%Y-%m-%d %H:%M:%S'),
        voucher_obj = self.pool.get('account.voucher')
        statement_line = self.browse(cr, uid, ids, context=context)
        unlink_ids = []
        for st_line in statement_line:
            if st_line.voucher_id:
                unlink_ids.append(st_line.voucher_id.id)
        if unlink_ids:
            voucher_obj.unlink(cr, uid, unlink_ids, context=context)
        cr.execute("""update account_bank_statement_line set  write_date =now(), active=False, amount=0.00, write_uid=%s where id in %s """,(uid,tuple(ids),))
        return True
#        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)    
account_bank_statement_line()

class account_total_line(osv.osv):

    _name = "account.total.line"
    _rec_name = "mode_id" 
    _columns = {
        'payments_ids': fields.many2many('account.payments', 'account_payments_total_rel', 'total_id', 'payment_id', 'payments', readonly=True,),
        #'payments_ids':fields.one2many('account.payments', 'total_id', 'Payments', required=False),
        "mode_id": fields.many2one("payment.mode","Type", readonly=True),
        "amount": fields.float("Amount",readonly=True),
        'cash_id':fields.many2one('account.bank.statement', 'Cash', required=False),
        'type': fields.selection([
            ('supplier','Supplier'),
            ('customer','Customer'),
            ('changed','Changed check'),
            ], 'Type', required=True),
    }
account_total_line()

# From Cashbox of OpenERP's Point of Sale
class account_bank_statement(osv.osv):
    
#    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):
#        res2 = {}
#        for statement in self.browse(cr, uid, ids, context=context):
#            res2[statement.id] = {'total_entry_encoding':0.0,
#                                  'total_outlet_encoding':0.0,
#                                  }
#            for line in statement.line_ids:
#                if line.payment_id.mode_id.cash:
#                    if line.type=='supplier':
#                        res2[statement.id]['total_outlet_encoding'] += line.amount
#                    elif line.type=='customer':
#                        res2[statement.id]['total_entry_encoding'] += line.amount
#                if line.type == 'changed':
#                    res2[statement.id]['total_outlet_encoding'] += line.amount
#        return res2

    

    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):
        res2 = {}
        statement_line_obj = self.pool.get('account.bank.statement.line')
        for statement in self.browse(cr, uid, ids, context=context):
            res2[statement.id] = {'total_entry_encoding':0.0,
                                  'total_outlet_encoding':0.0,
                                  }
            total_outlet = statement_line_obj.search(cr, uid, [('statement_id','=',statement.id),'|',('type','=','changed'),'&',('type','=','supplier'),('payment_id.mode_id.cash','=',True)])
            if total_outlet:
                cr.execute('select sum(amount) from account_bank_statement_line where id in %s',(tuple(total_outlet),))
                amount = cr.fetchall()
                res2[statement.id]['total_outlet_encoding'] = amount and amount[0][0] or 0.0
            total_entry = statement_line_obj.search(cr, uid, [('statement_id','=',statement.id),('type','=','customer'),('payment_id.mode_id.cash','=',True)])
            if total_entry:
                cr.execute('select sum(amount) from account_bank_statement_line where id in %s',(tuple(total_entry),))
                amount = cr.fetchall()
                res2[statement.id]['total_entry_encoding'] = amount and amount[0][0] or 0.0
#            for line in statement.line_ids:
#                if line.payment_id.mode_id.cash:
#                    if line.type=='supplier':
#                        res2[statement.id]['total_outlet_encoding'] += line.amount
#                    elif line.type=='customer':
#                        res2[statement.id]['total_entry_encoding'] += line.amount
#                if line.type == 'changed':
#                    res2[statement.id]['total_outlet_encoding'] += line.amount
        return res2
    
    def _get_sum_other_incomes(self, cr, uid, ids, name, arg, context=None):
        res2 = {}
        statement_line_obj = self.pool.get('account.bank.statement.line')
        for statement in self.browse(cr, uid, ids, context=context):
            encoding_total = 0.0
            total = statement_line_obj.search(cr, uid, [('statement_id','=',statement.id),('payment_id.mode_id.cash','!=',True)])
            if total:
                cr.execute("""select sum(amount) from account_bank_statement_line where type in ('customer','changed') and id in %s""",(tuple(total),))
                amount1= cr.fetchall()
                cr.execute("""select sum(amount) from account_bank_statement_line where type in ('supplier') and id in %s""",(tuple(total),))
                amount2=cr.fetchall()
                encoding_total = (amount1 and amount1[0][0] or 0.0) - (amount2 and amount2[0][0] or 0.0)
            res2[statement.id] = encoding_total
        return res2

    
    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res = {}
        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            val=statement.total_entry_encoding - statement.total_outlet_encoding
            val_final= statement.balance_start + val
            res[statement.id] = round(val_final,2)
        return res
    
    def _get_cash_open_box_lines(self, cr, uid, context=None):
        res = []
        curr = [0.01, 0.05, 0.10, 0.25, 0.50, 1, 5, 10, 20, 50, 100]
        for rs in curr:
            dct = {
                'pieces': rs,
                'number': 0
                }
            res.append(dct)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'moves')], context=context)
        if journal_ids:
            results = self.search(cr, uid, [('journal_id', 'in', journal_ids),('state', '=', 'confirm'),('user_id','=',uid)], order="date", context=context)
            if results:
                cash_st = self.browse(cr, uid, results, context=context)[-1]
                for cash_line in cash_st.starting_details_ids:
                    for r in res:
                        if cash_line.pieces == r['pieces']:
                            r['number'] = cash_line.number
        return res
    
    def _get_default_cash_close_box_lines(self, cr, uid, context=None):
        res = []
        curr = [0.01, 0.05, 0.10, 0.25, 0.50, 1, 5, 10, 20, 50, 100]
        for rs in curr:
            dct = {
                'pieces': rs,
                'number': 0
            }
            res.append(dct)
        return res
    
    def _get_starting_balance(self, cr, uid, ids, context=None):
        res = super(account_bank_statement,self)._get_starting_balance(cr, uid, ids, context)
        
        
        for statement in self.browse(cr, uid, ids, context=context):
            amount_total = 0.0
            
            if statement.journal_id.type not in('cash','moves','pcash'):#agregado pcash para straconx_cash_voucher
                continue

            for line in statement.starting_details_ids:
                amount_total+= line.pieces * line.number
            
            is_petty_cash=(statement.journal_id.type=='pcash')
            if(is_petty_cash):
                maximun_cash_voucher_amount=0.00
                browse_users=self.pool.get("res.users").browse(cr,uid,[statement.user_id.id],context)
                for user in browse_users:
                    maximun_cash_voucher_amount=user.maximun_cash_voucher_amount
                    user_login = user.login
                if(maximun_cash_voucher_amount>=amount_total):
                    res[statement.id] = {'balance_start': amount_total}
                else:
                    raise osv.except_osv(_("Integrity Error !"), _("El valor de la Caja Chica para este usuario debe ser máximo "+str(maximun_cash_voucher_amount)+" para el usuario "+ user_login ))
            else:
                res[statement.id] = {'balance_start': amount_total}
                 
        return res
    
    def _get_default_pay(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context).pay
    
    def _get_default_collect(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context).collect
    
    def _get_default_shop(self, cr, uid, context=None):
        if self.pool.get('res.users').browse(cr, uid, uid, context).cash_box_default_id:
            printer_id = self.pool.get('res.users').browse(cr, uid, uid, context).cash_box_default_id.id
            if printer_id:
                return self.pool.get('printer.point').browse(cr, uid, printer_id, context).shop_id.id
        return None

    def _get_default_printer(self, cr, uid, context=None):
        if self.pool.get('res.users').browse(cr, uid, uid, context).cash_box_default_id:
            return self.pool.get('res.users').browse(cr, uid, uid, context).cash_box_default_id.id
        return None

    def _sbalance_end_cash(self, cr, uid, ids, name, arg, context=None):
        """ Find ending balance  "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        balance_end_cash = 0.00
        for statement in self.browse(cr, uid, ids, context=context):
            balance_end_cash = statement.balance_start or 0.00 
#             saldo= statement.balance_end - statement.total_deposit
#             if saldo:
#                 balance_end_cash = statement.balance_end - statement.total_deposit                
#                 if statement.state <> 'open':
#                     if balance_end_cash - statement.balance_start < 0:
#                         raise osv.except_osv(_('Error !'),_('No se permite cerrar caja con valores negativos.'))
#             else:
#                 balance_end_cash = 0
            res[statement.id] = balance_end_cash
        return res

    def _total_sales(self, cr, uid, ids, name, arg, context=None):
        res = {}
        total = 0
        qty = 0
        invoice = self.pool.get('account.invoice')
        for st in self.browse(cr, uid, ids, context=context):
            user_id = st.user_id.id
            shop_id = st.shop_id.id
            printer_id = st.printer_id.id
            date_start = st.date            
            if st.original_closing_date:
                date_end = st.original_closing_date
            elif st.closing_date:
                date_end = st.closing_date
            else:
                date_end = time.strftime('%Y-%m-%d 23:59:59')
#                date_end = time.strftime('%Y-%m-%d %H:%M:%S') 
            if user_id and shop_id and printer_id and date_start and date_end:
                inv_search = invoice.search(cr,uid,[('user_id','=',user_id),('shop_id','=',shop_id),('printer_id','=',printer_id),('date_invoice2','>=',date_start),('date_invoice2','<=',date_end)])
                if inv_search:
                    inv_ids = invoice.browse(cr,uid,inv_search)
                    for invoices in inv_ids:
                        if invoices.state not in ('draft, proforma'):
                            total += invoices.amount_total_s
                            qty = qty + 1                  
            res[st.id]= {'sales_amount': total,
                         'sales_qty': qty}
            return res
            
    def _balance_end_cash(self, cr, uid, ids, name, arg, context=None):
        """ Find ending balance  "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for statement in self.browse(cr, uid, ids, context=context):
            if statement.state <> 'confirm':
                amount_total = 0.00
            else:
                amount_total = 0.00    
                for line in statement.ending_details_ids:
                    amount_total += line.pieces * line.number
            res[statement.id] = {'total_deposit':amount_total}
        return res            

    def _balance_cash_differences(self, cr, uid, ids, name, arg, context=None):
        res = {}
        cash_diferences = 0.00
        for statement in self.browse(cr, uid, ids, context=context):
            if statement.state <> 'confirm':
                cash_diferences = 0.00
            else:
                cash_diferences = 0.00  
                balance_end_cash = statement.balance_start
                total_deposit = statement.total_deposit or 0.00
                cash_diferences = statement.balance_end - total_deposit - balance_end_cash 
            res[statement.id] = {'cash_diferences':cash_diferences} 
        return res    

    def _get_statement(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()
       
    _inherit = 'account.bank.statement'
    
    _columns = {
        'collect':fields.boolean('Collect', required=False),
        'pay':fields.boolean('Pay', required=False),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'printer_id':fields.many2one('printer.point', 'Cash Collecter', required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'shop_id':fields.many2one('sale.shop', 'Shop', required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'total_entry_encoding': fields.function(_get_sum_entry_encoding, method=True, store=True, string="Cash Transaction Entry", multi="total", help="Total cash transactions Input"),
        'total_outlet_encoding': fields.function(_get_sum_entry_encoding, method=True, store=True, string="Cash Transaction Output", multi="total", help="Total cash transactions Output"),
        'balance_end': fields.function(_end_balance, method=True, string='Balance', 
            store={
                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, None, 50)},
            help="Closing balance based on Starting Balance and Cash Transactions"),
        'balance_end_cash': fields.function(_sbalance_end_cash, store=True, string='Closing Balance', help="Closing balance based on cashBox"),
        'total_ids':fields.one2many('account.total.line', 'cash_id', 'Total', required=False),
        'total_other_incomes': fields.function(_get_sum_other_incomes, method=True, store=True,type='float', string="Other Transaction", help="Total other transactions"),
#        'total_deposit': fields.function(_balance_end_cash, string='Valor en efectivo', help="Closing balance based on cashBox",multi="total",store=True                                            
#             store={
#                 'ending_details_ids':(lambda self, cr, uid, ids, c={}: ids, None, 30),
#                 'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, None, 50),
#                 'account.bank.statement.line': (_get_statement, ['amount'], 50)}
#            ),        
        'deposit':fields.boolean('deposit?', required=False),
        'deposit_numbers': fields.one2many('deposit.register', 'cash_id', 'Deposits IDS', required=False),
        'move_id':fields.many2one('account.move', 'Move Reference', readonly=True),
        'date': fields.datetime('Date', required=True, states={'confirm': [('readonly', True)]}, select=True),
        'sales_amount': fields.function(_total_sales, method=True, string="Valor", multi="total", help='Las facturas y notas de crédito que se han generado durante el período de la Caja',
                          store={
                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, None, 50),
                'account.bank.statement.line': (_get_statement, ['amount'], 50)}),
        'sales_qty': fields.function(_total_sales, method=True, string="Cantidad", multi="total", help='Las facturas y notas de crédito que se han generado durante el período de la Caja. Si la caja no esta cerada, calculará hasta las 18:00:00',
                          store={
                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, None, 50),
                'account.bank.statement.line': (_get_statement, ['amount'], 50),
            },),                
        'cash_diferences':fields.float('Diferencia en Caja', help="Muestra la diferencia de caja entre el valor ingresado y el valor a depositar"),
        'total_deposit': fields.float('Valor en efectivo', help="Closing balance based on cashBox"),
        'original_closing_date': fields.datetime("Closed On"),
        'note': fields.text('Notes'),
        'active':fields.boolean('Active'),
        'state': fields.selection([('draft', 'New'),
                                   ('open','Open'),
                                   ('cancel','Cancel'), 
                                   ('confirm', 'Closed')],
                                   'State', required=True, readonly="1"),
        }
    _defaults = {
        'starting_details_ids': _get_cash_open_box_lines,
        'ending_details_ids': _get_default_cash_close_box_lines,
        'pay': _get_default_pay,
        'collect': _get_default_collect,
        'printer_id': _get_default_printer,
        'shop_id': _get_default_shop,
        'deposit': lambda *a: False,
        'active':True,
     }
    
    def on_change_user(self, cr, uid, ids, user_id=None, context=None):
        values = {}
        warning={}
        domain={}
        if user_id:
            user=self.pool.get('res.users').browse(cr, uid, user_id, context)
            if not user.is_cashier :
                warning = {'title': _('Error!'),'message': _(('El usuario %s no tiene perfil de Cajero.')%user.name)}
            elif not user.cash_box_default_id:
                warning = {'title': _('Error!'),'message': _(('El usuario %s debe tener una Caja predeterminada asignada.')%user.name)}
            else:
                values['printer_id']=user.cash_box_default_id.id
                domain={'printer_id':[('id','=', user.cash_box_default_id.id)]}
        return {'value': values, 'domain':domain, 'warning':warning}
    
    def create(self, cr, uid, vals, context=None):
#        details_start = vals.get('starting_details_ids',[])
        if context is None:
            context = {}
        if not self.pool.get('res.users').browse(cr, uid, vals.get('user_id', uid), context).is_cashier:
            raise osv.except_osv(_('Error !'),_('You not have permission to open a box.'))
        
        if (not context.get("journal_type",False)):##
            context["journal_type"]="moves"        ##si es tipo moves 
            
        sql = [
                ('user_id', '=', vals.get('user_id', uid)),
                ('company_id', '=', vals.get('company_id', None)),
                ('state', '=', 'open'),
                ('printer_id', '=', vals.get('printer_id', None)),
                ('journal_id.type','=',context.get('journal_type'))
        ]
        
        open_jrnl = self.search(cr, uid, sql)
        comp = vals.get('company_id', uid)
        if open_jrnl:
            cash = self.browse(cr, uid, open_jrnl[0])
            if comp == cash.company_id.id:
                if(context.get('journal_type')!="pcash"):##si no es caja chica
                    raise osv.except_osv(_('Error'), _('You can not have two open register for the same point printer'))
                else:##si es caja chica
                    raise osv.except_osv(_('Error'), _('You can not have two open PETTY CASH for the same point printer'))
        
        res_id = super(osv.osv, self).create(cr, uid, vals, context=context)
#        open_close = self._get_cash_open_close_box_lines(cr, uid, context)
#        if details_start:
#            for start in details_start:
#                dict_val = start[2]
#                for end in open_close['end']:
#                    if end[2]['pieces'] == dict_val['pieces']:
#                        end[2]['number'] += dict_val['number']
#        else:
#            details_start=open_close['start']
#        self.write(cr, uid, [res_id], {'ending_details_ids': [],})
#        self.write(cr, uid, [res_id], {'ending_details_ids': open_close['end'],})
        return res_id
    
    def _equal_balance(self, cr, uid, cash_id, context=None):
        return True
        
    def add_line_cash_register(self, cr, uid, voucher_id, payment_id, move_line_id, context=None):
        statement_line_obj = self.pool.get('account.bank.statement.line')
#        curr_c = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
#        curr_company = curr_c.id
        account=None
        tp=None
        bk_type = 'pos'
        bk_name = 'POS'
        bk_typel = False 
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=context)
        payment=self.pool.get('account.payments').browse(cr, uid, payment_id, context)
        context.get('type_credit',False)
        move_line_invoice_id = context.get('move_line_invoice_id',False)
        
        if move_line_invoice_id:
            bk_type_obj = self.pool.get('account.move.line').browse(cr,uid,move_line_invoice_id)
            bk_typel = bk_type_obj.invoice.credit

        if not bk_typel:
            bk_type = 'pos'
            bk_name = 'POS '
        else:
            bk_type = 'credit'
            bk_name = 'CRE '
        
        if voucher.type in ('purchase', 'payment'):
            tp='supplier'
            account = payment.mode_id.credit_account_id.id
            name='PAGO A PROVEEDOR %s'%(voucher.reference or '')
            ref = payment.beneficiary
        elif voucher.type in ('sale', 'receipt'):
            tp='customer'
            account = payment.mode_id.debit_account_id.id
            a = voucher.line_ids 
            if a:
                n_name = voucher.reference
                if not n_name:
                    if payment.credit_notes:
                        n_name = payment.credit_note_id.number 
                    elif voucher.line_ids[0].move_line_id.reference:
                        n_name = voucher.line_ids[0].move_line_id.reference
                    else:
                        n_name = voucher.line_ids[0].move_line_id.move_id.ref
                if n_name:
                    name = bk_name+n_name
                    ref=n_name
                else:                
                    name=bk_name+voucher.reference
                    ref=voucher.reference  
            else:                
                name=voucher.receipt_id.name or voucher.number or voucher.reference
                ref=voucher.reference or voucher.number
        args = {
            'amount': payment.amount,
            'date': time.strftime('%Y-%m-%d'),
            'name': name,
            'account_id':account,
            'partner_id':voucher.partner_id.id,
            'ref': ref,
            'statement_id': voucher.bank_statement.id,
            'type':tp,
            'voucher_id':voucher.id,
            'payment_id':payment.id,
            'move_line_id':move_line_id,
            'bk_type':bk_type,
            'state':'posted'
        }
        line_id = statement_line_obj.create(cr, uid, args, context=context)
        return line_id
    
    def button_confirm_bank(self, cr, uid, ids, context=None):
        obj_seq = self.pool.get('ir.sequence')
        total_obj = self.pool.get('account.total.line')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
#            if (not st.journal_id.default_credit_account_id) \
#                    or (not st.journal_id.default_debit_account_id):
#                raise osv.except_osv(_('Configuration Error !'),
#                        _('Please verify that an account is defined in the journal.'))

            if not st.name == '/':
                st_number = st.name
            else:
                if st.journal_id.sequence_id:
                    c = {'fiscalyear_id': st.period_id.fiscalyear_id.id}
                    st_number = obj_seq.next_by_id(cr, uid, st.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.get(cr, uid, 'account.bank.statement')

            for line in st.move_line_ids:
                if line.state not in ('valid','cancel'):
                    raise osv.except_osv(_('Error !'),
                            _('The account entries lines are not in valid state.'))
            values={}
            for st_line in st.line_ids:
                if st_line.analytic_account_id:
                    if not st.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (st.journal_id.name,))
                if not st_line.amount:
                    continue
                if not values.has_key((st_line.type,st_line.payment_id.mode_id.id)):
                    values[(st_line.type,st_line.payment_id.mode_id.id)]=[st_line.amount,[st_line.payment_id.id]]
                else:
                    values[(st_line.type,st_line.payment_id.mode_id.id)][0]+=st_line.amount
                    values[(st_line.type,st_line.payment_id.mode_id.id)][1].append(st_line.payment_id.id)
            for tup in values.keys():
                total_obj.create(cr, uid, {'mode_id':tup[1],
                                           'type':tup[0],
                                           'amount':values[tup][0],
                                           'cash_id':st.id,
                                           'payments_ids':[[6,0,values[tup][1]]],})
            amount_total = 0.00
            for line in st.ending_details_ids:
                    amount_total += line.pieces * line.number
            balance_end_cash = st.balance_start
            total_deposit = amount_total or 0.00
            cash_diferences = st.balance_end - total_deposit - balance_end_cash  
            cr.execute("""update account_bank_statement set  write_date =now(), name=%s, balance_end_real=%s, total_deposit=%s, cash_diferences=%s, state='confirm' where id=%s""",(st_number,st.balance_end,amount_total,cash_diferences,st.id))
        
#             self.write(cr, uid, [st.id], {
#                     'name': st_number,
#                     'balance_end_real': st.balance_end,
#                     'total_deposit':amount_total,
#                     'cash_diferences':cash_diferences
#                     
#             }, context=context)
            self.log(cr, uid, st.id, _('Statement %s is confirmed, journal items are created.') % (st_number,))
#        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)
        return True
    
    
    def button_confirm_cash(self, cr, uid, ids, context=None):
        self.button_confirm_bank(cr, uid, ids, context=context)
        for cash in self.browse(cr, uid, ids, context):
            date= time.strftime("%Y-%m-%d %H:%M:%S")
            open_date = cash.date
            if cash.original_closing_date and cash.original_closing_date>open_date:
                date = cash.original_closing_date
                original_closing_date = cash.original_closing_date
            elif cash.closing_date and cash.closing_date > open_date:
                date=cash.closing_date
                original_closing_date = date
            elif date and date > open_date:
                date = date
                original_closing_date = date
            else:
                date = time.strftime("%Y-%m-%d 23:00:00")
                original_closing_date = time.strftime("%Y-%m-%d 23:00:00")
            cr.execute("""update account_bank_statement set  write_date =now(), closing_date=%s, original_closing_date=%s where id =%s """,(date, original_closing_date,cash.id))
#            self.write(cr, uid, [cash.id], {'closing_date': date, 'original_closing_date':original_closing_date}, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        done = []
        cash_box_line_pool = self.pool.get('account.cashbox.line')
        for st in self.browse(cr, uid, ids, context=context):
            if st.state=='draft':
                continue
            if st.line_ids:
                raise osv.except_osv(_('Error !'),_('You can not cancel this cash because already have payments received.'))
            for end in st.ending_details_ids:
                cash_box_line_pool.write(cr, uid, [end.id], {'number': 0})
            done.append(st.id)
        return self.write(cr, uid, done, {'state':'draft'}, context=context)

    def button_re_open(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        lines=[]
        deposits=[]
        chk=[]
        move_pool = self.pool.get('account.move')
        reconcile_pool = self.pool.get('account.move.reconcile')
        for st in self.browse(cr, uid, ids, context=context):
            remove_reconcile = []
            if st.move_id:
                for lin in st.move_id.line_id:
                    if lin.reconcile_id:
                        remove_reconcile += [lin.reconcile_id.id]
                    if lin.reconcile_partial_id:
                        remove_reconcile += [lin.reconcile_partial_id.id]
                reconcile_pool.unlink(cr, uid, remove_reconcile)
                move_pool.button_cancel(cr, uid, [st.move_id.id], context={})
                move_pool.unlink(cr, uid, [st.move_id.id], context={})
            for line in st.total_ids:
                lines.append(line.id)
                if line.type in ('customer','changed') and line.mode_id.to_deposit:
                    for l in line.payments_ids:
                        chk.append(l.id)
            for dep in st.deposit_numbers:
                deposits.append(dep.id)
        if lines:
            self.pool.get('account.total.line').unlink(cr, uid, lines, context)
        if deposits:
            self.pool.get('deposit.register').action_set_draft(cr, uid, deposits, context)
            self.pool.get('deposit.register').unlink(cr, uid, deposits, context)            
        if chk:
            self.pool.get('account.payments').write(cr, uid, chk, {'state':'hold'})
        self.write(cr, uid, ids, {'state': 'open','deposit': False,'closing_date':None,'total_deposit':0.00, 'cash_diferences':0.00, 'balance_end_cash':0.00}, context=context)
        return True

    def onchange_balance(self,cr,uid,ids,balance_end,total_deposit,context=None):
        res={'balance_end_cash':0.00}
        if balance_end and total_deposit:
            balance_end_cash = balance_end - total_deposit
            res['balance_end_cash'] = balance_end_cash
        return {'value': res}
        
    def button_cancel_changes(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        move_pool = self.pool.get('account.move')
        for st in self.browse(cr, uid, ids, context=context):
            if st.deposit:
                raise osv.except_osv(_('Error!'),_("You can not annulled changes check with values deposited"))
            if st.state != 'open':
                raise osv.except_osv(_('Error!'),_("You can not annulled changes check with the statement cash in state open"))
            lines_change=self.pool.get('account.bank.statement.line').search(cr, uid, [('statement_id','=',st.id),('type','=','changed')])
            if not lines_change:
                continue
            for line in self.pool.get('account.bank.statement.line').browse(cr, uid, lines_change, context):
                if line.move_line_id:
                    move_pool.button_cancel(cr, uid, [line.move_line_id.move_id.id], context={})
                    move_pool.unlink(cr, uid, [line.move_line_id.move_id.id], context={})
                if line.payment_id.state == 'exchanged':
                    self.pool.get('account.payments').write(cr, uid, [line.payment_id.id], {'state':'hold'})
            self.pool.get('account.bank.statement.line').unlink(cr, uid, lines_change, context={})
        self.write(cr, uid, ids, {}, context)
        return True

    def onchange_line_end_detail_ids(self, cr, uid, ids, line_dr_ids, context=None):
        context = context or {} 
        if not line_dr_ids:
            return {'value':{}}
        total =  0.00
        line_osv = self.pool.get('account.cashbox.line')
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['number','pieces'], context)
#        bank_obj = self.pool.get('account.bank.statement').browse(cr,uid,ids)
        for line in line_dr_ids:
            number = line.get('number', 0.0)
            pieces = line.get('pieces', 0.0)
            subtotal = number * pieces
            total += subtotal
#        cash_diferences = bank_obj.balance_end - total - bank_obj.balance_start
        return {'value': {'total_deposit': total}}        

    def onchange_line_start_detail_ids(self, cr, uid, ids, line_dr_ids, context=None):
        context = context or {} 
        if not line_dr_ids:
            return {'value':{}}
        total =  0.00
        line_osv = self.pool.get('account.cashbox.line')
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['number','pieces'], context)
        for line in line_dr_ids:
            number = line.get('number', 0.0)
            pieces = line.get('pieces', 0.0)
            subtotal = number * pieces
            total += subtotal
        return {'value': {'balance_start': total}}  

    def unlink(self, cr, uid, ids, context=None):
        stat = self.read(cr, uid, ids, ['state','line_ids'], context=context)
        unlink_ids = []
        for t in stat:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            elif t['line_ids']:
                raise osv.except_osv(_('¡Acción Inválida!'), _('No puede borrar Cajas que tiene línea de movimientos'))  
            else:
                raise osv.except_osv(_('Invalid action !'), _('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
        #osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
            cr.execute("""update account_bank_statement_line set write_date =now(),  active=False, amount = 0.00 where statement_id in %s """,(tuple(ids),))
            cr.execute("""update account_bank_statement set  write_date =now(), state='cancel', active=False where id in %s """,(tuple(ids),))
        return True
    
    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('¡Acción Inválida !'), _('No se puede duplicar Cajas de Movimientos de Dinero, por favor, proceda a abrir una nueva Caja'))

account_bank_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
