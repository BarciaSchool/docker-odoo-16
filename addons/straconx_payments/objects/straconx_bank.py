# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A
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

class Bank(osv.osv):
    _inherit = 'res.bank'
    _columns = {
        'account_protested_id':fields.many2one('account.account', 'Account Debit Note Protested Check', required=False),
        'account_rejected_id':fields.many2one('account.account', 'Account Debit Note Rejected Check', required=False),
        #'account_exchanged_id':fields.many2one('account.account', 'Account Debit Note Exchanged Check', required=False),
        'amount_protested': fields.float('amount Protested', digits=(16,2)),
        'amount_rejected': fields.float('amount Rejected', digits=(16,2)),
        #'amount_exchanged': fields.float('amount Exchanged', digits=(16,2)),
    }
Bank()


class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'
    _columns = {
        'sequence2': fields.integer('Sequence2'),
        'phone':fields.char('Telefono',size=13),
    }
res_partner_bank()