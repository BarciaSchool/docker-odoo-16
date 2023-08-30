# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#                  2012-2013 STRACONX S.A 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from osv import fields, osv
import time
from straconx_warning.wizard import wizard
from tools.translate import _

class picking_user(osv.osv):
    _name = 'stock.picking.user'
    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        'user_id': fields.many2one('res.users', 'User'),
        'location_id': fields.many2one('stock.location', 'Location Origin'),
        'location_dest_id': fields.many2one('stock.location', 'Location destination'),
        'type': fields.char('Type',size=200),
        'state':fields.related('picking_id','state',type='char',size=25, string='State', relation='stock.picking')
        }
picking_user()

class stock_picking(osv.osv):
    _inherit='stock.picking'

#TODO: Lograr que se borre toda la línea no solo el picking
    def unlink(self, cr, uid, ids, context=None):
        user_pick = self.pool.get('stock.picking.user')
        dels = []
        for i in ids:
            if i:
                cr.execute("""select id from stock_picking_user where picking_id =%s""",(i,))
                lt = cr.fetchall()
                res = super(stock_picking, self).unlink(cr, uid, [i], context=context)                 
                if lt:
                    lt = lt[0][0]
                    dels.append(lt)                
        if dels:
            user_pick.unlink(cr,uid,dels,context=context)
        
        return res
stock_picking()

class make_procurement(osv.osv_memory):
    _inherit = 'make.procurement'
    
    _columns = {
        'date_planned': fields.datetime('Planned Date', required=True),
        'shop_id': fields.many2one('sale.shop', 'Shop'),
        'shop_id_dest': fields.many2one('sale.shop', 'Shop Destiny'),
        'carrier_id': fields.many2one('delivery.carrier', 'Carrier'),
        'location_id': fields.many2one('stock.location', 'Location Origin'),
        'location_dest_id': fields.many2one('stock.location', 'Location destination'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=False),
        'view_picking':fields.boolean('Views Picking', required=False),        
    }
    
    _defaults={
               'date_planned':time.strftime('%Y-%m-%d %H:%M:%S'),
               'view_picking':False,
               }

#     _name = 'make.procurement'
    _description = 'Make Procurements'
    
    def onchange_product_id(self, cr, uid, ids, prod_id,context):
        """ On Change of Product ID getting the value of related UoM.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of IDs selected 
         @param prod_id: Changed ID of Product 
         @return: A dictionary which gives the UoM of the changed Product 
        """
        if not prod_id and context:
            act_id = context.get('active_id',False)
            if act_id:
                obj_model = self.pool.get('stock.shop.lines').browse(cr,uid,act_id).product_id.id
                product = self.pool.get('product.product').browse(cr, uid, obj_model)
        else:        
            product = self.pool.get('product.product').browse(cr, uid, prod_id)
        return {'value': {'uom_id': product.uom_id.id}}
    
    
    def make_procurement(self, cr, uid, ids, context=None):
        picking_obj=self.pool.get('stock.picking')
        data_obj = self.pool.get('ir.model.data')
        picking_id = None
        pick_name=''
        for proc in self.browse(cr, uid, ids, context=context):
            if not (proc.location_dest_id or proc.location_id):
                raise osv.except_osv(_('Invalid Action!'), _('You must defined location Origin and destination, please check.'))            
            #picking_id = picking_obj.search(cr,uid,[('digiter_id','=',uid),('state','=','draft'),('type','=','internal'),('internal_out','=',True),('location_dest_id','=',proc.location_dest_id.id),('shop_id','=',proc.shop_id.id),('shop_id_dest','=',proc.shop_id_dest.id)],limit=1,order='id')
            pick = self.pool.get('stock.picking.user').search(cr,uid,[('picking_id','<>',None),('user_id','=',uid),('picking_id.state','=','draft'),('type','=','internal'),('location_dest_id','=',proc.location_dest_id.id),('location_id','=',proc.location_id.id)],limit=1)
            if pick:
                picking=self.pool.get('stock.picking.user').browse(cr,uid,pick[0]).picking_id
                picking_id = picking.id
                pick_name = picking.name
            if not picking_id:
                pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.internal')
                result=picking_obj.onchange_partner_id(cr, uid, [1], None, 'internal',{'internal_out':True})['value']
                data={
                      'partner_id':result.get('partner_id',None),
                      'address_id': result.get('address_id',None),
                      'carrier_id':proc.carrier_id.id or result.get('carrier_id',None) or None,
                      'shop_id': proc.shop_id.id or None,
                      'shop_id_dest': proc.shop_id_dest.id or None,
                      'date': proc.date_planned or time.strftime('%Y-%m-%d %H:%M:%S'),
                      'location_id':proc.location_id.id,
                      'location_dest_id':proc.location_dest_id.id,
                      'digiter_id': uid,
                      'internal_out':True,
                      'consigment':False,
                      'confirm_reposition':False,
                      }
