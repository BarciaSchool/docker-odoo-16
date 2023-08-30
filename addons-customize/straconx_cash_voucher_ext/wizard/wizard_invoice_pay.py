from osv import osv,fields

class wizard_invoice_pay(osv.osv_memory):
    _inherit="wizard.invoice.pay"
    
    def is_oneline2pay(self,pay):
        return pay.is_cash_voucher
    
    def append_payment(self,cr,uid,payment_ids,pay,context=None):
        value=self.get_dict_payment(cr,uid,payment_ids,pay,context=context)
        if self.is_oneline2pay(pay):
            payment_ids.append(self.pool.get('account.payments').create(cr, uid,value))
        else:         
            total=0                   
            for i in range(1,pay.number_cash_voucher):
                amount=pay.amount/pay.number_cash_voucher
                if(i!=pay.number_cash_voucher):
                    total+=amount
                else:
                    amount=pay.amount-total
                value['amount']=amount
                value['is_cash_voucher']=True
                value['user_id']=uid
                payment_ids.append(self.pool.get('account.payments').create(cr, uid,value))
        return payment_ids
    
wizard_invoice_pay()

class wizard_invoice_pay_lines(osv.osv_memory):
    _inherit="wizard.invoice.pay.lines"
    
    _columns={
              "number_cash_voucher":fields.integer("# Fees"),
              }
    
    def onchange_number_cash_voucher(self,cr,uid,number_cash_voucher,is_cash_voucher,context=None):
        if(is_cash_voucher):
            if(number_cash_voucher):
                if(number_cash_voucher<0):
                    return {"value":{"number_cash_voucher":number_cash_voucher*-1},"warning":{"title":_("Validation Error!"),"message":_("The number of cash vouchers to pay must be greater than 0")}}
            return {"value":{"number_cash_voucher":1},"warning":{"title":_("Validation Error!"),"message":_("The number of cash vouchers to pay must be greater than 0")}}
        return {"value":{"number_cash_voucher":0}}
    
wizard_invoice_pay_lines()