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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
from osv import osv, fields

class product_kardex(osv.osv):
    _name = "product.stock.kardex"
    _rec_name ="date_start"

    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr,uid, uid).company_id.id
        return company or False

    def _get_categ_id(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for obj in self.browse(cr, uid, ids):
            if obj.product_id.categ_id:
                res[obj.id] = obj.product_id.categ_id.id
            else:
                ids = self.pool.get('product.category').search(cr, uid, [('name', '=', 'SIN CATEGORIA')], context=context)
                res[obj.id] = ids and ids[0] or None
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
    
    
    _columns = {
        'company_id': fields.many2one('res.company','Compañía'),                
        'date_start': fields.datetime('Fecha inicial'),
        'date_end': fields.datetime('Fecha final'),
        'ubication_id':fields.many2one('ubication', 'Ubicación'),
        'product_id':fields.many2one('product.product', 'Producto'),
        'location_id': fields.many2one('stock.location', 'Bodega'),
        'categ_id': fields.function(_get_categ_id, fnct_search=_categ_id_search, obj="product.category", method=True, type="many2one", string='Category', store=True,readonly='0'),
        'clas_id': fields.many2one('product.clasification', 'Clasificación'), 
        'kardex_move_line_ids':fields.one2many('product.stock.kardex.line','kardex_id','Líneas de Movimiento'),
        'init_qty': fields.float('Saldo Inicial'),
        'end_qty': fields.float('Saldo Final'),
    }
    
    _defaults = { 
        'company_id': _get_company_id,
        'date_start':'2010-01-01 00:00:00',
        'date_end':datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }    

    def search_lines(self, cr, uid, ids, context):
        cr.execute("""delete from product_stock_kardex_line WHERE KARDEX_ID = %s""",(ids[0],))           
        location_id = self.browse(cr,uid,ids[0]).location_id.id
        company_id = self.browse(cr,uid,ids[0]).company_id.id
        
        product_id = self.browse(cr,uid,ids[0]).product_id.id
        product_tmpl_id = self.pool.get('product.product').browse(cr,uid,product_id).product_tmpl_id.id
        categ_id=self.pool.get('product.template').browse(cr, uid, product_tmpl_id).categ_id.id
        date_from=self.browse(cr,uid,ids[0]).date_start or "1970-01-01 00:00:00"
        date_to=self.browse(cr,uid,ids[0]).date_end or str(datetime.now())
        
        moves={}
        move_in_ids=self.pool.get("stock.move").search(cr,uid,[("product_id","=",product_id),("company_id","=",company_id),("location_dest_id","=",[location_id]),("date",">=",date_from),("date","<=",date_to),("state","=","done")], order='date')
        for move in self.pool.get("stock.move").browse(cr,uid,move_in_ids):
            moves[move.id]=move
        move_out_ids=self.pool.get("stock.move").search(cr,uid,[("product_id","=",product_id),("company_id","=",company_id),("location_id","=",[location_id]),("date",">=",date_from),("date","<=",date_to),("state","=","done")], order='date')
        for move in self.pool.get("stock.move").browse(cr,uid,move_out_ids):
            moves[move.id]=move
        move_in_ids=set(move_in_ids)
        move_out_ids=set(move_out_ids)
        order_moves=moves.values()
        order_moves.sort(lambda a,b: cmp(a.date, b.date))
        lines=[]
        start_qty_in=self.pool.get("product.product").get_product_available(cr,uid,[product_id],context={"location": location_id, "compute_child": True, "what": ["in"], "to_date": date_from, "states": ["done"]})[product_id]
        start_qty_out=self.pool.get("product.product").get_product_available(cr,uid,[product_id],context={"location": location_id, "compute_child": True, "what": ["out"], "to_date": date_from, "states": ["done"]})[product_id]
        
        balance_init= (start_qty_in-start_qty_out) or 0.00
        self.write(cr,uid,ids,{'init_qty':balance_init})
        total_qty_in=start_qty_in
        total_qty_out=start_qty_out
        for move in order_moves:
            qty_in=move.id in move_in_ids and move.product_qty or 0.0
            qty_out=move.id in move_out_ids and move.product_qty or 0.0
            total_qty_in+=qty_in
            total_qty_out+=qty_out
            balance = balance_init + total_qty_in-total_qty_out           
            ref = ''
            if move.picking_id.type=='out':
                type='SALIDA'
                location_dest_id = move.location_dest_id.id
                location_id = move.location_id.id
                invoice=[]
                if move.picking_id.invoice_ids:
                    for p in move.picking_id.invoice_ids:
                        invoice = p.number
                        ref = invoice                
            elif move.picking_id.type=='in':
                type='ENTRADA'
                location_dest_id = move.location_dest_id.id
                location_id = move.location_id.id
                invoice=[]
                if move.picking_id.invoice_ids:
                    for p in move.picking_id.invoice_ids:
                        invoice = p.number
                        ref = invoice
                else:
                    ref = move.picking_id.name or move.name or move.ref
            elif move.picking_id.type=='internal' and move.picking_id.internal_out:
                type='TRANSF. ENVIADA'                
                location_dest_id = move.picking_id.location_dest_id.id
                location_id = move.picking_id.location_id.id
                ref = move.picking_id.name
            elif move.picking_id.type=='internal' and move.picking_id.internal_in:
                type='TRANSF. RECIBIDA'
                location_id = move.picking_id.location_dest_id.id
                location_dest_id = move.picking_id.location_id.id
                ref = move.picking_id.name
            elif move.picking_id.type=='production':
                type='PRODUCCIÓN'
                location_id = move.location_id.id
                location_dest_id = move.location_dest_id.id
                ref = move.picking_id.name                
            elif not move.picking_id:
                type='AJUSTE INVENT.'
                location_id = move.location_id.id
                location_dest_id = move.location_dest_id.id
                ref = move.name

            self.pool.get('product.stock.kardex.line').create(cr,uid,{
                "date_mov": move.date,
                "location_id_init": location_id,
                "location_id_dest": location_dest_id,
                "ref": ref,
                "price_unit": move.price_unit,
                "amount": move.price_unit*move.product_qty,
                "type":type,
                "partner_id": move.partner_id.id or move.company_id.partner_id.id,
                "incoming_qty": qty_in,
                "delivery_qty": qty_out,
                "balance": balance,
                "kardex_id":ids[0],
                "picking_id": move.picking_id.id or False,
                "categ_id":move.product_id.categ_id.id
            })

        end_balance= total_qty_in-total_qty_out
        self.write(cr,uid,ids,{'end_qty':end_balance})
        
        return True
    
product_kardex()

class product_kardex_line(osv.osv):
    _name = "product.stock.kardex.line"
    _rec_name = "kardex_id"
    _columns = {
            'kardex_id': fields.many2one('product.stock.kardex','Kardex'),
            'location_id_init': fields.many2one('stock.location', 'Bodega Origen'),
            'ubication_id_init':fields.many2one('ubication', 'Ubicación Origen'),
            'location_id_dest': fields.many2one('stock.location', 'Bodega Destino'),
            'ubication_id_dest':fields.many2one('ubication', 'Ubicación Destino'),
            'picking_id': fields.many2one('stock.picking','Picking'),
            'ref':fields.char('Referencia',size=40),            
            'date_mov': fields.datetime('Fecha Movimiento'),
            'product_id':fields.many2one('product.product', 'Producto'),
            'categ_id': fields.many2one('product.category', 'Categoría'), 
            'incoming_qty': fields.float('Entradas'),
            'delivery_qty': fields.float('Salidas'),
            'transfer_qty': fields.float('Transferencias'),
            'balance': fields.float('Saldo'),
            'price_unit': fields.float('Costo'),
            'amount': fields.float('Valor'),
            'type': fields.char('Type',size=20),
            'partner_id': fields.many2one('res.partner','Empresa')
    }
product_kardex_line()