#TODO: Agregar al picking sequence un no gap para evitar saltos de secuencias
                picking_id = picking_obj.create_picking(cr, uid, pick_name, 'ABAST - '+pick_name+': '+proc.location_id.name+' a '+proc.location_dest_id.name, 'internal', data, context)
                self.pool.get('stock.picking.user').create(cr,uid,{'picking_id':picking_id,'user_id':uid,'location_dest_id':proc.location_dest_id.id,'location_id':proc.location_id.id,'type':'internal'})
            data={'product_qty': proc.qty,
                  'product_uos_qty': proc.qty,
                  'product_uom': proc.uom_id.id,
                  'product_uos': proc.uom_id.id,
                  'date': proc.date_planned or time.strftime('%Y-%m-%d %H:%M:%S'),
                  }
            ubication_dest=self.pool.get('stock.location').search(cr, uid, [('usage','=','transit')], limit=1)
            if not ubication_dest:
                raise osv.except_osv(_('Invalid Action!'), _('You must create location type transit by the transfers.'))
            ubication=None
            ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id','=',proc.product_id.id),('location_ubication_id','=',proc.location_id.id)])
            if ubication_ids:
                ubication=self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
            else:
                ubica = self.pool.get('ubication').search(cr,uid,[('location_id','=',proc.location_id.id)])
                if not ubica:
                    raise osv.except_osv(_('Invalid Action!'), _('You must create at least one ubication for the location %s.')%(proc.location_id.complete_name,))
                
