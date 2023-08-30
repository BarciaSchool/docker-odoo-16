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

class region_zone(osv.osv):
    _name = 'res.region.zone'
    _columns = {
        'region_id': fields.many2one('res.region', 'region',required=True),
        'name': fields.char('Zone Name', size=64,required=True),
        'code': fields.char('Zone Code', size=10,help='The zone code in max ten chars.\n', required=True),
    }
    
    _order = 'name'
    
    def name_search(self, cr, user, name='', args=None, operator='ilike',
            context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, user, [('name', operator, name)] + args,
                    limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('code', 'ilike', name)] + args, 
                limit=limit,context=context)
        return self.name_get(cr, user, ids, context)

    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the zone must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the zone must be unique !')
    ]

region_zone()
