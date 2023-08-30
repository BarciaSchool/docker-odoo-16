# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

{
        "name" : "Ecuadorian SRI Electronic Invoice",
        "version" : "1.0",
        "author" :  "Straconx S.A.",
        "website" : "http://www.straconx.com/",
        "category" : "Ecuadorian Legislation",
        "description": """SRI Requirements for Electronic Invoice""",
        "depends" : [
                     'straconx_account',
                     'straconx_sri_requirements',
                     'straconx_base_synchro'      
                     ],
        "init_xml" : [],
        "demo_xml" : [],
        "update_xml" : [
                        'report/straconx_electronic_form.xml',                        
                        'data/data.xml',
                        'data/straconx_electronic_mail_template.xml',
                        'views/straconx_contingency.xml',
                        'views/straconx_invoice.xml',
                        'views/straconx_company.xml',                    
                        'views/straconx_delivery.xml',
                        'views/straconx_ir_attachment.xml',
                        'views/straconx_menu.xml',
                        'wizard/installer.xml',
                        'security/ir.model.access.csv'                   
                        ],
        "installable": True
}