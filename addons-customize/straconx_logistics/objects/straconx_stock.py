# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 - present STRACONX S.A.
#
#
##############################################################################

import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc


class stock_move(osv.osv):
    _inherit = 'stock.move'

    def _get_categ_id(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for obj in self.browse(cr, uid, ids):
                if obj.product_id.categ_id:
                    res[obj.id] = obj.product_id.categ_id.id
                else:
                    res[obj.id] = ''
            return res

    def _categ_id_search(self, cr, uid, obj, name, args, context):
            if not len(args):
                    return []
                    new_args = []
                    for argument in args:
                            operator = argument[1]
                            value = argument[2]
                            ids = self.pool.get('product.category').search(cr, uid, [('name', operator, value)], context=context)
                            new_args.append(('categ_id', 'in', ids))
                    if new_args:
                            new_args.append(('categ_id', '!=', False))
            return new_args

    def _get_ubication_id(self, cr, uid, ids, field_name, arg, context):
            res = {}
            for obj in self.browse(cr, uid, ids):
                if obj.ubication_id:
                    res[obj.id] = obj.ubication_id.id
                else:
                    res[obj.id] = ''
            return res

    def _ubication_id_search(self, cr, uid, obj, name, args, context):
            if not len(args):
                    return []
                    new_args = []
                    for argument in args:
                            operator = argument[1]
                            value = argument[2]
                            ids = self.pool.get('ubication').search(cr, uid, [('name', operator, value)], context=context)
                            new_args.append(('ubication_id', 'in', ids))
                    if new_args:
                            new_args.append(('ubication_id', '!=', False))
            return new_args

    def _cal_move_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for move in self.browse(cr, uid, ids, context=context):
            weight = weight_net = 0.00
            if move.product_id.weight > 0.00:
                converted_qty = move.product_qty

                if move.product_uom.id != move.product_id.uom_id.id:
                    converted_qty = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)
                weight = (converted_qty * move.product_id.weight)

                if move.product_id.weight_net > 0.00:
                    weight_net = (converted_qty * move.product_id.weight_net)
            res[move.id] = {'weight': weight,
                            'weight_net': weight_net}
        return res

    _columns = {'ref_product': fields.related('product_id', 'default_code', type='char', size=64,
                                              string='Reference Product', readonly=True,
                                              store={'stock.move': (lambda self, cr, uid, ids, c=None: ids,
                                                                    ['product_id', 'product_qty', 'product_uom'], 20)}),
                'move_id': fields.many2one('account.move', 'Reference Account Move'),
                'ubication_ids': fields.related('product_id', 'ubication_ids', type='one2many', relation='product.ubication',
                                                string='Ubications Items', readonly=True),
                'categ_id': fields.function(_get_categ_id, fnct_search=_categ_id_search, obj="product.category", method=True, type="many2one",
                                            string='Category', store=True),
                'ubication_id': fields.many2one('ubication', 'Ubication Case'),
                'weight': fields.function(_cal_move_weight, method=True, type='float', string='Weight',
                                          digits_compute=dp.get_precision('Stock Weight'),
                                          multi='_cal_move_weight',
                                          store={'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_qty', 'product_uom'],
                                                                20)}),
                'weight_net': fields.function(_cal_move_weight, method=True, type='float', string='Net weight',
                                              digits_compute=dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                                              store={'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id',
                                                                                                             'product_qty',
                                                                                                             'product_uom'], 20)}),
                'is_backorder': fields.boolean('Is Backorder?'),
                'qty_inv': fields.float('Inventory Move Quantity', digits_compute=dp.get_precision('Product UoM'),
                                        states={'done': [('readonly', True)]}),
                'active': fields.boolean('Activo'),
                'credit_note': fields.boolean('N/C'),
                'price_unit': fields.float('Unit Price', digits_compute=dp.get_precision('Purchase Price'),
                                           help="Technical field used to record the product cost set by the user during a picking confirmation"
                                           " (when average price costing method is used)"),
                }

    _defaults = {'ubication_id': lambda *a: None,
                 'is_backorder': lambda *a: False,
                 'active': True
                 }
    _order = 'ubication_id desc,ref_product asc ,name asc'

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, address_id=False, qty=0, type=False, context=None):
        """ On change of product id, if finds UoM, UoS, quantity and UoS quantity.
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param address_id: Address id of partner
        @return: Dictionary of values
        """
        if not prod_id:
            return {}
        lang = False
        if context is None:
            context={}
        values={}
        if address_id:
            addr_rec = self.pool.get('res.partner.address').browse(cr, uid, address_id)
            if addr_rec:
                lang = addr_rec.partner_id and addr_rec.partner_id.lang or False
        ctx = {'lang': lang}
        if qty<=0:
            qty=1
        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=ctx)
        transfer = context.get('transfer',False)
        if transfer:
            if product.state in ('draft','quotation') and product.type in ('product','consu'):
                warning = {'title': _('Aviso!'),'message': _(('¡Solo se puede transferir productos cuya importación haya sido liquidada o se han receptada la compra.!'))}
                return {'value': {'product_id': False}, 'warning':warning}
        uos_id  = product.uos_id and product.uos_id.id or False
        result = {
            'ref_product': product.default_code,
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_qty': qty,
            'product_uos_qty' : self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty']
        }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        else:
            if context.get('shop_id',False):
                loc_id= self.pool.get('sale.shop').browse(cr, uid, context['shop_id']).warehouse_id.lot_stock_id.id
                result['location_id'] = loc_id
        if type == 'in':            
            loc_id = self.pool.get('stock.location').search(cr,uid,[('usage','=','supplier')],limit=1)            
            loc_dest_id= self.pool.get('sale.shop').browse(cr, uid, context['shop_id']).warehouse_id.lot_input_id.id
            ubication=None
            if loc_dest_id:
                ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',prod_id),('location_ubication_id','=',loc_dest_id)])
                if ubication_ids:
                    ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
            result['location_dest_id'] = loc_dest_id             
            result['location_id'] = loc_id
            result['ubication_id']= ubication
        else:
            if loc_dest_id:
                result['location_dest_id'] = loc_dest_id
            else:
                if context.get('internal_out',False):
                    location_dest_ids=self.pool.get('stock.location').search(cr, uid, [('usage','=','transit')], limit=1)
                    result['location_dest_id'] = location_dest_ids and location_dest_ids[0] or None
            ubication=None
            if context.get('internal_out',False):
                ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',prod_id),('location_ubication_id','=',loc_id)])
                if ubication_ids:
                    ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
            elif context.get('internal_in',False):
                location=self.pool.get('stock.location').browse(cr, uid, result['location_dest_id'], context)
                ubication= location.location_ids and location.location_ids[0].id or None
            elif context.get('default_consigment',False):
                location=self.pool.get('stock.location').browse(cr, uid, result['location_dest_id'], context)
                ubication= location.location_ids and location.location_ids[0].id or None
        result['ubication_id']= ubication
        values={'value': result}
        return values
    
    
    def onchange_ubication_id(self, cr, uid, ids, product=None, ubication=None, context=None):
        values={}
        if ubication:
            if product:
                pubicacion_ids = self.pool.get('product.ubication').search(cr, uid,[('ubication_id','=',ubication),('product_id','=',product)] )
                if pubicacion_ids:
                    values['location_id'] = self.pool.get('ubication').browse(cr, uid, ubication, context).location_id.id
                else:
                    values['location_id']=None
        else:
            location_id = context.get('location_id',False)
            ubicacion_ids = self.pool.get('ubication').search(cr, uid,[('location_id','=',location_id)] )
            if ubicacion_ids:
                values['ubication_id'] = ubicacion_ids[0]
