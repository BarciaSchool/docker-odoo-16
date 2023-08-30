# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution   
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2010-2011 STRACONX S.A. (<http://openerp.straconx.com>). All Rights Reserved
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

class res_company(osv.osv): 
    _inherit = "res.company"
    
    def _get_address_data(self, cr, uid, ids, field_names, arg, context=None):
        return super(res_company,self)._get_address_data(cr, uid, ids, field_names, arg, context)
    
    def _set_address_data(self, cr, uid, company_id, name, value, arg, context=None):
        return super(res_company,self)._set_address_data(cr, uid, company_id, name, value, arg, context)

    _columns = {
        'region_id': fields.function(_get_address_data, fnct_inv=_set_address_data, type='many2one', domain="[('country_id', '=', country_id)]", relation='res.region', string="Region", multi='address'),
        'state_id': fields.function(_get_address_data, fnct_inv=_set_address_data, type='many2one', domain="[('region_id', '=', region_id)]", relation='res.country.state', string="Fed. State", multi='address'),
        'location_id': fields.function(_get_address_data, fnct_inv=_set_address_data, type='many2one', domain="[('state_id', '=', state_id)]", relation='city.city', string="City", multi='address'),
        'zip': fields.related('location_id', 'zipcode', string='zip', type='char', size=64, readonly=True, store=True),
        'city': fields.related('location_id', 'name', string='City', type='char', size=64, readonly=True,store=True),
    }
res_company()