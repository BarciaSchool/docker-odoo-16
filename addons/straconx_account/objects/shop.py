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

class sale_shop(osv.osv):
    
    def _check_journals(self,cr,uid,ids):
        for shop in self.browse(cr, uid, ids):
            res={}
            b=True
            for journal in shop.journal_ids:
                if res.has_key(journal.type):
                    b=False
                    break
                else:
                    res[journal.type]=True
        return b

    _inherit = 'sale.shop'
    _columns = {
                'printer_point_ids': fields.one2many('printer.point', 'shop_id', 'Printer Points',),
                'journal_ids': fields.many2many('account.journal', 'rel_shop_journal', 'shop_id', 'journal_id', 'Journals Used'),
                'shop_manager': fields.many2one('res.users','Shop Manager'),
                'shop_supervisor': fields.many2one('res.users','Shop Supervisor'),
                'logistics_manager': fields.many2one('res.users','Logistics Manager'),
                'logistics_stock': fields.many2one('res.users','Logistics Stock'),
                'credit_manager': fields.many2one('res.users','Credit Manager'),
                'purchase_manager': fields.many2one('res.users','Purchase Manager'),                
                'point_of_sale': fields.boolean('Is Point of Sale'),
                'wholesale': fields.boolean('Is Wholesale Store'),
                'headquarter': fields.boolean('Is Headquarter'),                                     
                'consignment': fields.boolean('Is Consignment'),

                }
    
    _constraints = [(_check_journals,'should only be a journal by type in the shop',['journal_ids'])]
sale_shop()
