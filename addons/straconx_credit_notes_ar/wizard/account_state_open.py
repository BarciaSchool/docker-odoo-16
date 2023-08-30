# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-2013 STRACONX S.A 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import osv

class account_state_open(osv.osv_memory):
    _inherit = 'account.state.open'

    def change_inv_state(self, cr, uid, ids, context=None):
        obj_invoice = self.pool.get('account.invoice')
        reconcile_pool = self.pool.get('account.move.reconcile')
        account_move_obj = self.pool.get('account.move')
        moves=[]
        recs=[]
        if context is None:
            context = {}
        if 'active_ids' in context:
            data_inv = obj_invoice.browse(cr, uid, context['active_ids'][0], context=context)
            if data_inv.reconciled:
                if data_inv.type in ('out_refund','in_refund'):
                    if data_inv.payment_ids:
                        for payment in data_inv.payment_ids:
                            if payment.invoice.id != data_inv.old_invoice_id.id:
                                moves.append(payment.move_id.id)
                            if payment.reconcile_partial_id:
                                recs += [payment.reconcile_partial_id.id]
                            if payment.reconcile_id:
                                recs += [payment.reconcile_id.id]
                    reconcile_pool.unlink(cr, uid, recs)
                    account_move_obj.button_cancel(cr, uid, moves, context=context)
                    account_move_obj.unlink(cr, uid, moves, context=context)
        return super(account_state_open, self).change_inv_state(cr, uid, ids, context)

account_state_open()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: