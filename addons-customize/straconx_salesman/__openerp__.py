# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 - 2013 STRACONX S.A. (<http://openerp.straconx.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Salesman for Sale Management in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Salesman',
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'description': """Salesman for Sale Management in Ecuador.
    * Add a objects called Salesmen, Sales Zones ans segment for Comercial Companies.""",
    'depends': ['straconx_states',
                'straconx_partners'
                ],
    'init_xml': [],
    'update_xml': ['views/region_zones_view.xml',
                   'views/salesman_view.xml',
                   'views/res_user_view.xml',
                   'views/res_partner_address.xml',
                   'views/straconx_menu.xml'
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
