# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

class users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'
    
    _columns = {
                'printer_point_ids':fields.many2many('printer.point', 'rel_user_box', 'user_id', 'box_id', 'boxes'),
                'shop_id':fields.many2one('sale.shop', 'Shop'),
                'old_auth':fields.boolean('Allows entry of expired authorizations?'),
                }

users()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
