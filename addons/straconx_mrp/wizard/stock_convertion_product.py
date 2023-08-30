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
from osv import fields, osv
import time
from tools.translate import _
from straconx_warning.wizard import wizard


class stock_convertion(osv.osv_memory):
    _name = "stock.product.convertion"

    _columns = {        
        'shop_id':fields.many2one('sale.shop', 'Tienda'),
        'partner_id':fields.many2one('res.partner', 'Empresa'),
        'address_id':fields.many2one('res.partner.address', 'Dirección'),
        'company_id':fields.many2one('res.company', 'Compañía'),
        'location_id': fields.many2one('stock.location','Bodega'),
        'product_id': fields.many2one('product.product', 'Producto'),
        'qty_product_id': fields.float('Cantidad'),
        'uom_id':fields.many2one('product.uom','UdM'),
        'product_dest_id':fields.many2one('product.product', 'Nuevo Producto'),
        'qty_product_dest_id':fields.float('Nueva Cantidad'),        
        'uom_dest_id':fields.many2one('product.uom','UdM'),
        'user_id': fields.many2one('res.users','Usuario'),
        'name': fields.datetime('Nombre'),
        'picking_prod_id': fields.many2one('stock.picking','Picking Salida'),
        'picking_id': fields.many2one('stock.picking', 'Picking Entrada'),
        'move_prod_id': fields.many2one('account.move','Movimiento de Salida'),
        'move_id': fields.many2one('account.move','Movimiento de Entrada')
    }
    _defaults = {
            'user_id': lambda self, cr, uid, ctx: uid,
            'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
            'name': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    def onchange_company_id(self, cr, uid, ids, company_id, context=False):
        result = {}
        company_obj = self.pool.get('res.company')
        address_obj = self.pool.get('res.partner.address')
        if company_id:
            partner_id = company_obj.browse(cr,uid,company_id).partner_id.id
            if partner_id:
                address_ids = self.pool.get('res.partner.address').search(cr,uid, [('partner_id','=',partner_id),('type','=','default')])
                if address_ids:
                    address_id = address_obj.browse(cr,uid,address_ids[0]).id
                else:
                    raise osv.except_osv(_('Aviso'), _('Debe definir por lo menos una dirección predeterminada para la compañía'))
            result['partner_id']=partner_id
            result['address_id']=address_id            
        return {'value': result}

    def onchange_shop(self, cr, uid, ids, shop_id=False, context={}):
        values={}
        domain={}
        default_internal_out = False
        if context is None:
            context = {}
        if shop_id:
            shop=self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
            search_location = self.pool.get('stock.location').search(cr, uid, [('location_id','child_of',[shop.warehouse_id.lot_stock_id.location_id.id]),('usage','=','internal')])
            if context.get('location_id',False) != shop.warehouse_id.lot_stock_id.id:
                values['location_id']=shop.warehouse_id.lot_stock_id.id
            else:
                search_location1 = search_location[:]
                shop.warehouse_id.lot_stock_id.id and search_location1.remove(shop.warehouse_id.lot_stock_id.id)
                values['location_id']= search_location1 and search_location1[0] or None
            domain['location_id']=[('id', 'in', search_location)]
        if not default_internal_out:
            domain['shop_id']=[('id', '=', shop_id)]
        return {'value':values, 'domain':domain}
    
    def onchange_location(self, cr, uid, ids, location_origin=False, context=None):
        values={}
        warning={}
        if location_origin:
            if context:
                shop_id = context.get('shop_id',False)
                if shop_id:
                    shop=self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
                    values['location_id']=shop.warehouse_id.lot_input_id.id                
        return {'value':values,'warning':warning}
    
    def onchange_product_id(self,cr,uid, ids, product_id, qty_product_id, uom_id, product_dest_id,qty_product_dest_id, uom_dest_id, context=False):
        result = {}
        product_obj = self.pool.get('product.product')
        uom_obj = self.pool.get('product.uom')
        if product_id and product_dest_id:
            if product_id == product_dest_id:
                raise osv.except_osv(_('Aviso'), _('Los productos de origen y destino deben ser diferentes'))
            uom_id = product_obj.browse(cr,uid,product_id).uom_id.id
            result['uom_id']= uom_id
            result['product_id'] = product_id            
            result['product_dest_id']= False
            result['uom_dest_id']= False
            result['qty_product_dest_id']=0.00            
        elif product_id and not product_dest_id:
            uom_id = product_obj.browse(cr,uid,product_id).uom_id.id
            result['uom_id']= uom_id
            result['product_id'] = product_id            
        return {'value': result}
            
    def onchange_product_dest_id(self,cr,uid, ids, product_id, qty_product_id, uom_id, product_dest_id,qty_product_dest_id, uom_dest_id, context=False):
        result = {}
        product_obj = self.pool.get('product.product')
        uom_obj = self.pool.get('product.uom')
        if product_id and product_dest_id:
            if product_id == product_dest_id:
                raise osv.except_osv(_('Aviso'), _('Los productos de origen y destino deben ser diferentes'))
            uom_dest_id = product_obj.browse(cr,uid,product_dest_id).uom_id.id
            result['product_dest_id']= product_dest_id
            result['uom_dest_id']= uom_dest_id
        elif not product_id and product_dest_id:
            raise osv.except_osv(_('Aviso'), _('Primero debe elegir un producto para convertir'))
        if uom_dest_id <> uom_id:
            raise osv.except_osv(_('Aviso'), _('Solo puede convertir productos que tenga la misma unidad de medida. Si desea convertir productos con diferentes unidades de medidas, utilice la opción de Ordenes de Producción'))        
        return {'value': result}

    def create_convertion(self, cr, uid, ids, context=None):
        account_move_obj = self.pool.get('account.move')
        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        shop_obj = self.pool.get('sale.shop')
        ubication_obj = self.pool.get('product.ubication')
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        picking_prod_id = False
        picking_id = False
        move = []
        for conv in self.browse(cr,uid,ids,context):
            if conv.qty_product_id<=0 or conv.qty_product_dest_id<=0:
                raise osv.except_osv(_('Aviso'), _('No se puede convertir productos con unidades en cero o negativas'))
            production_location_ids = location_obj.search(cr,uid,[('usage','=','production'),('company_id','=',conv.company_id.id)])
            if not production_location_ids:
                raise osv.except_osv(_('Aviso'), _('Por favor, debe crear o definir una Bodega tipo Producción en su compañía para proceder'))
            else:
                production_location = location_obj.browse(cr,uid,production_location_ids[0]).id
            if conv.location_id:
                ubication_id = ubication_obj.search(cr,uid,[('product_id','=',conv.product_id.id),('location_ubication_id','=',conv.location_id.id)])[0]
                if not ubication_id:
                    raise osv.except_osv(_('Aviso'), _('Por favor, debe crear una Ubicación para el Producto saliente'))                
                qyt_product_id = ubication_obj.browse(cr,uid,ubication_id)
                ubication_dest_id = ubication_obj.search(cr,uid,[('product_id','=',conv.product_dest_id.id),('location_ubication_id','=',conv.location_id.id)])[0]
                qyt_product_dest_id = ubication_obj.browse(cr,uid,ubication_dest_id)
                if not ubication_dest_id:
                    raise osv.except_osv(_('Aviso'), _('Por favor, debe crear una Ubicación para el Producto a convertir'))
            # Crea el picking de Salida de Producto
            
            if not conv.picking_prod_id:
                tp='internal'                
                note = 'Conversión del producto' + product_obj.browse(cr,uid,conv.product_id.id).default_code+ ' al ' +product_obj.browse(cr,uid,conv.product_dest_id.id).default_code
                origin = conv.shop_id.warehouse_id.lot_stock_id.id
                dest = production_location 
                if conv.partner_id:
                    if conv.partner_id.segmento_id.id:
                        segmento_id = conv.partner_id.segmento_id.id
                    else:
                        segmento_id = self.pool.get('res.partner.segmento').search(cr,uid,['is_default','=',True])[0]                     
                    pick_name = conv.shop_id.number_sri +" - " + self.pool.get('ir.sequence').next_by_code(cr, uid, 'mrp.production')
                    data={'partner_id':conv.partner_id.id,
                          'name': pick_name,
                          'address_id': conv.address_id.id,
                          'carrier_id':conv.partner_id.property_delivery_carrier.id or None,
                          'shop_id': conv.shop_id.id,
                          'shop_id_dest': conv.shop_id.id,
                          'company_id': conv.company_id.id,
                          'location_id': origin,
                          'location_dest_id': dest, 
                          'segmento_id': segmento_id,
                          'date': conv.name,
                          'date_expected':time.strftime('%Y-%m-%d %H:%M:%S'),
                          'note': note,
                          'invoice_state': 'none',
                          'internal_out': True,
                          'user_id': uid,
                          'type': tp                          
                         }
                    picking_prod_id=picking_obj.create_picking(cr, uid, pick_name, pick_name, tp, data, context)
                    
                    data2={
                          'product_id': conv.product_id.id,
                          'product_qty': conv.qty_product_id,
                          'product_uom': conv.uom_id.id,
                          'product_uos_qty': conv.qty_product_id,
                          'product_uos': conv.uom_id.id,
                          'address_id': conv.address_id.id,
                          'company_id': conv.company_id.id,
                          'state':'assigned'
                          }
                    move_id= picking_obj.create_move(cr, uid, pick_name, conv.product_id.id, origin, dest, qyt_product_id.ubication_id.id, picking_prod_id, data2, context)
                    move.append(move_id)
                    if move:
                        move_obj.action_done(cr, uid, [move_id], context=context)
                        picking_obj.action_done(cr,uid,[picking_prod_id],context = context)                        
            
            if not conv.picking_id:
                tp='internal'                
                note = 'Conversión del producto' + product_obj.browse(cr,uid,conv.product_id.id).default_code+ ' al ' +product_obj.browse(cr,uid,conv.product_dest_id.id).default_code
                dest = conv.shop_id.warehouse_id.lot_stock_id.id
                origin = production_location 
                if conv.partner_id:
                    if conv.partner_id.segmento_id.id:
                        segmento_id = conv.partner_id.segmento_id.id
                    else:
                        segmento_id = self.pool.get('res.partner.segmento').search(cr,uid,['is_default','=',True])[0]                    
                    pick_name = 'INGRESO DE ' + pick_name
                    data3={'partner_id':conv.partner_id.id,
                          'name': pick_name,
                          'address_id': conv.address_id.id,
                          'carrier_id':conv.partner_id.property_delivery_carrier.id or None,
                          'shop_id': conv.shop_id.id,
                          'shop_id_dest': conv.shop_id.id,
                          'company_id': conv.company_id.id,
                          'location_id': dest,
                          'location_dest_id': origin, 
                          'segmento_id': segmento_id,
                          'date': conv.name,
                          'date_expected':time.strftime('%Y-%m-%d %H:%M:%S'),
                          'note': note,
                          'invoice_state': 'none',
                          'internal_in': True,
                          'user_id': uid,
                          'type': tp                          
                         }
                    picking_id=picking_obj.create_picking(cr, uid, pick_name, pick_name, tp, data3, context)
                    
                    data4={
                          'product_id': conv.product_dest_id.id,
                          'product_qty': conv.qty_product_dest_id,
                          'product_uom': conv.uom_dest_id.id,
                          'product_uos_qty': conv.qty_product_dest_id,
                          'product_uos': conv.uom_dest_id.id,
                          'address_id': conv.address_id.id,
                          'company_id': conv.company_id.id,
                          'state':'assigned'
                          }
                    move_id2= picking_obj.create_move(cr, uid, pick_name, conv.product_dest_id.id, origin, dest, qyt_product_dest_id.ubication_id.id, picking_id, data4, context)
                    if move:
                        move_obj.action_done(cr, uid, [move_id2], context=context)
                        picking_obj.action_done(cr,uid,[picking_id],context = context)           

            if picking_prod_id and picking_id:
                self.write(cr,uid,ids, {'picking_prod_id':picking_prod_id, 'picking_id':picking_id})                    
        return wizard.get_action_warning(_("Producto Dividido con éxito!"),nodestroy=True)

stock_convertion()

