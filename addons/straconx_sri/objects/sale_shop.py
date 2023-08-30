# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields, osv
from tools.translate import _

class sale_shop(osv.osv): 
    _inherit = "sale.shop"
    
    def _get_address_data(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        address_obj = self.pool.get('res.partner.address')
        for shop in self.browse(cr, uid, ids, context=context):
            result[shop.id] = {}.fromkeys(field_names, False)
            if shop.partner_address_id:
                address = address_obj.read(cr, uid, shop.partner_address_id.id, field_names, context=context)
                for field in field_names:
                    result[shop.id][field] = address[field] or False
        return result
    
    def _set_address_data(self, cr, uid, shop_id, name, value, arg, context=None):
        shop = self.browse(cr, uid, shop_id, context=context)
        if shop.partner_address_id:
            self.pool.get('res.partner.address').write(cr, uid, [shop.partner_address_id.id], {name: value or False})
        return True
    
    _columns = {
                'partner_id': fields.related('company_id','partner_id', type='many2one', relation='res.partner', string='Partner', store=True),
                'partner_address_id':fields.many2one('res.partner.address', 'Address', required=False, domain="[('partner_id', '=', partner_id)]"),
                'number_sri': fields.function(_get_address_data, fnct_inv=_set_address_data, type='char', relation='res.partner.address', string="Number SRI", multi='address',),
                'emision_point': fields.boolean('Punto de Emisión'),
                }
    
    _defaults = {'emision_point': True,
                 }
    
    _sql_constraints = [
        ('address_uniq', 'unique (partner_address_id)',
            'The address selected must be from a one Shop. Please check !'),
    ]
    
    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        raise osv.except_osv(_('¡Error!'), _("¡No se puede duplicar una Tienda ya que contiene información única por punto de venta!"))
        
    def onchange_company(self, cr, uid, ids, company_id=None, context={}):
        result={'value':{}}
        if company_id:
            result['value']['partner_id']= self.pool.get('res.company').browse(cr, uid, company_id, context).partner_id.id
        return result
    
    def onchange_address_id(self, cr, uid, ids, address_id=None, context={}):
        result={'value':{}}
        if address_id:
            result['value']['number_sri']= self.pool.get('res.partner.address').browse(cr, uid, address_id, context).number_sri
        return result
    
sale_shop()