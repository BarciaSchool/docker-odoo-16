# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv
import time
from tools.translate import _
import netsvc

class account_invoice(osv.osv):
    
    def _get_withhold(self, cr, uid, ids, context=None):
        result = {}
        try:
            for withhold in self.pool.get('account.withhold').browse(cr, uid, ids, context=context):
                for invoice in withhold.invoice_ids:
                    result[invoice.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()
    
    _inherit = "account.invoice"
    _columns = {
                'withhold_lines_ids':fields.one2many('account.withhold.line', 'invoice_id', 'Withhold'),
                'withhold_id':fields.many2one('account.withhold', 'Withhold Reference', required=False),
                'withhold':fields.boolean('withhold', required=False),
                }
    _defaults = {
                 'withhold': lambda *a: False,
                 }
    
    def copy(self, cr, uid, ids, default={}, context=None):
        default = default or {}
        default.update({
            'withhold_lines_ids': False,
            'withhold': False,
            'withhold_id': False,
                    })
        return super(account_invoice, self).copy(cr, uid, ids, default, context)


    def button_reset_taxes(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).button_reset_taxes(cr, uid, ids, context)
        ret_line= self.pool.get('account.withhold.line')
        tax_obj = self.pool.get('account.tax')
        for inv in self.browse(cr, uid, ids, context):
            if inv.type not in ('out_refund','in_refund','out_invoice'):
                if inv.withhold_lines_ids:
                    cr.execute("update account_withhold_line set state='annulled', active=False WHERE invoice_id=%s", (inv.id,))
                for tax_line in inv.tax_line:
                    if (tax_line.tax_code_id.tax_type in ('withhold','withhold_vat') and tax_line.base>0):
                        tax_code = tax_line.tax_code_id.code[1:]
                        tax = tax_obj.search(cr, uid, [('description', '=', tax_code), ('child_ids','=',False),('type_tax_use','=','purchase'),('tax_type','in',('withhold','withhold_vat')),('company_id','=',inv.company_id.id)])
                        ret_line.create(cr, uid, {
                                         'tax_id': tax and tax[0] or None,
                                         'tax_base':tax_line.base,
                                         'invoice_id':inv.id,
                                         },context) 
        return res
    
    def add_withhold(self, cr, uid, ids, context=None):     
        res = {}
        ret_line= self.pool.get('account.withhold.line')
        tax_obj = self.pool.get('account.tax')
        tax_inv = self.pool.get('account.invoice.tax')
        for inv in self.browse(cr, uid, ids, context):
            if inv.type not in ('out_refund','in_refund','out_invoice'):   
                if inv.state == 'approved' or inv.state == 'open' or inv.state =='paid':
                    state = 'approved'
                else:
                    state = 'draft'
                tax = tax_obj.search(cr, uid, [('description', 'like', '332'), ('type_tax_use','=','purchase'), ('child_ids','=',False),('company_id','=',inv.company_id.id)])
                tax_in = tax_obj.browse(cr, uid, tax)[0]
                if tax:
                    ret_line_id = ret_line.search(cr,uid,[('tax_id','=',tax[0]),('invoice_id','=',inv.id)])
                    line_tax = tax_inv.search(cr, uid, [('tax_code_id','=',tax_in.tax_code_id.id),('invoice_id','=',inv.id)])
                    if not ret_line_id:
                        ret_line.create(cr, uid, {
                                         'tax_id': tax and tax[0] or None,
                                         'tax_base':inv.amount_untaxed,
                                         'invoice_id':inv.id,
                                         'period_id':inv.period_id.id,
                                         'partner_id':inv.partner_id.id,
                                         'state':state,
                                         },context) 
                    if not line_tax:
                        tax_inv.create(cr, uid, {
                                         'name': tax_in.description +"-"+ tax_in.name,
                                         'account_id': tax_in.account_collected_id.id,
                                         'base':inv.amount_untaxed,
                                         'base_code_id':tax_in.base_code_id.id,
                                         'tax_code_id':tax_in.tax_code_id.id,
                                         'base_amount':inv.amount_untaxed,
                                         'invoice_id':inv.id,
                                         },context) 
                else:
                    return res
        return res
    
    
    def delete_withhold(self, cr, uid, ids, context=None):     
        res = {}
        ret_line= self.pool.get('account.withhold.line')
        tax_obj = self.pool.get('account.tax')
        tax_inv = self.pool.get('account.invoice.tax')
        for inv in self.browse(cr, uid, ids, context):
            if inv.type not in ('out_refund','in_refund','out_invoice'):   

                tax = tax_obj.search(cr, uid, [('description', 'like', '332'), ('type_tax_use','=','purchase'), ('child_ids','=',False),('company_id','=',inv.company_id.id)])
                tax_in = tax_obj.browse(cr, uid, tax)[0]
                ret_line_id = ret_line.search(cr,uid,[('tax_id','=',tax[0]),('invoice_id','=',inv.id),('withhold_id','=',False)])
                line_tax = tax_inv.search(cr, uid, [('tax_code_id','=',tax_in.tax_code_id.id),('invoice_id','=',inv.id)])
                if ret_line_id:
                    cr.execute("""delete from account_withhold_line where id = %s and invoice_id = %s""",(ret_line_id[0],inv.id))
                if not inv.withhold or len(line_tax) > 1:
                    cr.execute("""delete from account_invoice_tax where id = %s and invoice_id = %s""",(line_tax[0], inv.id))                
        return res
    
    
    def print_withhold(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        invoice=[]
        withhold_id = []
        inv_obj = self.pool.get('account.invoice')
        for invoice in inv_obj.browse(cr, uid, ids, context):
            if invoice.withhold_id.state <> 'approved':
                raise osv.except_osv(_('¡Aviso!'), _("Solo puede imprimir retenciones en estado aprobado"))
            else:
                withhold_id = invoice.withhold_id.id
                nb_print = invoice.withhold_id.nb_print + 1
                self.pool.get('account.withhold').write(cr,uid,invoice.withhold_id.id,{'nb_print':nb_print})
                invoice = withhold_id
                if invoice:
                    data = {}
                    data['model'] = 'account.withhold'
                    data['ids'] = [invoice]
                    context['active_id']=invoice
                    context['active_ids']=[invoice]
                    return {
                       'type': 'ir.actions.report.xml',
                       'report_name': 'Retenciones_Proveedor',
                       'datas' : data,
                       'context': context,
                       'nodestroy': True,
                       }
        return True
    
    def action_number(self, cr, uid, ids, context=None):
        result = super(account_invoice, self).action_number(cr, uid, ids, context)
        for invoice in self.browse(cr, uid, ids, context):
            lines_wth=self.pool.get('account.withhold.line').search(cr, uid, [('invoice_id','=',invoice.id),('state','=','draft'),('tax_id.description','like','332%')])
            self.pool.get('account.withhold.line').write(cr, uid, lines_wth, {'state':'approved'}, context)
        return result
    
    def action_open_draft(self, cr, uid, ids, *args):
        res=super(account_invoice, self).action_open_draft(cr, uid, ids)
        for invoice in self.browse(cr, uid, ids):
            lines_wth=self.pool.get('account.withhold.line').search(cr, uid, [('invoice_id','=',invoice.id),('state','=','approved'),('tax_id.description','like','332%')])
            self.pool.get('account.withhold.line').write(cr, uid, lines_wth, {'state':'draft'})
        return res
        
    def action_cancel(self, cr, uid, ids, *args):
        res=super(account_invoice, self).action_cancel(cr, uid, ids)
        for invoice in self.browse(cr, uid, ids):
            lines_wth=self.pool.get('account.withhold.line').search(cr, uid, [('invoice_id','=',invoice.id),('state','=','approved'),('tax_id.description','like','332%')])
            self.pool.get('account.withhold.line').write(cr, uid, lines_wth, {'state':'draft'})
        return res
    
    def finalize_invoice_move_lines(self, cr, uid, invoice_browse, move_lines):
        """finalize_invoice_move_lines(cr, uid, invoice, move_lines) -> move_lines
        Hook method to be overridden in additional modules to verify and possibly alter the
        move lines to be created by an invoice, for special cases.
        :param invoice_browse: browsable record of the invoice that is generating the move lines
        :param move_lines: list of dictionaries with the account.move.lines (as for create())
        :return: the (possibly updated) final move_lines to create for this invoice
        """
        count = 0
        rem=[]
        b=False
        for line in move_lines:
            if not line[2]:
                rem.append(count)
            count+=1
        count=0
        for i in rem:
            i=i-count
            del move_lines[i]
            count+=1
        return move_lines

account_invoice()


class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"

    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_tax WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            type = self.pool.get('account.tax.code').browse(cr, uid, t['base_code_id'], context={}).tax_type
            if type not in ('withhold', 'withhold_vat'):
                res.append({
                    'type':'tax',
                    'name':t['name'],
                    'price_unit': t['amount'],
                    'quantity': 1,
                    'price': t['amount'] or 0.0,
                    'account_id': t['account_id'],
                    'tax_code_id': t['tax_code_id'],
                    'tax_amount': t['tax_amount']
                })
        return res
account_invoice_tax()

