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

class hr_aa_attendance_waj_action(osv.osv):
    _name = "hr.aa.attendance_waj.action"
    _description = "Attendances without associated journal"
    _columns = {
        'name': fields.many2one('hr.attendance', 'Attendance', select=True, readonly=True),
        'move_to': fields.selection([('next', 'Next'),('none', 'No action'),('prev', 'Previous')], 'Move to')
    }
hr_aa_attendance_waj_action()

class hr_aa_attendance_waj(osv.osv):
    _name = "hr.aa.attendance_waj"
    _description = "Attendances without associated journal"
    _auto = False
    _columns = {
        'name': fields.datetime('Date', select=True, readonly=True),
        'action' : fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'),('action','Action')], 'Action', readonly=True),
        'action_desc' : fields.many2one("hr.action.reason", "Action reason", domain="[('action_type', '=', action)]", readonly=True),
        'employee_id' : fields.many2one('hr.employee', 'Employee', readonly=True, select=True),
        'prev_journal_id' : fields.many2one('hr.aa.journal', 'Previous Journal', readonly=True, select=True),
        'next_journal_id' : fields.many2one('hr.aa.journal', 'Next Journal', readonly=True, select=True),
        'move_to': fields.selection([('next', 'Next'),('none', 'No action'),('prev', 'Previous')], 'Move to')
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'hr_aa_attendance_waj')
        cr.execute("""
            create or replace view hr_aa_attendance_waj as (
               select 
                   A.id as id,
                   A.name as name,
                   A.action as action,
                   A.action_desc as action_desc,
                   A.employee_id as employee_id,
                   P.journal_id as prev_journal_id,
                   N.journal_id as next_journal_id,
                   ACT.move_to as move_to
               from hr_attendance as A
                   left join hr_attendance as N on A.employee_id=N.employee_id and A.name < N.name
                   left join hr_attendance as AN on A.employee_id=AN.employee_id and A.name < AN.name and AN.name < N.name
                   left join hr_attendance as P on A.employee_id=P.employee_id and P.name < A.name
                   left join hr_attendance as PA on A.employee_id=PA.employee_id and PA.name < A.name and P.name < PA.name
                   left join hr_aa_attendance_waj_action as ACT on A.id=ACT.name
               where
                   A.journal_id is Null and
                   AN.name is Null and
                   PA.name is Null
        )""")

    def write(self, cr, uid, ids, vals, context={}):
        pool_waj_action = self.pool.get('hr.aa.attendance_waj.action')
        waj_action_ids = pool_waj_action.search(cr, uid, [('name','in',ids)])
        if len(waj_action_ids) == 0:
            for waj_id in ids:
                data = { 'name': waj_id }
                data.update(vals)
                pool_waj_action.create(cr, uid, data)
        else:
            waj_action = pool_waj_action.write(cr, uid, waj_action_ids, vals)
        return True

        
    def unlink(self, cr, uid, ids, context={}):
        raise osv.except_osv(_('Error !'), _('You cannot delete any record!'))

    def connect_to_journal(self, cr, uid, ids, context={}):
        """
        Connect an assistance to a journal modifing the attendance_range_start
        and attendance_range_end of the journal.
        """
        pool_att = self.pool.get('hr.attendance')
        pool_jou = self.pool.get('hr.aa.journal')
        pool_act = self.pool.get('hr.aa.attendance_waj.action')

        to_del = []
        for obj in self.browse(cr, uid, ids):
            if obj.move_to == 'next' and obj.next_journal_id:
                pool_jou.write(cr, uid, [obj.next_journal_id.id], {'attendance_range_start': obj.name})
                to_del.append(obj.id)
            elif obj.move_to == 'prev' and obj.prev_journal_id:
                pool_jou.write(cr, uid, [obj.prev_journal_id.id], {'attendance_range_end': obj.name})
                to_del.append(obj.id)

        # Remove done actions
        act_ids = pool_act.search(cr, uid, [('name','in',to_del)])
        pool_act.unlink(cr, uid, act_ids)

        return True
hr_aa_attendance_waj()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
