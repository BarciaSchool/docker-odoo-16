##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
#
##############################################################################

{
        "name" : "Ecuadorian Human Resources",
        "version" : "1.0.106",
        "author" : "STRACONX S.A.",
        "website" : "http://openerp.straconx.com",
        "category" : "Base",
        "description": """ """,
        "depends" : ['account',
                     'hr',
                     'straconx_talent_human',
                     'straconx_budgets_projects',
                     'straconx_budgets',

                     ],
        "init_xml" : [
                                          
                      ],
        "demo_xml" : [],
        "update_xml" : ['views/hr_contract_budgets.xml'
                   
                        ],
        "installable": True,
        'active': False,
}
