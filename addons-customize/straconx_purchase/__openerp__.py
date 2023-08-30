# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
##############################################################################


{
    'name': 'Purchase and International Trade Management',
    'version': '1.0',
    'category': 'Generic Modules/Purchase',
    'description': """Customization for Purchase Management. Add a object called Buyer, International Trade,
                        Products, Knowledge and modified Purchase workflow for Comercial Companies.""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends': ["purchase_payment",
                "sale",
                # "straconx_invoice",
                # "straconx_sales",
                "straconx_salesman",
                "straconx_listprices",
                "straconx_products",
                # "straconx_logistics",
                "straconx_images_link"
                ],
    "init_xml": ["data/no_dashboard.xml"],
    'update_xml': ["security/straconx_groups_security.xml",
                   "report/straconx_report.xml",
                   "views/straconx_invoice_supplier_view.xml",
                   "views/straconx_purchase_all_view.xml",
                   "views/straconx_partners_view.xml",
                   "views/straconx_purchase_category.xml",
                   "wizard/straconx_purchase_discount.xml",
                   "workflow/straconx_purchase_workflow.xml",
                   "views/straconx_menu.xml",
                   "data/straconx_purchase_data.xml",
                   "data/straconx_email_data.xml",
                   "security/ir.model.access.csv",
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
