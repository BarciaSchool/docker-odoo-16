# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2012-2013 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
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
import time
import datetime

class account_voucher(osv.osv):
    _inherit="account.voucher"
    _columns={
              'type_collect_employee':fields.selection([('normal','Normal'),('by_discount','By Discount'),],'Type Collect Employee',readonly=True, states={'draft': [('readonly', False)]}),
              'discount_id':fields.many2one('hr.discount', 'Discount', required=False),
              }
    _defaults={'type_collect_employee':'normal'}
    
    def __get_contract(self,cr,uid,partner_id,context=None):
        OBJ_HR_CONTRACT=self.pool.get("hr.contract")
        OBJ_RES_USERS=self.pool.get("res.users")
        srch_hr_employee=self.pool.get("hr.employee").search(cr,uid,[('partner_id','=',partner_id),('unemployee','!=',True)])
        if(not srch_hr_employee):
            raise osv.except_osv(_('Validation Error!'),_("You can use a DISCOUNT OF COLLABORATOR to cancel an invoice if you are an active employee."))
        srch_hr_contract=OBJ_HR_CONTRACT.search(cr,uid,[('employee_id','=',srch_hr_employee[0])])
        if(not srch_hr_contract):
            raise osv.except_osv(_('Validation Error!'),_("The employee has no contract."))
        srch_res_users=OBJ_RES_USERS.search(cr,uid,[('partner_id','=',partner_id)])
        if(uid in srch_res_users):
            raise osv.except_osv(_('Validation Error!'),_("Can not bill the employee with current user.")) 
        return OBJ_HR_CONTRACT.browse(cr,uid,srch_hr_contract[0],context=context)  
    
    def proforma_voucher(self, cr, uid, ids, context=None):
        check_amount = 0.00
        res= super(account_voucher,self).proforma_voucher(cr, uid, ids, context)
        mod_obj = self.pool.get('ir.model.data')
        discount=[]
        discount_pool = self.pool.get('hr.discount')
        for voucher in self.browse(cr, uid, ids, context):
            if not voucher.discount_id:
                if voucher.type_collect_employee == 'by_discount':
                    if len(voucher.payments)> 1:
                        raise osv.except_osv(_('Invalid action!'), _('You must be to create one payline in the voucher when is discount the employee.'))
                    employee_ids=self.pool.get('hr.employee').search(cr, uid, [('partner_id','=',voucher.partner_id.id)])
                    if not employee_ids:
                        raise osv.except_osv(_('Invalid action!'), _('There is not an employee created for this Partner'))
                    vals=discount_pool.onchange_employee_id(cr, uid, [], employee_ids[0],time.strftime('%Y-%m-%d'), context)['value']
                    vals.update(discount_pool.onchange_date(cr, uid, [], time.strftime('%Y-%m-%d'), vals['company_id'], context)['value'])
                    move_line_ids=self.pool.get('account.move.line').search(cr, uid, [('move_id','=',voucher.move_id.id),('account_id','=',voucher.payments[0].mode_id.debit_account_id.id)])
                    vals.update({'ref':'discount by invoice %s'%voucher.invoice_id.number or '',
                                 'amount':voucher.amount,
                                 'payment_form':'payment',
                                 'type':'discount',
                                 'mode_id':voucher.payments[0].mode_id.id,
                                 'user_id':uid,
                                 'employee_id': employee_ids[0],
                                 'debit_move_line': move_line_ids and move_line_ids[0] or None
                          })
                    discount_id=discount_pool.create(cr, uid,vals,context)
                    discount.append(discount_id)
                    voucher.write({'discount_id':discount_id})
            if voucher.payments:
                for pay in voucher.payments:
                    if pay.discount_employee:
                        OBJ_HR_DISCOUNT=self.pool.get("hr.discount")
                        OBJ_IR_SEQUENCE=self.pool.get('ir.sequence')
                        brw_hr_contract=self.__get_contract(cr, uid, pay.partner_id.id, context=context)
                        values={'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                                'date_from':time.strftime('%Y-%m-%d'),                        
                                'interest':0.00,
                                'number_of_quotas':pay.number_of_quotas,
                                'amount':pay.amount,
                                'payment_form':'payment',
                                'contract_id':brw_hr_contract.id,
                                'ref': voucher.line_cr_ids[0].move_line_id.ref or OBJ_IR_SEQUENCE.get(cr, uid, 'cv.collaborator.discount'),
                                'name': self.pool.get("hr.transaction.type").search(cr,uid,[('type_expense','=','discount'),('code','=','cvdiscount')])[0],
                                'collection_form':pay.collection_form,
                                'type':'discount',
                                'state':'draft',
                                'value_quota': pay.amount_partial,
                                'mode_id': pay.mode_id.id,
                                'shop_id': pay.shop_id.id,
                                'employee_id': brw_hr_contract.employee_id.id,
                                'partner_id': pay.partner_id.id,
                                    }
                        hr_discount_id=OBJ_HR_DISCOUNT.create(cr,uid,values,context=context)
                        OBJ_HR_DISCOUNT.write(cr, uid, [hr_discount_id],
                                               {"value_quota":pay.amount_partial})
                        hr_dis = OBJ_HR_DISCOUNT.browse(cr, uid, hr_discount_id)
                        #OBJ_HR_DISCOUNT.create_lines_discount(cr, uid,hr_dis,context=context)
                        OBJ_HR_DISCOUNT.button_create_discount(cr, uid,[hr_dis.id],context=context)
                        if hr_dis.lines_ids:
                            for line in hr_dis.lines_ids:
                                check_amount += line.amount
                        if round(pay.amount,2) == round(check_amount,2):
                            OBJ_HR_DISCOUNT.button_approve(cr, uid,[hr_discount_id],context=context)
                        discount.append(hr_discount_id)
        if discount:
            tree_res = mod_obj.get_object_reference(cr, uid, 'straconx_talent_human', 'hr_discount_tree_view')
            tree_id = tree_res and tree_res[1] or False
            form_res = mod_obj.get_object_reference(cr, uid, 'straconx_talent_human', 'hr_discount_form_view')
            form_id = form_res and form_res[1] or False
            search_id = mod_obj.get_object_reference(cr, uid, 'straconx_talent_human', 'hr_discount_search_view')
            return {
                'domain': "[('id', 'in',"+str(discount)+")]",
                'name':'Discount Employee',
                'view_type': 'form',
                'view_mode': 'tree, form',
                'search_view_id': search_id and search_id[1] or False ,
                'res_model': 'hr.discount',
                'views': [(tree_id, 'tree'),(form_id, 'form')],
                'type': 'ir.actions.act_window',
                'nodestroy': True,
            }
        return res
    
    def cancel_voucher(self, cr, uid, ids, context=None):
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.discount_id:
                if voucher.discount_id.state != 'draft':
                    raise osv.except_osv(_('Invalid action!'), _('You can not cancel the voucher because exist a discount in state invalid, please check.'))
        return super(account_voucher,self).cancel_voucher(cr, uid, ids, context)
account_voucher()