# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#
##############################################################################


from osv import fields, osv
from tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import netsvc

class straconx_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Picking Id',readonly=True, states={'draft':[('readonly',False)]},select=True, ondelete='restrict'),
        'carrier_id': fields.many2one('delivery.carrier','Carrier',readonly=True, states={'draft':[('readonly',False)]},select=True),
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32,readonly=True, states={'draft':[('readonly',False)]}),
        'driver_int': fields.many2one('res.users', 'Driver',readonly=True, states={'draft':[('readonly',False)]}),
        'more_information':fields.boolean('More Information', required=False),
        'number_of_packages': fields.integer('Number of Packages',readonly=True, states={'draft':[('readonly',False)]}),
        'weight_hand': fields.float('Weight', readonly=True, states={'draft':[('readonly',False)]}),
        'warehouse_user': fields.many2one('res.users', 'Warehouse User', domain=[('is_warehouse_user','=',True)]),
        'warehouse_id': fields.many2one('res.users', 'Warehouse User'),
        'picking_ids': fields.many2many('stock.picking', 'picking_invoice_rel', 'invoice_id', 'picking_id', 'Pickings',select=True),
        'delivery_status': fields.selection([('draft','Borrador'),('sent','Enviado'),('cancel','Anulado')],'Estado de Guía de Remisión'),
        'delivery_number': fields.many2one('stock.delivery','Delivery Number',readonly=True, states={'draft':[('readonly',False)]},select=True),
    }

    def onchange_carrier(self, cr, uid, ids, carrier_id=None, context=None):
        values={}
        if carrier_id:
            information = self.pool.get('delivery.carrier').browse(cr, uid, carrier_id, context).more_information
            values['more_information']=information
        return {'value':values}
    
    def action_cancel(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        context = {} # TODO: Use context from arguments
        res=super(straconx_invoice, self).action_cancel(cr, uid, ids)
        picking_obj=self.pool.get('stock.picking')
        for i in ids:
            invoice=self.browse(cr, uid, i, context)
            if invoice.picking_id:
                picking=invoice.picking_id.id
                if invoice.picking_id.state in ('confirmed','assigned','done'):
                    cr.execute('update account_invoice set picking_id = Null where id = %s',(invoice.id,))
                    picking_obj.delivery_annulled(cr, uid,[picking], context)
                    picking_obj.action_drafted(cr, uid,[picking], context)
                    picking_obj.unlink(cr, uid,[picking], context)
                    #wf_service.trg_validate(uid, 'stock.picking', invoice.picking_id.id, 'button_cancel', cr)
        return res
    
    def cancel_only_invoice(self, cr, uid, ids, *args):
        res=super(straconx_invoice, self).cancel_only_invoice(cr, uid, ids)
        picking_obj=self.pool.get('stock.picking')
        for i in ids:
            invoice=self.browse(cr, uid, i)
            if invoice.picking_id:
                picking_obj.write(cr, uid,[invoice.picking_id.id], {'invoice_state':'2binvoiced',
                                                                    'delivery_number':None,
                                                                    'delivery_date':None,
                                                                    'dn_invoiced':None,
                                                                    'authorization_id':False,
                                                                    'delivery_status':'draft'})
        return res
        

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'picking_id':None,
            'carrier_id':None,
            'driver_int':None,
            'delivery_number':False,
            'picking_ids':[],
                    })
        return super(straconx_invoice, self).copy(cr, uid, id, default, context)
        
    def action_number(self, cr, uid, ids, context=None):
        result = super(straconx_invoice, self).action_number(cr, uid, ids, context)
        wf_service = netsvc.LocalService("workflow")
        picking_obj=self.pool.get('stock.picking')
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.old_invoice_id and invoice.old_invoice_id.tpurchase!='expense' and invoice.old_invoice_id.picking_id and (invoice.old_invoice_id.picking_id.state!='done' and invoice.old_invoice_id.picking_id.state!='invoiced'):
                raise osv.except_osv(_('Invalid action!'), _(("No se puede devolver facturas con despachos pendientes!")))
            note=None
            picking_id = None
            move=[]
            data={}
            credit_note = False
            if invoice.type in ('out_refund','in_refund'):
                credit_note = True
                if invoice.old_invoice_id:
                    number = invoice.old_invoice_id.invoice_number_out or invoice.old_invoice_id.invoice_number_in
                    note='Refund of  '+  number
                if not invoice.picking_id:
                    if invoice.type == 'out_refund':
                        tp='in'
                        origin = invoice.partner_id.property_stock_customer.id
                        dest = invoice.shop_id.warehouse_id.lot_stock_id.id
                        domain=[('location_ubication_id','=',dest)]
                    elif invoice.type == 'in_refund':
                        tp='out'
                        origin = invoice.shop_id.warehouse_id.lot_stock_id.id
                        dest = invoice.partner_id.property_stock_supplier.id
                        domain=[('location_ubication_id','=',origin)]
                    if not picking_id:
                        pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.'+tp)
                        data={'move_type': 'one',
                              'partner_id':invoice.partner_id.id,
                              'address_id': invoice.address_invoice_id.id,
                              'carrier_id':invoice.carrier_id.id,
                              'shop_id': invoice.shop_id.id or None,
                              'segmento_id': invoice.partner_id.segmento_id.id or None,
                              'salesman_id': invoice.salesman_id.id or invoice.partner_id.salesman_id.id or None,
                              'date': invoice.date_invoice2 or time.strftime('%Y-%m-%d %H:%M:%S'),
                              'company_id': invoice.company_id.id,
                              'date_expected': invoice.date_invoice or time.strftime('%Y-%m-%d'),
                              'note': note,
                              'invoice_state': 'none',
                              'invoice_ids': [[6, 0, [invoice.id]]],
                              'credit_note': credit_note,
                              'company_id': invoice.company_id.id
                             }
                        picking_id=picking_obj.create_picking(cr, uid, pick_name, invoice.invoice_number, tp, data, context)
                    for line in invoice.invoice_line:
                        if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                            if invoice.old_invoice_id:
                                cr.execute("""SELECT sum(product_qty) FROM stock_move 
                                                WHERE picking_id in (SELECT picking_id FROM picking_invoice_rel WHERE invoice_id = %s)
                                                AND product_id = %s AND state = 'done' """,(invoice.old_invoice_id.id, line.product_id.id))
                                qty_done = cr.fetchone()
                                qty_done = qty_done and qty_done[0] or 0
                                if qty_done ==0:
                                    cr.execute("""SELECT sum(product_qty) FROM stock_move 
                                                    WHERE picking_id in (SELECT picking_id FROM account_invoice WHERE id = %s)
                                                    AND product_id = %s AND state = 'done' """,(invoice.old_invoice_id.id, line.product_id.id))
                                    qty_done = cr.fetchone()
                                    qty_done = qty_done and qty_done[0] or 0
                                if qty_done ==0:
                                    raise osv.except_osv(_('Invalid action!'), _(("El producto %s - %s no tiene ningún picking relacionado, por favor revisar.") % (line.quantity,line.product_id.default_code)))
                                if line.quantity > qty_done:
                                    raise osv.except_osv(_('Invalid action!'), _(("No se puede devolver más unidades (%s) del producto %s - %s que los vendidos (%s) al cliente.") % (line.quantity,line.product_id.default_code,line.product_id.name,qty_done)))
                            ubication=None
                            ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',line.product_id.id)]+domain)
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
                                  'credit_note': credit_note,
                                  'date_expected': invoice.date_invoice or time.strftime('%Y-%m-%d'),
                                  }
                            move_id= picking_obj.create_move(cr, uid, line.name[:64], line.product_id.id, origin, dest, ubication, picking_id, data, context)
                            move.append(move_id)
            if move:
                self.pool.get('stock.move').action_confirm(cr, uid, move)
                self.pool.get('stock.move').force_assign(cr, uid, move)
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_done', cr)
                self.write(cr, uid, [invoice.id],{'picking_id':picking_id})
            else:
                if picking_id:
                    self.pool.get('stock.picking').unlink(cr, uid, [picking_id], context)
