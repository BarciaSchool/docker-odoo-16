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

from osv import osv, fields

class res_partner_address(osv.osv): 
    _inherit = "res.partner.address"
    
    _columns = {
        'collect_assigned': fields.many2one('salesman.salesman', 'Collector Assigned', domain="[('is_collector','=',True)]", ondelete='restrict'),
        'salesman_assigned': fields.many2one('salesman.salesman', 'Salesman Assigned', domain="[('is_seller','=',True)]", ondelete='restrict'),
        'buyer_assigned': fields.many2one('salesman.salesman', 'Buyer Assigned', domain="[('is_buyer','=',True)]",ondelete='restrict'),
    }

res_partner_address()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'salesman_id': fields.related('address', 'salesman_assigned', type='many2one', relation="salesman.salesman", string='Comercial Asesor', store=True),
        'collect_id':fields.related('address', 'collect_assigned', type='many2one', relation="salesman.salesman", string='Dedicated Collector', store=True),
        'buyer_id': fields.related('address', 'buyer_assigned', type='many2one', relation="salesman.salesman", string='Buyer Asesor', store=True),
#        'segment_id': fields.many2one('res.partner.segment', 'Segment'),
#        'segment_category_id':fields.many2one('res.partner.segment.category', 'Segmento Industries Category'),
    }
res_partner()