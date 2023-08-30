# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 - present STRACONX S.A.
#
##############################################################################

from datetime import datetime
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc


class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _name = 'stock.picking'
    _order = 'date desc, shop_id asc, carrier_id asc'

    def _cal_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for picking in self.browse(cr, uid, ids, context=context):
            total_weight = total_weight_net = 0.00

            for move in picking.move_lines:
                total_weight += move.weight
                total_weight_net += move.weight_net
                res[picking.id] = {'weight': total_weight,
                                   'weight_net': total_weight_net,
                                   }
        return res

    def _get_picking_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[line.picking_id.id] = True
        return result.keys()

    def _get_payment_term(self, cr, uid, picking):
        """ Gets payment term from partner.
        @return: Payment term
        """
        partner = picking.address_id.partner_id
        if picking.type == 'in':
            if partner.property_payment_term_supplier:
                return partner.property_payment_term_supplier and partner.property_payment_term_supplier.id
            else:
                return partner.property_payment_term and partner.property_payment_term.id
        else:
            if partner.property_payment_term:
                return partner.property_payment_term and partner.property_payment_term.id
            else:
                return False

#    def _get_invoice_state(self, cr, uid, picking):
#        invoice_state = 'none'
#        if picking.type in ('in','out'):
#            invoice_state = '2binvoiced'
#        elif picking.type == 'internal' and picking.internal_in is True:
#            invoice_state = '2binvoiced'
#        elif picking.type == 'internal' and picking.internal_in is False:
#            invoice_state = 'none'
#        else:
#            invoice_state = 'none'
#        return invoice_state

    def create(self, cr, user, vals, context=None):
        if ('name' not in vals) or (vals.get('name') == '/'):
            seq_obj_name = 'stock.picking.' + vals['type']
            vals['name'] = self.pool.get('ir.sequence').next_by_code(cr, user, seq_obj_name)
        type = vals.get('type')
        if type in ('in', 'out') and not vals.get('invoice_state', False):
            vals['invoice_state'] = '2binvoiced'
        new_id = super(stock_picking, self).create(cr, user, vals, context)
        return new_id

    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('default_internal_out', False):
            default_internal_out = context.get('default_internal_out', False)
            default_consigment = context.get('default_consigment', False)
            if not default_internal_out or default_consigment:
                curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
                if curr_user:
                    if not curr_user.printer_point_ids:
                        return None
                    for s in curr_user.printer_point_ids:
                        if s.shop_id:
                            return s.shop_id.id
            else:
                return None

    def _get_shop_internal(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if curr_user:
            if not curr_user.printer_point_ids:
                return None
            for s in curr_user.printer_point_ids:
                if s.shop_id:
                    return s.shop_id.id
        return None

    def _get_salesman(self, cr, uid, context=None):
        res = self.pool.get('salesman.salesman').search(cr, uid, [('user_id', '=', uid)])
        return res and res[0] or None

    def _get_segmento(self, cr, uid, context=None):
        res = self.pool.get('res.partner.segmento').search(cr, uid, [('is_default', '=', True)])
        return res and res[0] or None

    def _check_picking_repeat(self, cr, uid, ids, context=None):
        b = True
        for picking in self.browse(cr, uid, ids, context=context):
            picking_ids = self.search(cr, uid, [('name', '=', picking.name), ('state', 'in', ('done', 'assigned'))])
            if len(picking_ids) > 1:
                b = False
        return b

    _columns = {'confirm_reposition': fields.boolean('Confirm Reposition', required=False),
                'pick_pendding_id': fields.many2one('stock.picking', 'Picking Pendding', select=True),
                'partner_id': fields.many2one('res.partner', 'Partner', readonly=True, states={'draft': [('readonly', False)]}),
                'address_id': fields.many2one('res.partner.address', 'Address', help="Address of partner", domain="[('partner_id', '=', partner_id)]",
                                              readonly=True, states={'draft': [('readonly', False)]}),
                'name': fields.char('Reference', size=128, select=True, readonly=True, states={'draft': [('readonly', False)]}),
                'local_address_partner': fields.char('Local Address', size=128, required=False),
                'address_partner': fields.char('Address_partner', size=128, required=False),
                'segmento_id': fields.many2one('res.partner.segmento', 'Segmento', readonly=True, states={'draft': [('readonly', False)]}),
                'salesman_id': fields.many2one('salesman.salesman', 'Assigned Salesman', readonly=True, states={'draft': [('readonly', False)]}),
                'weight_hand': fields.float('Weight'),
                'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft': [('readonly', False)]}),
                'shop_id_dest': fields.many2one('sale.shop', 'Shop Destiny', readonly=True, states={'draft': [('readonly', False)]}),
                'location_id': fields.many2one('stock.location', 'Location',
                                               help="Keep empty if you produce at the location where the finished products are needed."
                                               "Set a location if you produce at a fixed location. This can be a partner location "
                                               "if you subcontract the manufacturing operations.", readonly=True, select=True,
                                               states={'draft': [('readonly', False)]}),
                'location_dest_id': fields.many2one('stock.location', 'Dest. Location',
                                                    help="Location where the system will stock the finished products.",
                                                    select=True, readonly=True, states={'draft': [('readonly', False)]}),
                'driver_int': fields.many2one('res.users', 'Driver', domain=[('is_driver', '=', True)]),
                'digiter_id': fields.many2one('res.users', 'Digiter', readonly=True, states={'draft': [('readonly', False)]}),
                'carrier_id': fields.many2one("delivery.carrier", "Carrier", readonly=True, states={'draft': [('readonly', False)]}),
                'volume': fields.float('Volume'),
                'weight': fields.function(_cal_weight, method=True, type='float', string='Weight', digits_compute=dp.get_precision('Stock Weight'),
                                          multi='_cal_weight',
                                          store={'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                                                 'stock.move': (_get_picking_line, ['product_id', 'product_qty', 'product_uom', 'product_uos_qty'],
                                                                20),
                                                 }),
                'weight_net': fields.function(_cal_weight, method=True, type='float', string='Net Weight',
                                              digits_compute=dp.get_precision('Stock Weight'), multi='_cal_weight',
                                              store={'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                                                     'stock.move': (_get_picking_line, ['product_id', 'product_qty', 'product_uom',
                                                                                        'product_uos_qty'], 20),
                                                     }),
                'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32),
                'number_of_packages': fields.integer('Number of Packages'),
                'invoice_ids': fields.many2many('account.invoice', 'picking_invoice_rel', 'picking_id', 'invoice_id', 'Invoices',
                                                select=True, ondelete='restrict'),
                'moves_ids': fields.many2many('account.move', 'picking_move_rel', 'picking_id', 'move_id', 'Movimientos',
                                              select=True, ondelete='restrict'),
                'more_information': fields.boolean('More Information', required=False),
                'warehouse_user': fields.many2one('res.users', 'Warehouse User', domain=[('is_warehouse_user', '=', True)]),
                'warehouse_id': fields.many2one('res.users', 'Warehouse Grocer', domain=[('is_warehouse_user', '=', True)]),
                'nb_print': fields.integer('Number of Print', readonly=True),
                'origin': fields.char('Origin', size=128, help="Reference of the document that produced this picking.", select=True, readonly=True,
                                      states={'draft': [('readonly', False)]}),
                'date': fields.datetime('Order Date', help="Date of Order", select=True, readonly=True, states={'draft': [('readonly', False)]}),
                'date_expected': fields.datetime('Scheduled Date', readonly=True, states={'draft': [('readonly', False)]}, select=True,
                                                 help="Scheduled date for the processing of this move"),
                'date_done': fields.datetime('Date Done', help="Date of Completion"),
                'print_status': fields.char('Print Status', size=32),
                'journal_id_delivery': fields.many2one('account.journal', 'Journal'),
                'delivery_status': fields.selection([('draft', 'Draft'), ('sent', 'Sent'), ('cancel', 'Cancel')], 'Delivery Status'),
                'delivery_number': fields.char('Delivery Number', size=32),
                'delivery_date': fields.datetime('Delivery Note date'),
                'nb_print_dn': fields.integer('Number of Print', readonly=True),
                'print_status_dn': fields.char('Print Status', size=32),
                'dn_invoiced': fields.boolean('Is invoiced?'),
                'printer_id': fields.many2one('printer.point', 'Printer Point', domain="[('shop_id', '=', shop_id)]", readonly=True,
                                              states={'draft': [('readonly', False)]}),
                'warehouse_id_delivery': fields.many2one('res.users', 'Warehouse Grocer', readonly=True, states={'draft': [('readonly', False)]}),
                'authorization_id': fields.many2one('sri.authorization', 'Authorization', readonly=False,
                                                    help='This Number is necesary for SRI reports'),
                'delivery_guide_id': fields.many2one('stock.delivery', 'Delivery Guide', readonly=True,
                                                     states={'draft': [('readonly', False)]}),
                'internal_in': fields.boolean('IN', required=False),
                'internal_out': fields.boolean('OUT', required=False),
                'consigment': fields.boolean('consigment', required=False),
                'invoice_later': fields.boolean('Invoice Later?', required=False),
                'active': fields.boolean('Activo', required=False),
                'invoice_state': fields.selection([("invoiced", "Invoiced"),
                                                   ("2binvoiced", "To Be Invoiced"),
                                                   ("none", "Not Applicable")], "Invoice Control",
                                                  select=True, required=True, readonly=True,
                                                  ondelete='restrict', states={'draft': [('readonly', False)]}),
                'state': fields.selection([('draft', 'New'),
                                           ('auto', 'Waiting Another Operation'),
                                           ('confirmed', 'Waiting Availability'),
                                           ('assigned', 'Ready to Process'),
                                           ('done', 'Realizado'),
                                           ('invoiced', 'Facturado'),
                                           ('cancel', 'Cancelled'),
                                           ], 'State', readonly=True, select=True,
                                          help="* Draft: not confirmed yet and will not be scheduled until confirmed\n"
                                          "* Confirmed: still waiting for the availability of products\n"
                                          "* Available: products reserved, simply waiting for confirmation.\n"
                                          "* Waiting: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
                                          "* Done: has been processed, can't be modified or cancelled anymore\n"
                                          "* Cancelled: has been cancelled, can't be confirmed anymore"),
                'credit_note': fields.boolean('N/C'),
                'name': fields.char('Reference', size=128, select=True),
                'boxes': fields.integer('Cartones'),
                'rolls': fields.integer('Rollos'),
                'oth_pack': fields.integer('Otros Empaques'),
                'comment': fields.text('Comentarios', required=False),
                }
    _defaults = {'internal_in': lambda *a: False,
                 'internal_out': lambda *a: False,
                 'consigment': lambda *a: False,
                 'confirm_reposition': False,
                 'partner_id': None,
                 'digiter_id': lambda obj, cr, uid, context: uid,
                 'invoice_state': 'none',
                 'shop_id': _get_shop,
                 'shop_id_dest': _get_shop_internal,
                 'salesman_id': _get_salesman,
                 'segmento_id': _get_segmento,
                 'date_expected': None,
                 'delivery_status': 'draft',
                 'active': True,
                 'credit_note': False,
                 'active': True,
                 }

    _constraints = [(_check_picking_repeat, 'El picking ya existe más de una vez en estado Asignado o Aprobado', ['name'])]

    _sql_constraints = [('name_uniq', 'check(1=1)', 'Reference must be unique per Company!')]

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({'nb_print': 0,
                        'state': 'draft',
                        'print_status': '',
                        'warehouse_id': uid,
                        'delivery_status': 'draft',
                        'delivery_number': '',
                        'delivery_date': None,
                        'date_expected': None,
                        'delivery_guide_id': False
                        })
        return super(stock_picking, self).copy(cr, uid, id, default, context)

    def onchange_shop(self, cr, uid, ids, shop_id=False, context={}):
        values = {}
        domain = {}
        default_internal_out = False
        if context is None:
            context = {}
        if context.get('default_internal_out', False):
            default_internal_out = context.get('default_internal_out', False)
        if shop_id:
            shop = self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
            search_location = self.pool.get('stock.location').search(cr, uid, [('location_id', '=',
                                                                                [shop.warehouse_id.lot_stock_id.location_id.id]),
                                                                               ('usage', '=', 'internal')])
            if context.get('location_id', False) != shop.warehouse_id.lot_stock_id.id:
                values['location_id'] = shop.warehouse_id.lot_stock_id.id
            else:
                search_location1 = search_location[:]
                shop.warehouse_id.lot_stock_id.id and search_location1.remove(shop.warehouse_id.lot_stock_id.id)
                values['location_id'] = search_location1 and search_location1[0] or None
            domain['location_id'] = [('id', 'in', search_location)]
        if not default_internal_out:
            domain['shop_id'] = [('id', '=', shop_id)]
        return {'value': values, 'domain': domain}

    def onchange_shop_dest(self, cr, uid, ids, shop_id=False, context={}):
        values = {}
        domain = {}
        if context is None:
            context = {}
        if shop_id:
            shop = self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
            values['address_id'] = shop.partner_address_id.id
            values['partner_id'] = shop.company_id.partner_id.id
            search_location = self.pool.get('stock.location').search(cr, uid, [('location_id', '=',
                                                                                [shop.warehouse_id.lot_input_id.location_id.id]),
                                                                               ('usage', '=', 'internal')])
            if context.get('location_id', False) != shop.warehouse_id.lot_input_id.id:
                values['location_dest_id'] = shop.warehouse_id.lot_input_id.id
            else:
                search_location1 = search_location[:]
                shop.warehouse_id.lot_input_id.id and search_location1.remove(shop.warehouse_id.lot_input_id.id)
                values['location_dest_id'] = search_location1 and search_location1[0] or None
            domain['location_dest_id'] = [('id', 'in', search_location)]
        return {'value': values, 'domain': domain}

    def onchange_location(self, cr, uid, ids, location_origin=False, location_dest=False, context=None):
        values = {}
        warning = {}
        picking_obj = self.pool.get('stock.picking')
        stock_obj = self.pool.get('stock.move')
        if location_origin and location_dest:
            if location_origin == location_dest:
                warning['title'] = _('Location Incorrect !')
                warning['message'] = _("Las bodegas de origen y destino deben ser diferentes")
                values['location_id'] = None
                values['location_dest_id'] = location_dest
        elif not location_origin:
            if context:
                shop_id = context.get('shop_id', False)
                if shop_id:
                    shop = self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
                    values['location_id'] = shop.warehouse_id.lot_input_id.id
        return {'value': values, 'warning': warning}

    def onchange_carrier(self, cr, uid, ids, carrier, context=None):
        values = {}
        if carrier:
            values['more_information'] = self.pool.get('delivery.carrier').browse(cr, uid, carrier, context).more_information
        return {'value': values}

    def _get_salesman_asigned(self, cr, uid, context, address_id=None):

        if not address_id:
            return False

        pool_partner_address = self.pool.get('res.partner.address')
        address = pool_partner_address.browse(cr, uid, address_id, context)

        if (address.salesman_assigned):
            return address.salesman_assigned.id

        return False

    def onchange_partner_in(self, cr, uid, context, address_id=None):
        return {'value': {'salesman_id': self._get_salesman_asigned(cr, uid, context, address_id)}}

    def onchange_partner_id(self, cr, uid, ids, part=False, type=None, context=None):
        result = {}
        if context is None:
            context = {}
        else:
            consigment = context.get('default_consigment', False)
            if (not part or part == 1) and consigment:
                result['partner_id'] = False
                result['address_id'] = False
                return {'value': result}
        if not part:
            if not context.get('internal_out', False):
                return {'value': {'address_id': False, 'carrier_id': False, 'segmento_id': False}}
            else:
                part = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.partner_id.id
                result['partner_id'] = part

        partner_pool = self.pool.get('res.partner')
        addr = partner_pool.address_get(cr, uid, [part], ['delivery', 'invoice', 'contact', 'default'])
        partner = partner_pool.browse(cr, uid, part)

        result['segmento_id'] = False
        result['carrier_id'] = False

        if addr['default']:
            result['address_id'] = addr['default']
        elif addr['invoice']:
            result['address_id'] = addr['invoice']
        elif addr['delivery']:
            result['address_id'] = addr['delivery']
        elif addr['contact']:
            result['address_id'] = addr['contact']

        if partner.is_consignement:
            result['location_dest_id'] = partner.property_stock_consignement.id

        if (partner.segmento_id):
            result['segmento_id'] = partner.segmento_id.id

        if(partner.property_delivery_carrier):
            result['carrier_id'] = partner.property_delivery_carrier.id

        result['salesman_id'] = self._get_salesman_asigned(cr, uid, context, result['address_id'])

        return {'value': result}

    def onchange_loc_id(self, cr, uid, ids, shop_id=None, consigment=False, type=None, context=None):
        result = {}
        if shop_id:
            loc = self.pool.get('sale.shop').browse(cr, uid, shop_id, context=None)
            if type == "internal" and consigment:
                location_id = loc.warehouse_id.lot_stock_id.id
                result['location_id'] = location_id
        return {'value': result}

