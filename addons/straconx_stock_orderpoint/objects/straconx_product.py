    # -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 - present STRACONX S.A. 
#
#
##############################################################################


from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
import decimal_precision as dp


class product_ubication(osv.osv):
    _inherit = 'product.ubication'

    def _verified_order_qty(self, cr, uid, ids, context=None):
        for pubication in self.browse(cr, uid, ids, context):
            if pubication.max_qty < pubication.min_qty:
                raise osv.except_osv(_('Error!'), _(("La cantidad máxima en la ubicación %s debe ser mayor que la cantidad mínima") %(pubication.ubication_id.name)))
        return True

    
    _columns = {
        'max_qty': fields.float('Máximo'),
        'min_qty': fields.float('Mínimo'),
        'date_reorder': fields.date('Fecha Orden'),
        'state': fields.selection([('no_disp','Cotizando'),('available','Solicitar'),('transit','Tránsito'), ('done','Recibido'),('obsolete','Obsoleto')], 'Estado'),
    }

    _defaults = {'state': 'no_disp',
                 'date_reorder':time.strftime('%Y-%m-%d'),
                 'min_qty':0,
                 'max_qty':0
    }
    
    _constraints = [(_verified_order_qty, 'Cantidad Máxima debe ser mayor a la Cantidad Mínima a pedir', ['max_qty','min_qty'])]    

product_ubication()


class product_product(osv.osv):
    _inherit = 'product.product'
        
    def onchange_state_product(self, cr, uid, ids, state, context=None):

        ubication_obj = self.pool.get('product.ubication')
        ubication_ids = []
        if ids:
            product_id = self.browse(cr,uid,ids[0]).id
        else:
            return state
        if product_id and state:
            ubication_ids = ubication_obj.search(cr,uid,[('product_id','=',product_id)])
            if state == 'sellable':      
                new_state = 'available'
                old_state = ['no_disp','obsolete','end']
                cr.execute("""update product_ubication set write_date =now(), state =%s where state in %s and id in %s""",(new_state, tuple(old_state), tuple(ubication_ids)))
            elif state in ('end','obsolete'):
                new_state = 'obsolete'
                cr.execute("""update product_ubication set write_date =now(),  state =%s where id in %s""",(new_state, tuple(ubication_ids),))
            elif state in ('quotation','draft'):
                new_state = 'no_disp'
                cr.execute("""update product_ubication set write_date =now(),  state =%s where id in %s""",(new_state, tuple(ubication_ids),))
        return state
                

    def create(self, cr, uid, vals, context={}):
        max_qty = 0.00
        min_qty = 0.00
        res = super(product_product, self).create(cr, uid, vals, context)
        date_c = time.strftime('%Y-%m-%d %H:%M:%S')
        if res:
            prod_id = self.browse(cr,uid,res)
            if prod_id.ubication_ids:
                for ubica in prod_id.ubication_ids:
                    if prod_id.uom_po_id.id <> prod_id.uom_id.id:
                        max_qty =  2 * prod_id.packing_p * prod_id.packing_q
                        min_qty = prod_id.packing_p * prod_id.packing_q
                    if max_qty >0 and min_qty > 0:
                        sql="""UPDATE PRODUCT_UBICATION SET max_qty = %s, min_qty= %s, write_date=%s, write_uid=%s, state='no_disp' where product_id =%s and id =%s"""
                        cr.execute(sql,(max_qty, min_qty,date_c, uid, res, ubica.id))
        return res
                
product_product()                    
                
                
                
            
        