#                 pubicacion_ids = self.pool.get('product.ubication').search(cr, uid,[('ubication_id','in',ubicacion_ids),('product_id','=',product)] )
#                 if pubicacion_ids:
#                     values['ubication_id'] = self.pool.get('product.ubication').browse(cr, uid, pubicacion_ids[0], context).ubication_id.id
            else:
                values['ubication_id']=None
        return {'value': values}
    
    def onchange_locations(self, cr, uid, ids, shop=None, partner=None, type='internal', loc_or=None, loc_dest=None, context=None):
        if context is None:
            context = {}
        values={}
        domain={}
        if not partner:
            raise osv.except_osv(_('Warning!'), _('You must first choose Partner Consigment!'))
        if not shop:
            raise osv.except_osv(_('Warning!'), _('You must first choose a Shop!'))
        if not (loc_or and loc_dest):
            if type=='internal':
                partner=self.pool.get('res.partner').browse(cr, uid, partner, context)
                shop=self.pool.get('sale.shop').browse(cr, uid, shop, context)
                if partner.is_consignement:
                    if not partner.property_stock_consignement:
                        raise osv.except_osv(_('Warning!'), _("The Partner doesn't have a consignement location defined!"))
                    values['location_dest_id']= partner.property_stock_consignement.id
                    domain['location_dest_id']=[('id','=',partner.property_stock_consignement.id)]
                if not shop.warehouse_id.lot_stock_id:
                    raise osv.except_osv(_('Warning!'), _("The shop doesn't have a stock location defined!"))
                values['location_id']= shop.warehouse_id.lot_stock_id.id
                domain['location_id']=[('id','=',shop.warehouse_id.lot_stock_id.id)]
        return {'value':values, 'domain':domain}
    
    def onchange_locations_internal(self, cr, uid, ids, product_id=False, type='internal', loc_or=False, loc_dest=False, internal_out=True, internal_in=False, context={}):
        if context is None:
            context = {}
        values={}
        domain={}
        if type=='internal':
            if not (loc_or and loc_dest):
                raise osv.except_osv(_('Warning!'), _("The location origin or destiny is not defined in the picking!"))
            location_dest_ids=self.pool.get('stock.location').search(cr, uid, [('usage','=','transit')], limit=1)
