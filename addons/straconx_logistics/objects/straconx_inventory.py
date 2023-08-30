# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################

import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp


class stock_inventory_line(osv.osv):
    _inherit = 'stock.inventory.line'

    def _get_inventory(self, cr, uid, ids, context=None):
        result = {}
        try:
            for inventory in self.pool.get('stock.inventory').browse(cr, uid, ids, context=context):
                for line in inventory.inventory_line_id:
                    result[line.id] = True
            return result.keys()
        except AttributeError:
            return result.keys()

    _columns = {'ubication_id': fields.many2one('ubication', 'Ubication Case'),
                'categ_id': fields.many2one('product.category', 'Category'),
                'product_amount': fields.float('Quantity', digits_compute=dp.get_precision('Product UoM')),
                'qty_diff': fields.float('Qty dif', digits_compute=dp.get_precision('Product UoM')),
                'transaction': fields.selection([('in', 'IN'), ('out', 'OUT'), ('none', 'None')],
                                                'Transaction Result', select=True, readonly=True),
                'date': fields.related('inventory_id', 'date', type='datetime', string="Fecha",
                                       store={'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['inventory_id'], 5),
                                              'stock.inventory': (_get_inventory, ['state'], 4)},),
                'state': fields.related('inventory_id', 'state', type='selection',
                                        selection=[('draft', 'Borrador'),
                                                   ('done', 'Realizado'),
                                                   ('confirm', 'Confirmado'),
                                                   ('cancel', 'Anulado')],
                                        string="State",
                                        store={'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['inventory_id'], 5),
                                               'stock.inventory': (_get_inventory, ['state'], 4),
                                               },),
                'default_code': fields.char('Código', size=100)
                }

    _order = 'default_code asc, product_id asc, ubication_id asc'

#    TODO: Product and ubications must be unique
    _sql_constraints = [('ubication_product_uniq', 'unique(product_id,ubication_id,inventory_id)',
                         'This product already exists in this ubication for this inventory, please check')]

    def onchange_location(self, cr, uid, ids, location_id=None, context=None):
        res = {}
        if location_id:
            ubication = self.pool.get('ubication').search(cr, uid, [('location_id', '=', location_id)], limit=1, context=context)
            res['ubication_id'] = ubication and ubication[0] or None
        return {'value': res}

    def onchange_product(self, cr, uid, ids, product_id=None, context=None):
        res = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            res['default_code'] = product.default_code or None
            res['categ_id'] = product.categ_id and product.categ_id.id or None
            res['product_uom'] = product.uom_id and product.uom_id.id or None
        location_id = context.get('location', False)
        if location_id:
            ubication_ids = self.pool.get('ubication').search(cr, uid, [('location_id', '=', location_id)], limit=1, context=context)
            if ubication_ids:
                ubication_id = ubication_ids[0]
            else:
                raise osv.except_osv(_('Aviso!'), _('¡No existen ubicaciones creadas dentro de esta bodega para el producto seleccionado!'))
            res['location_id'] = location_id
            res['ubication_id'] = ubication_id
        return {'value': res}

stock_inventory_line()


class inventory_motive(osv.osv):
    _name = "stock.inventory.motive"
    _columns = {'code': fields.char('code', size=5, required=True),
                'name': fields.char('Motive', size=255, required=True),
                'type': fields.selection([('normal', 'Normal'), ('other', 'Ajuste')], 'State', select=True),
                'active': fields.boolean('Activo')}
    _sql_constraints = [('code_company_uniq', 'unique (code,name)', 'The code of the motive must be unique per company !')]
inventory_motive()


