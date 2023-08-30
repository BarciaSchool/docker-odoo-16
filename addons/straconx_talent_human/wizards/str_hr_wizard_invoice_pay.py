from osv import osv,fields
import decimal_precision as dp
from tools.translate import _
import time

class wizard_invoice_pay(osv.osv_memory):
    _inherit="wizard.invoice.pay"
    
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
    
    def append_payment(self,cr,uid,payment_ids,pay,invoice,context=None):
        check_amount = 0.00
        OBJ_ACCOUNT_PAYMENTS=self.pool.get('account.payments')
        if self.is_oneline2pay(pay):
            payment_id=OBJ_ACCOUNT_PAYMENTS.create(cr, uid,self.get_dict_payment(cr, uid, payment_ids, pay,invoice,context=context))
            payment_ids.append(payment_id)
            if pay.discount_employee:
                OBJ_HR_DISCOUNT=self.pool.get("hr.discount")
                OBJ_IR_SEQUENCE=self.pool.get('ir.sequence')
                brw_hr_contract=self.__get_contract(cr, uid,invoice.partner_id.id, context=context)
                values={'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                        'date_from':time.strftime('%Y-%m-%d'),                        
                        'interest':0.00,
                        'number_of_quotas':pay.number_of_quotas,
                        'amount':pay.amount,
                        'payment_form':'payment',
                        'contract_id':brw_hr_contract.id,
                        'ref':invoice.invoice_number_out or OBJ_IR_SEQUENCE.get(cr, uid, 'cv.collaborator.discount'),
                        'name':self.pool.get("hr.transaction.type").search(cr,uid,[('type_expense','=','discount'),('code','=','cvdiscount')])[0],
                        'collection_form':pay.collection_form,
                        'type':'discount',
                        'state':'draft',
                        'value_quota':pay.amount_partial,
                        'mode_id':pay.mode_id.id,
                        'shop_id': pay.shop_id.id,
                        'employee_id':brw_hr_contract.employee_id.id,
                        'partner_id':invoice.partner_id.id,
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
                OBJ_ACCOUNT_PAYMENTS.write(cr,uid,[payment_id],
                                        {"discount_id":hr_discount_id,
                                         "invoice_id":invoice.id})
                cr.execute("update account_invoice set has_discount_employee=%s where id=%s",(True,invoice.id))
        return payment_ids
    
wizard_invoice_pay()


class wizard_invoice_pay_lines(osv.osv_memory):
    _inherit="wizard.invoice.pay.lines"
    
    def _calculate_amount_partial(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for line in self.browse(cr, uid, ids, context=context):                
                res[line.id] = line.number_of_quotas and round(line.amount/line.number_of_quotas,2) or 0
            return res
        
    _columns={
              "discount_employee":fields.boolean("Discount employee"),
              "number_of_quotas":fields.integer("Quotas"),
              'collection_form':fields.selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', select=True, readonly=True,states={'draft': [('readonly', False)]}),
              "amount_partial":fields.function(_calculate_amount_partial, method=True, string='Next Amount Paid', store=True, digits_compute=dp.get_precision('Sale Price')),            
              }
    _defaults={
               "number_of_quotas":1
               }
    
#     def on_change_mode_payment(self, cr, uid, ids, mode=False, partner=False, amount=0.00, type='receipt', company_id=False, payment_date=False, context=None, received_date=False, shop_id=False):
#         OBJ_HR_EMPLOYEE=self.pool.get("hr.employee")
#         result=super(wizard_invoice_pay_lines, self).on_change_mode_payment(cr, uid, ids, mode, partner, amount, type, company_id, payment_date, context, received_date, shop_id)
#         if mode:            
#             mode_pay=self.pool.get('payment.mode').browse(cr, uid, mode, context=context)
#             result['value']['mode_id']=mode_pay.id
#             if(mode_pay.discount_employee and mode_pay.collect_employee):
#                 srch_hr_employee=OBJ_HR_EMPLOYEE.search(cr,uid,[('partner_id','=',partner),('unemployee','!=',True)])
#                 result['value']['discount_employee']=srch_hr_employee
#                 result['value']['number_of_quotas']=srch_hr_employee and 1 or 0
#                 result['value']['name']=srch_hr_employee and None
#                 if(not srch_hr_employee):
#                     result['value']['mode_id']=False
#                     result['warning']={'title':_('Validation Error!'),'message':_("You can use a DISCOUNT OF COLLABORATOR to cancel an invoice if you are an active employee or is the active user.")}
#                     return result
#                 return result
#             result['value']['discount_employee']=False
#             result['value']['number_of_quotas']=0
#         return result
    
    def onchange_number_of_quotas(self,cr,uid,ids,number_of_quotas,discount_employee,amount,context=None):
        if(discount_employee):
            if(number_of_quotas):
                if(number_of_quotas<0):                    
                    number_of_quotas=number_of_quotas*-1
                    return {"value":{"number_of_quotas":number_of_quotas,
                                     "amount_partial":round(amount/(float(number_of_quotas)),2)
                                     },"warning":{"title":_("Validation Error!"),"message":_("The number of quotas to pay must be greater than 0")}}
                return {"value":{"amount_partial":round(amount/(float(number_of_quotas)),2)}}
            return {"value":{"number_of_quotas":1,"amount_partial":amount},"warning":{"title":_("Validation Error!"),"message":_("The number of quotas to pay must be greater than 0")}}
        return {"value":{"number_of_quotas":0,"amount_partial":0}}
    
wizard_invoice_pay_lines()