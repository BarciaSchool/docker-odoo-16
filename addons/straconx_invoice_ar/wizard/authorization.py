# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2011-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
#
##############################################################################

from tools.translate import _
from osv import fields, osv
import time


class authorization(osv.osv_memory):

    _inherit = 'wizard.authorization'

    def button_validate(self, cr, uid, ids, context=None):
        res = super(authorization, self).button_validate(cr, uid, ids, context)
        lines_ids = False
        verify = False
        if res:
            if context.get('supervisor_id', False):
                supervisor_id = context.get('supervisor_id', False)
            if context.get('active_model', None) == 'account.invoice':
                lines_ids = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id', '=', context['active_id'])])
            if lines_ids:
                self.pool.get(context['active_model']+'.line').write(cr, uid, lines_ids, {'authorized': True}, context)
                self.pool.get(context['active_model']).write(cr, uid, [context['active_id']], {'authorized': True, 'wizard_auth': True,
                                                                                               'supervisor_id': supervisor_id,
                                                                                               'date_authorized': time.strftime('%Y-%m-%d %H:%M:%S')},
                                                             context)
            if context.get('draft_invoice', False):
                if context.get('active_id', False):
                    invoice_id = context.get('active_id', False)
                    verify = self.pool.get('account.invoice').action_open_draft(cr, supervisor_id, [invoice_id], context)
            if context.get('cancel_invoice', False):
                if context.get('active_id', False):
                    invoice_id = context.get('active_id', False)
                    self.pool.get('account.invoice').action_open_draft(cr, supervisor_id, [invoice_id], context)
                    verify = self.pool.get('account.invoice').action_cancel(cr, supervisor_id, [invoice_id], context)
            if verify:
                return {'type': 'ir.actions.act_window_close'}
            return True
authorization()