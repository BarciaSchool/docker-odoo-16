# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

import time
from osv import fields, osv
import decimal_precision as dp

class account_tax_code_template(osv.osv):
    _inherit = "account.tax.code.template"
    _columns = {
        'tax_type': fields.selection([('vat', 'VAT'),('withhold','Withhold'), ('withhold_vat','Withhold Vat'), ('other', 'Other'),('duties','Duties')], 'Tax Type', size=32,
                                     help="Select 'VAT' for VAT tax to be used at the time of making invoice."\
                                         "Select 'Withhold' for Withhold and VAT's Withhold tax to be used at the time of making invoice."\
                                         "Select 'Duties' for Duties tax to be used at the time of trade international liquidation."),
        'name': fields.char('Tax Case Name', size=256, required=True),
                }

    def generate_tax_code(self, cr, uid, tax_code_root_id, company_id, context=None):
        '''
        This function generates the tax codes from the templates of tax code that are children of the given one passed
        in argument. Then it returns a dictionary with the mappping between the templates and the real objects.

        :param tax_code_root_id: id of the root of all the tax code templates to process
        :param company_id: id of the company the wizard is running for
        :returns: dictionary with the mappping between the templates and the real objects.
        :rtype: dict
        '''
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_code = self.pool.get('account.tax.code')
        tax_code_template_ref = {}
        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)

        #find all the children of the tax_code_root_id
        children_tax_code_template = tax_code_root_id and obj_tax_code_template.search(cr, uid, [('parent_id','child_of',[tax_code_root_id])], order='id') or []
        for tax_code_template in obj_tax_code_template.browse(cr, uid, children_tax_code_template, context=context):
            vals = {
                'name': (tax_code_root_id == tax_code_template.id) and company.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False,
                'company_id': company_id,
                'sign': tax_code_template.sign,
                'tax_type': tax_code_template.tax_type,
            }
            #check if this tax code already exists
            rec_list = obj_tax_code.search(cr, uid, [('name', '=', vals['name']),('code', '=', vals['code']),('company_id', '=', vals['company_id'])], context=context)
            if not rec_list:
                #if not yet, create it
                new_tax_code = obj_tax_code.create(cr, uid, vals)
                #recording the new tax code to do the mapping
                tax_code_template_ref[tax_code_template.id] = new_tax_code
        return tax_code_template_ref
account_tax_code_template()

class account_tax_code(osv.osv):
    _inherit = "account.tax.code"
    _columns = {
        'tax_type': fields.selection([('vat', 'VAT'),('withhold','Withhold'), ('withhold_vat','Withhold Vat'), ('other', 'Others Taxes'),('duties','Duties')], 'Tax Type', size=32,
                                 help="Select 'VAT' for VAT tax to be used at the time of making invoice."\
                                 "Select 'Withhold' for Withhold and VAT's Withhold tax to be used at the time of making invoice."\
                                 "Select 'Duties' for Duties tax to be used at the time of trade international liquidation."),
        'state': fields.selection([('active','Activo'),('inactive','Descontinuado')], 'Estado SRI', size=32,),                
                }
    
    _defaults = {'state':'active'}
account_tax_code()

