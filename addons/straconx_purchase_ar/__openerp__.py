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
                "straconx_listprices",
                "straconx_products",
                "straconx_images_link"
                ],
    "init_xml": [],
    'update_xml': [
                   "views/strx_purchase_all_view.xml"
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
