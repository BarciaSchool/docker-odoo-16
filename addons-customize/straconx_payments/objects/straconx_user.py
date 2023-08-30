# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A.   
#              (<http://openerp.straconx.com>). All Rights Reserved
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

import netsvc
from osv import fields, osv
from tools.translate import _

class res_users(osv.osv):
    
    def _check_cashier(self, cr, uid, ids, context=None):
        b=True
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.is_cashier:
                if not (obj.collect or obj.pay):
                    b=False
        return b
    
    _inherit = 'res.users'
    _columns = {
                'is_cashier': fields.boolean('Is cashier?'),
                'collect': fields.boolean('collect'),
                'pay': fields.boolean('pay'),
                'cash_box_default_id':fields.many2one('printer.point', 'Cash Box Default', required=False),
                'maximun_cash_voucher_amount': fields.float("Maximun Cash Voucher" ,help="maximum amount for a cash voucher"),
                }
    _defaults = {
                'is_cashier': lambda *a: False,
                'collect': lambda *a: False,
                'pay': lambda *a: False,
     }
    _constraints = [
        (_check_cashier, 'You must choose if the cashier is collection or payment', ['collect','pay']),]
    
    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'cash_box_default_id':None,
                        'is_cashier':False,
                        'collect':False,
                        'pay':False,
                        })
        return super(res_users, self).copy_data(cr, uid, id, default, context=context)

res_users()