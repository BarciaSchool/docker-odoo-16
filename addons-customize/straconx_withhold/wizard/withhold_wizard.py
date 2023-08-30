# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
import time
import netsvc
import re

sql="""SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo 
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""
class withhold_wizard(osv.osv_memory):

    def _total(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for ret in self.browse(cr, uid, ids, context=context):
            val = 0.0
            for line in ret.lines_ids:
                    val += line.retained_value
            res[ret.id] = val
        return res
            
    _name = 'account.withhold.wizard'
    _columns = {
                'partner_id':fields.many2one('res.partner', 'Partner'),
                'address_id':fields.many2one('res.partner.address', 'Address Partner', domain="[('partner_id', '=', partner_id)]"),
                'shop_id': fields.many2one('sale.shop', 'Shop'),
                'printer_id':fields.many2one('printer.point', 'Printer Point',domain="[('shop_id', '=', shop_id)]"),
                'pre_printer':fields.boolean('Pre-printer', required=False),
                'electronic':fields.boolean('Electrónica', required=False),
                'automatic':fields.boolean('Automatic', required=False),
                'invoice_id':fields.many2one('account.invoice', 'invoice', required=False),
                'number':fields.char('Number', size=17),
                'date': fields.date('Emission Date'),
                'authorization_id':fields.many2one('sri.authorization', 'Authorization'),
                'authorization':fields.char('Authorization', size=10, required=False, readonly=True),
                'user_id':fields.many2one('res.users', 'User', required=False),
                'journal_id': fields.many2one('account.journal', 'journal'),
                'lines_ids': fields.one2many('account.withhold.wizard.line', 'wizard_id', 'Withhold line'),
                'transaction_type':fields.selection([('purchase','Purchase'),('sale','Sale')],  'Transaction type', readonly=True),
                'company_id': fields.many2one('res.company', 'Company'),
                'period_id': fields.many2one('account.period', 'Fiscal Period', domain=[('state','<>','done')], readonly=True),
                'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account'),
                }
    #_constraints = [(_check_number,_('The number is incorrect, it must be like 001-00X-000XXXXXX, X is a number'),['number'])]

    _defaults = {
                 'date': time.strftime('%Y-%m-%d'),
                 }

    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        values={}
        res=[]
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        if 'value' not in context.keys():
            for inv in objs:
                for line in inv.withhold_lines_ids:

                    values1= {
                              'id_lines':str(line.id),
                              'tax_id': line.tax_id.id,
                              'tax_base': line.tax_base,
                              'percentage': line.percentage,
                              'retained_value': line.retained_value,
                              }
                    res.append(values1)
                    
                values = {
                         'user_id':uid,
                         'lines_ids': res,
                         'partner_id':inv.partner_id.id,
                         'address_id':inv.address_invoice_id.id,
                         'invoice_id':inv.id,
                         'date':time.strftime('%Y-%m-%d'),
                         'company_id':inv.company_id.id,
                         'period_id':inv.period_id.id,
                         'shop_id':inv.shop_id.id,
                        }
                if inv.electronic:
                    values ['date']=time.strftime('%Y-%m-%d')
                else:
                    values ['date']=inv.date_invoice
                if inv.type == 'out_invoice':
                    values ['transaction_type']= 'sale'
                    values ['printer_id']= inv.printer_id.id
                elif inv.type == 'in_invoice':
                    values ['transaction_type']= 'purchase'
        else:
            values = context['value']
        return values
    
    def onchange_shop(self, cr, uid, ids, company=None, shop=None, type=None, context=None):
        result=self.pool.get('account.withhold').onchange_shop(cr, uid, ids, company, shop, type, context)
        result['value'].update({'authorization_id':result['value'].get('authorization_purchase',None),
                                'number':result['value'].get('number_purchase',None),})
        return result
    
    def onchange_cash(self, cr, uid, ids, company=None, shop=None, type=None, printer_id=None, journal=None, context=None):
        result=self.pool.get('account.withhold').onchange_cash(cr, uid, ids, company, shop, type, printer_id, journal, context)
        if printer_id:
            tpr = self.pool.get('printer.point').browse(cr,uid,printer_id)
            if tpr.type_printer=='electronic':
                date_withhold = time.strftime('%Y-%m-%d')
                result['value'].update({'date_withhold': date_withhold})               
        result['value'].update({'authorization_id':result['value'].get('authorization_purchase',None), 
                                'journal_id':journal,
                                'number':result['value'].get('number_purchase',None),})
        return result
        
    def onchange_number(self, cr, uid, ids, number, type=None, shop=None, printer_id=None, journal=None, company=None, date=None, context=None):
        result = self.pool.get('account.withhold').onchange_number(cr, uid, ids, number, type, shop, printer_id, journal, company, date, context)
        result['value'].update({'authorization_id':result['value'].get('authorization_purchase',None),
                                'number':result['value'].get('number_purchase',None),})
        return result
    
    def onchange_number_out(self, cr, uid, ids, number, type=None, address=None, journal=None, date=None,context=None):
        result = self.pool.get('account.withhold').onchange_number_out(cr, uid, ids, number, type, address, journal, date,context)
        result['value'].update({'authorization_id':result['value'].get('authorization_sale',None),
                                'number':result['value'].get('number_sale',None),})
        result['domain'].update({'authorization_id':result['value'].get('authorization_sale',None)})
        return result
    def onchange_date(self, cr, uid, ids, date=None, company_id=False, context=None):
        default={}
        if not company_id:
            period_ids = False
        else:
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date or time.strftime('%Y-%m-%d')),('date_stop','>=',date or time.strftime('%Y-%m-%d')), ('company_id', '=', company_id)])
        default['date_withhold']= date
        default['period_id']= period_ids[0]
        return {'value':default}  
        
    def onchange_auth_sale(self, cr, uid, ids, auth=None, number=None, address=None, journal=None, context=None):
        result = self.pool.get('account.withhold').onchange_auth_sale(cr, uid, ids, auth, number, address, journal, context)
        result['value'].update({'number':result['value'].get('number_sale',None)})
        return result
    
    def approve_withhold(self, cr, uid, ids, context = None):
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])[0]
        withhold_obj=self.pool.get('account.withhold')
        withhold_line_obj=self.pool.get('account.withhold.line')
        wf_service = netsvc.LocalService("workflow")
        for obj in self.browse(cr, uid, ids, context=None):
            if not obj.authorization_id:
                raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization, please check'))
            if not obj.lines_ids:
                raise osv.except_osv(_('Invalid action!'), _('Must be create lines withhold')) 
            date= obj.date
            company_id = obj.company_id.id     
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date or time.strftime('%Y-%m-%d')),('date_stop','>=',date or time.strftime('%Y-%m-%d')), ('company_id', '=', company_id)])
            period = period_ids[0]
            lines_id=[]
            for line in obj.lines_ids:
                id_new=withhold_line_obj.create(cr, uid, {'invoice_id':objs.id,
                                                   'tax_id':line.tax_id.id,
                                                   'tax_base':line.tax_base,
                                                   })
                lines_id.append(id_new)
            vals={'invoice_id':objs.id,
                  'partner_id':objs.partner_id.id,
                  'address_id':obj.address_id.id,
                  'journal_id':obj.journal_id.id,
                  'shop_id':obj.shop_id.id,
                  'printer_id':obj.printer_id.id,
                  'automatic':obj.automatic,
                  'pre_printer':obj.pre_printer,
                  'electronic': obj.electronic,
                  'date': obj.date,
                  'period_id':period,
                  'transaction_type':obj.transaction_type,
                  'account_analytic_id':obj.account_analytic_id.id,
                  'withhold_line_ids':[[6,0,lines_id]]
                  }
            if obj.transaction_type == 'sale':
                vals['number_sale']=obj.number
                vals['authorization_sale']=obj.authorization_id.id
                fiscal_position=objs.partner_id.property_account_position or None
                if fiscal_position and fiscal_position.name == 'CONTRIBUYENTES ESPECIALES':
                    vals['flag']=True
                vals['fiscal_position_id']=fiscal_position and fiscal_position.id or None
            else:
                vals['number_purchase']=obj.number
                vals['authorization_purchase']=obj.authorization_id.id
                fiscal_position=objs.company_id.partner_id.property_account_position or None
                if fiscal_position and fiscal_position.name == 'CONTRIBUYENTES ESPECIALES':
                    vals['flag']=True
                vals['fiscal_position_id']=fiscal_position and fiscal_position.id or None
            with_id=withhold_obj.create(cr, uid, vals, context)
#            withhold_obj.write(cr, uid, [with_id], {''})
            wf_service.trg_validate(uid, 'account.withhold', with_id, 'button_approve', cr)
            self.pool.get('account.invoice').write(cr,uid,[objs.id],{'withhold_id':with_id, 'withhold':True})
        return {'type': 'ir.actions.act_window_close'}

withhold_wizard()

class withhold_wizard_line(osv.osv_memory):
    _name = "account.withhold.wizard.line"
    
    _columns = {
            'wizard_id': fields.many2one('account.withhold.wizard', 'wizard'),
            'id_lines':fields.char('id_lines', size=16, required=False, readonly=False),
            'tax_id':fields.many2one('account.tax', 'Tax'),
            'tax_base': fields.float('Tax Base', digits_compute=dp.get_precision('Account')),
            'percentage': fields.float('Percentage Value', digits_compute=dp.get_precision('Account')),
            'retained_value': fields.float('Retained Value', digits_compute=dp.get_precision('Account')),
            }
    
    def on_change_tax(self, cr, uid, ids, invoice=None, tax=None, context={}):
        result={'value':{}}
        if (invoice and tax):
            tax_base=0.0
            tax_browse=self.pool.get('account.tax').browse(cr, uid, tax, context)
            if tax_browse.tax_code_id.tax_type == 'withhold_vat':
                tax_base=self.pool.get('account.invoice').browse(cr, uid, invoice, context).amount_total_vat
            elif tax_browse.tax_code_id.tax_type == 'withhold':
                tax_base=self.pool.get('account.invoice').browse(cr, uid, invoice, context).amount_untaxed
            porcentaje= ((tax_browse.amount)*(-100)) or 0.0
            value_retined = float(tax_base * (porcentaje/100))
            result['value']['tax_base']=tax_base
            result['value']['percentage']=porcentaje
            result['value']['retained_value']=value_retined
        return result
    
withhold_wizard_line()