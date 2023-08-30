# -*- coding: utf-8 -*-
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


from osv import osv, fields
import time
from tools.translate import _
from validate_email import validate_email

class res_segmento(osv.osv):
    _name = 'res.partner.segmento'
    
    def _check_default(self,cr,uid,ids):
        b=True
        for segmento in self.browse(cr, uid, ids):
            if segmento.is_default:
                seg_ids=self.search(cr, uid, [('is_default','=',True),('id','not in',tuple(ids))])
                if seg_ids:
                    b=False
        return b
    
    _columns = {
            'shortcut': fields.char('Shortcut', required=True, size=16),
            'name': fields.char('Segment', required=True, size=46, translate=True),
            'is_default':fields.boolean('Default', required=False),
    }
    _order = 'name'
    
    _constraints = [
        (_check_default,'Only there must be a default segment',['is_default'])]
res_segmento()

class res_segmento_category(osv.osv):
    _name = 'res.partner.segmento.category'
    _columns = {
            'shortcut': fields.char('Shortcut', required=True, size=16),
            'name': fields.char('Partner Industries Category', required=True, size=46, translate=True),
    }
    _order = 'name'
res_segmento_category()

class res_clase_v(osv.osv):
    _name = 'res.partner.clasev'
    _columns = {
            'shortcut': fields.char('Shortcut', required=True, size=16),
            'name': fields.char('Sales Clasification', required=True, size=46, translate=True),
    }
    _order = 'name'
res_clase_v()

class res_clase_c(osv.osv):
    _name = 'res.partner.clasec'
    _columns = {
            'shortcut': fields.char('Shortcut', required=True, size=16),
            'name': fields.char('Credit Clasification', required=True, size=46, translate=True),
    }
    _order = 'name'
res_clase_c()

class res_estado(osv.osv):
    _name = 'res.partner.estado'
    _columns = {
            'shortcut': fields.char('Shortcut', required=True, size=16),
            'name': fields.char('Credit Clasification', required=True, size=46, translate=True),
    }
    _order = 'name'
res_estado()

class Bank(osv.osv):
    _inherit = 'res.bank'
    _columns = {
        'lname': fields.char('Long name', size=128),
        'vat': fields.char('VAT code',size=32 ,help="Value Added Tax number"),
        'website': fields.char('Website',size=64),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),
    }
Bank()

class act_comercial(osv.osv):
    _name = 'res.partner.comactivities'
    _columns = {
        'name': fields.char('Comercial Activities', required=True, size=400, translate=True),
        'shortcut': fields.char('Shortcut', required=True, size=10),
    }
    _order = 'name'
act_comercial()

class credit_history_partner(osv.osv):
    _name = 'res.partner.credit.history'
    _columns = {
        'name':fields.char('Subject', size=50),
        'message': fields.text('Description'),
        'date_note': fields.datetime('Date', readonly=True),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),
        'state':fields.selection([('open','Open'),('close','Close'),('resolve','Resolve'),('pending','Pending'),('cancel','Cancel')],'Status'),
    }
    _defaults= {
        'date_note':lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda self, cr, uid, context: uid,
        'state':lambda *a:'open',
        }
    _order = 'date_note desc'
credit_history_partner()

class res_partner_references(osv.osv):
    _name = 'res.partner.reference'
    _rec_name = 'partner_id'

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'reference_id': fields.many2one('res.partner', 'Partner'),
        'credit': fields.float('Credit Ammount'),
        'credit_time': fields.integer('Credit Time'),
        'since': fields.char('From Year',size=4),
        'credit_comment': fields.text('Comment'),
        'confirm_people':fields.char('People', size=128),
    }
res_partner_references()

