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
from tools import config
from tools.translate import _

class res_users(osv.osv):
    _inherit = 'res.users'
    
    def _get_partner_data(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        partner_obj = self.pool.get('res.partner')
        for user in self.browse(cr, uid, ids, context=context):
            result[user.id] = {}.fromkeys(field_names, False)
            if user.partner_id:
                partner = partner_obj.read(cr, uid, user.partner_id.id, field_names, context=context)
                for field in field_names:
                    result[user.id][field] = partner[field] or False
        return result
    
    def _set_partner_data(self, cr, uid, user_id, name, value, arg, context=None):
        user = self.browse(cr, uid, user_id, context=context)
        if user.partner_id:
            self.pool.get('res.partner').write(cr, uid, [user.partner_id.id], {name: value or False})
        return True


    _columns = {
        'vat': fields.function(_get_partner_data, fnct_inv=_set_partner_data, type='char', string="vat",size=32, multi='vat'),
        'partner_id':fields.many2one('res.partner', 'Partner', required=False),
        'address_id':fields.many2one('res.partner.address', 'Address', domain="[('partner_id', '=', partner_id)]"),
    }

res_users()