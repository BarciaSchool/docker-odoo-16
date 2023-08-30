# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################


{
    "name": "Partners Module",
    "version": "0.1",
    "author": "STRACONX S.A.",
    "website": "http://openerp.straconx.com",
    "category": "Custom Modules",
    "description": """
    This module management partners. Change customer and suppliers forms.
    It reports current information regarding amount of debt in invoices, orders, etc.
    """,
    "depends": ['crm',
                'purchase_payment',
                'straconx_base_contact',
                'straconx_states',
                # 'straconx_sri',
                ],
    "init_xml": [],
    "demo_xml": [],
    "update_xml": ['views/straconx_partner_generic_view.xml',
                   'views/straconx_partner_account_view.xml',
                   'views/straconx_attributes_view.xml',
                   'views/straconx_menu.xml',
                   'data/straconx_customer_data.xml',
                   'data/actividades.xml',
                   ],
    "active": False,
    "installable": True
}