#    def onchange_loc_dest_id(self, cr, uid, ids, location_dest_id, type=None, consigment = False, context=None):
#        result={}
#        location_dest_id=self.pool.get('stock.location').browse(cr, uid, location_dest_id, context=None)
#        if type=="internal":
#            if not consigment:
#                part=location_dest_id.address_id.partner_id.id
#                address= location_dest_id.address_id.id
#                return {'value': {'partner_id':part,'address_id': address}}
#            else:
#                return {'value': {'partner_id':False,'address_id': False,}}
#        return {'value': result}

    def confirm_resposition(self, cr, uid, ids, context=None):
        for pick in self.browse(cr, uid, ids, context=context):
            shop_id = pick.shop_id.number_sri
            shop_dest_id = pick.shop_id_dest.number_sri
            seq_obj_name = 'stock.picking.internal'
            if pick.name == '/' or None:
                name = shop_id + '|' + shop_dest_id + '-' + self.pool.get('ir.sequence').next_by_code(cr, uid, seq_obj_name)
            else:
                name = shop_id + '|' + shop_dest_id + '-' + pick.name
        return self.write(cr, uid, ids, {'confirm_reposition': True, 'name': name}, context)

    def action_drafted(self, cr, uid, ids, context=None):
        """ Changes picking state to draft.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        move_obj = self.pool.get('stock.move')
        journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'stock')])[0]
        account_move_obj = self.pool.get('account.move')
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.delivery_status == 'sent':
                raise osv.except_osv(_('Invalid Action!'), _('You can not change this picking to draft because exist delivery note in state sent.'))
            if pick.invoice_ids:
                for invoice in pick.invoice_ids:
                    if invoice.state in ('open', 'paid'):
                        raise osv.except_osv(_('Invalid Action!'),
                                             _('You can not change this picking to draft because exist invoices related in state open or paid.'))
            if pick.pick_pendding_id and pick.consigment:
                self.pool.get('stock.picking').action_drafted(cr, uid, [pick.pick_pendding_id.id], context)
                self.pool.get('stock.picking').unlink(cr, uid, [pick.pick_pendding_id.id], context)
            if pick.invoice_state == 'invoiced':
                pick.write({'invoice_state': '2binvoiced'})
            move_ids = account_move_obj.search(cr, uid, [('ref', '=', pick.name), ('journal_id', '=', journal_id), ('state', '!=', 'cancel')])
            if move_ids:
                account_move_obj.button_cancel(cr, uid, move_ids, context=context)
                account_move_obj.unlink(cr, uid, move_ids, context=context)
            if pick.type == 'internal' and pick.internal_out:
                old_pick_name = 'DESP: ' + pick.name
                old_pick_id = self.search(cr, uid, [('name', '=', old_pick_name)])
                if old_pick_id:
                    context.update({'old_pick_id': old_pick_id})
                    self.pool.get('stock.picking').action_drafted(cr, uid, [old_pick_id[0]], context)
                    self.pool.get('stock.picking').unlink(cr, uid, [old_pick_id[0]], context)
                    move_ids = account_move_obj.search(cr, uid, [('ref', '=', old_pick_name), ('journal_id', '=', journal_id),
                                                                 ('state', '!=', 'cancel')])
                    if move_ids:
                        account_move_obj.button_cancel(cr, uid, move_ids, context=context)
                        account_move_obj.unlink(cr, uid, move_ids, context=context)
            ids2 = [move.id for move in pick.move_lines]
            move_obj.action_drafted(cr, uid, ids2, context)
            wf_service.trg_delete(uid, 'stock.picking', pick.id, cr)
            wf_service.trg_create(uid, 'stock.picking', pick.id, cr)
        self.write(cr, uid, ids, {'state': 'draft'})
        self.log_picking(cr, uid, ids, context=context)
        return True

    def action_drafted_transfer_in(self, cr, uid, ids, context=None):
        """ Changes picking state to draft.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        journal_id = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'stock')])[0]
        account_move_obj = self.pool.get('account.move')
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.type == 'internal' and pick.internal_in:
                for m in pick.move_lines:
                    move_obj.write(cr, uid, m.id, {'state': 'assigned'})
                move_ids = account_move_obj.search(cr, uid, [('ref', '=', pick.name), ('journal_id', '=', journal_id), ('state', '!=', 'cancel')])
                if move_ids:
                    account_move_obj.button_cancel(cr, uid, move_ids, context=context)
                    account_move_obj.unlink(cr, uid, move_ids, context=context)
            self.write(cr, uid, ids, {'state': 'assigned'})
            self.log_picking(cr, uid, ids, context=context)
        return True

    def action_process(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context, active_ids=ids, active_model=self._name)
        for pick in self.browse(cr, uid, ids):
            done = True
            if pick.move_lines:
                for l in pick.move_lines:
                    if l.state != 'done':
                        done = False
        if done:
            self.write(cr, uid, ids, {'state': 'done'})
        else:
            partial_id = self.pool.get("stock.partial.picking").create(cr, uid, {}, context=context)
            value = {'name': _("Products to Process"),
                     'view_mode': 'form',
                     'view_id': False,
                     'view_type': 'form',
                     'res_model': 'stock.partial.picking',
                     'res_id': partial_id,
                     'type': 'ir.actions.act_window',
                     'nodestroy': True,
                     'target': 'new',
                     'domain': '[]',
                     'context': context,
                     }
            return value

    def draft_force_assign(self, cr, uid, ids, *args):
        for pick in self.browse(cr, uid, ids):
            if pick.type == "internal":
                user = self.pool.get('res.users').browse(cr, uid, uid)
                if not user.shop_id:
                    raise osv.except_osv(_('Aviso!'), _('El usuario debe tener una tienda asignada.'))
                if pick.internal_out:
                    if user.id != 1:
                        if pick.shop_id.id != user.shop_id.id:
                            raise osv.except_osv(_('Acción Inválida!'), _('Solo puede aprobar pedidos de su tienda.'))
            if pick.type == 'internal' and pick.internal_out:
                if not pick.warehouse_id:
                    raise osv.except_osv(_('Acción Inválida!'), _('Necesita definir un Usuario Despachador.'))
                if not pick.date_expected and not pick.consigment:
                    raise osv.except_osv(_('Acción Inválida!'), _('Necesita definir la fecha esperada de entrega.'))
                if not pick.carrier_id:
                    raise osv.except_osv(_('Acción Inválida!'), _('Necesita definir un Transportista para la entrega.'))
                if pick.date_expected and pick.date_expected <= pick.date:
                    raise osv.except_osv(_('Acción Inválida!'), _('La fecha de entrega debe ser mayor a la fecha de envío.'))
        return super(stock_picking, self).draft_force_assign(cr, uid, ids, args)

    def draft_validate(self, cr, uid, ids, context=None):
        """ Validates picking directly from draft state.
        @return: True
        """
        product_obj = self.pool.get('product.product')
        wf_service = netsvc.LocalService("workflow")
