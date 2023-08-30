# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2013-2014 STRACONX S.A 
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


class hr_department(osv.osv):

    _inherit = "hr.department"

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name'], context=context)
        res = []
        for record in reads:
            name = record['name']
            res.append((record['id'], name))
        return res

    _columns = {
        'area_id': fields.many2one('account.area', 'Area', required=True),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'active': fields.boolean('Active'),
        'member_ids': fields.one2many('hr.employee', 'department_id', 'Members', readonly=True, domain=[('unemployee', '!=', True)]),
        }

    _defaults = {'active': True
                 }
hr_department()


class hr_job(osv.osv):

    _inherit = "hr.job"
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        }
    _sql_constraints = [('name_company_uniq', 'unique(name, department_id, company_id)', 'The name of the job position must be unique per company!')]

hr_job()