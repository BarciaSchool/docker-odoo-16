# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Report Aeroo Generator',
    'version': '1.0',
    'description': """
    This module allows users to define reports of Aeroo for different
    objects such as invoice or sale order.
    It creates the menu to the configuration objects in:
        Configuration / Personalization / Aeroo Reports / Report Configuration
    """,
    'category': 'Aeroo Reporting',
    'author': 'Sistemas ADHOC',
    'website': 'http://www.sistemasadhoc.com.ar/',
    'depends': ['sale', 'account', 'purchase', 'account_voucher', 'delivery',
                'report_aeroo', 'report_aeroo_ooo'],
    'init_xml': [],
    'update_xml': [
        'wizard/product_catalog_wizard.xml',
        'report_configuration_view.xml',
        'account_invoice_view.xml',
        'sale_view.xml',
        'stock_view.xml',
        'account_voucher_view.xml',
        'purchase_view.xml',
        'security/security.xml',],
    'demo_xml': [],
    'test':[],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