#            if context.get('internal_out',False):
            if internal_out==True: 
                values['location_id']= loc_or
                values['location_dest_id'] = location_dest_ids and location_dest_ids[0] or None
                domain['location_id']=[('id','=',loc_or)]
                if product_id:
                    ubication=None
                    ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',product_id),('location_ubication_id','=',loc_or)])
                    if ubication_ids:
                        ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
                    values['ubication_id']= ubication
            elif internal_in==True:
                values['location_dest_id'] = loc_dest
                domain['location_dest_id']=[('id','=',loc_dest)]
                values['location_id']= location_dest_ids and location_dest_ids[0] or None
                location=self.pool.get('stock.location').browse(cr, uid, loc_dest, context)
                values['ubication_id']= location.location_ids and location.location_ids[0].id or None 
        return {'value':values, 'domain':domain}

    def action_drafted(self, cr, uid, ids, context=None):
        """ Draft the moves and if all moves are drafted it draft the picking.
        @return: True
        """
        if not len(ids):
            return True
        if context is None:
            context = {}
        pickings = {}
        picking_obj = self.pool.get('stock.picking')
        self.write(cr, uid, ids, {'state': 'draft'})
        for move in self.browse(cr, uid, ids, context=context):
            if move.move_dest_id:
                move_dest_id = self.pool.get('stock.move').browse(cr,uid,move.move_dest_id.id)
                if not move_dest_id:
                    self.pool.get('stock.move').write(cr,uid,move.id,{'move_dest_id':False})                    
                elif move.move_dest_id.state == 'done':
                    if not move.move_dest_id.picking_id.consigment:
                        raise osv.except_osv(_('Warning'), _('El picking interno %s se encuentra en estado Realizado. Por favor, cancelar este picking para continuar.')%(move.move_dest_id.picking_id.name))
                    if not pickings.get(move.move_dest_id.picking_id.id, False):
                        pickings[move.move_dest_id.picking_id.id] = True
            if move.move_id:
                self.pool.get('account.move').button_cancel(cr, uid, [move.move_id.id], context)
                self.pool.get('account.move').unlink(cr, uid, [move.move_id.id], context)
            if not move.ubication_id:
                if move.picking_id:
                    ubication_id = self.pool.get('product.ubication').search(cr, uid, [('shop_ubication_id','=',move.picking_id.shop_id.shop_ubication_id.id),('product_id','=',move.product_id.id)])
                elif move.location_dest_id.id:
                    ubication_id = self.pool.get('product.ubication').search(cr, uid, [('location_ubication_id','=',move.location_dest_id.id),('product_id','=',move.product_id.id)])
                else:
                    raise osv.except_osv(_('Error!'), _(("Debe especificar una ubicación de destino para el producto %s - %s de la categoría %s")%(move.product_id.default_code, move.product_id.name, move.categ_id.name)))            
            else:
                ubication_ids = self.pool.get('product.ubication').search(cr,uid,[('ubication_id','=',move.ubication_id.id),('product_id','=',move.product_id.id)])
                if ubication_ids:
                    ubica_id = self.pool.get('product.ubication').browse(cr,uid,ubication_ids[0])
                    new_qty = 0.00
                    if ubica_id.qty:
                        old_qty = ubica_id.qty
                    else:
                        old_qty = 0.00
                    if move.picking_id.type =='in':
                        new_qty = old_qty - move.product_qty
                    elif move.picking_id.type =='out':
                        new_qty = old_qty + move.product_qty
                    elif move.picking_id.type =='internal' and move.picking_id.internal_out:
                        new_qty = old_qty + move.product_qty
                    elif move.picking_id.type =='internal' and move.picking_id.internal_in:
                        new_qty = old_qty - move.product_qty
                    date = time.strftime('%Y-%m-%d %H:%M:%S')
                    cr.execute("""update product_ubication set qty=%s, write_uid=%s, write_date=%s where id=%s """,(new_qty,uid,date,ubica_id.id))
        for pick in picking_obj.browse(cr, uid, pickings.keys()):
            picking_obj.action_drafted(cr, uid, [pick.id], context)
            picking_obj.unlink(cr, uid, [pick.id], context)
        self.write(cr, uid, ids, {'move_dest_id': False})
        return True

    def lost_unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        count=0
        picking=[]
        for move in self.browse(cr, uid, ids, context=context):
            if move.state != 'draft' and not ctx.get('call_unlink',False):
                raise osv.except_osv(_('UserError'),
                        _('You can only delete draft moves.'))
            if move.picking_id.move_lines:
                for move_act in move.picking_id.move_lines:
                    if move_act.id != move.id:
                        count+=1
            if not count:
                picking.append(move.picking_id.id)
        res=super(stock_move, self).unlink(cr, uid, ids, context=ctx)
        if picking:
            self.pool.get('stock.picking').action_cancel(cr, uid, picking, context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                if move.state != 'draft':
                    raise osv.except_osv(_('UserError'),
                        _('You can cancel related picking or inventory.'))
            if move.ubication_id:
                ub_ids=self.pool.get('product.ubication').search(cr, uid, [('ubication_id','=',move.ubication_id.id),('product_id','=',move.product_id.id)])
                self.pool.get('product.ubication').write(cr, uid, ub_ids, {}, context)
        if ids:
            cr.execute("""update stock_move set  write_date =now(), state='cancel', active='False' where id in %s """,(tuple(ids),))
        return True
#        return super(stock_move, self).unlink(cr, uid, ids, context=context)

    
    def action_cancel(self, cr, uid, ids, context):
        res= super(stock_move, self).action_cancel(cr, uid, ids, context)
        for move in self.browse(cr, uid, ids, context):
            if move.ubication_id:
                ub_ids=self.pool.get('product.ubication').search(cr, uid, [('ubication_id','=',move.ubication_id.id),('product_id','=',move.product_id.id)])
                self.pool.get('product.ubication').write(cr, uid, ub_ids, {}, context)
        return res


    def action_scrap(self, cr, uid, ids, quantity, location_id, note=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        if quantity <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide a positive quantity to scrap!'))
        res = []
        product_obj = self.pool.get('product.product')
        lost_sales_obj = self.pool.get('lost.sales')
        for move in self.browse(cr, uid, ids, context=context):
            if quantity > move.product_qty:
                raise osv.except_osv(_('Warning!'), _('The number of lost sales can not be more the request of the move!'))
            lost_sales_obj.create(cr, uid, {
                                            'product_id':move.product_id.id,
                                            'qty': quantity,
                                            'uom_id': move.product_uom.id,
                                            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                                            'picking_id': move.picking_id.id,
                                            'partner_id': move.picking_id.partner_id.id,
                                            'shop_id': move.picking_id.shop_id.id,
                                            'salesman_id': move.picking_id.salesman_id.id,
                                            'ref_sale': move.picking_id.origin,
                                            'note': note,
                                            })
            rest_qty = move.product_qty - quantity
            self.write(cr, uid, [move.id], {'product_qty': rest_qty} ,context)
            if rest_qty == 0:
                self.write(cr, uid, [move.id], {'state':'draft'} ,context)
                self.lost_unlink(cr, uid, [move.id,], context)
#                    self.action_cancel(cr, uid, [move.id,], context)
        return True

    def _get_reference_accounting_values_for_valuation(self, cr, uid, move, context=None):
        """
        Return the reference amount and reference currency representing the inventory valuation for this move.
        These reference values should possibly be converted before being posted in Journals to adapt to the primary
        and secondary currencies of the relevant accounts.
        """
        product_uom_obj = self.pool.get('product.uom')

        # by default the reference currency is that of the move's company
        reference_currency_id = move.company_id.currency_id.id

        default_uom = move.product_id.uom_id.id
        qty = product_uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, default_uom)

        # if product is set to average price and a specific value was entered in the picking wizard,
        # we use it
        if move.product_id.cost_method == 'average' and move.product_id:
            reference_amount = qty * move.product_id.standard_price
            # currency_ctx = dict(context, currency_id = move.company_id.currency_id.id)
            # reference_currency_id = move.product_id.price_get('standard_price', context=currency_ctx)[move.product_id.id]

        # Otherwise we default to the company's valuation price type, considering that the values of the
        # valuation field are expressed in the default currency of the move's company.
        else:
            if context is None:
                context = {}
            currency_ctx = dict(context, currency_id=move.company_id.currency_id.id)
            amount_unit = move.product_id.price_get('standard_price', context=currency_ctx)[move.product_id.id]
            reference_amount = amount_unit * qty

        return reference_amount, reference_currency_id

    def _create_product_valuation_moves(self, cr, uid, move_ids, context=None):
        """
        Generate the appropriate accounting moves if the product being moves is subject
        to real_time valuation tracking, and the source or destination location is
        a transit location or is outside of the company.
        """
        move_id = None
        move_obj = self.pool.get('account.move')

        move_base = self.browse(cr, uid, move_ids[0])
        period = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', move_base.date),
                                                                  ('date_stop', '>=', move_base.date), ('company_id', '=', move_base.company_id.id)])
        details = 'MOVIMIENTO POR AJUSTE DE INVENTARIO'
        if not period:
            raise osv.except_osv(_('Aviso!'), _('¡No existe períodos contables definidos para la fecha seleccionada!'))
        else:
            period = period[0]

        if move_base.picking_id:
            shop_id = move_base.picking_id.shop_id and move_base.picking_id.shop_id.id or None
            if move_base.picking_id.type == 'in' and move_base.picking_id.credit_note:
                details = 'INGRESO DE INVENTARIO POR NOTA DE CRÉDITO'
            elif move_base.picking_id.type == 'in' and move_base.picking_id.international:
                details = 'INGRESO DE INVENTARIO POR LIQUIDACIÓN DE IMPORTACIÓN'
            elif move_base.picking_id.type == 'in' and not (move_base.picking_id.international or move_base.picking_id.credit_note):
                details = 'INGRESO DE INVENTARIO POR COMPRA DE MERCADERÍA'
            elif move_base.picking_id.type == 'internal' and move_base.picking_id.internal_out:
                details = 'MOVIMIENTO DE INVENTARIO POR ENVIO DE TRANSFERENCIA'
            elif move_base.picking_id.type == 'internal' and move_base.picking_id.internal_in:
                details = 'MOVIMIENTO DE INVENTARIO POR RECEPCION DE TRANSFERENCIA'
            elif move_base.picking_id.type == 'internal' and move_base.picking_id.consigment:
                details = 'MOVIMIENTO DE INVENTARIO POR CONSIGNACION DE PRODUCTOS'
            else:
                details = 'MOVIMIENTO DE INVENTARIO POR VENTA DE PRODUCTOS'

        else:
            shop_id = self.pool.get('sale.shop').search(cr, uid, [('warehouse_id.lot_input_id', 'in', (move_base.location_dest_id.id,
                                                                                                       move_base.location_id.id))])
            if shop_id:
                shop_id = shop_id and shop_id[0] or None
            elif not shop_id:
                loc_search = move_base.location_id.address_id.id
                if not loc_search:
                    loc_search = move_base.location_dest_id.address_id.id
                if loc_search:
                    shop_id = self.pool.get('sale.shop').search(cr, uid, [('partner_address_id', '=', loc_search)])
                    if shop_id:
                        shop_id = shop_id[0]
                    else:
                        raise osv.except_osv(_('Error!'), _(("Necesita especificar una tienda o centro de costo para el movimiento de inventario")))
                else:
                    active_model = context.get('active_model', False)
                    active_id = context.get('active_id', False)
                    if active_model:
                        try:
                            shop_id = self.pool.get(active_model).browse(cr, uid, active_id).shop_id.id
                        except:
                            shop_id = self.pool.get('sale.shop').browse(cr, uid, 1).id
            else:
                raise osv.except_osv(_('Error!'), _(("Necesita especificar una tienda o centro de costo para el movimiento de inventario")))

        if move_base.picking_id.stock_journal_id:
            journal_id = move_base.picking_id.stock_journal_id.id
        elif not move_base.picking_id.stock_journal_id:
            journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'stock')])[0]
        else:
            raise osv.except_osv(_('Error!'), _(("Necesita definir un diario tipo Inventario para continuar")))
        if move_base.picking_id.invoice_ids and move_base.picking_id.invoice_ids[0].state not in ('cancel'):
            name = move_base.picking_id.invoice_ids[0].invoice_number or move_base.picking_id.invoice_ids[0].invoice_number_out \
                or move_base.picking_id.invoice_ids[0].invoice_number_in
            if not name:
                name = 'N/C ' + move_base.picking_id.partner_id.name
        elif move_base.picking_id.name:
            name = move_base.picking_id.name
        else:
            name = move_base.name

        move_id = move_obj.create(cr, uid,
                                  {'name': name,
                                   'journal_id': journal_id,
                                   'details': details,
                                   'date': move_base.date,
                                   'partner_id': move_base.picking_id and move_base.picking_id.partner_id.id or False,
                                   'address_id': move_base.picking_id and move_base.picking_id.address_id.id or False,
                                   'shop_id': move_base.picking_id and move_base.picking_id.shop_id.id or shop_id,
                                   'company_id': move_base.picking_id and move_base.picking_id.company_id.id or move_base.company_id.id,
                                   'period_id': period,
                                   'ref': name})

        for move in move_ids:
            move = self.browse(cr, uid, move)
            if move.product_id.valuation == 'real_time' and move.product_qty > 0:
                if context is None:
                    context = {}
                src_company_ctx = dict(context, force_company=move.location_id.company_id.id)
                dest_company_ctx = dict(context, force_company=move.location_dest_id.company_id.id)
                account_moves = []
                reference_amount, reference_currency_id = self._get_reference_accounting_values_for_valuation(cr, uid, move, src_company_ctx)
                if move.location_id.company_id and (move.location_id.usage == 'internal' and move.location_dest_id.usage not in ('internal', 'inventory') 
                                                    or move.location_id.company_id != move.location_dest_id.company_id):
                    if move.location_dest_id.usage == 'production':
                        journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                        if move.picking_id.shop_id and move.picking_id.shop_id_dest:
                            context.update({'shop_id': move.picking_id.shop_id.id, 'shop_id_dest': move.picking_id.shop_id_dest.id})
                            account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_variation, acc_dest,  reference_amount,
                                                                             reference_currency_id, context)
                    elif move.location_dest_id.usage == 'customer':
                        journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                        account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_dest, acc_variation, reference_amount,
                                                                         reference_currency_id, context)
                    elif move.location_dest_id.usage != 'transit' and not move.picking_id.shop_id_dest:
                        journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                        if move.picking_id.shop_id and move.picking_id.shop_id_dest:
                            context.update({'shop_id': move.picking_id.shop_id.id, 'shop_id_dest': move.picking_id.shop_id_dest.id})
                            account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_dest, acc_dest, reference_amount,
                                                                             reference_currency_id, context)

                if move.location_id.company_id and (move.location_id.usage == 'transit' and move.location_dest_id.usage == 'production'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_variation, acc_dest, reference_amount,
                                                                     reference_currency_id, context)
                    
                elif move.location_id.company_id and (move.location_id.usage == 'inventory' and move.location_dest_id.usage == 'internal'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    context.update({'move': move.id})
                    review_move = context.get('review_move', False)
                    if review_move:
                        acc_variation = context.get('account_id', False)
                        acc_variation = acc_variation.id
                    account_moves = self._create_account_moves_lines(cr, uid, False, move_id, acc_dest, acc_variation,  reference_amount,
                                                                     reference_currency_id, context)
                    
                elif move.location_id.company_id and (move.location_id.usage == 'production' and move.location_dest_id.usage == 'internal'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_dest, acc_variation, reference_amount,
                                                                     reference_currency_id, context)

                elif move.location_id.company_id and (move.location_id.usage == 'internal' and move.location_dest_id.usage == 'production'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    account_moves = self._create_account_moves_lines(cr, uid, move, move_id,  acc_variation, acc_dest, reference_amount,
                                                                     reference_currency_id, context)

                elif move.location_id.company_id and (move.location_id.usage == 'internal' and move.location_dest_id.usage == 'transit'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    context.update({'shop_id': move.picking_id.shop_id.id, 'shop_id_dest': move.picking_id.shop_id_dest.id})
                    account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_src, acc_dest, reference_amount,
                                                                     reference_currency_id, context)

                elif move.location_id.company_id and (move.location_id.usage == 'transit' and move.location_dest_id.usage == 'internal'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    context.update({'shop_id': move.picking_id.shop_id.id, 'shop_id_dest': move.picking_id.shop_id_dest.id})
                    account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_src, acc_dest, reference_amount,
                                                                     reference_currency_id, context)

                elif move.location_id.company_id and (move.location_id.usage == 'internal' and move.location_dest_id.usage == 'inventory'):
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    context.update({'move': move.id})
                    review_move = context.get('review_move', False)
                    if review_move:
                        acc_variation = context.get('account_id', False)
                        acc_variation = acc_variation.id
                    account_moves = self._create_account_moves_lines(cr, uid, False, move_id, acc_variation, acc_dest, reference_amount,
                                                                     reference_currency_id, context)

                elif move.picking_id.international:
                    journal_id, acc_src, acc_dest, acc_variation = self._get_accounting_data_for_valuation(cr, uid, move, src_company_ctx)
                    context.update({'move': move.id})
                    account_moves = self._create_account_moves_lines(cr, uid, move, move_id, acc_variation, acc_dest, reference_amount,
                                                                     reference_currency_id, context)
            else:
                account_moves = []
        return account_moves

    def _create_account_moves_lines(self, cr, uid, move, move_id, dest_account_id, src_account_id, reference_amount,
                                    reference_currency_id, context=None):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given stock move.
        """
        # prepare default values considering that the destination accounts have the reference_currency_id as their main currency
        move_obj = self.pool.get('stock.move')
        account_account_obj = self.pool.get('account.account')
        move_account_obj = self.pool.get('account.move')
        account_move_obj = self.pool.get('account.move.line')
        pick_obj = self.pool.get('stock.picking')
        if move and move.picking_id:
            moves = move_obj.search(cr, uid, [('picking_id', '=', move.picking_id.id)])
            picking_id = pick_obj.browse(cr, uid, move.picking_id.id)
            partner_id = picking_id.partner_id.id or (picking_id.address_id and picking_id.address_id.partner_id and
                                                      picking_id.address_id.partner_id.id)
            if moves:
                moves_list = move_obj.browse(cr, uid, moves)
        else:
            moves = context.get('move', False)
            if moves:
                moves_list = move_obj.browse(cr, uid, [moves])
            else:
                moves_list = move_obj.browse(cr, uid, [move_id])
            if moves_list:
                picking_id = False
                partner_id = account_account_obj.browse(cr, uid, dest_account_id).company_id.partner_id.id

        id_move = move_account_obj.browse(cr, uid, move_id)

        if picking_id and picking_id.type == 'out':
            debit_account = src_account_id
            credit_account = dest_account_id
        else:
            debit_account = dest_account_id
            credit_account = src_account_id
        if debit_account == credit_account:
            shop_id = context.get('shop_id')
            shop_id_dest = context.get('shop_id_dest')
        else:
            if picking_id:
                shop_id = picking_id.shop_id.id
                shop_id_dest = picking_id.shop_id_dest.id
            else:
                shop_id = context.get('shop_id')
                shop_id_dest = context.get('shop_id')
        if not shop_id_dest or not shop_id:
            shop_id = id_move.shop_id.id
            shop_id_dest = id_move.shop_id.id

        if not shop_id_dest or not shop_id:
            raise osv.except_osv(_('Error!'), _(("Necesita especificar una tienda o centro de costo para el movimiento de inventario")))

#        for move in moves_list:
        if move:
            move = self.browse(cr, uid, move.id)
        if context.get('move', False):
            moves_id = context.get('move', False)
            move = self.browse(cr, uid, moves_id)
        debit_line_vals = {'journal_id': id_move.journal_id.id,
                           'currency_id': reference_currency_id,
                           'company_id': picking_id and picking_id.company_id.id or move.company_id.id,
                           'state': 'valid',
                           'debit': reference_amount,
                           'credit': 0.00,
                           'account_id': debit_account,
                           'period_id': id_move.period_id.id,
                           'date': id_move.date or time.strftime('%Y-%m-%d'),
                           'move_id': move_id,
                           'product_id': move.product_id.id,
                           'quantity': move.product_qty,
                           'reference': move.name,
                           'name': move.product_id.default_code + ' - ' + move.product_id.name,
                           'partner_id': partner_id,
                           'shop_id': shop_id,
                           'amount_currency': reference_amount,
                           'active': True
                           }

        credit_line_vals = {'journal_id': id_move.journal_id.id,
                            'currency_id': reference_currency_id,
                            'company_id': move.company_id.id or picking_id.company_id.id,
                            'state': 'valid',
                            'debit': 0.00,
                            'credit': reference_amount,
                            'account_id': credit_account,
                            'period_id': id_move.period_id.id,
                            'date': id_move.date or time.strftime('%Y-%m-%d'),
                            'move_id': move_id,
                            'product_id': move.product_id.id,
                            'quantity': move.product_qty,
                            'reference': move.name,
                            'name': move.product_id.default_code + ' - ' + move.product_id.name,
                            'partner_id': partner_id,
                            'shop_id': shop_id_dest,
                            'amount_currency': reference_amount,
                            'active': True
                            }

        account_obj = self.pool.get('account.account')
        src_acct, dest_acct = account_obj.browse(cr, uid, [src_account_id, dest_account_id], context=context)
        src_main_currency_id = src_acct.company_id.currency_id.id
        dest_main_currency_id = dest_acct.company_id.currency_id.id
        cur_obj = self.pool.get('res.currency')
        if reference_currency_id != src_main_currency_id:
            credit_line_vals['credit'] = cur_obj.compute(cr, uid, reference_currency_id, src_main_currency_id, reference_amount, context=context)
            if (not src_acct.currency_id) or src_acct.currency_id.id == reference_currency_id:
                if move.invoice_line_id:
                    credit_line_vals.update(currency_id=reference_currency_id, amount_currency=reference_amount)
                else:
                    credit_line_vals.update(currency_id=reference_currency_id, amount_currency=reference_amount)
        if reference_currency_id != dest_main_currency_id:
            # fix debit line:
            debit_line_vals['debit'] = cur_obj.compute(cr, uid, reference_currency_id, dest_main_currency_id, reference_amount, context=context)
            if (not dest_acct.currency_id) or dest_acct.currency_id.id == reference_currency_id:
                debit_line_vals.update(currency_id=reference_currency_id, amount_currency=reference_amount)
        if debit_line_vals:
            if debit_line_vals.get('debit',0.00)<0.00:
                debit = debit_line_vals.get('debit',0.00)
                if debit_line_vals.get('product_id',False):
                    pr_id = debit_line_vals.get('product_id',False)
                    product_id = self.pool.get('product.product').browse(cr,uid,pr_id)                        
                    raise osv.except_osv(_('Error!'), _(('El movimiento del producto %s - %s tiene un valor negativo %s, por favor revisar su transacción. En caso de ser un producto almacenable, revisar el costo del mismo!')%(product_id.default_code,product_id.name,debit)))
                else:
                    reference = debit_line_vals.get('reference',None)
                    raise osv.except_osv(_('Error!'), _(('El movimiento con referencia %s tiene un valor negativo %s, por favor revisar su transacción. En caso de ser un producto almacenable, revisar el costo del mismo!')%(reference,debit)))

            
            sql_debit = """INSERT INTO account_move_line(
            create_uid, create_date,   
            journal_id, currency_id,  
            partner_id, credit, 
            company_id, state, 
            debit,account_id, 
            period_id, date,  
            move_id, product_id,  
            quantity,  
            reference, ref,  
            name, shop_id,
            amount_currency,active) values(%s,'%s',%s,%s,%s,%s,%s,'%s',%s,%s,%s,'%s',%s,%s,%s,'%s','%s','%s',%s,%s,True)""" %(uid,time.strftime('%Y-%m-%d %H:%M:%S'),
            debit_line_vals.get('journal_id',False),debit_line_vals.get('currency_id',False),
            debit_line_vals.get('partner_id',False),debit_line_vals.get('credit',0.00),
            debit_line_vals.get('company_id',False),debit_line_vals.get('state','valid'),
            debit_line_vals.get('debit',0.00), debit_line_vals.get('account_id',False),
            debit_line_vals.get('period_id',False),debit_line_vals.get('date',False),
            debit_line_vals.get('move_id',False),debit_line_vals.get('product_id',False),
            debit_line_vals.get('quantity',False),
            debit_line_vals.get('reference',None),debit_line_vals.get('reference',None),
            debit_line_vals.get('name',None),debit_line_vals.get('shop_id',False),
            debit_line_vals.get('amount_currency',0.00))
            cr.execute(sql_debit)

        if credit_line_vals:
            if credit_line_vals.get('debit',0.00)<0.00:
                debit = credit_line_vals.get('debit',0.00)
                if credit_line_vals.get('product_id',False):
                    pr_id = credit_line_vals.get('product_id',False)
                    product_id = self.pool.get('product.product').browse(cr,uid,pr_id)                        
                    raise osv.except_osv(_('Error!'), _(('El movimiento del producto %s - %s tiene un valor negativo %s, por favor revisar su transacción. En caso de ser un producto almacenable, revisar el costo del mismo!')%(product_id.default_code,product_id.name,debit)))
                else:
                    reference = credit_line_vals.get('reference',None)
                    raise osv.except_osv(_('Error!'), _(('El movimiento con referencia %s tiene un valor negativo %s, por favor revisar su transacción. En caso de ser un producto almacenable, revisar el costo del mismo!')%(reference,debit)))

            sql_credit = """INSERT INTO account_move_line(
            create_uid, create_date,   
            journal_id, currency_id,  
            partner_id, credit, 
            company_id, state, 
            debit,account_id, 
            period_id, date,  
            move_id, product_id,  
            quantity,  
            reference, ref,  
            name, shop_id,
            amount_currency,active) values(%s,'%s',%s,%s,%s,%s,%s,'%s',%s,%s,%s,'%s',%s,%s,%s,'%s','%s','%s',%s,%s,True)""" %(uid,time.strftime('%Y-%m-%d %H:%M:%S'),
            credit_line_vals.get('journal_id',False),credit_line_vals.get('currency_id',False),
            credit_line_vals.get('partner_id',False),credit_line_vals.get('credit',0.00),
            credit_line_vals.get('company_id',False),credit_line_vals.get('state','valid'),
            credit_line_vals.get('debit',0.00), credit_line_vals.get('account_id',False),
            credit_line_vals.get('period_id',False),credit_line_vals.get('date',False),
            credit_line_vals.get('move_id',False),credit_line_vals.get('product_id',False),
            credit_line_vals.get('quantity',False),
            credit_line_vals.get('reference',None),credit_line_vals.get('reference',None),
            credit_line_vals.get('name',None),credit_line_vals.get('shop_id',False),
            credit_line_vals.get('amount_currency',0.00))
            cr.execute(sql_credit)
#             account_move_obj.create(cr,uid,debit_line_vals)
#             account_move_obj.create(cr,uid,credit_line_vals)
        return move_id


    #@profile
    def action_done(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        @return:
        """
        partial_datas = ''
        picking_ids = []
        move_ids = []
        ub_ids = ''
        account_obj = self.pool.get('account.move')
        partial_obj = self.pool.get('stock.partial.picking')
        wf_service = netsvc.LocalService("workflow")
        partial_id = []
        if partial_id:
            partial_id = [partial_id[-1]]
            partial_datas = partial_obj.read(cr, uid, partial_id, context=context)[0]
        if context is None:
            context = {}
        todo = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ('draft'):
                todo.append(move.id)
        if todo:
            self.action_confirm(cr, uid, todo, context=context)
            todo = []
        moves_id = None
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done', 'confirmed', 'assigned', 'waiting']:
                move_ids.append(move.id)
            if not move.ubication_id:
                if move.picking_id:
                    ubication_id = self.pool.get('product.ubication').search(cr, uid, [('shop_ubication_id','=',move.picking_id.shop_id.shop_ubication_id.id),('product_id','=',move.product_id.id)])
                elif move.location_dest_id.id:
                    ubication_id = self.pool.get('product.ubication').search(cr, uid, [('location_ubication_id','=',move.location_dest_id.id),('product_id','=',move.product_id.id)])
                else:
                    raise osv.except_osv(_('Error!'), _(("Debe especificar una ubicación de destino para el producto %s - %s de la categoría %s")%(move.product_id.default_code, move.product_id.name, move.categ_id.name)))            
            elif move.ubication_id and move.state not in ['done','cancel']:
                if (move.picking_id and move.picking_id.international) or move.picking_id.type=='in':
                    location_ubication_id = move.location_dest_id.id
                else:
                    location_ubication_id = move.location_id.id                    
                ubication_ids = self.pool.get('product.ubication').search(cr,uid,[('ubication_id','=',move.ubication_id.id),('product_id','=',move.product_id.id),('location_ubication_id','=',location_ubication_id)])
                if ubication_ids:
                    ubica_id = self.pool.get('product.ubication').browse(cr,uid,ubication_ids[0])
                    new_qty = 0.00
                    if ubica_id.qty:
                        old_qty = ubica_id.qty
                    else:
                        old_qty = 0.00
                    if move.picking_id.type == 'in':
                        new_qty = old_qty + move.product_qty
                    elif move.picking_id.type == 'out':
                        new_qty = old_qty - move.product_qty
                    elif move.picking_id.type == 'internal' and move.picking_id.internal_out:
                        new_qty = old_qty - move.product_qty
                    elif move.picking_id.type == 'internal' and move.picking_id.internal_in:
                        new_qty = old_qty + move.product_qty
                    date = move.date or time.strftime('%Y-%m-%d %H:%M:%S')
                    cr.execute("""update product_ubication set qty=%s, write_uid=%s, write_date=%s where id=%s """, (new_qty, uid, date, ubica_id.id))
            if move.picking_id:
                picking_ids.append(move.picking_id.id)
            if move.move_dest_id.id and (move.state != 'done'):
                self.write(cr, uid, [move.id], {'move_history_ids': [(4, move.move_dest_id.id)]})
                if move.move_dest_id.state in ('waiting', 'confirmed'):
                    if move.prodlot_id.id and move.product_id.id == move.move_dest_id.product_id.id:
                        self.write(cr, uid, [move.move_dest_id.id], {'prodlot_id': move.prodlot_id.id})
                    self.force_assign(cr, uid, [move.move_dest_id.id], context=context)
                    if move.move_dest_id.picking_id:
                        wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                    if move.move_dest_id.auto_validate:
                        self.action_done(cr, uid, [move.move_dest_id.id], context=context)

        moves_id = self._create_product_valuation_moves(cr, uid, move_ids, context=context)
        if moves_id:
            account_obj.post(cr, uid, [moves_id])
#         self.write(cr, uid, [move.id], {'move_id': moves_id}, context=context)
        prodlot_id = partial_datas and partial_datas.get('move%s_prodlot_id' % (move.id), False)
        if prodlot_id:
            self.write(cr, uid, [move.id], {'prodlot_id': prodlot_id}, context=context)
        if move_ids:
            cr.execute("""update stock_move set  write_date =now(), state='done' where id in %s """, (tuple(move_ids),))
        for id in move_ids:
            wf_service.trg_trigger(uid, 'stock.move', id, cr)
            move_act = self.browse(cr, uid, id, context)
            if move_act.picking_id.type == 'in' or (move_act.picking_id.internal_in and move_act.picking_id.type == 'internal'):
                ub_id = move_act.ubication_id.id
                if not move_act.ubication_id:
                    if ubication_id:
                        ub_search = self.pool.get('ubication').search(cr, uid, [('shop_ubication_id', '=',
                                                                                 move_act.picking_id.shop_id.shop_ubication_id.id)])
                        if ub_search:
                            ub_id = self.pool.get('ubication').browse(cr, uid, ub_search[0]).id
                    else:
                        raise osv.except_osv(_('Warning!'),
                                             _(('The move of product %s - %s required a ubication in the warehouse %s, please check!') %
                                               (move_act.product_id.default_code, move_act.product_id.name, move_act.location_dest_id.name)))
                    verify_id = self.pool.get('product.ubication').search(cr, uid, [('ubication_id', '=', ub_id),
                                                                                    ('product_id', '=', move_act.product_id.id)])
                    if not verify_id:
                        raise osv.except_osv(_('Aviso!'), _('No existe ubicación creada para el producto %s - %s en la bodega %s!') %
                                             (move_act.product_id.default_code, move_act.product_id.name, move_act.product_id.location_id.name))
        return True

    def action_done_inventory(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        @return:
        """
        move_ids = []
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        todo = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == "draft":
                self.write(cr, uid, move.id, {'state': 'done'})
#                todo.append(move.id)
#        if todo:
#            self.action_confirm(cr, uid, todo, context=context)
#            todo = []
        moves_id = None
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done', 'cancel', 'assigned']:
                move_ids.append(move.id)
            if not move.ubication_id:
                raise osv.except_osv(_('Error!'), _(("Debe especificar una ubicación de destino para el producto %s - %s de la categoría %s") %
                                                    (move.product_id.default_code, move.product_id.name, move.categ_id.name)))
            #  move_ids.append(move.id)
            if move.move_dest_id.id and (move.state != 'done'):
                self.write(cr, uid, [move.id], {'move_history_ids': [(4, move.move_dest_id.id)]})
            moves_id = self._create_product_valuation_moves(cr, uid, [move.id], context=context)
            self.pool.get('account.move').post(cr, uid, [moves_id], context)
            self.write(cr, uid, [move.id], {'move_id': moves_id}, context=context)
            if move.state not in ('confirmed', 'done', 'assigned'):
                todo.append(move.id)
        self.write(cr, uid, move_ids, {'state': 'done'}, context=context)
        for id in move_ids:
            wf_service.trg_trigger(uid, 'stock.move', id, cr)
        return True

stock_move()
