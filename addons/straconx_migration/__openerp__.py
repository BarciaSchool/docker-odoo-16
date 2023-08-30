# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2009 - present STRACONX S.A. 
#    (http://openerp.straconx.com) All Rights Reserved.
#                       
#    This program is private software.
#
#
##############################################################################

{
    "name" : "Migration Information by related company",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "category" : "Generic Modules /Migration",
    "website" : "http://openerp.straconx.com",
    "description": """
    Migration Information by related company
    """,
    "depends" : [   
                    "product",
                ],
    "init_xml" : [],
    "update_xml" : [
                    'views/str_migration.xml',
                    'views/str_menu.xml',
                    ],
    "demo_xml" : [],
    "installable": True
}