#        move_obj = self.pool.get('stock.move')
        self.draft_force_assign(cr, uid, ids)
        self.action_assign(cr, uid, ids)
        for pick in self.browse(cr, uid, ids, context=context):
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
            if pick.type == 'in' and pick.international:
                for m in pick.move_lines:
                    if m.product_id.state != 'sellable':
                        product_obj.write(cr, uid, m.product_id.id, {'state': 'sellable'})
            if pick.state == 'confirmed':
                return True
            else:
                return self.action_process(cr, uid, ids, context=context)

    def _get_discount_invoice(self, cursor, user, move_line):
        if move_line.purchase_line_id:
            return move_line.purchase_line_id.discount
        elif move_line.sale_line_id:
            return move_line.sale_line_id.discount
        return super(stock_picking, self)._get_discount_invoice(cursor, user, move_line)

    def _get_offer_invoice(self, cursor, user, move_line):
        if move_line.purchase_line_id:
            return move_line.purchase_line_id.offer
        elif move_line.sale_line_id:
            return move_line.sale_line_id.offer_value
        return 0.0

    def _get_price_original(self, cursor, user, move_line):
        if move_line.purchase_line_id:
            return move_line.purchase_line_id.price_unit
        elif move_line.sale_line_id:
            return move_line.sale_line_id.price_unit
        elif move_line.product_id.standard_price != 0:
            return move_line.product_id.standard_price
        else:
            return 0.0

