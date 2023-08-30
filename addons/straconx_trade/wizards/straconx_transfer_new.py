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

from tools.translate import _
from osv import fields, osv
import time

class transfer_new(osv.osv_memory):
    
    _name = 'stock.wizard.transfer'
    
    _columns = {
               'shop_id':fields.many2one('sale.shop'),
               'location_dest_id': fields.many2one('stock.location', 'Dest. Location',help="Nueva bodega donde se enviará el nuevo picking", select=True),               
               }
    
    def create_transfer(self, cr, uid, ids, context=None):
        shop_location_id = []
        for w in self.browse(cr,uid,ids):
            if context:
                active_id = context.get('active_id',False)
            if active_id:
                default = {}
                picking_obj = self.pool.get('stock.picking').browse(cr,uid,active_id)
                picking_type = 'internal'
                move_obj=self.pool.get('stock.move')
                seq_obj_name =  'stock.picking.' + picking_type
#                location_search = picking_obj.location_id.id                
                location_search = w.location_dest_id.id 
                if location_search:
                    shop_location_id = self.pool.get('ubication').search(cr,uid,[('location_id','=',location_search)])[0]
                if shop_location_id:
                    location_ids = self.pool.get('ubication').browse(cr,uid,shop_location_id).shop_ubication_id.id
                    shop_ids = self.pool.get('sale.shop').search(cr,uid,[('shop_ubication_id','=',location_ids)])[0]
                    if shop_ids:
                        shop_id = self.pool.get('sale.shop').browse(cr,uid,shop_ids)
                    else:
                        raise osv.except_osv(_('Warning!'), _('No hay tienda definida para la ubicación elegida'))  
                        
                default['name'] = self.pool.get('ir.sequence').next_by_code(cr, uid, seq_obj_name)
                default['origin'] = 'Transferencia de Importación '+picking_obj.origin +' a Bodega '+ w.location_dest_id.name
                default['address_id'] = shop_id.partner_address_id.id
                default['backorder_id'] = False
                default['invoice_state'] = 'none'
                default['type']='internal'
                default['shop_id']= picking_obj.shop_id.id
                default['shop_id_dest']= shop_id.id
                default['location_id']=picking_obj.location_id.id
                default['location_dest_id']= w.location_dest_id.id
                default['internal_out']=True,
                default['international']=False,
                default['confirm_reposition']=False,
                default['date']=time.strftime('%Y-%m-%d %H:%M:%S'),
                res=self.pool.get('stock.picking').copy(cr, uid, active_id, default, context)
                if res:
                    picking_obj = self.pool.get('stock.picking').browse(cr, uid, res, context=context)
                    location_dest_id=self.pool.get('stock.location').search(cr, uid, [('usage','=','transit')], limit=1)[0]
                    for move in picking_obj.move_lines:
                        if location_dest_id: 
                            move_obj.write(cr, uid, [move.id], {'tracking_id': False,'prodlot_id':False, 'product_qty':0, 'qty_receive':0 ,'location_dest_id':location_dest_id,'move_history_ids2': [(6, 0, [])], 'move_history_ids': [(6, 0, [])]})
                        else:
                            raise osv.except_osv(_('Warning!'), _('Revise que exista la ubicación y bodega de destino en su sistema!'))
                    action_model,action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'straconx_logistics', "straconx_action_picking_internal_out")
                    if action_model:
                        action_pool = self.pool.get(action_model)
                        action = action_pool.read(cr, uid, action_id, context=context)
                        action['domain'] = "[('id','in', ["+','.join(map(str,[res]))+"])]"
                    return action

transfer_new()
