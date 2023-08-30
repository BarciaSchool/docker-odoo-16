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

class account_journal_type(osv.osv):
    _name = "account.journal.type"
    _columns = {
                'code':fields.char('Code', size=32, required=True, readonly=False, traslate=True),
                'name':fields.char('Name', size=32, required=True, readonly=False, traslate=True),
                }
account_journal_type()

class account_account_type_internal(osv.osv):
    _name = "account.account.type.internal"
    _columns = {
                'code':fields.char('Code', size=32, required=True, readonly=False, traslate=True),
                'name':fields.char('Name', size=32, required=True, readonly=False, traslate=True),
                }
account_account_type_internal()