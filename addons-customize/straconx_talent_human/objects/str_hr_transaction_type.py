# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################

from osv import fields,osv
import decimal_precision as dp

class hr_transaction_type(osv.osv):
    _name = 'hr.transaction.type'
    _columns = {
        'code': fields.char('code', required=True, size=64),
        'name': fields.char('Description', required=True, size=64),
        'debit_account_id': fields.many2one('account.account', 'Debit Account', required=False),
        'credit_account_id': fields.many2one('account.account', 'Credit Account', required=False),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'type':fields.selection([('incomes','Incomes'),('expenses','Expenses')],'type', select=True),
        'type_expense':fields.selection([('discount','Discount'),('advance','Advance'),('loans','Loans'),],'type Expense', select=True),
        'type_income':fields.selection([('extra_hours','Extra Hours'),('other','Other Income')],'type Income', select=True),
        'generate_lines_employee':fields.boolean('Generate Lines of all employee', required=False, help="If active this field, the discount generate lines for each employee. This discount are made monthly"),
        'value_extra': fields.float('% value hours extra', digits_compute=dp.get_precision('Payroll')),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'is_paid':fields.boolean('Pay with document'),
        'internal':fields.boolean('Discount Internal'),
        'collection_form':fields.selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', select=True),
        }
        
    _sql_constraints = [('name_uniq','unique(code,company_id)', 'Code of transaction must be unique'),
                        ]
    _defaults={
        'collection_form':'end_month',
        }
    
hr_transaction_type()