# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
##############################################################################
from osv import fields, osv
from tools.translate import _


def _code_get_type(self, cr, uid, context={}):
    cr.execute('select code, name from account_journal_type')
    return cr.fetchall()

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'type': fields.selection(_code_get_type, 'Code',size=32, required=True,
                                 help="Select 'Sale' for customer invoices journals."\
                                 " Select 'Purchase' for supplier invoices journals."\
                                 " Select 'Cash' or 'Bank' for journals that are used in customer or supplier payments."\
                                 " Select 'General' for miscellaneous operations journals."\
                                 " Select 'Opening/Closing Situation' for entries generated for new fiscal years."),
            }
account_journal()

class account_analytic_journal(osv.osv):
    _inherit = 'account.analytic.journal'
    _columns = {
        'default': fields.boolean('Default', help="If the active field is set to False, it will allow you to hide the analytic journal without removing it."),
        'code': fields.char('Journal Code', size=10),
    }
    _defaults = {
        'default': False,
    }

    def create(self, cr, uid, vals, context={}):
        if vals.get('default', False):
            adef = self.search(cr, uid, [('default', '=', True)])
            if adef:
                default_journal = self.browse(cr, uid, adef[-1]).name
                raise osv.except_osv(_('¡Aviso!'), _("Ya existe %s como Diario de Costo Predeterminado") % (default_journal))
        return super(account_analytic_journal, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('default', False):
            adef = self.search(cr, uid, [('default', '=', True)])
            if adef:
                if adef[-1] != ids[-1]:
                    default_journal = self.browse(cr, uid, adef[-1]).name
                    raise osv.except_osv(_('¡Aviso!'), _("Ya existe %s como Diario de Costo Predeterminado") % (default_journal))
        return super(account_analytic_journal, self).write(cr, uid, ids, vals, context)


account_analytic_journal()
