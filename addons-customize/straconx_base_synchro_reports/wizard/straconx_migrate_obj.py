# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc
import psycopg2
import datetime as dt 
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class migrate_objects(osv.osv_memory):
    _name = "base.synchro.migrate"
    _columns = {
                'migrate_id': fields.text('ID', help="Puede agregar varios id separados por espacios"), 
                'model': fields.many2one('ir.model','Modelo'),
                'shop_id': fields.many2one('sale.shop','Tienda Destino')                                
              }
                 
    
    def action_migrate(self, cr, uid, ids, context=None):
        base_obj = self.pool.get('base.synchro.server')
        for obj in self.browse(cr, uid, ids, context=context):
            review_ids = []
            picking_ids = []
            move_ids = []
            reconcile_ids = []
            if obj.model:
                model = obj.model.model
                model = str(model).replace(".","_")
            if obj.shop_id:
                pool = cr.dbname
                host_pool = 'localhost' 
                server_url = obj.shop_id.server_url
                database_dest = obj.shop_id.server_db
                server_port = obj.shop_id.server_port
                server_login = obj.shop_id.login
                server_password = obj.shop_id.password                
                datas_ids = obj.migrate_id.split()
                for d in datas_ids:
                    review_ids.append(int(d))
                if type(review_ids) != list:
                    raise osv.except_osv('¡Error!', _("Por favor, ingrese solo datos enteros separados por coma.")) 
                source_or= psycopg2.connect(database=pool, user=server_login, password=server_password, host=host_pool, port=server_port, options='-c statement_timeout=60s')           
                conection = psycopg2.connect(database=database_dest, user=server_login, password=server_password, host=server_url, port=server_port, options='-c statement_timeout=60s')                       
                if source_or and conection:
                    if model =='account_invoice':
                        inv_obj = self.pool.get('account.invoice')
                        for inv in review_ids:
                            inv_id = inv_obj.browse(cr,uid,inv)
                            if inv_id.picking_id:
                                picking_ids.append(inv_id.picking_id.id)
                            if inv_id.move_id:
                                move_ids.append(inv_id.move_id.id)                            
                        base_obj.data_both(model,source_or,pool,conection,database_dest, review_ids, context)                        
                        model = 'account_invoice_line'
                        inv_lines = self.pool.get('account.invoice.line').search(cr,uid,[('invoice_id','in',review_ids)])
                        if inv_lines:                            
                            base_obj.data_both(model,source_or,pool,conection,database_dest, inv_lines, context)                        
                        model = 'stock_picking'
                        if picking_ids:                            
                            base_obj.data_both(model,source_or,pool,conection,database_dest, picking_ids, context)
                        model = 'stock_move'
                        stock_move_ids = self.pool.get('stock.move').search(cr,uid,[('picking_id','in',picking_ids)])
                        if stock_move_ids:                            
                            base_obj.data_both(model,source_or,pool,conection,database_dest, stock_move_ids, context)
                        model = 'account_move'
                        if move_ids:                            
                            base_obj.data_both(model,source_or,pool,conection,database_dest, move_ids, context)
                        model = 'account_move_line'
                        move_line_ids = self.pool.get('account.move.line').search(cr,uid,[('move_id','in',move_ids)])
                        if move_line_ids:                            
                            base_obj.data_both(model,source_or,pool,conection,database_dest, move_line_ids, context)
                            for line_move in move_line_ids:
                                l_id = self.pool.get('account.move.line').browse(cr,uid,line_move)
                                if l_id.reconcile_partial_id:
                                    reconcile_ids.append(l_id.reconcile_partial_id.id)
                                elif l_id.reconcile_id:
                                    reconcile_ids.append(l_id.reconcile_id.id)
                                if reconcile_ids:
                                    model = 'account_move_reconcile'
                                    base_obj.data_both(model,source_or,pool,conection,database_dest, reconcile_ids, context)
                    elif model =='stock_picking':
                        base_obj.data_both(model,source_or,pool,conection,database_dest, review_ids, context)
                        model = 'stock_move'
                        stock_move_ids = self.pool.get('stock.move').search(cr,uid,[('picking_id','in',review_ids)])
                        if stock_move_ids:                            
                            base_obj.data_both(model,source_or,pool,conection,database_dest, stock_move_ids, context)
                    elif model == 'account_move':
                        base_obj.data_both(model,source_or,pool,conection,database_dest, review_ids, context)
                        model = 'account_move_line'
                        move_line_ids = self.pool.get('account.move.line').search(cr,uid,[('move_id','in',review_ids)])
                        if move_line_ids:
                            base_obj.data_both(model,source_or,pool,conection,database_dest, move_line_ids, context)
                    elif model == 'product_product':
                        base_obj.data_both(model,source_or,pool,conection,database_dest, review_ids, context)
                        model = 'product_template'
                        product_template_ids = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','in',review_ids)])
                        if product_template_ids:
                            base_obj.data_both(model,source_or,pool,conection,database_dest, product_template_ids, context)
                    elif model == 'res_partner':
                        base_obj.compare_partner(model,source_or,pool,conection,database_dest, review_ids, context)
                        model = 'res_partner_address'
                        res_partner_address_ids = self.pool.get('res.partner.address').search(cr,uid,[('partner_id','in',review_ids)])
                        if res_partner_address_ids:
                            base_obj.data_both(model,source_or,pool,conection,database_dest, res_partner_address_ids, context)
                    else:
                        base_obj.data_both(model,source_or,pool,conection,database_dest, review_ids, context)
            return {'type': 'ir.actions.act_window_close'}
migrate_objects()
