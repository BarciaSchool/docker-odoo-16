# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
#
##############################################################################

import os, time
#from datetime import datetime
import datetime as dt 
from dateutil.relativedelta import relativedelta
from datetime import datetime
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc
from account_voucher import account_voucher


class account_invoice(osv.osv):

    _inherit = 'account.invoice'

    def print_invoice_electronic(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            if invoice.electronic:
                nb_print = invoice.nb_print + 1
                self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
                if invoice:
                    data = {}
                    data['model'] = 'account.invoice'
                    data['ids'] = ids
                    context['active_id']=invoice.id
                    context['active_ids']=ids
                    return {
                       'type': 'ir.actions.report.xml',
                       'report_name': 'electronic.invoice.report.id',
                       'datas' : data,
                       'context': context,
                       'nodestroy': True,
                       }
                return True
            
            elif invoice.automatic:
                nb_print = invoice.nb_print + 1
                self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
                if invoice:
                    data = {}
                    data['model'] = 'account.invoice'
                    data['ids'] = ids
                    context['active_id']=invoice.id
                    context['active_ids']=ids
                    return {
                       'type': 'ir.actions.report.xml',
                       'report_name': 'pentaho.invoice.report.id',
                       'datas' : data,
                       'context': context,
                       'nodestroy': True,
                       }
                return True

            else:
                nb_print = invoice.nb_print + 1
                self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
                if invoice:
                    data = {}
                    data['model'] = 'account.invoice'
                    data['ids'] = ids
                    context['active_id']=invoice.id
                    context['active_ids']=ids
                    return {
                       'type': 'ir.actions.report.xml',
                       'report_name': 'invoice_report_id',
                       'datas' : data,
                       'context': context,
                       'nodestroy': True,
                       }
                return True 

account_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

