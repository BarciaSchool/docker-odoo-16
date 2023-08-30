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

class res_company(osv.osv):
    _inherit = "res.company"
    
    _columns = {
        'legal_representative_id':fields.many2one('res.partner', 'Legal Representative', required=False),
        'counter_id':fields.many2one('res.partner', 'Counter', required=False),
    }
res_company()


class res_country(osv.osv):
    _inherit = 'res.country'
    _columns = {
        'iso_code': fields.char('ISO Code', size=3),
    }
    
class res_partner(osv. osv):
    _inherit = 'res.partner'
    _columns = {
         'type_reg': fields.selection([('01','Régimen General'),
                                       ('02','Paraíso Fiscal'),
                                       ('03','Régimen fiscal preferente o jurisdicción de menor imposición')],'Tipo de Régimen'),  
                    } 
res_country()