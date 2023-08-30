# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################



from osv import fields,osv

class tipo_comprobante(osv.osv):
    
    _name = 'sri.document.type'
    
    _columns = {
                'code':fields.char('Code', size=4, required=True,),
                'name':fields.char('Name', size=255, required=True,),
                    }
    
    _sql_constraints = [
        ('code_uniq', 'unique (code)',
            'The code of document type must be unique!'),
    ]
    
    _order = "code"