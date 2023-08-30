# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved	   
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

class payment_mode(osv.osv):
    
    def _check_type(self, cr, uid, ids, context=None):
        b=True
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.cash:
                if (obj.check or obj.credit_card or obj.others):
                    b=False
            elif obj.check:
                if (obj.cash or obj.credit_card or obj.others):
                    b=False
            elif obj.credit_card:
                if (obj.cash or obj.check or obj.others):
                    b=False
            elif obj.others:
                if (obj.cash or obj.check or obj.credit_card):
                    b=False
        return b
    
    _inherit="payment.mode"
    _columns = {
                'debit_account_id': fields.many2one('account.account', 'Debit Account', required=False),
                'credit_account_id': fields.many2one('account.account', 'Credit Account', required=False),
                'journal': fields.many2one('account.journal', 'Journal', required=False),
                'account_bank_id': fields.many2one('res.partner.bank', "Bank account",required=False,help='Bank Account for the Payment Mode'),
                'bank_id': fields.many2one('check.book', "Cheque Book", help='Cheque Book for the Payment Mode'),
                'bank_ids': fields.one2many('check.book', 'mode_id', 'Cheque Book'),
                'cash':fields.boolean('Cash', required=False),
                'check':fields.boolean('Check', required=False),
                'deposit':fields.boolean('Depósito', required=False),
                'discount':fields.boolean('Descuento', required=False),
                'credit_card':fields.boolean('Credit Card', required=False),
                'others':fields.boolean('Others', required=False),
                'only_receipt':fields.boolean('Only Receipt', required=False),
                'only_payment':fields.boolean('Only Payment', required=False),
                'pos':fields.boolean('Pagos POS', required=False),
                'mode_withhold':fields.boolean('Retención Fuente', required=False),
                'mode_withhold_vat':fields.boolean('Retención IVA', required=False),
                'required_bank':fields.boolean('Required Bank', required=False),
                'required_seq':fields.boolean('Required Sequence', required=False),
                'required_seq_check':fields.boolean('Required Sequence', required=False),
                'required_document':fields.boolean('Required Document', required=False),
                'required_line_account':fields.boolean('Required Line', required=False),
                'to_deposit':fields.boolean('to Deposit', required=False),
                'credit_notes':fields.boolean('Credit Notes', required=False),
                'debit_notes':fields.boolean('Debit Notes', required=False),                
                'authorization':fields.boolean('Authorization', required=False),
                'default':fields.boolean('default', required=False),
                'type': fields.many2one('payment.type', 'Payment type', required=False, help='Select the Payment Type for the Payment Mode.'),
                'sequence': fields.integer('Sequence'),
                'sri_code': fields.char('Código SRI', size=2, help="Tabla 16 del ATS"),
                'active':fields.boolean('Activo', required=False),
                "discount_employee":fields.boolean("Discount Employee"),
                }
    
    _defaults = {
        'cash': lambda *a: False,
        'check': lambda *a: False,
        'credit_card': lambda *a: False,
        'others': lambda *a: False,
        'required_bank': lambda *a: False,
        'required_document': lambda *a: False,
        'required_seq': lambda *a: False,
        'to_deposit': lambda *a: False,
        'authorization': lambda *a: False,
        'default': lambda *a: False,
        'active': lambda *a: True,
     }
    
    _order = 'sequence, name'
              
#    _constraints = [
#        (_check_type, 'You must select only one type of Payment mode', ['cash','check','credit_card','others']),
#    ]
payment_mode()
