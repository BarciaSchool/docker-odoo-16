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
    'name': 'Straconx System',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """ Solicita cambio de contraseña a los usuarios cuando se han creado.
                    Modificación de vistas predeterminada para ir_module_module""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends': ['base', 'web'],
    'init_xml': [],
    'update_xml': ['data/update_sql.sql',
                   'wizard/straconx_change_password.xml',
                   'views/straconx_ir.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
