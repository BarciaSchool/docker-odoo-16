from osv import osv,fields

class payment_mode(osv.osv):
    _inherit="payment.mode"
    _columns={
              "is_cash_voucher":fields.boolean("Cash Voucher"),
              }
    
payment_mode()

class account_payments(osv.osv):
    _inherit = "account.payments"
    
    def on_change_mode_payment(self, cr, uid, ids, mode=False, partner=False, amount=0.00, type='receipt', company_id=False, payment_date=False, supplier=None, line_payments_ids=[], context=None, received_date=False, shop_id=False):
        result=super(account_payments, self).on_change_mode_payment(cr, uid, ids, mode, partner, amount, type, company_id, payment_date, supplier, line_payments_ids, context, received_date, shop_id)
        if mode:
            mode_pay=self.pool.get('payment.mode').browse(cr, uid, mode, context=context)
            result['value']['is_cash_voucher']=mode_pay.is_cash_voucher
        return result
    
account_payments()