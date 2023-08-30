# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved	   
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


{
    "name" : "QP Talent Human Information",
    "version" : "1.0",
    "depends" : [
                    "straconx_talent_human",
                    ],
    "author" : "STRACONX S.A.",
    "category": 'Generic Modules/Base',
    "website" : "http://openerp.straconx.com/",
    "description": """Init employee datas""",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
            "data/str_06_areas_contables.xml",
            "data/str_departamentos.xml",
            "data/str_job.xml",
            "data/str_resource.xml",
            "data/str_employee.xml",
            "data/str_contratos.xml",
            "data/str_st_payroll_data.xml",
            "data/str_st_incomes_expenses.xml",
            "data/str_incom_exp_lines.xml"
            ],
    "active": False,
    "installable": False,
}
