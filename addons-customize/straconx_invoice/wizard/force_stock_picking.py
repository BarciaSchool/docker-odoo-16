# -*- coding: utf-8 -*-
from osv import osv,fields
import time

class force_stock_picking(osv.osv_memory):
    _name = "force.stock.picking"
    _columns = {
              'company_id': fields.many2one('res.company', 'Company', required=True),
              'shop_id': fields.many2one('sale.shop', 'Tienda', required=False),
              }
    
    def force_availability(self, cr, uid, ids, context=None):
        obj_account_invoice = self.pool.get("account.invoice")        
        obj_stock_picking = self.pool.get("stock.picking")
        for brw_self in self.browse(cr, uid, ids, context=context):
            srch_account_invoice = obj_account_invoice.search(cr, uid, [('migrate', '=', True), ('state', 'in', ('paid','open')), ('picking_id', '!=', False), ('company_id', '=', brw_self.company_id.id), ('type', '=', 'out_invoice')])
            if(not srch_account_invoice):
                continue
            stock_pickings = obj_account_invoice.read(cr, uid,srch_account_invoice,['picking_id','id'])
            list_stock_picking_id=[]
            for dict_id in stock_pickings:
                list_stock_picking_id.append(dict_id["picking_id"][0])
            srch_stock_picking = obj_stock_picking.search(cr, uid, [('id', 'in', tuple(list_stock_picking_id)), ('state', '=', 'assigned')])
            osv._logger.warning('%s',str(len(srch_stock_picking)))
            if(not srch_stock_picking):
                continue
            for brw_stock_picking in obj_stock_picking.browse(cr, uid, srch_stock_picking, context=context):
                try:                                        
                    obj_stock_picking.action_move(cr,uid,[brw_stock_picking.id],context)
                    osv._logger.warning('picking %s in state assigned is approved',brw_stock_picking.id)
                    cr.commit()                    
                except:
                    osv._logger.warning("Force the picking %s error with id # %s",brw_stock_picking.name,brw_stock_picking.id)
                    cr.rollback()
        return {'type': 'ir.actions.act_window_close'}

    def force_availability_draft(self, cr, uid, ids, context=None):
        obj_account_invoice = self.pool.get("account.invoice")        
        obj_stock_picking = self.pool.get("stock.picking")
        for brw_self in self.browse(cr, uid, ids, context=context):
            if not brw_self.shop_id.id:
                raise osv.except_osv(_('Aviso!'), _('¡Necesita seleccionar una tienda para poder continuar!'))
            srch_account_invoice = obj_account_invoice.search(cr, uid, [('state', 'in', ('paid','open')), ('company_id', '=', brw_self.company_id.id), ('type', '=', 'out_invoice')])
            if(not srch_account_invoice):
                continue
