# -*- coding: UTF-8 -*- #
#########################################################################
#Copyright (C) 2013-2014 STRACONX S.A           #
#                                                                       
#########################################################################

import time
import datetime
from dateutil.relativedelta import relativedelta
from os.path import join as opj
from operator import itemgetter
from addons.straconx_warning.wizard.wizard import get_action_warning

from tools.translate import _
from osv import fields, osv
import netsvc
import tools

class auth_wizard(osv.osv_memory):
        
    _name = 'delivery.auth.wizard'
    _columns = {
        'journal_id_delivery': fields.many2one('account.journal','Journal'),
        'delivery_status': fields.selection([('sent','Sent'),('draft','Draft'),('cancel','Cancel')],'Delivery Status'),
        'delivery_number': fields.char('Delivery Number', size=32),
        'delivery_date': fields.datetime('Delivery Note date'),
        'carrier_id': fields.many2one('delivery.carrier','Transportista'),
        'placa': fields.char('Placa', size=7, required=False),
        'driver': fields.char('Conductor', size=64, required=False),        
        'printer_id':fields.many2one('printer.point', 'Printer Point', domain="[('shop_id', '=', shop_id)]"),
        'shop_id': fields.many2one('sale.shop','Shop'),
        'picking_id': fields.many2one('stock.picking','Picking'),
        'company_id': fields.many2one('res.company','Company'),
        'nb_print_dn': fields.integer('Number of Print', readonly=True),
        'print_status_dn': fields.char('Print Status', size=32),
        'dn_invoiced': fields.boolean('Is invoiced?'),
        'warehouse_id_delivery': fields.many2one('res.users', 'Warehouse Grocer'),
        'authorization_id':fields.many2one('sri.authorization', 'Authorization', readonly=False,help='This Number is necesary for SRI reports'),
        'comment':fields.text('Comentarios', required=False),
                }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}      
        res={}
        warning={}
        a_id = []         
        values={'value':{},'domain':{}}
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        sql="""SELECT journal_id FROM rel_shop_journal as rel, account_journal as jo 
                    WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""
        proof = False
        if 'value' not in context.keys():
            for pick in objs:
                cr.execute(sql,(pick.shop_id.id,'delivery'))
                result=cr.fetchall()
                company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
                if not result:
                    name=self.pool.get('sale.shop').browse(cr, uid, pick.shop_id.id,context).name
                    warning = {'title': _('Error!'),'message': _(('You must be selected in the shop %s the journal respective for this document.')%name)}
                    return {'warning':warning}
                else:
                    delivery_journal_id = result[0][0]
                    delivery = self.pool.get('account.journal').browse(cr,uid,delivery_journal_id).type
                if pick.shop_id:                    
                    printer_ids = self.pool.get('printer.point').search(cr,uid,[('shop_id','=',pick.shop_id.id)])
                    if printer_ids:
                        for p_id in printer_ids:
                            if p_id == pick.printer_id.id:
                                proof = True
                                printer_id = pick.printer_id.id
                            else:
                                proof = False
                                printer_id = False
                                
                    if pick.printer_id and proof:
                        printer_id = pick.printer_id.id
                        if printer_id:
                            auth = self.pool.get('sri.authorization.line').search(cr,uid,[('printer_id','=',printer_id),('name','=',delivery),])
                            if auth: 
                                a_id = self.pool.get('sri.authorization.line').browse(cr,uid,auth[0]).authorization_id.id
                            else:
                                p_id = self.pool.get('printer.point').search(cr,uid,[('shop_id','=',pick.shop_id.id)])
                                if p_id:
                                    for p in p_id:
                                        if p <> pick.printer_id.id:
                                            printer_id = self.pool.get('printer.point').browse(cr,uid,p)
                                            if printer_id:
                                                auth = self.pool.get('sri.authorization.line').search(cr,uid,[('printer_id','=',printer_id.id),('name','=',delivery),])
                                                if auth: 
                                                    a_id = self.pool.get('sri.authorization.line').browse(cr,uid,auth[0]).authorization_id.id
#                                                 else:
#                                                     raise osv.except_osv(_('¡Acción Inválida!'), _('Su tienda no tiene autorización para Guías de Remisión en el punto de impresión %s. Intente con otro punto de impresión para continuar')%(pick.printer_id.id))
                                                                                    
                res['journal_id_delivery'] = delivery_journal_id
                res['shop_id'] = pick.shop_id.id
                res['warehouse_id_delivery'] = uid
                res['delivery_date']= time.strftime('%Y-%m-%d %H:%M:%S')
                res['delivery_status'] = 'sent'
                res['carrier_id']= pick.carrier_id.id or False
                res['printer_id'] = printer_id
                res['company_id'] = company_id
                res['authorization_id']=a_id
        else:
#                res = context['value']
                res = values
        return res

    def onchange_printer(self, cr, uid, ids, printer_id=None, date=None, context=None):
        printer_obj = self.pool.get('printer.point')
        authorization_obj=self.pool.get('sri.authorization')
        auth_line_obj=self.pool.get('sri.authorization.line')
        values = {}
        res = {}
        if context is None:
            context = {}
        sql="""SELECT journal_id FROM rel_shop_journal as rel, account_journal as jo WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""
        if printer_id:
            p_id = self.pool.get('printer.point').browse(cr,uid,printer_id)
            shop_id = printer_obj.browse(cr,uid,printer_id).shop_id.id            
            if shop_id:
                name=self.pool.get('sale.shop').browse(cr, uid, shop_id,context).name
                cr.execute(sql,(shop_id,'delivery'))
                result=cr.fetchall()
                if not result:                    
                    warning = {'title': _('Error!'),'message': _(('You must be selected in the shop %s the journal respective for this document.')%name)}
                    return {'warning':warning}
                else:
                    delivery_journal_id = result[0][0]
                    delivery = self.pool.get('account.journal').browse(cr,uid,delivery_journal_id).type
                    auth = self.pool.get('sri.authorization.line').search(cr,uid,[('printer_id','=',printer_id),('name','=',delivery),('state','=',True)])
                    if auth: 
                        a_id = self.pool.get('sri.authorization.line').browse(cr,uid,auth[0])
                        res['warehouse_id_delivery'] = uid
                        res['shop_id'] = shop_id
                        res['delivery_date']= time.strftime('%Y-%m-%d %H:%M:%S')
                        res['delivery_status'] = 'sent'
                        res['authorization_id']=a_id.authorization_id.id
                    else:
                        warning = {'title': _('Error!'),'message': _(('La tienda %s no tiene autorización para Guías de Remisión en el punto de impresión %s. Intente con otro punto de impresión para continuar')%(name,p_id.name))}
                        return {'warning':warning}
        return {'value':res}     

    def create_delivery(self, cr, uid, ids, context=None):
        auth_obj = self.pool.get('sri.authorization')
        guide_obj = self.pool.get('stock.delivery')
        active_model = context.get('active_model',False)
        act_id = context.get('active_id',False)
        invoice_id = False
        if act_id:
            if active_model == 'stock.picking':
                picking_ids = self.pool.get(active_model).browse(cr , uid, act_id)
                active_id = act_id
            elif active_model == 'account.invoice':
                picking_ids = self.pool.get(active_model).browse(cr , uid, act_id)
                active_id = picking_ids.picking_id.id
                invoice_id = picking_ids.id
        for delivery in self.browse(cr,uid,ids,context=None):
            if not delivery.printer_id:
                raise osv.except_osv('Error!', _("The Shop must be a Cash Box assigned with authorization for Delivery Journals"))
            if not delivery.authorization_id:
                raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
            else:
                line_id = auth_obj.get_line_id(cr,uid, delivery.journal_id_delivery.type, delivery.shop_id.id, delivery.printer_id.id,delivery.authorization_id.id)
            if not delivery.delivery_number:
                number = auth_obj.get_number(cr, uid, [delivery.authorization_id.id], delivery.journal_id_delivery.type, delivery.shop_id.id, delivery.printer_id.id, delivery.company_id.id)
            else:
                number = delivery.delivery_number
            self.pool.get('sri.authorization.line').add_document(cr,uid,line_id,{})
        if context is None:
            context = {}
        datos={}
        picking_pool = self.pool.get('stock.picking')
        onshipdata_obj = self.read(cr, uid, ids, ['journal_id_delivery','delivery_date','delivery_status','printer_id','authorization_id','carrier_id','driver','placa','comment'])
        if context.get('new_picking', False):
            onshipdata_obj['id'] = onshipdata_obj.new_picking
            onshipdata_obj[ids] = onshipdata_obj.new_picking
        active_ids = context.get('active_ids', [])
