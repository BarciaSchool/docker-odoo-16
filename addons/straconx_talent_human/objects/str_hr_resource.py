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
from tools.translate import _

class resource_calendar_attendance(osv.osv):
    _inherit = "resource.calendar.attendance"
    
    def _check_hours(self,cr,uid,ids):
        b=True
        for resource in self.browse(cr, uid, ids):
            hour = round(resource.hour_from, 2)
            if hour < 0 or hour > 23.98:
                b=False
            hour = round(resource.hour_to, 2)
            if hour < 0 or hour > 23.98:
                b=False
        return b
    
    _constraints = [(_check_hours,'the hours entered is incorrect, please check',['hour_from','hour_to'])]
resource_calendar_attendance()