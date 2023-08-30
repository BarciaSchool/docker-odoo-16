# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
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


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=False),
        'discount_employee': fields.boolean('discount', required=False),
    }

    def product_id_change(self, cr, uid, ids, product=False, uom=False, qty=0, name=False, type='out_invoice', partner_id=False,fposition_id=False, price_unit=0, address_invoice_id=False, currency_id=False, context=False, company_id=False,discount=0, offer=0, shop_id=False,order_id=False, order_line=False):

        result = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id,price_unit, address_invoice_id, currency_id, context, company_id, discount,offer, shop_id)

        employee_obj = self.pool.get('hr.employee')
        department_id = False
        if context:
            active_id = context.get('active_id', False)
        else:
            active_id = False
        if active_id:
            invoice_id = self.pool.get('account.invoice').browse(cr, uid, active_id)
            if type in ('out_invoice', 'out_refund'):
                user_vat = invoice_id.salesman_id.user_id.vat
                user_vat_ids = employee_obj.search(cr, uid, [('vat', '=', user_vat)])
                if user_vat:
                    employee_ids = employee_obj.search(cr, uid, [('vat', '=', user_vat[0])])
                    if employee_ids:
                        department_id = employee_obj.browse(cr, uid, employee_ids[0]).department_id.id
            else:
                if self.browse(cr, uid, ids[-1]).employee_id:
                    department_id = self.browse(cr, uid, ids[-1]).employee_id.department_id.id
            result['value']['department_id'] = department_id
        return result

    def move_line_get_item(self, cr, uid, line, context=None):
        if line.invoice_id.type in ('out_invoice', 'out_refund'):
            offer_total = line.offer_value_total
        else:
            offer_total = 0
        return {'type': 'src',
                'name': line.name[:64],
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'offer_value_total': offer_total,
                'price': line.price_subtotal,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uos_id': line.uos_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'taxes': line.invoice_line_tax_id,
                'employee_id': line.employee_id and line.employee_id.id or None,
                }

account_invoice_line()
