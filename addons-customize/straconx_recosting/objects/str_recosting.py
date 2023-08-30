# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#    This program is private software.
#
##############################################################################

from osv import osv, fields
from tools.translate import _
import psycopg2
import time
import decimal_precision as dp
    
class account_products_recosting(osv.osv):
    _name = "account.products.recosting"

    _columns = {
        'company_id': fields.many2one('res.company','Company', required=True,readonly=True),
        'date_from': fields.date('From Date', readonly=True, states={'draft':[('readonly',False)]}, select=True),
        'date_to': fields.date('To Date', readonly=True, states={'draft':[('readonly',False)]}, select=True),
        'date_process': fields.datetime('Process Date', readonly=True, states={'draft':[('readonly',False)]}, select=True),        
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'invoice_ids': fields.many2many('account.invoice', 'account_product_recosting_rel', 'recosting_id', 'invoice_id', 'Invoices',select=True,ondelete='restrict'),        
        'state': fields.selection([
            ('draft','Draft'),
            ('done','Done'),
            ],'State', select=True, readonly=True,),     
                }
    
    _defaults = {
         'state': 'draft',
         'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'migration.products', context=c),
         'user_id': lambda s, cr, u, c: u,
         'date_from':lambda *a:time.strftime('%Y-%m-%d %H:%M:%S'),
         'date_to':lambda *a:time.strftime('%Y-%m-%d %H:%M:%S'),
         'date_process':lambda *a:time.strftime('%Y-%m-%d %H:%M:%S'), 
     }

    def start_recosting(self, cr, uid, ids, context=None):
        if ids:
            for wizard_id in self.browse(cr,uid,ids):
                if wizard_id.date_from and wizard_id.date_to and wizard_id.user_id and wizard_id.company_id.id:
                    cr.execute("""select id from account_invoice where date_invoice >=%s and date_invoice <=%s and company_id=%s and state in ('open','paid') """,(wizard_id.date_from, wizard_id.date_to,wizard_id.company_id.id))
                    invoice_ids = cr.fetchall()
                    if invoice_ids:
                        for inv_id in invoice_ids:                        
                            cr.execute("""insert into account_product_recosting_rel(recosting_id, invoice_id) values(%s,%s)""",(wizard_id.id, inv_id))
                            
                    return True                    
account_products_recosting()
