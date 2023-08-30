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
from tools.translate import _
import time

class sale_forecast_line_categ(osv.osv):
    
    def _check_amount(self,cr,uid,ids):
        b=True
        for line in self.browse(cr, uid, ids):
            if line.amount<0.0:
                b=False
        return b
    
#    def _final_evolution_details(self, cr, uid, ids, name, args, context={}):
#        forecast_line_categ =  self.browse(cr, uid, ids, context=context)
#        result={}
#        for line in forecast_line_categ:
#            where = []
#            where2=[]
#            if not line.forecast_line_id.salesman_id:
#                continue
#            if line.product_category_id:
#                where2.append(('categ_id','=',line.product_category_id.id))
#            product_id = self.pool.get('product.product').search(cr,uid,where2)
#            where.append(('salesman_id','=',line.forecast_line_id.salesman_id.id))
#            if line.forecast_line_id.computation_type in ('invoice_fix','amount_invoiced') :
#                obj = 'account.invoice'
#                where.append(('date_invoice','>=',line.forecast_line_id.forecast_id.date_from))
#                where.append(('date_invoice','<=',line.forecast_line_id.forecast_id.date_to))
#                state_dict = {
#                    'draft' : line.forecast_line_id.state_draft,
#                    'open' : line.forecast_line_id.state_confirmed,
#                    'paid' : line.forecast_line_id.state_done,
#                    'cancel' : line.forecast_line_id.state_cancel
#                    }
##                self.pool.get('account.invoice.line').search(cr,uid,[('product_id','in',product_id)])
#            else :
#                obj = 'sale.order'
#                where.append(('date_order','>=',line.forecast_line_id.forecast_id.date_from))
#                where.append(('date_order','<=',line.forecast_line_id.forecast_id.date_to))
#                state_dict = {
#                    'draft' : line.forecast_line_id.state_draft,
#                    'progress' : line.forecast_line_id.state_confirmed,
#                    'done' : line.forecast_line_id.state_done,
#                    'cancel' : line.forecast_line_id.state_cancel
#                    }
#            state = filter(lambda x : state_dict[x],state_dict)
#            if state:
#                where.append(('state','in',state))
#
#            searched_ids = self.pool.get(obj).search(cr,uid,where)
#            if  line.forecast_line_id.computation_type  in ('amount_sales','amount_invoiced') :
##                if line.computation_type == 'amount_sales':
##                    li='sale.order.line'
##                elif line.computation_type == 'amount_invoiced':
##                    li='account.invoice.line'
#                res = self.pool.get(obj).browse(cr,uid,searched_ids)
#                amount =0
#                for r in res:
#                    if line.forecast_line_id.computation_type == 'amount_sales' and product_id:
#                        for sline in r.order_line:
#                            if sline.product_id.type=='product' and sline.product_id.id in product_id:
#                                amount += sline.price_subtotal
#                    elif line.forecast_line_id.computation_type == 'amount_invoiced' and product_id:
#                        for iline in r.invoice_line:
#                            if iline.product_id.type=='product' and iline.product_id.id in product_id:
#                                if r.type == 'out_invoice':
#                                    amount += iline.price_subtotal
#                                elif r.type == 'out_refund':  
#                                    amount -= iline.price_subtotal
#                    else:
#                        amount += r.amount_untaxed
#                result[line.id]=amount
#        return result
    
    def _get_line_forecast(self, cr, uid, ids, context=None):
        result = {}
        try:
            for line in self.pool.get('sale.forecast.line').browse(cr, uid, ids, context=context):
                for lc in line.line_categ_ids:
                    result[lc.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()
        
    def _forecast_rate_categ(self, cr, uid, ids, field_names, args, context):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 0
            if line.amount:
                res[line.id] = (line.computed_amount/line.amount) * 100
        return res
    
    def _calculate_commission(self, cr, uid, ids, field_names, args, context):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.forecast_line_id:
                if not line.forecast_line_id.table_commission_id.line_ids:
                    continue
                value=0.0
                table=line.forecast_line_id.table_commission_id
                cr.execute("""SELECT amount FROM table_commission_line WHERE table_id = %s AND %s BETWEEN minimum_value AND maximum_value
                              UNION
                              SELECT amount FROM table_commission_line WHERE table_id = %s AND maximum_value = 
                              (SELECT MAX(maximum_value) FROM table_commission_line WHERE table_id = %s) AND %s > maximum_value""",(table.id, line.forecast_rate_categ, table.id, table.id, line.forecast_rate_categ))
                result=cr.fetchall()
                if result:
                    if table.type == 'percentage':
                        value=(line.computed_amount * result[0][0])/100
                    else:
                        value= result[0][0]
#                for lc in table.line_ids:
#                    if line.forecast_rate_categ >= lc.minimum_value and line.forecast_rate_categ <=lc.maximum_value:
#                        if table.type == 'percentage':
#                            value=(line.computed_amount * lc.amount)/100
#                        else:
#                            value= lc.amount
                res[line.id] = value
        return res
    
    _name = "sale.forecast.line.categ"
    _description = "Forecast Line Categ"

    _columns = {
        'forecast_line_id':fields.many2one('sale.forecast.line', 'Forecast Line', required=False),
        'product_category_id':fields.many2one('product.category', 'Category', required=False),
        'amount': fields.float('Value Forecasted'),
        'computed_amount': fields.float('Real Value', readonly=True),
        'amount_commission': fields.function(_calculate_commission, string='Amount Commission',method=True,
                                           store={'sale.forecast.line.categ': (lambda self, cr, uid, ids, c={}: ids, ['computed_amount','forecast_line_id'], 1),
                                                  'sale.forecast.line': (_get_line_forecast, 'table_commission_id', 2),},),
#        'computed_amount': fields.function(_final_evolution_details, string='Real Value',method=True,
#                                           store={'sale.forecast.line.categ': (lambda self, cr, uid, ids, c={}: ids, ['product_category_id','forecast_line_id'], 1),
#                                                  'sale.forecast.line': (_get_line_forecast, None, 2),},),
        'forecast_rate_categ' : fields.function(_forecast_rate_categ, method=True, string='Progress (%)',),
    }
    
    _sql_constraints = [
        ('forecast_line_categ_uniq', 'unique(forecast_line_id,product_category_id)', 'Can not exist a same category between the lines forecast!')
    ] 
    
    _constraints = [
        (_check_amount,'The value entered must be more than zero',['amount']),
        ]
    
    def action_calculate(self, cr, uid, ids, context=None):
        forecast_line_categ =  self.browse(cr, uid, ids, context=context)
        amount=0.0
        for line in forecast_line_categ:
            where = []
            where2=[]
            if not line.forecast_line_id.salesman_id:
                continue
            if line.product_category_id:
                where2.append(('categ_id','=',line.product_category_id.id))
            product_id = self.pool.get('product.product').search(cr,uid,where2)
            where.append(('salesman_id','=',line.forecast_line_id.salesman_id.id))
            if line.forecast_line_id.computation_type in ('invoice_fix','amount_invoiced') :
                obj = 'account.invoice'
                where.append(('date_invoice','>=',line.forecast_line_id.forecast_id.date_from))
                where.append(('date_invoice','<=',line.forecast_line_id.forecast_id.date_to))
                state_dict = {
                    'draft' : line.forecast_line_id.state_draft,
                    'open' : line.forecast_line_id.state_confirmed,
                    'paid' : line.forecast_line_id.state_done,
                    'cancel' : line.forecast_line_id.state_cancel
                    }
            else :
                obj = 'sale.order'
                where.append(('date_order','>=',line.forecast_line_id.forecast_id.date_from))
                where.append(('date_order','<=',line.forecast_line_id.forecast_id.date_to))
                state_dict = {
                    'draft' : line.forecast_line_id.state_draft,
                    'progress' : line.forecast_line_id.state_confirmed,
                    'done' : line.forecast_line_id.state_done,
                    'cancel' : line.forecast_line_id.state_cancel
                    }
            state = filter(lambda x : state_dict[x],state_dict)
            if state:
                where.append(('state','in',state))
            if line.forecast_line_id.segmento_id:
                where.append(('segmento_id','=',line.forecast_line_id.segmento_id.id))

            searched_ids = self.pool.get(obj).search(cr,uid,where)
            if  line.forecast_line_id.computation_type  in ('amount_sales','amount_invoiced') :
#                if line.computation_type == 'amount_sales':
#                    li='sale.order.line'
#                elif line.computation_type == 'amount_invoiced':
#                    li='account.invoice.line'
                res = self.pool.get(obj).browse(cr,uid,searched_ids)
                amount =0
                for r in res:
                    if line.forecast_line_id.computation_type == 'amount_sales' and product_id:
                        for sline in r.order_line:
                            if sline.product_id.type=='product' and sline.product_id.id in product_id:
                                amount += sline.price_subtotal
                    elif line.forecast_line_id.computation_type == 'amount_invoiced' and product_id:
                        for iline in r.invoice_line:
                            if iline.product_id.type=='product' and iline.product_id.id in product_id:
                                if r.type == 'out_invoice':
                                    amount += iline.price_subtotal
                                elif r.type == 'out_refund':  
                                    amount -= iline.price_subtotal
                    else:
                        amount += r.amount_untaxed
            self.write(cr, uid, [line.id], {'computed_amount':amount})
        return True

sale_forecast_line_categ()

class sale_forecast_line(osv.osv):
    _inherit = "sale.forecast.line"
    
#    def _final_evolution(self, cr, uid, ids, name, args, context={}):
#        forecast_line =  self.browse(cr, uid, ids, context=context)
#        result={}
#        for line in forecast_line:
#            where = []
#            where2=[]
#            if line.product_categ:
#                categ_id = map(lambda x : x.id ,line.product_categ)
#                where2.append(('categ_id','in',categ_id))
#            if line.product_product:
#                p_id = map(lambda x : x.id ,line.product_product)
#                where2.append(('id','in',p_id))
#            if line.line_categ_ids:
#                categ_id = map(lambda x : x.product_category_id.id ,line.line_categ_ids)
#                where2.append(('categ_id','in',categ_id))
#            product_id = self.pool.get('product.product').search(cr,uid,where2)
#            if line.computation_type == 'cases':
#                where.append(('user_id','=',line.salesman_id.name.id))
#            else:
#                where.append(('salesman_id','=',line.salesman_id.id))
#            if line.computation_type in ('invoice_fix','amount_invoiced') :
#                obj = 'account.invoice'
#                where.append(('date_invoice','>=',line.forecast_id.date_from))
#                where.append(('date_invoice','<=',line.forecast_id.date_to))
#                state_dict = {
#                    'draft' : line.state_draft,
#                    'open' : line.state_confirmed,
#                    'paid' : line.state_done,
#                    'cancel' : line.state_cancel
#                    }
##                self.pool.get('account.invoice.line').search(cr,uid,[('product_id','in',product_id)])
#            elif line.computation_type == 'cases' :
#                obj = 'crm.lead'
#                where.append(('create_date','>=',line.forecast_id.date_from))
#                where.append(('date_closed','<=',line.forecast_id.date_to))
#                state_dict = {
#                    'draft' : line.state_draft,
#                    'confirmed' : line.state_confirmed,
#                    'done' : line.state_done,
#                    'cancel' : line.state_cancel
#                    }
#                if line.crm_case_section:
#                    section_id = map(lambda x : x.id ,line.crm_case_section)
#                    where.append(('section_id','in',section_id))
#                if line.crm_case_categ:
#                    categ_id = map(lambda x : x.id ,line.crm_case_categ)
#                    where.append(('categ_id','in',categ_id))
#            else :
#                obj = 'sale.order'
#                where.append(('date_order','>=',line.forecast_id.date_from))
#                where.append(('date_order','<=',line.forecast_id.date_to))
#                state_dict = {
#                    'draft' : line.state_draft,
#                    'progress' : line.state_confirmed,
#                    'done' : line.state_done,
#                    'cancel' : line.state_cancel
#                    }
#            state = filter(lambda x : state_dict[x],state_dict)
#            if state:
#                where.append(('state','in',state))
#
#            searched_ids = self.pool.get(obj).search(cr,uid,where)
#            if  line.computation_type  in ('amount_sales','amount_invoiced') :
##                if line.computation_type == 'amount_sales':
##                    li='sale.order.line'
##                elif line.computation_type == 'amount_invoiced':
##                    li='account.invoice.line'
#                res = self.pool.get(obj).browse(cr,uid,searched_ids)
#                amount =0
#                for r in res:
#                    if line.computation_type == 'amount_sales' and product_id:
#                        for sline in r.order_line:
#                            if sline.product_id.type=='product' and sline.product_id.id in product_id:
#                                amount += sline.price_subtotal
#                    elif line.computation_type == 'amount_invoiced' and product_id:
#                        for iline in r.invoice_line:
#                            if iline.product_id.type=='product' and iline.product_id.id in product_id:
#                                if r.type == 'out_invoice':
#                                    amount += iline.price_subtotal
#                                elif r.type == 'out_refund':  
#                                    amount -= iline.price_subtotal
#                    else:
#                        amount += r.amount_untaxed
#                result[line.id]=amount
#            else:
#                result[line.id]=len(searched_ids)
#        return result

#    def _final_evolution(self, cr, uid, ids, name, args, context={}):
#        forecast_line =  self.browse(cr, uid, ids, context=context)
#        result={}
#        for line in forecast_line:
#            result[line.id] = 0.0
#            for lc in line.line_categ_ids:
#                result[line.id]+=lc.computed_amount
#        return result
    
    def _total_amount(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = {'amount_paid':0.0,
                               'computed_amount':0.0,
                               'amount':0.0}
            for lines in line.line_categ_ids:
                if lines.product_category_id and lines.amount>=0:
                    result[line.id]['amount'] += lines.amount
                result[line.id]['amount_paid'] += lines.amount_commission
                result[line.id]['computed_amount'] +=lines.computed_amount
        return result
    
#    def _total_amount_paid(self, cr, uid, ids, name, args, context=None):
#        result = {}
#        for line in self.browse(cr, uid, ids, context=context):
#            result[line.id] = 0.0
#            for lc in line.line_categ_ids:
#                result[line.id] = lc.amount_commission
#        return result
    
    def _get_line_forecast_categ(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.forecast.line.categ').browse(cr, uid, ids, context=context):
            result[line.forecast_line_id.id] = True
        return result.keys()
    
    _columns = {
        'salesman_id':fields.many2one('salesman.salesman', 'Salesman', readonly=True,states={"draft":[("readonly",False)]}),
        'segmento_id':fields.many2one('res.partner.segmento', 'Segmento', readonly=True,states={"draft":[("readonly",False)]}),
        'table_commission_id':fields.many2one('table.commission', 'table Commission', readonly=True,states={"draft":[("readonly",False)]}),
        'user_id': fields.related('salesman_id','user_id', type='many2one', relation='res.users', string='User', readonly=True, store=True),
        'date_from':fields.related('forecast_id','date_from',string="Date From", type="date",store=True),
        'date_to':fields.related('forecast_id','date_to',string="Date To", type="date",store=True),
        'computation_type' : fields.selection([('amount_invoiced','Amount Invoiced'),('amount_sales','Amount Sales'),],'Computation Base On',required=True, readonly=True,states={"draft":[("readonly",False)]}),
        'state': fields.selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done'),('cancel','Canceled')], 'State', required=True, readonly=True, select=1),
        #'amount_commission': fields.float('Amount Commission'),
        'payment_id': fields.many2one('account.payments', 'Payment', required=False),
        'move_line_id':fields.many2one('account.move.line', 'Move Line', readonly=True),
#        'computed_amount': fields.float('Real Value', readonly=True),
        'line_categ_ids':fields.one2many('sale.forecast.line.categ', 'forecast_line_id', 'Details for category', readonly=True,states={"draft":[("readonly",False)]}),
        'amount_paid': fields.function(_total_amount, type='float', string='Amount to paid',method=True, multi='amount_paid',),
        'amount': fields.function(_total_amount, type='float', string='Value Forecasted',method=True, multi='amount',
                                  store={
                                    'sale.forecast.line': (lambda self, cr, uid, ids, c={}: ids, ['line_categ_ids'], 3),
                                    'sale.forecast.line.categ': (_get_line_forecast_categ, 'amount', 4),
                                    },),
        'computed_amount': fields.function(_total_amount, string='Real Value',method=True, multi='computed_amount',
                                   store={
                                        'sale.forecast.line': (lambda self, cr, uid, ids, c={}: ids, ['line_categ_ids'], 5),
                                        'sale.forecast.line.categ': (_get_line_forecast_categ, ['computed_amount'], 6),
                                        },),
    }
    
    _defaults = {
        'state_confirmed' : True,
        'state_done' : True,
        'state':'draft',
    }
    
    
    def onchange_salesman(self, cr, uid, ids, salesman_id=None, context={}):
        default={'segmento_id':None}
        domain={}
        if salesman_id:
            salesman = self.pool.get('salesman.salesman').browse(cr, uid, salesman_id)
            segmento = [segment.id for segment in salesman.segmento_ids]
            default['segmento_id']= segmento and segmento[0] or None 
            default.update(self.onchange_segmento(cr, uid, ids, default['segmento_id'], context)['value'])
            domain={'segmento_id':[('id','in', segmento)]}
        return {'value':default,'domain':domain} 

    def onchange_segmento(self, cr, uid, ids, segmento_id=None, context={}):
        default={'table_commission_id':None}
        if segmento_id:
            segmento=self.pool.get('res.partner.segmento').browse(cr, uid, segmento_id, context)
            default['table_commission_id']=segmento.table_ids and segmento.table_ids[0].id or None
        return {'value':default}
    
    def action_calculate(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context):
            for lc in line.line_categ_ids:
                if not lc.product_category_id:
                    raise osv.except_osv(_('Error!'), _('The line must have a category of product.'))
                self.pool.get('sale.forecast.line.categ').action_calculate(cr, uid, [lc.id], context)
        return True
    
    def action_confirmed(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context):
            if not line.forecast_id:
                raise osv.except_osv(_('Error!'), _('You must selected a Forecast Sales.'))
            if not line.salesman_id.user_id.address_id:
                raise osv.except_osv('Error!', _(("The user %s must have a address and partner defined")%(line.salesman_id.user_id.name)))
            self.write(cr, uid, [line.id],{'state':'confirmed'})
        return True    
    
    def action_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state':'done'})
        forecast_dict={}
        for line in self.browse(cr, uid, ids, context):
            if line.amount_paid <= 0:
                continue
            if line.forecast_id.mode_id.check:
                if not line.forecast_id.one_check:
                    if line.forecast_id.mode_id.account_bank_id:
                        bank_account=line.forecast_id.mode_id.account_bank_id
                    else:
                        bank_id=self.pool.get('res.partner.bank').search(cr, uid, [('partner_id','=',line.forecast_id.company_id.partner_id.id),('default_bank','=',True)])
                        bank_account= bank_id and self.pool.get('res.partner.bank').browse(cr, uid, bank_id[0], context) or None
                    if not bank_account:
                        raise osv.except_osv(_('Error'), _('You must have a account bank by default'))
                    check_id=self.pool.get('account.payments').create(cr, uid, {
                                                                       'mode_id':line.forecast_id.mode_id.id,
                                                                       'type':'payment',
                                                                       'beneficiary':line.salesman_id.user_id.address_id.partner_id.beneficiary or line.salesman_id.user_id.address_id.partner_id.name or None,
                                                                       'received_date':line.forecast_id.date_to,
                                                                       'partner_id':line.salesman_id.user_id.address_id.partner_id.id,
                                                                       'amount':line.amount_paid,
                                                                       'bank_account_id':bank_account.id,
                                                                       'bank_id':bank_account.bank.id,
                                                                       'required_bank':True,
                                                                       'required_document':True,
                                                                       })
                    self.write(cr, uid, [line.id], {'payment_id':check_id})
                else:
                    if not forecast_dict.has_key(line.forecast_id):
                        forecast_dict[line.forecast_id]=line.amount_paid
                    else:
                        forecast_dict[line.forecast_id]+=line.amount_paid
        if forecast_dict:
            for forecast in forecast_dict.keys():
                if forecast.mode_id.account_bank_id:
                    bank_account=forecast.mode_id.account_bank_id
                else:
                    bank_id=self.pool.get('res.partner.bank').search(cr, uid, [('partner_id','=',forecast.company_id.partner_id.id),('default_bank','=',True)])
                    bank_account= bank_id and self.pool.get('res.partner.bank').browse(cr, uid, bank_id[0], context) or None
                if not bank_account:
                    raise osv.except_osv(_('Error'), _('You must have a account bank by default'))
                check_id=self.pool.get('account.payments').create(cr, uid, {
                                                           'mode_id':forecast.mode_id.id,
                                                           'type':'payment',
                                                           'beneficiary':forecast.beneficiary,
                                                           'received_date':forecast.date_to,
                                                           'partner_id':forecast.company_id.partner_id.id,
                                                           'amount':forecast_dict[forecast],
                                                           'bank_account_id':bank_account.id,
                                                           'bank_id':bank_account.bank.id,
                                                           'required_bank':True,
                                                           'required_document':True,
                                                           })
                forecast.write({'check_id':check_id})
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        checks=[]
        for line in self.browse(cr, uid, ids, context):
            if line.payment_id:
                if line.payment_id.state != 'draft':
                    raise osv.except_osv(_('Error'), _('you can not cancel the pay because exist check approve'))
                checks.append(line.payment_id.id)
        self.pool.get('account.payments').unlink(cr, uid, checks)
        self.write(cr, uid, ids,{'state':'cancel'})
        return True
    
    def action_set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state':'draft'})
        return True
sale_forecast_line()


class sale_forecast(osv.osv):
    _inherit = "sale.forecast"
    
    def _check_date(self,cr,uid,ids):
        b=True
        for forecast in self.browse(cr, uid, ids):
            if forecast.date_to < forecast.date_from:
                b=False
        return b
    
    def _forecast_rate(self, cr, uid, ids, field_names, args, context):
        res = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            value=1.00
            if forecast.line_ids:
                amount = reduce(lambda x, y: x + y.forecast_rate, forecast.line_ids, 0.0)
                avg = len(forecast.line_ids)
                value=amount/avg or 1.00
            res[forecast.id] = value
        return res
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id)])
        return period_ids[0]
    
    def _get_journal(self, cr, uid, ids, context=None):
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','=','commission')])
        if not journal_ids:
            return None
        return journal_ids[0]
    
    _columns = {
        'forecast_rate' : fields.function(_forecast_rate, method=True, string='Progress (%)'),
        'state': fields.selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done'),('cancel','Canceled')], 'State', required=True, readonly=True, select=1),
        "mode_id": fields.many2one("payment.mode","Mode",readonly=True,states={"draft":[("readonly",False)]}),
        'period_id': fields.many2one('account.period', 'Fiscal Period', domain=[('state','<>','done')], readonly=True, states={'draft':[('readonly',False)]}),
        'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True, states={'draft':[('readonly',False)]}),
        'check':fields.boolean('check?'),
        'one_check':fields.boolean('Only One Check', readonly=True, states={'draft':[('readonly',False)]}),
        'beneficiary':fields.char('Beneficiary', size=128, readonly=True, states={'draft':[('readonly',False)]}),
        'check_id':fields.many2one('account.payments', 'Check', required=False, readonly=True),
    }
    
    _defaults = {
                'period_id': _get_period,
                'journal_id':_get_journal,
                'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'sale.forecast.line', context=c),
                }
    
    _constraints = [
        (_check_date,'The date to must be greater than the date from',['date_from','date_to']),
        ]
    
    def onchange_mode(self, cr, uid, ids, mode=None, context={}):
        default={}
        if not mode:
            return {'value':default}
        mode = self.pool.get('payment.mode').browse(cr, uid, mode)
        default['check']= mode.check
        default['one_check']= False
        return {'value':default} 
    
    def action_confirmed(self, cr, uid, ids, context=None):
        line_ids=[]
        for forecast in self.browse(cr, uid, ids, context):
            line_ids = [line.id for line in forecast.line_ids if line.state=='draft']
        self.pool.get('sale.forecast.line').action_confirmed(cr, uid, line_ids, context)
        self.write(cr, uid, ids,{'state':'confirmed'})
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        line_ids=[]
        for forecast in self.browse(cr, uid, ids, context):
            if forecast.move_id:
                move_pool.button_cancel(cr, uid, [forecast.move_id.id], context={})
                move_pool.unlink(cr, uid, [forecast.move_id.id], context={})
            if forecast.check_id:
                if forecast.check_id.state != 'hold':
                    raise osv.except_osv(_('Error'), _('you can not cancel the pay because exist check approve'))
                self.pool.get('account.payments').unlink(cr, uid, [forecast.check_id.id])
            line_ids = [line.id for line in forecast.line_ids if line.state!='cancel']
        self.pool.get('sale.forecast.line').action_cancel(cr, uid, line_ids, context)
        self.write(cr, uid, ids,{'state':'cancel'})
        return True
    
    def action_set_draft(self, cr, uid, ids, context=None):
        line_ids=[]
        for forecast in self.browse(cr, uid, ids, context):
            line_ids = [line.id for line in forecast.line_ids]
        self.pool.get('sale.forecast.line').action_set_draft(cr, uid, line_ids, context)
        self.write(cr, uid, ids,{'state':'draft'})
        return True
    
    def action_done(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        seq_obj = self.pool.get('ir.sequence')
        if context is None:
            context={}
        context['search_shop']=True
        for forecast in self.browse(cr, uid, ids, context):
            if not forecast.company_id.property_account_commission_sales:
                raise osv.except_osv('Error!', _("You must select a account of commission in the company"))
            if not forecast.journal_id:
                raise osv.except_osv('Error!', _("You must select a journal of commission for this forecast"))
            cod=seq_obj.get_id(cr, uid, forecast.journal_id.sequence_id.id)
            if forecast.name:
                name=forecast.name
            else:
                name=cod
            moves=[]
            lines=[]
            total=0
            move = {'name': name,
                    'journal_id': forecast.journal_id.id,
                    'date': forecast.date_to,
                    'ref': cod+'-'+forecast.name or '',
                    'period_id': forecast.period_id.id or False
                    }
            move_id = move_pool.create(cr, uid, move, context)
            for line in forecast.line_ids:
#                b=True
#                if forecast.company_id.value_commission >0:
#                    if line.forecast_rate < forecast.company_id.value_commission:
#                        b=False
#                if b:
#                    if line.amount_commission <=0:
#                        raise osv.except_osv('Error!', _("The amount commission must be greater than zero"))
#                    if line.forecast_rate<100:
#                        amount= (line.amount_commission * line.forecast_rate)/100
#                    else:
#                        amount= line.amount_commission
                if line.amount_paid>0:
                    ref=forecast.name+'-'+line.salesman_id.user_id.name
                    move_line = {
                        'name': forecast.name or '/',
                        'ref':ref,
                        'debit': round(line.amount_paid,2),
                        'credit': 0,
                        'account_id': forecast.company_id.property_account_commission_sales.id,
                        'move_id': move_id,
                        'journal_id': forecast.journal_id.id,
                        'period_id': forecast.period_id.id,
                        'partner_id': line.salesman_id.user_id.address_id.partner_id.id,
                        'date': forecast.date_to,
                        }
                    move_line_id=move_line_pool.create(cr, uid, move_line, context)
                    self.pool.get('sale.forecast.line').write(cr, uid, [line.id], {'move_line_id':move_line_id}, context)
                    moves.append(move_line_id)
                    total+=round(line.amount_paid,2)
                lines.append(line.id)
            if total>0:
                move_line_id = move_line_pool.create(cr, uid, {
                    'name': forecast.name,
                    'ref': forecast.name+'-'+forecast.mode_id.name,
                    'debit': 0,
                    'credit': total,
                    'account_id': forecast.mode_id.credit_account_id.id,
                    'move_id': move_id,
                    'journal_id': forecast.journal_id.id,
                    'period_id': forecast.period_id.id,
                    'partner_id': forecast.company_id.partner_id.id,
                    'date': forecast.date_to,
                    }, context)
                moves.append(move_line_id)
            self.pool.get('sale.forecast.line').action_done(cr, uid, lines, context)
            if moves:
                move_pool.post(cr, uid, [move_id], context=context)
            else:
                move_pool.unlink(cr, uid, [move_id], context=context)
                move_id=None
            self.write(cr, uid, [forecast.id], {'move_id':move_id,'state':'done'})
        return True
        
sale_forecast()