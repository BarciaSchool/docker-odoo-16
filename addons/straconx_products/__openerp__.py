# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
##############################################################################


{
    'name': 'Product Management for Ecuador',
    'version': '1.0',
    'category': 'Generic Modules/Products',
    'description': """Customization for Product Management in Ecuador.""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends' : [
                    "stock",
                    "knowledge",
#                    "project",
                    "straconx_account",
#                    "label_product",
                ],    
    'init_xml': [],
    'update_xml': [
                    "wizard/product_information.xml",
                    "views/straconx_product_attributes_view.xml",
                    "views/straconx_product_all_view.xml",
                    "views/straconx_product_normal_view.xml",
                    "views/straconx_product_template_sale.xml",
                    "views/straconx_product_category.xml",
                    "views/straconx_menu.xml",          
                    "data/data.xml",
                    "data/colors.xml",
                    "security/ir.model.access.csv",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
