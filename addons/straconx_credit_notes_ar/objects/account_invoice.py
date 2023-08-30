# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################


import time
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    
    _columns = {
        'quantity_refund': fields.float('Quantity Refund', readonly=True),
        'old_line_id':fields.many2one('account.invoice.line', 'Old Line', required=False),
    }

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name=False, type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, currency_id=False, context=None, company_id=None, discount=0, offer=0, shop_id=False):
        if context is None:
            context = {}
        if not (product and name):
            result ={}
        if (product or name):    
            result=super(account_invoice_line,self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id, context, company_id, discount, offer, shop_id)
            if context is None:
                context={}
            context.update({'shop_id':shop_id})
            if product:
#                 if not uom:
#                     uom = self.pool.get('product.product').browse(cr,uid,product).uos_id.id or self.pool.get('product.product').browse(cr,uid,product).uom_id.id
                a=None
                res = self.pool.get('product.product').browse(cr, uid, product, context=context)
                fpos_obj = self.pool.get('account.fiscal.position')
                fpos = fposition_id and fpos_obj.browse(cr, uid, fposition_id, context=context) or None
                if type == 'out_invoice':
#                     a = res.product_tmpl_id.property_account_income.id
                    cr.execute("""select value_reference from ir_property where name ='property_account_income'""")
                    property_account_income = cr.fetchall()
                    if len(property_account_income)>0:
                        a = int(property_account_income[0][0].split(',')[1])
                        if not a:
                            a = res.categ_id.property_account_income_categ.id
                elif type == 'out_refund':
                    warning= {"title":_("¡Aviso!"),"message":_(("El producto %s - %s que corresponde a la categoría %s no permite devoluciones")% (res.default_code, res.name, res.categ_id.name))}
                    result['warning'] = warning
                    if res.type in ('product','consu'):
                        a = res.product_tmpl_id.property_account_refund_sale.id
                        if not a:
                            a = res.categ_id.property_account_refund_sale_categ.id
                    elif res.type in ('admin_service','service'):
                        a = res.product_tmpl_id.property_account_discount_sale.id
                        if not a:
                            a = res.categ_id.property_account_discount_sale_categ.id
                    if not a:
                        raise osv.except_osv('Error!', _("You can assign a sale refund account"))
                elif type == 'in_invoice':
                    a = res.product_tmpl_id.property_account_expense.id
                    if not a:
                        a = res.categ_id.property_account_expense_categ.id
                if a:
                    a = fpos_obj.map_account(cr, uid, fpos, a)
                    result['account_id'] = a
        return result

