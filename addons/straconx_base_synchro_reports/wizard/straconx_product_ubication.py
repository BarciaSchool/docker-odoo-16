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
from tools.translate import _
from datetime import datetime
import time
import decimal_precision as dp
import psycopg2
import logging
_logger = logging.getLogger(__name__)


class product_shops(osv.osv):
    _name = 'wizard.product.ubication'
    _rec_name = 'product_id'
    _columns = {'product_id': fields.many2one('product.product', 'Producto'),
                'date': fields.datetime('Fecha'),
                'lines_product_ids': fields.one2many('wizard.product.ubication.lines', 'wizard_id', 'Productos'),
                'purchases': fields.float('Compras'),
                'inputs': fields.float('Ingresos'),
                'outputs': fields.float('Ventas'),
                'transfers': fields.float('Transferencias'),
                'stock': fields.float('Stock'),
                'inventory': fields.float('Ajustes'),
                'manufacturer': fields.float('Producción'),
                'refunds': fields.float('Devoluciones'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = {}
        active_id = context.get('active_id', False)
        product_id = self.pool.get('product.product').browse(cr, uid, active_id)
        if product_id:
            res['product_id'] = product_id.id
            res['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
            res['company_id'] = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
            res['purchases'] = product_id.p_qty
        return res

    def do_product_conection(self, cr, uid, ids, context=None):
            location_obj = self.pool.get('stock.location')
            shop_obj = self.pool.get('sale.shop')
            sql = """SELECT DISTINCT
                    PU.LOCATION_UBICATION_ID,
                    PP.ID AS PRODUCT_ID,
                    COALESCE(SUM(CASE WHEN SP.TYPE = 'in' AND SM.LOCATION_DEST_ID = %s
                    AND (SM.CREDIT_NOTE = False OR SM.CREDIT_NOTE IS NULL) THEN product_qty END),0) AS INGRESOS,
                    COALESCE(SUM(CASE WHEN SP.TYPE = 'out' AND SM.LOCATION_ID = %s
                    THEN product_qty END),0) AS VENTAS,
                    COALESCE(SUM(CASE WHEN SP.TYPE = 'internal' AND SM.LOCATION_ID = %s
                    AND SP.INTERNAL_OUT = True THEN product_qty END),0) AS TRANS_ENVIADAS,
                    COALESCE(SUM(CASE WHEN SP.TYPE = 'internal' AND SM.LOCATION_DEST_ID = %s
                    AND SP.INTERNAL_IN = True THEN product_qty END),0) AS TRANS_RECIBIDAS,
                    COALESCE(SUM(CASE WHEN SP.TYPE = 'in' AND SM.LOCATION_ID = %s
                    AND SM.CREDIT_NOTE = True THEN product_qty END),0) AS DEVOLUCIONES,
                    COALESCE(SUM(CASE WHEN SM.PICKING_ID IS NULL AND SM.LOCATION_DEST_ID = %s
                    THEN product_qty WHEN SM.PICKING_ID IS NULL AND SM.LOCATION_ID = %s THEN product_qty*-1 END),0) AS AJUSTES
                    FROM STOCK_MOVE SM
                    LEFT JOIN PRODUCT_PRODUCT PP ON SM.PRODUCT_ID = PP.ID
                    LEFT JOIN STOCK_PICKING SP ON SP.ID = SM.PICKING_ID
                    LEFT JOIN PRODUCT_UBICATION PU ON PU.PRODUCT_ID = PP.ID
                    WHERE PP.ACTIVE = TRUE
                    AND PU.LOCATION_UBICATION_ID = %s
                    AND PP.ID = %s
                    AND PP.ID = SM.PRODUCT_ID
                    AND SM.STATE = 'done'
                    AND SM.LOCATION_ID != SM.LOCATION_DEST_ID
                    GROUP BY PU.LOCATION_UBICATION_ID, PP.ID
                    ORDER BY PP.ID"""

            for w in self.browse(cr, uid, ids):
                cr.execute("""delete from wizard_product_ubication_lines where wizard_id = %s """, (w.id, ))
                if not w.company_id:
                    raise osv.except_osv('Error!', _("Por favor, seleccione una compañía para continuar."))
                else:
                    company_id = w.company_id.id
                if not w.product_id:
                    raise osv.except_osv('Error!', _("Por favor, seleccione un producto para evaluar."))
                else:
                    product_id = w.product_id.id
                location_ids = location_obj.search(cr, uid, [('usage', '=', 'internal'), ('company_id', '=', company_id), ('active', '=', True),
                                                             ('location_id', '!=', None)])
                inputs = 0.00
                sales = 0.00
                transfer_send = 0.00
                transfer_unit = 0.00
                refunds = 0.00
                stock = 0.00
                inventories = 0.00
                conection = False

                if location_ids:
                    shop = False
                    for location in location_ids:
                        shop_ubication_id = location_obj.browse(cr, uid, location).location_id.id
                        shop_ids = shop_obj.search(cr, uid, [('shop_ubication_id', '=', shop_ubication_id)])
                        if shop_ids:
                            shop = shop_obj.browse(cr, uid, shop_ids[0])
                        if shop:
                            database = shop_obj.browse(cr, uid, shop.id).server_db
                            port = shop_obj.browse(cr, uid, shop.id).server_port
                            host = shop_obj.browse(cr, uid, shop.id).server_url
                            user = shop_obj.browse(cr, uid, shop.id).login
                            password = shop_obj.browse(cr, uid, shop.id).password
                            date = time.strftime('%Y-%m-%d %H:%M:%S')
                            if not database or not port or not host or not user or not password:
                                raise osv.except_osv('Error!', _("La tienda %s no tiene configurada toda la información de conexión.")
                                                     % (shop.name))
                            try:
                                conection = psycopg2.connect(database=database, user=user, password=password,
                                                             host=host, port=port, options='-c statement_timeout=15s')
                            except psycopg2.Error:
                                _logger.exception('Connection to the database failed')
                                pass

                            if conection:
                                conect = conection.cursor()
                                conect.execute(sql, (location, location, location, location, location, location,  location, location, product_id))
                                il = conect.fetchall()
                                if il:
                                    purchase_unit = il[0][2]
                                    sales_unit = il[0][3]
                                    transfer_unit_send = il[0][4]
                                    transfer_unit_rec = il[0][5]
                                    refunds_unit = il[0][6]
                                    inventories_unit = il[0][7]
                                    stock_unit = purchase_unit - sales_unit - transfer_unit_send + transfer_unit_rec + refunds_unit + inventories_unit

                                    inputs += purchase_unit
                                    sales += sales_unit
                                    transfer_send += transfer_unit_send
                                    transfer_unit += transfer_unit_rec
                                    refunds += refunds_unit
                                    stock += stock_unit
                                    inventories += inventories_unit
                                    cr.execute("""INSERT INTO wizard_product_ubication_lines(location_id, product_id,purchase_unit,sales_unit,
                                    transfer_send, transfer_unit, refunds, inventories, stock_unit, wizard_id)
                                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (il[0][0], il[0][1], purchase_unit, sales_unit, transfer_unit_send,
                                                                               transfer_unit_rec, refunds_unit, inventories_unit, stock_unit, w.id))
                inputs = inputs
                outputs = sales
                transfers = transfer_send - transfer_unit
                stock = stock
                inventory = inventories
                manufacturer = 0.00
                cr.execute("""update wizard_product_ubication set write_date =now(), stock=%s, inputs=%s, outputs=%s, manufacturer=%s, inventory=%s,
                    transfers=%s where id=%s""", (stock, inputs, outputs, manufacturer, inventory, transfers, ids[0]))
                return True

product_shops()


class product_shops_lines(osv.osv):
    _name = 'wizard.product.ubication.lines'
    _columns = {'location_id': fields.many2one('stock.location', 'Bodega', readonly=True),
                'product_id': fields.many2one('product.product', 'Producto'),
                'stock_unit': fields.float('Inventario'),
                'purchase_unit': fields.float('Compras'),
                'sales_unit': fields.float('Ventas'),
                'transfer_unit': fields.float('Transf. Recibidas'),
                'transfer_send': fields.float('Transf. Enviadas'),
                'refunds': fields.float('Devoluciones'),
                'inventories': fields.float('Ajustes'),
                'wizard_id': fields.many2one('wizard.product.ubication', 'Asistente')}
product_shops_lines()