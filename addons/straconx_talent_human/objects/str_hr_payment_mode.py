# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved	   
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

from openerp.osv import fields, osv

class payment_mode(osv.osv):
    
    _inherit = "payment.mode"
    _columns = {
                'collect_employee':fields.boolean('Collect Employee', required=False),
                "discount_employee":fields.boolean("Discount Employee"),
                }
payment_mode()

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
              'has_discount_employee':fields.boolean("Has discount employee?"),
              }
    _defaults = {
                 'has_discount_employee':False,
                 }
    
    def print_invoice_hr_discount(self, cr, uid, ids, context=None):
        brw_self=self.browse(cr, uid,ids[0],context=context)
        OBJ_ACCOUNT_PAYMENTS=self.pool.get("account.payments")
        if(brw_self.has_discount_employee):
            srch_account_payments=OBJ_ACCOUNT_PAYMENTS.search(cr,uid,[('invoice_id','=',brw_self.id),('discount_id','!=',False)])
            if(srch_account_payments):
                brw_account_payments=OBJ_ACCOUNT_PAYMENTS.browse(cr,uid,srch_account_payments[0],context=context)
                datas = {'ids':[brw_account_payments.discount_id.id],'model':'hr.discount'}
                context['active_id']=brw_account_payments.discount_id.id
                context['active_model']='account.invoice'
                context['active_ids']=[brw_account_payments.discount_id.id]
                return {
                       'type': 'ir.actions.report.xml',
                       'report_name': 'pentaho.employee.discount',
                       'datas' : datas,
                       'context': context,
                       'nodestroy':True
                       }
            raise osv.except_osv(_("Error!"),_("No employee discount on this invoice."))
        raise osv.except_osv(_("Error!"),_("No employee discount on this invoice."))
account_invoice()

class account_payments(osv.osv):
    _inherit="account.payments"
    _columns={
              "invoice_id":fields.many2one("account.invoice","Invoice"),
              "discount_id":fields.many2one("hr.discount","Discount"),  
              }
    
account_payments()
