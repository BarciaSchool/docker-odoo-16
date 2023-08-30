# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A (Lajonner Crespín Moran) 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################
from osv import osv, fields
from tools.translate import _
import time
import traceback

class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
              "is_procurement":fields.boolean("Is procurement"),
              }
    _defaults = {
               "is_procurement":False,
               }

stock_picking()

class stock_move(osv.osv):
    _inherit = "stock.move"
    _columns = {
              "stock_warehouse_orderpoint_id":fields.many2one('stock.warehouse.orderpoint', 'Minimum Stock Rules'),
              }

stock_move()

class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
              "sequence":fields.integer("Sequence", help="The lower the value of the first sequence will be served their supply"),
              "picking_shop_id":fields.many2one("sale.shop", "Shop Biller")
              }

stock_warehouse()

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {
                "picking_warehouse_ids":fields.one2many("stock.warehouse", "picking_shop_id", "Warehouses")
                }
        
    def onchange_central_warehouse(self, cr, uid, ids, central_warehouse, company_id=False, context=None):
        if(context is None):
            context = {}
        if(not company_id):
            return {}
        if(not central_warehouse):
            return {}
        for warehouse_id in ids:
            criterias = company_id and [('company_id', '=', company_id), ('central_warehouse', '=', central_warehouse), ('id', '!=', warehouse_id)] or [('company_id', '=', company_id), ('central_warehouse', '=', central_warehouse)]
            if (self.search_count(cr, uid, criterias)):
                return {"value":{"central_warehouse":False},
                        "warning":{"title":_("Validation Error!"), "message":_("There should be only one central warehouse by company.")}}
        return {}

sale_shop()

class delivery_carrier(osv.osv):
    _inherit = "delivery.carrier"
    _columns = {
              "default":fields.boolean("Default"),
              }
    _default = {
              "default":False
              }
    
    def onchange_default(self, cr, uid, ids, partner_id, default, context=None):
        if(context is None):
            context = {}
        for carrier_id in ids:
            if (self.search_count(cr, uid, [("id", "!=", carrier_id), ("default", "=", True), ("partner_id", "=", partner_id), ("active", "=", True)])):
                return {"value":{"default":False},
                        "warning":{"title":_("Validation Error!"), "message":_("There should be only one default carrier by company.")}}
        return {}
    
delivery_carrier()

