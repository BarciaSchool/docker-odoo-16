# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
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

class move_type(osv.osv):
    _name = "move.type"
    _columns = {
        'sequence': fields.integer('Seq.'),
        'name':fields.char('Name', size=64, required=True,),
        #'shop_id':fields.many2one('sale.shop', 'Shop', required=False),
        'account_id':fields.many2one('account.account', 'account', required=False),
        'type':fields.selection([('in','Income'),('out','expense')],'type', select=True),
        'register_move':fields.boolean('Register in Move Account?', required=False),
        'required_reference':fields.boolean('Required Reference?', required=False),
        'shop_ids':fields.many2many('sale.shop', 'rel_move_type_shop', 'move_type_id', 'shop_id', 'Shops'),
    }    
    _order = "sequence asc"
move_type()

class invoice_type(osv.osv):
    _name = "invoice.type"
    _columns = {
        'sequence': fields.integer('Seq.'),
        'name':fields.char('Name', size=64, required=True,),
        #'shop_id':fields.many2one('sale.shop', 'Shop', required=False),
        'account_id':fields.many2one('account.account', 'account', required=False),
        'type':fields.selection([('iva','IVA'),('noiva','No IVA')],'type', select=True),
        'register_move':fields.boolean('Register in Move Account?', required=False),
        'account_id_iva':fields.many2one('account.tax', 'Tax', required=False),
        'shop_ids':fields.many2many('sale.shop', 'rel_invoice_type_shop', 'invoice_type_id', 'shop_id', 'Shops'),
    }    
    _order = "sequence asc"
invoice_type()