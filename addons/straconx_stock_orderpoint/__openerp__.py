# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>).        
#    All Rights Reserved
#
##############################################################################
{
    'name': 'Purchase orders and pickings from minimum stock rules',
    'version': '1.0',
    'category': 'Ecuadorian Location/Logistics management',
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """This module was designed to:
                    * Handle minimum stock rules.
                    * Make purchase orders to a manufacturer if the product is required.
                    * Make supply orders to a central warehouse.""",
    'depends': ['straconx_purchase',
                'straconx_logistics'],
    'init_xml': [],
    'update_xml': ['views/stock_warehouse_orderpoint.xml',
                   "views/stock_warehouse.xml",
                   "views/product_orderpoint.xml",                   
                   "views/delivery_carrier.xml",
                   "wizard/procurement_orderpoint.xml",
                   ],
    'demo_xml': [],
    'test':[],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: