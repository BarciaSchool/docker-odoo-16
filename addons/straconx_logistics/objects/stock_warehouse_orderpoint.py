from datetime import date
from osv import osv, fields
from tools.translate import _
import netsvc

class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
              "is_procurement":fields.boolean("Is procurement"),
              }
    _defaults = {
               "is_procurement":False,
               }

stock_picking()

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {}
        
    def onchange_central_warehouse(self, cr, uid, ids, central_warehouse, company_id=False, context=None):
        if(context is None):
            context = {}
        if(not company_id):
            return {}
        if(not central_warehouse):
            return {}
        for id in ids:
            criterias = company_id and [('company_id', '=', company_id), ('central_warehouse', '=', central_warehouse), ('id', '!=', id)] or [('company_id', '=', company_id), ('central_warehouse', '=', central_warehouse)]
            if (self.search_count(cr, uid, criterias)):
                return {"value":{"central_warehouse":False},
                        "warning":{"title":_("Validation Error!"), "message":_("There should be only one central warehouse by company.")}}
        return {}

sale_shop()

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
        
    def create_internal_procurement(self, cr, uid,automatic=False, context=None):
        if context is None:
            context = {}
        warehouse_obj = self.pool.get('stock.warehouse')
        stock_picking_object = self.pool.get("stock.picking")
        sale_shop_object = self.pool.get("sale.shop")
        stock_warehouse_orderpoint_object = self.pool.get("stock.warehouse.orderpoint")
        stock_location_object = self.pool.get('stock.location')
        stock_move_object = self.pool.get('stock.move')
        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)##lista de warehouses
        
        for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):            
            stock_move_ids = []
            origin_sale_shop_ids = sale_shop_object.search(cr, uid, [('company_id', '=', warehouse.company_id.id), ('central_warehouse', '=', True)])##tienda que es bodega central
            if(not origin_sale_shop_ids):##no hay 1 bodega central
                raise osv.except_osv(_('Validation Error!'), _("There is no central warehouse."))            
            if(origin_sale_shop_ids.__len__() > 1):#hay mas de una bodega central
                raise osv.except_osv(_('Validation Error!'), _("There should be only one central warehouse by company."))    
            cr.execute("select name,date from stock_picking where is_procurement=true and date>=current_date and date<current_date+1 and company_id=%s and state!='draft' and location_dest_id=%s", (warehouse.company_id.id, warehouse.lot_input_id.id))
            pickings = cr.fetchall()
            if(pickings):
                raise osv.except_osv(_('Validation Error!'), _("Today,only one picking can be created by provision."))
            if(stock_picking_object.search(cr,uid,[('state','=','auto'),('is_procurement','=',True),('company_id','=',warehouse.company_id.id),('location_dest_id','=',warehouse.lot_input_id.id)])):
                raise osv.except_osv(_('Validation Error!'), _("There pickings pending dispatch"))
            picking_id = pickings and (pickings[0])[0] or False
            search_stock_warehouse_orderpoint = stock_warehouse_orderpoint_object.search(cr, uid, [('warehouse_id', '=', warehouse.id), ('active', '=', True)])
            browse_origin_sale_shop = sale_shop_object.browse(cr, uid, origin_sale_shop_ids[0], context)
            if(search_stock_warehouse_orderpoint):##si hay reglas de stock minimo
                if(warehouse.id != browse_origin_sale_shop.warehouse_id.id):##si es diferente la tienda de origen de la de destino
                    vals_stock_picking = {"name":_("PROCUREMENT %s/%s %s" % (warehouse.name, warehouse.lot_input_id.name, date.today())),
                                      "digiter_id":uid,"shop_id":origin_sale_shop_ids[0],
                                      "shop_id_dest":(sale_shop_object.search(cr, uid, [('warehouse_id', '=', warehouse.id)]))[0], ##???
                                      "location_id":browse_origin_sale_shop.warehouse_id.lot_input_id.id,
                                      "location_dest_id":warehouse.lot_input_id.id,"address_id":warehouse.lot_input_id.address_id.id,
                                      "carrier_id":(self.pool.get("delivery.carrier").search(cr, uid, [('active', '=', True)]))[0],
                                      "date":date.today(),"is_procurement":True,"type":"internal","consigment":False,"internal_out":True,
                                      "company_id":warehouse.company_id.id,
                                      "partner_id":warehouse.company_id.partner_id.id,
                                      }      
                    picking_id = stock_picking_object.create(cr, uid, vals_stock_picking, context)                    
                for browse_stock_warehouse_orderpoint in stock_warehouse_orderpoint_object.browse(cr, uid, search_stock_warehouse_orderpoint, context):
                    browse_product_product = browse_stock_warehouse_orderpoint.product_id
                    if(browse_product_product.state != 'obsolete'):##si no es producto obsoleto
                        central_stock = stock_location_object._product_virtual_get(cr, uid, browse_origin_sale_shop.warehouse_id.lot_input_id.id, [browse_product_product.id], {'uom': browse_stock_warehouse_orderpoint.product_uom.id})[browse_product_product.id]
                        if(warehouse.id == browse_origin_sale_shop.warehouse_id.id):
                            if(central_stock < browse_stock_warehouse_orderpoint.product_min_qty):
                                self.process_produre_order(cr, uid, automatic, browse_product_product, warehouse, browse_stock_warehouse_orderpoint, context)
                        else:
                            location_stock = stock_location_object._product_virtual_get(cr, uid, warehouse.lot_input_id.id, [browse_product_product.id], {'uom': browse_stock_warehouse_orderpoint.product_uom.id})[browse_product_product.id]
                            if(location_stock < browse_stock_warehouse_orderpoint.product_min_qty):##si el stock de la ubicacion es menor al minimo permitido                                                  
                                value = browse_stock_warehouse_orderpoint.product_max_qty - location_stock##cantidad a reponer 
                                if(value > 0):##si la cantidad a reponer es mayor a 0
                                    if(value >= central_stock):##si la cantidad a reponer es mayor al stock de la bodega central
                                        self.process_produre_order(cr, uid, automatic, browse_product_product, warehouse, browse_stock_warehouse_orderpoint, context)
                                    else:##
                                        search_stock_warehouse_orderpoint_central = stock_warehouse_orderpoint_object.search(cr, uid, [('warehouse_id', '=', browse_origin_sale_shop.warehouse_id.id), ('active', '=', True), ('product_id', '=', browse_product_product.id)])
                                        make_stock_move = True
                                        ##verificar si se puede reponer ,verificar reglas de stock minimo de la tienda central
                                        if (search_stock_warehouse_orderpoint_central):
                                            browse_stock_warehouse_orderpoint_central = stock_warehouse_orderpoint_object.browse(cr, uid, search_stock_warehouse_orderpoint_central[0], context)
                                            if(browse_stock_warehouse_orderpoint_central):
                                                if((central_stock - value) <= browse_stock_warehouse_orderpoint_central.product_min_qty):##si el nuevo stock de la tienda central va a ser menor que el minimo requerido no hacer el movimiento
                                                    make_stock_move = False
                                        if(make_stock_move):
                                            vals_stock_move = {
                                                    'name': _("MOVE PICKING %s/%s %s-%s" % (warehouse.name, warehouse.lot_input_id.name, date.today(), browse_product_product.default_code)),
                                                    'location_id': browse_origin_sale_shop.warehouse_id.lot_input_id.id,
                                                    'product_id': browse_product_product.id,
                                                    "ubication_id":self._get_inmove_ubication_id(cr, uid, browse_origin_sale_shop.warehouse_id.lot_input_id, browse_product_product.id),
                                                    "location_dest_id":self._get_location_dest_id(cr, uid, stock_location_object, context),
                                                    'product_uom': browse_stock_warehouse_orderpoint.product_uom.id,
                                                    'product_uos': browse_stock_warehouse_orderpoint.product_uom.id,
                                                    'company_id': browse_stock_warehouse_orderpoint.company_id.id,
                                                    'auto_validate': True,'picking_id':picking_id,'date_expected': date.today(),'state': 'draft','product_qty': value,
                                                    'stock_warehouse_orderpoint_id':browse_stock_warehouse_orderpoint.id,
                                                }
                                            stock_move_ids.append(stock_move_object.create(cr, uid, vals_stock_move, context))
                                        else:
                                            self.process_produre_order(cr, uid, automatic, browse_product_product, warehouse, browse_stock_warehouse_orderpoint, context)
                if(not stock_move_ids and picking_id):##si nunca creo al menos una linea --elimina el stock_picking creado
                    stock_picking_object.unlink(cr, uid, [picking_id], context)
        return True
    
    def _get_location_dest_id(self, cr, uid, stock_location_object, context):
        search_stock_location = stock_location_object.search(cr, uid, [('usage', '=', 'transit')])
        if(search_stock_location):
            return search_stock_location[0]
        return False
    
    def _get_inmove_ubication_id(self, cr, uid, browse_location, product_id, context=None):
