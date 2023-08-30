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

class hr_attendance(osv.osv):
    _inherit = "hr.attendance"
    _name = "hr.attendance"

    def _get_contract(self, cr, uid, ids, field_name, arg, context=None):
        _query_ = """
            SELECT
                A.id, C.id
            FROM
                hr_attendance as A,
                hr_contract as C
            WHERE
                (((not C.date_end is Null) and
                  (C.date_start, C.date_end) OVERLAPS (A.name, A.name)) OR
                (C.date_end is Null and C.date_start <= A.name)) AND
                (A.employee_id = C.employee_id) AND
                A.id in ( %s )
        """ % ",".join(map(str, ids))
        cr.execute(_query_)
        return dict(cr.fetchall())

    def _get_turn_hours(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        conts = self._get_contract(cr, uid, ids, 'contract', None, context=context)
        items = conts.items()
        if len(items) == 0: return False
        att_ids, con_ids = tuple(map(list, zip(*items)))
        cons = self.pool.get('hr.contract').browse(cr, uid, con_ids)
        atts = self.pool.get('hr.attendance').browse(cr, uid, att_ids)
        for (att, cont) in zip(atts, cons):
            date_dt = tu.datetime.combine(tu.d(att.date), tu.time(0))
            wd = tu.d(att.date).weekday()
            turns = [ (date_dt + tu.timedelta(days = int(i.dayofweek) - wd, hours=i.hour_from),
                       date_dt + tu.timedelta(days = int(i.dayofweek) - wd, hours=i.hour_to + 24*(i.hour_to < i.hour_from)))
                     for i in cont.turn_id.attendance_ids ]
            turns = filter(lambda (f,t):
                             f - tu.timedelta(hours=6) <= tu.dt(att.datetime) and
                             tu.dt(att.datetime) <= t + tu.timedelta(hours=6), turns)
            if len(turns) > 0:
                res[att.id] = { 
                    'turn_date': tu.d2s(turns[0][0].date()),
                    'turn_start': tu.dt2s(turns[0][0]),
                    'turn_end': tu.dt2s(turns[0][1])
                }
            else:
                res[att.id] = { 
                    'turn_date': False,
                    'turn_start': False,
                    'turn_end': False 
                }
        return res

    def _get_holidays(self, cr, uid, ids, field_name, arg, context=None):
        state_map = {
            'confirmed_holidays': 'confirm',
            'validated_holidays': 'validate',
            'refused_holidays':   'refuse',
        }
        if field_name in state_map:
            state = 'and state = \'%s\'' % state_map[field_name]
        else:
            state = ''
        _query_ = """
            SELECT
                A.id, H.id
            FROM
                hr_attendance as A
                LEFT OUTER JOIN
                hr_holidays as H
                ON
                (H.date_from, H.date_to) OVERLAPS (A.name, A.name) AND
                (A.employee_id = H.employee_id OR H.employee_id is Null)
            WHERE
                A.id in ( %s )
                %s
        """ % (",".join(map(str, ids)), state)
        cr.execute(_query_)
        res = dict(map(lambda i: (i, []), ids))
        for a, h in cr.fetchall():
            if h: res[a].append(h)
        return res

    def _get_has_holidays(self, cr, uid, ids, field_name, arg, context=None):
        state_map = {
            'has_confirmed_holidays': 'confirmed',
            'has_validated_holidays': 'validated',
            'has_refused_holidays':   'refused',
        }
        if field_name in state_map:
            field_name = '%s_holidays' % state_map[field_name]
        else:
            field_name = 'holidays'
        res = self._get_holidays(cr, uid, ids, field_name, arg,
                                 context=context)
        for k in res:
            res[k] = len(res[k])>0
        return res

    def _get_previous(self, cr, uid, ids, field_name, arg, context=None):
        _query_ = """
            SELECT
                A.id, P.id
            FROM
                hr_attendance as A
                LEFT JOIN
                hr_attendance as P
                ON A.employee_id = P.employee_id AND A.name > P.name
                LEFT OUTER JOIN
                hr_attendance as M
                ON  P.name < M.name
                AND A.employee_id = M.employee_id
                AND A.name > P.name AND A.name > M.name
            WHERE
                A.id in ( %s ) AND
                M.name is Null
        """ % ",".join(map(str, ids))
        cr.execute(_query_)
        return dict(cr.fetchall())

    def _get_next(self, cr, uid, ids, field_name, arg, context=None):
        _query_ = """
            SELECT
                A.id, P.id
            FROM
                hr_attendance as A
                LEFT JOIN
                hr_attendance as P
                ON A.employee_id = P.employee_id AND A.name < P.name
                LEFT OUTER JOIN
                hr_attendance as M
                ON  P.name > M.name
                AND A.employee_id = M.employee_id
                AND A.name < P.name AND A.name < M.name
            WHERE
                A.id in ( %s ) AND
                M.name is Null
            ORDER BY A.employee_id, A.name
        """ % ",".join(map(str, ids))
        cr.execute(_query_)
        return dict(cr.fetchall())

    def _get_date(self, cr, uid, ids, field_name, arg, context=None):
        res = map(lambda a: (a.id, tu.d2s(tu.dt(a.name).date())),
            self.browse(cr, uid, ids))
        return dict(res)

    def _get_datetime(self, cr, uid, ids, field_name, arg, context=None):
        res = map(lambda a: (a.id, a.name),
            self.browse(cr, uid, ids))
        return dict(res)

    def _get_journal(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        pool_journal = self.pool.get('hr.aa.journal')
        attendances = self.browse(cr, uid, ids, context=context)
        for a in attendances:
            att_begin = tu.dt2s(tu.dt(a.name) + tu.timedelta(hours=3))
            att_end = tu.dt2s(tu.dt(a.name) - tu.timedelta(hours=3))
	    if att_begin > att_end:
		# Cambio Gustavo. Swapeo att_begin por att_end
		att_temp = att_begin
		att_begin = att_end
		att_end = att_temp
	    employee_id = a.employee_id.id
	    # import pdb;pdb.set_trace()
            journal_ids = pool_journal.search(cr, uid, [
                ('turn_start', '<=', att_begin),
                ('turn_end', '>=', att_end),
                ('employee_id', '=', employee_id),
            ])
	    # assert(len(journal_ids) <= 1)
	    if len(journal_ids) > 1:
	            raise except_orm('JournalError', 'Mas de un journal para ese turno')
            if len(journal_ids) > 0: res[a.id] = journal_ids[0]
        return res

    def _get_attendance_by_journal(self, cr, uid, ids, context=None):
        res = []
        pool_att = self.pool.get('hr.attendance')
        journals = self.browse(cr, uid, ids, context)
        for j in journals:
            if not j.turn_start: continue
            turn_start = tu.dt2s(tu.dt(j.turn_start) - tu.timedelta(hours=3))
            turn_end = tu.dt2s(tu.dt(j.turn_end) + tu.timedelta(hours=3))
            employee_id = j.employee_id.id
            res += pool_att.search(cr, uid, [
                ('name', '>=', turn_start),
                ('name', '<=', turn_end),
                ('employee_id', '=', employee_id),
            ])
        return res

    _columns = {
        'previous' : fields.function(_get_previous, type='one2one',
                                     obj='hr.attendance', method=True,
                                     string='Previous attendance'),
        'next' : fields.function(_get_next, type='one2one',
                                     obj='hr.attendance', method=True,
                                     string='Next attendance'),
        'holidays' : fields.function(_get_holidays, type='many2many',
                                     obj='hr.holidays', method=True,
                                     string='Holidays'),
        'confirmed_holidays' : fields.function(_get_holidays, type='many2many',
                                     obj='hr.holidays', method=True,
                                     string='Holidays'),
        'validated_holidays' : fields.function(_get_holidays, type='many2many',
                                     obj='hr.holidays', method=True,
                                     string='Validated Holidays'),
        'refused_holidays' : fields.function(_get_holidays, type='many2many',
                                     obj='hr.holidays', method=True,
                                     string='Refused Holidays'),
        'has_holidays' : fields.function(_get_holidays, type='bool',
                                     obj='hr.holidays', method=True,
                                     string='Has Holidays?'),
        'has_confirmed_holidays' : fields.function(_get_has_holidays,
                                                   type='bool',
                                     obj='hr.holidays', method=True,
                                     string='Has Confirmed Holidays?'),
        'has_validated_holidays' : fields.function(_get_has_holidays,
                                                   type='bool',
                                     obj='hr.holidays', method=True,
                                     string='Has Validated Holidays?'),
        'has_refused_holidays' : fields.function(_get_has_holidays, type='bool',
                                     obj='hr.holidays', method=True,
                                     string='Has Refused Holidays?'),
        'contract' : fields.function(_get_contract, type='one2one',
                                     obj='hr.contract', method=True,
                                     string='Contract'),
        'turn_date' : fields.function(_get_turn_hours, type='date',
                                       method=True, string='Turn day',
                                       multi = 'turns'
                                      ),
        'turn_start' : fields.function(_get_turn_hours, type='datetime',
                                       method=True, string='Turn start',
                                       multi = 'turns'
                                      ),
        'turn_end' : fields.function(_get_turn_hours, type='datetime',
                                     method=True, string='Turn end',
                                     multi = 'turns'
                                    ),
        'date' : fields.function(_get_date, type='date',
                                     method=True, string='Attendance date'),
        'datetime' : fields.function(_get_datetime, type='datetime',
                                     method=True, string='Attendance datetime'),
        'journal_id': fields.function(_get_journal, type='many2one',
                                      obj='hr.aa.journal', string='Attendances',
                                      method=True,
                                      store = {'hr.aa.journal': (_get_attendance_by_journal, ['date','turn_id'], 10)},
                                     ),
    }

    _defaults = {
        'employee_id': lambda self, cr, uid, context : context['employee_id'] if context and 'employee_id' in context else None,
        'journal_id': lambda self, cr, uid, context : context['journal_id'] if context and 'journal_id' in context else None,
        'name': lambda self, cr, uid, context : context['timestamp'] if context and 'timestamp' in context else None,
        'action': lambda self, cr, uid, context : context['action'] if context and 'action' in context else None,
    }
    """
# Intento de deshabilitar las restricciones.
# Pero no funciona :(
    def _altern_si_so(self, cr, uid, ids):
        #" ""
        Remove default constrains to hr_attendance.
        class: hr_attendance.
        #" ""
        return True
    _constraints = [(lambda *x: True, 'Error: Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    """
hr_attendance()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
