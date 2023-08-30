# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2012-2013 STRACONX S.A.
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

from osv import osv, fields


class Country(osv.osv):
    _inherit = 'res.country'
    _columns = {
        'regions_ids': fields.one2many('res.region', 'country_id', 'Regions'),
    }
Country()


class region(osv.osv):
    _name = 'res.region'
    _description = 'region'
    _columns = {
        'name': fields.char('region Name', size=64,
                            help='The full name of the region.', required=True, translate=True),
        'code': fields.char('region Code', size=5,
                            help='The Region code in two chars.\n'
                            'You can use this field for quick search.', required=True),
        'country_id': fields.many2one('res.country', 'Country', required=False),
        'states_ids': fields.one2many('res.country.state', 'region_id', 'States'),
    }

    _order = 'name'

    _sql_constraints = [
        ('name_uniq', 'unique (name,country_id)',
            'The name of the region must be unique by country!'),
        ('code_uniq', 'unique (code,country_id)',
            'The code of the region must be unique by country!')
    ]

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = False
        if len(name) == 2:
            ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                              limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)] + args,
                              limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

region()


class CountryState(osv.osv):
    _inherit = 'res.country.state'
    _columns = {
        'city_ids': fields.one2many('city.city', 'state_id', 'Cities'),
        'region_id': fields.many2one('res.region', 'Region'),
        'country_id': fields.related('region_id', 'country_id', type='many2one', relation='res.country', string='Country', store=True, readonly=True),
    }
CountryState()


class city(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        res = []
        for line in self.browse(cr, uid, ids):
            state = line.state_id.name
            region = line.state_id.region_id.name
            country = line.state_id.country_id.name
            loc = "%s, %s, %s, %s" % (line.name, state, region, country)
            location = loc.upper()
            res.append((line['id'], location))
        return res

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        res = super(city, self).search(cr, uid, args, offset, limit, order, context, count)
        if not res and args:
            args = [('zipcode', 'ilike', args[0][2])]
            res = super(city, self).search(cr, uid, args, offset, limit, order, context, count)
        return res

    _name = 'city.city'
    _description = 'City'
    _columns = {
        'zipcode': fields.char('ZIP', size=64, required=True, select=1),
        'name': fields.char('City', size=64, required=True, select=1),
        'state_id': fields.many2one('res.country.state', 'State', required=True, select=1),
    }
city()