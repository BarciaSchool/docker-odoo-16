# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
##############################################################################

from osv import osv, fields
import decimal_precision as dp

class action_purchase_discount(osv.osv_memory):
    _name = 'purchase.discount'

    _columns = {
        'discount': fields.float('Descuento (%)', digits_compute=dp.get_precision('Account'))
    }
    _defaults = {
        'discount': 30,
    }
#    @profile
    def apply_discount(self, cr, uid, ids, context=None):
        order_ref = self.pool.get('account.invoice')
        order_line_ref = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)
        if isinstance(record_id, (int, long)):
            record_id = [record_id]
        discount = this.discount
        b=True
        for order in order_ref.browse(cr, uid, record_id, context=context):
            for line in order.invoice_line:
                values=order_line_ref.onchange_offer(cr, uid, [line.id], line.product_id.id, 0.00, line.quantity, line.price_unit,line.margin,line.price_product,discount,line.invoice_line_tax_id,line.price_iva,context=context)['value']
                values.update({'discount':this.discount,'authorized':b})
                price_unit = values.get('price_unit',0)
                price_subtotal = values.get('price_subtotal',0)
                cr.execute("""update account_invoice_line set  write_date =now(), price_unit = %s, discount=%s, price_subtotal =%s, authorized=True where id =%s""",(price_unit, discount, price_subtotal, line.id))
#                 line.write(values)
        order_ref.button_reset_taxes(cr, uid, record_id, context)
        return {}

action_purchase_discount()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