#     def _get_subtotal_invoice(self, cursor, user, move_line):
#         if move_line.purchase_line_id:
#             return  move_line.purchase_line_id.price_subtotal
#         elif move_line.sale_line_id:
#             return move_line.sale_line_id.price_subtotal
#         return 0.0

#    @profile
    # FIXME: needs refactoring, this code is partially duplicated in stock_move.do_partial()!
    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, address_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        ubication_ids = self.pool.get('product.ubication')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.type == 'internal':
                user = self.pool.get('res.users').browse(cr, uid, uid)
                if not user.shop_id:
                    raise osv.except_osv(_('Aviso!'), _('El usuario debe tener una tienda asignada.'))
                if pick.internal_in:
                    if user.id != 1:
                        if pick.shop_id.id != user.shop_id.id:
                            raise osv.except_osv(_('Acción Inválida!'), _('Solo puede aprobar pedidos de su tienda.'))
            warning = {}
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms, product_uos_qty = {}, {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s' % (move.id), {})
                product_qty = partial_data.get('product_qty') or 0.0
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom')
                product_price = partial_data.get('product_price') or 0.0
                product_currency = partial_data.get('product_currency')
                prodlot_id = partial_data.get('prodlot_id') or False
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = partial_data.get('product_uos')
                product_uos_qty = partial_data.get('product_uos_qty')
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if (pick.type == 'out') or (pick.type == 'internal') or (pick.type == 'in'):
                    ub_ids = ubication_ids.search(cr, uid, [('ubication_id', '=', move.ubication_id.id), ('product_id', '=', move.product_id.id)])
                    if ub_ids:
                        u = ubication_ids.browse(cr, uid, ub_ids[0], context)
                        # TODO: Reactivar esta parte del código cuando se migre la información de Inventario.
                        if move.state in ('draft', 'cancel'):
                            if round(move_product_qty[move.id], 6) > round(u.qty, 6) and move_product_qty[move.id] > 0:
                                raise osv.except_osv(_('Incorrect amount !'),
                                                     _('You can not dispatching an amount greater than available in the ubication,'
                                                       ' please dispatching the existing of the ubication.'))
                        else:
                            new_qty = 0.00
                            if ubication_ids.browse(cr, uid, u.id).qty:
                                old_qty = ubication_ids.browse(cr, uid, u.id).qty
                            else:
                                old_qty = 0.00
                            if pick.type == 'in':
                                new_qty = old_qty + product_qty
                            elif pick.type == 'out':
                                new_qty = old_qty - product_qty
                            elif pick.type == 'internal' and pick.internal_out:
                                new_qty = old_qty - product_qty
                            elif pick.type == 'internal' and pick.internal_in:
                                new_qty = old_qty + product_qty
                            date = time.strftime('%Y-%m-%d %H:%M:%S')
                            cr.execute("""update product_ubication set qty=%s, write_uid=%s, write_date=%s where id=%s """,
                                       (new_qty, uid, date, u.id))
                if move.product_qty == product_qty:
                    complete.append(move)
                elif move.product_qty > product_qty:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id in product_avail:
                        product_avail[product.id] += qty
                    else:
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                                         move_currency_id, product_price)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                                           product.uom_id.id)
                        if product.qty_available <= 0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])
                                             + (new_price * qty))/(product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                       {'price_unit': product_price,
                                        'price_currency_id': product_currency})

            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking = self.copy(cr, uid, pick.id,
                                            {'name': sequence_obj.get(cr, uid, 'stock.picking.%s' % (pick.type)),
                                             'move_lines': [],
                                             'state': 'draft',
                                             })
                if product_qty != 0:
                    defaults = {'product_qty': product_qty,
                                'product_uos_qty': product_uos_qty,  # TODO: put correct uos_qty
                                'picking_id': new_picking,
                                'state': 'assigned',
                                'move_dest_id': False,
                                'price_unit': move.price_unit,
                                }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)

                if partial_qty:
                    qty_partial = partial_qty[move.id]
                else:
                    qty_partial = 0.00

                move_obj.write(cr, uid, [move.id],
                               {'product_qty': move.product_qty - qty_partial,
                                'product_uos_qty': move.product_qty - qty_partial,  # TODO: put correct uos_qty
                                })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})

            for move in complete:
                defaults = {'product_uom': move.product_uom.id,
                            'product_qty': move_product_qty[move.id],
                            'product_uos_qty': move.product_uos_qty,
                            'product_uos': product_uoms[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)

            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty': product_qty,
                    'product_uos_qty': product_uos_qty,  # TODO: put correct uos_qty
                    'product_uom': product_uom,
                    'product_uos': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking])
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                warning = {'title': _('Warning!'), 'message': _(('Picking %s have a pending items for send.') % pick.name)}
                delivered_pack_id = new_picking
            else:
                if (pick.type == 'in' and pick.international) or pick.type in ('out', 'internal'):
                    self.action_move(cr, uid, [pick.id])
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id, 'warning': warning or False}
        return res