#        ubication_ids = self.pool.get('ubication').search(cr, uid, [('location_id','=',browse_location.id)])
        product_ubication_object = self.pool.get("product.ubication")
        search_product_ubication = product_ubication_object.search(cr, uid, [('product_id', '=', product_id), ('location_ubication_id', '=', browse_location.id)])
        if(search_product_ubication):
            return product_ubication_object.browse(cr, uid, search_product_ubication[0], context).ubication_id.id
        return False
    
    def make_procurement_order(self, cr, uid,browse_product_product, browse_stock_warehouse, context):
        ##crear procedimiento si stock virtual es mayor a 0
        product_product_object=self.pool.get("product.product")
        procurement_object=self.pool.get("procurement.order")
        wf_service = netsvc.LocalService("workflow")
        for read_product_product in product_product_object.read(cr, uid,[browse_product_product.id], ['virtual_available'], context=context):
            if read_product_product['virtual_available'] >= 0.0:
                continue
            if browse_product_product.supply_method == 'buy':
                location_id = browse_stock_warehouse.lot_input_id.id
            elif browse_product_product.supply_method == 'produce':
                location_id = browse_stock_warehouse.lot_stock_id.id
            else:
                continue
            procurement_id = procurement_object.create(cr, uid, self._prepare_automatic_op_procurement(cr, uid, browse_product_product, browse_stock_warehouse, location_id, context=context), context=context)
            ##si no tiene fabricante dejar en estado borrador
            if (browse_product_product.manufacturer):
                wf_service.trg_validate(uid, 'procurement.order', procurement_id, 'button_confirm', cr)
                wf_service.trg_validate(uid, 'procurement.order', procurement_id, 'button_check', cr)
    
    def procure_orderpoint_confirm(self, cr, uid,ids,context=None):
        ##crea la procurement.order y las aprueba
        ##adaptacion del _procure_orderpoint_confirm(self,cr, uid, automatic=False,use_new_cursor=False, context=None, user_id=False) 
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        location_obj = self.pool.get('stock.location')
        procurement_obj = self.pool.get('procurement.order')
        request_obj = self.pool.get('res.request')
        wf_service = netsvc.LocalService("workflow")
        report = []
        
        for op in orderpoint_obj.browse(cr, uid, ids, context=context):
            if op.procurement_id.state != 'exception':
                if op.procurement_id and op.procurement_id.purchase_id and op.procurement_id.purchase_id.state in ('draft', 'confirmed'):
                    continue
            prods = location_obj._product_virtual_get(cr, uid,op.location_id.id, [op.product_id.id],{'uom': op.product_uom.id})[op.product_id.id]

            if prods < op.product_min_qty:
                qty = max(op.product_min_qty, op.product_max_qty)-prods

                reste = qty % op.qty_multiple
                if reste > 0:
                    qty += op.qty_multiple - reste

                if qty <= 0:
                    continue
                if op.product_id.type not in ('consu'):
                    if op.procurement_draft_ids:
                    # Check draft procurement related to this order point
                        pro_ids = [x.id for x in op.procurement_draft_ids]
                        procure_datas = procurement_obj.read(
                            cr, uid, pro_ids, ['id', 'product_qty'], context=context)
                        to_generate = qty
                        for proc_data in procure_datas:
                            if to_generate >= proc_data['product_qty']:
                                wf_service.trg_validate(uid, 'procurement.order', proc_data['id'], 'button_confirm', cr)
                                procurement_obj.write(cr, uid, [proc_data['id']],  {'origin': op.name}, context=context)
                                to_generate -= proc_data['product_qty']
                            if not to_generate:
                                break
                        qty = to_generate

                if qty:
                    proc_id = procurement_obj.create(cr, uid,
                                                         self._prepare_orderpoint_procurement(cr, uid, op, qty, context=context),
                                                         context=context)
                    wf_service.trg_validate(uid, 'procurement.order', proc_id,'button_confirm', cr)
                    wf_service.trg_validate(uid, 'procurement.order', proc_id,'button_check', cr)
                    orderpoint_obj.write(cr, uid, [op.id],{'procurement_id': proc_id}, context=context)
        
        if uid and report:
            request_obj.create(cr, uid, {
                'name': 'Orderpoint report.',
                'act_from': uid,
                'act_to': uid,
                'body': '\n'.join(report)
            })
        return {}
    
    def process_produre_order(self,cr,uid,automatic,browse_product_product,warehouse,browse_stock_warehouse_orderpoint,context=None):
        ## make_procurement_order && procure_orderpoint_confirm
        if(automatic):
            self.make_procurement_order(cr, uid,browse_product_product, warehouse, context) 
        self.procure_orderpoint_confirm(cr, uid,[browse_stock_warehouse_orderpoint.id], context)
        
