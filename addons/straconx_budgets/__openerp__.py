# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################

{
    'name': 'Budgets Management',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'complexity': "normal",
    'description': """
This module allows accountants to manage analytic and crossovered budgets.
==========================================================================

Once the Master Budgets and the Budgets are defined (in Accounting/Budgets/),
the Project Managers can set the planned amount on each Analytic Account.

The accountant has the possibility to see the total of amount planned for each
Budget and Master Budget in order to ensure the total planned is not
greater/lower than what he planned for this Budget/Master Budget. Each list of
record can also be switched to a graphical view of it.

Three reports are available:
    1. The first is available from a list of Budgets. It gives the spreading, for these Budgets, of the Analytic Accounts per Master Budgets.

    2. The second is a summary of the previous one, it only gives the spreading, for the selected Budgets, of the Analytic Accounts.

    3. The last one is available from the Analytic Chart of Accounts. It gives the spreading, for the selected Analytic Accounts,
     of the Master Budgets per Budgets.

""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/budget.jpeg', 'images/budgetary_position.jpeg'],
    'depends': ['account',
                'sale',
                'hr',
                'straconx_purchase'
                ],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'security/account_budget_security.xml',
        'views/str_account_analytic.xml',
        'views/str_budget_view.xml',
        'workflow/str_budget_workflow.xml',
        'views/str_budget_menu.xml',
        'report/str_budget_report.xml',

    ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
