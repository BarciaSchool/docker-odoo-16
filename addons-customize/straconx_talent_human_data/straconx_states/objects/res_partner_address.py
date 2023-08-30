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

class res_partner_address(osv.osv): 
    _inherit = "res.partner.address"
    
    def name_get(self, cr, user, ids, context=None):
        if not len(ids):
            return []
        res = []
        if context is None:
            context = {}
        for r in self.read(cr, user, ids, ['zip', 'city', 'partner_id', 'street', 'name']):
            if context.get('contact_display', 'contact')=='partner' and r['partner_id']:
                res.append((r['id'], r['partner_id'][1]))
            else:
                addr = r['name'] or ''
                if r['name']:
                    addr += ' - '
                addr += "%s %s %s" % (r.get('street', '') or '', r.get('zip', '') \
                                    or '', r.get('city', '') or '')
                res.append((r['id'], addr.strip() or '/'))
        return res

    _columns = {
        'location_id': fields.many2one('city.city', 'Location'),
        'phone2':fields.char('Phone 2',size=13),
        'sector': fields.char('Sector',size=150),
        'parish': fields.char('Parish',size=150),
        'zip': fields.related('location_id', 'zipcode', string='zip', type='char', size=64, readonly=True, store=True),
        'city': fields.related('location_id', 'name', string='City', type='char', size=64, readonly=True,store=True),
        'state_id': fields.related('location_id','state_id', type='many2one', relation='res.country.state', string='State', store=True, readonly=True),
        'region_id': fields.related('location_id','state_id','region_id', type='many2one', relation='res.region', string='Region', store=True, readonly=True),
        'country_id': fields.related('location_id','state_id','region_id','country_id', type='many2one', relation='res.country', string='Country', store=True, readonly=True), 
    }
res_partner_address()