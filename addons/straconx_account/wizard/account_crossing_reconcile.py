# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A
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

import time

from osv import osv, fields
from tools.translate import _

class account_crossing_reconcile(osv.osv_memory):
    _name = 'account.crossing.reconcile'
    _description = 'Crossing Reconcile'
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id)])
        return period_ids and period_ids[0] or None
    
    def _amount(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for wizard in self.browse(cr, uid, ids, context=context):
            result[wizard.id]=wizard.move_line_id[wizard.type_reconcile]
        return result

    _columns = {
        'account_id':fields.many2one('account.account', 'Account of moves', required=False, domain="[('reconcile','=', True)]",),
        'move_line_id':fields.many2one('account.move.line', 'Move line to reconcile', required=False,),
        'move_lines_ids': fields.many2many('account.move.line', 'reconcile_move_line_rel', 'reconcile_id', 'move_line_id', 'Move to Reconcile',domain="[('account_id','=', account_id),('reconcile_id','=', False)]"),
        'partner_id':fields.many2one('res.partner', 'Partner', required=False,),
        'amount': fields.function(_amount, method=True,type="float", string='amount', store=False,),
        'allow_write_off': fields.boolean('Allow write off'),
        'writeoff_acc_id': fields.many2one('account.account', 'Account'),
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'period_id': fields.many2one('account.period', 'Period'),
        'type_reconcile':fields.selection([('debit','Debit'),('credit','Credit'),],'Type reconcile', select=True),
        }

    _defaults = {
        'period_id': _get_period,
        'type_reconcile':'debit',
        }

    def onchange_account(self, cr, uid, ids, account, type_reconcile, context=None):
        res={}
        res['value']={'move_line_id':None, 'move_lines_ids':[]}
        if not (account and type_reconcile):
            res['domain']={'move_line_id':[('id','in',[])]}
            return res
        res['domain']={'move_line_id':[('account_id','=',account),(type_reconcile,'>',0), ('reconcile_id','=', False)]}
        if type_reconcile == 'debit':
            res['domain']['move_lines_ids']=[('account_id','=',account),('credit','>',0), ('reconcile_id','=', False)]
        else:
            res['domain']['move_lines_ids']=[('account_id','=',account),('debit','>',0), ('reconcile_id','=', False)]
        return res
    
    def onchange_move_line(self, cr, uid, ids, move_line_id, type_reconcile, context=None):
        move_line=self.pool.get('account.move.line').browse(cr, uid, move_line_id, context)
        res={'amount':0.0}
        if move_line and type_reconcile:
            res['amount']=move_line[type_reconcile]
        return {'value':res}

    def reconcile(self, cr, uid, ids, context=None):
        move_line_obj = self.pool.get('account.move.line')
        obj_model = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        form = self.browse(cr, uid, ids, context)[0]
        allow_write_off = form.allow_write_off
        line_reconcile = [form.move_line_id.id]
        context['search_shop']=True
        context['partner_id']=form.partner_id and form.partner_id.id or False 
        amount= 0
        for line in form.move_lines_ids:
            line_reconcile.append(line.id)
            amount += line.credit if form.type_reconcile == 'debit' else line.debit
        if allow_write_off:
            if form.writeoff_acc_id:
                account=form.writeoff_acc_id.id
            else:
                account=form.account_id.id
            move_line_obj.reconcile(cr, uid, line_reconcile, 'auto', account, form.period_id.id, form.journal_id.id, context)
        else:
            if not form.move_lines_ids:
                raise osv.except_osv(_('UserError'), _('You must select at least 2 lines to reconcile'))
            if form.move_line_id[form.type_reconcile] != amount:
                raise osv.except_osv(_('UserError'), _('the sum amount of lines moves must be equals to move line selected'))
            context['fy_closing']=True
            move_line_obj.reconcile_partial(cr, uid, line_reconcile, context=context)
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','account_crossing_reconcile_view1')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.crossing.reconcile',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

account_crossing_reconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
