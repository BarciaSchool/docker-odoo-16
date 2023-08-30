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
from tools.translate import _

class res_company(osv.osv):
    _inherit = "res.company"
    
    def _get_partner_data(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        part_obj = self.pool.get('res.partner')
        for company in self.browse(cr, uid, ids, context=context):
            result[company.id] = {}.fromkeys(field_names, False)
            if company.partner_id:
                partner = part_obj.read(cr, uid, company.partner_id.id, field_names, context=context)
                for field in field_names:
                    result[company.id][field] = partner[field] or False
        return result
    
    def _set_partner_data(self, cr, uid, company_id, name, value, arg, context=None):
        company = self.browse(cr, uid, company_id, context=context)
        if company.partner_id:
            self.pool.get('res.partner').write(cr, uid, [company.partner_id.id], {name: value or False})
        return True
    
    _columns = {
        'property_account_position': fields.function(_get_partner_data, fnct_inv=_set_partner_data, type='many2one', relation='account.fiscal.position', string="Fiscal Position", multi='partner'),
        'resolution_sri':fields.char('Resolution SRI', size=8, required=False),
        'date_resolution': fields.date('Date Resolution'),
        'portal_active':fields.boolean('Los clientes tienen acceso al Portal'),
        'authorizations_ids':fields.one2many('sri.authorization', 'company_id', 'Authorizations', required=False),
    }
    
    _defaults = {
        'portal_active': False
                 }

res_company()