#    @profile
    def create_move(self, cr, uid, name=None, product=None, location_origin=None, location_dest=None, ubication=None,
                    picking=None, data={}, context={}):
        vals = {'name': name,
                'product_id': product,
                'product_qty': data.get('product_qty', 0),
                'product_uos_qty': data.get('product_uos_qty', 0),
                'product_uom': data.get('product_uom', None),
                'product_uos': data.get('product_uos', None),
                'price_unit': data.get('price_unit', None),
                'date': data.get('date', time.strftime('%Y-%m-%d %H:%M:%S')),
                'location_id': location_origin,
                'location_dest_id': location_dest,
                'picking_id': picking,
                'ubication_id': ubication,
                'address_id': data.get('address_id', None),
                'tracking_id': data.get('tracking_id', None),
                'state': data.get('state', 'draft'),
                'company_id': data.get('company_id', 1),
                'date_expected': data.get('date_expected', time.strftime('%Y-%m-%d %H:%M:%S')),
                }
        return self.pool.get('stock.move').create(cr, uid, vals, context)

    def create_picking(self, cr, uid, name='', origin=None, tp=None, data={}, context={}):
        if name:
            cr.execute("""SELECT id FROM STOCK_PICKING WHERE NAME like %s and state not in ('cancel')""", (name,))
            check_name = cr.fetchone()
            if check_name and check_name[0]:
                self.unlink(cr, uid, [check_name[0]])
        vals = {'name': name,
                'origin': origin,
                'type': tp,
                'invoice_state': data.get('invoice_state', 'none'),
                'delivery_status': data.get('delivery_status', None),
                'stock_journal_id': data.get('stock_journal_id', None),
                'internal_in': data.get('internal_in', False),
                'internal_out': data.get('internal_out', False),
                'carrier_id': data.get('carrier_id', None),
                'consigment': data.get('consigment', False),
                'confirm_reposition': data.get('confirm_reposition', True),
                'shop_id': data.get('shop_id', None),
                'shop_id_dest': data.get('shop_id_dest', None),
                'printer_id': data.get('printer_id', None),
                'partner_id': data.get('partner_id', None),
                'address_id': data.get('address_id', None),
                'date': data.get('date', time.strftime('%Y-%m-%d %H:%M:%S')),
                'min_date': data.get('min_date', time.strftime('%Y-%m-%d %H:%M:%S')),
                'location_dest_id': data.get('location_dest_id', None),
                'location_id': data.get('location_id', None),
                'move_type': data.get('move_type', 'direct'),
                'segmento_id': data.get('segmento_id', None),
                'salesman_id': data.get('salesman_id', None),
                'warehouse_id': data.get('warehouse_id', uid),
                'note': data.get('note', ''),
                'company_id': data.get('company_id', False),
                'date_expected': data.get('date_expected', time.strftime('%Y-%m-%d %H:%M:%S')),
                'invoice_ids': data.get('invoice_ids', []),
                'company_id': data.get('company_id', 1),
                }
        return self.create(cr, uid, vals, context)

#    @profile
    def action_move(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        mod_obj = self.pool.get('ir.model.data')
        move_obj = self.pool.get('stock.move')
        for pick in self.browse(cr, uid, ids, context=context):
            todo = []
            todo_new = []
            picking_new = None
            for move in pick.move_lines:
                if move.state == 'draft':
                    self.pool.get('stock.move').action_confirm(cr, uid, [move.id], context=context)
                    todo.append(move.id)
                elif move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
            if len(todo):
                for move in move_obj.browse(cr, uid, todo, context):
                    if pick.type == "internal" and pick.internal_out:
                        if not picking_new:
                            pick_name = 'DESP: ' + pick.name
                            data = {'delivery_status': 'cancel',
                                    'location_id': pick.location_dest_id.id,
                                    'location_dest_id': pick.location_id.id,
                                    'shop_id': pick.shop_id_dest.id,
                                    'shop_id_dest': pick.shop_id.id,
                                    'warehouse_id': uid,
                                    'stock_journal_id': pick.stock_journal_id.id,
                                    'partner_id': pick.partner_id.id,
                                    'address_id': pick.address_id.id,
                                    'carrier_id': pick.carrier_id.id,
                                    'printer_id': pick.printer_id.id,
                                    'company_id': pick.company_id.id,
                                    'date': pick.date,
                                    'min_date': pick.min_date,
                                    'internal_in': True,
                                    }
                            picking_new = self.create_picking(cr, uid, pick_name, pick.name, 'internal', data, context)
                        ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('location_ubication_id', '=', pick.location_dest_id.id),
                                                                                            ('product_id', '=', move.product_id.id)])
                        if ubication_ids:
                            ubication = self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0], context).ubication_id.id
                        else:
                            ubication = pick.location_dest_id.location_ids and pick.location_dest_id.location_ids[0].id or None
                        data = {'product_qty': move.product_qty,
                                'product_uos_qty': move.product_uos_qty,
                                'product_uom': move.product_uom.id,
                                'product_uos': move.product_uos.id,
                                'price_unit': move.price_unit,
                                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'company_id': move.company_id.id,
                                }
                        move_new = self.create_move(cr, uid, move.name, move.product_id.id, move.location_dest_id.id, pick.location_dest_id.id,
                                                    ubication, picking_new, data, context)
                        todo_new.append(move_new)
                        move_obj.write(cr, uid, [move.id], {'move_dest_id': move_new}, context)
                    elif (pick.type == "internal" and pick.internal_in) or pick.type == "in":
                        wf_service.trg_validate(uid, 'stock.picking', picking_new, 'button_confirm', cr)
