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
{
    'name': 'Customization for Invoice Management in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Invoices based in rules SRI',
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """Module that allows the customer to give a bonus sales invoice.""",
    'depends': [
                "straconx_sales",
                ],
    'init_xml': [],
    'update_xml': [
                   "views/straconx_invoice_line.xml",
                   "views/straconx_partner.xml",
                   "views/straconx_invoice_pos_view.xml",
                   "views/straconx_view_sales.xml",
                   "views/straconx_view_sale_salesman.xml",  
                   "views/straconx_delivery_view.xml",
                   "wizard/installer.xml",
                   "report/cost_bonus_invoice.xml",
                   "wizard/wizard_report_bonus.xml",
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}