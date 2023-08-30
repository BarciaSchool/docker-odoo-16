# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - 20011 STRACONX S.A. (<http://openerp.straconx.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from report import report_sxw
from osv import fields, osv
import time
from operator import itemgetter, attrgetter

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
#        lines = {}
#        param = {}
        categ = {}
        self.localcontext.update({
#            "lines": lines,
 #           "param": param,
        })
        

    def set_context(self, objects, data, ids, report_type = None):
#    def lines(self, form):
#        print "stock_card lines",form
        cr=self.cr
        uid=self.uid
        location_id = []
        categ_id = []
        date_from = []
        date_to = []
        if data['form']['category_id']:
            categ_id=data['form']['category_id']
        if data['form']['location_id']:
            location_id = location_id=data['form']['location_id']
        if data['form']['date_from']:            
            date_from= data['form']['date_from'] 
        else:
#            date_from = '1970-01-01 00:00:00'
            date_from = time.strftime("%Y-%m-%d %H:%M:%S")
        if data['form']["date_to"]:            
            date_to = data['form']["date_to"] 
        else:
            date_to = time.strftime("%Y-%m-%d %H:%M:%S")        
        lines = []
        param = []
        moves = []
        g={}
        categ=[]
        # find all moves coming to location
        if categ_id:
            categ_list = self.pool.get('product.category').search(cr,uid,[('id','=',categ_id[0]),('is_comercial','=',True)])            
        else:
            categ_list = self.pool.get('product.category').search(cr,uid,[('is_comercial','=',True)])                                  
        for c in categ_list:
            #categ_id_name = self.pool.get('product.category').browse(cr,uid,c).name
            category=self.pool.get('product.category').browse(cr,uid,c)            
            search_product = self.pool.get('product.template').search(cr,uid,[('categ_id','=',c),('type','in',[('product')])])
            pro_id = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','in',search_product)])
            product_list = self.pool.get('product.product').browse(cr,uid,pro_id)
            order_moves = []
            lines = []
            #if not g.has_key(c):
            for p in product_list:
                product_id = self.pool.get('product.product').browse(cr,uid,p.id)
                move_in_ids=self.pool.get("stock.move").search(cr,uid,[("product_id","=",product_id.id),("location_dest_id","child_of",[location_id[0]]),("date",">=",date_from),("date","<=",date_to),("state","=","done")]) 
                for move in self.pool.get("stock.move").browse(cr,uid,move_in_ids):
                    moves[move.id]=move
                # find all moves leaving from location
                move_out_ids=self.pool.get("stock.move").search(cr,uid,[("product_id","=",product_id.id),("location_id","child_of",[location_id[0]]),("date",">=",date_from),("date","<=",date_to),("state","=","done")])
                for move in self.pool.get("stock.move").browse(cr,uid,move_out_ids):
                    moves[move.id]=move
                move_in_ids=set(move_in_ids)
                move_out_ids=set(move_out_ids)
                # order moves by date
                if order_moves:
                    order_moves=moves.values()
                    order_moves.sort(lambda a,b: cmp(a.date, b.date))
                if date_from: 
                    start_qty_in=self.pool.get("product.product").get_product_available(cr,uid,[product_id.id],context={"location": location_id[0], "compute_child": True, "to_date": date_from,"states": ["done"]})[product_id.id]
                balance = start_qty_in
                cost_unit = product_id.standard_price
                price_unit = product_id.list_price
                total_cost = cost_unit * balance
                total_price = price_unit * balance
                if total_price >0:
                    margin_curr = total_price - total_cost
                    margin_perc = ((total_price - total_cost)/ total_price)*100
                else:
                    margin_curr = total_price - total_cost
                    margin_perc = 0.00
                lines.append({
                    "code": product_id.default_code,
                    "product_id": product_id.name,
                    "balance": balance,
                    "price_unit": price_unit,
                    "cost_unit":cost_unit,
                    "total_cost":total_cost,                                
                    "total_price":total_price,
                    "margin_curr":margin_curr,
                    "margin_perc":margin_perc,
                })
            g[category]=lines
        #categ.append(g)
        #print categ
        print g
        self.localcontext.update({
            "categ": g,

        })
        super(Parser, self).set_context(objects, data, ids, report_type)