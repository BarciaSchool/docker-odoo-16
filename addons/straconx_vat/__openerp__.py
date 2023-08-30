# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012 STRACONX S.A. (http://openerp.straconx.com) All Rights Reserved.
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
    "name" : "Ecuador - Vat Validator",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "category" : "Ecuadorian Location/Check vat (CI - RUC)",
    "website" : "http://openerp.straconx.com",
    "description": """
    Ecuadorian Vat based validation check SRI
    * Define a field to differentiate if Cedula, RUC or Consumidor Final.
    * Define a wizard to enter the VAT for the company in the configuration.
    """,
    "license" : "GPL-3",
    "depends" : [   
                    "base_vat",
                ],
    "init_xml" : [],
    "update_xml" : [
                    'views/res_partner_view.xml',
                    'wizard/installer.xml',
                    ],
    "demo_xml" : [],
    "installable": True
}
