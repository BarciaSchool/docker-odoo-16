# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
##############################################################################

import time
import netsvc
from datetime import date, datetime, timedelta

from osv import fields, osv
from tools import config
from tools.translate import _

class res_users(osv.osv):
    _inherit = 'res.users'
    
    def _check_max_offer(self,cr,uid,ids):
        b=True
        for user in self.browse(cr, uid, ids):
            if user.is_seller:
                if (user['max_offer'] < 0):
                    b=False
        return b
            
    _columns = {
                #'is_supervisor': fields.boolean('Is Supervisor?'),
                'max_offer': fields.float('% Maximum offer', digits=(16,2)),
                'max_discount': fields.float('% Maximum discount', digits=(16,2)),
                'authorization':fields.char('Authorization', size=20, required=False,),
                'changed_offer': fields.boolean('Permited Change Offer'),
                'changed_discount': fields.boolean('Permited Change Discount'),
                'changed_prices': fields.boolean('Permited Change Prices'),
                }
    
    _constraints = [
        (_check_max_offer,'The percentage maximum Offer must be a positive number',['max_offer'])]

    def _get_default_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        company_id = False
        proxy = self.pool.get('multi_company.default')
        user = self.browse(cr, uid, uid, context=context)
        if proxy.browse(cr, uid, uid, context):
            for rule in proxy.browse(cr, uid, uid, context):
                if eval(rule.expression, {'context': context, 'user': user}):
                    company_id = rule.company_dest_id.id
        if user and not company_id:
            company_id = user.company_id.id
        shop_obj = self.pool.get('sale.shop')
        shop_ids = shop_obj.search(cr,uid,[('headquarter','=',True),('company_id','=',company_id)]) 
        if shop_ids:
            return shop_ids and shop_ids[0]
        else:
            return[]
        
    _defaults = {
            'shop_id':_get_default_shop
                 }
        
    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
                        'max_offer': 0, 
                        'authorization': None, 
                        })
        return super(res_users, self).copy_data(cr, uid, id, default, context=context)
    
res_users()
