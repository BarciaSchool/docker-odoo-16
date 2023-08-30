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

import wizard
import netsvc
import pooler
from tools.translate import _

end_form = '''<?xml version="1.0"?>
<form title="Result">
     <field name="mesg"/>
</form>'''

end_fields = {
        'mesg': {'string': 'Message', 'type': 'char' },
}

def _connect_to_journal(self,cr,uid,data,context=None):
    pool = pooler.get_pool(cr.dbname)
    att = pool.get('hr.aa.attendance_waj')

    att.connect_to_journal(cr, uid, data['ids'], context=context)
    return {}

def _action_open_window(self, cr, uid, data, context):
    return {
        'name': _('Attendances without Associated Journals'),
        'res_model': 'hr.aa.attendance_waj',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'view_id': False,
        'type': 'ir.actions.act_window'
    }

class wiz_connect_to_journal(wizard.interface):
    states={
        'init':{
        'actions':[_connect_to_journal],
        'result':{
            'type':'action',
            'action': _action_open_window,
            'state': 'end',
            },
        },
    }

wiz_connect_to_journal('hr.aa.connect_to_journal')

