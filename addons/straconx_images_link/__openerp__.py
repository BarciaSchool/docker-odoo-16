# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A.  
#              (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################
{
    'name': 'To record the image of the products as a link.',
    'version': '1.0',
    'category':'Added functionality - Product Extension',
    'description': """This module is an adaptation of product_images_olbs, allows:
* Create a repository for images.
* Record the images as a link.
* Migrate the images recorded in a database repository and create your own link.""",
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'depends': [
                "product_images_olbs",
                'straconx_products',
                ],
    'init_xml': [],
    'update_xml': [ 'views/product_images.xml',
                    'views/straconx_product_knowledge_view.xml',
				    'wizard/installer.xml',
                    'security/ir.model.access.csv'
                   ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
