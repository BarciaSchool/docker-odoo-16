# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################
from osv import fields,osv
import decimal_precision as dp
import re
import time
from tools.translate import _
import netsvc

sql="""SELECT rel.journal_id FROM rel_shop_journal as rel, account_journal as jo 
        WHERE rel.journal_id = jo.id AND rel.shop_id = %s and jo.type = %s"""

class account_withhold(osv.osv):
    
    def _get_retention(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.withhold.line').browse(cr, uid, ids, context=context):
            result[line.withhold_id.id] = True
        return result.keys()
    
    def _total(self, cr, uid, ids, field_name, arg, context=None):
        #cur_obj = self.pool.get('res.currency')
        result = {}
        for ret in self.browse(cr, uid, ids, context=context):
            result[ret.id]={
                            'total':0.0,
                            'total_iva':0.0,
                            'total_renta':0.0,
                            #'total_base':0.0,
                            }
            #cur = ret.invoice_id.currency_id
            for line in ret.withhold_line_ids:
                if line.tax_id:
                    if line.tax_id.tax_code_id.tax_type == 'withhold_vat':
                        result[ret.id]['total_iva']+=line.retained_value
                    else:
                        result[ret.id]['total_renta']+=line.retained_value
                    result[ret.id]['total']+=line.retained_value
                    #result[ret.id]['total_base']+=line.tax_base
        return result
    
    def _total_withhold(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for ret in self.browse(cr, uid, ids, context=context):
            result[ret.id]=0.0
            for line in ret.withhold_line_ids:
                result[ret.id]+=line.retained_value
        return result
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id)])
#         period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date),('date_stop','>=',date), ('company_id', '=', user.company_id.id)])
        return period_ids and period_ids[0] or None
    
    def _get_fiscalyear(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id),('state', '=', 'draft')])
        return fiscalyear_ids and fiscalyear_ids[0] or None
    
    def _get_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('transaction_type','sale')
    
    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if curr_user.cash_box_default_id:
            return curr_user.cash_box_default_id.shop_id.id
        elif curr_user.printer_point_ids:
            for s in curr_user.printer_point_ids:
                if s.shop_id:
                    return s.shop_id.id 
        else:
            return None
    
    def _check_witthold_repeat(self, cr, uid, ids, context=None):
        b=True
        for withhold in self.browse(cr, uid, ids, context=context):
            withhold_ids=self.search(cr, uid, [('number','=',withhold.number),('partner_id','=',withhold.partner_id.id),('state','=','approved')])
            if len(withhold_ids)>1:
                b=False
        return b        
    
    _name = 'account.withhold'
    _columns = {
        'invoice_ids':fields.one2many('account.invoice', 'withhold_id', 'Invoices References',readonly=True, states={'draft':[('readonly',False)]}),
        'invoice_id':fields.many2one('account.invoice', 'Invoice reference', readonly=True, states={'draft':[('readonly',False)]}),
        'flag':fields.boolean('flag', required=False),
        'journal_id': fields.many2one('account.journal', 'journal', readonly=True, states={'draft':[('readonly',False)]}),
        'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True, states={'draft':[('readonly',False)]}),
        'printer_id':fields.many2one('printer.point', 'Printer Point',readonly=True, states={'draft':[('readonly',False)]}, domain="[('shop_id', '=', shop_id)]"),
        'pre_printer':fields.boolean('Pre-printer', required=False),
        'automatic':fields.boolean('Automatic', required=False),
        'number': fields.char('Number', size=17, required=False,),
        'number_purchase': fields.char('Retention Number', size=17, readonly=True, states={'draft':[('readonly',False)]}),
        'number_sale': fields.char('Retention Number', size=17, readonly=True,states={'draft':[('readonly',False)]}),
        'date': fields.date('Emission Date',readonly=True, states={'draft':[('readonly',False)]}),
        'process_date': fields.date('Process Date',readonly=True),
        'authorization':fields.char('Authorization', size=40, required=False, readonly=True, states={'draft':[('readonly',False)]}),
        'authorization_purchase':fields.many2one('sri.authorization', 'Authorization', readonly=True, states={'draft':[('readonly',False)]},help='This Number is necesary for SRI reports'),
        'authorization_sale':fields.many2one('sri.authorization', 'Authorization', readonly=True, states={'draft':[('readonly',False)]},help='This Number is necesary for SRI reports'),
        'transaction_type':fields.selection([
            ('purchase','Purchase'),
            ('sale','Sale'),
            ('recaps','Recaps'),
            ('isd','Impuesto de Salida de Divisas')
            ],  'Transaction type', required=True, readonly=True),
        'withhold_line_ids': fields.one2many('account.withhold.line', 'withhold_id', 'Withhold Lines'),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]}),
        'address_id':fields.many2one('res.partner.address', 'Address Partner', readonly=True, states={'draft':[('readonly',False)]}, domain="[('partner_id', '=', partner_id)]"),
        'fiscal_position_id':fields.many2one('account.fiscal.position', 'Fiscal Position', readonly=True, states={'draft':[('readonly',False)]}),
        'state':fields.selection([
            ('draft','Draft'),
            ('approved','Approved'),
            ('annulled','Annulled'),
            ],  'state', required=True, readonly=True),
        'total': fields.function(_total_withhold, method=True, type='float', string='Total', store = {
                                 'account.withhold': (lambda self, cr, uid, ids, c={}: ids, ['withhold_line_ids'], 11),
                                 'account.withhold.line': (_get_retention, ['tax_base', 'percentage', 'retained_value',], 11),
                                 }),
        'total_iva': fields.function(_total, method=True, type='float', string='Total withhold vat', store = False, multi='total_iva'), 
        'total_renta': fields.function(_total, method=True, type='float', string='Total withhold', store = False, multi='total_renta'),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'period_id': fields.many2one('account.period', 'Fiscal Period', domain=[('state','<>','done')], readonly=True, states={'draft':[('readonly',False)]}),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
        'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True,),
        'user_id': fields.many2one('res.users', 'User',readonly=True, states={'draft': [('readonly', False)]}, select=True),
        'print_status': fields.char('Print Status', size=32),
        'printer_user_id': fields.many2one('res.users', 'Printer User'),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'draft':[('readonly',False)]}),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'active':fields.boolean('Activo'),
        'electronic':fields.boolean('Electrónica'),
