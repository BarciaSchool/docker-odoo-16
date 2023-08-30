# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A
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

class account_refund_motive(osv.osv):
    _name = "account.refund.motive"
    _columns = {
        'code': fields.char('code', size=5, required=True),
        'name': fields.char('Motive', size=255, required=True),
        'classification':fields.selection([('sales','Sales'),('purchase','Purchase'),('all','Sales and Purchase')],'Classification', select=True,required=True),
                }
    
    _sql_constraints = [
        ('code_refund_uniq', 'unique (code,name)', 'The code of the motive refund must be unique!')
    ]
account_refund_motive()