class stock_warehouse_orderpoint(osv.osv):
    
    _inherit = "stock.warehouse.orderpoint"
    _columns = {
              "stock_move_ids":fields.one2many('stock.move', 'stock_warehouse_orderpoint_id', 'Stock Moves'),
            }
    
    def _check_unique_rules(self, cr, uid, ids):
        for browse_stock_warehouse_orderpoint in self.browse(cr, uid, ids):
            if(self.search(cr, uid, [('active', '=', True), ('company_id', '=', browse_stock_warehouse_orderpoint.company_id.id), ('product_id', '=', browse_stock_warehouse_orderpoint.product_id.id), ('location_id', '=', browse_stock_warehouse_orderpoint.location_id.id), ('id', '!=', browse_stock_warehouse_orderpoint.id)])): return False
        return True
    
    _constraints = [(_check_unique_rules, _('Can only be one active minimum stock rule by location !'), ['name', 'product_id', 'location_id', 'active'])]


    def create_internal_procurement(self, cr, uid, company_id, origin_sale_shop_ids, automatic=False, context=None):
        if context is None:
            context = {}
        warehouse_object = self.pool.get('stock.warehouse')
        stock_picking_object = self.pool.get("stock.picking")
        stock_location_object = self.pool.get('stock.location')
        stock_move_object = self.pool.get('stock.move')
        purchase_order_object = self.pool.get("purchase.order")        
        purchase_order_line_object = self.pool.get("purchase.order.line")
        message_ok = False
        message_error = False
        message_product_error = False
        try:
            warehouse_ids = warehouse_object.search(cr, uid, [], context=context, order="sequence asc")##lista de warehouses
            for warehouse in warehouse_object.browse(cr, uid, warehouse_ids, context=context):            
                stock_move_ids = []
                vals_stock_picking = {}
                purchase_orders = {}
                purchase_order_lines = {}  
                cr.execute("select name,date from stock_picking where is_procurement=true and date>=current_date and date<current_date+1 and company_id=%s and state!='draft' and location_dest_id=%s", (warehouse.company_id.id, warehouse.lot_input_id.id))
                pickings = cr.fetchall()
                ##un solo picking de abastecimiento por dia
                if(pickings):
                    message_error = message_error and "%s\n Today,only one picking can be created by provision on %s." % (message_error, warehouse.lot_input_id.name,) or "Today,only one picking can be created by provision on %s." % (warehouse.lot_input_id.name,)
                    continue
                ##si no hay picking pendiente por despachar
                if(stock_picking_object.search(cr, uid, [('state', '=', 'auto'), ('is_procurement', '=', True), ('company_id', '=', warehouse.company_id.id), ('location_dest_id', '=', warehouse.lot_input_id.id)])):
                    message_error = message_error and "%s\n There pickings pending dispatch on %s ." % (message_error, warehouse.lot_input_id.name,) or "There pickings pending dispatch %s." % (warehouse.lot_input_id.name)
                    continue
                cr.execute("select name,date_order from purchase_order where is_procurement=true and date_order>=current_date and date_order<current_date+1 and company_id=%s and location_id=%s", (warehouse.company_id.id, warehouse.lot_input_id.id))
                orders=cr.fetchall()
                ##una sola orden de compra por dia
                if(orders):
                    message_error=message_error and "%s\n Today,only one purchase order can be created by provision on %s." % (message_error, warehouse.lot_input_id.name,) or "Today,only one purchase order can be created by provision on %s." % (warehouse.lot_input_id.name,)
                    continue
                ##si hay ordenes de compra por procesar
                if(stock_picking_object.search(cr, uid, [('state', 'in',('draft','wait','confirmed')),('is_procurement', '=', True), ('company_id', '=', warehouse.company_id.id), ('location_dest_id', '=', warehouse.lot_input_id.id)])):
                    message_error = message_error and "%s\n There purchase orders pending to confirm %s ." % (message_error, warehouse.lot_input_id.name,) or "There purchase orders pending to confirm %s." % (warehouse.lot_input_id.name)
                    continue
                picking_id = False
                search_stock_warehouse_orderpoint = self.search(cr, uid, [('warehouse_id', '=', warehouse.id), ('active', '=', True)])
                browse_origin_sale_shop = self.pool.get("sale.shop").browse(cr, uid, origin_sale_shop_ids[0], context)
                if(search_stock_warehouse_orderpoint):##si hay reglas de stock minimo
                    if(warehouse.id != browse_origin_sale_shop.warehouse_id.id):##si es diferente la tienda de origen de la de destino
                        vals_stock_picking = {"name":self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.inventory') or "PROVISION %s/%s %s" % (warehouse.name, warehouse.lot_input_id.name, time.strftime('%Y-%m-%d')),
                                          "digiter_id":uid, "shop_id":origin_sale_shop_ids[0],
                                          "shop_id_dest":self._get_shop_dest_id(cr, uid, warehouse, context), ##???
                                          "location_id":browse_origin_sale_shop.warehouse_id.lot_input_id.id,
                                          "location_dest_id":warehouse.lot_input_id.id, "address_id":warehouse.lot_input_id.address_id.id,
                                          "carrier_id":self._get_carrier_id(cr, uid, warehouse.company_id.partner_id.id, context),
                                          "date":time.strftime('%Y-%m-%d'), "is_procurement":True, "type":"internal", "consigment":False, "internal_out":True,
                                          "company_id":warehouse.company_id.id,
                                          "partner_id":warehouse.company_id.partner_id.id,
                                          "note":"PROVISION %s/%s %s" % (warehouse.name, warehouse.lot_input_id.name, time.strftime('%Y-%m-%d'),),
                                          }
                        picking_id = stock_picking_object.create(cr, uid, vals_stock_picking, context)                    
                    for browse_stock_warehouse_orderpoint in self.browse(cr, uid, search_stock_warehouse_orderpoint, context):
                        browse_product_product = browse_stock_warehouse_orderpoint.product_id
                        if(browse_product_product.state != 'obsolete'):##si no es producto obsoleto
                            central_stock = stock_location_object._product_virtual_get(cr, uid, browse_origin_sale_shop.warehouse_id.lot_input_id.id, [browse_product_product.id], {'uom': browse_stock_warehouse_orderpoint.product_uom.id})[browse_product_product.id]
                            if(warehouse.id == browse_origin_sale_shop.warehouse_id.id):
                                if(central_stock < browse_stock_warehouse_orderpoint.product_min_qty):
                                    purchase = self.get_purchase_order(cr, uid, purchase_orders, browse_product_product, warehouse, browse_stock_warehouse_orderpoint.location_id, context)
                                    if(not purchase[3]):
                                        message_product_error = self._get_message_error(cr, uid, message_product_error, browse_product_product, purchase[1], purchase[2])
                                        continue
                                    purchase_orders = purchase[0]
                                    purchase_order_lines = self.get_purchase_order_line(cr, uid, purchase_orders, purchase_order_lines, browse_product_product, warehouse, browse_stock_warehouse_orderpoint, browse_stock_warehouse_orderpoint.product_max_qty - central_stock, purchase[2], context)
                            else:
                                location_stock = stock_location_object._product_virtual_get(cr, uid, warehouse.lot_input_id.id, [browse_product_product.id], {'uom': browse_stock_warehouse_orderpoint.product_uom.id})[browse_product_product.id]
                                if(location_stock < browse_stock_warehouse_orderpoint.product_min_qty):##si el stock de la ubicacion es menor al minimo permitido                                                  
                                    value = browse_stock_warehouse_orderpoint.product_max_qty - location_stock##cantidad a reponer 
                                    if(value > 0):##si la cantidad a reponer es mayor a 0
                                        if(value >= central_stock):##si la cantidad a reponer es mayor al stock de la bodega central
                                            purchase = self.get_purchase_order(cr, uid, purchase_orders, browse_product_product, warehouse, browse_stock_warehouse_orderpoint.location_id, context)
                                            if(not purchase[3]):
                                                message_product_error = self._get_message_error(cr, uid, message_product_error, browse_product_product, purchase[1], purchase[2])
                                                continue
                                            purchase_orders = purchase[0]
                                            purchase_order_lines = self.get_purchase_order_line(cr, uid, purchase_orders, purchase_order_lines, browse_product_product, warehouse, browse_stock_warehouse_orderpoint, value, purchase[2], context)
                                        else:##
                                            search_stock_warehouse_orderpoint_central = self.search(cr, uid, [('warehouse_id', '=', browse_origin_sale_shop.warehouse_id.id), ('active', '=', True), ('product_id', '=', browse_product_product.id)])
                                            make_stock_move = True
                                            ##verificar si se puede reponer ,verificar reglas de stock minimo de la tienda central
                                            if (search_stock_warehouse_orderpoint_central):
                                                browse_stock_warehouse_orderpoint_central = self.browse(cr, uid, search_stock_warehouse_orderpoint_central[0], context)
                                                if(browse_stock_warehouse_orderpoint_central):
                                                    if((central_stock - value) <= browse_stock_warehouse_orderpoint_central.product_min_qty):##si el nuevo stock de la tienda central va a ser menor que el minimo requerido no hacer el movimiento
                                                        make_stock_move = False
                                            if(make_stock_move):
                                                vals_stock_move = {
                                                        'name': "%s-%s" % (vals_stock_picking["name"], browse_product_product.default_code),
                                                        'location_id': browse_origin_sale_shop.warehouse_id.lot_input_id.id,
                                                        'product_id': browse_product_product.id,
                                                        "ubication_id":self._get_inmove_ubication_id(cr, uid, browse_origin_sale_shop.warehouse_id.lot_input_id, browse_product_product.id),
                                                        "location_dest_id":self._get_location_dest_id(cr, uid, context),
                                                        'product_uom': browse_stock_warehouse_orderpoint.product_uom.id,
                                                        'product_uos': browse_stock_warehouse_orderpoint.product_uom.id,
                                                        'company_id': browse_stock_warehouse_orderpoint.company_id.id,
                                                        'auto_validate': True,
                                                        'picking_id':picking_id,
                                                        'date_expected': time.strftime('%Y-%m-%d'),
                                                        'state': 'draft',
                                                        'product_qty': value,
                                                        'stock_warehouse_orderpoint_id':browse_stock_warehouse_orderpoint.id,
                                                    }
                                                stock_move_ids.append(stock_move_object.create(cr, uid, vals_stock_move, context))
                                            else:
                                                purchase = self.get_purchase_order(cr, uid, purchase_orders, browse_product_product, warehouse, browse_stock_warehouse_orderpoint.location_id, context)
                                                if(not purchase[3]):
                                                    message_product_error = self._get_message_error(cr, uid, message_product_error, browse_product_product, purchase[1], purchase[2])
                                                    continue
                                                purchase_orders = purchase[0]
                                                purchase_order_lines = self.get_purchase_order_line(cr, uid, purchase_orders, purchase_order_lines, browse_product_product, warehouse, browse_stock_warehouse_orderpoint, value, purchase[2], context)
                    if(picking_id):
                        if(not stock_move_ids):##si nunca creo al menos una linea --elimina el stock_picking creado
                            stock_picking_object.unlink(cr, uid, [picking_id], context)
                        else:##valida el stock picking
                            stock_picking_object.draft_validate(cr, uid, [picking_id], context)
                            message_ok = message_ok and message_ok + "\nPICKING: " + vals_stock_picking["name"] or "PICKING:" + vals_stock_picking["name"]##agrega una linea al mensaje de los pickings hechos en res_request
                for purchase_type in purchase_order_lines:
                    for purchase_partner_id in purchase_order_lines.get(purchase_type, {}):##recorre la linea de las ordenes de compra
                        if(purchase_order_lines[purchase_type].get(purchase_partner_id, [])):##si existen lineas
                            order_id = purchase_order_object.create(cr, uid, purchase_orders[purchase_type][purchase_partner_id], context)##crea una orden de compra
                            for purchase_lines in purchase_order_lines[purchase_type][purchase_partner_id]:##recorre las lineas
                                purchase_lines["order_id"] = order_id##asigna la orden a las lineas
                                purchase_order_line_object.create(cr, uid, purchase_lines, context)##crea las lineas
                            if(automatic):
                                pass##APROBAR LAS ORDENES DE COMPRA
                        message_ok = message_ok and message_ok + "\nPURCHASE ORDER: " + purchase_orders[purchase_type][purchase_partner_id]["name"] or "PURCHASE ORDER: " + purchase_orders[purchase_type][purchase_partner_id]["name"]##por cada orden creada agrega un lineas a la informacion del res_request
            message_ok = message_ok and "ACTIONS:\n" + message_ok or "\n\n ACTIONS: NO"##armar mensaje informacion correcta
            message_error = message_error and "\n\n EXCEPTIONS:\n" + message_error or "\n\n EXCEPTIONS: NO"##armar mensaje informacion erronea
            message_product_error = message_product_error and "\n\n UNPROCESSED PRODUCTS:\n" + message_product_error or "\n\n UNPROCESSED PRODUCTS: NO"
            self.send_request_message(cr, uid, "PICKINGS AND PURCHASE ORDERS %s" % (time.strftime('%Y-%m-%d'),), message_ok + message_error + message_product_error, False, context)##crear informe
        except Exception:##cualquier exception
            self.send_request_message(cr, uid, "PICKING AND PURCHASE ORDER -ERRORS %s" % (time.strftime('%Y-%m-%d')),"ABORTED TRANSACTION", True, context)
        return True
        
    def get_purchase_order(self, cr, uid, purchase_orders, browse_product_product, browse_stock_warehouse, browse_stock_location, context=None):
        if(context is None):
            context = {}
        purchase_order_object = self.pool.get("purchase.order")
        partner_id = browse_product_product.manufacturer and browse_product_product.manufacturer.partner_id and browse_product_product.manufacturer.partner_id.id or False
        type_purchase = False
        if(partner_id):
            type_purchase = self._get_type_purchase(cr, uid, browse_product_product.manufacturer.partner_id, browse_product_product, context)
            if(not type_purchase):
                return (purchase_orders, partner_id, type_purchase, False) 
            if(not purchase_orders.has_key(type_purchase)):
                purchase_orders[type_purchase] = {}
            if(not purchase_orders[type_purchase].has_key(partner_id)):                
                purchase_orders[type_purchase][partner_id] = {
                                             "name":self.pool.get("ir.sequence").get(cr, uid, 'internal.transaction') or "PROVISION %s/%s %s %s" % (browse_stock_warehouse.name, browse_stock_warehouse.lot_input_id.name, browse_product_product.manufacturer.partner_id.name, time.strftime('%Y-%m-%d')),
                                             "partner_id":partner_id,
                                             "company_id":browse_stock_warehouse.company_id.id,
                                             "shop_id":browse_stock_warehouse.picking_shop_id.id,
                                             'solicited':self._get_buyer_id(cr, uid, browse_product_product.manufacturer.partner_id, uid, context),
                                             "warehouse_id":browse_stock_warehouse.id,
                                             "location_id":browse_stock_location.id,
                                             "date_order":time.strftime('%Y-%m-%d'),
                                             "notes":"PROVISION %s/%s %s %s" % (browse_stock_warehouse.name, browse_stock_warehouse.lot_input_id.name, browse_product_product.manufacturer.partner_id.name, time.strftime('%Y-%m-%d')),
                                             "type_purchase":type_purchase,
                                             "pricelist_id":self._get_product_pricelist_id(cr, uid, context),
                                             "is_procurement":True,
                                             }
                new_context = context.copy()
                new_context['shop'] = 'headquarter'
                vals_type_purchase = purchase_order_object.onchange_type_purchase(cr, uid, [], type_purchase, context)
                vals_partner = purchase_order_object.onchange_partner_id(cr, uid, [], partner_id, type_purchase)
                vals_type_purchase = vals_type_purchase["value"] or {}
                vals_partner = vals_partner["value"] or {}
                vals_partner["payment_term"] = vals_partner["payment_term"] or self._get_payment_term_id(cr, uid, browse_product_product.manufacturer.partner_id, context)
                vals_type_purchase.update(vals_partner)
                purchase_orders[type_purchase][partner_id].update(vals_type_purchase)
                return (purchase_orders, partner_id, type_purchase, True)
        return (purchase_orders, partner_id, type_purchase, False)##DICCIONARIO DE PURCHASE ORDER,PARTNER,TIPO DE COMPRA,ES CORRECTO
    
    def get_purchase_order_line(self, cr, uid, purchase_orders, purchase_order_lines, browse_product_product, browse_stock_warehouse, browse_stock_warehouse_orderpoint, quantity, type_purchase, context=None):
        if(context is None):
            context = {}
        purcharse_order_line_object = self.pool.get("purchase.order.line")
        partner_id = browse_product_product.manufacturer and browse_product_product.manufacturer.partner_id and browse_product_product.manufacturer.partner_id.id or False
        if(not purchase_order_lines.has_key(type_purchase)):
            purchase_order_lines[type_purchase] = {}
        if(partner_id):
            lines = purchase_order_lines[type_purchase].get(partner_id, [])
            detail_line = {"product_id":browse_product_product.id,
                     "product_qty":quantity,
                     "product_uom":browse_stock_warehouse_orderpoint.product_uom.id,
                     "name":browse_product_product.name,
                     "company_id":browse_stock_warehouse.company_id.id,
                     "date_planned":time.strftime('%Y-%m-%d'),
                    }
            vals_parent = purchase_orders[type_purchase][partner_id]
            new_context = context.copy()
            new_context['force_product_uom'] = True
            new_context['type'] = 'in_invoice'
            vals_product_id = purcharse_order_line_object.onchange_product_id(cr, uid, [], vals_parent.get("pricelist_id", False), browse_product_product.id, quantity,
                            browse_stock_warehouse_orderpoint.product_uom.id, partner_id, vals_parent["date_order"], vals_parent["fiscal_position"],
                            time.strftime('%Y-%m-%d'), browse_product_product.name, browse_product_product.standard_price, "", new_context)
            vals_product_id = vals_product_id["value"] or {}
            detail_line.update(vals_product_id)
            lines.append(detail_line)
            purchase_order_lines[type_purchase][partner_id] = lines
        return purchase_order_lines
    
    def send_request_message(self, cr, uid, title, message, do_raise=True, context=None):
        name=cr.dbname
        try:
            if(not do_raise):
                self.pool.get("res.request").create(cr, uid, {"name":title, "act_from":1, "act_to":uid, "active":True, "body":message,"state":'draft'}, context)
                osv._logger.info("%s send request ok : %s",name,title)
            else:
                raise
        except:
            osv._logger.error("%s error executing send request %s",name,title)
            osv._logger.error("%s %s",name,traceback.format_exc())
            raise        
                
    def _get_message_error(self, cr, uid, message_product_error, browse_product_product, has_manufacturer, has_type):
        if(not has_manufacturer):
            return message_product_error and "%s\n THE PRODUCT %s HAS NOT  MANUFACTURER." % (message_product_error, browse_product_product.name,) or "THE PRODUCT %s HAS NOT  MANUFACTURER." % (browse_product_product.name,)
        if(not has_type):
            return message_product_error and "%s\n THE PRODUCT MANUFACTURER %s HAS NOT ORIGIN." % (message_product_error, browse_product_product.name,) or "THE PRODUCT MANUFACTURER %s HAS NOT ORIGIN." % (browse_product_product.name,)
        return message_product_error
    
    def _get_product_pricelist_id(self, cr, uid, context=None):
        search_product_pricelist = self.pool.get("product.pricelist").search(cr, uid, [('active', '=', True), ('type', '=', 'purchase')])
        if(search_product_pricelist):
            return search_product_pricelist[0]
        return False
    
    def _get_type_purchase(self, cr, uid, browse_res_partner, browse_product_product, context=None):
        object_purchase_category = self.pool.get("purchase.category")
        search_purchase_category = []
        if(browse_res_partner.origin):
            if(browse_res_partner.origin != "local"):##teoricamente los origenes son local e internacional de lo cual deberia elegir uno
                ##tambien el abastecimiento solo se hara por productos tipo almacenable
                code = (browse_product_product.timport != 'normal') and 'RAP' or 'IMP'
                search_purchase_category = object_purchase_category.search(cr, uid, [('origin', '=', browse_res_partner.origin), ('code', '=', code)])
            else:##local
                search_purchase_category = object_purchase_category.search(cr, uid, [('origin', '=', browse_res_partner.origin), ('code', '=', 'LOC')])
        if(search_purchase_category):
            return search_purchase_category[0]        
        return False
            
    def _get_buyer_id(self, cr, uid, browse_res_partner, user_id, context=None):
        if(not browse_res_partner.buyer_id):
            search_salesman_salesman = self.pool.get("salesman.salesman").search(cr, uid, [('is_buyer', '=', True), ('user_id', '=', user_id)])
            if(search_salesman_salesman):
                return search_salesman_salesman[0]
            return False
        return browse_res_partner.buyer_id.id

    def _get_payment_term_id(self, cr, uid, browse_res_partner, context=None):
        if(browse_res_partner.property_payment_term_supplier):
            return browse_res_partner.property_payment_term_supplier.id
        search_account_payment_term = self.pool.get("account.payment.term").search(cr, uid, [('default', '=', True)])
        if(search_account_payment_term):
            return search_account_payment_term[0]        
        return False
    
    def _get_shop_dest_id(self, cr, uid, browse_stock_warehouse, context=None):
        if(not browse_stock_warehouse):
            return False
        if(context is None):
            context = {}
        object_sale_shop = self.pool.get("sale.shop")
        object_stock_warehouse = self.pool.get("stock.warehouse")
        search_sale_shop = object_sale_shop.search(cr, uid, [('warehouse_id', '=', browse_stock_warehouse.id)])
        if(search_sale_shop):
            return search_sale_shop[0]
        for browse_stock_warehouse in object_stock_warehouse.browse(cr, uid, [browse_stock_warehouse.id], context):
            if(browse_stock_warehouse.picking_shop_id):
                return browse_stock_warehouse.picking_shop_id.id
        return False
    
    def _get_location_dest_id(self, cr, uid, context):
        search_stock_location = self.pool.get("stock.location").search(cr, uid, [('usage', '=', 'transit')])
        if(search_stock_location):
            return search_stock_location[0]
        return False
    
    def _get_inmove_ubication_id(self, cr, uid, browse_location, product_id, context=None):
        product_ubication_object = self.pool.get("product.ubication")
        search_product_ubication = product_ubication_object.search(cr, uid, [('product_id', '=', product_id), ('location_ubication_id', '=', browse_location.id)])
        if(search_product_ubication):
            return product_ubication_object.browse(cr, uid, search_product_ubication[0], context).ubication_id.id
        return False
    
    def _get_carrier_id(self, cr, uid, partner_id, context=None):
        search_delivery_carrier = self.pool.get("delivery.carrier").search(cr, uid, [('active', '=', True), ('default', '=', True), ('partner_id', '=', partner_id)])
        if(search_delivery_carrier):
            return search_delivery_carrier[0]
        return False
        
stock_warehouse_orderpoint()