# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2011-present STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import time
from tools.translate import _

sql = """SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""


class stock_invoice_incoming(osv.osv_memory):
    _name = "stock.invoice.incoming"

    def _get_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}

        model = context.get('active_model')
        if not model or model != 'stock.picking':
            return []

        model_pool = self.pool.get(model)
        journal_obj = self.pool.get('account.journal')
        res_ids = context and context.get('active_ids', [])
        vals = []
        browse_picking = model_pool.browse(cr, uid, res_ids, context=context)
        journal_type = []
        for pick in browse_picking:
            if not pick.move_lines:
                continue
            src_usage = pick.move_lines[0].location_id.usage
            dest_usage = pick.move_lines[0].location_dest_id.usage
            type = pick.type
            if type == 'out' and dest_usage == 'supplier':
                journal_type = ['purchase_refund']
            elif type == 'out' and dest_usage == 'customer':
                journal_type = ['sale']
            elif type == 'in' and src_usage == 'supplier':
                journal_type = ['purchase', 'purchase_liquidation']
            elif type == 'in' and src_usage == 'customer':
                journal_type = ['sale_refund']
            else:
                journal_type = ['sale']

            value = journal_obj.search(cr, uid, [('type', 'in', journal_type)])
            for jr_type in journal_obj.browse(cr, uid, value, context=context):
                t1 = jr_type.id, jr_type.name
                if t1 not in vals:
                    vals.append(t1)
        if not vals:
            raise osv.except_osv(_('Warning !'), _('Either there are no moves linked to the picking or Accounting Journals are misconfigured!'))
        return vals

    _columns = {
        'type_journal': fields.selection([('purchase', 'Purchase Invoice'),
                                          ('purchase_liquidation', 'Purchase Liquidation')],
                                         'Type Document', select=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=False),
        'invoice_number_in': fields.char('Invoice Number', size=17, required=False, help="Unique number of the invoice."),
        'authorization_purchase': fields.many2one('sri.authorization', 'Authorization'),
        'partner_address_id': fields.many2one('res.partner.address', 'Address Partner'),
        'shop_id': fields.many2one('sale.shop', 'Shop'),
        'printer_id': fields.many2one('printer.point', 'Printer Point', domain="[('shop_id', '=', shop_id)]", readonly=True),
        'tpurchase': fields.selection([('purchase', 'Purchase'), ('expense', 'Expense')], 'Purchase type', select=True),
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32),
        'carrier_id': fields.many2one("delivery.carrier", "Carrier", readonly=True),
        'flag': fields.boolean('flag', required=False),
        'invoice_date2': fields.datetime('Invoiced date'),
        'authorization': fields.char('Autorizacion', size=37),
        'access_key': fields.char('Clave de Acceso', size=50),
        'weight_hand': fields.float('Weight'),
        'group': fields.boolean("Group by partner"),
        'number_of_packages': fields.integer('Number of Packages'),
        'warehouse_user': fields.many2one('res.users', 'Warehouse User', domain=[('is_warehouse_user', '=', True)]),
        'origin': fields.char('Origin', size=64, help="Reference of the document that produced this picking.", select=True),
        'picking_id': fields.many2one('stock.picking', 'Picking', required=True),
        'electronic': fields.boolean('electronic')
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(stock_invoice_incoming, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')
        count = 0
        active_ids = context.get('active_ids', [])
        for pick in pick_obj.browse(cr, uid, active_ids, context=context):
            if pick.invoice_state != '2binvoiced':
                count += 1
        if len(active_ids) == 1 and count:
            raise osv.except_osv(_('Warning !'), _('This picking list does not require invoicing.'))
        if len(active_ids) == count:
            raise osv.except_osv(_('Warning !'), _('None of these picking lists require invoicing.'))
        return res

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = {}
        objs = self.pool.get(context['active_model']).browse(cr, uid, context['active_ids'])
        if 'value' not in context.keys():
            for pick in objs:
                res['type_journal'] = 'purchase'
                res['invoice_date2'] = time.strftime('%Y-%m-%d %H:%M:%S')
                res['flag'] = pick.more_information
                res['tpurchase'] = 'purchase'
                res['picking_id'] = pick.id
                res['shop_id'] = pick.shop_id.id
                res['partner_address_id'] = pick.address_id.id
                res['invoice_number_in'] = None
                res['origin'] = pick.origin
                cr.execute(sql, (pick.shop_id.id, 'purchase'))
                result = cr.fetchall()
                if result:
                    res['journal_id'] = result[0][0]
        else:
            res = context['value']
        return res

    def onchange_type(self, cr, uid, ids, type_document, context=None):
        if context is None:
            context = {}
        res = {}
        domain = {}
        pick = self.pool.get('stock.picking').browse(cr, uid, context.get('active_id', None))
        if type_document:
            dom = [('type', '=', type_document)]
            journal = self.pool.get('account.journal').search(cr, uid, dom,)
            cr.execute(sql, (pick.shop_id.id, type_document))
            result = cr.fetchall()
            if result:
                res['journal_id'] = result[0][0]
            else:
                res['journal_id'] = journal and journal[0] or None
            domain['journal_id'] = [('id', 'in', journal)]
        return {'value': res, 'domain': domain}

    def onchange_number_in(self, cr, uid, ids, number, type=None, shop_id=None, printer_id=None, journal=None, company=False, date=None, context=None):
        if context is None:
            context = {}
        result = self.pool.get('account.invoice').onchange_number(cr, uid, ids, number, 'in_invoice', shop_id, printer_id, journal, False, date, context=context)        
        return result

    def onchange_auth_purchase(self, cr, uid, ids, auth=None, number=None, address=None, journal=None, context=None):
        if context is None:
            context = {}
        result = self.pool.get('account.invoice').onchange_auth_purchase(cr, uid, ids, auth, number, address, journal, context=context)
        return result

    def open_in_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_ids = []
        data_pool = self.pool.get('ir.model.data')
        res = self.create_in_invoice(cr, uid, ids, context=context)
        invoice_ids += res.values()
        inv_type = context.get('inv_type', False)
        journal_type = context.get('journal_type', False)
        action_model = False
        action = {}
        if not invoice_ids:
            raise osv.except_osv(_('Error'), _('No Invoices were created'))
        if inv_type == "in_invoice" and journal_type == "purchase":
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree2")
        elif inv_type == "in_invoice" and journal_type == "purchase_liquidation":
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'straconx_invoice', "action_straconx_purchase_liquidation_invoice")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str, invoice_ids))+"])]"
        return action

    def create_in_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        picking_pool = self.pool.get('stock.picking')
        incomingdata_browse = self.browse(cr, uid, ids, context)[0]
        incomingdata_obj = self.read(cr, uid, ids, ['journal_id', 'group', 'invoice_date2', 'invoice_date', 'type', 'invoice_number_in', 'electronic',
                                                    'authorization', 'access_key', 'authorization_purchase', 'tpurchase', 'expiration_date',
                                                    'carrier_tracking_ref', 'weight_hand', 'number_of_packages', 'warehouse_user', 'driver_int'])
        context['invoice_date2'] = incomingdata_browse.invoice_date2
        context['invoice_date'] = incomingdata_browse.invoice_date2[:10]
        active_ids = context.get('active_ids', [])
        active_picking = picking_pool.browse(cr, uid, context.get('active_id', False), context=context)

        inv_type = picking_pool._get_invoice_type(active_picking)
        journal_id = incomingdata_browse.journal_id.id
        context['inv_type'] = 'in_invoice'
        context['journal_type'] = incomingdata_browse.journal_id.type
        context['tpurchase'] = incomingdata_browse.tpurchase or None
        if incomingdata_browse.journal_id.type == 'purchase':
            context['invoice_number_in'] = incomingdata_browse.invoice_number_in
            context['authorization_purchase'] = incomingdata_browse.authorization_purchase.id or None
            context['electronic'] = incomingdata_browse.electronic
            context['authorization'] = incomingdata_browse.authorization
            context['access_key'] = incomingdata_browse.access_key
        elif incomingdata_browse.journal_id.type == 'purchase_liquidation':
            context['shop_id'] = incomingdata_browse.shop_id.id or None
            context['printer_id'] = incomingdata_browse.printer_id.id or None
            context['origin'] = incomingdata_browse.origin
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
                                                 journal_id=journal_id,
                                                 group=incomingdata_obj[0]['group'],
                                                 type='in_invoice',
                                                 context=context)
        return res

stock_invoice_incoming()
