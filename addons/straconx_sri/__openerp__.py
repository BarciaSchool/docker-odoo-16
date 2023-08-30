# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

{
    "name" : "Ecuador - authorizations and standards based on the SRI",
    "version" : "1.0",
    "author" : "STRACONX S.A.",
    "category" : "Ecuadorian Location/SRI Rules",
    "website" : "http://openerp.straconx.com",
    "description": """
    Module of Permit authorizations given by the IRS for the generation of tributary documents
    * Define the type Documents, tax sustent and type transaction based in table of Anexo.
    * Define type of partner depending rules SRI
    * Define Authorizations by company.
    * Define Authorizations by supplier for a sequence control based on the SRI.
    """,
    "license" : "GPL-3",
    "depends" : ["account",   
                 "straconx_account",
                ],
    "init_xml" : [],
    "update_xml" : [
                    'data/data_cron.xml',
                    'data/tipo_comprobantes.xml',
                    'data/sri_type_journal.xml',
                    "data/type_company_data.xml",
                    'data/sustento_tributario.xml',
                    'data/tipo_transaccion.xml',
                    'data/fiscal_templates.xml',
                    'wizard/multi_tax_products.xml',
                    'wizard/sri_generate_lines_authorization.xml',
                    'views/account_journal_type_view.xml',
                    'views/res_partner_type_company_view.xml',
                    'views/res_partner_view.xml',
                    'views/res_partner_address_view.xml',
                    'views/sri_authorization.xml',
                    'views/res_company_view.xml',
                    'views/sustento_tributario_view.xml',
                    'views/tipo_comprobante_view.xml',
                    'views/tipo_transaccion_view.xml',
                    'views/stock_warehouse_view.xml',
                    'views/printer_point_view.xml',
                    'views/shop_view.xml',
                    'views/straconx_menu.xml',
                    'security/ir.model.access.csv'
                    ],
    "demo_xml" : [],
    "installable": True
}
