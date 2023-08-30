# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A (Jorge Valdiviezo) 
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

from osv import fields,osv
import time

class table_commission(osv.osv):
    
    _name = "table.commission"
    _description = "Table Commission"

    _columns = {
        'name':fields.char('Name', size=128, required=True),
        'segmento_id':fields.many2one('res.partner.segmento', 'Segmento', required=False, ondelete="cascade"),
        'line_ids':fields.one2many('table.commission.line', 'table_id', 'Table Lines', required=False),
        'type':fields.selection([
            ('percentage','Percentage'),
            ('fixed_amount','Fixed Amount'),],'Type Table', select=True, 
        help="This field indicate if the value to paid in the commission is a percentaje of the goald or fixed amount"),
    }
    
table_commission()

class table_commission_line(osv.osv):
    
    def _check_values(self,cr,uid,ids):
        b=True
        for line in self.browse(cr, uid, ids):
            if line.minimum_value < 0 or line.maximum_value < 0:
                b=False
            if line.minimum_value > line.maximum_value:
                b=False
        return b
    
    def _check_range_values(self,cr,uid,ids):
        b=True
        for line in self.browse(cr, uid, ids):
            if line.table_id:
                lines_ant=self.search(cr, uid, [('table_id','=',line.table_id.id),('id','not in',tuple([line.id]))])
                for l in lines_ant:
                    lb=self.browse(cr, uid, l, None)
                    if line.minimum_value >= lb.minimum_value and line.minimum_value <= lb.maximum_value:
                        b=False
                        #raise osv.except_osv('Error!', _('The minimum amount can not be in other range already exists'))
                    if line.maximum_value >= lb.minimum_value and line.maximum_value <= lb.maximum_value:
                        b=False
                    if lb.minimum_value > line.minimum_value  and lb.maximum_value < line.maximum_value:
                        b=False
                        #raise osv.except_osv('Error!', _('The maximum amount can not be in other range already exists'))
        return b
    
    
    _name = "table.commission.line"
    _description = "Table Commission Line"

    _columns = {
        'table_id':fields.many2one('table.commission', 'Table Commission', required=False),
        'sequence': fields.integer('sequence'),
        'minimum_value': fields.float('Minimum Value', digits=(16,3)),
        'maximum_value': fields.float('Maximum Value', digits=(16,3)),
        'amount': fields.float('Amount', digits=(16,2)),
    }
    
    _order = 'sequence asc'
    
    _constraints = [
        (_check_values,'The minimum and maximum values must be greater that 0 and maximum value can not be less that minimum value',['minimum_value','maximum_value']),
        (_check_range_values,'The range entered can not be in other range already exists',['minimum_value','maximum_value']),
        ]
table_commission_line()