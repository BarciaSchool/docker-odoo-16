# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################

{
    'name': 'Projects Budgets Management',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'complexity': "normal",
    'description': """
This module allows accountants to manage analytic and crossovered budgets.
==========================================================================

Once the Master Budgets and the Budgets are defined (in Accounting/Budgets/),
the Project Managers can set the planned amount on each Analytic Account.
""",
    'author': 'STRACONX S.AA',
    'website': 'http://openerp.straconx.com',
    'depends': ['straconx_budgets'
    ],
    'init_xml': [],
    'update_xml': ['views/str_account_phase.xml',
                   'views/str_budget_view.xml',
                   'views/str_budget_menu.xml',
                   'report/str_budget_report.xml',
                   'security/ir.model.access.csv',                   
                   ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