#                        wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                    else:
                        if not picking_new:
                            pick_name = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.picking.internal')
                            data = {'delivery_status': 'cancel',
                                    'stock_journal_id': pick.stock_journal_id.id,
                                    'internal_in': pick.internal_in,
                                    'internal_out': pick.internal_out,
                                    'carrier_id': pick.carrier_id.id,
                                    'consigment': pick.consigment,
                                    'shop_id': pick.shop_id.id,
                                    'shop_id_dest': pick.shop_id_dest.id or pick.shop_id.id,
                                    'printer_id': pick.printer_id.id,
                                    'partner_id': pick.partner_id.id,
                                    'address_id': pick.address_id.id,
                                    'date': pick.date,
                                    'min_date': pick.min_date,
                                    'location_id': pick.location_id.id,
                                    'location_dest_id': pick.location_dest_id.id,
                                    'company_id': pick.company_id.id
                                    }
                            picking_new = self.create_picking(cr, uid, pick_name, pick.type.upper()+': '+pick.name, pick.type, data, context)
                        ubication_ids = self.pool.get('product.ubication').search(cr, uid, [('location_ubication_id', '=', pick.location_dest_id.id),
                                                                                            ('product_id', '=', move.product_id.id)])
                        ubication = ubication_ids and self.pool.get('product.ubication').browse(cr, uid, ubication_ids[0],
                                                                                                context=None).ubication_id.id
                        data = {'product_qty': move.product_qty,
                                'product_uos_qty': move.product_uos_qty,
                                'product_uom': move.product_uom.id,
                                'product_uos': move.product_uos.id,
                                'price_unit': move.price_unit,
                                'ubication_id': ubication,
                                'location_id': pick.location_id.id,
                                'location_dest_id': pick.location_dest_id.id,
                                'date': pick.date,
                                'company_id': move.company_id.id,
                                }
                        move_new = self.create_move(cr, uid, move.name, move.product_id.id, move.location_dest_id.id, move.location_id.id, ubication,
                                                    picking_new, data, context)
                        todo_new.append(move_new)
                        move_obj.write(cr, uid, [move.id], {'move_dest_id': move_new}, context)
                if todo_new:
                    self.pool.get('stock.move').action_confirm(cr, uid, todo_new)
                    self.pool.get('stock.move').force_assign(cr, uid, todo_new)
                    wf_service.trg_validate(uid, 'stock.picking', picking_new, 'button_confirm', cr)
                    self.write(cr, uid, [pick.id], {'pick_pendding_id': picking_new, 'warehouse_user': uid})
                    if pick.consigment:
                        wf_service.trg_validate(uid, 'stock.picking', picking_new, 'button_done', cr)
                move_obj.action_done(cr, uid, todo, context=context)
            wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
