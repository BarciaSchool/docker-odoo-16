from osv import osv, fields
from tools.translate import _
import netsvc
from datetime import datetime
import pooler
import time

class approve_invoice(osv.osv_memory):
    _name = "approve.invoice"
    _inherit = "res.config.installer"
    _columns = {
              'company_id': fields.many2one('res.company', 'Company', required=True),
              'create_payment': fields.boolean('Create Payments?'),
              }
    
    def execute(self, cr, uid, ids, context=None):
        if(context is None):
            context = {}
        context['force_availability'] = True
        browse_approve_invoice_list = self.browse(cr, uid, ids, context)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'moves')], limit=1)
        wf_service = netsvc.LocalService("workflow")
        for browse_approve_invoice in browse_approve_invoice_list:
            invoice_ids = self.pool.get("account.invoice").search(cr, uid, [('migrate', '=', True), ('state', '=', 'draft'), ('company_id', '=', browse_approve_invoice.company_id.id)])
            for invoice in invoice_ids:
                wf_service.trg_validate(uid, 'account.invoice', invoice, 'invoice_open', cr)
                cr.commit()
                invoice = self.pool.get('account.invoice').browse(cr, uid, invoice)
                if invoice.migrate:
                    if invoice.is_paid and invoice.type == 'out_invoice':
                        cr.execute('select payment_id from rel_shop_payment rs, payment_mode pm where pm.id = payment_id and shop_id = %s and pm.only_receipt = True and pm.cash = True', [invoice.shop_id.id, ])
                        paids = cr.fetchall()
                        paids = [i[0] for i in paids]
                        payments = {
                           'mode_id':paids[0],
                           'type':'receipt',
                           'received_date':invoice.date_invoice,
                           'partner_id':invoice.partner_id.id,
                           'amount':round(invoice.amount_total, 2),
                           'amount_received':round(invoice.amount_total, 2)
                           }
                        context.update({'active_model':'account.invoice', 'active_ids':[invoice.id], 'active_id':invoice.id})
                        pays = self.pool.get('wizard.invoice.pay').create(cr, uid, {'partner_id':invoice.partner_id.id,
                                                                           'shop_id':invoice.shop_id.id,
                                                                           'journal_id':journal_ids and journal_ids[0] or None,
                                                                           'amount':round(invoice.amount_total, 2),
                                                                           'paid':round(invoice.amount_total, 2),
                                                                           'payment_ids':[[0, 0, payments]],
                                                                           }, context)
                        self.pool.get('wizard.invoice.pay').pay(cr, uid, [pays], context)
                        cr.commit()
                    
approve_invoice()