#                 self.pool.get('product.ubication').create(cr, uid, {'ubication_id':ubica[0],
#                                                                     'product_id':proc.product_id.id})
#                 ubication =ubica[0]                          
            picking_obj.create_move(cr, uid, 'ABAST: '+proc.product_id.name, proc.product_id.id, proc.location_id.id, ubication_dest[0], ubication, picking_id, data, context)
            if not pick or proc.view_picking:
                id2 = data_obj._get_id(cr, uid, 'straconx_logistics', 'view_picking_internal_tree')
                id3 = data_obj._get_id(cr, uid, 'straconx_logistics', 'view_picking_internal_out_form')
                
                if id2:
                    id2 = data_obj.browse(cr, uid, id2, context=context).res_id
                if id3:
                    id3 = data_obj.browse(cr, uid, id3, context=context).res_id
            
                action= {
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'stock.picking',
                    'res_id' : picking_id,
                    'views': [(id3,'form'),(id2,'tree')],
                    'type': 'ir.actions.act_window',
                    'nodestroy': False,
                 }
                if not pick:
                    res1=wizard.get_action_warning('Se ha creado el picking %s'%pick_name,action)
                    res1['nodestroy']=False
                else:
                    res1=action
                return res1
            res1= wizard.get_action_warning('El producto %s se a agregado al picking %s'%(proc.product_id.name,pick_name))
            res1['nodestroy']=False
            return res1
            #return {'type': 'ir.actions.act_window_close'}
                    
        
    def on_change_shop(self, cr, uid, ids, shop_id=False, location_id=False, context={}):
        if context is None:
            context={}
        result={}
        if context.get('del_loc',False):
            result['location_id']=None
        if shop_id:
            warehouse=self.pool.get('sale.shop').browse(cr, uid, shop_id, context).warehouse_id
            if context.get('origin',False):
                result['location_id']=warehouse.lot_stock_id.id
            if context.get('dest',False):
                result['location_dest_id']=warehouse.lot_input_id.id
        else:
            if location_id:
                try:
                    wh_id = self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',location_id)])
                    if wh_id:
                        sh = self.pool.get('sale.shop').search(cr,uid,[('warehouse_id','=',wh_id[0])],limit=1)
                        if sh:
                            result['shop_id']=sh and sh[0] or None
                    else:
                        sh = self.pool.get('sale.shop').search(cr,uid,[('central_warehouse','=',True)],limit=1)[0]
                        if sh:
                            result['shop_id']=sh
                except:
                    raise osv.except_osv(_('Warehouse Required!'), _('Need a shop with a central warehouse.'))                
        return {'value':result}

    def onchage_qty_stock(self, cr, uid, ids, qty=0.00, product_id=None, location_id=None, location_dest_id=None, context={}):
        if context is None:
            context={}
        result={}
        warning={}
        if qty>0 and product_id and location_id and location_dest_id:
            proof = self.pool.get('product.ubication').search(cr,uid,[('product_id','=',product_id),('location_ubication_id','=',location_id),('qty','>=',qty)])
            if proof:
                return True
            else:
                product_id = self.pool.get('product.product').browse(cr,uid,product_id)
                location_id = self.pool.get('stock.location').browse(cr,uid,location_id)
                warning = {
                    'title': 'Warning!',
                    'message': ('Product %s no have enought stock in ubication %s.'%(product_id.name,location_id.name))
                    }                        
                result = {'warning': warning}
        return result

    def default_get(self, cr, uid, fields, context=None):
        res = super(make_procurement, self).default_get(cr, uid, fields, context=context)
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        pro_id = self.pool.get('stock.shop.lines').browse(cr,uid,record_id).product_id.id
        active_model = context.get('active_model', False)
        if active_model == 'stock.shop':
            product_id = self.pool.get('stock.shop').browse(cr, uid, record_id, context=context).product_id.id
        else:
            product_id = self.pool.get('product.product').browse(cr, uid, pro_id, context=context).id
        if uid:
            user = self.pool.get('res.users').browse(cr,uid,uid).id
            cr.execute("""select location_id, location_dest_id from stock_picking_user where user_id =%s and picking_id is not null and picking_id = (select id from stock_picking where id = picking_id and state='draft') and type='internal'""",([user]))
            pcash = cr.fetchall()
            if pcash:
                cash = pcash[0][0]
                cash_dest = pcash[0][1]
                if cash:
                    warehouse = self.pool.get('stock.warehouse').search(cr,uid,[('lot_stock_id','=',cash)],limit=1)
                    if warehouse:
                        shop=self.pool.get('sale.shop').search(cr,uid,[('warehouse_id','=',warehouse[0])],limit=1)
                        shop_id = shop and shop[0] or None
                    else:
                        shop = self.pool.get('sale.shop').search(cr,uid,[('central_warehouse','=',True)],limit=1)
                        if shop:
                            shop_id = self.pool.get('sale.shop').browse(cr, uid, shop[0], context).id
                        else:
                            raise osv.except_osv(_('No Shop!'), _('Location need a shop for continue. Assign a shop..'))
                else:
                    shop_id = None
                    cash = None       
                if cash_dest:
                    warehouse_dest = self.pool.get('stock.warehouse').search(cr,uid,[('lot_input_id','=',cash_dest)],limit=1)
                    if warehouse_dest:
                        shop_dest=self.pool.get('sale.shop').search(cr,uid,[('warehouse_id','=',warehouse_dest[0])],limit=1)
                        if not shop_dest:
                            raise osv.except_osv(_('Invalid Action!'), _('Your user need a shop for continue.'))
                        shop_id_dest = shop_dest[0]
                    else:
                        shop_id_dest = None
                        cash_dest = None            
                res.update({'shop_id':shop_id,'location_id':cash,'shop_id_dest':shop_id_dest,'location_dest_id':cash_dest})
            else:
                cr.execute("""select box_id from rel_user_box where user_id= %s order by box_id limit 1""",([user]))
                pcash = cr.fetchall()
                if pcash:
                    cash = pcash[0][0]
                    shop_id = self.pool.get('printer.point').browse(cr,uid,cash).shop_id.id
                    if shop_id:
                        #warehouse=self.pool.get('sale.shop').browse(cr, uid, shop_id, context).warehouse_id.lot_stock_id.id            
                        #res.update({'shop_id_dest':shop_id,'location_dest_id':warehouse})
                        res.update({'shop_id_dest':shop_id})
                else: 
                    raise osv.except_osv(_('Invalid Action!'), _('Your user need a shop for continue.'))                                
        company= self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id         
        res.update({'product_id':product_id})
        res.update({'carrier_id':company.partner_id.property_delivery_carrier.id or None})
        return res

make_procurement()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

