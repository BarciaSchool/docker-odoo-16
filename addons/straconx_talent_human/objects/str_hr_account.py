# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from osv import fields,osv
from tools.translate import _
import decimal_precision as dp
import tools
import netsvc

class hr_account_position(osv.osv):
    _name = 'hr.account.position'
    _description = 'Human Resource Account Position'
    
    
    def _get_rule_id(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
#        res={}
#        rule_pool = self.pool.get('hr.salary.rule')
#        area_pool = self.pool.get('account.area')
#        result = []
        if fields and fields.get('rule_id',False):
            ids = fields.get('rule_id',False)
            if ids:
                return ids
            else:
                return None
#             area_ids = area_pool.search(cr,uid,[])
#             if area_ids:
#                 for a in area_ids:
#                     result = ({
#                     'area_id':area_pool.browse(cr,uid,a).id or None,
#                     'account_debit':rule_pool.browse(cr,uid,ids).account_debit.id or None,
#                     'account_credit':rule_pool.browse(cr,uid,ids).account_credit.id or None,
#                     'rule_id':rule_pool.browse(cr,uid,ids).id or None,
#                     })
#                     rule_pool.write(cr,uid,ids,{'account_ids':result})                        
            
    _columns = {
        'area_id': fields.many2one('account.area', 'Area'),
        'account_debit': fields.many2one('account.account', 'Debit Account'),
        'account_credit': fields.many2one('account.account', 'Credit Account'),
        'rule_id':fields.many2one('hr.salary.rule', 'Salary Rule', select=True),        
        }

    _defaults = {
        'rule_id': _get_rule_id
                 }
    _sql_constraints = [('rule_area_uniq', 'unique (area_id,rule_id)','Salary Rule x Area must be unique. Please check !')]
    
    
hr_account_position()
                    
                    
                    
class account_move_line(osv.osv):
    _inherit = "account.move.line"
                    
    _columns={
            'l_discount_id': fields.many2one('hr.discount.lines','Discount Line')            
              }

account_move_line()


class account_payments(osv.osv):
    _inherit = "account.payments"
                    
    def create_check(self, cr, uid, ids, mode_id, name, date, partner_id, amount, account_bank, bank_id, prov_id = False, slip_id = False, inv_id=False, cheque_id=False, shop_id = False,context = None):
        if prov_id:
            if not cheque_id:
                check_book = self.pool.get('check.receipt').search(cr, uid,[('state','=','open'),('bank','=',bank_id)])[0]
                cheque_id = self.pool.get('check.receipt').search(cr, uid,[('state','=','open'),('book_id','=',check_book)])[0]
            cheque = self.pool.get('check.receipt').browse(cr, uid,cheque_id)
            check_id = self.create(cr, uid, {
                                           'mode_id':mode_id,
                                           'type':'payment',
                                           'beneficiary':name,
                                           'received_date':date,
                                           'partner_id':partner_id,
                                           'amount':amount,
                                           'bank_account_id':account_bank,
                                           'bank_id':bank_id,
                                           'provision_id':prov_id,
                                           'shop_id':shop_id,
                                           'cheque_id':cheque_id,
                                           'required_bank':True,
                                           'required_document':True,
                                           'name': cheque.name,
                                           'state': 'paid'
                                           }, context = context)
        if slip_id:
            if not cheque_id:
                cheque_id = self.pool.get('check.receipt').search(cr, uid,[('state','=','open'),('book_id.bank','=',bank_id)])[0]
#                 cr.execute("""select id from check_receipt where state ='open' and book_id = (select id from check_book where bank = %s) """,(bank_id,))
#                 result = cr.fetchall()
#                 if result:
#                     print result[0][0]
#                     cheque_id = result[0][0]
                     
            check_id = self.create(cr, uid, {
                                           'mode_id':mode_id,
                                           'type':'payment',
                                           'beneficiary':name,
                                           'received_date':date,
                                           'partner_id':partner_id,
                                           'amount':amount,
                                           'bank_account_id':account_bank,
                                           'bank_id':bank_id,
                                           'slip_id':slip_id,
                                           'shop_id':shop_id,
                                           'cheque_id':cheque_id,
                                           'required_bank':True,
                                           'required_document':True,
                                           'state': 'draft'
                                           }, context = context)
        if inv_id:
            cheque_id = self.pool.get('check.receipt').search(cr, uid,[('state','=','open'),('bank_id','=',bank_id)])[0]
            check_id = self.create(cr, uid, {
                                           'mode_id':mode_id,
                                           'type':'payment',
                                           'beneficiary':name,
                                           'received_date':date,
                                           'partner_id':partner_id,
                                           'amount':amount,
                                           'bank_account_id':account_bank,
                                           'bank_id':bank_id,
                                           'invoice_id':inv_id,
                                           'shop_id':shop_id,
                                           'cheque_id':cheque_id,
                                           'required_bank':True,
                                           'required_document':True,
                                           'state': 'draft'
                                           }, context = context)            
        return check_id
account_move_line()                    