class res_partner(osv.osv):

    def _get_vat(self, cr, uid, context=None):
        country_company = None
        company_obj = self.pool.get('res.users')
        country_company = company_obj.browse(cr, uid, uid).company_id.partner_id.vat[:2]
        if country_company:
            return country_company


    def _get_segmento(self, cr, uid, context=None):
        segmento_ids=self.pool.get('res.partner.segmento').search(cr, uid, [('is_default','=',True)])
        return segmento_ids and segmento_ids[0] or None 
    
    _inherit = 'res.partner'
    _columns = {
        'name1': fields.related('name', type='char', size=128, string='Name', readonly=True),
        'shortcut_company': fields.related('type_company_id','shortcut', type='char', size=10, string='shortcut company', readonly=True),
        'first_name':fields.char('First Name', size=64), 
        'second_name':fields.char('Second Name', size=64), 
        'last_name':fields.char('Last Name', size=64), 
        'mother_last_name':fields.char('Mother Last Name', size=64),
        'address': fields.one2many('res.partner.address', 'partner_id', 'Agencies', required=True),
        'beneficiary': fields.char('Beneficiary',size=256),
        'segmento_id': fields.many2one('res.partner.segmento', 'Segmento'),
        'clasev_id': fields.many2one('res.partner.clasev', 'ClaseV'),
        'clasec_id': fields.many2one('res.partner.clasec', 'ClaseC'),
        'estado_id': fields.many2one('res.partner.estado', 'Credit State'),
        'segmento_category_id':fields.many2one('res.partner.segmento.category', 'Segmento Industries Category'),
        'comercial': fields.related('address', 'name', type='char', size=250, string='Comercial'), # Nombre Comercial del Partner
        'codant':fields.char('Former Code', size=20, select=True), # Codigo anterior
        'potential': fields.float('Potential'),
        'actcomercial': fields.many2one('res.partner.comactivities', 'Comercial Activities', help='Comercial Activities for this partner.'),
        'datecom': fields.date('Start Date', select=1),
        'location': fields.related('address', 'location_id', type='char', string='Location'),
        'street': fields.related('address', 'street', type='char', string='Street'),
        'credit_history_id': fields.one2many('res.partner.credit.history','partner_id','Credit History Notes'),
        'credit_references_id':fields.one2many('res.partner.reference','partner_id','Credit References'),
        'approb': fields.boolean('Approve'),
        'active2': fields.boolean('Approve'),
        'is_consignement': fields.boolean('Is consignement'),
        'permit_changed':fields.boolean('Permit Changed?'),
        'type_good': fields.selection([('goods','Bienes'),('services','Servicios')],'Tipo de Compra'),   
        'capital': fields.float('Capital'),
        'patrimonio': fields.float('Patrimonio'),
        'property_stock_consignement': fields.property(
          'stock.location',
          type='many2one',
          relation='stock.location',
          string="Consignement Location",
          method=True,
          view_load=True,
          help="This stock location will be used, instead of the default one, as the destination location for goods you send to this partner"),
            'payment_type_customer': fields.property(
            'payment.type',
            type='many2one',
            relation='payment.mode',
            string ='Customer Payment Type',
            method=True,
            view_load=True,
            help="Payment type of the customer"),
        'payment_type_supplier': fields.property(
            'payment.type',
            type='many2one',
            relation='payment.mode',
            string ='Supplier Payment Type',
            method=True,
            view_load=True,
            help="Payment type of the supplier"),
    }
    _order = 'name asc, vat asc'

    _defaults = {'vat': _get_vat,
                 'segmento_id': _get_segmento,
                 'active2': True,
                 }

    def onchange_name(self,cr,uid,ids,first_name='',second_name='',last_name='',mother_last_name='',context=None):
        values={}
        res = ''
        if first_name:
            res += first_name+' '
        if second_name:
            res += second_name+' '
        if last_name:
            res += last_name+' '
        if mother_last_name:
            res += mother_last_name+' '
        values['name']=res
        values['name1']=res
        return {'value':values}

    def vat_change(self, cr, uid, ids, vat=None, context=None):
        if vat and vat[0:2] == 'EC' and len(vat) > 2:
            repeat = self.search(cr, uid, [('vat', '=', vat), ('id', 'not in', ids)])
            if repeat:
                raise osv.except_osv(_('Invalid action !'), _('Specified VAT Number already exists for any other registered partner'))
            check_vat = self.check_vat_ec(vat[2:])
            if not check_vat:
                raise osv.except_osv(_('Invalid action !'), _('Specified VAT Number is invalid'))
        elif vat and vat[0:1]=='PA':
            check_vat = self.check_vat_pa(vat[2:])
