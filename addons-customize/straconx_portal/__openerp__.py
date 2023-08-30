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
    'name' : "Portal",
    'version' : "1.0",
    'depends' : ["straconx_base_synchro"],
    'author' : "OpenERP SA, STRACONX S.A.",
    'category': 'Portal',
    'description': """
This module defines 'portals' to customize the access to your OpenERP database
for external users.

A portal defines customized user menu and access rights for a group of users
(the ones associated to that portal).  It also associates user groups to the
portal users (adding a group in the portal automatically adds it to the portal
users, etc).  That feature is very handy when used in combination with the
module 'share'.
    """,
    'website': 'http://www.openerp.com',
    'images' : ['images/accounts.jpeg'],
    'data': [
        'security/portal_security.xml',
        'data/01_cron_uploads.xml',
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/portal_view.xml',
        'views/res_user_view.xml',
        'wizard/portal_wizard_view.xml',
    ],
    'installable': True,     
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