#            self.write(cr,uid,ids,{'delivery_status':'draft'})
            cr.execute("""update account_invoice set write_date =now(), delivery_status='draft' where id in %s """,(tuple(ids),))
        return result
    
    
    def action_open_draft(self, cr, uid, ids, *args):
        res=super(straconx_invoice, self).action_open_draft(cr, uid, ids)
        for invoice in self.browse(cr, uid, ids):
            if invoice.type in ('out_refund','in_refund'):
                if invoice.picking_id:
                    picking=invoice.picking_id.id
                    self.write(cr, uid, [invoice.id], {'picking_id':None})
                    self.pool.get('stock.picking').action_drafted(cr, uid,[picking], context={})
                    self.pool.get('stock.picking').unlink(cr, uid, [picking], context={})
        return res

    def delivery_annulled(self, cr, uid, ids, context=None):        
        delivery = self.pool.get('stock.delivery')
        delete = []
        i = self.pool.get('account.invoice').browse(cr,uid,ids)
        for i in ids:
            delivery_se = delivery.search(cr,uid,[('invoice_id','=',i)])
            delivery_id = delivery.browse(cr,uid,delivery_se)
            if(delivery_id):
                delete.append(delivery_id[0].id)
            for del_id in delivery_id:
                self.pool.get('account.invoice').write(cr,uid,del_id.invoice_id.id,{'delivery_status':'draft'})
                self.pool.get('stock.delivery').write(cr,uid,del_id.id,{'state':'cancel'})
                self.pool.get('stock.picking').write(cr,uid,del_id.picking_id.id,{'delivery_status':'draft'})
        return True

    def print_inv_delivery(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.delivery_number.nb_print + 1
            self.pool.get('stock.delivery').write(cr,uid,invoice.delivery_number.id,{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'stock.delivery'
                data['ids'] = [invoice.delivery_number.id]
                context['active_id']=invoice.delivery_number.id
                context['active_ids']=invoice.delivery_number.id
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'delivery_guide_not_invoiced',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True       
straconx_invoice()
