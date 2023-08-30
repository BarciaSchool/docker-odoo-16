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
from osv import osv, fields
import decimal_precision as dp
from tools import float_compare
from tools.translate import _
import netsvc
import time
import tools
from operator import attrgetter


class mrp_production(osv.osv):
    _inherit = 'mrp.production'

    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if curr_user:
            if not curr_user.printer_point_ids:
                return None
            for s in curr_user.printer_point_ids:
                if s.shop_id:
                    return s.shop_id.id
        else: 
            return None

    _columns = {
        'shop_id': fields.many2one('sale.shop', 'Shop',readonly=True, states={'draft':[('readonly',False)]}),                
        'shop_id_dest': fields.many2one('sale.shop', 'Shop',readonly=True, states={'draft':[('readonly',False)]}),
    }
    
    _defaults = {
        'shop_id': _get_shop
    }
    
    def _make_production_internal_shipment_line(self, cr, uid, production_line, shipment_id, consume_move_id, destination_location_id=False, production=False, context=None):
        if not production:
            return {} 
        stock_move = self.pool.get('stock.move')
        ubication_obj = self.pool.get('product.ubication')
        production = self.pool.get('mrp.production').browse(cr,uid,production)
        date_planned = production.date_planned
        destination_location_id = production.product_id.product_tmpl_id.property_stock_production.id
        # Internal shipment is created for Stockable and Consumer Products
        if production_line.product_id.type not in ('product', 'consu'):
            return False
        move_name = _('PROD: %s') % production.name
        source_location_id = production.location_src_id.id
        ubication_id = ubication_obj.search(cr,uid,[('location_ubication_id','=',source_location_id),('product_id','=',production_line.product_id.id)])
        if ubication_id:
            ubication_id = ubication_obj.browse(cr,uid,ubication_id[0]).ubication_id.id
        else:
            ubication_id = False         
        location_dest_ids=self.pool.get('stock.location').search(cr, uid, [('usage','=','transit')], limit=1)
        if location_dest_ids:
            destination_location_id = location_dest_ids[0] 
        return stock_move.create(cr, uid, {
                        'name': move_name,
                        'picking_id': shipment_id,
                        'product_id': production_line.product_id.id,
                        'product_qty': production_line.product_qty,
                        'product_uom': production_line.product_uom.id,
                        'product_uos_qty': production_line.product_qty,
                        'product_uos': production_line.product_uos and production_line.product_uos.id or False,
                        'date': date_planned,
                        'location_id': source_location_id,
                        'location_dest_id': destination_location_id,
                        'ubication_id':ubication_id,
                        'state': 'draft',
                        'company_id': production.company_id.id,
                })
        

    def _make_production_internal_shipment(self, cr, uid, location_id, location_dest_id, production, context=None):

        ir_sequence = self.pool.get('ir.sequence')
        stock_picking = self.pool.get('stock.picking')
        routing_loc = None
        pick_type = 'internal'
        address_id = False
          
        # Take routing address as a Shipment Address.
        # If usage of routing location is a internal, make outgoing shipment otherwise internal shipment
        journal_id = self.pool.get('account.journal').search(cr,uid,[('type','=','stock')])[0]
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
            routing_loc = production.bom_id.routing_id.location_id
            if routing_loc.usage <> 'internal':
                pick_type = 'out'
            address_id = routing_loc.address_id and routing_loc.address_id.id or routing_loc.company_id.partner_id.address_id[0].id or  False
        if not address_id:
            address_id = production.shop_id_dest.partner_address_id.id
  
        # Take next Sequence number of shipment base on type
        pick_name = ir_sequence.next_by_code(cr, uid, 'stock.picking.' + pick_type)
  
        picking_id = stock_picking.create(cr, uid, {
            'shop_id': production.shop_id.id,
            'shop_id_dest': production.shop_id_dest.id,
            'location_id': location_id, 
            'location_dest_id': location_dest_id,
            'partner_id':production.company_id.partner_id.id,
            'internal_out': True,
            'confirm_reposition': False,
            'name': pick_name,
            'origin': (production.origin or '').split(':')[0] + ':' + production.name,
            'type': pick_type,
            'move_type': 'one',
            'stock_journal_id': journal_id,
            'state': 'draft',
            'address_id': address_id,
            'auto_picking': self._get_auto_picking(cr, uid, production),
            'company_id': production.company_id.id,
            'active': True
        })
        production.write({'picking_id': picking_id}, context=context)
        return picking_id


    def _make_production_produce(self, cr, uid, production, context=None):
        ir_sequence = self.pool.get('ir.sequence')
        stock_picking = self.pool.get('stock.picking')
        routing_loc = None
        pick_type = 'internal'
        address_id = False
          
        # Take routing address as a Shipment Address.
        # If usage of routing location is a internal, make outgoing shipment otherwise internal shipment
        journal_id = self.pool.get('account.journal').search(cr,uid,[('type','=','stock')])[0]
        if not address_id:
            address_id = production.shop_id_dest.partner_address_id.id
        source_location_id = production.location_src_id.id 
        location_dest_id = production.product_id.product_tmpl_id.property_stock_production.id
  
        # Take next Sequence number of shipment base on type
        pick_name = ir_sequence.get(cr, uid, 'stock.picking.' + pick_type)
  
        picking_id = stock_picking.create(cr, uid, {
            'shop_id': production.shop_id.id,
            'shop_id_dest': production.shop_id_dest.id,
            'location_id': source_location_id,
            'location_dest_id': location_dest_id,
            'partner_id':production.company_id.partner_id.id,
            'internal_out': True,
            'confirm_reposition': False,
            'name': pick_name,
            'origin': (production.origin or '').split(':')[0] + ':' + production.name,
            'type': pick_type,
            'move_type': 'one',
            'stock_journal_id': journal_id,
            'state': 'draft',
            'address_id': address_id,
            'auto_picking': self._get_auto_picking(cr, uid, production),
            'company_id': production.company_id.id,
        })
        production.write({'picking_id': picking_id}, context=context)
        return picking_id


    def _make_action_consume(self, cr, uid, production, context=None):
        ir_sequence = self.pool.get('ir.sequence')
        stock_picking = self.pool.get('stock.picking')
        routing_loc = None
        pick_type = 'internal'
        address_id = False
          
        # Take routing address as a Shipment Address.
        # If usage of routing location is a internal, make outgoing shipment otherwise internal shipment
        journal_id = self.pool.get('account.journal').search(cr,uid,[('type','=','stock')])[0]
        if not address_id:
            address_id = production.shop_id_dest.partner_address_id.id
        source_location_id = production.product_id.product_tmpl_id.property_stock_production.id 
        location_dest_id = production.location_src_id.id
  
        # Take next Sequence number of shipment base on type
        pick_name = 'ENVIO DE PRODUCCIÓN ' + ir_sequence.get(cr, uid, 'stock.picking.' + pick_type)
  
        picking_id = stock_picking.create(cr, uid, {
            'shop_id': production.shop_id_dest.id,
            'shop_id_dest': production.shop_id.id,
            'location_id': source_location_id,
            'location_dest_id': location_dest_id,
            'partner_id':production.company_id.partner_id.id,
            'internal_out': True,
            'confirm_reposition': False,
            'name': pick_name,
            'origin': (production.origin or '').split(':')[0] + ':' + production.name,
            'type': pick_type,
            'move_type': 'one',
            'stock_journal_id': journal_id,
            'state': 'draft',
            'address_id': address_id,
            'auto_picking': self._get_auto_picking(cr, uid, production),
            'company_id': production.company_id.id,
        })
        production.write({'picking_id': picking_id}, context=context)
        return picking_id


