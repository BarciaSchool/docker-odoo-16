# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import netsvc
import time
from tools.translate import _

class str_debit_reconcile (osv.osv):
    _name='straconx.debit.reconcile'
    _columns={
              'name':fields.char('Número', size=60),
              'shop_id': fields.many2one('sale.shop','Tienda', required=True, states={'draft':[('readonly',False)]}),
              'company_id': fields.many2one('res.company','Compañía', states={'draft':[('readonly',False)]}),
              'account_id': fields.many2one('account.account','Cuenta', required=True, states={'draft':[('readonly',False)]}),
              'bank_account_id': fields.many2one('res.partner.bank','Cuenta Bancaria', required=True, states={'draft':[('readonly',False)]}),
              'type':fields.selection([
                 ('debit_note','Nota de Débito'),
                 ('deposit','Depósito'),
                 ('credit_note','Nota de crédito')],'Tipo', states={'draft':[('readonly',False)]}),
              'amount':fields.float('Monto', required=True, states={'draft':[('readonly',False)]}),
              "process_date": fields.date("Fecha"), 
              "state": fields.selection([('draft','Borrador'),('cashed','Cobrado')],'Estado', readonly=True),
              'move_id': fields.many2one('account.move','Asiento', states={'draft':[('readonly',False)]}),    
             }
    _defaults={
        "state": lambda *a: "draft",
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'check.book', context=c),
        }
    
    def create(self, cr, uid, vals, context={}):
        vals['state'] = 'cashed'
        return super(str_debit_reconcile, self).create(cr, uid, vals, context)
    
    def approve_reconcile(self, cr, uid, ids, context=None):
        rec_id = self.browse(cr, uid, ids[0])
        journal_obj = self.pool.get('account.journal')
        move_line_pool = self.pool.get('account.move.line')
        name = ''
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', rec_id.process_date or time.strftime('%Y-%m-%d')), ('date_stop', '>=', rec_id.process_date or time.strftime('%Y-%m-%d')), ('company_id', '=', rec_id.company_id.id)])
        if rec_id.type == 'debit_note':
            name = 'NOTA DE DÉBITO'
            journal_id = journal_obj.search(cr, uid, [('type','=','debit_note')])[0]
        else:
            journal_id = journal_obj.search(cr, uid, [('type','=','purchase_refund')])[0]
            if rec_id.type == 'credir_note':
                name = 'NOTA DE CŔEDITO'
            else:
                name = 'DEPÓSITO'
        move = {
            'ref': 'Conciliación ' + rec_id.name,
            'journal_id': journal_id,
            'date': rec_id.process_date,
            'shop_id':rec_id.shop_id.id,
            'period_id':period_ids[0],
            'details':'Conciliación Bancaria por '+name,
            'partner_id': rec_id.company_id.partner_id.id,
            'name': 'Conciliación ' + rec_id.name,
            }
        move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
        if rec_id.type == 'debit_note':
            debit = 0.00
            credit = rec_id.amount
        else:
            debit = rec_id.amount 
            credit = 0.00            
        move_line_pool.create(cr, uid, {
                        'name': 'Conciliación Bancaria por '+name,
                        'debit': debit,
                        'credit':credit,
                        'account_id':  rec_id.account_id.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_ids[0],
                        'partner_id':  rec_id.company_id.partner_id.id,
                        'date':  rec_id.process_date,
                        'company_id': rec_id.company_id.id
                        },context=context)
        rec_id.write({'move_id':move_id, 'state':'cashed'})
        
        return True
str_debit_reconcile()