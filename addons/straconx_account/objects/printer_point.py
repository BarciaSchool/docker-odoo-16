# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv

class printer_point(osv.osv):
    
    _name = 'printer.point' 
    _columns = {
                    'name':fields.char('Name', size=255, required=True), 
                    'shop_id':fields.many2one('sale.shop', 'Shop',ondelete="cascade"),
                    'user_ids':fields.many2many('res.users', 'rel_user_box', 'box_id', 'user_id', 'Users'),
                    'type':fields.boolean('internal')
                }
    _defaults = {'type':False}
        
printer_point()