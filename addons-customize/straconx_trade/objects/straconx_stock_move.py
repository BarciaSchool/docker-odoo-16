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

import time
from osv import fields, osv
from tools.translate import _
import netsvc
import decimal_precision as dp


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line',),
        'price_unit_trade': fields.float('Unit Price Trade', digits_compute=dp.get_precision('Trade')),
        'qty_receive': fields.float('Qty Receive'),
        'authorized': fields.boolean('authorized', required=False),
        'flag': fields.boolean('flag', required=False),
        'debit_note_id': fields.many2one('account.debit.note', 'Debit Note'),
    }
    _defaults = {
        'invoice_line_id': False,
        'authorized': True,
        'flag': False
    }

    def onchange_qty_receive(self, cr, uid, ids, qty=None, qty_receive=None, context=None):
        values = {}
        if not (qty and qty_receive):
            return None
        if qty != qty_receive:
            values['authorized'] = False
        else:
            values['authorized'] = True
        return {'value': values}

    # @profile
    def _get_accounting_data_for_valuation(self, cr, uid, move, context=None):
        """
        Return the accounts and journal to use to post Journal Entries for the real-time
        valuation of the move.

        :param context: context dictionary that can explicitly mention the company to consider via the 'force_company' key
        :raise: osv.except_osv() is any mandatory account or journal is not defined.
        """
        product_obj = self.pool.get('product.product')
        accounts = product_obj.get_product_accounts(cr, uid, move.product_id.id, context)
        if move.invoice_line_id and move.location_dest_id.usage != 'transit':
            acc_src = move.invoice_line_id.account_id.id
        elif move.location_id.valuation_out_account_id and not move.location_id.usage == 'production':
            acc_src = move.location_id.valuation_out_account_id.id
        elif move.location_dest_id.usage == 'transit':
            acc_src = accounts['property_stock_transit_account_id']
        elif move.location_dest_id.usage == 'production':
            acc_src = move.location_dest_id.valuation_out_account_id.id
            if not acc_src:
                raise osv.except_osv(_('¡Error!'), _('No existe las cuentas de movimientos configuradas para la bodega %s') %
                                     (move.location_dest_id.name))
        else:
            acc_src = accounts['stock_account_input']

        if move.invoice_line_id and move.location_dest_id.usage != 'transit':
            acc_dest = move.invoice_line_id.account_id.id
        elif move.location_dest_id.valuation_in_account_id and not move.location_dest_id.usage == 'production':
            acc_dest = move.location_dest_id.valuation_in_account_id.id
        elif move.location_id.usage == 'transit':
            acc_dest = accounts['property_stock_transit_account_id']
        else:
            acc_dest = accounts['stock_account_output']

        if move.invoice_line_id and move.location_dest_id.usage != 'transit':
            acc_variation = accounts['stock_account_input']
        elif move.location_dest_id.usage in ('production'):
            acc_variation = move.location_dest_id.valuation_in_account_id.id
        elif move.location_id.usage in ('production'):
            acc_variation = move.location_id.valuation_out_account_id.id
        else:
            acc_variation = accounts.get('property_stock_valuation_account_id', False)

        journal_id = accounts['stock_journal']

        if acc_dest == acc_variation and not move.location_dest_id.usage == 'production':
            raise osv.except_osv(_('Error!'),
                                 _('Can not create Journal Entry, Output Account defined on this product and Variant account on category '
                                   'of this product are same.'))

        if acc_src == acc_variation and not move.location_dest_id.usage == 'production':
            raise osv.except_osv(_('Error!'),  _('Can not create Journal Entry, Input Account defined on this product and Variant account on category'
                                                 ' of this product are same.'))
        if not acc_src:
            raise osv.except_osv(_('Error!'),  _('There is no stock input account defined for this product or its category: "%s" (id: %d)') %
                                 (move.product_id.name, move.product_id.id,))
        if not acc_dest:
            raise osv.except_osv(_('Error!'),  _('There is no stock output account defined for this product or its category: "%s" (id: %d)') %
                                 (move.product_id.name, move.product_id.id,))
        if not journal_id:
            raise osv.except_osv(_('Error!'), _('There is no journal defined on the product category: "%s" (id: %d)') %
                                 (move.product_id.categ_id.name, move.product_id.categ_id.id,))
        if not acc_variation:
            raise osv.except_osv(_('Error!'), _('There is no inventory variation account defined on the product category: "%s" (id: %d)') %
                                 (move.product_id.categ_id.name, move.product_id.categ_id.id,))
        return journal_id, acc_src, acc_dest, acc_variation

    def _create_account_move_line(self, cr, uid, move, dest_account_id, src_account_id, reference_amount, reference_currency_id, context=None):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given stock move.
        """
        # prepare default values considering that the destination accounts have the reference_currency_id as their main currency
        partner_id = (move.picking_id.address_id and move.picking_id.address_id.partner_id and move.picking_id.address_id.partner_id.id) or False
        if move.invoice_line_id:
            partner_id = move.invoice_line_id.invoice_id.partner_id.id or False
        if move.picking_id.type == 'out':
            debit_account = src_account_id
            credit_account = dest_account_id
        else:
            debit_account = dest_account_id
            credit_account = src_account_id

        debit_line_vals = {'name': move.name,
                           'product_id': move.product_id and move.product_id.id or False,
                           'quantity': move.product_qty,
                           'reference': move.picking_id and move.picking_id.name or False,
                           'date': time.strftime('%Y-%m-%d'),
                           'partner_id': partner_id,
                           'debit': reference_amount,
                           'account_id': debit_account
                           }
        amount_duty = 0
        credit = []
        if move.invoice_line_id:
            amount_duty = move.invoice_line_id.amount_tax_duty * move.invoice_line_id.quantity
            credit_line_vals = {'name': move.name,
                                'product_id': move.product_id and move.product_id.id or False,
                                'quantity': move.product_qty,
                                'reference': move.picking_id and move.picking_id.name or False,
                                'date': time.strftime('%Y-%m-%d'),
                                'partner_id': partner_id,
                                'credit': reference_amount-amount_duty,
                                'account_id': credit_account
                                }
            duty = {
                'name': move.name,
                'product_id': move.product_id and move.product_id.id or False,
                'quantity': move.product_qty,
                'reference': move.picking_id and move.picking_id.name or False,
                'date': time.strftime('%Y-%m-%d'),
                'partner_id': partner_id,
                'credit': amount_duty,
                'account_id': move.invoice_line_id.invoice_id.trade_id1.company_id.property_account_duty_account.id or None,
                }
        else:
            credit_line_vals = {'name': move.name,
                                'product_id': move.product_id and move.product_id.id or False,
                                'quantity': move.product_qty,
                                'reference': move.picking_id and move.picking_id.name or False,
                                'date': time.strftime('%Y-%m-%d'),
                                'partner_id': partner_id,
                                'credit': reference_amount,
                                'account_id': credit_account
                                }
        # if we are posting to accounts in a different currency, provide correct values in both currencies correctly
        # when compatible with the optional secondary currency on the account.
        # Financial Accounts only accept amounts in secondary currencies if there's no secondary currency on the account
        # or if it's the same as that of the secondary amount being posted.
        account_obj = self.pool.get('account.account')
        src_acct, dest_acct = account_obj.browse(cr, uid, [src_account_id, dest_account_id], context=context)
        src_main_currency_id = src_acct.company_id.currency_id.id
        dest_main_currency_id = dest_acct.company_id.currency_id.id
        cur_obj = self.pool.get('res.currency')
        if reference_currency_id != src_main_currency_id:
            # fix credit line:
            if move.invoice_line_id:
                credit_line_vals['credit'] = cur_obj.compute(cr, uid, reference_currency_id, src_main_currency_id, reference_amount-amount_duty,
                                                             context=context)
                duty['credit'] = cur_obj.compute(cr, uid, reference_currency_id, src_main_currency_id, amount_duty, context=context)
            else:
                credit_line_vals['credit'] = cur_obj.compute(cr, uid, reference_currency_id, src_main_currency_id, reference_amount, context=context)
            if (not src_acct.currency_id) or src_acct.currency_id.id == reference_currency_id:
                if move.invoice_line_id:
                    credit_line_vals.update(currency_id=reference_currency_id, amount_currency=reference_amount-amount_duty)
                    duty.update(currency_id=reference_currency_id, amount_currency=amount_duty)
                else:
                    credit_line_vals.update(currency_id=reference_currency_id, amount_currency=reference_amount)
        if reference_currency_id != dest_main_currency_id:
            # fix debit line:
            debit_line_vals['debit'] = cur_obj.compute(cr, uid, reference_currency_id, dest_main_currency_id, reference_amount, context=context)
            if (not dest_acct.currency_id) or dest_acct.currency_id.id == reference_currency_id:
                debit_line_vals.update(currency_id=reference_currency_id, amount_currency=reference_amount)
        if move.invoice_line_id:
            return [(0, 0, debit_line_vals), (0, 0, credit_line_vals), (0, 0, duty)]
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]

    # @profile
    def _get_reference_accounting_values_for_valuation(self, cr, uid, move, context=None):
        """
        Return the reference amount and reference currency representing the inventory valuation for this move.
        These reference values should possibly be converted before being posted in Journals to adapt to the primary
        and secondary currencies of the relevant accounts.
        """
        product_uom_obj = self.pool.get('product.uom')

        # by default the reference currency is that of the move's company
        if move.company_id:
            cr.execute("""select currency_id from res_company where id =%s """, (move.company_id.id,))
            currency = cr.fetchall()
            if currency:
                reference_currency_id = currency[0][0]
#        reference_currency_id = move.company_id.currency_id.id
        reference_amount = 0.00

        default_uom = move.product_id.uom_id.id
        qty = product_uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, default_uom)
        if move.product_id.cost_method == 'average' and move.product_id and move.picking_id.international:
            reference_amount = qty * move.price_unit_trade
        elif move.product_id.cost_method == 'average' and move.product_id:
            if move.product_id.standard_price:
                reference_amount = qty * move.product_id.standard_price

        else:
            if context is None:
                context = {}
            currency_ctx = dict(context, currency_id=move.company_id.currency_id.id)
            amount_unit = move.product_id.price_get('standard_price', context=currency_ctx)[move.product_id.id]
            reference_amount = amount_unit * qty

        return reference_amount, reference_currency_id

stock_move()