#            self.pool.get('stock.picking').action_done(cr,uid,pick.id)
        return True

    def _get_address_invoice(self, cr, uid, picking):
        """ Gets invoice address of a partner
        @return {'contact': address, 'invoice': address} for invoice
        """
        partner_obj = self.pool.get('res.partner')
        partner = picking.address_id.partner_id
        return partner_obj.address_get(cr, uid, [partner.id],
                                       ['contact', 'invoice'])

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        if context is None:
            context = {}
        if not move_line.sale_line_id and not move_line.purchase_line_id:
            if move_line.price_unit > 0 and move_line.product_qty > 0:
                return move_line.price_unit * move_line.product_qty
        return super(stock_picking, self)._get_price_unit_invoice(cr, uid, move_line, type)

    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        """ Builds the dict containing the values for the invoice
            @param picking: picking object
            @param partner: object of the partner to invoice
            @param inv_type: type of the invoice ('out_invoice', 'in_invoice', ...)
            @param journal_id: ID of the accounting journal
            @return: dict that will be used to create the invoice object
        """
        if context is None:
            context = {}
        result = {'value': {}}
        if inv_type in ('out_invoice', 'out_refund'):
            if partner.property_account_receivable.company_id.id != picking.company_id.id:
                account_id = self.pool.get('account.account').search(cr, uid, [('code', '=',  partner.property_account_receivable.code),
                                                                               ('company_id', '=', picking.company_id.id)])[0]
            else:
                account_id = partner.property_account_receivable.id
            context['printer_id'] = picking.printer_id and picking.printer_id.id or None
            result = self.pool.get('account.invoice').onchange_shop(cr, uid, picking.id, picking.company_id.id, picking.shop_id.id,
                                                                    'out_invoice', context)
            payment_term = partner.property_payment_term and partner.property_payment_term.id or False
        else:
            if partner.property_account_payable.company_id.id != picking.company_id.id:
                account_id = self.pool.get('account.account').search(cr, uid, [('code', '=', partner.property_account_payable.code),
                                                                               ('company_id', '=', picking.company_id.id)])[0]
            else:
                account_id = partner.property_account_payable.id
            if context.get('journal_type', None) == 'purchase':
                jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '01')])
                result = self.pool.get('account.invoice').onchange_type_document(cr, uid, picking.id, jnl_id and jnl_id[0] or None, inv_type,
                                                                                 context.get('tpurchase', None), context)
            elif context.get('journal_type', None) == 'purchase_liquidation':
                jnl_id = self.pool.get('sri.document.type').search(cr, uid, [('code', '=', '03')])
                result = self.pool.get('account.invoice').onchange_shop(cr, uid, picking.id, picking.company_id.id, context.get('shop_id', None),
                                                                        'in_invoice', context)
                result['value'].update(self.pool.get('account.invoice').onchange_type_document(cr, uid, picking.id, jnl_id and jnl_id[0] or None,
                                                                                               inv_type, context.get('tpurchase', None),
                                                                                               context)['value'])
            payment_term = partner.property_payment_term_supplier and partner.property_payment_term_supplier.id or False
        address_contact_id, address_invoice_id = self.pool.get('res.partner').address_get(cr, uid, [partner.id],
                                                                                          ['contact', 'invoice']).values()
        comment = self._get_comment_invoice(cr, uid, picking)
        number_of_package = 0
        peso = 0
        driver_id = False
        tracking = None
        if context.get('invoice_date2', False):
            date_invoice2 = context.get('invoice_date2', False)
            date_invoice = date_invoice2[:10]
        else:
            date_invoice2 = time.strftime('%Y-%m-%d %H:%M:%S')
            date_invoice = time.strftime('%Y-%m-%d')

        warehouse_user = picking.warehouse_user and picking.warehouse_user.id or None
        if picking.carrier_id.more_information:
            tracking = picking.carrier_tracking_ref
            number_of_package = picking.number_of_packages
            peso = picking.weight_hand
        else:
            driver_id = picking.driver_int.id
        self.write(cr, uid, [picking.id], {'state': 'invoiced'})
        invoice_vals = {
            'name': picking.name,
            'origin': (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
            'type': inv_type,
            'account_id': account_id,
            'partner_id': partner.id,
            'address_invoice_id': address_invoice_id,
            'address_contact_id': address_contact_id,
            'comment': comment,
            'payment_term': payment_term,
            'fiscal_position': partner.property_account_position.id,
            'date_invoice': date_invoice,
            'date_invoice2': date_invoice2,
            'company_id': picking.company_id.id,
            'user_id': uid,
            'picking_id': picking.id,
            'printer_id': context.get('printer_id', None) or picking.printer_id.id or None,
            'salesman_id': picking.salesman_id.id,
            'segmento_id': picking.segmento_id.id,
            'carrier_id': picking.carrier_id.id,
            'shop_id': context.get('shop_id', None) or picking.shop_id.id,
            'account_analytic_id': picking.shop_id.project_id.id or picking.company_id.property_analytic_account.id,
            'more_information': picking.more_information,
            'warehouse_id': uid,
            'electronic': context.get('electronic', None),
            'access_key': context.get('access_key', None),
            'authorization_purchase': context.get('authorization_purchase', None),
            'invoice_number_in': context.get('invoice_number_in', None),
            'tpurchase': context.get('tpurchase', None),
            'authorization_sales': result['value'].get('authorization_sales', None),
            'authorization': result['value'].get('authorization', None) or context.get('authorization', None),
            'pre_printer': result['value'].get('pre_printer', False),
            'automatic': result['value'].get('automatic', False),
            'driver_int': driver_id,
            'warehouse_user': warehouse_user or uid,
            'carrier_tracking_ref': tracking,
            'weight_hand': peso,
            'currency_id': picking.company_id.currency_id.id,
            'number_of_packages': number_of_package,
            'journal_id': journal_id,
        }
        cur_id = self.get_currency_id(cr, uid, picking)
        if cur_id:
            invoice_vals['currency_id'] = cur_id
        if journal_id:
            invoice_vals['journal_id'] = journal_id
        return invoice_vals

    def action_invoice_create(self, cr, uid, ids, journal_id=False, group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        if context is None:
            context = {}
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        wf_service = netsvc.LocalService("workflow")
        invoices_group = {}
        res = {}
        inv_type = type

        if group:
            pick_id = self.browse(cr, uid, ids[0])
            partner = pick_id.partner_id
            invoice_vals = self._prepare_invoice(cr, uid, pick_id, partner, inv_type, journal_id, context=context)
            invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
            invoice = invoice_obj.browse(cr, uid, invoice_id)
            for picking in self.browse(cr, uid, ids, context=context):
                for move_line in picking.move_lines:
                    if move_line.state == 'cancel':
                        continue
                    if move_line.scrapped:
                        continue
                    vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                                      invoice.id, invoice_vals, context=context)
                    if vals:
                        invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=None)
                        self._invoice_line_hook(cr, uid, move_line, invoice_line_id)
                invoice_obj.button_compute(cr, uid, [invoice.id], context=context,
                                           set_total=(inv_type in ('in_invoice', 'in_refund')))
                self.write(cr, uid, [picking.id], {'invoice_state': 'invoiced'}, context=context)
                self._invoice_hook(cr, uid, picking, invoice.id)
            res[picking.id] = invoice.id
            self.create_cost_carrier(cr, uid, res, type, context)
            invoice_ids = res.values()
        else:
            for picking in self.browse(cr, uid, ids, context=context):
                if picking.invoice_state != '2binvoiced':
                    continue
                partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
                if not partner:
                    raise osv.except_osv(_('Error, no partner !'),
                                         _('Please put a partner on the picking list if you want to generate invoice.'))

                if not inv_type:
                    inv_type = self._get_invoice_type(picking)
                else:
                    invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                    invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                    invoices_group[partner.id] = invoice_id
                res[picking.id] = invoice_id
                for move_line in picking.move_lines:
                    if move_line.state == 'cancel':
                        continue
                    if move_line.scrapped:
                        # do no invoice scrapped products
                        continue
                    vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                                      invoice_id, invoice_vals, context=context)
                    if vals:
                        invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=None)
                        self._invoice_line_hook(cr, uid, move_line, invoice_line_id)
                invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                                           set_total=(inv_type in ('in_invoice', 'in_refund')))
                self.write(cr, uid, [picking.id], {'invoice_state': 'invoiced'}, context=context)
                self._invoice_hook(cr, uid, picking, invoice_id)
            self.create_cost_carrier(cr, uid, res, type, context)
            invoice_ids = res.values()
        for id in invoice_ids:
            inv = invoice_obj.browse(cr, uid, id, context)
            if (inv.type in ('out_invoice', 'out_refund') or (inv.type == 'in_invoice' and inv.journal_id.type ==
                                                              'purchase_liquidation')) and (inv.automatic or inv.pre_printer):
                wf_service.trg_validate(uid, 'account.invoice', id, 'invoice_open', cr)
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
            'invoice_ids': [[6, 0, invoice_ids]]
            }, context=context)
        return res

    def get_prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
                                 invoice_vals, context=None):
        """ Builds the dict containing the values for the invoice line
            @param group: True or False
            @param picking: picking object
            @param: move_line: move_line object
            @param: invoice_id: ID of the related invoice
            @param: invoice_vals: dict used to created the invoice
            @return: dict that will be used to create the invoice line
        """
        if group:
            name = (picking.name or '') + '-' + move_line.name
        else:
            name = move_line.name
        origin = move_line.picking_id.name or ''
        if move_line.picking_id.origin:
            origin += ':' + move_line.picking_id.origin

        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            account_id = move_line.product_id.product_tmpl_id.property_account_income.id
            if not account_id:
                account_id = move_line.product_id.categ_id.property_account_income_categ.id
        else:
            account_id = move_line.product_id.product_tmpl_id.property_account_expense.id
            if not account_id:
                account_id = move_line.product_id.categ_id.property_account_expense_categ.id

        if not account_id:
            raise osv.except_osv(_('Error'),
                                 _('El producto no tiene definida una cuenta de contable para ingreso de inventario!'))
        account = self.pool.get('account.account').browse(cr, uid, account_id)
        if account.company_id.id != picking.company_id.id:
            account_id = self.pool.get('account.account').search(cr, uid, [('code', '=', account.code),
                                                                           ('company_id', '=', picking.company_id.id)])[0]
        if invoice_vals['fiscal_position']:
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = False
        if move_line.product_qty >= move_line.product_uos_qty:
            qty = move_line.product_qty
            uos_id = move_line.product_uom and move_line.product_uom.id
        elif move_line.product_qty < move_line.product_uos_qty:
            qty = move_line.product_qty > move_line.product_uos_qty
            uos_id = move_line.product_uos and move_line.product_uos.id        
        if not uos_id and invoice_vals['type'] in ('out_invoice', 'out_refund'):
            uos_id = move_line.product_uom.id or move_line.product_id.uom_id.id
        discount = self._get_discount_invoice(cr, uid, move_line)
        offer = self._get_offer_invoice(cr, uid, move_line)
        price_product = self._get_price_original(cr, uid, move_line)
        p_net = price_product * (1-(discount*0.01)) * (1-(offer*0.01))
        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            price_unit = self._get_price_unit_invoice(cr, uid, move_line, invoice_vals['type'])
        else:
            price_unit = price_product
        taxes = self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type'])
        account_tax_obj = self.pool.get('account.tax')
         
        if taxes:
            amount_iva = 0.00
            for t in taxes:
                tax_code = account_tax_obj.browse(cr, uid, t)
                if tax_code.ref_base_code_id.tax_type == 'vat':
                    if discount == 0.00 and offer == 0.00:
                        amount_iva += float('%.3f' % ((price_unit)))*tax_code.amount
                    else:
                        price_unit = p_net
                        amount_iva += float('%.3f' % ((price_unit)))*tax_code.amount
                amount_iva = amount_iva
        else:
            amount_iva = 0.00
        price_subtotal = (p_net*qty)
        if move_line.purchase_line_id.product_id: 
            product_id = move_line.purchase_line_id.product_id.id
        elif move_line.product_id:
            product_id = move_line.product_id.id
        else:
            product_id = False
         
        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'account_id': account_id,
            'price_unit': float('%.6f' % (price_unit)),
            'price_iva': (float('%.6f' % (price_unit + amount_iva))) or 0.0,
            'iva_value': float('%.3f' % (amount_iva *qty)) or 0.0,
            'quantity': qty,
            'product_id':  product_id,
            'price_product': float('%.6f' % (price_product)),
            'price_subtotal': float('%.6f' % (price_subtotal)),
            'discount': float('%.6f' % (discount)),
            'offer': float('%.6f' % (offer)),
            'uos_id': uos_id,
            'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type']))],
            'account_analytic_id': move_line.purchase_line_id.account_analytic_id and move_line.purchase_line_id.account_analytic_id.id or False,
            'purchase_line_id': move_line.purchase_line_id and move_line.purchase_line_id.id or False,
            'department_id': move_line.purchase_line_id.department_id and move_line.purchase_line_id.department_id.id or False,
            'cost_journal': move_line.purchase_line_id.cost_journal and move_line.purchase_line_id.cost_journal.id or False
        }

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
        return self.get_prepare_invoice_line(cr, uid, group, picking, move_line, invoice_id, invoice_vals, context)

    def create_cost_carrier(self, cr, uid, result, type, context=None):
        invoice_obj = self.pool.get('account.invoice')
        picking_obj = self.pool.get('stock.picking')
        carrier_obj = self.pool.get('delivery.carrier')
        grid_obj = self.pool.get('delivery.grid')
        invoice_line_obj = self.pool.get('account.invoice.line')
        picking_ids = result.keys()
        invoice_ids = result.values()
        invoices = {}
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context=context):
                invoices[invoice.id] = invoice

        for picking in picking_obj.browse(cr, uid, picking_ids, context=context):
            if not picking.carrier_id:
                continue
            grid_id = carrier_obj.grid_get(cr, uid, [picking.carrier_id.id], picking.address_id.id, context=context)
            if not grid_id:
                raise osv.except_osv(_('Warning'),
                                     _('The carrier %s (id: %d) has no delivery grid!')
                                     % (picking.carrier_id.name, picking.carrier_id.id))
            invoice = invoices[result[picking.id]]
            price = grid_obj.get_price_from_picking(cr, uid, grid_id,
                                                    invoice.amount_untaxed, picking.weight, picking.volume,
                                                    context=context)
            if not picking.carrier_id.product_id:
                raise osv.except_osv(_('Error'),
                                     _('the carrier does not have a product selected by default!'))
            account_id = picking.carrier_id.product_id.product_tmpl_id.property_account_income.id
            if not account_id:
                account_id = picking.carrier_id.product_id.categ_id.property_account_income_categ.id

                taxes = picking.carrier_id.product_id.taxes_id

            if price > 0:
                partner_id = picking.address_id.partner_id and picking.address_id.partner_id.id or False
                taxes_ids = [x.id for x in picking.carrier_id.product_id.taxes_id]
                if partner_id:
                    partner = picking.address_id.partner_id
                    taxes = picking.carrier_id.product_id.taxes_id
                    account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, partner.property_account_position, account_id)
                    taxes_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, partner.property_account_position, taxes)

                invoice_line_obj.create(cr, uid, {'name': picking.carrier_id.name,
                                                  'invoice_id': invoice.id,
                                                  'uos_id': picking.carrier_id.product_id.uom_id.id or picking.carrier_id.product_id.uos_id.id,
                                                  'product_id': picking.carrier_id.product_id.id,
                                                  'account_id': account_id,
                                                  'price_unit': price,
                                                  'discount': 0,
                                                  'price_total': price,
                                                  'quantity': 1,
                                                  'invoice_line_tax_id': [(6, 0, taxes_ids)],
                                                  'account_analytic_id': False,
                                                  })
                invoice_obj.button_compute(cr, uid, invoice_ids, context=context, set_total=(type in ('in_invoice', 'in_refund')))
        return True

    def delivery_annulled(self, cr, uid, ids, context=None):
        delivery = self.pool.get('stock.delivery')
        delete = []
        for i in ids:
            delivery_se = delivery.search(cr, uid, [('picking_id', '=', i)])
            delivery_id = delivery.browse(cr, uid, delivery_se)
            if(delivery_id):
                delete.append(delivery_id[0].id)
            for del_id in delivery_id:
                self.pool.get('stock.delivery').write(cr, uid, [del_id.id], {'state': 'cancel'})
                self.pool.get('stock.picking').write(cr, uid, [del_id.picking_id.id], {'delivery_status': 'draft'})
        return True

    def unlink(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state in ['done', 'cancel']:
                raise osv.except_osv(_('Error'), _('You cannot remove the picking which is in %s state !') % (pick.state,))
            else:
                ids2 = [move.id for move in pick.move_lines]
                ctx = context.copy()
                ctx.update({'call_unlink': True})
                if pick.state != 'draft':
                    # Cancelling the move in order to affect Virtual stock of product
                    move_obj.action_cancel(cr, uid, ids2, ctx)
                # Removing the move
                move_obj.unlink(cr, uid, ids2, ctx)
        cr.execute("""update stock_picking set  write_date =now(), state ='cancel', active=False where id in %s""", (tuple(ids),))
        return True

    def print_delivery_guide(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        delivery_obj = self.pool.get('stock.delivery')
        for picking in self.browse(cr, uid, ids, context=context):
            delivery_ids = delivery_obj.search(cr, uid, [('picking_id', '=', picking.id), ('state', '!=', 'cancel')])
            delivery = delivery_obj.browse(cr, uid, delivery_ids[-1])
            nb_print = delivery.nb_print + 1
            self.write(cr, uid, [picking.id], {'nb_print_dn': nb_print})
            delivery_obj.write(cr, uid, [delivery.id], {'nb_print': nb_print})
            if delivery:
                data = {}
                data['model'] = 'stock.delivery'
                data['ids'] = [delivery.id]
                context['active_id'] = delivery.id
                context['active_ids'] = [delivery.id]
                return {'type': 'ir.actions.report.xml',
                        'report_name': 'delivery_guide_not_invoiced',
                        'datas': data,
                        'context': context,
                        'nodestroy': True,
                        }
            return True

    def write(self, cr, uid, ids, vals, context=None):
        stock_obj = self.pool.get('stock.move')
        if vals:
            partner_id = vals.get('partner_id', False)
        else:
            partner_id = self.browse(cr, uid, ids[0]).partner_id
        if not partner_id:
            for picking in self.browse(cr, uid, ids):
                if not picking.partner_id or (picking.type == 'internal' and picking.address_id and not picking.partner_id):
                    vals['partner_id'] = picking.company_id.partner_id.id
                if picking.type == 'in' and picking.partner_id.id != picking.company_id.partner_id.id:
                    if not picking.invoice_ids:
                        vals['invoice_state'] = '2binvoiced'
                if picking.move_lines and picking.internal_out:
                    for m in picking.move_lines:
                        if m.location_id != picking.location_id:
                            stock_obj.write(cr, uid, [m.id], {'location_id': picking.location_id.id})
        return super(stock_picking, self).write(cr, uid, ids, vals, context=context)

stock_picking()
