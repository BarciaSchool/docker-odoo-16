# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2013-2014 STRACONX S.A 
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
from datetime import date, timedelta
import decimal_precision as dp

class product_information(osv.osv_memory):
    _name = "product.information"
    
    def _date_products(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        sql_date ="""select date_invoice from account_invoice_line ail, account_invoice ai 
                    where ail.invoice_id = ai.id and product_id = %s and type = %s and ai.state not in ('draft','cancel') order by date_invoice desc"""
        for wizard in self.browse(cr, uid, ids, context): 
            res[wizard.id]= {'date_purchase':None,
                             'date_sale':None}
            cr.execute(sql_date,(context.get('active_id',None),'in_invoice'))
            result=cr.fetchall()
            if result:
                res[wizard.id]['date_purchase']= result[0][0]
            cr.execute(sql_date,(context.get('active_id',None),'out_invoice'))
            result1=cr.fetchall()
            if result1:
                res[wizard.id]['date_sale']= result1[0][0] or None
        return res

    def _month_products(self, cr, uid, ids, field_name, arg, context=None):
        res = {} 
                
        def get_first_day(dt, d_years=0, d_months=0):
            y, m = dt.year + d_years, dt.month + d_months
            a, m = divmod(m-1, 12)
            return date(y+a, m+1, 1)

        def get_last_day(dt):
            return get_first_day(dt, 0, 1) + timedelta(-1)

        d = date.today()
        fist_day = get_first_day(d)
        last_day = get_last_day(d)

        sql_date ="""select sum(quantity) from account_invoice_line ail, account_invoice ai 
                     where ail.invoice_id = ai.id and product_id = %s and ai.state not in ('draft','cancel') and type = %s and ai.date_invoice between %s and %s """

        for wizard in self.browse(cr, uid, ids, context): 
            res[wizard.id]= {'month_purchase':0.00}
            cr.execute(sql_date,(context.get('active_id',None),'in_invoice',fist_day,last_day))
            result=cr.fetchall()
            if result:
                product_purchase = result[0][0]
                res[wizard.id]['month_purchase']= product_purchase

            res[wizard.id]= {'month_sale':0.00}
            cr.execute(sql_date,(context.get('active_id',None),'out_invoice',fist_day,last_day))
            result1=cr.fetchall()
            if result1:
                product_sale = result1[0][0]
                res[wizard.id]['month_sale']= product_sale
                res[wizard.id]['month_purchase']= product_purchase             
        return res


    def _year_products(self, cr, uid, ids, field_name, arg, context=None):
        res = {} 
                
        def get_first_day_year(dt, d_years=0, d_months=0):
            y, m = dt.year + d_years, dt.month + d_months
            a, m = divmod(m-1, 12)
            return date(y+a, 1, 1)

        def get_last_day_year(dt):
            return get_first_day_year(dt, 12, 31)

        d = date.today()
        fist_day = get_first_day_year(d)
        last_day = get_last_day_year(d)

        sql_date ="""select sum(quantity) from account_invoice_line ail, account_invoice ai 
                        where ail.invoice_id = ai.id and product_id = %s and ai.state not in ('draft','cancel') and type = %s and ai.date_invoice between %s and %s """

        for wizard in self.browse(cr, uid, ids, context): 
            res[wizard.id]= {'year_purchase':0.00}
            cr.execute(sql_date,(context.get('active_id',None),'in_invoice',fist_day,last_day))
            result=cr.fetchall()
            if result:
                product_purchase = result[0][0]
                res[wizard.id]['year_purchase']= product_purchase
                
            res[wizard.id]= {'year_sale':0.00}
            cr.execute(sql_date,(context.get('active_id',None),'out_invoice',fist_day,last_day))
            result1=cr.fetchall()
            if result1:
                product_sale = result1[0][0]
                res[wizard.id]['year_sale']= product_sale
        return res
    
    _columns = {
                'date_purchase':fields.function(_date_products, method=True, type='date', string='Last Purchase', multi='date', store=True),
                'date_sale':fields.function(_date_products, method=True, type='date', string='Last Sale', multi='date', store=True),
                'month_purchase':fields.function(_month_products, method=True, string='Month Purchase', digits_compute=dp.get_precision('Purchase Price'), multi='month'),
                'month_sale':fields.function(_month_products, method=True, string='Month Sale', digits_compute=dp.get_precision('Purchase Price'), multi='month'),
                'year_purchase':fields.function(_year_products, method=True, string='Year Purchase', digits_compute=dp.get_precision('Purchase Price'), multi='year'),
                'year_sale':fields.function(_year_products, method=True, string='Year Sale', digits_compute=dp.get_precision('Purchase Price'), multi='year'),
                }
    
product_information()