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
import decimal_precision as dp

class stock_partial_move_memory_in(osv.osv_memory):
    _inherit = 'stock.partial.move'
    _columns = {
        'cost' : fields.float("Cost", digits_compute=dp.get_precision('Trade'), help="Unit Cost for this product line"),
    }
stock_partial_move_memory_in()


class stock_partial_picking(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        pick_obj = self.pool.get('stock.picking')
        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        for pick in pick_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            has_product_cost = (pick.type == 'in' and pick.trade_id)
            for m in pick.move_lines:
                if m.state in ('done','cancel') :
                    continue
                if has_product_cost and m.product_id.cost_method == 'average' and m.invoice_line_id:
                    list_index = 0
                    for item in res['move_ids']:
                        if item['move_id'] == m.id:
                            res['move_ids'][list_index]['cost'] = m.price_unit_trade
                            res['move_ids'][list_index]['price_unit_trade'] = m.price_unit_trade
                            res['move_ids'][list_index]['price_unit'] = m.price_unit_trade
                            res['move_ids'][list_index]['currency'] = m.invoice_line_id.invoice_id.currency_id.id
                        list_index += 1
        return res
stock_partial_picking()