class stock_inventory(osv.osv):
    _inherit = 'stock.inventory'
    _columns = {'user_id': fields.many2one('res.users', 'User', states={'draft': [('readonly', False)]}, select=True),
                'motive': fields.many2one('stock.inventory.motive', 'Motive', readonly=True, states={'draft': [('readonly', False)]}, select=True),
                'location_id': fields.many2one('stock.location', 'Location', readonly=True, states={'draft': [('readonly', False)]}),
                'categ_id': fields.many2one('product.category', 'Category', readonly=True, states={'draft': [('readonly', False)]}),
                'inventory_line_id': fields.one2many('stock.inventory.line', 'inventory_id', 'Inventories', readonly=True,
                                                     states={'draft': [('readonly', False)], 'counting': [('readonly', False)]}),
                'note': fields.text('Observations', readonly=True, states={'draft': [('readonly', False)], 'counting': [('readonly', False)]}),
                'reference': fields.char('Reference', size=60, states={'draft': [('readonly', False)]}, select=True),
                'review_move': fields.boolean('Revisar Inventario Contablemente', states={'draft': [('readonly', False)]}),
                'account_id': fields.many2one('account.account', 'Cuenta Contable', states={'draft': [('readonly', False)]}),
                'state': fields.selection([('draft', 'Draft'),
                                           ('counting', 'Counting'),
                                           ('confirm', 'Confirmed'),
                                           ('done', 'Done'),
                                           ('cancel', 'Cancelled')], 'State', readonly=True, select=True),
                }
    _defaults = {'user_id': lambda obj, cr, uid, context: uid,
                 'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'stock.inventory')}

    _order = 'date desc, name asc'

    def action_counting(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for inventory in self.browse(cr, uid, ids, context):
            if inventory.name:
                if inventory.location_id.name in inventory.name:
                    name = inventory.name
                elif inventory.location_id.name and inventory.name:
                    name = inventory.location_id.name + '/' + inventory.name
                else:
                    seq_obj_name = 'stock.inventory'
                    name = inventory.location_id.name + '-' + self.pool.get('ir.sequence').next_by_code(cr, uid, seq_obj_name)
            if not inventory.date:
                raise osv.except_osv(_('Warning!'), _('You must choose a date in the stock inventory!'))
            for line in inventory.inventory_line_id:
                uom = None
                if not line.product_id:
                    raise osv.except_osv(_('Warning!'), _('You must choose a product in the inventory line!'))
                if not line.location_id:
                    raise osv.except_osv(_('Warning!'), _(('You must choose a location in the product %s of inventory line!') %
                                                          (line.product_id.name)))
                uom = line.product_uom.id or line.product_id.uom.id
                sql_update = """((SELECT product_id, SUM(x.coeff * x.product_qty) as product_qty FROM
                                (SELECT product_id,1.0 as coeff, location_dest_id as loc_id, sum(product_qty) AS product_qty
                                FROM stock_move sm WHERE location_dest_id =%s AND location_id != location_dest_id AND state = 'done'
                                and sm.product_id = %s
                                and sm.date <=%s
                                GROUP BY product_id,location_dest_id 
                                UNION
                                SELECT product_id,-1.0 as coeff, location_id as loc_id,sum(product_qty) AS product_qty
                                FROM stock_move sm WHERE location_id =%s AND location_id != location_dest_id AND state = 'done'
                                and sm.product_id = %s
                                and sm.date <=%s
                                GROUP BY product_id,location_id )
                                AS x GROUP BY product_id,x.loc_id))"""
                cr.execute(sql_update, (line.location_id.id, line.product_id.id, inventory.date, line.location_id.id, line.product_id.id,
                                        inventory.date))
                data = cr.fetchone()
                if data:
                    total = data[1]
                else:
                    total = 0.00
                ubi_ids = self.pool.get('product.ubication').search(cr, uid, [('product_id', '=', line.product_id.id),
                                                                              ('ubication_id', '=', line.ubication_id.id)])
                if ubi_ids:
                    total = total
                else:
                    raise osv.except_osv(_('Error!'), _(('Todos los productos necesita un ubicación: Producto=%s, Bodega=%s, Ubicación=%s!') %
                                                        (line.product_id.name, line.location_id.name, line.ubication_id.name)))
                if inventory.motive.type == 'normal':
                    change = line.product_qty - total
                elif inventory.motive.type == 'other':
                    change = line.product_qty
                if change < 0:
                    transaction = 'in'
                elif change > 0:
                    transaction = 'out'
                else:
                    transaction = 'none'
                self.pool.get('stock.inventory.line').write(cr, uid, [line.id], {'product_amount': total,
                                                                                 'date': inventory.date,
                                                                                 'qty_diff': change,
                                                                                 'product_uom': uom,
                                                                                 'transaction': transaction})
        self.write(cr, uid, ids, {'state': 'counting', 'name': name})
        return True

    def action_done(self, cr, uid, ids, context=None):
        """ Finish the inventory
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        product_ids = []
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.account_id:
                context.update({'account_id': inv.account_id, 'review_move': inv.review_move})
            moves = []
            for line in inv.move_ids:
                if not (line.location_id.company_id and line.location_dest_id.company_id):
                    raise osv.except_osv(_('Error!'), _(('The warehouses %s and %s must have a company by default') %
                                                        (line.location_id.name, line.location_dest_id.name)))
                moves.append(line.id)
            move_obj.action_done_inventory(cr, uid, moves, context=context)
            self.write(cr, uid, [inv.id], {'state': 'done', 'date_done': inv.date}, context=context)
            for line in inv.inventory_line_id:
                if line.product_id and line.ubication_id:
                    product_ids.append(line.product_id.id)
                elif not line.ubication_id:
                    raise osv.except_osv(_('Error!'), _(('All products needs a ubication: product=%s - %s, warehouse=%s, Ubication=%s!') %
                                                        (line.product_id.default_code, line.product_id.name, line.location_id.name,
                                                         line.ubication_id.name)))
            if product_ids:
                sql_update = """update product_ubication as pu set qty = xlm.product_qty, write_date =now() from
                        ((SELECT product_id, SUM(x.coeff * x.product_qty) as product_qty FROM
                        (SELECT product_id,1.0 as coeff, location_dest_id as loc_id, sum(product_qty) AS product_qty
                        FROM stock_move sm WHERE location_dest_id =%s AND location_id != location_dest_id AND state = 'done'
                        and sm.product_id in %s
                        GROUP BY product_id,location_dest_id, product_uom
                        UNION
                        SELECT product_id,-1.0 as coeff, location_id as loc_id,sum(product_qty) AS product_qty
                        FROM stock_move sm WHERE location_id =%s AND location_id != location_dest_id AND state = 'done'
                        and sm.product_id in %s
                        GROUP BY product_id,location_id, product_uom)
                        AS x GROUP BY product_id,x.loc_id)) as xlm
                        where pu.product_id = xlm.product_id
                        and location_ubication_id = %s
                        and xlm.product_id in %s"""
                cr.execute(sql_update, (line.location_id.id, tuple(product_ids), line.location_id.id, tuple(product_ids), line.location_id.id,
                                        tuple(product_ids)))
                self.pool.get('product.product').write(cr, uid, product_ids, {})
        return True

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirm the inventory and writes its finished date
        @return: True
        """
        if context is None:
            context = {}
        # to perform the correct inventory corrections we need analyze stock location by
        # location, never recursively, so we use a special context
        product_context = dict(context, compute_child=False)

        for inv in self.browse(cr, uid, ids, context=context):
            move_ids = []
            for line in inv.inventory_line_id:
                product_context.update(uom=line.product_uom.id, date=inv.date, prodlot_id=line.prod_lot_id.id)
                if line.inventory_id.motive.type == 'normal':
                    change = line.product_qty - line.product_amount
                elif line.inventory_id.motive.type == 'other':
                    change = line.product_qty
                line.write({'qty_diff': change})
                lot_id = line.prod_lot_id.id
                if inv.account_id:
                    context.update({'account_id': inv.account_id})
                transaction = 'none'
                if change:
                    location_id = line.product_id.product_tmpl_id.property_stock_inventory.id
                    value = {
                        'name': 'INV:' + str(line.inventory_id.id) + ':' + line.inventory_id.name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'prodlot_id': lot_id,
                        'date': inv.date,
                        'ubication_id': line.ubication_id.id,
                    }
                    if change > 0:
                        value.update({
                            'product_qty': abs(change),
                            'location_id': location_id,
                            'location_dest_id': line.location_id.id,
                            'origin': 'IN:' + line.inventory_id.name,
                        })
                        transaction = 'in'
                    else:
                        value.update({
                            'product_qty': abs(change),
                            'location_id': line.location_id.id,
                            'location_dest_id': location_id,
                            'origin': 'OUT:' + line.inventory_id.name
                        })
                        transaction = 'out'
                    move_ids.append(self._inventory_line_hook(cr, uid, line, value))
                self.pool.get('stock.inventory.line').write(cr, uid, [line.id], {'transaction': transaction})
            message = _('Inventory') + " '" + inv.name + "' " + _("is done.")
            self.log(cr, uid, inv.id, message)
            self.write(cr, uid, [inv.id], {'state': 'confirm', 'move_ids': [(6, 0, move_ids)]})
        return True

    def action_cancel_inventory(self, cr, uid, ids, context=None):
        """ Cancels both stock move and inventory
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        account_move_obj = self.pool.get('account.move')
        for inv in self.browse(cr, uid, ids, context=context):
            for line in inv.inventory_line_id:
                self.pool.get('stock.inventory.line').write(cr, uid, [line.id], {'product_amount': 0.00,
                                                                                 'qty_diff': 0.00}, context=context)
            move_obj.action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
            move_obj.write(cr, uid, [x.id for x in inv.move_ids], {'state': 'draft'}, context=context)
            for move in inv.move_ids:
                account_move_ids = account_move_obj.search(cr, uid, [('name', '=', move.name)])
                if account_move_ids:
                    account_move_data_l = account_move_obj.read(cr, uid, account_move_ids, ['state'], context=context)
                    for account_move in account_move_data_l:
                        account_move_obj.write(cr, uid, [account_move['id']], {'state': 'draft'}, context=context)
                        account_move_obj.unlink(cr, uid, [account_move['id']], context=context)
            move_obj.unlink(cr, uid, [x.id for x in inv.move_ids], context=context)
            self.write(cr, uid, [inv.id], {'state': 'cancel'}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.state != 'draft':
                raise osv.except_osv(_('UserError'), _('You can delete only in draft status the inventory.'))
        return super(stock_inventory, self).unlink(cr, uid, ids, context=context)
stock_inventory()