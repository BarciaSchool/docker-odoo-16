# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv

class account_journal_type(osv.osv):
    _inherit = "account.journal.type"
    _columns = {
        'sri_type_control':fields.selection([('company','Sequence Company'),('partner','Sequence Partner'), ('company_partner','Company and Partner'),('internal','internal control')],'Control Type SRI', select=True,
                                             help="Indicate if the journal control is based in documents authorizated by SRI or internal control."),
        'sri_type_document':fields.many2one('sri.document.type','Tipo de Documento')
                }
    _defaults={'sri_type_control':'internal',
               }
account_journal_type()