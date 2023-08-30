# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
##############################################################################

import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from itertools import groupby
import psycopg2
import tools
import logging
_logger = logging.getLogger(__name__)

class purchase_trade(osv.osv):
    _inherit = "purchase.trade"
    
    def button_send_mail(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        mail_message = self.pool.get('mail.message')
        for trade in self.browse(cr,uid,ids,context):
            for pick in trade.picking_id:
                if pick.state =='draft':
                    self.pool.get('stock.picking').action_move_in(cr,uid,[pick.id],context=None)
                    xml_id = 'email_template_edi_picking_trade_request'
                    template_ids = mod_obj.get_object_reference(cr, uid, 'stock', xml_id)
                    data_email = self.pool.get('email.template').send_mail(cr,uid,template_ids[1],pick.id,False,context)                   
                    context.update({'shop_dest_id':pick.shop_id.id})
            for invoice in trade.purchase_ids:
                if invoice.state <> 'draft':
                    self.pool.get('account.invoice').action_move_invoice(cr,uid,[invoice.id],context)
            self.write(cr,uid,ids,{'state':'done'})
        return True
    
    def button_cancel_picking(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('account.move')
        journal_id = self.pool.get('account.journal').search(cr,uid,[('type','=','stock')])[0]
        wf_service = netsvc.LocalService("workflow")
        state_source = False
        if not context:
            context = {}
        invoices_ids = context.get('invoices_ids',False)
        for trade in self.browse(cr, uid, ids, context):
            for pick in trade.picking_id :
                # BASE DE DATOS DE ORIGEN
                shop_id_database = pick.shop_id.server_db
                shop_id_user = pick.shop_id.login
                shop_id_password = pick.shop_id.password
                shop_id_host=pick.shop_id.server_url
                shop_id_port=pick.shop_id.server_port
                # BASE DE DATOS DESTINO
                shop_dest_id_database = pick.shop_id_dest.server_db
                shop_dest_id_user = pick.shop_id_dest.login
                shop_dest_id_password = pick.shop_id_dest.password
                shop_dest_id_host = pick.shop_id_dest.server_url
                shop_dest_id_port=pick.shop_id_dest.server_port
                            
                if shop_id_database <> shop_dest_id_database:
                    if not shop_id_database or not shop_dest_id_database:
                        raise osv.except_osv('Error!', _("Please, select a database."))
                    try:
                        source_or= psycopg2.connect(database=shop_id_database, user=shop_id_user, password=shop_id_password, host=shop_id_host, port=shop_id_port)
                        source = source_or.cursor()
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_id_database,shop_id_host))                    

                    try:
                        conection = psycopg2.connect(database=shop_dest_id_database, user=shop_dest_id_user, password=shop_dest_id_password, host=shop_dest_id_host, port=shop_dest_id_port)    
                        conect = conection.cursor()  
                    except psycopg2.Error: 
                        _logger.exception('Connection to the database failed')
                        raise osv.except_osv('¡Error!', _("NO existe conexión con la base de datos %s en la dirección %s.")%(shop_dest_id_database,shop_dest_id_host))
                    
                    source.execute("select state from stock_picking where id = %s",(pick.id,))
                    state_source = source.fetchall()
                    if state_source:
                        state_source = state_source[0][0]
                        if state_source == 'draft':
                            source.execute("update stock_picking set state = 'cancel' where id = %s",(pick.id,))
                            source.execute("update stock_move set state = 'cancel' where picking_id = %s",(pick.id,))
                            source_or.commit()
                    else:
                        state_source = []
                    conect.execute("select state from stock_picking where id = %s",(pick.id,))
                    state_conect = conect.fetchall()
                    state_conect = state_conect[0]
                    if state_conect:
                        state_conect = state_conect[0][0]
                    else:
                        state_conect = [] 
                if state_source in ('draft','cancel') or not state_source:            
                    if pick.state=='cancel':
                        continue
                    self.pool.get('stock.picking').action_drafted(cr, uid,[pick.id], context={})
                    wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
                else:
                    raise osv.except_osv('Error!', _("Por favor, solicitar en la tienda de recepción del Picking, que cambie su estado a Cancelado."))                    
            move_ids = move_obj.search(cr,uid,[('ref','=',pick.name),('journal_id','=',journal_id),('state','!=','cancel')])
            if move_ids:
                move_obj.button_cancel(cr, uid, move_ids, context=context)
                move_obj.unlink(cr, uid, move_ids, context=context)
        trade.write({'state':'progress'})
        if invoices_ids:
            for invoices_id in invoices_ids:
                source.execute("""delete from account_move_line where move_id=(select move_id from account_invoice where id = %s)""",(invoices_id,))
                source.execute("""delete from account_move where id=(select move_id from account_invoice where id = %s)""",(invoices_id,))
                source.execute("""delete from account_invoice where id = %s""",(invoices_id,))
                source.execute("""delete from account_invoice_line where invoice_id = %s""",(invoices_id,))   
            source_or.commit()             
        return True

    
purchase_trade()