#        active_picking = picking_pool.browse(cr, uid, context.get('active_id',False), context=context)
        active_picking = picking_pool.browse(cr, uid, active_id, context=context)
        datos['warehouse_id_delivery'] = uid
        datos['authorization_id'] = onshipdata_obj[0]['authorization_id']
        datos['printer_id'] = onshipdata_obj[0]['printer_id']
        datos['delivery_date'] = onshipdata_obj[0]['delivery_date']
        datos['delivery_status'] = onshipdata_obj[0]['delivery_status']
        datos['delivery_number'] = number
        datos['picking_id'] = active_picking.id
        datos['carrier_id']=onshipdata_obj[0]['carrier_id']
        datos['driver']=onshipdata_obj[0]['driver']
        datos['placa']=onshipdata_obj[0]['placa']
        datos['comment']=onshipdata_obj[0]['comment']
        if invoice_id:
            datos['invoice_id']= invoice_id
        datos['journal_id_delivery'] = onshipdata_obj[0]['journal_id_delivery']
        
        res = guide_obj.action_delivery_create(cr, uid, active_ids,
              datos = datos,
              context = context)
        return res

    def onchange_carrier_id(self, cr, uid, ids, carrier_id=False, context=None):
        carrier_obj = self.pool.get('delivery.carrier')
        values = {}
        res = {}
        if context is None:
            context = {}
        sql="""SELECT journal_id FROM rel_shop_journal as rel, account_journal as jo WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""
        if carrier_id:
            carrier_data = carrier_obj.browse(cr,uid,carrier_id)
            res['driver'] = carrier_data.driver or None
            res['placa'] = carrier_data.placa or None
        return {'value':res}


        
    def open_delivery(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        delivery_ids = []
        data_pool = self.pool.get('ir.model.data')
        res = self.create_delivery(cr, uid, ids, context=context)
        for r in res:
            delivery = self.pool.get('stock.delivery').browse(cr,uid,r)
            if delivery:
                delivery_ids = [delivery.picking_id.id]
            else:
                delivery_ids = []
        action_model = False
        action = {}
        if not delivery_ids:
            raise osv.except_osv(_('Error'), _('No Delivery Notes were created'))
#        return True
        return get_action_warning(_("La Guía de Remisión # %s fue creada" % (delivery.number)),action={'type': 'ir.actions.act_window_close'},nodestroy=False)
            
auth_wizard()