#        'sri_annulled': fields.integer('Solicitud de Anulación SRI'),
        'sri_annulled': fields.char('Solicitud de Anulación SRI', size=50),
        'bank_account_id': fields.many2one('account.account','Cuenta Bancaria'),
        'cert_original': fields.integer('Número de Certificado Original'),
        'acrecentamiento': fields.integer('Acrecentamiento'),
        'comprobante_id':fields.many2one('tax.code.comprobante', 'Comprobante', required=False),
        'operacion_id':fields.many2one('tax.code.operacion', 'Operacion', required=False),
        'condicion_id':fields.many2one('tax.code.condicion', 'Condicion', required=False),
        'ret_apli_id':fields.many2one('tax.code.retencion.aplicada', 'Retención Aplicada', required=False),      
    }
    
    _rec_name='number'
    
    _constraints = [(_check_witthold_repeat,'La retención ya existe con el mismo número y para el mismo proveedor en estado Aprobado',['name'])]    
    
    _sql_constraints = [('number_purchase_uniq','check(1=1)', 'There is another Withhold generated with this number, please verify')]
    
    _defaults = {
                 'number': '',
                 'shop_id':_get_shop,
                 'transaction_type':_get_type,
                 'state': lambda *a: 'draft',
                 'fiscalyear_id': _get_fiscalyear,
                 'period_id': _get_period,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.withhold', context=c),
                 'user_id': lambda obj, cr, uid, context: uid,
                 'date': time.strftime('%Y-%m-%d'),
                 'nb_print':0,
                 'active':True
                 }
    
    _order = 'number asc'
    
    def onchange_shop(self, cr, uid, ids, company=None, shop=None, type=None, context=None):
        printer_obj = self.pool.get('printer.point')
        if context is None:
            context = {}
        values={'value':{},'domain':{}}
        box_ids=[]
        shop_ids = []
        box_id=[]
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
#         if user.cash_box_default_id:
#             box_ids.append(user.cash_box_default_id.id)
        for s in user.printer_point_ids:
            if s.shop_id:
                shop_ids.append(s.shop_id.id)                
        if shop:
            box_ids = printer_obj.search(cr,uid,[('shop_id','=',shop)])
            cr.execute(sql,(shop,'withhold'))
            res=cr.fetchall()
            if not res:
                name=self.pool.get('sale.shop').browse(cr, uid, shop,context).name
                warning = {'title': _('Error!'),'message': _(("You must be selected in the shop %s the journal respective for this document.")%name)}
                return {'value': {'shop_id': None}, 'warning':warning}
            values['value']['journal_id']=res[0][0]
            box_id=printer_obj.search(cr, uid, [('id', 'in', box_ids),('shop_id', '=', shop)])
            if not box_id:
                values['value']['authorization']=None
                values['value']['authorization_purchase']=None
                values['value']['account_analytic_id']=None
            else:
                cash=box_id[0]
                if context.get('printer_id',None):
                    cash=context.get('printer_id',None)
                result=self.onchange_cash(cr, uid, ids, company, shop, type, cash,values['value']['journal_id'], context)
                analytic = self.pool.get('sale.shop').browse(cr,uid,shop,context).project_id.id
                values['value'].update(result['value'])
                values['value']['printer_id']=cash
                values['value']['account_analytic_id']=analytic
        domain={'shop_id':[('id','in', shop_ids)], 'printer_id':[('id','in', box_id)]}
        values['domain']=domain
        return values
    
    def onchange_date(self, cr, uid, ids, date=None, company_id=False, context=None):
        default={}
        if not company_id:
            period_ids = False
        else:
            period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date or time.strftime('%Y-%m-%d')),('date_stop','>=',date or time.strftime('%Y-%m-%d')), ('company_id', '=', company_id)])
        default['date_withhold']= date
        default['period_id']= period_ids[0]
        return {'value':default}
       
    def onchange_cash(self, cr, uid, ids, company=None, shop=None, type=None, printer_id=None, journal=None, context=None):
        authorization_obj=self.pool.get('sri.authorization')
        values = {'value':{}}
        if context is None:
            context = {}
        if not journal:
            journal=self.pool.get('account.journal').search(cr, uid,[('type','=','withhold'),('company_id','=',company)])
            if journal:
                journal = journal[0]
                values['value']['journal_id']=journal
        if not (journal and shop):
            warning = {'title': _('Verify data!'),'message': _("you must select the shop and Journal.")}
            return {'value': {'printer_id': None}, 'warning':warning}
        if printer_id:
            if type == 'purchase':
                values['value']['pre_printer']=False
                values['value']['automatic']=False
                values['value']['electronic']=False
                type_journal=self.pool.get('account.journal').browse(cr, uid, journal, context).type
                dic_auth = authorization_obj.get_auth_only(cr, uid, type_journal, company, shop, printer_id, context=context)
                if dic_auth['type_printer']: 
                    if dic_auth['type_printer']=='auto':
                        values['value']['pre_printer']=False
                        values['value']['automatic']=True
                        values['value']['date'] = time.strftime('%Y-%m-%d')
                    elif dic_auth['type_printer'] =='pre':
                        values['value']['pre_printer']=True
                        values['value']['automatic']=False
                    elif dic_auth['type_printer'] =='electronic':
                        values['value']['electronic']=True
                        values['value']['pre_printer']=False
                        values['value']['automatic']=False 
                        values['value']['date'] = time.strftime('%Y-%m-%d')                       
                    else:
                        values['value']['pre_printer']=False
                        values['value']['automatic']=False    

                if dic_auth['authorization']:
                    values['value']['authorization'] = authorization_obj.browse(cr, uid, dic_auth['authorization'],context).name
                    values['value']['authorization_purchase'] = dic_auth['authorization']
                else:
                    values['value']['authorization'] = None
                    values['value']['authorization_purchase'] = None
                    values['value']['date'] = None
                values['value']['number_purchase'] = None
        return values
    
    def onchange_number(self, cr, uid, ids, number, type=None, shop=None, printer_id=None, journal=None, company=None, date=None, context=None):
        result = {}
        warning= {}
        if context is None:
            context = {}
        if number:
            if (type =='purchase'):
                if not (shop and printer_id and journal):
                    warning = {'title': _('Verify data!'),'message': _("you must select the shop, cash, and Journal.")}
                    return {'value': {'number_purchase': ''}, 'warning':warning}
                type_journal=self.pool.get('account.journal').browse(cr, uid, journal, context).type                
                info = self.pool.get('sri.authorization').get_auth(cr, uid, type_journal, shop, printer_id, number, company, date, uid, context)
                if not info['auth']:
                    result['authorization'] = None
                    result['authorization_purchase'] = None
                    result['number_purchase'] = info['sequence']
                    warning = {
                        'title': _('Warning!'),
                        'message': _('¡No existe autorización para el número de documento ingresado!')
                        }
                else:
                    result['authorization_purchase'] = info['auth']
                    result['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, info['auth'],context).name
                    result['number_purchase'] = info['sequence']
        return {'value':result, 'warning':warning}
                
    
    def onchange_number_out(self, cr, uid, ids, number, type=None, address=None, journal=None, date=None, context=None):
        result = {}
        warning= {}
        au=[]
        if context is None:
            context = {}
        migrate = context.get('migrate',False)
        authorization = context.get('authorization',None)
        if type == 'sale':
            if number:
                if not (address and journal):
                    warning = {'title': _('Verify data!'),'message': _("you must select the address and Journal.")}
                    return {'value': {'number_sale': '', 'authorization_sale':'',}, 'warning':warning}
                type_journal=self.pool.get('account.journal').browse(cr, uid, journal, context).type
                vals=self.pool.get('sri.authorization').get_id_supplier(cr, uid, address, number, type_journal,None, date, context=context)
                if migrate:
                    result['authorization'] = authorization
                    result['authorization_sale'] = None
                    result['number_sale'] = number                    
                elif not vals:
                    result['authorization'] = None
                    result['authorization_sale'] = None
                    result['number_sale'] = None
                    warning = {
                        'title': _('Warning!'),
                        'message': _('¡No existe autorización para el número de documento ingresado!')
                        }
                else:
                    for a in vals:
                        au.append(a['auth'])
                    result['number_sale'] = vals[-1]['number']
                    result['authorization_sale'] = vals[-1]['auth']
                    result['authorization'] = self.pool.get('sri.authorization').browse(cr, uid, vals[-1]['auth'],context).name
                    if len(vals)>1:
                            warning = {
                            'title': _('Warning!'),
                            'message': _('This number of invoice can correspond to more than one authorization!')
                            }
        return {'value':result, 'warning':warning,'domain':{'authorization_sale':[('id','in', au)]}}
    

    def onchange_auth_sale(self, cr, uid, ids, auth=None, number=None, address=None, journal=None, context=None):
        values={}
        vals=[]
        if auth:
            if not (address and journal and number):
                warning = {'title': _('Verify data!'),'message': _("you must select the address, Journal and number.")}
                return {'value': {'number_out': ''}, 'warning':warning}
            type_journal=self.pool.get('account.journal').browse(cr, uid, journal, context).type
            num = number.split('-')
            if len(num)>1:
                if len(num)!=3:
                    raise osv.except_osv(_('Invalid action!'), _('The format number is incorrect'))
                vals=self.pool.get('sri.authorization').get_id_supplier(cr, uid, address, num[2], type_journal, auth, context)
            else:
                vals=self.pool.get('sri.authorization').get_id_supplier(cr, uid, address, num[0], type_journal, auth, context)
            if vals:
                values['number_sale'] = vals[-1]['number']
        return {'value':values}
    
    def on_change_partner(self, cr, uid, ids, partner=None, type=None, context={}):
        result={'value':{}}
        if partner:
            res= self.pool.get('res.partner').address_get(cr, uid, [partner], ['default', 'invoice'])
            if res['default']:
                result['value']['address_id']=res['default']
            elif res['invoice']:
                result['value']['address_id']=res['invoice']
            if type=='sale':
                fiscal_position=self.pool.get('res.partner').browse(cr, uid, partner, context).property_account_position or None
                if fiscal_position and fiscal_position.name == 'CONTRIBUYENTES ESPECIALES':
                    result['value']['flag']=True
                    result['value']['invoice_id']=None
                else:
                    result['value']['flag']=False
                result['value']['fiscal_position_id']= fiscal_position and fiscal_position.id or None
        return result
    
    def on_change_company(self, cr, uid, ids, company=None, type=None, context={}):
        result={'value':{}}
        if type=='purchase' and company:
            fiscal_position=self.pool.get('res.company').browse(cr, uid, company, context).partner_id.property_account_position or None
            if fiscal_position and fiscal_position.name == 'CONTRIBUYENTES ESPECIALES':
                result['value']['flag']=True
                result['value']['invoice_id']=None
            else:
                result['value']['flag']=False
            result['value']['fiscal_position_id']= fiscal_position and fiscal_position.id or None
        return result
        
    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('authorization_sale',False):
            vals['authorization']=self.pool.get('sri.authorization').browse(cr, uid,vals['authorization_sale'],context).name
        if vals.get('authorization_purchase',False):
            vals['authorization']=self.pool.get('sri.authorization').browse(cr, uid,vals['authorization_purchase'],context).name
        return super(account_withhold, self).write(cr, uid, ids, vals, context)

    def create(self, cr, uid, vals, context={}):
        if vals.get('authorization_sale' , False):
            vals['authorization']=self.pool.get('sri.authorization').browse(cr, uid,vals['authorization_sale'],context).name
        if vals.get('authorization_purchase' , False):
            vals['authorization']=self.pool.get('sri.authorization').browse(cr, uid,vals['authorization_purchase'],context).name
        return super(account_withhold, self).create(cr, uid, vals, context)
    
    def copy(self, cr, uid, ids, default={}, context=None):
        raise osv.except_osv(_('¡Acción Inválida!'), _('No se puede copiar un Comprobante de Retención'))

    def copy_data(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('¡Acción Inválida!'), _('No se puede copiar un Comprobante de Retención'))
    
    def unlink(self, cr, uid, ids, context=None):
        for ret in self.browse(cr, uid, ids, context):
            if ret.state != 'draft':
                raise osv.except_osv(_('Invalid action !'), _('Only can delete withhold(s) in state draft!'))
            else:
                if ret.invoice_id:
                    self.pool.get('account.invoice').write(cr,uid,[ret.invoice_id.id],{'withhold_id':False})
                if ret.withhold_line_ids:
                    for line in ret.withhold_line_ids:
                        self.pool.get('account.withhold.line').unlink(cr,uid,[line.id])
                self.write(cr,uid,ids,{'active':False,'state':'annulled','number_purchase':None,'number':None})                
        return True
    
    def get_lines_withhold(self,cr, uid, ids, context=None):
        lines_id=[]
        for withhold in self.browse(cr, uid, ids, context):
            if withhold.fiscal_position_id.name == 'CONTRIBUYENTES ESPECIALES' and withhold.flag:
                for invoice in withhold.invoice_ids:
                    lines_id+=[line_tax.id for line_tax in invoice.withhold_lines_ids if line_tax.state == 'draft']
            else:
                if withhold.invoice_id:
                    lines_id+=[line_tax.id for line_tax in withhold.invoice_id.withhold_lines_ids if line_tax.state == 'draft']
            self.write(cr, uid, ids, {'withhold_line_ids':[[6,0,lines_id]]}, context)
        return True
    
    def create_move_line(self, cr, uid, ret_line, partner, journal, period, name, account, amount, move_id, date=time.strftime('%Y-%m-%d'), context={}):
        line={
                'name': name,
                'date': date,
                'partner_id': partner,
                'account_id': account,
                'journal_id': journal,
                'period_id': period,
                'reference': name,
                'ref': name,
                'move_id': move_id,
                }
        if ret_line:
            line['tax_code_id']=ret_line.tax_id.tax_code_id.id
            line['tax_amount']=ret_line.retained_value
        if context.get('credit_card',False):
            line['name']='RETENCIONES DE T/C'
            line['credit']=amount
            line['debit']=0.00                                         
        if context.get('isd',False):
            line['name']='RETENCION POR IMPUESTO DE SALIDA DE DIVISAS'
            line['credit']=amount
            line['debit']=0.00                                         
        elif context.get('sale',False):
            line['debit']=amount
            line['credit']=0.0
            line['name']='RETENCIONES DE CLIENTES'
        elif context.get('purchase',False):
            line['name']='RETENCIONES DE PROVEEDORES'
            line['debit']=0.0
            line['credit']=amount
        elif context.get('out_invoice',False):
            line['name']='FACTURAS DE CLIENTES'
            line['debit']=0.0
            line['credit']=amount
        elif context.get('out_refund',False):
            line['name']='NOTAS DE CRÉDITO DE CLIENTES'
            line['debit']=0.0
            line['credit']=amount                    
        elif context.get('in_invoice',False):
            line['name']='FACTURAS DE PROVEEDORES'
            line['debit']=amount
            line['credit']=0.0
        elif context.get('in_refund',False):
            line['name']='NOTA DE CRÉDITO DE PROVEEDORES'
            line['debit']=amount
            line['credit']=0.0                        
        return line
    
    def create_move_account(self, cr, uid, withhold, vals, context):
        """Method define the account move to reduce the pendding value of the invoice
        Paramethers:
        cr: cursor
        uid: id user
        withhold: browse record of present withhold
        vals: dictionary that have key= invoices and values= lines withhold"""
        move_line_obj = self.pool.get('account.move.line')
        move_pool = self.pool.get('account.move')
        if context is None:
            context={}
        self.write(cr, uid, [withhold.id], {'invoice_ids':[[5]]})
        withhold.refresh()
        name=self.pool.get('ir.sequence').next_by_id(cr, uid, withhold.journal_id.sequence_id.id)
        petty_cash = context.get('petty_cash',False)
        recaps = context.get('recaps', False)
        isd = False
        if withhold.transaction_type=='recaps':
            recaps = True
        elif withhold.transaction_type=='isd':
            isd = True            
        if withhold.number:
            ref=withhold.number
        else:
            ref=name
        if withhold.transaction_type == 'sale':
            details = 'RETENCIONES DE CLIENTES'
        elif withhold.transaction_type == 'purchase':
            details = 'RETENCIONES DE PROVEEDORES'
        elif withhold.transaction_type == 'recaps':
            details = 'RETENCIONES DE EMISORES DE T/C'
        elif withhold.transaction_type == 'isd':
            details = 'RETENCIONES DE IMPUESTO DE SALIDA DE DIVISAS'

        move_line_ids=[]
        move = {'name': name,
                'journal_id': withhold.journal_id.id,
                'date': withhold.date,
                'ref': ref,
                'details': details,
                'period_id': withhold.period_id.id,
                'partner_id':withhold.partner_id.id,
                'shop_id': withhold.shop_id.id,
                    }
        move_id = move_pool.create(cr, uid, move)

        if isd:
            context.update({'isd':True})
            account=withhold.bank_account_id.id
            if not account:
                raise osv.except_osv(_('¡Acción Inválida!'), _('Debe elegir la cuenta contable sobre la cual realizaron su débito.'))                
            move_line=self.pool.get('account.withhold').create_move_line(cr, uid, None, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, withhold.number, account, withhold.total, move_id, withhold.date,context)            
            move_line_ids.append(move_line_obj.create(cr, uid, move_line))
            for line in withhold.withhold_line_ids:
                ctx={'sale':True}
                account = line.tax_id.account_paid_id.id
                move_line=self.pool.get('account.withhold').create_move_line(cr, uid, line, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, withhold.number, account, line.retained_value, move_id, withhold.date,ctx) 
                line.write({'state':'approved'})
                move_line_ids.append(move_line_obj.create(cr, uid, move_line))
            if move_line_ids:
                move_pool.post(cr, uid, [move_id], context)                   
        
        elif recaps:
            context.update({'credit_card':True})
            account=withhold.company_id.property_account_active_credit_card.id
            if not account:
                raise osv.except_osv(_('¡Acción Inválida!'), _('No se ha configurado la cuenta contable para tarjeta de Crédito. Puede hacerlo desde Configuración/Compañía'))                
            move_line=self.pool.get('account.withhold').create_move_line(cr, uid, None, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, withhold.number, account, withhold.total, move_id, withhold.date,context)            
            move_line_ids.append(move_line_obj.create(cr, uid, move_line))
            for line in withhold.withhold_line_ids:
                ctx={'sale':True}
                account = line.tax_id.account_paid_id.id
                move_line=self.pool.get('account.withhold').create_move_line(cr, uid, line, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, withhold.number, account, line.retained_value, move_id, withhold.date,ctx) 
                line.write({'state':'approved'})
                move_line_ids.append(move_line_obj.create(cr, uid, move_line))
            if move_line_ids:
                move_pool.post(cr, uid, [move_id], context)                           
        
        elif not recaps and not isd:
            for invoice in vals.keys():
                suma=0
                rec_ids=[]
                if (invoice.state not in ('open','paid') and not invoice.pos) or (invoice.state=='draft' and not invoice.pos):
                    raise osv.except_osv('Error!', _("the invoice has an invalid state"))
                if withhold.date < invoice.date_invoice:
                    raise osv.except_osv('Error!', _("The date of retention can not be least than the date of invoice"))
                for line in vals.get(invoice):
                    if withhold.transaction_type == 'sale':
                        account=line.tax_id.account_collected_id.id
                        ctx={'sale':True}
                    else:
                        account=line.tax_id.account_paid_id.id
                        ctx={'purchase':True}
                    move_line=self.create_move_line(cr, uid, line, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, ref, account, line.retained_value, move_id, withhold.date,ctx)
                    move_line_id=move_line_obj.create(cr, uid, move_line) if line.retained_value > 0 else None
                    self.pool.get('account.withhold.line').write(cr, uid, [line.id], {'move_line_id':move_line_id, 'state':'approved'})
                    move_line_id and move_line_ids.append(move_line_id)
                    suma+=line.retained_value
                if suma >0:
                    dif= round(invoice.residual,2) - suma
                    if dif<0 and not petty_cash:
                        account_advance=None
                        if withhold.transaction_type == 'sale':
                            account_advance=withhold.company_id.property_account_advance_customer.id or None
                        else:
                            account_advance=withhold.company_id.property_account_advance_supplier.id or None
                        ctx={invoice.type:True}
                        if not account_advance:
                            raise osv.except_osv('Error!', _("You must configure the advance accounts in the company"))
                        move_line=self.create_move_line(cr, uid, None, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, invoice.number, account_advance, abs(dif), move_id, withhold.date,ctx)
                        move_line_ids.append(move_line_obj.create(cr, uid, move_line))
                        if invoice.residual>0:
                            account=invoice.account_id.id
                            move_line=self.create_move_line(cr, uid, None, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, invoice.number, account, invoice.residual, move_id, withhold.date,ctx)
                            move_line_ids.append(move_line_obj.create(cr, uid, move_line))
                    else:
                        account=invoice.account_id.id
                        ctx={invoice.type:True}
                        move_line=self.create_move_line(cr, uid, None, withhold.partner_id.id, withhold.journal_id.id, withhold.period_id.id, invoice.number, account, suma, move_id, withhold.date,ctx)
                        move_line_ids.append(move_line_obj.create(cr, uid, move_line))
                if move_line_ids:
                    move_pool.post(cr, uid, [move_id], context={})
                    if invoice.type in ("out_invoice"):
                        move_line_inv = move_line_obj.search(cr, uid, [('invoice', '=', invoice.id),('state','=','valid'), ('account_id.type', '=', 'receivable'), ('reconcile_id', '=', False),('partner_id', '=', withhold.partner_id.id)], context=context)
                    else:
                        move_line_inv = move_line_obj.search(cr, uid, [('invoice', '=', invoice.id),('state','=','valid'), ('account_id.type', '=', 'payable'), ('reconcile_id', '=', False),('partner_id', '=', withhold.partner_id.id)], context=context)    
                    if move_line_inv:
                        rec_ids=[move_line_ids[-1],move_line_inv[0]]
                    context['fy_closing']=True
                    if len(rec_ids) >= 2:
                        move_line_obj.reconcile_partial(cr, uid, rec_ids, context=context)
                else:
                    move_pool.unlink(cr, uid, [move_id], context={})
                    move_id=None
                self.pool.get('account.invoice').write(cr, uid, [invoice.id], {'withhold_id':withhold.id, 'withhold':True})
                lines_wth=self.pool.get('account.withhold.line').search(cr, uid, [('invoice_id','=',invoice.id),('state','=','draft')])
                self.pool.get('account.withhold.line').unlink(cr, uid, lines_wth, context)                
        return self.write(cr, uid, [withhold.id], {'move_id':move_id})
    
    def action_aprove(self,cr,uid,ids,context=None):
        if not context:
            context = {}
        auth_obj = self.pool.get('sri.authorization')
        for ret in self.browse(cr,uid,ids,context=None):
            date_process = None
            if not ret.date:
                date_process = time.strftime('%Y-%m-%d')
            else:
                date_process = ret.date
            self.write(cr, uid, [ret.id],{'process_date':date_process}, context)
            invoices_vals={}
            for line in ret.withhold_line_ids:
                if line.state !='draft':
                    continue
                if line.invoice_id:
                    if line.invoice_id.withhold_id.id != ret.id and line.withhold_id.state == 'approved':
                        raise osv.except_osv('Error!', _(("there is already been approved for withhold by the invoice %s, please check")%(ret.invoice_id.number)))
                    if not invoices_vals.has_key(line.invoice_id):
                        invoices_vals[line.invoice_id]=[line]
                    else:
                        invoices_vals[line.invoice_id]+=[line]
            if ret.transaction_type == 'recaps':
                context.update({'recaps':True})                
            if ret.transaction_type in ('sale','recaps'):
                if not ret.number:
                    raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                if not ret.authorization:
                    if not ret.authorization_sale and not ret.electronic:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
                if not (ret.shop_id and ret.printer_id):
                    raise osv.except_osv(_('Error!'), _("The withholding can not be approved because of missing fields to be completed: shop or printer"))
                if not ret.electronic and not ret.authorization:
                    vals=self.pool.get('sri.authorization').get_id_supplier(cr, uid, ret.address_id.id, ret.number_sale, ret.journal_id.type, ret.authorization_sale.id, context)
                    number = ret.number_sale.split('-')
                    if not vals:
                        raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization for this number of sequence, please check'))
                    if self.search(cr, uid, [('partner_id', '=', ret.partner_id.id), ('transaction_type','=','sale'), ('number_sale','=',vals[-1]['number']) , ('id','not in',tuple(ids)),('state','=','approved')]):
                        raise osv.except_osv(_('Error!'), _("There is an withhold with number %s for supplier %s") % (vals[-1]['number'], ret.partner_id.name))
                    self.write(cr, uid, [ret.id], {'number': vals[-1]['number'],
                                                   'number_sale': vals[-1]['number'],
                                                   'authorization_sale': vals[-1]['auth'],
                                                   'user_id':uid,}, context)
                else:
                    context.update({'petty_cash':True})
                    self.write(cr, uid, [ret.id], {'number': ret.number,
                                                   'number_sale': ret.number,
                                                   'authorization_sale': False,
                                                   'user_id':uid,}, context)
                    
            elif ret.transaction_type == 'purchase':
                type_journal = ret.journal_id.type
                if not (ret.automatic or ret.pre_printer or ret.electronic):                    
                    if not ret.number_purchase:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist number for the document, please check'))
                    auth = auth_obj.get_auth(cr, uid, type_journal, ret.shop_id.id, ret.printer_id.id, ret.number_purchase, ret.company_id.id, ret.date, context)
                    if not auth['auth']:
                        raise osv.except_osv(_('Invalid action!'), _('Do not exist authorization for this number of sequence, please check'))
                    line_id=auth_obj.get_line_id(cr, uid, type_journal, ret.shop_id.id, ret.printer_id.id, auth['auth'], context)
                    self.pool.get('sri.authorization.line').add_document(cr, uid, line_id, context)
                    self.write(cr, uid, [ret.id], {'number': auth['sequence'],
                                                   'number_purchase':auth['sequence'], 
                                                   'authorization_purchase':auth['auth'],
                                                   'user_id':uid,
                                                   }, context)
                else:
                    if not ret.authorization_purchase:
                        raise osv.except_osv(_('Invalid action!'), _('Not exist authorization for the document, please check'))
                    if not auth_obj.check_date_document(cr, uid, ret.authorization_purchase.id, ret.date):
                        raise osv.except_osv(_('Invalid action!'), _('The date entered is not valid for the authorization'))
                    line_id=auth_obj.get_line_id(cr, uid, type_journal, ret.shop_id.id, ret.printer_id.id, ret.authorization_purchase.id, context)
                    if not ret.number_purchase:
                        b = True
                        while b :
                            number = auth_obj.get_number(cr, uid, [ret.authorization_purchase.id], type_journal,ret.shop_id.id,ret.printer_id.id, ret.company_id.id)
#                             self.pool.get('sri.authorization.line').add_sequence(cr, uid,line_id,{})
                            if not self.search(cr, uid, [('transaction_type','=','purchase'),('number','=',number),('shop_id','=',ret.shop_id.id), ('printer_id','=',ret.printer_id.id),('id','not in',tuple(ids))],):
                                b=False
                    else:
                        number = ret.number_purchase
                    self.pool.get('sri.authorization.line').add_document(cr,uid,line_id,{})
                    self.write(cr, uid, [ret.id], {'number': number, 
                                                   'number_purchase':number,
                                                   'number_purchase':number, 
                                                   'user_id':uid,
                                                   }, context)
            ret.refresh()
            self.create_move_account(cr, uid, ret, invoices_vals, context)
        return self.write(cr, uid, ids, {'state': 'approved'}, context)
       
    def action_annulled(self,cr,uid,ids,context=None):
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        reconcile_pool = self.pool.get('account.move.reconcile')
        withhold = self.pool.get('account.withhold').browse(cr, uid, ids, context)
        invoices=[]
        lines=[]
        for ret in withhold:
            if ret.electronic and not ret.sri_annulled and ret.transaction_type=='purchase':
                raise osv.except_osv(_('¡Acción Inválida!'), _('¡Por favor, ingrese el número de solicitud de anulación del SRI antes de continuar!'))
            if ret.electronic and len(str(ret.sri_annulled)) <5 and ret.transaction_type=='purchase':
                raise osv.except_osv(_('¡Acción Inválida!'), _('¡Por favor, ingrese el número COMPLETO de la solicitud de anulación del SRI antes de continuar!'))
            if ret.move_id:
                for line in ret.move_id.line_id:
                    move_lines=[]
                    lines.append(line.id)
                    if line.reconcile_id:
                        move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                        move_lines.remove(line.id)
                        reconcile_pool.unlink(cr, uid, line.reconcile_id.id)
                    if line.reconcile_partial_id:
                        move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                        move_lines.remove(line.id)
                        reconcile_pool.unlink(cr, uid, line.reconcile_partial_id.id)
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
                move_pool.button_cancel(cr, uid, [ret.move_id.id], context={})
                move_pool.unlink(cr, uid, [ret.move_id.id], context={})
                move_line_pool.unlink(cr, uid, lines, context={})
            for line in ret.withhold_line_ids:
                self.pool.get('account.withhold.line').write(cr, uid, [line.id], {'state':'annulled'})
                if line.invoice_id:
                    invoices.append(line.invoice_id.id)
            self.pool.get('account.invoice').write(cr, uid, invoices, {'withhold':False, 'withhold_id':False}, context)
            date_process = time.strftime('%Y-%m-%d %H:%M:%S')
            number = ret.number                  
        self.write(cr, uid, ids, {'state':'annulled','number':number, 'number_purchase':number, 'number_sale':number}, context)
        return True
    
    def button_set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft', 'number':None})
        wf_service = netsvc.LocalService("workflow")
        authorization_obj=self.pool.get('sri.authorization')
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')                
        lines=[]
        line_id = []
        for ret in self.browse(cr, uid, ids):
            invoice_id = [ret.invoice_id.id]
            if (ret.electronic and not ret.sri_annulled and ret.transaction_type !='purchase') or ret.pre_printer or ret.automatic:
                if ret.authorization_sale:
                    line_id=authorization_obj.get_line_id(cr, uid, ret.journal_id.type, ret.shop_id.id, ret.printer_id.id, ret.authorization_sale.id, {})
                if ret.authorization_purchase:
                    line_id=authorization_obj.get_line_id(cr, uid, ret.journal_id.type, ret.shop_id.id, ret.printer_id.id, ret.authorization_purchase.id, {})
                if line_id:
                    self.pool.get('sri.authorization.line').rest_document(cr,uid,line_id,{})
                    self.pool.get('sri.authorization.line').rest_sequence(cr,uid,line_id,{})
                line_wth= [line.id for line in ret.withhold_line_ids]
                self.pool.get('account.withhold.line').write(cr, uid, line_wth, {'state':'draft'})
                if ret.move_id:
                    for line in ret.move_id.line_id:
                        move_lines=[]
                        lines.append(line.id)
                        if line.reconcile_id:
                            move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                            move_lines.remove(line.id)
                            reconcile_pool.unlink(cr, uid, line.reconcile_id.id)
                        if line.reconcile_partial_id:
                            move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                            move_lines.remove(line.id)
                            reconcile_pool.unlink(cr, uid, line.reconcile_partial_id.id)
                        if len(move_lines) >= 2:
                            move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
                    move_pool.button_cancel(cr, uid, [ret.move_id.id], context={})
                    move_pool.unlink(cr, uid, [ret.move_id.id], context={})
                    move_line_pool.unlink(cr, uid, lines, context={})
                    self.write(cr,uid,ret.id,{'move_id':False})
                wf_service.trg_delete(uid, 'account.withhold', ret.id, cr)
                wf_service.trg_create(uid, 'account.withhold', ret.id, cr)
            else:
                raise osv.except_osv(_('¡Acción Inválida!'), _('¡Las retenciones electrónicas no se pueden cambiar a borrador, solo pueden ser anuladas!'))            
#         self.pool.get('account.invoice').write(cr, uid, invoice_id, {'withhold':False})
        return True
    
    def print_withhold(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for withhold in self.browse(cr, uid, ids, context=context): 
            nb_print = withhold.nb_print + 1
            self.write(cr,uid,withhold.id,{'nb_print':nb_print})
            if withhold:
                data = {}
                data['model'] = 'account.withhold'
                data['ids'] = ids
                context['active_id']=withhold.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'Retenciones_Proveedor',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 


account_withhold()

class account_withhold_line(osv.osv):
    
    def _amount_retained(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            value_retined = float(line.tax_base * (line.percentage/100))
            cur = self.pool.get('res.users').browse(cr, uid, [uid,], context)[0]['company_id']['currency_id']
            res[line.id] = cur_obj.round(cr, uid, cur, value_retined)
        return res

    def _name_wth(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = ''
            if line.tax_id:
                if line.tax_id.tax_code_id.tax_type == 'withhold_vat':
                    res[line.id] = 'IVA'
                else:
                    res[line.id] = 'RENTA'
        return res

    def _percentaje_retained(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id]=0.0
            if line.tax_id:
                porcentaje= (line.tax_id.amount)*(-100)
                res[line.id]=porcentaje
        return res
    
    _name = 'account.withhold.line'
    _columns = {
        'withhold_id': fields.many2one('account.withhold', 'Withhold', ondelete='cascade'),
        'invoice_id': fields.many2one('account.invoice', 'Number of Invoice', readonly=False, states={'approved':[('readonly',True)],'annulled':[('readonly',True)]}, ondelete='cascade'),
        'move_line_id':fields.many2one('account.move.line', 'Move Line Reference', readonly=True),
        #'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
        'fiscalyear_id': fields.related('withhold_id', 'fiscalyear_id', type='many2one', relation='account.fiscalyear', string='Fiscal Year', store=True, readonly=True),
        'period_id': fields.related('withhold_id', 'period_id', type='many2one', relation='account.period', string='Fiscal Period', store=True, readonly=True),
        'tax_id':fields.many2one('account.tax', 'Tax',readonly=True, states={'draft': [('readonly', False)]}, select=True),
        'tax_base': fields.float('Tax Base', digits_compute=dp.get_precision('Account'),readonly=True, states={'draft': [('readonly', False)]}, select=True),
        'name': fields.function(_name_wth, method=True, type='char', size=60, string='Tax Name', store=True),
        'percentage': fields.function(_percentaje_retained, method=True, type='float', string='Percentage Value',
                                          store={
                                                 'account.withhold.line': (lambda self, cr, uid, ids, c={}: ids, ['tax_id',], 8),
                                                 #'account.withhold': (_get_retention_line, None, 9),
                                                 },),
        'retained_value': fields.function(_amount_retained, method=True, type='float', string='Retained Value', 
                                          store={
                                                 'account.withhold.line': (lambda self, cr, uid, ids, c={}: ids, ['tax_base','percentage',], 10),
                                                 #'account.withhold': (_get_retention_line, None, 11),
                                                 },),
        'state':fields.selection([
            ('draft','Draft'),
            ('approved','Approved'),
            ('annulled','Annulled'),
            ],  'state', required=True, readonly=True), 
        'partner_id': fields.related('withhold_id', 'partner_id', type='many2one', relation='res.partner', string='Partner', readonly=True, store=True),
        'address_id': fields.related('withhold_id', 'address_id', type='many2one', relation='res.partner.address', string='Address Partner',readonly=True),
        'number':fields.related('withhold_id', 'number', type='char',size=17, string='number',readonly=True),
        'date': fields.related('withhold_id', 'date', type='date', string='Date', store=True, readonly=True),
        'transaction_type':fields.related('withhold_id','transaction_type', type='selection', 
                                selection=[        
                                        ('purchase','Purchase'),
                                        ('sale','Sale'),
                                        ],string='Transaction type', readonly=True),
        'active':fields.boolean('Activo')                
    }
    
    _defaults={'invoice_id':None,
               'state':'draft',
               'active':True
               }
    
    _rec_name='tax_id'
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not len(ids):
            return []
        for line in self.browse(cr, uid, ids, context):
            name=""
            if line.name:
                name=name+"%s"%(line.name)
            if line.tax_id:
                if name:
                    name+"-"
                name=name+"%s"%(line.tax_id.name)
            res.append((line.id, name))
        return res
    
    def on_change_invoice(self, cr, uid, ids, invoice=None, tax=None, invoice_parent_id=None ,flag=False, context={}):
        result={'value':{'tax_base':0}}
        if (invoice and tax):
            if self.pool.get('account.tax').browse(cr, uid, tax, context).tax_code_id.tax_type == 'withhold_vat':
                result['value']['tax_base']=self.pool.get('account.invoice').browse(cr, uid, invoice, context).amount_total_vat
            elif self.pool.get('account.tax').browse(cr, uid, tax, context).tax_code_id.tax_type == 'withhold':
                result['value']['tax_base']=self.pool.get('account.invoice').browse(cr, uid, invoice, context).amount_untaxed
        if not flag:
            result['value']['invoice_id']=invoice_parent_id
            result['domain']={'invoice_id':[('id','=',invoice_parent_id)]}
        return result
    
    def unlink(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context):
            if line.state != 'draft':
                raise osv.except_osv(_('Invalid action !'), _('Only can delete lines withhold in state draft !'))
            else:
                self.write(cr,uid,ids,{'active':False,'state':'annulled'})
        return True            
#         return super(account_withhold_line, self).unlink(cr, uid, ids, context)
account_withhold_line()