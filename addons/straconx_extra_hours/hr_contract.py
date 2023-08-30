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
import netsvc
import timeutils as tu

logger = netsvc.Logger()

class hr_contract(osv.osv):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = "hr.contract"
    _columns = {
        'turn_id' : fields.many2one('resource.calendar', 'Turn', select=True, required=False),
	'working_hours_per_day' : fields.integer('Working Hours Per Day'),
        'sequence': fields.integer('Sequence'),
        'department_id' : fields.many2one('hr.department', 'Department', select=True, required=False),
    }

    _defaults = {
	'sequence': lambda *a: 1,
	}

    def get_turn(self, cr, uid, ids, date, context=None):
        res = {}
	if isinstance(date, str):
            date = tu.dt(date)
        for cont in self.browse(cr, uid, ids):
            if (tu.d(cont.date_start) <= date and
                (cont.date_end == False or date <= tu.d(cont.date_end))):
                    ts = filter(lambda i:
                        i.dayofweek == str(date.weekday()) or i.dayofweek == '',
                                           cont.turn_id.timesheet_id)
                    if len(ts) == 1:
                        ddate = tu.datetime.combine(date.date(), tu.time(0))
                        res[cont.id] = (ddate +
                                        tu.timedelta(hours=ts[0].hour_from),
                                        ddate +
                                        tu.timedelta(hours=
                                        24 * (ts[0].hour_from >
                                              ts[0].hour_to) + ts[0].hour_to))
                    elif len(ts) > 1:
                        raise RuntimeError("More than one turn enabled at same time. See Timesheet line.")
                    else:
                        res[cont.id] = False
            else:
                res[cont.id] = False
        return res
hr_contract()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
