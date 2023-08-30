# -*- encoding: utf-8 -*-
##############################################################################
#
#    Clock Reader for OpenERP
#    Copyright (C) 2004-2009 Moldeo Interactive CT
#    (<http://www.moldeointeractive.com.ar>). All Rights Reserved
#    $Id$
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
from interface import Interface
import netsvc
import timeutils as tu
from tools.translate import _
from tools.sql import drop_view_if_exists

logger = netsvc.Logger()

class hr_holidays(osv.osv):
    _inherit = "hr.holidays"
    _name = "hr.holidays"

    def onchange_hr_aa_const_or_null(self, cr, uid, ids, name, default, value):
        # I need setup the employee on an instance creation but I dont know how
        # to setup null.
        #val = {}
        #if value:
        #    val = { name: default }
        val = { name: default }
        return { 'value': val }

    def onchange_hr_aa_dates(self, cr, uid, ids, field,
                             date_from, date_to,
                             newdate_from, newdate_to):
        val = {}
	import pdb;pdb.set_trace()
        newdate_from = newdate_from or date_from
        newdate_to = newdate_to or date_to
        if newdate_to < date_from:
            newdate_to = date_from
        if date_to < newdate_from:
            newdate_from = date_to
        if newdate_from > newdate_to and field=='date_from':
            newdate_from = newdate_to
        if newdate_from > newdate_to and field=='date_to':
            newdate_to = newdate_from
        val['date_from'] = newdate_from
        val['date_to'] = newdate_to
        return { 'value': val }

    _defaults = {
        'employee_id': lambda self, cr, uid, context : context['employee_id'] if context and 'employee_id' in context else None,
        'date_from': lambda self, cr, uid, context : context['date_from'] if context and 'date_from' in context else None,
        'date_to': lambda self, cr, uid, context : context['date_to'] if context and 'date_to' in context else None,
    }
hr_holidays()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
