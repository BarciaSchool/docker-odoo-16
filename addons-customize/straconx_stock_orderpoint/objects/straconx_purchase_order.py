# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A. 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################
from osv import osv, fields

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _columns = {
              "is_procurement":fields.boolean("Is procurement"),
              }
    _defaults = {
               "is_procurement":False,
               }

purchase_order()