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
    'name': 'Straconx Control',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """Control Access for STRACONX's Customers""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends': ['base', 'web'],
    'init_xml': [],
    'update_xml': ['wizard/straconx_control_credit.xml',
                   'data/str.xml'],
    'demo_xml': [],
    'auto_install': False,
    'installable': True,
    'active': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
