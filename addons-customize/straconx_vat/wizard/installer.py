# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Ecuadorenlinea.net.
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
from osv import fields, osv


class company_installer(osv.osv_memory):

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id and user.company_id.id or False

    def check_ref(self, cr, uid, ids):
        for data in self.browse(cr, uid, ids):
            ref = data.name
            if len(ref) >= 10:
                return True
            else:
                return False

    _name = 'company.installer'
    _inherit = 'res.config.installer'
    _columns = {'name': fields.char('CEDULA/RUC', size=15, required=True),
                'company_id': fields.many2one('res.company', 'Company', required=True),
                }

    _defaults = {'company_id': _default_company}

    _constraints = [(check_ref, 'The number of RUC is incorrect', ['name'])]

    def execute(self, cr, uid, ids, context=None):
        super(company_installer, self).execute(cr, uid, ids, context=context)
        for data in self.browse(cr, uid, ids, context=context):
            self.pool.get('res.partner').write(cr, uid, [data.company_id.partner_id.id], {'vat': data.name}, context=context)
company_installer()
