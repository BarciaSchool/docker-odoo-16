# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv
import time
from tools.translate import _

sql="""SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo 
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""

class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"

    _columns = {
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32),
        'flag':fields.boolean('flag', required=False),
        'no_driver':fields.boolean('driver', required=False),
        'invoice_date': fields.date('Invoiced date'),
        'invoice_date2': fields.datetime('Invoiced date'),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal')], 'Type',),
        'weight_hand': fields.float('Weight'),
        'number_of_packages': fields.integer('Number of Packages'),
        'warehouse_user': fields.many2one('res.users', 'Warehouse User', domain=[('is_warehouse_user','=',True)]),
        'driver_int': fields.many2one('res.users', 'Driver', domain=[('is_driver','=',True)]),
    }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}      
        res={}  
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        if 'value' not in context.keys():
            for pick in objs:
                journal_obj = self.pool.get('account.journal')
                value = journal_obj.search(cr, uid, [('type', '=','sale' )])
                res['type']=pick.type
                for jr_type in journal_obj.browse(cr, uid, value, context=context):
                    t1 = jr_type.id

                if pick.type=="out":
                    cr.execute(sql,(pick.shop_id.id,'sale'))
                    result=cr.fetchall()
                    if result:
                        res['journal_id']=result[0][0]
                    res['invoice_date']=time.strftime('%Y-%m-%d')
                    res['invoice_date2']=time.strftime('%Y-%m-%d %H:%M:%S')
                    res['flag']=pick.more_information
                    res['no_driver']=pick.carrier_id.no_driver

        else:
            res = context['value']
        return res

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_ids = []
        data_pool = self.pool.get('ir.model.data')
        res = self.create_invoice(cr, uid, ids, context=context)
        invoice_ids += res.values()
        inv_type = context.get('inv_type', False)
        action_model = False
        action = {}
        if not invoice_ids:
            raise osv.except_osv(_('Error'), _('No Invoices were created'))
        if inv_type == "out_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'straconx_invoice', "action_invoice_form_print")
        if inv_type == "in_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree2")
        elif inv_type == "out_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_form_print")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
        return action
               
    def create_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        picking_pool = self.pool.get('stock.picking')
        onshipdata_obj = self.read(cr, uid, ids, ['journal_id', 'group','invoice_date2','invoice_date', 'type','carrier_tracking_ref','weight_hand','number_of_packages','warehouse_user','driver_int'])
        if context.get('new_picking', False):
            onshipdata_obj['id'] = onshipdata_obj.new_picking
            onshipdata_obj[ids] = onshipdata_obj.new_picking
        context['invoice_date2'] = onshipdata_obj[0]['invoice_date2']
        active_ids = context.get('active_ids', [])
        active_picking = picking_pool.browse(cr, uid, context.get('active_id',False), context=context)
        dicc={'carrier_tracking_ref':onshipdata_obj[0]['carrier_tracking_ref'] or None,
              'weight_hand':onshipdata_obj[0]['weight_hand'],
              'number_of_packages':onshipdata_obj[0]['number_of_packages'],
            }
        for field in ('warehouse_user', 'driver_int'):
            dicc[field] = onshipdata_obj[0][field] and onshipdata_obj[0][field][0] or None
        active_picking.write(dicc)
        inv_type = picking_pool._get_invoice_type(active_picking)
        context['inv_type'] = inv_type
        if inv_type == "out_invoice":
            context['journal_type'] = 'sale'
        elif inv_type == "out_refund":
            context['journal_type'] = 'sale_refund'
        if isinstance(onshipdata_obj[0]['journal_id'], tuple):
            onshipdata_obj[0]['journal_id'] = onshipdata_obj[0]['journal_id'][0]
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id = onshipdata_obj[0]['journal_id'],
              group = onshipdata_obj[0]['group'],
              type = inv_type,
              context=context)
        return res
    
stock_invoice_onshipping()
