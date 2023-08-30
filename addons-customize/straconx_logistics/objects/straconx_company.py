# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields, osv

class res_company(osv.osv):
    _inherit = "res.company"
    
    _columns = {
        'property_inventory_difference': fields.property( 
                'account.account',
                type='many2one',
                relation='account.account',
                string='Inventory Difference Account',
                method=True,
                view_load=True,
                domain="[('type', '=', 'stock')]",),
    }
    
res_company()