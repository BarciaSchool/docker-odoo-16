# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2013-2014 Jorge Valdiviezo (jorgito2006@gmail.com) All Rights Reserved     
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
    """Override company to add file of query to synchronize"""
    _inherit = "res.company"
    _columns = {        
        'file_synchronize_repository':fields.char(
                        'File synchronize Repository Path', 
                        size=256,
                        help='Local mounted path on OpenERP server where file query to synchronize is stored.'
                    ),
    }    
    
    def get_local_file_synchronize_repository(self, cr, uid, id=None, context=None):
        if id:
            return self.browse(cr, uid, id, context=context).file_synchronize_repository
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.file_synchronize_repository

res_company()
