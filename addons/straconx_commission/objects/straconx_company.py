# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A (Jorge Valdiviezo) 
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

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
#            'value_commission': fields.float('Value Commission Percentage', digits=(16,2), 
#                                        help="""This field indicate the amount required for receive a commission for sales in the company.
#                                        Please leave a negative value if you want to take into consideration in the payment of commission"""),
            'property_account_commission_sales': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Commission Sales Account Customer',
                method=True,
                view_load=True,
                domain="[('type', '=', 'other')]",),
            }

res_company()
