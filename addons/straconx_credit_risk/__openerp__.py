# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved     
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
    "name" : "Credit Risk Module",
    "version" : "0.1",
    "description" : """This module management credit relations. 
    create a customers personalized form, add payments management and reports.
    Adds a new button in the partner form to analyze current state of a partner risk.
    It reports current information regarding amount of debt in invoices, orders, etc.
    It also modifies the workflow of sale orders by adding a new step when partner's risk is exceeded.
    Amount credit code is based in work of NaN for Trod y Avia, S.L.
    """,
    "author" : "STRACONX S.A.",
    "website" : "http://openerp.straconx.com",
    "depends" : [ 
        'account_payment',
        'straconx_account',
        'straconx_states', 
        'straconx_salesman',
        'straconx_partners',
        'straconx_payments',
    ], 
    "category" : "Custom Modules",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        'report/straconx_credit_risk_form.xml',
        'security/straconx_groups_risk.xml',
        'data/cron_sales.xml',
        'wizard/open_risk_window_straconx.xml',
        'views/straconx_partners_risk_view.xml',
        'views/straconx_sales_credit_risk_view.xml',
        'views/straconx_menu.xml',
        'workflow/sale_workflow.xml',
#        'security/ir.model.access.csv',        
    ],
    "active": False,
    "installable": True,
#    'application': True,
}
