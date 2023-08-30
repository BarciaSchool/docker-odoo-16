# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#
##############################################################################

{
    'name': 'Pricelists',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """Pricelists customizations""",
    'author': 'STRACONX S.A.',
    'website' : 'http://openerp.straconx.com',
    'depends': [
        'account',
        'stock',
        'sale',
        'straconx_products',
        'straconx_partners',
            ],
    'init_xml': [],
    'update_xml': [
        'views/straconx_discount_views.xml',
        'views/straconx_product.xml',
        'views/straconx_listprices.xml',
        'views/straconx_menu.xml',
        'data/prices_lists.xml',
        'security/ir.model.access.csv',
                   ],
    'demo_xml': [],
    'test':[],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
