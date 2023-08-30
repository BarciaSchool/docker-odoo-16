# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv
import decimal_precision as dp

class price_segmento(osv.osv):
    _name = 'price.segmento'
    _rec_name = 'segmento_id'
#     def _price(self, cr, uid, ids, prop, unknow_none,context=None):
#         res={}
#         for line in self.browse(cr, uid, ids):
#             if line.segmento_id and line.product_id:
#                 res[line.id] = line.product_id.list_price * (1-(line.segmento_id.discount/100))
#         return res

#    def _calculate_nprice(self, cr, uid, ids, context=None):
    def write(self, cr, uid, ids, vals, context={}):
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'AccountInvoice')
        account_tax_obj = self.pool.get('account.tax')
        product_obj = self.pool.get('product.product')
        product_id = vals.get('product_id' , False)
        if product_id:
            product_id = product_obj.browse(cr,uid,product_id)
        else:
            product_id = self.browse(cr,uid,ids[0]).product_id
        tax_value = 0.00
        p_net = vals.get('p_net' , False)
        print ids, p_net 
        if p_net:
            nprice= p_net
        else:
            p_net = product_id.p_net
            nprice = p_net 
        if nprice > 0:
            if product_id.taxes_id:
                for t in product_id.taxes_id:
                    tax_code = account_tax_obj.browse(cr, uid, t.id)
                    if tax_code.ref_base_code_id.tax_type == 'vat':
                        tax_value = tax_code.amount                    
                        nprice = round(nprice/(1+tax_value) ,di)
            else:
                nprice = round(nprice,di) 
        iva = round(nprice*tax_value,di)
        if product_id.standard_price>0 and nprice:
            margin_segm = (nprice - product_id.standard_price)/nprice * 100
        vals['p_net'] = p_net
        vals['lst_price_s'] = nprice 
        vals['iva_price'] = iva
        vals['margin_segm'] = margin_segm
        res_id =  super(price_segmento, self).write(cr, uid, ids, vals, context)
        return res_id
        
    _columns = {
        'segmento_id':fields.many2one('res.partner.segmento', 'Segmento', required=False, ondelete="cascade"),
        'product_id':fields.many2one('product.product', 'product', required=False, ondelete="cascade"),
        'p_net': fields.float('P.V.P.', digits_compute=dp.get_precision('Sale Price')),
        'lst_price_s': fields.float('Precio Bruto', digits_compute=dp.get_precision('Sale Price')),
        'iva_price': fields.float('IVA', digits_compute=dp.get_precision('Sale Price')),       
        'margin_segm':fields.float('% Margen', digits_compute=dp.get_precision('Sale Price')),
    }
        
    _sql_constraints = [('segment_product_uniq','unique(segmento_id,product_id)', 'This segment already exist in the product, please check')]

price_segmento()