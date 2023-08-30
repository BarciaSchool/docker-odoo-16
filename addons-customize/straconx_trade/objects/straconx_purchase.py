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


class purchase_order_line(osv.osv):
    _inherit = "purchase.order.line"
    _columns = {
        'tradetax': fields.many2one('product.tradetax', 'Tradetax'),
        'international': fields.boolean('International', required=False),
    }

    _defaults = {'international': lambda*a: False}

    def product_id_change(self, cr, uid, ids, pricelist, product, qty, uom, partner_id, categ_id=False, date_order=False, fiscal_position=False,
                          date_planned=False, name=False, price_unit=False, notes=False, discount=0, offer=0, shop_id=False, price_with_tax=False,
                          context=None):
        res = super(purchase_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, categ_id, date_order,
                                                                 fiscal_position, date_planned, name, price_unit, notes, discount, offer, shop_id,
                                                                 price_with_tax, context)
        if product:
            prod = self.pool.get('product.product').browse(cr, uid, product, context=context)
            res['value']['tradetax'] = prod.tradetax.id
        return res

    def onchange_type_purchase(self, cr, uid, ids, type=False):
        res = {}
        if type:
            type_purchase = self.pool.get('purchase.category').browse(cr, uid, type, context=None).code
            if type_purchase in ('IMP', 'RAP'):
                res['international'] = True
            else:
                res['international'] = False
        return {'value': res}

purchase_order_line()


class purchase_order(osv.osv):
    _inherit = "purchase.order"

#    _columns = {
#        'international':fields.boolean('International', required=False),
#    }

    def inv_line_create(self, cr, uid, a, ol):
        res = super(purchase_order, self).inv_line_create(cr, uid, a, ol)
        res[2]['tradetax'] = ol.tradetax.id
        res[2]['international'] = ol.international
        return res

    def verify_type_purchase(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            if order.type_purchase.code in ('IMP', 'RAP'):
                return False
            return True

purchase_order()
