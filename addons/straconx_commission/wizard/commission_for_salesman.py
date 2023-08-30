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
import time
from datetime import datetime
from dateutil import relativedelta

from osv import fields, osv
from tools.translate import _

class commission_for_salesman(osv.osv_memory):

    _name ='commission.salesman.wizard'
    _columns = {
        'salesman_ids': fields.many2many('salesman.salesman', 'salesman_group_rel', 'commission_id', 'salesman_id', 'Salesman'),
        'computation_type' : fields.selection([('amount_invoiced','Amount Invoiced'),('amount_sales','Amount Sales'),],'Computation Base On',required=True),
        'line_categ_ids':fields.one2many('commission.salesman.line.wizard', 'forecast_line_id', 'Details for category', required=False),
    }
    
    _defaults = {
        'computation_type' : 'amount_invoiced',
    }
    
    def create_lines(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        forecast_line_obj=self.pool.get('sale.forecast.line')
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        obj=self.browse(cr, uid, ids[0], context)
        lines=[]
        for forecast in objs:
            list_categ=[]
            if not (obj.salesman_ids and obj.line_categ_ids):
                raise osv.except_osv(_('Error!'),_('You must enter salesman and lines of category'))
            for categ in obj.line_categ_ids:
                c={'product_category_id':categ.product_category_id.id,
                   'amount':categ.amount,}
                list_categ.append((0,0,c))
            for salesman in obj.salesman_ids:
#                if not (salesman.segmento_ids and salesman.table_commission_id):
#                    raise osv.except_osv(_('Error!'),_(('You must defined a segmento and table commission in the salesman %s') % (salesman.user_id.name)))
                if not salesman.segmento_ids:
                    raise osv.except_osv(_('Error!'),_(('You must select at least a segmento in the salesman %s') % (salesman.user_id.name)))
                for segment in salesman.segmento_ids:
                    if not segment.table_ids:
                        continue
                    line_ant= forecast_line_obj.search(cr, uid, [('salesman_id','=',salesman.id),('segmento_id','=',segment.id),('forecast_id','=',forecast.id)])
                    if not line_ant:
                        line_id=forecast_line_obj.create(cr, uid, {'salesman_id':salesman.id,
                                                                   'segmento_id':segment.id or None,
                                                                   'table_commission_id':segment.table_ids[0].id or None,
                                                                   'computation_type':obj.computation_type,
                                                                   'forecast_id':forecast.id,
                                                                   'line_categ_ids':list_categ
                                                                   })
                        lines.append(line_id)
        forecast_line_obj.action_calculate(cr, uid, lines, context)
        return {'type': 'ir.actions.act_window_close'}

commission_for_salesman()

class commission_for_salesman_line(osv.osv_memory):
    _name ='commission.salesman.line.wizard'
    _columns = {
        'forecast_line_id':fields.many2one('commission.salesman.wizard', 'Forecast Line', required=False),
        'amount': fields.float('Value Forecasted', required=True),
        'product_category_id':fields.many2one('product.category', 'Category', required=True),
    }
commission_for_salesman_line()