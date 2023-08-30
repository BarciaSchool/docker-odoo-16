# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010 - present  STRACONX S.A.
#
##############################################################################


{
    'name': 'Audit Trail',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module lets administrator track every user operation on all the objects of the system.
===========================================================================================

The administrator can subscribe to rules for read, write and
delete on objects and can check logs.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [
        'wizard/audittrail_view_log_view.xml',
        'views/audittrail_view.xml',
        'views/audittrail_menu.xml',        
        'security/ir.model.access.csv',
        'security/audittrail_security.xml',
        'data/audittrail_data.xml'
    ],
    'installable': True,
    'auto_install': False,
    'images': ['images/audittrail1.jpeg','images/audittrail2.jpeg','images/audittrail3.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
