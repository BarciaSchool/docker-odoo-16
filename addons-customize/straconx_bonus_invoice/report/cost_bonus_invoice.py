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
from report import report_sxw
import time

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        active_id=context['active_id']
        browse_report_bonus=self.pool.get("wizard.report.bonus").browse(cr,uid,active_id,context)
        browse_res_user=self.pool.get("res.users").browse(cr,1,uid,context)
        company_filter=""
        product_filter=""
        partner_filter=""
        date_filter=""
        company_name="Todas"
        if(browse_report_bonus):
            company_filter=browse_report_bonus.company_id and "and company_id=%s" %(browse_report_bonus.company_id.id) or ""
            product_filter=browse_report_bonus.product_id and "and product_id=%s" %(browse_report_bonus.product_id.id) or ""
            partner_filter=browse_report_bonus.partner_id and "and partner_id=%s" %(browse_report_bonus.partner_id.id) or ""
            date_filter=(browse_report_bonus.initial_date and browse_report_bonus.end_date) and "and invoice_id in(select id from account_invoice where date_invoice between '%s' and '%s')" %(browse_report_bonus.initial_date,browse_report_bonus.end_date) or browse_report_bonus.initial_date and "and invoice_id in (select id from account_invoice where date_invoice >='%s')" % (browse_report_bonus.initial_date) or browse_report_bonus.end_date and "and invoice_id in (select id from account_invoice where date_invoice <='%s')" % (browse_report_bonus.end_date) or ""
            company_name=browse_report_bonus.company_id and browse_report_bonus.company_id.name or "Todas"
        cr.execute("""select il.id as id,
                       pp.default_code as default_code,
                       pp.name_template as name,
                       il.cost as cost,
                       il.bonus as bonus
                       from
                        (select product_id as id
                            from stock_move where bonus_qty>0
                            and state='done' %s %s %s
                            group by product_id) as sm,
                        (select product_id as id,
                            sum(bonus_qty) as bonus,
                            sum(bonus_qty*price_product) as cost
                            from account_invoice_line where bonus_qty>0 and state='paid' %s %s %s %s
                            group by product_id) as il,
                        product_product as pp
                        where il.id=sm.id and il.id=pp.id""" % (company_filter,product_filter,partner_filter,company_filter,product_filter,partner_filter,date_filter))
        detail=cr.fetchall()
        total_cost = reduce(lambda x,record: x + record[3], detail, 0.0)        
        self.localcontext.update({
            'detail':detail,
            'login':browse_res_user.login,
            'total_cost':total_cost,
            "company_name":company_name,
            "print_date":time.strftime("%Y-%m-%d %H:%M:%S"),        
        })
        self.context = context