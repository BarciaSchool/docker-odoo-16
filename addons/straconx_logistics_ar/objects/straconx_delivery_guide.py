    # -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 - present STRACONX S.A. 
#
#
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc
from straconx_warning.wizard.wizard import get_action_warning

class stock_delivery(osv.osv):
    _name = 'stock.delivery'    
           
    _columns = {
        'name': fields.char('Name',size=100),
        'picking_id': fields.many2one('stock.picking', 'Picking Pendding', select=True,readonly=True, states={'draft':[('readonly',False)]}),
        'invoice_id': fields.many2one('account.invoice','Facturas', select=True,readonly=True, states={'draft':[('readonly',False)]}),
        'digiter_id':fields.many2one('res.users', 'Digiter',readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.datetime('Delivery Guide date',readonly=True, states={'draft':[('readonly',False)]}),  
        'date_due':fields.datetime('Fecha de terminación',readonly=True, states={'draft':[('readonly',False)]}),
        'carrier_id': fields.many2one('delivery.carrier','Transportista'),
        'placa': fields.char('Placa', size=7, required=False),
        'driver': fields.char('Conductor', size=64, required=False),
        'authorization_id':fields.many2one('sri.authorization', 'Authorization', help='This Number is necesary for SRI reports',readonly=True, states={'draft':[('readonly',False)]}),
        'number': fields.char('Guide Number', size=17, help="Unique number of the delivery guide, computed automatically when the invoice is created.",readonly=True, states={'draft':[('readonly',False)]}),
        'motivo': fields.char('Motivo', size=64, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
        'nb_print': fields.integer('Impresiones'), 
        'state': fields.selection([
            ("draft", "Borrador"),
            ("sent", "Enviado"),
            ("cancel", "Anulado")], "State",
            select=True, required=True, readonly=True, ondelete='restrict', states={'draft': [('readonly', False)]}),
        'comment':fields.text('Comentarios', required=False),                
        }

    _sql_constraints = [
        ('picking_uniq', 'unique(picking_id,number,state)', 'Exists another delivery guide with this picking, please, check!'),
        ('number_uniq', 'unique(number)', 'Number for delivery guide must be unique!'),
    ]

    _defaults = {'nb_print':0,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.delivery', context=c),
                 
                 }
    
    def action_delivery_create(self, cr, uid, ids, datos=None, context=None):
        if context is None:
            context = {}
        warning={}
        delivery_obj = self.pool.get('stock.picking')
        invoice_id_obj = self.pool.get('account.invoice')
        res = {}
        if datos:
            authorization_id = datos.get('authorization_id',False)
            if authorization_id:
                authorization_id = authorization_id[0]
            else:
                raise osv.except_osv(_('Invalid Action!'), _('Need a authorization for create delivery guide.'))
            picking_id = datos.get('picking_id',False)
            if picking_id:
                picking_id = picking_id
                invoice_obj = invoice_id_obj.search(cr,uid,([]))                
            else:
                raise osv.except_osv(_('Invalid Action!'), _('Need a picking for create delivery guide.')) 
            number = datos.get('delivery_number',False)
            carrier_id = datos.get('carrier_id',False)
            invoice_id = datos.get('invoice_id',False)
            if invoice_id:
                invoice_id = invoice_id
                
            else:
                invoice_id = False
                
            picking_data = self.pool.get('stock.picking').browse(cr,uid,picking_id)
            if picking_data.type == 'out':
                motivo = 'VENTA'
            elif picking_data.type == 'internal':
                motivo = 'TRASLADO ENTRE SUCURSALES' 
            elif picking_data.type == 'in':
                motivo = 'RECEPCION DE MERCADERÍA DE PROVEEDORES'
            
            date_due = delivery_obj.browse(cr,uid,picking_id).date_expected  
                
            delivery_vals = {
                'digiter_id':uid,
                'date':datos.get('delivery_date',False),
                'state':datos.get('delivery_status',False),
                'number':datos.get('delivery_number',False),
                'authorization_id':authorization_id,
                'picking_id':picking_id,
                'invoice_id':invoice_id,
                'carrier_id': carrier_id[0],
                'name':datos.get('delivery_number',False),
                'motivo':motivo,
                'date_due':date_due,
                'comment':datos.get('comment',False),
            }
            delivery = self.create(cr, uid, delivery_vals, context=context)            
            res = [delivery]
            invoice_id_obj.write(cr,uid,invoice_id,{'delivery_status':datos.get('delivery_status',False),'delivery_number':res[0]})
            delivery_obj.write(cr,uid,picking_id,{'delivery_status':datos.get('delivery_status',False),
                                                  'delivery_number':datos.get('delivery_number',False),
                                                  'delivery_date':datos.get('delivery_date',False),
                                                  'warehouse_id_delivery':uid,
                                                  'delivery_guide_id':delivery,
                                                  'authorization_id':authorization_id})     
                   
        return res

    def unlink(self, cr, uid, ids, context=None):
        for delivery in self.browse(cr, uid, ids, context=context):
            picking_id = self.browse(cr,uid,delivery.id).picking_id.id
            invoice_id = self.browse(cr,uid,delivery.id).invoice_id.id
            self.pool.get('stock.picking').write(cr, uid,picking_id, {
                                'delivery_status':'draft',
                                'delivery_number':None,
                                'delivery_date':None,
                                'warehouse_id_delivery':None,
                                'delivery_guide_id':False,
                                'dn_invoiced':None,
                                'authorization_id':False,
                                })
            self.pool.get('account.invoice').write(cr,uid,invoice_id,{
                                'delivery_status':'draft',
                                'delivery_number': False
                                })
#        self.unlink(cr,uid,delivery)
        cr.execute("""update stock_delivery set write_date =now(),  state='cancel' where id in %s""",(tuple(ids),))
#        return super(stock_delivery, self).unlink(cr, uid, ids, context=context)

    def print_delivery(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for delivery in self.browse(cr, uid, ids, context=context): 
            nb_print = delivery.nb_print + 1
            self.write(cr,uid,[delivery.id],{'nb_print':nb_print})
            if delivery:
                data = {}
                data['model'] = 'stock.delivery'
                data['ids'] = ids
                context['active_id']=delivery.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'delivery_guide_not_invoiced',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True       



stock_delivery()