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

from osv import fields,osv

class res_partner_address(osv.osv):
    
    _inherit = "res.partner.address"
    
    def create(self, cr, uid, values, context=None):
        if not values.get('salesman_assigned',False):
            salesman_ids=self.pool.get('salesman.salesman').search(cr, uid, [('user_id','=',uid)])
            values['salesman_assigned'] = salesman_ids and salesman_ids[0] or None 
        return super(res_partner_address, self).create(cr, uid, values, context)
    
res_partner_address()
