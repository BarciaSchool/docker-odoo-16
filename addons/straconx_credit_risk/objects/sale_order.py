# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Albert Cervera i Areny (http://www.nan-tic.com). All Rights Reserved
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

from osv import osv, fields
import datetime
from tools.translate import _
import time


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'

    def _amount_invoiced(self, cr, uid, ids, field_name, arg, context):
        result = {}
        for line in self.browse(cr, uid, ids, context):
            # Calculate invoiced amount with taxes included.
            # Note that if a line is only partially invoiced we consider
            # the invoiced amount 0. 
            # The problem is we can't easily know if the user changed amounts
            # once the invoice was created
            if line.invoiced:
                result[line.id] = line.price_subtotal + self._tax_amount(cr, uid, line)
            else:
                result[line.id] = 0.0
        return result

    def _tax_amount(self, cr, uid, line):
        val = 0.0
        for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_uom_qty, line.order_id.partner_invoice_id.id, line.product_id, line.order_id.partner_id):
            val += c['amount']
        return val

    _columns = {
        'amount_invoiced': fields.function(_amount_invoiced, method=True, string='Invoiced Amount', type='float'),
    }
sale_order_line()

class sale_order(osv.osv):
    _inherit = 'sale.order'
        
    def verify_state(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids):
            if o.partner_id.estado_id:
                if o.partner_id.estado_id.shortcut == 'Susp':
                    raise osv.except_osv('Error!', _('This partner has suspended. Please, talk with credit official'))
            segmento_ids=self.pool.get('res.partner.segmento').search(cr, uid, [('is_default','=',True)])
            segmento=segmento_ids and segmento_ids[0] or None
            if not o.segmento_id:
                return False 
            elif o.partner_id.available_risk - o.amount_total >= 0.0 or o.segmento_id.id == segmento:
                return True
            elif o.partner_id.available_risk - o.amount_total < 0.0:
                return False

    def action_denied(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'credit_denied', 'date_denied': time.strftime('%Y-%m-%d %H:%M:%S')})
        for o in self.browse(cr, uid, ids):
            message = _("The quotation '%s' has been denied for credit risk.") % (o.name,)
            self.log(cr, uid, o.id, message)
        return True
        
    def _amount_invoiced(self, cr, uid, ids, field_name, arg, context):
        result = {}
        for order in self.browse(cr, uid, ids, context):
            if order.invoiced:
                amount = order.amount_total
            else:
                amount = 0.0
                for line in order.order_line:
                    amount += line.amount_invoiced
            result[order.id] = amount
        return result
    
    def onchange_partner_id(self, cr, uid, ids, part,context=None):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part)
        if part:
            part = self.pool.get('res.partner').browse(cr, uid, part)
            warning={}
            result['value']['estado_id'] = part.estado_id and part.estado_id.id or None
            if part.estado_id.shortcut == 'Susp':
    #            raise osv.except_osv('Error!', _('This partner has suspended. Please, talk with credit official'))        
                warning = {
                    'title': _('Suspend Partner'),
                    'message': _('This partner has suspend for due invoices. Please, talk with credit department.')
                }
    #            return {'value': val, 'warning':warning}
    #        return {'type': 'ir.actions.act_window_close'}
            
            if part.available_risk < 0.0:
                warning = {
                    'title': _('Credit Limit Exceeded'),
                    'message': _('Warning: Credit Limit Exceeded.\n\nThis partner has a credit limit of %(limit).2f and already has a debt of %(debt).2f.') % {
                        'limit': part.credit_limit,
                        'debt': part.total_debt,
                    }
                }
            if part.pending_amount < 0.0:
                warning = {
                    'title': _('Invoice Dues'),
                    'message': _('Warning: Invoices Dues.\n\nThis partner has a invoices dues of %(limit).2f over a debt of %(debt).2f.') % {
                        'limit': part.pending_amount,
                        'debt': part.total_debt,
                    }
                }
            if part.protested_cheques < 0.0:
                warning = {
                    'title': _('Protested Cheques'),
                    'message': _('Warning: Protested Cheques.\n\nThis partner has a Protested Cheques of %(limit).2f over a debt of %(debt).2f.') % {
                        'limit': part.circulating_amount,
                        'debt': part.total_debt,
                    }
                }        
            result['warning']=warning
        return result

    _columns = {
        'amount_invoiced': fields.function(_amount_invoiced, method=True, string='Invoiced Amount', type='float'),
        'date_denied': fields.datetime('Ordered Date', readonly=True, select=True,),
        'note_denied': fields.text('Description Denied',readonly=True ,states={'wait_risk': [('readonly', False)]}),
        'estado_id': fields.many2one('res.partner.estado', 'Credit State', readonly=True ,states={'draft': [('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Quotation'),
            ('waiting_date', 'Waiting Schedule'),
            ('manual', 'Manual In Progress'),
            ('progress', 'In Progress'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ('expired', 'Expired'),
            ('cancel', 'Cancelled'),
            ('credit_denied', 'Credit Denied'),
            ('wait_risk', 'Waiting Risk Approval'),
            ],'Order State', readonly=True, help="Gives the state of the quotation or sales order. \nThe exception state is automatically set when a cancel operation occurs in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception). \nThe 'Waiting Schedule' state is set when the invoice is confirmed but waiting for the scheduler to run on the date 'Ordered Date'.", select=True),
    }
    
    def expired_process_all(self, cr, uid, context=None):
        camp_obj = self.pool.get('sale.order')
        camp_ids = camp_obj.search(cr, uid, [('state','=','draft')], context=context)
        for camp in camp_obj.browse(cr, uid, camp_ids, context=context):
            if camp.is_backorder:
                continue
            if camp.date_valid < time.strftime('%Y-%m-%d'):
                camp.write({'state':'expired','authorized':True,'verify':False,'wizard_auth':False})
        return True
sale_order()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
