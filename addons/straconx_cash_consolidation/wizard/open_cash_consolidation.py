# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
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

from osv import fields, osv
from tools.translate import _
import time

class open_cash_consolidation(osv.osv_memory):
    _name = 'open.cash.consolidation'
    _description = 'Open Cash Consolidation'
    
    _columns={
              'shop_id':fields.many2one('sale.shop', 'Shop',),
              'printer_id':fields.many2one('printer.point', 'Printer', domain="[('shop_id', '=', shop_id)]",readonly=True,states={'draft':[('readonly',False)]}),
              'user_id':fields.many2one('res.users', 'User',),
              'date': fields.date('Date'),
              'company_id': fields.many2one('res.company', 'Company', required=True),
              'account_id':fields.many2one('account.account', 'account'),
              'partner_id':fields.many2one('res.partner', 'partner'),
              'journal_id': fields.many2one('account.journal', 'journal'),
              'amount_initial': fields.float('Amount Initial', digits=(16, 2)),
              }
    
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        user=self.pool.get('res.users').browse(cr, uid, uid, context)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','=','cash_consolidation')])
        values={'user_id':uid,
                'company_id':user.company_id.id,
                'date':time.strftime('%Y-%m-%d'),
                'journal_id':journal_ids and journal_ids[0] or None,
                }
        return values
    
    def on_change_user(self, cr, uid, ids, user_id, context=None):
        return self.pool.get('cash.consolidation').on_change_user(cr, uid, ids, user_id, context)
    
    def on_change_shop(self, cr , uid, ids, shop_id, user_id, context=None):
        return self.pool.get('cash.consolidation').on_change_shop(cr, uid, ids, shop_id, user_id, context)
    
    def on_change_company(self, cr, uid, ids, company_id, context=None):
        return self.pool.get('cash.consolidation').on_change_company(cr, uid, ids, company_id, context)

    def open_cash(self, cr, uid, ids, context=None):
        data = {}
        mod_obj = self.pool.get('ir.model.data')
        cash_obj = self.pool.get('cash.consolidation')
        wizard=self.browse(cr, uid,ids[0], context)
        if context is None:
            context = {}
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',wizard.date),('date_stop','>=',wizard.date), ('company_id', '=', wizard.company_id.id)])
        if not period_ids:
            raise osv.except_osv(_('Error !'), _('You must defined a period for this date!')) 
        data.update({'journal_id': wizard.journal_id.id,
                     'company_id': wizard.company_id.id,
                     'user_id': wizard.user_id.id,
                     'shop_id':wizard.shop_id.id,
                     'printer_id':wizard.printer_id.id,
                     'date':wizard.date,
                     'partner_id':wizard.partner_id.id,
                     'account_id':wizard.account_id.id,
                     'period_id': period_ids[0],
                     'amount_initial': wizard.amount_initial,
                     })
#        context.update({'shop_id':wizard.shop_id.id})
        cash_id = cash_obj.create(cr, uid, data, context=context)
        cash_obj.action_open(cr, uid, [cash_id], context)
        tree_res = mod_obj.get_object_reference(cr, uid, 'straconx_cash_consolidation', 'cash_consolidation_tree_view')
        tree_id = tree_res and tree_res[1] or False
        form_res = mod_obj.get_object_reference(cr, uid, 'straconx_cash_consolidation', 'cash_consolidation_form_view')
        form_id = form_res and form_res[1] or False
        search_id = mod_obj.get_object_reference(cr, uid, 'straconx_cash_consolidation', 'cash_consolidation_search_view')
        return {
            'domain': "[('id', '=',"+str(cash_id)+")]",
            'name':'Cash Consolidation',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'search_view_id': search_id and search_id[1] or False ,
            'res_model': 'cash.consolidation',
            'views': [(tree_id, 'tree'),(form_id, 'form')],
            'type': 'ir.actions.act_window'
        }
open_cash_consolidation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
