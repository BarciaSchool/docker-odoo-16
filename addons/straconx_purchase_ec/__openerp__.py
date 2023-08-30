# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
##############################################################################


{
    'name': 'Purchase and International Trade Management for Ecuador',
    'version': '1.0',
    'category': 'Generic Modules/Purchase',
    'description': """Customization for Purchase Management in Ecuador. Add a object called Buyer, International Trade, Products, Knowledge and modified Purchase workflow for Comercial Companies.""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends' : ["straconx_purchase"],    
    "init_xml" : [],
    'update_xml': ["views/straconx_menu.xml",
                   "security/ir.model.access.csv",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