#     def _make_production_produce_line(self, cr, uid, production, production_id, context=None):
#         stock_move = self.pool.get('stock.move')
#         moves_ids=[]
#         source_location_id = production.product_id.product_tmpl_id.property_stock_production.id
#         destination_location_id = production.location_dest_id.id
#         move_name = _('PROD: %s') + production.name 
#         for line in production.bom_id.bom_lines:
#             data = {
#                 'name': move_name,
#                 'date': production.date_planned,
#                 'product_id': line.product_id.id,
#                 'product_qty': production.product_qty * line.product_qty,
#                 'product_uom': line.product_uom.id,
#                 'product_uos_qty': production.product_uos_qty or False,
#                 'product_uos': line.product_id.product_tmpl_id.uos_id.id or False,
#                 'location_id': source_location_id,
#                 'location_dest_id': destination_location_id,
#                 'move_dest_id': production.move_prod_id.id,
#                 'picking_id': production_id,
#                 'state': 'draft',
#                 'company_id': production.company_id.id,
#                 'active':True
#             }
#             move_id = stock_move.create(cr, uid, data, context=context)
#             moves_ids.append(move_id)
#         stock_move.action_done(cr,uid,moves_ids,context)
#         production.write({'move_created_ids': [(6, 0, [move_id])]}, context=context)
#         return move_id


    def _make_production_produce_line(self, cr, uid, production, production_id, context=None):
        stock_move = self.pool.get('stock.move')
        moves_ids=[]
        source_location_id = production.product_id.product_tmpl_id.property_stock_production.id
        destination_location_id = production.location_dest_id.id
        move_name = _('PROD: %s') + production.name 
        data = {
            'name': move_name,
            'date': production.date_planned,
            'product_id': production.product_id.id,
            'product_qty': production.product_qty,
            'product_uom': production.product_uom.id,
            'product_uos_qty': production.product_uos and production.product_uos_qty or False,
            'product_uos': production.product_uos and production.product_uos.id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'move_dest_id': production.move_prod_id.id,
            'picking_id': production_id,
            'state': 'draft',
            'company_id': production.company_id.id,
        }
        move_id = stock_move.create(cr, uid, data, context=context)
        #stock_move.action_done(cr,uid,[move_id],context)
        production.write({'move_created_ids': [(6, 0, [move_id])]}, context=context)
        return move_id
    
    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms production order.
        @return: Newly generated Shipment Id.
        """
        shipment_id = False
        wf_service = netsvc.LocalService("workflow")
        uncompute_ids = filter(lambda x:x, [not x.product_lines and x.id or False for x in self.browse(cr, uid, ids, context=context)])
        self.action_compute(cr, uid, uncompute_ids, context=context)
        
        for production in self.browse(cr, uid, ids, context=context):
#             if not production.workcenter_lines:
#                 raise osv.except_osv(_('Aviso!'),_('Necesita definir por lo menos un Centro de Trabajo para iniciar la producción.'))
            location_id = production.product_id.product_tmpl_id.property_stock_production.id
            location_dest_id = production.location_dest_id.id
            production_id = self._make_production_internal_shipment(cr, uid, location_id, location_dest_id, production, context=context)
            if production_id:
                produce_move_id = self._make_production_produce_line(cr, uid, production, production_id,context=context)
                #self.pool.get('stock.move').browse(cr,uid,produce_move_id).state
            # Take routing location as a Source Location.
            source_location_id = production.location_src_id.id
            if production.bom_id.routing_id and production.bom_id.routing_id.location_id:

                source_location_id = production.product_id.product_tmpl_id.property_stock_production.id
            location_id = production.location_src_id.id 
            location_dest_id = production.product_id.product_tmpl_id.property_stock_production.id
            shipment_id = self._make_production_internal_shipment(cr, uid, location_id, location_dest_id, production, context=context)

            
            for line in production.product_lines:
                consume_move_id = self._make_production_consume_line(cr, uid, line, produce_move_id, source_location_id=source_location_id, context=context)
                if shipment_id:
                    shipment_move_id = self._make_production_internal_shipment_line(cr, uid, line, shipment_id, consume_move_id, destination_location_id=source_location_id, production=production.id,context=context)
                    self._make_production_line_procurement(cr, uid, line, shipment_move_id, context=context)
            
#             if shipment_id:        
#                 wf_service.trg_validate(uid, 'stock.picking', shipment_id, 'button_confirm', cr)
            production.write({'state':'confirmed'}, context=context)
            message = _("Manufacturing order '%s' is scheduled for the %s.") % (
                production.name,
                datetime.strptime(production.date_planned,'%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y'),
            )
            self.log(cr, uid, production.id, message)
        return shipment_id

    def force_production(self, cr, uid, ids, *args):
        shipment_id = False
        wf_service = netsvc.LocalService("workflow")
        pubication = self.pool.get('product.ubication')
        stock_obj = self.pool.get('stock.move')
        procurement_ids = []
        new_picking = False
        for production in self.browse(cr, uid, ids):
            if production.picking_id and production.picking_id.state <> 'done':
                raise osv.except_osv(_('Aviso!'),_('Necesita receptar el Picking %s para empezar el proceso de producción.')%production.picking_id.name)
            else:
                self.action_in_production(cr,uid,ids)
            if production.move_lines and not production.picking_id:
                location_id = production.location_src_id.id 
                location_dest_id = production.location_dest_id.id
                for move in production.move_lines:
                    if move.state == 'waiting':
                        ubication_ids = pubication.search(cr,uid,[('product_id','=',move.product_id.id),('location_ubication_id','=',location_id)])
                        if ubication_ids: 
                            qty = pubication.browse(cr,uid,ubication_ids[0]).qty
                            if move.product_qty > qty :
                                new_picking = True
                                procurement_ids.append([move.id,(move.product_qty - qty)])
            if new_picking:
                context = {}
                shipment_id = self._make_production_internal_shipment(cr, uid, production, context=context)
                production.write({'picking_id':shipment_id}, context=context)
                if shipment_id:
                    for p in procurement_ids:
                        line = stock_obj.browse(cr,uid,p[0])
                        consume_move_id = p[1]
                        source_location_id= production.location_src_id.id
                        shipment_move_id = self._make_production_internal_shipment_line(cr, uid, line, shipment_id, consume_move_id, destination_location_id=source_location_id, production=production.id, context=context)
                     
        return True
   
    def onchange_shop(self, cr, uid, ids, shop_id=False, context={}):
        values={}
        domain={}
        default_internal_out = False
        if context is None:
            context = {}
        if context.get('default_internal_out',False):
            default_internal_out = context.get('default_internal_out',False)        
        if shop_id:
            shop=self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
            search_location = self.pool.get('stock.location').search(cr, uid, [('location_id','child_of',[shop.warehouse_id.lot_stock_id.location_id.id])])
            if context.get('location_src_id',False) != shop.warehouse_id.lot_stock_id.id:
                values['location_src_id']=shop.warehouse_id.lot_stock_id.id
            else:
                search_location1 = search_location[:]
                shop.warehouse_id.lot_stock_id.id and search_location1.remove(shop.warehouse_id.lot_stock_id.id)
                values['location_src_id']= search_location1 and search_location1[0] or None
            domain['location_src_id']=[('id', 'in', search_location)]
        if not default_internal_out:
            domain['shop_id']=[('id', '=', shop_id)]
        return {'value':values, 'domain':domain}
     
    def onchange_shop_dest(self, cr, uid, ids, shop_id=False, context={}):
        values={}
        domain={}
        if context is None:
            context = {}
        if shop_id:
            shop=self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
            values['address_id']=shop.partner_address_id.id
            values['partner_id']=shop.company_id.partner_id.id
            search_location = self.pool.get('stock.location').search(cr, uid, [('location_id','child_of',[shop.warehouse_id.lot_input_id.location_id.id])])
            if context.get('location_id',False) != shop.warehouse_id.lot_input_id.id:
                values['location_dest_id']=shop.warehouse_id.lot_input_id.id
            else:
                search_location1 = search_location[:]
                shop.warehouse_id.lot_input_id.id and search_location1.remove(shop.warehouse_id.lot_input_id.id)
                values['location_dest_id']= search_location1 and search_location1[0] or None
            domain['location_dest_id']=[('id', 'in', search_location)]
        return {'value':values,'domain':domain}
     
    def onchange_location(self, cr, uid, ids, location_src_id=False,location_dest_id=False, context=None):
        values={}
        warning={}
        if location_src_id :
            usage = self.pool.get('stock.location').browse(cr,uid,location_src_id).usage
            if usage =='view':
                raise osv.except_osv(_('Aviso!'), _('Solo puede usar bodegas tipo interno, producción o abastecimiento.'))
        if location_dest_id:
            if usage =='view':
                raise osv.except_osv(_('Aviso!'), _('Solo puede usar bodegas tipo interno, producción o abastecimiento.'))

#             if location_src_id == location_dest_id:
#                 warning['title']= _('Location Incorrect !')
#                 warning['message']= _("Las bodegas de origen y destino deben ser diferentes")
#                 values['location_id']=location_src_id
#                 values['location_dest_id']=False
        return {'value':values,'warning':warning}

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce
        @param production_mode: specify production mode (consume/consume&produce).
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        production = self.browse(cr, uid, production_id, context=context)

        produced_qty = 0
        for produced_product in production.move_created_ids2:
            if (produced_product.scrapped) or (produced_product.product_id.id <> production.product_id.id):
                continue
            produced_qty += produced_product.product_qty

        if production_mode in ['consume','consume_produce']:
            consumed_data = {}

            # Calculate already consumed qtys

            prod_shp_id = self._make_action_consume(cr, uid, production, context=context)
            if prod_shp_id:
                context.update({'picking_id':prod_shp_id})            
                for consumed in production.move_lines2:
                    if consumed.scrapped:
                        continue
                    if not consumed_data.get(consumed.product_id.id, False):
                        consumed_data[consumed.product_id.id] = 0
                    consumed_data[consumed.product_id.id] += consumed.product_qty
    
                # Find product qty to be consumed and consume it
    
                    for scheduled in production.product_lines:
        
                        # total qty of consumed product we need after this consumption
                        total_consume = ((production_qty + produced_qty) * scheduled.product_qty / production.product_qty)
        
                        # qty available for consume and produce
                        qty_avail = scheduled.product_qty - consumed_data.get(scheduled.product_id.id, 0.0)
        
                        if qty_avail <= 0.0:
                            # there will be nothing to consume for this raw material
                            continue
        
                        raw_product = [move for move in production.picking_id.move_lines if move.product_id.id==scheduled.product_id.id]
                        if raw_product:
                            # qtys we have to consume
                            qty = total_consume - consumed_data.get(scheduled.product_id.id, 0.0)
        #                     if float_compare(qty, qty_avail, precision_rounding=scheduled.product_id.uom_id.rounding) == 1:
        #                         # if qtys we have to consume is more than qtys available to consume
        #                         prod_name = scheduled.product_id.name_get()[0][1]
        #                         raise osv.except_osv(_('Warning!'), _('You are going to consume total %s quantities of "%s".\nBut you can only consume up to total %s quantities.') % (qty, prod_name, qty_avail))
                            if qty <= 0.0:
                                # we already have more qtys consumed than we need 
                                continue
        
                            consumed = 0
                            rounding = raw_product[0].product_uom.rounding
        
                            # sort the list by quantity, to consume smaller quantities first and avoid splitting if possible
                            raw_product.sort(key=attrgetter('product_qty'))
                            
                            # search for exact quantity
                            for consume_line in raw_product:
                                if tools.float_compare(consume_line.product_qty, qty, precision_rounding=rounding) == 0:
                                    # consume this line
                                    consume_line.action_consume(qty, consume_line.location_id.id, context=context)
                                    consumed = qty
                                    break
        
                            index = 0                        
                            # consume the smallest quantity while we have not consumed enough
                            while tools.float_compare(consumed, qty, precision_rounding=rounding) == -1 and index < len(raw_product):
                                consume_line = raw_product[index]
                                to_consume = min(consume_line.product_qty, qty - consumed) 
                                consume_line.action_consume(to_consume, consume_line.location_id.id, context=context)
                                consumed += to_consume
                                index += 1
    
    
                prod_shp_id = self._make_action_consume(cr, uid, production, context=context)
                if prod_shp_id:
                    context.update({'picking_id':prod_shp_id})

                    if production_mode == 'consume_produce':
                        # To produce remaining qty of final product
                        #vals = {'state':'confirmed'}
                        #final_product_todo = [x.id for x in production.move_created_ids]
                        #stock_mov_obj.write(cr, uid, final_product_todo, vals)
                        #stock_mov_obj.action_confirm(cr, uid, final_product_todo, context)
                        produced_products = {}
                        for produced_product in production.move_created_ids2:
                            if produced_product.scrapped:
                                continue
                            if not produced_products.get(produced_product.product_id.id, False):
                                produced_products[produced_product.product_id.id] = 0
                            produced_products[produced_product.product_id.id] += produced_product.product_qty
            
                        for produce_product in production.move_created_ids:
                            produced_qty = produced_products.get(produce_product.product_id.id, 0)
                            subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                            rest_qty = (subproduct_factor * production.product_qty) - produced_qty
            
                            if rest_qty < production_qty:
                                prod_name = produce_product.product_id.name_get()[0][1]
                                raise osv.except_osv(_('Warning!'), _('You are going to produce total %s quantities of "%s".\nBut you can only produce up to total %s quantities.') % (production_qty, prod_name, rest_qty))
                            if rest_qty > 0 :
                                stock_mov_obj.action_consume(cr, uid, [produce_product.id], (subproduct_factor * production_qty), context=context)
            
                    for raw_product in production.move_lines2:
                        new_parent_ids = []
                        parent_move_ids = [x.id for x in raw_product.move_history_ids]
                        for final_product in production.move_created_ids2:
                            if final_product.id not in parent_move_ids:
                                new_parent_ids.append(final_product.id)
                        for new_parent_id in new_parent_ids:
                            stock_mov_obj.write(cr, uid, [raw_product.id], {'move_history_ids': [(4,new_parent_id)]})
        
                wf_service = netsvc.LocalService("workflow")
                self.write(cr, uid, [production_id], {'state':'done'})
                wf_service.trg_validate(uid, 'mrp.production', production_id, 'button_produce_done', cr)
                return True

 
    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the production order and related stock moves.
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        for production in self.browse(cr, uid, ids, context=context):
            if production.state == 'confirmed' and production.picking_id.state not in ('draft', 'cancel'):
                raise osv.except_osv(
                    _('Could not cancel manufacturing order !'),
                    _('You must first cancel related internal picking attached to this manufacturing order.'))
            if production.move_created_ids:
                move_obj.action_cancel(cr, uid, [x.id for x in production.move_created_ids],context)
            move_obj.action_cancel(cr, uid, [x.id for x in production.move_lines],context)
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

mrp_production()


class mrp_bom(osv.osv):

    _inherit = 'mrp.bom'
    _description = 'Bill of Material'

    _columns = {
                'standard_price': fields.float('Costo', digits_compute=dp.get_precision('Purchase Price')),
                'subtotal_cost': fields.float('Subtotal', digits_compute=dp.get_precision('Purchase Price')),
                'product_qty': fields.float('Ctdad producto', digits_compute=dp.get_precision('Purchase Price')),
                'notes': fields.text('Observaciones')
                }


    def onchange_product_id(self, cr, uid, ids, product_id, name, product_qty, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        cost = 0
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if prod.packing_q == 0:
                packing_q = 1
            else: 
                packing_q = prod.packing_q
            if prod.uom_po_id.id == prod.uom_id.id:    
                if prod.standard_price and product_qty:
                    cost = prod.standard_price
                    subtotal_cost = prod.standard_price * product_qty 
                else:
                    subtotal_cost = 0.00
            else:
                   
                if prod.standard_price and product_qty:
                    cost = prod.standard_price/ packing_q
                    subtotal_cost = prod.standard_price * product_qty / packing_q
                else:
                    subtotal_cost = 0.00
            return {'value': {'name': prod.name, 'product_uom': prod.uom_id.id,'standard_price':cost, 'subtotal_cost': subtotal_cost}}
        return {}



mrp_bom()


class StockMove(osv.osv):
    _inherit = 'stock.move'

    def action_consume(self, cr, uid, ids, product_qty, location_id=False, context=None): 
        """ Consumed product with specific quatity from specific source location.
        @param product_qty: Consumed product quantity
        @param location_id: Source location
        @return: Consumed lines
        """       
        res = []
        production_obj = self.pool.get('mrp.production')
        if context:
            picking_id = context.get('picking_id',False)
            if picking_id:
                self.write(cr,uid,ids,{'picking_id':picking_id})
        wf_service = netsvc.LocalService("workflow")        
        for move in self.browse(cr, uid, ids):
            if product_qty <= 0:
                raise osv.except_osv(_('Warning!'), _('Please provide Proper Quantity !'))
            res = []
            move_qty = move.product_qty
            if move_qty <= 0:
                raise osv.except_osv(_('Error!'), _('Can not consume a move with negative or zero quantity !'))
            quantity_rest = move.product_qty
            quantity_rest -= product_qty
            uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty
            if quantity_rest <= 0:
                quantity_rest = 0
                uos_qty_rest = 0
                quantity = move.product_qty

            uos_qty = quantity / move_qty * move.product_uos_qty
            if quantity_rest > 0:
                default_val = {
                    'product_qty': quantity,
                    'product_uos_qty': uos_qty,
                    'state': move.state,
                    'location_id': location_id or move.location_id.id,
                }
                current_move = self.copy(cr, uid, move.id, default_val)
                res += [current_move]
                update_val = {}
                update_val['product_qty'] = quantity_rest
                update_val['product_uos_qty'] = uos_qty_rest
                self.write(cr, uid, [move.id], update_val)

            else:
                quantity_rest = quantity
                uos_qty_rest =  uos_qty
                res += [move.id]
                update_val = {
                        'product_qty' : quantity_rest,
                        'product_uos_qty' : uos_qty_rest,
                        'location_id': location_id or move.location_id.id,
                }
                self.write(cr, uid, [move.id], update_val)

            product_obj = self.pool.get('product.product')
            for new_move in self.browse(cr, uid, res, context=context):
                for (id, name) in product_obj.name_get(cr, uid, [new_move.product_id.id]):
                    message = _("Product  '%s' is consumed with '%s' quantity.") %(name, new_move.product_qty)
                    self.log(cr, uid, new_move.id, message)
            self.action_done(cr, uid, res, context=context)
            
            production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])
            for prod in production_obj.browse(cr, uid, production_ids, context=context):
                if prod.state == 'confirmed':
                    production_obj.force_production(cr, uid, [prod.id])
                wf_service.trg_validate(uid, 'mrp.production', prod.id, 'button_produce', cr)
#             for new_move in new_moves:
#                 if new_move == move.id:
#                     This move is already there in move lines of production order
#                     continue
#                 production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})
#                 res.append(new_move)
        return res
        
StockMove()