procurement_order()

class stock_warehouse_orderpoint(osv.osv):
    _inherit = "stock.warehouse.orderpoint"
    _columns = {
              "stock_move_ids":fields.one2many('stock.move', 'stock_warehouse_orderpoint_id', 'Stock Moves'),
              "manufacturer_id":fields.many2one("res.manufacturer","Manufacturer",help="The manufacturer is required if you want to make a replacement and none of the wineries in the company can supply it."),
            }
    
    def _check_unique_rules(self,cr,uid,ids):
        for browse_stock_warehouse_orderpoint in self.browse(cr, uid, ids):
            if(self.search(cr,uid,[('active','=',True),('company_id','=',browse_stock_warehouse_orderpoint.company_id.id),('product_id','=',browse_stock_warehouse_orderpoint.product_id.id),('location_id','=',browse_stock_warehouse_orderpoint.location_id.id),('id','!=',browse_stock_warehouse_orderpoint.id)])): return False
        return True
    
    _constraints = [(_check_unique_rules,'Can only be one active minimum stock rule by location !', ['name','product_id','location_id','active'])]

    def onchange_product_id(self,cr,uid,ids,product_id,context=None):
        if product_id:
            browse_product_product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'product_uom': browse_product_product.uom_id.id,
                     'manufacturer':browse_product_product.manufacturer and browse_product_product.manufacturer.id or False
                    }
            return {'value':value}
        return {}        
    
    def write(self,cr,uid, ids, vals, context=None):
        super(stock_warehouse_orderpoint,self).write(cr,uid,ids,vals,context)
        product_product_object=self.pool.get("product.product")
        for browse_stock_warehouse_orderpoint in self.browse(cr, uid, ids,context):
            if(browse_stock_warehouse_orderpoint.manufacturer_id):
                product_product_object.write(cr,uid,[browse_stock_warehouse_orderpoint.product_id.id],{"manufacturer":browse_stock_warehouse_orderpoint.manufacturer_id.id},context)
        return True
    
    def create(self,cr,uid, vals, context=None):
        new_id=super(stock_warehouse_orderpoint,self).create(cr,uid,vals,context)
        if(vals.get("manufacturer_id",False)):
            browse_stock_warehouse_orderpoint=self.browse(cr, uid,new_id,context)
            self.pool.get("product.product").write(cr,uid,[browse_stock_warehouse_orderpoint.product_id.id],{"manufacturer":browse_stock_warehouse_orderpoint.manufacturer_id.id},context)
        return new_id
    
stock_warehouse_orderpoint()

class stock_move(osv.osv):
    _inherit = "stock.move"
    _columns = {
              "stock_warehouse_orderpoint_id":fields.many2one('stock.warehouse.orderpoint', 'Minimum Stock Rules'),
              }

stock_move()
