# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
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


class credit_card_bank(osv.osv):
    _name = 'res.bank.emisor'
    _columns = {'name': fields.char('Emisor', size=40)}
credit_card_bank()


class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'
    _columns = {
        'acc_country_id': fields.many2one("res.country", 'Bank country'),
        'type_account_bank': fields.many2one("res.bank.emisor", 'Emisor'),
        'bank_name': fields.related('bank', 'name', type='char', string='Bank Name', store=True, size=64),
        }

    def onchange_emisor(self, cr, uid, ids, state=False, context=None):
        result = {}
        if state not in ('credit_card','debit_card'):            
            type_account_bank= self.pool.get('res.bank.emisor').search(cr,uid,[('name','=','OTRAS')])            
#        result['type_account_bank'] = type_account_bank 
        return {'value':result}            
res_partner_bank()

class Bank(osv.osv):
    _inherit = 'res.bank'
    _columns = {
        'lname': fields.char('Long name', size=128),
        'vat': fields.char('VAT code',size=32 ,help="Value Added Tax number"),
        'website': fields.char('Website',size=64),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),        
    }
Bank()
