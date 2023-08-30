# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields,osv

class account_payment_term(osv.osv):
    _inherit = 'account.payment.term'
    _columns = {
                'default': fields.boolean('Default', help="This field is active to be chosen automatically on out refund and in refund."),
                    }
        
account_payment_term()