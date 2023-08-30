# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
##############################################################################

from osv import osv, fields
from tools.translate import _
import time


class open_statement(osv.osv_memory):
    _name = 'open.statement'
    _description = 'Open Statements'

    _columns = {'date': fields.datetime('Date Open Cash', required=True),
                'company_id': fields.many2one('res.company', 'Company'),
                'shop_id': fields.many2one('sale.shop', 'Shop'),
                'printer_id': fields.many2one('printer.point', 'Printer'),
                }

    _defaults = {'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                 'company_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id,
                 'shop_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).shop_id.id,
                 'printer_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).cash_box_default_id.id
                 }

    def open_statement(self, cr, uid, ids, context=None):
        """
             Open the statements
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Blank Directory
        """

        ###########################################################################################
        browse_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wizard = self.browse(cr, uid, ids[0])
        company_id = wizard.company_id.id
        shop_id = wizard.shop_id.id
        printer_id = wizard.printer_id.id
        date = wizard.date
        data = {}
        mod_obj = self.pool.get('ir.model.data')
        statement_obj = self.pool.get('account.bank.statement')
        sequence_obj = self.pool.get('ir.sequence')
        printer_obj = self.pool.get('printer.point')
        shop_obj = self.pool.get('sale.shop')
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}
        journal_type = context.get('journal_type', 'moves')
        name = context.get('name', 'Cash Register')
        if not browse_user.is_cashier:
            raise osv.except_osv(_('Message'), _('You do not have permission to open a %s.') % (name))
        if not browse_user.cash_box_default_id:
            raise osv.except_osv(_('Message'), _('The user do not have cash box default to open a %s.') % (name))
#        printer_ids= browse_user.cash_box_default_id.id
        journal_ids = journal_obj.search(cr, uid, [('type', '=', journal_type), ('company_id', '=', company_id)], context=context)
        if not journal_ids:
            raise osv.except_osv(_('Message'), _('You must define a journal type %s') % (journal_type))
        period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', company_id),
                                                                     ('date_start', '<=', date[:10]), ('date_stop', '>=', date[:10])])[0]
        if printer_id:
            pt_id = printer_obj.browse(cr, uid, printer_id)
            if not pt_id.type:
                auth_id = self.pool.get('sri.authorization.line').search(cr, uid, [('printer_id', '=', printer_id),('state', '=', True)])
                if not auth_id:
                    raise osv.except_osv(_('Message'), _('El punto de impresión que desea abrir no tiene autorizaciones del SRI activas'))

        for journal in journal_obj.browse(cr, uid, journal_ids, context=context):
            ids = statement_obj.search(cr, uid, [('state', 'in', ('open', 'draft')), ('user_id', '=', uid), ('company_id', '=', company_id),
                                                 ('journal_id', '=', journal.id)], context=context)
            if len(ids):
                raise osv.except_osv(_('Message'),
                                     _('You can not open a Cashbox for "%s".\nPlease close its related cash register.') % (journal.name))

            number = ''
            if journal.sequence_id:
                number = sequence_obj.next_by_id(cr, uid, journal.sequence_id.id)
            else:
                number = sequence_obj.get(cr, uid, 'account.cash.statement')

            data.update({'journal_id': journal.id,
                         'period_id': period_id,
                         'company_id': company_id,
                         'date': date,
                         'user_id': uid,
                         'state': 'draft',
                         'name': number,
                         'collect': browse_user.collect,
                         'pay': browse_user.pay,
                         'shop_id': shop_id,
                         'printer_id':  printer_id,
                         })
            statement_id = statement_obj.create(cr, uid, data, context=context)

        tree_res = mod_obj.get_object_reference(cr, uid, 'account', 'view_bank_statement_tree')
        tree_id = tree_res and tree_res[1] or False
        form_res = mod_obj.get_object_reference(cr, uid, 'account', 'view_bank_statement_form2')
        form_id = form_res and form_res[1] or False
        search_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_account_bank_statement_filter')

        return {
            'domain': "[('state', '=', 'draft'),('user_id', '=', " + str(uid) + "), ('journal_id', '=', " + str(journal.id) + "),"
            "('journal_id.type', '=' , '" + journal_type + "')]",
            'name': name,
            'view_type': 'form',
            'view_mode': 'form,tree',
            'search_view_id': search_id and search_id[1] or False,
            'res_model': 'account.bank.statement',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'context': {'search_default_open': 1},
            'type': 'ir.actions.act_window'
        }

    def onchange_statement_shop(self, cr, uid, ids, company=None, shop=None, context=None):
        if context is None:
            context = {}
        values = {'value': {}, 'domain': {}}
        box_ids = []
        box_id = []
        shop_id = self.pool.get('sale.shop').browse(cr, uid, shop)
        boxes_ids = self.pool.get('printer.point').search(cr, uid, [('shop_id', '=', shop)])
        for s in boxes_ids:
            box_ids.append(s)
            box_id = self.pool.get('printer.point').search(cr, uid, [('id', 'in', box_ids), ('shop_id', '=', shop_id.id)])
            if not box_id:
                raise osv.except_osv(_('Message'), _('No existe cajas asignadas para esta tienda %s.') % (shop_id.name))
            else:
                cash = box_id[0]
                values['value']['printer_id'] = cash
        domain = {'printer_id': [('id', 'in', box_id)]}
        values['domain'] = domain
        return values

open_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
