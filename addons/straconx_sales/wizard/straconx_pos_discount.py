# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#
##############################################################################

from osv import osv, fields
import decimal_precision as dp

class pos_discount(osv.osv_memory):
    _inherit = 'invoice.discount'


    def apply_discount(self, cr, uid, ids, context=None):
        order_ref = self.pool.get('account.invoice')
        order_line_ref = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)
        if isinstance(record_id, (int, long)):
            record_id = [record_id]
        b=True
        for order in order_ref.browse(cr, uid, record_id, context=context):
            if self.pool.get('res.users').browse(cr, uid, uid, context=None).max_offer < this.offer:
                b=False
            for line in order.invoice_line:
                if line.discount > 0.00:
                    context.update({'invoice_line_tax_id':line.invoice_line_tax_id})
                    values=order_line_ref.onchange_offer(cr, uid, [line.id], line.product_id.id, this.offer, line.quantity, line.price_unit,line.margin,line.price_product,line.discount,line.invoice_line_tax_id,line.price_iva,line.invoice_id.fiscal_position.id,context=context)['value']
                    values.update({'offer':this.offer,'authorized':b})
                    line.write(values)
        order_ref.button_reset_taxes(cr, uid, record_id, context)
        return {}

pos_discount()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
