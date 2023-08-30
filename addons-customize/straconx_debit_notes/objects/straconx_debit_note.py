# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv
from tools.translate import _
import time
import decimal_precision as dp
from account_voucher import account_voucher

class account_debit_note(osv.osv):
    
    def _total_amount(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for note in self.browse(cr, uid, ids, context=context):
            result[note.id] = 0.0
            for line in note.line_ids:
                result[note.id] += line.amount or 0.0
        return result
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal = []
        if context.get('default_type',False) in ('debit_customer','debit_supplier'):
            journal=self.pool.get('account.journal').search(cr, uid, [('type','=','debit_note')])
        elif context.get('default_type',False) in ('advance_customer','advance_supplier'):
            journal=self.pool.get('account.journal').search(cr, uid, [('type','=','advances')])
        return journal and journal[0] or None
    
    def _compute_lines(self, cr, uid, ids, name, args, context=None):
        result = {}
        for debit in self.browse(cr, uid, ids, context=context):
            src = []
            lines = []
            if debit.move_id:
                for m in debit.move_id.line_id:
                    temp_lines = []
                    if m.reconcile_id:
                        temp_lines = map(lambda x: x.id, m.reconcile_id.line_id)
                    elif m.reconcile_partial_id:
                        temp_lines = map(lambda x: x.id, m.reconcile_partial_id.line_partial_ids)
                    lines += [x for x in temp_lines if x not in lines]
                    src.append(m.id)

            lines = filter(lambda x: x not in src, lines)
            result[debit.id] = lines
        return result
    
    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        result = {}
        checked_partial_rec_ids = []
        for debit in self.browse(cr, uid, ids, context=context):
            residual = 0.00
            result[debit.id] = 0.0
            if debit.move_id:
                for m in debit.move_id.line_id:
                    if debit.type in ('debit_customer','debit_customer'):
                        if m.account_id.type in ('receivable'):
                            if m.reconcile_partial_id:
                                partial_reconcile_id = m.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                residual += m.amount_residual_currency
                            elif m.reconcile_id:
                                residual += 0.00
                            else:
                                residual += m.amount_residual_currency
                    if debit.type in ('debit_supplier','advance_supplier'):
                        if m.account_id.type in ('payable'):
                            if m.reconcile_partial_id:
                                partial_reconcile_id = m.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                residual += m.amount_residual_currency
                            elif m.reconcile_id:
                                residual += 0.00
                            else:
                                residual += m.amount_residual_currency
            if residual == 0.00 and debit.state=='posted':
                self.write(cr,uid,[debit.id],{'state':'paid'})            
            elif residual != 0.00 and debit.state=='paid':
                self.write(cr,uid,[debit.id],{'state':'posted'})
            result[debit.id] = residual
        return result


    def _get_debit_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.debit.note.line').browse(cr, uid, ids, context=context):
            result[line.debit_note_id.id] = True
        return result.keys()
    
    def _get_debit_from_line(self, cr, uid, ids, context=None):
        move = {}
        for line in self.pool.get('account.move.line').browse(cr, uid, ids, context=context):
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    move[line2.move_id.id] = True
            if line.reconcile_id:
                for line2 in line.reconcile_id.line_id:
                    move[line2.move_id.id] = True
        debit_ids = []
        if move:
            debit_ids = self.pool.get('account.debit.note').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return debit_ids
    
    def _get_name(self, cr, uid, context={}):
        cr.execute("""select type_vat,name from res_partner where supplier = True""")
        return cr.fetchall()
    
    def _get_debit_from_reconcile(self, cr, uid, ids, context=None):
        move = {}
        for r in self.pool.get('account.move.reconcile').browse(cr, uid, ids, context=context):
            for line in r.line_partial_ids:
                move[line.move_id.id] = True
            for line in r.line_id:
                move[line.move_id.id] = True

        debit_ids = []
        if move:
            debit_ids = self.pool.get('account.debit.note').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return debit_ids

    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        for s in curr_user.printer_point_ids:
            if s.shop_id:
                return s.shop_id.id 
        return None
        
    _name="account.debit.note"
    _columns={
        #'cliente_des':fields.selection(_get_name, 'Descripcion', size=300, required=False),
        'number':fields.char('Number', size=32, required=False, readonly=False),
        "line_ids":fields.one2many('account.debit.note.line','debit_note_id','Debit Note Line',readonly=True, states={'draft':[('readonly',False)]}),
        "partner_id":fields.many2one('res.partner','Partner',readonly=True, states={'draft':[('readonly',False)]}),
        "period_id":fields.many2one('account.period','Period',readonly=True, states={'draft':[('readonly',False)]}),
        "user_id":fields.many2one('res.users','User',readonly=True, states={'draft':[('readonly',False)]}),
        "company_id":fields.many2one('res.company','Company',readonly=True, states={'draft':[('readonly',False)]}),
        "journal_id":fields.many2one('account.journal','Journal',readonly=True, states={'draft':[('readonly',False)]}),
        'move_id':fields.many2one('account.move', 'Reference Account Move', readonly=True),
        "state": fields.selection([('draft','Draft'),('posted','Posted'),('paid','Paid'),('cancel','Canceled')],'State', readonly=True),
        "date": fields.date("Date",readonly=True, states={'draft':[('readonly',False)]}),
        "account_id":fields.many2one('account.account','Account',readonly=True, states={'draft':[('readonly',False)]}),
        "reference":fields.char('Reference', size=256, required=False, states={'draft':[('readonly',False)]}),
        "name":fields.char('Name', size=256, required=False),
        "total_amount": fields.function(_total_amount, method=True,type="float", string='Total Amount', store=True),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'print_status': fields.char('Print Status', size=32),
        'varios':fields.boolean('Varios', required=False),
        'printer_user_id': fields.many2one('res.users', 'Printer User'),
        'payment_ids': fields.function(_compute_lines, method=True, relation='account.move.line', type="many2many", string='Payments'),
        'shop_id': fields.many2one('sale.shop','Shop',readonly=True, states={'draft':[('readonly',False)]}),
        'comments': fields.text('Comentarios'),
        'residual': fields.function(_amount_residual, method=True, digits_compute=dp.get_precision('Account'), string='Residual',
            store={
                'account.debit.note': (lambda self, cr, uid, ids, c={}: ids, ['line_ids','move_id'], 50),
                'account.debit.note.line': (_get_debit_line, ['amount','debit_note_id'], 50),
                'account.move.line': (_get_debit_from_line, None, 50),
                'account.move.reconcile': (_get_debit_from_reconcile, None, 50),
            },
            help="Remaining amount due."),
        'type':fields.selection([
            ('debit_customer','Customer Debit Note'),
            ('debit_supplier','Supplier Debit Note'),
            ('advance_customer','Customer Advance Payment'),
            ('advance_supplier','Supplier Advance Payment'),
        ],'Default Type', readonly=True),
    }
    
    def get_account_period(self,cr,uid,context):
            search_account_period=self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d'))])
            if(search_account_period):
                return search_account_period[0]
            return False
            
            
    _defaults={
        "state": lambda *a: "draft",
        "user_id": lambda obj, cr, uid, context: uid,
        'shop_id': _get_shop,
        "date": lambda *a: time.strftime('%Y-%m-%d'),
        "company_id": lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        "period_id": lambda self, cr, uid, context: self.get_account_period(cr,uid,context) or False,
        'journal_id':_get_journal,
    }
    
        
    def write(self, cr, uid, ids, vals, context={}):
        result = {}
        checked_partial_rec_ids = []
        for debit in self.browse(cr, uid, ids, context=context):
            residual = 0.00
            result[debit.id] = 0.0            
            if debit.move_id and debit.state not in ('draft','cancel'):
                for m in debit.move_id.line_id:
                    if debit.type in ('debit_customer','debit_customer'):
                        if m.account_id.type in ('receivable'):
                            if m.reconcile_partial_id:
                                partial_reconcile_id = m.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                residual += m.amount_residual_currency
                            elif m.reconcile_id:
                                residual += 0.00
                            else:
                                residual += m.amount_residual_currency
                    if debit.type in ('debit_supplier','advance_supplier'):
                        if m.account_id.type in ('payable'):
                            if m.reconcile_partial_id:
                                partial_reconcile_id = m.reconcile_partial_id.id
                                if partial_reconcile_id in checked_partial_rec_ids:
                                    continue
                                checked_partial_rec_ids.append(partial_reconcile_id)
                                residual += m.amount_residual_currency
                            elif m.reconcile_id:
                                residual += 0.00
                            else:
                                residual += m.amount_residual_currency
            vals['residual']=residual
            if round(residual,2) == 0.00 and debit.state=='posted':
                vals['state']='paid'
            elif round(residual,2) != 0.00 and debit.state=='paid':
                vals['state']='posted'                
        return super(account_debit_note, self).write(cr, uid, ids, vals, context)
    
    def onchange_company(self, cr, uid, ids, company=None, type=None, context=None):
        if context is None:
            context = {}
        values={}
        if company:
            if type=='advance_customer':
                values['account_id']= self.pool.get('res.company').browse(cr, uid, company, context).property_account_advance_customer.id or False
            shop_id = self.pool.get('sale.shop').search(cr,uid,[('company_id','=',company)])[0]
            values['shop_id']=shop_id        
            values['journal_id']=self.pool.get('account.journal').search(cr,uid,[('company_id','=',company),('type','=','advances')])[0]
            values['period_id']=self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')),('company_id','=',company)])[0]     
#            if type=='advance_supplier':
#                values['line_ids'] = []
#                if self.pool.get('res.company').browse(cr, uid, company, context).property_account_advance_supplier:
#                    values['line_ids'].append({'account_id':self.pool.get('res.company').browse(cr, uid, company, context).property_account_advance_supplier.id})
        return {'value':values, 'domain':{'shop_id':[('company_id', '=', company)],'journal_id':[('company_id', '=', company)], 'period_id':[('company_id', '=', company)]}}
    
#    def onchange_shop(self, cr, uid, ids, company=None, shop=None, type=None, context=None):
#        if context is None:
#            context = {}
#        values={}
#        box_ids=[]
#        shop_ids = []
#        box_id=[]
#        curr_user = self.pool.get('res.users').browse(cr, uid, [uid, ], context)[0]
#        if curr_user:
#            if not curr_user.box_ids:
#                raise osv.except_osv('Error!', _("Your User doesn't have Cash Box assigned"))
#            for s in curr_user.box_ids:
#                box_ids.append(s.id)
#                if s.shop_id:
#                    shop_ids.append(s.shop_id.id)
#        if shop:
#            box_id=self.pool.get('printer.point').search(cr, uid, [('id', 'in', box_ids),('shop_id', '=', shop)])
#            if not box_id:
#                values['value']={}
#                values['value']['printer_id']=None
#            else:
#                values=self.onchange_cash(cr, uid, ids, company, shop, type, box_id[0], context)
#                values['value']['printer_id']=box_id[0]
#            if type=='debit_sri':
#                values['value']['journal_id'] = self.pool.get('sale.shop').browse(cr, uid, [shop,], context)[0].debit_note_journal_id.id
#        domain={'shop_id':[('id','in', shop_ids)], 'printer_id':[('id','in', box_id)]}
#        values['domain']=domain
#        return values
    
#    def onchange_cash(self, cr, uid, ids, company=None, shop=None, type=None, printer_id=None, context=None):
#        authorization_obj=self.pool.get('sri.authorization')
#        values = {}
#        curr_shop = False
#        journal=None
#        if shop:
#            curr_shop = self.pool.get('sale.shop').browse(cr, uid, [shop,], context)[0]
#        if curr_shop:
#            if type:
#                if type == 'debit_sri':
#                    if curr_shop.debit_note_journal_id:
#                        journal = curr_shop.debit_note_journal_id.sequence_id.code
#                    if printer_id:
#                        values['pre_printer']=self.pool.get('printer.point').browse(cr, uid, printer_id, context).pre_printer
#                        authorization_id = authorization_obj.search(cr, uid, [('printer_id','=',printer_id),('state','=',True),('type','=', journal)])
#                        if authorization_id:
#                            values['authorization'] = authorization_obj.browse(cr, uid, authorization_id,context)[0].name
#                            values['authorization_sri'] = authorization_obj.browse(cr, uid, authorization_id,context)[0].id
#                            values['automatic'] = authorization_obj.browse(cr, uid, authorization_id,context)[0].automatic
#                            if values['automatic']:
#                                values['date'] = time.strftime('%Y-%m-%d')
#                        else:
#                            values['authorization'] = None
#                            values['authorization_sri'] = None
#                            values['automatic'] = False
#        return {'value': values}
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        default={}
        if not partner_id:
            raise osv.except_osv(_('Invalid action!'), _('You must define first a partner!'))
        if context is None:
            context={}
        partner_id=self.pool.get('res.partner').browse(cr, uid, partner_id, context)        
        if partner_id.beneficiary:
#            default['value']['beneficiary'] = partner_id.beneficiary
            default['beneficiary'] = partner_id.beneficiary
        else:
#            default['value']['beneficiary'] = partner_id.name
            default['beneficiary'] = partner_id.name
        return {'value':default}
    
    def onchange_date(self, cr, uid, ids, date, company_id, context=None):
        default={}
        if date:
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date or time.strftime('%Y-%m-%d')),('date_stop','>=',date or time.strftime('%Y-%m-%d')), ('company_id', '=', company_id)])
            default['period_id']= period_ids and period_ids[0] or None 
        return {'value':default}
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
    def create_move_lines(self, cr, uid, note, move_id, name, partner, debit, credit, account,company_id, context={}):
        nd_type = None
        if context.get('is_payment',False):
            reference = note.payments[0].name            
        else:
            reference = note.number
        date_maturity = self.pool.get('account.move').browse(cr,uid,move_id).date
        if context.get('date',False):
            date_maturity = context.get('date',False)            
        if context.get('type','debit_customer'):
            nd_type = context.get('type','debit_customer')
        if nd_type in ('debit_customer','advance_customer','protested','rejected','customer_changed') and debit >0:
            date_maturity = date_maturity
        elif nd_type in ('debit_supplier','advance_supplier') and credit >0:
            date_maturity = date_maturity
        else:
            date_maturity = False
         
        move_line_pool = self.pool.get('account.move.line')
        move_line = {
            'name': name or '/',
            'debit': debit,
            'reference': reference,
            'credit': credit,
            'account_id': account.id,
            'move_id': move_id,
            'journal_id': note.journal_id.id,
            'period_id': note.period_id.id,
            'date_maturity': date_maturity,
            'partner_id': partner.id,
            'company_id': company_id,
            'date': note.date,
            }
        move_line_id= move_line_pool.create(cr, uid, move_line)
        return move_line_id
        
    
    def create_move(self, cr, uid, note, name, ref,context=None):
        move = {'name': name,
                'shop_id': note.shop_id.id,
                'journal_id': note.journal_id.id,
                'partner_id': note.partner_id.id,
                'details':name,
                'date': note.date,
                'ref': ref,
                'period_id': note.period_id.id or False
                }
        return self.pool.get('account.move').create(cr, uid, move)
    
    def confirm_debit_note(self,cr,uid,ids,context={}):
        if context is None:
            context={}
        seq_obj = self.pool.get('ir.sequence')
        total=0
        name=''
        ref=''
        move_line=[]
        for note in self.browse(cr,uid,ids):
            if note.line_ids:                
                reference = note.line_ids[0].name 
            if not note.number:
                number=seq_obj.next_by_id(cr, uid, note.journal_id.sequence_id.id)
            else:
                number=note.number
            if note.type in ("debit_customer","debit_supplier"):
                if note.type == 'debit_customer':
                    ref='N/DEB. CLIENTES POR '+reference
                    name='N/DEB. CLIENTES '+number
                else:
                    ref='N/DEB. PROV. POR '+reference
                    name='N/DEB. PROV. '+number
            if note.type in ("advance_customer","advance_supplier"):
                if note.type == 'advance_customer':
                    ref='ANT. CL. POR  '+reference
                    name = 'ANT. CL. '+number
                else:
                    ref='ANT. PROV. POR '+reference
                    name = 'ANT. PROV. '+number
            move_id= self.create_move(cr, uid, note, name, note.reference or ref, context)
            total=0
            for line in note.line_ids:
                context.get()
                move_line.append(self.create_move_lines(cr, uid, note, move_id, line.name, note.partner_id, line.amount, 0.0, line.account_id,line.account_id.company_id.id, context))
                total+=line.amount
            if total > 0:
                move_line.append(self.create_move_lines(cr, uid, note, move_id, name, note.partner_id, 0.0, total, note.account_id, note.account_id.company_id.id, context))
            if not move_line:
                self.pool.get('account.move').unlink(cr, uid, [move_id], context={})
            else:
                self.pool.get('account.move').post(cr, uid, [move_id], context={})
                self.write(cr, uid, [note.id], {'move_id':move_id})
            self.write(cr, uid, [note.id], {'number':number,'state':'posted','name':name,'reference':ref})
        return True
    
    def cancel_debit_note(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        for note in self.browse(cr, uid, ids, context=context):
            for lines in note.line_ids:
                self.pool.get('account.debit.note.line').write(cr,uid,[lines.id],{'amount':0})
            if note.move_id:
                move_pool.button_cancel(cr, uid, [note.move_id.id], context={})
                move_pool.unlink(cr, uid, [note.move_id.id], context={})
        self.write(cr, uid, ids, {'state':'cancel','total_amout':0.00,'residual':0.00})
        return True
    
    def action_cancel_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'}, context)
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        debit_notes = self.read(cr, uid, ids, ['state'], context=context)
        for debit in debit_notes:
            if debit['state'] != 'draft':
                raise osv.except_osv(_('Invalid action!'), _('You can delete debit Notes in state Draft'))
                #self.write(cr,uid,[debit['id']],{'payments':[(2,debit['id'])]})
        return super(account_debit_note, self).unlink(cr, uid, ids, context)
    
    

    
account_debit_note()

class account_debit_note_line(osv.osv):
    
    _name="account.debit.note.line"
    _columns={
        "debit_note_id": fields.many2one("account.debit.note","Debit Note",ondelete='cascade'),
        "account_id":fields.many2one('account.account','Account'),
        'name':fields.char('Description', size=256, required=True),
        'amount': fields.float('amount', digits_compute=dp.get_precision('Account')),
    }
    
    _defaults={
        "account_id": lambda *a: None,
    }
    
    def onchange_line(self, cr, uid, ids, company=None, type=None, account=None, context=None):
        if context is None:
            context = {}
        values={}
        if not account:
            if type=='advance_supplier':
                values['account_id']= self.pool.get('res.company').browse(cr, uid, company, context).property_account_advance_supplier.id or False
        return {'value':values, 'domain':{'account_id':[('company_id', '=', company)]}}
    
account_debit_note_line()

class account_move_line(osv.osv):
    _inherit="account.move.line"
    _columns={        
        'varios':fields.boolean('Varios', required=False),
    }
account_move_line()