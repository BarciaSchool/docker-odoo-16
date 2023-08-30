# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

import time
from osv import osv, fields
from tools.translate import _

class change_pos_box(osv.osv_memory):
    _name = 'change.check'
    _description = 'change Box'

    def _get_default_journal(self, cr, uid, context=None):
        journal_id=self.pool.get('account.journal').search(cr, uid, [('type','=','moves')])
        if not journal_id: 
            return None
        return journal_id[0]
    
    def _get_mode_id(self, cr, uid, context=None):
        shop_id = False
        result = {}
        if context:
            active_id = context.get('active_id', False)
            if active_id:
                shop_id = self.pool.get('account.bank.statement').browse(cr,uid,active_id).shop_id.id
        if not shop_id or not context:
            shop_id = self.pool.get('res.users').browse(cr,uid,uid).shop_id.id
        if shop_id:
            cr.execute('select payment_id from rel_shop_payment rsp left join payment_mode pm on pm.id = rsp.payment_id where shop_id = %s and pm.cash = True and pm.default =True and (pm.petty = False or pm.petty is null)',[shop_id,])
            paids=cr.fetchall()
            if len(paids) >= 1:
                result = paids[0][0]
            else:
                result = []
        return result

    def _get_shop_id(self, cr, uid, context=None):
        shop_id = False
        result = {}
        if context:
            active_id = context.get('active_id', False)
            if active_id:
                shop_id = self.pool.get('account.bank.statement').browse(cr,uid,active_id).shop_id.id
        if not shop_id or not context:
            shop_id = self.pool.get('res.users').browse(cr,uid,uid).shop_id.id
        if shop_id:
            result = shop_id
        else:
            result = []
        return result

    _columns = {
        'name': fields.char('Description', size=32, required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'mode_id': fields.many2one("payment.mode","Type", help="Indicate the mode that go to output the cash"),
        'cheque_id': fields.many2one('account.payments','Cheque'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'bank_account_id': fields.many2one('res.partner.bank','Cuenta Bancaria'),
        'number': fields.char('# Cheque', size=10),
        'amount': fields.float('Monto'),
        'date': fields.date('Date'),
        'ref': fields.char('Ref', size=32),
        'shop_id': fields.many2one('sale.shop', 'Tienda'),
    }
    _defaults = {
         'mode_id': _get_mode_id,
         'journal_id': _get_default_journal,
         'name': _('CANJE DE CHEQUE'),
         'date': time.strftime('%Y-%m-%d'), 
         'shop_id': _get_shop_id,
    }
    
    def onchange_partner(self, cr, uid, ids, partner_id, context={}):
        if context is None:
            context = {}
        res = {}
        bank_obj = self.pool.get('res.partner.bank')
        if not partner_id:
            raise osv.except_osv(_('¡Acción Inválida!'), _('Debe definir un Cliente para continuar'))
        else: 
            bank_ids = bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
            if bank_ids:
                bank_account_id = bank_obj.browse(cr,uid,bank_ids)
            else:
                raise osv.except_osv(_('¡Acción Inválida!'), _('Debe agregar una cuenta corriente del cliente para continuar'))
        res.update({'bank_account_id': bank_account_id[0].id})
        return {'value':res}

    
    def get_out(self, cr, uid, ids, context=None):
        vals = {}
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        move_pool = self.pool.get('account.move')
        shop_pool= self.pool.get('sale.shop')        
        move_line_pool = self.pool.get('account.move.line')
        bank_obj = self.pool.get('account.payments')
        shop_id = False
        period_id = False
        statement_id = False
        statement_key = False        
        external = True
        if context is None:
            context = {}
        if context.get('active_model','change.check')=='account.bank.statement':
            external = False
        for data in  self.browse(cr, uid, ids, context=context):
            if not external:
                statement_id=statement_obj.browse(cr, uid, context.get('active_id'), context=context)
                shop_id = shop_pool.browse(cr,uid,statement_id.shop_id.id)
                statement_key = statement_id.id 
                period_id = statement_id.period_id.id 
                if statement_id.state!='open':
                    raise osv.except_osv(_('Invalid action!'), _('La Caja debe estar Abierta'))
                if (statement_id.balance_start + statement_id.total_entry_encoding - statement_id.total_outlet_encoding) < data.amount:
                    raise osv.except_osv(_('Monto no disponible!'), _('No tiene suficiente dinero en caja para cambiar este cheque'))
            mode_ids=self.pool.get('payment.mode').search(cr,uid,[('check','=',True),('only_receipt','=',True)])
            if mode_ids:
                mode_id = self.pool.get('payment.mode').browse(cr,uid,mode_ids[0])
            else:
                raise osv.except_osv(_('¡Acción Inválida!'), _('Se necesita definir una forma de pago tipo Cheque para continuar'))
            if not shop_id:
                shop_id = shop_pool.browse(cr,uid,data.shop_id.id)     
            if not period_id:
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', data.date), ('date_stop', '>=', data.date), ('company_id', '=', shop_id.company_id.id)])
                if period_ids:
                    period_id = period_ids[0]
            if data.amount >0:
                move_id = move_pool.create(cr, uid, {
                            'name': 'CANJE DE CHEQUE ' or '',
                            'journal_id': data.journal_id.id,
                            'shop_id':shop_id.id,
                            'partner_id': data.partner_id.id,
                            'details': 'CANJE DE CHEQUE',
                            'date': data.date,
                            'ref': 'CANJE DE CHEQUE #' + data.number,
                            'period_id': period_id,
                            })
                cheque_id = bank_obj.create(cr,uid,{
                    'mode_id':mode_id.id,
                    'received_date':data.date,
                    'partner_id':data.partner_id.id,
                    'amount':data.amount,
                    'bank_account_id':data.bank_account_id.id,
                    'bank_id':data.bank_account_id.bank.id,
                    'name': data.number,
                    'move_id': move_id,
                    'required_bank':True,
                    'shop_id':shop_id.id,
                    'state':'hold',
                    'required_document':True})
                cash_id = bank_obj.create(cr,uid,{
                    'mode_id':data.mode_id.id,
                    'received_date':data.date,
                    'partner_id':data.partner_id.id,
                    'amount':data.amount,
                    'bank_account_id':data.bank_account_id.id,
                    'bank_id':data.bank_account_id.bank.id,
                    'name': "EFECTIVO POR CANJE DE CHEQUE #" +data.number,
                    'move_id': move_id,
                    'required_bank':True,
                    'type':'payment',
                    'shop_id':shop_id.id,
                    'required_document':True})
            else:
                raise osv.except_osv(_('¡Acción Inválida!'), _('El valor del cheque debe ser mayor a 0'))
            data.cheque_id = bank_obj.browse(cr,uid,cheque_id)
            data.cash_id = bank_obj.browse(cr,uid,cash_id)
            if not data.cheque_id.mode_id.debit_account_id:
                raise osv.except_osv(_('Invalid Account!'), _('No existe una cuenta de débito para esta transacción'))             
            account_debit=data.cheque_id.mode_id.debit_account_id.id
            account_credit=data.mode_id.debit_account_id.id
            tp='changed'            
            id_move = move_line_pool.create(cr, uid, {
                'name': data.cheque_id.mode_id.name or '/',
                'debit': data.cheque_id.amount,
                'credit': 0,
                'account_id': account_debit,
                'move_id': move_id,
                'journal_id': data.journal_id.id,
                'period_id': period_id,
                'partner_id': data.partner_id.id,
                'date': data.date,
                'reference': 'CANJE DE CHEQUE #' + data.cheque_id.name,
                'shop_id':shop_id.id,
                'statement_id': statement_key
                }, context)
            move_line_pool.create(cr, uid, {
                    'name': data.mode_id.name,
                    'debit': 0,
                    'credit': data.cheque_id.amount,
                    'account_id': account_credit,
                    'move_id': move_id,
                    'journal_id': data.journal_id.id,
                    'period_id': period_id,
                    'partner_id': data.partner_id.id,
                    'date': data.date,
                    'shop_id':shop_id.id,
                    'reference': 'CANJE DE CHEQUE #' + data.cheque_id.name,
                    'statement_id': statement_key
                }, context)
            if statement_id:
                vals= {'ref': 'CANJE DE CHEQUE #' + data.cheque_id.name or '',
                       'statement_id': statement_key,
                       'amount':data.cheque_id.amount,
                       'date':data.date,
                       'partner_id':data.partner_id.id,
                       'account_id':account_debit,
                       'payment_id':data.cheque_id.id,
                       'name':'CANJE DE CHEQUE #' + data.cheque_id.name or '',
                       'type':'customer',
                       'company_id':statement_id.user_id.company_id.id,
                       'move_line_id':id_move,
                       'bk_type': tp
                     }
                statement_line_obj.create(cr, uid, vals, context=context)
                vals2= {'ref': 'SALIDA DE EFECTIVO POR CANJE DE CHEQUE #' + data.cheque_id.name or '',
                       'statement_id': statement_key,
                       'amount':data.cash_id.amount,
                       'date':data.date,
                       'partner_id':data.cheque_id.partner_id.id,
                       'account_id':account_debit,
                       'payment_id':data.cash_id.id,
                       'name':'SALIDA DE EFECTIVO POR CANJE DE CHEQUE #' + data.cheque_id.name or '',
                       'type':'supplier',
                       'company_id':statement_id.user_id.company_id.id,
                       'move_line_id':False,
                       'bk_type': 'supplier'
                     }
                statement_line_obj.create(cr, uid, vals2, context=context)
                statement_obj.write(cr, uid, [statement_id.id], {}, context)
            move_pool.post(cr, uid, [move_id], context=None)
        return {}

change_pos_box()

