# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved  
#
##############################################################################

import time

from osv import fields, osv
from tools.translate import _
import netsvc
from account_voucher import account_voucher

class account_invoice_refund(osv.osv_memory):

    """Refunds invoice"""
    
    def _get_invoice(self, cr, uid, context={}):
        if context is None:
            context = {}
        if context.get('active_id',None):
            return context.get('active_id',None)

#     def _get_shop_id(self,cr,uid,context={}):
#         if context.get('active_id',None):
#             invoice_id = context.get('active_id',None)
#             if invoice_id:
#                 inv_id = self.pool.get('account.invoice').browse(cr,uid,invoice_id)
#                 if inv_id and inv_id.shop_id:
#                     return inv_id.shop_id.id
#                 else:
#                     return []
# 
#     def _get_printer_id(self,cr,uid,context={}):
#         if context.get('active_id',None):
#             invoice_id = context.get('active_id',None)
#             if invoice_id:
#                 inv_id = self.pool.get('account.invoice').browse(cr,uid,invoice_id)
#                 if inv_id and inv_id.printer_id:
#                     return inv_id.printer_id.id
#                 else:
#                     return []

    _inherit = "account.invoice.refund"
    _columns = {
                'required_auth':fields.boolean('required authorized', required=False),
                'user_authorized': fields.many2one('res.users', 'User Authorized'),
                'invoice_id': fields.many2one('account.invoice', 'Invoice'),
#                 'shop_id': fields.many2one('sale.shop', 'Tienda'),
#                 'printer_id': fields.many2one('printer.point','Caja'),
                'date2': fields.datetime('Refund date', help='This date will be used as the invoice date for Refund Invoice and Period will be chosen accordingly!'),
                'motive': fields.many2one('account.refund.motive', 'Motive', required=True),
                'filter_refund': fields.selection([('internal','Interna'),('refund', 'Autorizada SRI'), ('cancel', 'Anular factura')], "Refund Type", required=True, help='Refund invoice base on this type. You can not Modify and Cancel if the invoice is already reconciled'),
                'line_ids':fields.one2many('invoice.refund.line', 'wizard_id', 'Lines', required=False),
    }

    _defaults = {
        'date2': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'filter_refund': 'refund',
        'invoice_id':_get_invoice,
#         'shop_id': _get_shop_id,
#         'printer_id': _get_printer_id,
    }
    
    def on_change_motive(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        inv_type = context.get('type', 'out_invoice')
        motive_ids=[]
        if inv_type== 'out_invoice':
            motive_ids=self.pool.get('account.refund.motive').search(cr, uid, [('classification','in',('sales','all'))])
        elif inv_type== 'in_invoice':
            motive_ids=self.pool.get('account.refund.motive').search(cr, uid, [('classification','in',('purchase','all'))])
        return {'domain':{'motive':[('id','in', motive_ids)]}}
    
    def onchange_line_ids(self, cr, uid, ids, line_ids, context=None):
        res={'required_auth':False}
        if not line_ids:
            return {'value':res}
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, self.pool.get('invoice.refund.line'), line_ids, ['product_id'], context)
        for line in line_dr_ids:
            product_id = line.get('product_id',None)
            product = product_id and self.pool.get('product.product').browse(cr, uid, product_id, context) or None
            if product and not product.categ_id.permit_refund:
                res['required_auth'] = True
        return {'value': res}

    def compute_refund(self, cr, uid, ids, mode='refund', context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: the account invoice refund’s ID or list of IDs

        """
        inv_obj = self.pool.get('account.invoice')
        reconcile_obj = self.pool.get('account.move.reconcile')
        account_m_line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        wf_service = netsvc.LocalService('workflow')
        inv_tax_obj = self.pool.get('account.invoice.tax')
        inv_line_obj = self.pool.get('account.invoice.line')
        res_users_obj = self.pool.get('res.users')
        if context is None:
            context = {}

        for form in self.browse(cr, uid, ids, context=context):
            created_inv = []
            date = False
            period = False
            description = False
            company = res_users_obj.browse(cr, uid, uid, context=context).company_id
            if not form.line_ids and form.filter_refund <> 'cancel':
                raise osv.except_osv(_('Error !'), _('Usted debe ingresar por lo menos un producto de devolución'))
            journal_id = form.journal_id.id
            for inv in inv_obj.browse(cr, uid, context.get('active_ids'), context=context):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise osv.except_osv(_('Error !'), _('Can not %s draft/proforma/cancel invoice.') % (mode))
#                 if inv.reconciled and mode in ('cancel'):
#                     raise osv.except_osv(_('Error !'), _('No se puede cancelar una factura que ha sido pagada, excepto que sea reversado primero el pago para proceder a crear la Nota de Crédito'))
                if form.period.id:
                    period = form.period.id
                else:
                    period = inv.period_id and inv.period_id.id or False

                if not journal_id:
                    journal_id = inv.journal_id.id
                id_ant = inv.id
                if form.date:
                    date = form.date2
                    if not form.period.id:
                            cr.execute("select name from ir_model_fields \
                                            where model = 'account.period' \
                                            and name = 'company_id'")
                            result_query = cr.fetchone()
                            if result_query:
                                cr.execute("""select p.id from account_fiscalyear y, account_period p where y.id=p.fiscalyear_id \
                                    and date(%s) between p.date_start AND p.date_stop and y.company_id = %s limit 1""", (date, company.id,))
                            else:
                                cr.execute("""SELECT id
                                        from account_period where date(%s)
                                        between date_start AND  date_stop  \
                                        limit 1 """, (date,))
                            res = cr.fetchone()
                            if res:
                                period = res[0]
                else:
                    date = inv.date_invoice
                if form.description:
                    description = form.description
                else:
                    description = inv.name

                if not period:
                    raise osv.except_osv(_('Data Insufficient !'), \
                                            _('No Period found on Invoice!'))
                
                cr.execute("SELECT product_id from account_invoice_line where invoice_id = %s", (inv.id,))
                res = cr.fetchall()
                res = [r[0] for r in res]
                dict_refund={}
                context.update({'refund_mode':mode})
                for l in form.line_ids:
                    if l.product_id.id not in res:
                        raise osv.except_osv(_('Invalid Action !'), _('The product %s not exist in the invoice, please check!') %(l.product_id.name,))
                    dict_refund[l.product_id.id]=l.quantity
                refund_id = inv_obj.refund(cr, uid, [inv.id], date, period, description, journal_id, dict_refund,context)
                refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
                if form.user_authorized:
                    refund.write({'user_authorized_refund':form.user_authorized.id})

                if mode == 'internal' and id_ant:
                    number = 'NCI-'+inv.number
                    verify = self.pool.get('account.invoice').search(cr,uid,[('number','like',number)])
                    if verify: 
                        name = int(len(verify)) + 1
                        number = 'NCI '+inv.number + '-'+str(name)
                        invoice_number_out = number
                    else:
                        number = 'NCI '+inv.number
                        invoice_number_out = number
                        invoice_number_in = number
                else:
                    number = False
                    invoice_number_out = False    
                    invoice_number_in = False                    
                
                inv_obj.write(cr, uid, [refund.id], {'date_due': date[:10],
                                                'check_total': inv.check_total,
                                                'old_invoice_id':id_ant,
                                                'motive_id':form['motive'].id,
                                                'refund_type':mode,
                                                'number': number,
                                                'invoice_number_out': invoice_number_out,
                                                'invoice_number_in':invoice_number_in,
                                                'date_invoice2': form['date2']})
                inv_obj.button_compute(cr, uid, refund_id)

                created_inv.append(refund_id[0])
                if mode in ('internal','refund'):
                    wf_service.trg_validate(uid, 'account.invoice', refund.id, 'invoice_open', cr)
                elif mode in ('cancel'):
                    movelines = inv.move_id.line_id
                    to_reconcile_ids = {}
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            if not to_reconcile_ids.has_key(line.account_id.id):
                                to_reconcile_ids[line.account_id.id] = [line.id]
                            else:
                                to_reconcile_ids[line.account_id.id] += [line.id]
                        if type(line.reconcile_id) != osv.orm.browse_null:
                            reconcile_obj.unlink(cr, uid, line.reconcile_id.id)
                    wf_service.trg_validate(uid, 'account.invoice', \
                                        refund.id, 'invoice_open', cr)
                    refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
                    for tmpline in  refund.move_id.line_id:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                    context['comment']=_(('Write-Off invoice number %s')% inv.number)
                    for account in to_reconcile_ids:
                        account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                                        writeoff_period_id=period,
                                        writeoff_journal_id = inv.journal_id.id,
                                        writeoff_acc_id=inv.account_id.id,
                                        context=context
                                        )
                    if mode == 'refund':
                        invoice = inv_obj.read(cr, uid, [inv.id],
                                    ['name', 'type', 'number', 'reference',
                                    'comment', 'date_due', 'partner_id',
                                    'address_contact_id', 'address_invoice_id',
                                    'partner_insite', 'partner_contact',
                                    'partner_ref', 'payment_term', 'account_id',
                                    'currency_id', 'invoice_line', 'tax_line',
                                    'journal_id', 'period_id', 'shop_id','printer_id','company_id'], context=context)
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.read(cr, uid, invoice['invoice_line'], context=context)
                        invoice_lines = inv_obj._refund_cleanup_lines(cr, uid, invoice_lines)
                        tax_lines = inv_tax_obj.read(cr, uid, invoice['tax_line'], context=context)
                        tax_lines = inv_obj._refund_cleanup_lines(cr, uid, tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': date,
                            'state': 'draft',
                            'number': False,
                            'invoice_line': invoice_lines,
                            'tax_line': tax_lines,
                            'period_id': period,
                            'name': description
                        })
                        for field in ('address_contact_id', 'address_invoice_id', 'partner_id',
                                'account_id', 'currency_id', 'payment_term', 'journal_id',
                                'shop_id','printer_id','company_id'):
                                invoice[field] = invoice[field] and invoice[field][0]
                        inv_id = inv_obj.create(cr, uid, invoice, {})
                        if inv.payment_term.id:
                            data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv.payment_term.id, date)
                            if 'value' in data and data['value']:
                                inv_obj.write(cr, uid, [inv_id], data['value'])
                        created_inv.append(inv_id)
            xml_id = (inv.type == 'out_refund') and 'account.action_invoice_tree3_view2' or \
                     (inv.type == 'in_refund') and 'action_invoice_tree4_view2' or \
                     (inv.type == 'out_invoice') and 'action_invoice_tree3' or \
                     (inv.type == 'in_invoice') and 'action_invoice_tree4'
            result = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
            id = result and result[1] or False
            result = act_obj.read(cr, uid, id, context=context)
            invoice_domain = eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result

    def invoice_refund(self, cr, uid, ids, context=None):
        data_refund = self.read(cr, uid, ids, ['filter_refund'],context=context)[0]['filter_refund']
        return self.compute_refund(cr, uid, ids, data_refund, context=context)

account_invoice_refund()

class invoice_refund_line(osv.osv_memory):
    _name = "invoice.refund.line"
    _columns={
              'invoice_id':fields.many2one('account.invoice', 'invoice', required=False),
              'wizard_id':fields.many2one('account.invoice.refund', 'wizard', required=False),
              'product_id':fields.many2one('product.product', 'product', required=False),
              'quantity': fields.float('quantity', digits=(16,2))
              }
    
    def onchange_product(self, cr, uid, ids, product_id=None, invoice_id=None, context=None):
        result={}
        warning={}
        if product_id:
            product=self.pool.get('product.product').browse(cr, uid, product_id, context)
            if not product.categ_id.permit_refund:
                warning= {"title":_("Warning!"),"message":_(("El producto %s - %s que corresponde a la categoría %s no permite devoluciones")% (product.default_code,product.name, product.categ_id.name))}
            if invoice_id:
                cr.execute("SELECT SUM(quantity) FROM account_invoice_line WHERE invoice_id = %s AND product_id = %s",(invoice_id, product.id))
                res=cr.fetchall()
                qty = res[0][0]
                if not qty:
                    inv=self.pool.get('account.invoice').browse(cr, uid, invoice_id)
                    return {"warning":{"title":_("Error!"),"message":_(("El producto %s no existe en la factura %s.") % (product.name,inv.number))},
                            "value":{'product_id':None}}
                result['quantity'] = qty
        return {'value':result, 'warning':warning}
invoice_refund_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