#             stock_pickings = obj_account_invoice.read(cr, uid,srch_account_invoice,['picking_id','id'])
            stock_pickings=[]
            for inv in obj_account_invoice.browse(cr,uid,srch_account_invoice):
                stock_pickings.append(inv.picking_id.id)
            list_stock_picking_id=[]
            for dict_id in stock_pickings:
                list_stock_picking_id.append(dict_id["picking_id"][0])
            srch_stock_picking = obj_stock_picking.search(cr, uid, [('id', 'in', tuple(list_stock_picking_id)), ('state', '!=', 'done'),('shop_id','=',brw_self.shop_id.id)])
            osv._logger.warning('%s',str(len(srch_stock_picking)))
            if(not srch_stock_picking):
                continue
            for brw_stock_picking in obj_stock_picking.browse(cr, uid, srch_stock_picking, context=context):
                try:                                        
                    obj_stock_picking.action_move(cr,uid,[brw_stock_picking.id],context)
                    osv._logger.warning('picking %s in state assigned is approved',brw_stock_picking.id)
                    cr.commit()                    
                except:
                    osv._logger.warning("Force the picking %s error with id # %s",brw_stock_picking.name,brw_stock_picking.id)
                    cr.rollback()
        return {'type': 'ir.actions.act_window_close'}

    def force_availability_done(self, cr, uid, ids, context=None):
        obj_account_invoice = self.pool.get("account.invoice")
        obj_account_invoice_lines = self.pool.get("account.invoice.line")        
        obj_stock_picking = self.pool.get("stock.picking")
        move_obj=self.pool.get('stock.move')
        for brw_self in self.browse(cr, uid, ids, context=context):
            if not brw_self.shop_id.id:
                raise osv.except_osv(_('Aviso!'), _('¡Necesita seleccionar una tienda para poder continuar!'))
            srch_account_invoice = obj_account_invoice.search(cr, uid, [('state', 'in', ('paid','open')),('shop_id','=',brw_self.shop_id.id), ('company_id', '=', brw_self.company_id.id), ('type', '=', 'out_invoice'),('picking_id','=',False)])
            if(not srch_account_invoice):
                continue
            osv._logger.warning('Se van a crear %s picking(s) de la factura(s) pendiente(s)',len(srch_account_invoice)) 
            for inv in srch_account_invoice:
                try:                                        
                    invoice = obj_account_invoice.browse(cr,uid,inv) 
                    invoice_lines = obj_account_invoice_lines.search(cr,uid,[('invoice_id','=',invoice.id),('product_id','!=',False)])
                    if not invoice.picking_id and invoice_lines:
                        picking_id = None
                        move=[]
                        tp='out'
                        origin = invoice.shop_id.warehouse_id.lot_stock_id.id
                        dest = invoice.partner_id.property_stock_customer.id or self.pool.get('stock.location').search(cr,uid,[('usage','=','customer')])[0]
                        if not dest:
                            raise osv.except_osv(_('Aviso!'), _('¡Necesita definir la Bodega de destino para continuar!'))                            
                        if not picking_id:
                            pick_name = invoice.shop_id.number_sri +"-" +self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.'+tp)
                            data={'partner_id':invoice.partner_id.id,
                                  'address_id': invoice.address_invoice_id.id,
                                  'carrier_id':invoice.carrier_id.id or invoice.partner_id.property_delivery_carrier.id or None,
                                  'shop_id': invoice.shop_id.id or None,
                                  'segmento_id': invoice.partner_id.segmento_id.id or None,
                                  'salesman_id': invoice.salesman_id.id or invoice.partner_id.salesman_id.id or None,
                                  'date': invoice.date_invoice2,
                                  'note': 'Picking reprocesado de factura #'+ invoice.invoice_number,
                                  'invoice_state': 'invoiced',
                                  'invoice_ids': [[6, 0, [invoice.id]]],
                                  'state':'done',
                                  'location_id': origin,
                                  'location_dest_id':dest,
                                 }
                            cr.execute("""INSERT INTO stock_picking(create_uid, create_date, address_id,min_date, date,partner_id, name, auto_picking, move_type, company_id, invoice_state, state, max_date, type,carrier_id, internal_in, internal_out, invoice_later, local_address_partner, date_expected, weight_net,warehouse_id, confirm_reposition, consigment, digiter_id, salesman_id, shop_id, more_information, segmento_id)values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(uid, invoice.date_invoice2,invoice.address_invoice_id.id,invoice.date_invoice2,invoice.date_invoice2,invoice.partner_id.id,pick_name,'False','direct',invoice.company_id.id,'invoiced','done',invoice.date_invoice2,'out',invoice.carrier_id.id or invoice.partner_id.property_delivery_carrier.id, 'False','False','False',invoice.address_invoice_id.id,invoice.date_invoice2,0,invoice.user_id.id,'True','False',invoice.user_id.id,invoice.salesman_id.id,invoice.shop_id.id,'False',invoice.segmento_id.id))                                
                        for line in invoice.invoice_line:
                            if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                                ubication=None
                                ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',line.product_id.id),('location_ubication_id','=',origin)])
                                if ubication_ids:
                                    ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
                                data={
                                      'product_qty': line.quantity,
                                      'product_uom': line.uos_id.id or line.product_id.uom_id.id,
                                      'product_uos_qty': line.quantity,
                                      'product_uos': line.uos_id.id or line.product_id.uom_id.id,
                                      #'product_packaging': line.product_packaging.id,
                                      'address_id': invoice.address_invoice_id.id,
                                      'company_id': invoice.company_id.id,
                                      'state':'done',
                                      'date': invoice.date_invoice2,
                                      'location_id': origin,
                                      'location_dest_id':dest,
                                      'ubication_id': ubication,
                                      }
                                move_id= obj_stock_picking.create_move(cr, uid, line.name[:64], line.product_id.id, origin, dest, ubication, picking_id, data, context)
                                move.append(move_id)
                    if move:
            #            picking_obj.delivery_picking_available(cr, uid, picking_id, context)
                        cr.execute('UPDATE account_invoice SET write_date =now(),  picking_id=%s WHERE id=%s',(picking_id,invoice.id))
                        cr.execute('INSERT INTO PICKING_INVOICE_REL(INVOICE_ID,PICKING_ID)VALUES(%s,%s)',(invoice.id, picking_id))
                        move_obj.action_done(cr, uid, move, context=context)
                        osv._logger.warning('Fue creado el picking de la factura # %s ',invoice.invoice_number)
                        cr.commit()                                        
                except:
                    osv._logger.warning("Error en la aprobación del picking de la factura %s con id # %s con fecha %s",invoice.invoice_number,invoice.id,invoice.date_invoice)
                    cr.rollback()
        return {'type': 'ir.actions.act_window_close'}
force_stock_picking()
