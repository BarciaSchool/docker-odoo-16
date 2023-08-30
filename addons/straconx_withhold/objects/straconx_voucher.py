# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
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

from osv import fields,osv
from tools.translate import _
import netsvc

class account_voucher(osv.osv):
    _inherit = "account.voucher"
    _columns = {
                'withhold_ids':fields.one2many('account.withhold', 'voucher_id', 'Withhold'), 
                }
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date=None, context=None):
        if context is None:
            context={}
        default= super(account_voucher,self).onchange_partner_id(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context)
        if context.get('invoice_id', False):
#            if ttype != 'payment':
#                withhold_ids=self.pool.get('account.withhold').search(cr, uid, [('invoice_id.partner_id.id','=',partner_id),('transaction_type','=','sale'),('state','=','draft')])
#            else:
#                withhold_ids=self.pool.get('account.withhold').search(cr, uid, [('invoice_id.partner_id.id','=',partner_id),('transaction_type','=','purchase'),('print_status','not in',[('printed')])])
#            default['value']['withhold_ids']=withhold_ids
            invoice=self.pool.get('account.invoice').browse(cr, uid, context.get('invoice_id', False), context)
            if invoice and invoice.origin_transaction <>'international' and invoice.withhold_id:
                default['value']['withhold_ids']=invoice.withhold_id and [invoice.withhold_id.id] 
        return default
    
    def action_move_line_create(self, cr, uid, ids, context=None):
        res= super(account_voucher,self).action_move_line_create(cr, uid, ids, context)
        wf_service = netsvc.LocalService("workflow")
        for voucher in self.browse(cr, uid, ids):
            if voucher.withhold_ids:
                for ret in voucher.withhold_ids:
                    wf_service.trg_validate(uid, 'account.withhold', ret.id, 'button_approve', cr)
        return res
    
#     def cancel_voucher(self, cr, uid, ids, context=None):
#         res = super(account_voucher, self).cancel_voucher(cr, uid, ids, context=context)
#         wf_service = netsvc.LocalService("workflow")
#         invoice=[]
#         withhold=[]
#         for voucher in self.browse(cr, uid, ids, context=context):
#             for ret in voucher.withhold_ids:
#                 wf_service.trg_validate(uid, 'account.withhold', ret.id, 'button_annulled', cr)
#            invoice = [line.move_line_id.invoice.id for line in voucher.line_ids if line.amount >0 and line.move_line_id.invoice]
#            invoice1=list(set(invoice))
#            for inv in self.pool.get('account.invoice').browse(cr, uid, invoice1, context):
#                for ret in inv.withhold_ids:
#                    if ret.state == 'approved':
#                        wf_service.trg_validate(uid, 'account.withhold', ret.id, 'button_annulled', cr)
#        return res
    
    def action_cancel_draft(self, cr, uid, ids, context=None):
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.withhold_ids:
                for ret in voucher.withhold_ids:
                    self.pool.get('account.withhold').button_set_draft(cr, uid, [ret.id,], context)
        return super(account_voucher, self).action_cancel_draft(cr, uid, ids, context=context)
    
account_voucher()
