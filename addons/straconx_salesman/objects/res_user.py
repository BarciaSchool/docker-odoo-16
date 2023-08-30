# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
##############################################################################

from osv import fields, osv

class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
                'is_seller': fields.boolean('Is Seller?'),
                'is_buyer': fields.boolean('Is Buyer?'),
                'is_collector':fields.boolean('Is Collector?'),
                'is_manager': fields.boolean('Is manager?'),
                'is_driver': fields.boolean('Is driver?'),
                'is_supervisor': fields.boolean('Is Supervisor?'),
                'is_driver': fields.boolean('Is driver?'),
                'is_warehouse_user': fields.boolean('Is Warehouse User?'),
                }
    
    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'is_seller': False, 
                        'is_buyer': False, 
                        'is_collector': False,
                        'is_manager': False,
                        'is_supervisor': False,
                        })
        return super(res_users, self).copy_data(cr, uid, id, default, context=context)
res_users()
