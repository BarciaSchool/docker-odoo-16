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

from osv import fields, osv

class stock_warehouse(osv.osv): 
    _inherit = "stock.warehouse"

    _columns = {
                'partner_id': fields.related('company_id','partner_id', type='many2one', relation='res.partner', string='Partner', store=True),
                'partner_address_id':fields.many2one('res.partner.address', 'Address', required=False, domain="[('partner_id', '=', partner_id)]"),
                }
    
    def onchange_company(self, cr, uid, ids, company_id=None, context={}):
        result={'value':{}}
        if company_id:
            result['value']['partner_id']= self.pool.get('res.company').browse(cr, uid, company_id, context).partner_id.id
        return result
stock_warehouse()