class account_tax_template(osv.osv):

    _inherit = 'account.tax.template'
    _columns = {
        'name': fields.char('Tax Name', size=256, required=True),
        'tax_type': fields.selection([('vat', 'VAT'),('withhold','Withhold'), ('withhold_vat','Withhold Vat'), ('other', 'Others Taxes'),('duties','Duties')], 'Tax Type', size=32,
                                 help="Select 'VAT' for VAT tax to be used at the time of making invoice."\
                                 "Select 'Withhold' for Withhold and VAT's Withhold tax to be used at the time of making invoice."\
                                 "Select 'Duties' for Duties tax to be used at the time of trade international liquidation."),
        }

    def _generate_tax(self, cr, uid, tax_templates, tax_code_template_ref, company_id, context=None):
        """
        This method generate taxes from templates.

        :param tax_templates: list of browse record of the tax templates to process
        :param tax_code_template_ref: Taxcode templates reference.
        :param company_id: id of the company the wizard is running for
        :returns:
            {
            'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
            'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        if context is None:
            context = {}
        res = {}
        todo_dict = {}
        tax_template_to_tax = {}
        for tax in tax_templates:
            vals_tax = {
                'name':tax.name,
                'sequence': tax.sequence,
                'amount': tax.amount,
                'type': tax.type,
                'applicable_type': tax.applicable_type,
                'domain': tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_to_tax) and tax_template_to_tax[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
                'base_code_id': tax.base_code_id and ((tax.base_code_id.id in tax_code_template_ref)
                                                      and tax_code_template_ref[tax.base_code_id.id]) or False,
                'tax_code_id': tax.tax_code_id and ((tax.tax_code_id.id in tax_code_template_ref)
                                                    and tax_code_template_ref[tax.tax_code_id.id]) or False,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_code_id': tax.ref_base_code_id and ((tax.ref_base_code_id.id in tax_code_template_ref)
                                                              and tax_code_template_ref[tax.ref_base_code_id.id]) or False,
                'ref_tax_code_id': tax.ref_tax_code_id and ((tax.ref_tax_code_id.id in tax_code_template_ref)
                                                            and tax_code_template_ref[tax.ref_tax_code_id.id]) or False,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'include_base_amount': tax.include_base_amount,
                'description': tax.description,
                'company_id': company_id,
                'type_tax_use': tax.type_tax_use,
                'price_include': tax.price_include,
                'tax_type': tax.tax_type,
            }
            new_tax = self.pool.get('account.tax').create(cr, uid, vals_tax)
            tax_template_to_tax[tax.id] = new_tax
            #as the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax] = {
                'account_collected_id': tax.account_collected_id and tax.account_collected_id.id or False,
                'account_paid_id': tax.account_paid_id and tax.account_paid_id.id or False,
            }
        res.update({'tax_template_to_tax': tax_template_to_tax, 'account_dict': todo_dict})
        return res


account_tax_template()

class account_tax(osv.osv):

    _inherit = 'account.tax'
    _columns = {
        'name': fields.char('Tax Name', size=256, required=True),
        'state': fields.selection([('active','Activo'),('inactive','Descontinuado')], 'Estado SRI', size=32,),
        'tax_type':fields.related('tax_code_id', 'tax_type', type='selection',
                                  selection=[('vat', 'IVA'),('withhold','Retención en la Fuente'), ('withhold_vat','Retención del IVA'), ('other', 'Otros Impuestos'),('duties','Aranceles')],string="Tipo de Impuesto",
                                  store={
                                         'account.tax.code': (lambda self, cr, uid, ids, c={}: ids, ['tax_code_id'], 5),
                                         },
                                  )}
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use)', 'Tax Name must be unique per company!'),
    ]
    _order = 'type_tax_use desc, description asc'
    _defaults = {'state':'active'}    
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context=context):
            name= record['description'] and record['description']+' ' or ''
            name += record['name'] and record['name'] or ''
            res.append((record['id'],name ))
        return res


    def compute_all(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None, force_excluded=False):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'AccountInvoice')
        totalin = totalex = round(price_unit, precision) * quantity
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, address_id=address_id, product=product, partner=partner)
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, address_id=address_id, product=product, partner=partner)
        for r in tex:
            totalin += r.get('amount', 0.0)
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }

account_tax()


class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"

    _columns = {
        'base': fields.float('Base', digits_compute=dp.get_precision('Account')),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'base_amount': fields.float('Base Code Amount', digits_compute=dp.get_precision('Account')),
        'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Account')),
        'name': fields.char('Tax Description', size=256, required=True),
    }


    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'AccountInvoice')

        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, line.price_unit, line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id)['taxes']:
                tax['price_unit'] = round(tax['price_unit'],precision) 
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = round(tax['amount'],precision)
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = round(tax['price_unit'],precision) * line['quantity']

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
#                     val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
#                     val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['base_amount'] = round(val['base']*tax['base_sign'],3)
                    val['tax_amount'] = round(val['amount']*tax['base_sign'],3)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = round(val['base']*tax['base_sign'],3)
                    val['tax_amount'] = round(val['amount']*tax['base_sign'],3)
#                     val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
#                     val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = round(t['base'],precision)
            t['amount'] = round(t['amount'],precision)
            t['base_amount'] = round(t['base_amount'],precision)
            t['tax_amount'] = round(t['tax_amount'],precision)
        return tax_grouped

account_invoice_tax()