#         elif vat and len(vat)==2:
#             raise osv.except_osv(_('Invalid action !'), _('Necesita agregar el número de identificación'))
        result=super(res_partner, self).vat_change(cr, uid, ids, vat, context)
        result['value']['first_name']=''
        result['value']['second_name']=''
        result['value']['last_name']=''
        result['value']['mother_last_name']=''
        type_company=result['value'].get('type_company_id',None)
        res=self.on_change_type_company_id(cr, uid, ids, type_company, context)
        result['value'].update(res['value'])
        return result
    
    def on_change_type_company_id(self, cr, uid, ids, type_company_id=None, context={}):
        res={}
        if type_company_id:
            type_company=self.pool.get('res.partner.type.company').browse(cr, uid, type_company_id)
            res['shortcut_company']=type_company.shortcut
        return {'value':res}

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not len(ids):
            return []
        if context.get('show_ref'):
            rec_name = 'vat'
        else:
            rec_name = 'name'

        res = [(r['id'], r[rec_name]) for r in self.read(cr, uid, ids, [rec_name], context)]
        return res


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        # short-circuit ref match when possible
        if name and operator in ('=', 'ilike', '=ilike', 'like'):
            ids = self.search(cr, uid, [('vat', 'ilike', name)] + args, limit=limit, context=context)
            if ids:
                return self.name_get(cr, uid, ids, context)
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
    
res_partner()

class res_partner_function(osv.osv):
    _name = 'res.partner.function'
    _columns = {
    'name': fields.char('Function', size=128),
    }
res_partner_function()
    
class res_partner_job(osv.osv):
    _inherit = 'res.partner.job'
    _order = 'sequence_contact'

    _columns = {
        'partner_id': fields.many2one('res.partner','Partner'),
        'first_name': fields.char('First Name', size=128),
        'second_name': fields.char('Second Name', size=128),
        'function': fields.many2one('res.partner.function','Function'),
        'vat': fields.char('VAT code',size=20),
        'sex': fields.selection([('men','Men'),('woman','Woman')],'Sex'),
        'comment': fields.text('Comment', size=128),
        'title': fields.many2one('res.partner.title','Title'),
        'website': fields.char('Website', size=120),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'country_id': fields.many2one('res.country','Nationality'),
        'birthdate': fields.date('Birth Date'),
        'email': fields.char('E-Mail', size=240),
    }
    
res_partner_job()


class res_partner_address(osv.osv): 
    _inherit = "res.partner.address"
    _columns = {
        'job_ids': fields.one2many('res.partner.job', 'partner_id', 'Functions and Addresses'),
        'name': fields.char('Contact Name', size=256, select=1),
    }
    _defaults={'type':'default',
               }

    def create(self, cr, uid, vals, context={}):
        if not vals.get('name',False):
            if vals.get('partner_id',False):
                partner_id = vals.get('partner_id',False) 
                name_partner = self.pool.get('res.partner').browse(cr,uid,partner_id).name
                if name_partner:
                    name = name_partner 
                    vals['name'] = name
        return super(res_partner_address, self).create(cr, uid, vals, context)                              

    def onchange_email(self,cr,uid,ids,email,context=None):
        result ={}
        if email:
            email = email.replace(" ", "")
            is_valid = validate_email(email)
            if is_valid:
                result['email']=email 
                return {'value': result}
            else:
                raise osv.except_osv(_('¡Acción Inválida!'), _('El correo electrónico es incorrecto. Por favor revise.')) 
res_partner_address()