account_invoice_line()

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'old_invoice_id': fields.many2one('account.invoice','Old Invoice', readonly=True, states={'draft':[('readonly',False)]},select=True),
        'user_authorized_refund': fields.many2one('res.users', 'User Authorized Refund'),
        'refund_type': fields.selection([('refund','Refund'),('discount','Discount'),('internal','Internal'),('cancel','Anular')],'Type of Refund', readonly=True, select=True, states={'draft':[('readonly',False)]}),
        'motive_id': fields.many2one('account.refund.motive', 'Motive', readonly=True, states={'draft':[('readonly',False)]}),
    }

    def action_number(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.type == 'out_refund':
                if invoice.refund_type in ('refund','internal') and invoice.old_invoice_id:
                    for line in invoice.invoice_line:
                        if line.product_id:
                            #lines_ant_ids=self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',invoice.old_invoice_id.id),('product_id','=',line.product_id.id)], limit=1)
                            cr.execute("SELECT SUM(quantity) FROM account_invoice_line WHERE invoice_id = %s AND product_id = %s",(invoice.old_invoice_id.id, line.product_id.id))
                            sum_qty=cr.fetchall()
                            sum_qty= sum_qty[0][0]
                            if not sum_qty:
                                raise osv.except_osv(_('Error!'), _(("the refund product %s does not exist in the invoice reference %s.") % (line.product_id.name,invoice.old_invoice_id.number)))
                            cr.execute("""SELECT sum(ail.quantity) FROM account_invoice_line ail, account_invoice ai 
                                          WHERE ail.invoice_id = ai.id and ai.type = 'out_refund' and ai.state in ('open','paid') and ai.old_invoice_id = %s and ail.product_id = %s""",(invoice.old_invoice_id.id, line.product_id.id))
                            res_qty=cr.fetchall()
                            res_qty= res_qty and res_qty[0][0] or 0
                            if res_qty+line.quantity > sum_qty:
                                raise osv.except_osv(_('Error!'), _(("No puede devolver una cantidad mayor a la vendida del producto %s. Puede que exista una devolución anterior o no haya comprado la cantidad ingresada.") % (line.product_id.name)))
        return super(account_invoice, self).action_number(cr, uid, ids, context)

    def action_move_create(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.type in ('out_refund', 'in_refund'):
                default_payment_term = self.pool.get('account.payment.term').search(cr, uid, [('default', '=', True)], limit=1)
                if not default_payment_term:
                    raise osv.except_osv(_('Error !'), _("You must defined a payment term by default."))
                self.write(cr, uid, [invoice.id], {'payment_term': default_payment_term[0]}, context={})
        return super(account_invoice, self).action_move_create(cr, uid, ids, context)

    def action_open_draft(self, cr, uid, ids, *args):
        for invoice in self.browse(cr, uid, ids, context=None):
            if invoice.type == 'out_refund':
                if invoice.refund_type == 'refund' and invoice.old_invoice_id:
                    for line in invoice.invoice_line:
                        if line.old_line_id:
                            self.pool.get('account.invoice.line').write(cr, uid, [line.old_line_id.id], {'quantity_refund':line.old_line_id.quantity_refund-line.quantity})
        return super(account_invoice, self).action_open_draft(cr, uid, ids, args)
    
    def action_cancel(self, cr, uid, ids, *args):
        for invoice in self.browse(cr, uid, ids, context=None):
            if invoice.type == 'out_refund':
                if invoice.refund_type == 'refund' and invoice.old_invoice_id:
                    for line in invoice.invoice_line:
                        if line.old_line_id:
                            self.pool.get('account.invoice.line').write(cr, uid, [line.old_line_id.id], {'quantity_refund':line.old_line_id.quantity_refund-line.quantity})
            else:
                for line in invoice.invoice_line:
                    if line.quantity_refund>0:
                        raise osv.except_osv(_('Invalid action!'), _(('You can not cancel this invoice because there are products returned. Product: %s Quantity Refund: %s')%(line.product_id.name, str(line.quantity_refund))))
        return super(account_invoice, self).action_cancel(cr, uid, ids, args)
    
    def cancel_only_invoice(self, cr, uid, ids, *args):
        for invoice in self.browse(cr, uid, ids, context=None):
            if invoice.type == 'out_refund':
                if invoice.refund_type == 'refund' and invoice.old_invoice_id:
                    for line in invoice.invoice_line:
                        if line.old_line_id:
                            self.pool.get('account.invoice.line').write(cr, uid, [line.old_line_id.id], {'quantity_refund':line.old_line_id.quantity_refund-line.quantity})
            else:
                for line in invoice.invoice_line:
                    if line.quantity_refund>0:
                        raise osv.except_osv(_('Invalid action!'), _(('You can not cancel this invoice because there are products returned. Product: %s Quantity Refund: %s')%(line.product_id.name, str(line.quantity_refund))))
        return super(account_invoice, self).cancel_only_invoice(cr, uid, ids, args)
    
    def get_refund_cleanup_lines(self, cr, uid, lines,dict_refund={}):
        lines_new=[]
        refund_qty=0.00
        type_refund = dict_refund.get('type_refund',False)
        for line in lines:
            dt = False
            invoice=self.browse(cr,uid,line['invoice_id'][0],context=None)
            del line['id']
            del line['invoice_id']
            for field in ('company_id', 'partner_id', 'account_id', 'product_id',
                          'uos_id', 'account_analytic_id', 'tax_code_id', 'base_code_id','digiter_id',
                          'salesman_id','segmento_id','shop_id','city_state','address_invoice_id'):
                line[field] = line.get(field, False) and line[field][0]
            if line['product_id']:
                if line['product_id'] not in dict_refund:
                    dict_refund[line['product_id']] = 0.00
                    dt = True
                cr.execute("SELECT SUM(quantity) FROM account_invoice_line WHERE invoice_id = %s AND product_id = %s",(invoice.id, line['product_id']))
                sum_qty=cr.fetchall()
                sum_qty= sum_qty[0][0]
                if not sum_qty:
                    product = self.pool.get('product.product').browse(cr, uid, line['product_id'])
                    raise osv.except_osv(_('Error!'), _(("the refund product %s does not exist in the invoice reference %s.") % (product.name,invoice.number)))
                cr.execute("""SELECT sum(ail.quantity) FROM account_invoice_line ail, account_invoice ai 
                              WHERE ail.invoice_id = ai.id and ai.type = 'out_refund' and ai.state in ('open','paid') and ai.old_invoice_id = %s and ail.product_id = %s""",(invoice.id, line['product_id']))
                res_qty=cr.fetchall()
                res_qty= res_qty and res_qty[0][0] or 0
                if res_qty+dict_refund[line['product_id']] > sum_qty:
                    product = self.pool.get('product.product').browse(cr, uid, line['product_id'])
                    raise osv.except_osv(_('!Error! No puede devolver una cantidad mayor a la vendida'), _(("El producto %s ya tiene una devolución de %s que sumado a la actual %s totaliza %s que es mayor a los %s que fue la cantidad vendida. Solo puede aceptar una devolución de %s ") % (product.name, res_qty, dict_refund[line['product_id']],(res_qty + dict_refund[line['product_id']]) , sum_qty, (sum_qty - (res_qty + dict_refund[line['product_id']])))))
                qty_rest=sum_qty-res_qty
                if qty_rest==0:
                    continue
                if type_refund=='cancel':
                    line['quantity'] = dict_refund[line['product_id']]
                    refund_qty = dict_refund[line['product_id']]
                    del dict_refund[line['product_id']]
                elif dict_refund[line['product_id']]>0.00 and dt == False:
                    line['quantity'] = dict_refund[line['product_id']]
                    refund_qty = dict_refund[line['product_id']]
                    del dict_refund[line['product_id']]
                else:
                    line['quantity'] = qty_rest
                if invoice.type=="out_invoice":
                    type='out_refund'
                elif invoice.type=="in_invoice":
                    type='in_refund'                                        
                if refund_qty>0.00 or qty_rest >0.00:
                    result=self.pool.get('account.invoice.line').product_id_change(cr, uid, [],line['product_id'], line['uos_id'],qty = line['quantity'], type=type, partner_id=invoice.partner_id.id, fposition_id=invoice.fiscal_position.id,price_unit=line['price_unit'],company_id=invoice.company_id.id,discount=line['discount'], offer=line['offer'],shop_id = invoice.shop_id.id)['value']
                    if type_refund == 'cancel':
                        del line['account_id']
                        line['account_id'] = result['account_id']
                        lines_new.append(line)
                    else:
                        if result.get('quantity',0.00)>0:
                            if result.get('account_id',False):                                                                                                                                                                                                                                              
                                line['account_id'] = result['account_id']  
                            if result.get('categ_id',False):                                                                                                                                                                                                                                              
                                line['categ_id'] = result['categ_id']               
                            if 'invoice_line_tax_id' in line:
                                line['invoice_line_tax_id'] = [(6,0, line.get('invoice_line_tax_id', [])) ]                
                            if result.get('price_subtotal',0.00):
                                line['price_subtotal'] = result.get('price_subtotal',0.00)
                                line['iva_value'] = result.get('iva_value',0.00)
                            if result.get('price_unit',0.00):
                                line['price_unit'] = result.get('price_unit',0.00)
                            lines_new.append(line)
        return map(lambda x: (0,0,x), lines_new)
    
    def _refund_cleanup_lines(self, cr, uid, lines,dict_refund={}):
        return self.get_refund_cleanup_lines(cr, uid, lines, dict_refund)
        
    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, dict_refund={},context=None):
        invoices = self.read(cr, uid, ids, ['name', 'type', 'number', 'reference', 
                                            'comment', 'date_due', 'partner_id', 'address_contact_id',
                                            'address_invoice_id', 'partner_contact', 'partner_insite',
                                            'partner_ref', 'payment_term', 'account_id', 'currency_id',
                                            'invoice_line', 'tax_line', 'journal_id', 'fiscal_position', 'invoice_number_in',
                                            'shop_id', 'printer_id','company_id','old_invoice_id','user_id','salesman_id',
                                            'electronic', 'automatic', 'pre_printer'])
        obj_invoice_line = self.pool.get('account.invoice.line')
        obj_invoice_tax = self.pool.get('account.invoice.tax')
        obj_journal = self.pool.get('account.journal')
        new_ids = []
        type_refund = {}
#        context = {}
#        refund_mode = context.get('refund_mode',None)
        for invoice in invoices:
            del invoice['id']

            type_dict = {
                'out_invoice': 'out_refund', # Customer Invoice
                'in_invoice': 'in_refund',   # Supplier Invoice
                'out_refund': 'out_invoice', # Customer Refund
                'in_refund': 'in_invoice',   # Supplier Refund
            }
             
            if context.get('refund_mode',False):
                refund_mode = context.get('refund_mode',False)
            
            if refund_mode == 'cancel':
                dict_refund.update({'type_refund':'cancel'})
                invoice_lines = obj_invoice_line.read(cr, uid, invoice['invoice_line'])
                invoice_lines = self._refund_cleanup_lines(cr, uid, invoice_lines,dict_refund)
            else:
                search_invoice_line = obj_invoice_line.search(cr, uid, [('id','in',invoice['invoice_line']),('product_id','in',dict_refund.keys())])
                invoice_lines = obj_invoice_line.read(cr, uid, search_invoice_line)
                invoice_lines = self._refund_cleanup_lines(cr, uid, invoice_lines, dict_refund)

            tax_lines = obj_invoice_tax.read(cr, uid, invoice['tax_line'])
            tax_lines = filter(lambda l: l['manual'], tax_lines)
            tax_lines = self._refund_cleanup_lines(cr, uid, tax_lines)
            if not date:
                date = time.strftime('%Y-%m-%d')
            if period_id:
                invoice.update({
                    'period_id': period_id,
                })
            if description:
                invoice.update({
                    'name': description,
                })
            #TODO diferencio si es una factura tipo compra o venta para poderle asignar los campos necesarios segun el SRI
            
            if invoice['type'] == 'in_invoice':
                if journal_id:
                    refund_journal_ids = [journal_id]
                else:
                    refund_journal_ids = obj_journal.search(cr, uid, [('type','=','purchase_refund')])
                if not refund_journal_ids:
                    raise osv.except_osv(_('Error, no Journal !'),_('Please put a journal to generate invoice.'))
                context['journal_type']=self.pool.get('account.journal').browse(cr, uid, refund_journal_ids[0]).type
                invoice.update({
                    'type': type_dict[invoice['type']],
                    'date_invoice': date[:10],
                    'date_invoice2': date,
                    'state': 'draft',
                    'number': False,
                    'invoice_number_in': False,
                    'invoice_line': invoice_lines,
                    'tax_line': tax_lines,
                    'journal_id': refund_journal_ids,
                })

            elif invoice['type'] == "out_invoice":
                if journal_id:
                    refund_journal_ids = [journal_id]
                else:
                    refund_journal_ids = obj_journal.search(cr, uid, [('type','=','sale_refund')])
                if not refund_journal_ids:
                    raise osv.except_osv(_('Error, no Journal !'),_('Please put a journal to generate invoice.'))
                context['journal_type']=self.pool.get('account.journal').browse(cr, uid, refund_journal_ids[0]).type
                context['printer_id']=invoice['printer_id'] and invoice['printer_id'][0] or None
                context['refund_mode']=context.get('refund_mode','None')
                result=self.onchange_shop(cr, uid, ids, invoice['company_id'][0], invoice['shop_id'][0], 'out_refund', context)
                invoice.update({
                    'type': type_dict[invoice['type']],
                    'date_invoice': date[:10],
                    'state': 'draft',
                    'number': False,
                    'invoice_number_out':False,
                    'invoice_line': invoice_lines,
                    'tax_line': tax_lines,
                    'journal_id': refund_journal_ids,
                    'authorization_sales':result['value'].get('authorization_sales',None),
                    'authorization':result['value'].get('authorization',None),
                    'pre_printer':result['value'].get('pre_printer',False),
                    'automatic':result['value'].get('automatic',False),
                    'electronic':result['value'].get('electronic',False),
                })

                            
            # take the id part of the tuple returned for many2one fields
            for field in ('address_contact_id', 'address_invoice_id', 'partner_id',
                    'account_id', 'currency_id', 'payment_term', 'journal_id',
                    'user_id','fiscal_position','shop_id','printer_id','company_id',
                    'old_invoice_id','salesman_id',
                    ):
                invoice[field] = invoice[field] and invoice[field][0]
            # create the new invoice
            new_ids.append(self.create(cr, uid, invoice, context))
        return new_ids

    def print_credit_notes(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.nb_print + 1
            self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'Nota_de_Credito',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 
    
account_invoice()
