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

class hr_employee(osv.osv):
    _inherit = 'hr.employee'
    _description = 'hr.employee'

    def _get_employee_turn(self, cr, uid, ids, field_name, arg, context):
	    res = {}
            for i in ids:
                #get the id of the current function of the employee of identifier "i"
                sql_req= """
                        SELECT c.turn_id AS turn_id
                        FROM hr_contract c
                        WHERE
                          (c.employee_id = %d)
                        ORDER BY create_date DESC
                        """ % (i,)

                cr.execute(sql_req)
                sql_res = cr.dictfetchone()

                if sql_res: #The employee has one associated contract
                    res[i] = sql_res['turn_id']
                else:
                    #res[i] must be set to False and not to None because of XML:RPC
                    # "cannot marshal None unless allow_none is enabled"
                    res[i] = False
            return res

    def _get_employee_wage_type(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for i in ids:
                #get the id of the current function of the employee of identifier "i"
                sql_req= """
                        SELECT c.wage_type_id AS wage_type_id
                        FROM hr_contract c
                        WHERE
                          (c.employee_id = %d)
                        ORDER BY create_date DESC
                        """ % (i,)

                cr.execute(sql_req)
                sql_res = cr.dictfetchone()

                if sql_res: #The employee has one associated contract
                    res[i] = sql_res['wage_type_id']
                else:
                    #res[i] must be set to False and not to None because of XML:RPC
                    # "cannot marshal None unless allow_none is enabled"
                    res[i] = False
            return res


    def _search_turn_id(self, cr, uid, obj, name, args, context):
	    import pdb;pdb.set_trace()
	    # 
	    return [0]


    _columns = {
        'clock_login_id' : fields.text('Login id del reloj'),
        'turn_id' : fields.function(
		_get_employee_turn,
		type='many2one',
		obj="resource.calendar",
		method=True,
		select=True,
		fcnt_search=_search_turn_id,
		string='Turn Function'),
        'wage_type_id' : fields.function(
                _get_employee_wage_type,
                type='many2one',
                obj="hr.contract.wage.type",
		select=True,
                method=True,
                string='Wage Type'),

	}

    def get_attendance_days(self, cr, uid, ids, daterange=[], context=None):
        """
        Return all attendances of this employee
        """
        res = {}
        if len(daterange) == 2:
            daterange = [('date', '>=', str(daterange[0])),
                         ('date', '<=', str(daterange[1]))] 
        else:
            daterange=[]
        for emp in self.browse(cr, uid, ids):
            journal_ids = self.pool.get('hr.journal').search(cr,uid,
                [('employee_id', '=', emp.id)]+daterange, context=context)
            res[emp.id] = self.pool.get('hr.journal').browse(cr, uid, journal_ids,
                                                context=context)
        return res

    def get_valid_holidays(self, cr, uid, ids, date, context=None):
        res = {}

        _query_ = """
            SELECT employee_id, id, state
            FROM hr_holidays
            WHERE
                employee_id in (%(employee)s) AND
                (
                SELECT CASE
                WHEN not date_to is Null THEN
                    (date_from, date_to)
                    overlaps
                    (DATE '%(date)s', DATE '%(date)s')
                ELSE
                    date_from <= DATE '%(date)s'
                END
                )
            UNION
            SELECT E.e, H.id, H.state
            FROM hr_holidays as H,
                 (VALUES %(employee_x)s) as E(e)
            WHERE
                H.employee_id is Null AND
                (
                SELECT CASE
                WHEN not H.date_to is Null THEN
                    (H.date_from, H.date_to)
                    overlaps
                    (DATE '%(date)s', DATE '%(date)s')
                ELSE
                    H.date_from <= DATE '%(date)s'
                END
                )
            """ % {
                'employee': ','.join(map(str, ids)),
                'employee_x': '(' + '),('.join(map(str, ids)) + ')',
                'date': tu.dt2s(date),
        }
        cr.execute(_query_)
        emp_hol = cr.fetchall()
        for (emp_id, hol_id, state) in emp_hol:
            if not emp_id in res: res[emp_id] = {'draft': [], 'confirm': [],
                                                 'refuse': [], 'validate': [],
                                                 'cancel': []}
            res[emp_id][state].append(hol_id)
        return res

    def get_valid_contract(self, cr, uid, ids, date, context=None):
        res = {}

        _query_ = """
            SELECT C.employee_id, C.id, C.sequence,count(*)
            FROM hr_contract AS C
            WHERE
                C.employee_id in (%(employee)s) AND
                (
                SELECT CASE
                WHEN not C.date_end is Null THEN
                    (C.date_start, C.date_end)
                    overlaps
                    (DATE '%(date)s', DATE '%(date)s')
                ELSE
                    C.date_start <= DATE '%(date)s'
                END
                )
            GROUP BY
                C.employee_id,C.id,C.sequence
	    ORDER BY C.sequence ASC
            """ % {
                'employee': ','.join(map(str, ids)),
                'date': tu.dt2s(date),
                }
        cr.execute(_query_)
        emp_con = cr.fetchall()
	if len(emp_con) == 2:
		emp_con.pop(1)

#	import pdb;pdb.set_trace()

        if len(emp_con) == 0:
            raise except_orm('TurnError', 'No hay contrat para esa persona para ese día')

        for (emp_id, con_id, seq, c) in emp_con:
            if c > 1:
                raise RuntimeError('More than one contract at same time for'
                                   ' employee with id=%i' % emp_id)
            else:
                res[emp_id] = con_id
        return res

    def get_valid_turn(self, cr, uid, ids, date, context=None):
        res = {}

        _query_ = """
            SELECT C.employee_id, min(C.id), count(*)
            FROM hr_contract AS C, hr_timesheet AS TS
            WHERE
                C.turn_id=TS.tgroup_id AND
                C.employee_id in (%(employee)s) AND
                ((CAST(TS.dayofweek AS INTEGER)+1) %% 7)=EXTRACT(DOW FROM TIMESTAMP '%(date)s') AND
                (
                SELECT CASE
                WHEN not C.date_end is Null THEN
                    (C.date_start, C.date_end)
                    overlaps
                    (DATE '%(date)s', DATE '%(date)s')
                ELSE
                    C.date_start <= DATE '%(date)s'
                END
                )
            GROUP BY
                C.employee_id
            """ % {
                'employee': ','.join(map(str, ids)),
                'date': tu.dt2s(date),
                }
        cr.execute(_query_)
        emp_con = cr.fetchall()

        for (emp_id, con_id, c) in emp_con:
            if c > 1:
                raise RuntimeError('More than one contract at same time for'
                                   ' employee with id=%i' % emp_id)
            else:
                res[emp_id] = con_id
        return res


hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
