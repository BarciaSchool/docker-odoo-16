# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
##############################################################################

import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from straconx_warning.wizard import wizard
import time
import netsvc
import method
from tools import float_compare
from account_voucher import account_voucher

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _columns = {
        'authorized':fields.boolean('flag', required=False),
        'sequence': fields.integer('sequence'),
    }
    _defaults = {'sequence': 0,
                 'authorized':True,
                 }
    
    def sequence_change(self, cr, uid, ids, invoice_line_ids, shop_id=None, context=None):
        if not shop_id:
            raise osv.except_osv(_('No Shop Defined !'), _('You must select a Shop.'))
        shop = self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
        sequence= method.sequence_change(invoice_line_ids, shop, context)
        if not sequence:
            raise osv.except_osv(_('Error !'), _('You can not generate more than %s lines per Invoices.') % str(shop.limits_line_invoice))
        return {'value':{'sequence':sequence}}
    
    def copy_data(self, cr, uid, id, default=None, context=None):
        a = []
        taxes = [6,False,a]
        if not default:
            default = {}
        line = self.browse(cr, uid, id, context)
        if line.product_id:
            product_id = line.product_id.id
        else:
            product_id = False 
#           [[6, False, [2, 8, 94]]]
        if line.invoice_line_tax_id:
            for l in line.invoice_line_tax_id:
                a.append(l.id)
        else:
            taxes = []
        res=self.onchange_offer(cr, uid, id, product=product_id, qty=line.quantity, price_product=line.price_product, taxes=line.invoice_line_tax_id, price_iva =line.price_iva, fiscal_position=line.invoice_id.fiscal_position.id)['value']
        res.update({'offer':0.0,'discount':0.00})
        default.update(res)
        return super(account_invoice_line, self).copy_data(cr, uid, id, default, context=context)

account_invoice_line()

class straconx_invoice(osv.osv):
    
    def _pickings_done(self, cr, uid, ids, name, args, context=None):
        res={}
        for id in ids:
            res[id]=False
            cr.execute("""SELECT picking_id FROM picking_invoice_rel 
                            INNER JOIN stock_picking ON (id = picking_id) 
                            WHERE invoice_id = %s AND state != 'done' """,(id,))
            pickings=cr.fetchone()
            if not pickings:
                res[id]=True
        return res

    def _get_p_offer(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if curr_user.changed_offer:
            p_offer = True
        else:
            p_offer = False 
        return p_offer    

    def _get_p_changed(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if curr_user.changed_discount:
            p_discount = True
        else:
            p_discount = False 
        return p_discount    

    
    _inherit = 'account.invoice'
        
    _columns = {
        'pos':fields.boolean('pos', required=False),
        'authorized':fields.boolean('authorized', required=False),
        'wizard_auth':fields.boolean('wizard auth', required=False),
        'supervisor_id':fields.many2one('res.users', 'Supervisor', required=False),
        'voucher_id':fields.many2one('account.voucher', 'Voucher Pay', required=False),
        'date_authorized': fields.datetime('Date Authorization'),
        'picking_done': fields.function(_pickings_done, method=True, type="boolean", string='Picking done?',),
        'p_offer':fields.boolean('Permited Offer'),
        'p_changed':fields.boolean('Permited Discount'), 
        'nb_print_proforma': fields.integer('Se ha impreso está proforma')       
    }
    
    _defaults = {
        'pos':False,
        'authorized':True,
        'p_offer':_get_p_offer,
        'p_changed':_get_p_changed,
        'nb_print_proforma': 0,
    }
    
    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, context=None):
        context = context or {} 
        if not line_dr_ids:
            return {'value':{}}
        line_osv = self.pool.get('account.invoice.line')
        line_dr_ids = account_voucher.resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['price_iva','price_subtotal','price_product','offer','discount','price_unit','iva_value','quantity','invoice_line_tax_id'], context)
        total = 0.00
        amount_tax = 0.00
        total_quantity = 0.00
        total_discount = 0.00
        total_offer = 0.00
        pretotal = 0.00
        tax_value = 0.00
        total_amount = 0.00
        b=True
        for line in line_dr_ids:
            if not line.get('authorized',True):
                b=False
            amount = line.get('price_subtotal',0.0)
            price_iva = line.get('price_iva',0.0)
            price_product = line.get('price_product',0.0)
            discount = line.get('discount',0.0)
            offer = line.get('offer',0.0)
            quantity = line.get('quantity',0.0)
            price_subtotal = line.get('price_subtotal',0.0)
            iva_value = line.get('iva_value',0.0)
            pretotal += price_product * quantity
            total_quantity += quantity
            total_discount += price_product * discount/100 * quantity
            total_offer += (price_product * (1 - discount/100)) * offer/100 * quantity
            total += amount
            amount_tax += iva_value        
        amount_total = round(total + amount_tax,2)        
        return {'value': {'authorized':b,'pretotal':pretotal,'amount_untaxed': total,'amount_total_vat':amount_tax,'amount_total':amount_total,'amount_total_discount':total_discount,'amount_total_offer':total_offer,'account_quantity':total_quantity}}
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'authorized': True, 'wizard_auth': False})
        return super(straconx_invoice, self).copy(cr, uid, id, default, context=context)
    
    def button_reset_taxes(self, cr, uid, ids, context=None):
        res = super(straconx_invoice, self).button_reset_taxes(cr, uid, ids, context)
        for inv in self.browse(cr, uid, ids, context):
            cr.execute('SELECT id FROM account_invoice_line WHERE invoice_id = %s AND authorized = false',(inv.id,))
            result = cr.fetchall()
            if result:
                inv.write({'authorized':False})
            else:
                inv.write({'authorized':True})
        return res

    #@profile        
    def action_validate(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context):
            inv_state = wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_open', cr)            
            if not inv_state:
#                 self.action_date_assign(cr,uid,[invoice.id],context)
                self.action_move_create(cr,uid,[invoice.id],context)
                self.action_number(cr,uid,[invoice.id],context)
                #self.write(cr,uid,[invoice.id],{'state':'open'})
                cr.execute("update account_invoice set state='open', write_date=now() where id=%s",(invoice.id,))               
            cr.execute("""SELECT rel.picking_id 
                        FROM picking_invoice_rel rel, stock_picking pick 
                        WHERE rel.picking_id = pick.id AND
                        pick.state = 'confirmed' AND  
                        invoice_id = %s""",(invoice.id,))
            res1=cr.fetchall()
            if res1:
                res2=wizard.get_action_warning('Existen Productos Pendientes de despachar, por favor revisar')
                res2['nodestroy']=True
                return res2                    
        return True
    
    def action_number(self, cr, uid, ids, context=None):
        result = super(straconx_invoice, self).action_number(cr, uid, ids, context)
        picking_obj=self.pool.get('stock.picking')
        for invoice in self.browse(cr, uid, ids, context):
            lines_ids=self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',invoice.id),('authorized','=',False)])
            if lines_ids:
                raise osv.except_osv(_('Invoice not authorized!'),
                                     _('You must be solicited authorization to supervisor by this invoice, press calculate and digit the authorization'))
            note=None
            picking_id = None
            move=[]
            data={}
            if invoice.type == 'out_invoice' and invoice.pos:
                if not invoice.picking_id:
                    tp='out'
                    origin = invoice.shop_id.warehouse_id.lot_stock_id.id
                    dest = invoice.partner_id.property_stock_customer.id or invoice.shop_id.warehouse_id.lot_output_id.id 
                    if not picking_id:
                        pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.'+tp)
                        data={'partner_id':invoice.partner_id.id,
                              'address_id': invoice.address_invoice_id.id,
                              'carrier_id':invoice.carrier_id.id or invoice.partner_id.property_delivery_carrier.id or None,
                              'shop_id': invoice.shop_id.id or None,
                              'segmento_id': invoice.partner_id.segmento_id.id or None,
                              'salesman_id': invoice.salesman_id.id or invoice.partner_id.salesman_id.id or None,
                              'date': invoice.date_invoice2 or time.strftime('%Y-%m-%d %H:%M:%S'),
                              'note': note,
                              'invoice_state': 'none',
                              'invoice_ids': [[6, 0, [invoice.id]]],
                             }
                        picking_id=picking_obj.create_picking(cr, uid, pick_name, invoice.invoice_number, tp, data, context)
                    for line in invoice.invoice_line:
                        if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                            ubication=None
                            ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',line.product_id.id),('location_ubication_id','=',origin)])
                            if ubication_ids:
                                ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
                            data={
                                  'product_qty': line.quantity,
                                  'product_uom': line.uos_id.id or line.product_id.uom_id.id,
                    
                                  'product_uos_qty': line.quantity,
                                  'product_uos': line.uos_id.id or line.product_id.uom_id.id,
                                  #'product_packaging': line.product_packaging.id,
                                  'address_id': invoice.address_invoice_id.id,
                                  'company_id': invoice.company_id.id,
                                  }
                            move_id= picking_obj.create_move(cr, uid, line.name[:64], line.product_id.id, origin, dest, ubication, picking_id, data, context)
                            move.append(move_id)
            if move:
                picking_obj.delivery_picking_available(cr, uid, picking_id, context)
                cr.execute('UPDATE account_invoice SET picking_id=%s WHERE id=%s',(picking_id,invoice.id))
                #self.write(cr, uid, [invoice.id],{'picking_id':picking_id})
            else:
                if picking_id:
                    self.pool.get('stock.picking').unlink(cr, uid, [picking_id], context)
        return result
    
    def done_picking_pending(self, cr, uid, ids, context=None):
        picking_obj=self.pool.get('stock.picking')
        for id in ids:
            cr.execute("""SELECT picking_id FROM picking_invoice_rel 
                            INNER JOIN stock_picking ON (id = picking_id) 
                            WHERE invoice_id = %s AND state != 'done' """,(id,))
            pickings=cr.fetchone()
            if pickings:
                picking_obj.delivery_picking_available(cr, uid, pickings[0], context)
        return True
    
    def action_open_draft(self, cr, uid, ids, *args):
        res=super(straconx_invoice, self).action_open_draft(cr, uid, ids)
        for invoice in self.browse(cr, uid, ids):
            if invoice.pos:
                if invoice.picking_id:
                    picking=invoice.picking_id.id
                    self.write(cr, uid, [invoice.id], {'picking_id':None})
                    self.pool.get('stock.picking').action_drafted(cr, uid,[picking], context={})
                    self.pool.get('stock.picking').unlink(cr, uid, [picking], context={})
        return res
    
    def annuled_voucher(self, cr, uid, invoice, context=None):
        if context is None:
            context = {}
        voucher_obj=self.pool.get('account.voucher')
        if invoice.voucher_id:
            voucher_obj.cancel_voucher(cr, uid, [invoice.voucher_id.id], context)
            if context.get('delete_voucher',False):
                voucher_obj.action_cancel_draft(cr, uid, [invoice.voucher_id.id], context)
                voucher_obj.unlink(cr, uid, [invoice.voucher_id.id], context)
        else:
            voucher_ids=voucher_obj.search(cr, uid, [('invoice_id','=',invoice.id),('state','=','posted')], context=None)
            if voucher_ids:
                voucher_obj.cancel_voucher(cr, uid, voucher_ids, context=None)
                if context.get('delete_voucher',False):
                    voucher_obj.action_cancel_draft(cr, uid, voucher_ids, context)
                    voucher_obj.unlink(cr, uid, voucher_ids, context)
        return True
    
    def action_cancel_pos(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for invoice in self.browse(cr, uid, ids):
            self.annuled_voucher(cr, uid, invoice, context)
            self.write(cr,uid,invoice.id,{'state':'cancel'})
            wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_cancel', cr)
        self.clean_values_invoice_cancel(cr, uid, ids, context)
        return True
    
    def action_open_draft_pos(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context['delete_voucher']=True
        for invoice in self.browse(cr, uid, ids):
            self.annuled_voucher(cr, uid, invoice, context)
        return self.action_open_draft(cr, uid, ids, context)
    
    def on_change_company_id(self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id):
        val = {}
#         dom = {}
        obj_journal = self.pool.get('account.journal')
        account_obj = self.pool.get('account.account')
        inv_line_obj = self.pool.get('account.invoice.line')
        if company_id and part_id and type:
            acc_id = False
            partner_obj = self.pool.get('res.partner').browse(cr,uid,part_id)
            if partner_obj.property_account_payable and partner_obj.property_account_receivable:
                if partner_obj.property_account_payable.company_id.id != company_id and partner_obj.property_account_receivable.company_id.id != company_id:
                    property_obj = self.pool.get('ir.property')
                    rec_pro_id = property_obj.search(cr, uid, [('name','=','property_account_receivable'),('res_id','=','res.partner,'+str(part_id)+''),('company_id','=',company_id)])
                    pay_pro_id = property_obj.search(cr, uid, [('name','=','property_account_payable'),('res_id','=','res.partner,'+str(part_id)+''),('company_id','=',company_id)])
                    if not rec_pro_id:
                        rec_pro_id = property_obj.search(cr, uid, [('name','=','property_account_receivable'),('company_id','=',company_id)])
                    if not pay_pro_id:
                        pay_pro_id = property_obj.search(cr, uid, [('name','=','property_account_payable'),('company_id','=',company_id)])
                    rec_line_data = property_obj.read(cr, uid, rec_pro_id, ['name','value_reference','res_id'])
                    pay_line_data = property_obj.read(cr, uid, pay_pro_id, ['name','value_reference','res_id'])
                    rec_res_id = rec_line_data and rec_line_data[0].get('value_reference',False) and int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                    pay_res_id = pay_line_data and pay_line_data[0].get('value_reference',False) and int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                    if not rec_res_id and not pay_res_id:
                        raise osv.except_osv(_('Configuration Error !'),
                            _('Can not find a chart of account, you should create one from the configuration of the accounting menu.'))
                    if type in ('out_invoice', 'out_refund'):
                        acc_id = rec_res_id
                    else:
                        acc_id = pay_res_id
                    val= {'account_id': acc_id}
            if ids:
                if company_id:
                    inv_obj = self.browse(cr,uid,ids)
                    for line in inv_obj[0].invoice_line:
                        if line.account_id:
                            if line.account_id.company_id.id != company_id:
                                result_id = account_obj.search(cr, uid, [('name','=',line.account_id.name),('company_id','=',company_id)])
                                if not result_id:
                                    raise osv.except_osv(_('Configuration Error !'),
                                        _('Can not find a chart of account, you should create one from the configuration of the accounting menu.'))
                                inv_line_obj.write(cr, uid, [line.id], {'account_id': result_id[-1]})
            else:
                if invoice_line:
                    for inv_line in invoice_line:
                        obj_l = account_obj.browse(cr, uid, inv_line[2]['account_id'])
                        if obj_l.company_id.id != company_id:
                            raise osv.except_osv(_('Configuration Error !'),
                                _('Invoice line account company does not match with invoice company.'))
                        else:
                            continue
        if company_id and type:
            if type in ('out_invoice'):
                journal_type = 'sale'
            elif type in ('out_refund'):
                journal_type = 'sale_refund'
            elif type in ('in_refund'):
                journal_type = 'purchase_refund'
            else:
                journal_type = 'purchase'
            journal_ids = obj_journal.search(cr, uid, [('company_id','=',company_id), ('type', '=', journal_type)])
            val['shop_id']= self.pool.get('sale.shop').search(cr,uid,[('company_id','=',company_id)])[0]
            val['period_id']=self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')),('company_id','=',company_id)])[0]
            if journal_ids:
                val['journal_id'] = journal_ids[0]
            ir_values_obj = self.pool.get('ir.values')
            res_journal_default = ir_values_obj.get(cr, uid, 'default', 'type=%s' % (type), ['account.invoice'])
            for r in res_journal_default:
                if r[1] == 'journal_id' and r[2] in journal_ids:
                    val['journal_id'] = r[2]
            if not val.get('journal_id', False):
                raise osv.except_osv(_('Configuration Error !'), (_('Can\'t find any account journal of %s type for this company.\n\nYou can create one in the menu: \nConfiguration\Financial Accounting\Accounts\Journals.') % (journal_type)))
#             dom = {'journal_id':  [('id', 'in', val['journal_id'])]}
        else:
            journal_ids = obj_journal.search(cr, uid, [])
        values = self.onchange_shop(cr, uid, ids, company_id, val['shop_id'],type,context = None)
        if values['value']['account_analytic_id']:
            val['account_analytic_id']= values['value']['account_analytic_id']
            val['printer_id']= values['value']['printer_id']
        return {'value': val, 'domain':{'shop_id':[('company_id', '=', company_id)],'journal_id':[('company_id', '=', company_id)], 'period_id':[('company_id', '=', company_id)]}}

    def print_proforma(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            if invoice.vat=='EC9999999999999':
                raise osv.except_osv(_('¡Acción Inválida!'), _('No se puede proformar al Consumidor Final'))
            nb_print_proforma = invoice.nb_print_proforma + 1
            self.write(cr,uid,[invoice.id],{'nb_print_proforma':nb_print_proforma,'state':'proforma'})
            invoice.refresh()
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'proforma_report_id',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 
        
straconx_invoice()
