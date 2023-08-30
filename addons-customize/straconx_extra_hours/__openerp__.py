# -*- encoding: utf-8 -*-
##############################################################################
#
#    Attendance Annalysis for OpenERP
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
{   'active': False,
    'author': 'Moldeo Interactive CT',
    'category': 'Generic Modules/Human Resources',
    'demo_xml': [],
    'depends': ['hr_attendance', 'hr_holidays', 'hr_contract'],
    'description': '\n\n    Module to do analisis over human resources attendances.\n\n    ',
    'init_xml': [],
    'installable': True,
    'name': 'Human Resources Attendance Annalysis',
    'update_xml': [   'security/hraa_security.xml',
                      'security/ir.model.access.csv',
                      'hr_attendance_analysis_workflow.xml',
                      'hr_attendance_analysis_view.xml',
                      'hr_attendance_analysis_wizard.xml',
                      'hr_action_reason_rule_view.xml',
                      'hr_action_reason_rule_wizard.xml',
                      'hr_action_reason_rule_workflow.xml',
                      'hr_contract_view.xml',
                      'hr_employee_view.xml',
                      'hr_journal_view.xml',
                      'hr_journal_wizard.xml',
                      'hr_journal_workflow.xml',
                      'hr_payroll_view.xml',
                      'hr_payroll_report.xml',
                      'hr_payroll_workflow.xml',
                      'hr_payroll_wizard.xml',
                      'hr_aa_attendance_waj_view.xml',
                      'hr_aa_attendance_waj_wizard.xml'],
    'version': '1.3',
    'website': 'http://www.moldeointeractive.com.ar'}
