# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import method
import time
from tools.translate import _

def _get_name(self, cr, uid, context={}):
    cr.execute("""select code, name from account_journal_type where sri_type_control in ('partner','company_partner')""")
    return cr.fetchall()

class sri_authorization(osv.osv):

    def _verify_state(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for auth in self.browse(cr, uid, ids, context=context):
            res[auth.id]=False
            if auth.address_id:
                res[auth.id]= (not auth.auto_expired)
            else:
                if not auth.auto_expired:
                    for line in auth.lines_ids:
                        if line.state:
                            res[auth.id]=True
        return res
    
    def _check_padding(self,cr,uid,ids):
        for auth in self.browse(cr, uid, ids):
            if (auth['padding'] <= 0):
                return False
            else:
                return True
    
    def _check_date(self,cr,uid,ids):
        for auth in self.browse(cr, uid, ids):
            if (auth['start_date'] > auth['expiration_date']):
                return False
            else:
                return True

    def _expiration_date(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for auth in self.browse(cr, uid, ids, context):
            res[auth.id] = None
            if auth.start_date:
                dt = datetime.strptime(auth.start_date, '%Y-%m-%d') + relativedelta(years=1)
                res[auth.id] = dt.strftime('%Y-%m-%d')
        return res
    
    def _generate_document(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for auth in self.browse(cr, uid, ids, context):
            b=False
            for line in auth.lines_ids:
                if line.generate_document:
                    b=True
                    break
            res[auth.id]=b
        return res
    
    def _check_name(self,cr,uid,ids):
        for auth in self.browse(cr, uid, ids):
            cadena=auth.name
            tipo=auth.auto_printer
            if auth.company_id and len(cadena)<>10 and tipo:
                raise osv.except_osv(_('¡Acción Inválida!'), _('La autorización de la compañía solo puede contener 10 dígitos'))
            return method.check_only_authorization(cadena)
        
    def _check_address(self,cr,uid,ids):
        for auth in self.browse(cr, uid, ids):
            partner_id = auth.address_id.partner_id.id
            cadena=auth.name
            starting_number = auth.starting_number 
            ending_number = auth.ending_number
            tipo=auth.auto_printer
            address_data = self.pool.get('res.partner.address').search(cr,uid[('partner_id','=',partner_id)])
            datas = self.search(cr,uid,[('ending_number','ending_number',ending_number),('starting_number','=',starting_number),('address_id','in',address_data)])
            if len(datas)>1:
                raise osv.except_osv(_('¡Acción Inválida!'), _('La autorización ya se encuentra creada en esta Empresa en una de sus sucursales'))
            else:
                return True
                    
    def _get_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sri.authorization.line').browse(cr, uid, ids, context=context):
            result[line.authorization_id.id] = True
        return result.keys()
            
    _name = 'sri.authorization'

    _columns = {
            'company_id':fields.many2one('res.company', 'Company', required=False),
            'name':fields.char('Authorization', size=37, required=True),
            'auto_printer': fields.boolean('automatic'),
            'auto_expired':fields.boolean('Expired?'),
            'start_date': fields.date('Start Date', required=True),
            'expiration_date': fields.date('Expiration Date', required=True),
            'padding': fields.integer('Number padding'),
            'printer_aut':fields.char('Printer Authorization', size=10, required=False),
            'lines_ids':fields.one2many('sri.authorization.line', 'authorization_id', 'Documents Authorized', required=False),
            'generate_document': fields.function(_generate_document, method=True, type='boolean', string='Generate Document',),
            'auth_generate': fields.boolean('Autorizaciones ya generadas'),
            'state': fields.function(_verify_state, method=True, type='boolean', string='Active',
                                        store={'sri.authorization': (lambda self, cr, uid, ids, c={}: ids, ['lines_ids','auto_expired','address_id'], 10),
                                               'sri.authorization.line': (_get_line , ['state','counter','expired'], 9)}),
#            campos extras para el control de las autorizaciones de proveedores, pueden ser omitidos
            'address_id':fields.many2one('res.partner.address', 'Address Partner', ondelete="cascade"),
            'code_address':fields.selection(_get_name, 'Name', size=64, required=False),
            'prefix_shop':fields.char('prefix shop', size=3, required=False, readonly=False),
            'prefix_point':fields.char('prefix point', size=3, required=False, readonly=False),
            'starting_number': fields.integer('Start', required=False),
            'ending_number': fields.integer('End', required=False),
            'type_printer':fields.selection([('auto','Auto Impresor'),('pre','Preimpresos'),('electronic','Facturación Electrónica')],'Type Printer', select=True,
                                help="defines how it will generate documents"),
            'environment':fields.selection([('1','Pruebas'),('2','Producción')],'Ambiente', select=True),
            'type_emision':fields.selection([('1','Emisión Normal'),('2','Emisión por Indisponibilidad del Sistema')],'Tipo de Emisión', select=True),
            'active': fields.boolean('active')
            
    }
        
    _defaults = {
        'start_date': lambda *a: time.strftime('%Y-%m-%d'),
        'padding': 9,
        'type_printer':'pre',
        'environment':'1',
        'active': True, 
        'state':True   
    }
    
    _constraints = [(_check_name,'The name must be only numbers',['name']),
                    (_check_padding,'The padding number must be more than 0',['padding']),
                    (_check_date,'The expiration date must be more than start date',['start_date','expiration_date']),
#                    (_check_address,'Can not exist authorizations with the same name for the same address partner',['partner_id']),
                    ]
    
    _sql_constraints = [('auth_name_uniq','unique(name,company_id)', 'Can not exist authorizations with the same name for the same company'),
                        ('auth_name_address_uniq','unique(name,code_address,address_id,prefix_shop,prefix_point,state)', '')
                        ]

    def unlink(self, cr, uid, ids, context=None):
        for auth in self.browse(cr, uid, ids, context):
            lines_ids= [line.id for line in auth.lines_ids if line.counter > 0]
            if lines_ids:
                raise osv.except_osv(_('Invalid action!'), _('You can delete authorization that have already generated documents'))
        else:
            self.write(cr,uid,ids,{'active':False})
        return True
        #return super(sri_authorization, self).unlink(cr, uid, ids, context)
        
    def check_date_document(self, cr, uid, auth_id, date=None, user = None, context=None):
        try:
            if user and int(user):
                user = self.pool.get('res.users').browse(cr,uid,user)
            else:
                user = user
            auth=self.browse(cr, uid, auth_id, context)
            if ((date >= auth.start_date) and (date <= auth.expiration_date)) or user.old_auth == True:
                return True
            else:
                return False 
        except:
            return False
        
    def on_change_start_date(self, cr, uid, ids, start_date=None, context={}):
        result={}
        if start_date:
            dt = datetime.strptime(start_date, '%Y-%m-%d') + relativedelta(years=1)
            result['expiration_date'] = dt.strftime('%Y-%m-%d')
        return {'value':result}
           
    def get_number(self, cr, uid, auth_ids, journal_type, shop_id=None, printer_id=None, company_id=None, context=None):
        res={}
        if not company_id:
            company_id=self.pool.get('res.company')._company_default_get(cr, uid, 'sri.authorization', context=context)
        if not auth_ids:
            raise osv.except_osv(_('Error!'),_('Does not exist authorization for this document!'))
        if not journal_type:
            raise osv.except_osv(_('Error!'),_('Can not get sequence for missing data: type of journal'))
        for auth in self.browse(cr, uid, auth_ids, context=None ):
            line_id=self.pool.get('sri.authorization.line').search(cr, uid, [('name','=',journal_type),('shop_id','=',shop_id),('printer_id','=',printer_id),('authorization_id','=',auth.id),('authorization_id.company_id','=',company_id)])
            if not line_id:
                raise osv.except_osv(_('Error!'),_(('no authorization to create documents with the type of journal: %s')%(journal_type)))
            line=self.pool.get('sri.authorization.line').browse(cr, uid, line_id[0], context)
            res['padd']=auth.padding
            res['prefix_shop']= line.shop_id.number_sri
            res['prefix_printer']= line.printer_id.number_sri
            res['number_next']=line.number_next
            if not (res['padd'] and res['prefix_shop'] and res['prefix_printer'] and res['number_next']):
                raise osv.except_osv(_('Error!'),_('can not concatenate the series!'))
            return res['prefix_shop'] +'-'+ (res['prefix_printer']) + '-' +  '%%0%sd' % res['padd'] % res['number_next']
        return False 

    def get_id_supplier(self, cr, uid, address=None, sequence=None, code=None, authorization_ids=None, date=None, inv=None, context=None):
        lista=[]
        address_obj = self.pool.get('res.partner.address')
        number=sequence.split('-')
        prefix_shop=None
        prefix_point=None
        if address:
            partner_id = address_obj.browse(cr,uid,address).partner_id.id
            if partner_id:
                address_ids = address_obj.search(cr,uid,[('partner_id','=',partner_id)])
            if not address_ids:
                address_ids = [address]
        
        if not date:
            date = time.strftime('%Y-%m-%d')
        if len(number)>1:
            if len(number)!=3:
                raise osv.except_osv(_('Invalid action!'), _('The format number is incorrect'))
            prefix_shop=number[0]
            prefix_point=number[1]
            sequence=number[2]
        else:
            sequence=number[0]
        for a in sequence:
            if not (a >='0' and a<='9'):
                raise osv.except_osv(_('Error!'),_('the number entered is incorrect!'))
        if not authorization_ids:
#            domain=[('address_id','=',address),('state','=',True),('code_address','=',code)]
            domain=[('address_id','in',address_ids),('start_date','<=',date),('expiration_date','>=',date),('code_address','=',code)]
            authorization_ids = self.search(cr, uid, domain)
            if not authorization_ids:
                line_obj=self.pool.get('sri.authorization.line')
                if inv:
                    line_id = line_obj.search(cr, uid, [('printer_id','=',inv.printer_id.id), ('shop_id','=',inv.shop_id.id), ('name','=',inv.journal_id.type), ('starting_number','<=',int(sequence)),('ending_number','>=',int(sequence))])
                else:
                    line_id = line_obj.search(cr, uid, [('starting_number','<=',int(sequence)),('ending_number','>=',int(sequence))])
                for line in line_obj.browse(cr, uid, line_id, context):
                    if not inv:
                        user_id = 1
                    else:
                        user_id = inv.user_id
                    if self.check_date_document(cr, uid, line.authorization_id.id, date, user_id, context):    
                        authorization_ids = line.authorization_id.id
                        authorization_ids=[authorization_ids]
        else:
            authorization_ids=[authorization_ids]
        for auth in self.browse(cr, uid, authorization_ids, context=None):
            if int(sequence)>=auth.starting_number and int(sequence)<=auth.ending_number:
                if not (auth.padding and auth.prefix_shop and auth.prefix_point):
                    raise osv.except_osv(_('Error!'),_('can not concatenate the series!'))
                if prefix_shop and prefix_shop != auth.prefix_shop:
                    continue
                if prefix_point and prefix_point != auth.prefix_point:
                    continue
                lista.append({'auth':auth.id,'number':auth.prefix_shop +'-'+ auth.prefix_point + '-' +  '%%0%sd' % auth.padding % int(sequence)})
        return lista
  
    def get_auth(self, cr, uid, journal_type, shop_id=None, printer_id=None, sequence=None, company_id=None, date=None, user = None, context=None):
        dic={'auth': None, 'sequence':sequence}
        try:
            if not (shop_id and printer_id):
                return dic
            if sequence:
                number=sequence.split('-')
                prefix_shop=None
                prefix_printer=None
                if len(number)>1:
                    if len(number)!=3:
                        raise osv.except_osv(_('Invalid action!'), _('The format number is incorrect'))
                    prefix_shop=number[0]
                    prefix_printer=number[1]
                    sequence=number[2]
                else:
                    sequence=number[0]
                for a in sequence:
                    if not (a >='0' and a<='9'):
                        raise osv.except_osv(_('Error!'),_('the number entered is incorrect!'))
                if not company_id:
                    company_id=self.pool.get('res.company')._company_default_get(cr, uid, 'sri.authorization', context=context)
                line_obj=self.pool.get('sri.authorization.line')
                if prefix_shop:
                    if self.pool.get('sale.shop').browse(cr, uid, shop_id,context).number_sri != prefix_shop:
                        return dic
                else:
                    prefix_shop=self.pool.get('sale.shop').browse(cr, uid, shop_id,context).number_sri
                if prefix_printer:
                    if self.pool.get('printer.point').browse(cr, uid, printer_id,context).number_sri != prefix_printer:
                        return dic
                else:
                    prefix_printer=self.pool.get('printer.point').browse(cr, uid, printer_id,context).number_sri
                if not date:
                    date=time.strftime('%Y-%m-%d')
                line_id = line_obj.search(cr, uid, [('printer_id','=',printer_id), ('shop_id','=',shop_id), ('name','=',journal_type), ('starting_number','<=',int(sequence)),('ending_number','>=',int(sequence))])
                for line in line_obj.browse(cr, uid, line_id, context):
    #                if not line.authorization_id.auto_printer:
                    if self.check_date_document(cr, uid, line.authorization_id.id, date, user, context):
                        dic['auth']=line.authorization_id.id
                        dic['sequence']=prefix_shop +'-'+ prefix_printer + '-' +  '%%0%sd' % line.authorization_id.padding % int(sequence)
                return dic
        except:
            return dic
        
    def get_line_id(self, cr, uid, journal_type, shop=None, printer=None, auth=None, context={}):
        if not (journal_type and shop and printer and auth):
            return None
        return self.pool.get('sri.authorization.line').search(cr, uid, [('name','=',journal_type),('shop_id','=',shop), ('printer_id','=',printer),('authorization_id','=',auth)])
    
    def get_auth_only(self, cr, uid, type, company_id=None, shop_id=None, printer_id=None, date_document=None, context=None):
        sequence =None
        if not company_id:
            company_id=self.pool.get('res.company')._company_default_get(cr, uid, 'sri.authorization', context=context)            
        if company_id:
            company = self.pool.get('res.company').browse(cr,uid,company_id)            
        dic={'authorization': None, 'sequence':sequence, 'type_printer':'pre'}
        if context is None:
            context = {}
        if not date_document :
            date_document = time.strftime('%Y-%m-%d')
        line_auth_obj = self.pool.get('sri.authorization.line')
        if not (shop_id and printer_id):
            raise osv.except_osv(_('Error!'),_('can not get authorization, data are missing!'))
        else:
            line_auth_ids = line_auth_obj.search(cr, uid, [('name','=',type),('shop_id','=',shop_id), ('printer_id','=',printer_id), ('state', '=',True ),('authorization_id.company_id', '=',company_id )])
#        if self.pool.get('printer.point').browse(cr, uid, printer_id, context).type_printer != 'auto':
#            line_auth_ids = line_auth_obj.search(cr, uid, [('name','=',type),('shop_id','=',shop_id), ('printer_id','=',printer_id), ('state', '=',True ),('authorization_id.company_id', '=',company_id )])
#        else:
#            line_auth_ids = line_auth_obj.search(cr, uid, [('name','=',type),('shop_id','=',shop_id), ('printer_id','=',printer_id), ('state', '=',True ),('authorization_id.company_id', '=',company_id ),('authorization_id.auto_printer', '=',True )])
        #if not line_auth_ids:
         #   raise osv.except_osv(_('Error!'),_('Las cajas que tiene asignada el usuario no tiene autorizaciones activas. Elija otra caja o revise con el administrador de sistemas sus Cajas asignadas.'))
        for line in line_auth_ids:
            line = line_auth_obj.browse(cr,uid,line)
            ct = True
            if self.check_date_document(cr, uid, line.authorization_id.id, date_document[0:10], uid, context):                
                sequence =  line.number_next
                while ct == True:
                    sequence = sequence
                    dic['authorization']=line.authorization_id.id
                    dic['type_printer']=line.type_printer
                    shop_id = line.shop_id.id
                    if shop_id: 
                        prefix_shop=self.pool.get('sale.shop').browse(cr, uid, shop_id,context).number_sri
                    printer_id = line.printer_id.id
                    if printer_id:
                        prefix_printer = self.pool.get('printer.point').browse(cr, uid, printer_id,context).number_sri                
                    dic['sequence']=prefix_shop +'-'+ prefix_printer + '-' +  '%%0%sd' % line.authorization_id.padding % int(sequence)
                    if dic['sequence']:
                        check_number = dic['sequence']
                        cot = self.pool.get('account.invoice').search(cr,uid,[('invoice_number','=',check_number),('partner_id','<>',company.partner_id.id),('journal_id.type','=',type)])
                        if not cot:
                            return dic
                        else:
                            sequence = sequence + 1
            else:
                raise osv.except_osv('Error!', _('No existen autorizaciones en la fecha que fue emitida la factura. Por favor, cambie la fecha de emisión de la retención. O su usuario no tiene permisos para ingresar autorizaciones antiguas'))    

    def verify_expiration_date(self, cr, uid, context):
        lines_obj=self.pool.get('sri.authorization.line')
        auth_ids=self.search(cr, uid, [('auto_expired','!=',True),('expiration_date','<',time.strftime('%Y-%m-%d'))])
        for auth in self.browse(cr, uid, auth_ids, context):
            if auth.auto_printer and auth.state: 
                for line in auth.lines_ids:
                    line_next_ids=lines_obj.search(cr, uid, [('expired','=',True),('name','=',line.name),('shop_id','=',line.shop_id.id),('printer_id','=',line.printer_id.id),('authorization_id.auto_printer','=',True),('authorization_id.start_date','>',auth.expiration_date)])
                    lines_obj.write(cr, uid, line_next_ids, {'expired':False, 'starting_number':line.ending_number+1, 'ending_number':line.ending_number+1}, context)
                    lines_obj.write(cr, uid, [line.id], {'expired':True}, context)
        self.write(cr, uid, auth_ids, {'auto_expired':True})
        return True

    def create_authorization(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        printer_obj = self.pool.get('printer.point')
        doc_obj = self.pool.get('account.journal.type')
        sri_line_obj = self.pool.get('sri.authorization.line')
        doc_ids = []
        for w in self.browse(cr, uid, ids, context):
            if not w.name:
                raise osv.except_osv('Error!', _('Necesita ingresar la autorización para continuar'))
            if not w.start_date or not w.expiration_date:
                raise osv.except_osv('Error!', _('Necesita ingresar las fechas de inicio y fin de la autorización'))
            if not w.company_id:
                raise osv.except_osv('Error!', _('Seleccione la compañía que se le otorgo la autorización'))
            else:
                shop_list = shop_obj.search(cr,uid,[('company_id','=',w.company_id.id),('emision_point','=',True)])
                if shop_list:
                    shop_ids = shop_obj.browse(cr,uid,shop_list)
                else:
                    raise osv.except_osv('Error!', _('No existen puntos de emisión creados para la compañía seleccionada'))
                if shop_ids:
                    for shop in shop_ids:
                        cr.execute("""select ajt.code, ajt.name from account_journal_type ajt
                            left join account_journal aj on aj.type = ajt.code
                            left join rel_shop_journal rsj on rsj.journal_id = aj.id
                            where sri_type_control in ('company','company_partner') 
                            and rsj.shop_id = %s""",(shop.id,))
                        doc_list  = cr.fetchall()
                        if doc_list:
                            for d in doc_list:
                                doc_ids.append(d[0])
                            printer_ids = printer_obj.search(cr,uid,[('shop_id','=',shop.id),('type_printer','=','auto'),('type','=',False)])
                            if printer_ids:
                                for printer in printer_ids:
                                    for doc in doc_ids:
                                        old_auth = sri_line_obj.search(cr,uid,[('printer_id','=',printer),('name','=',doc),('state','=',True)])
                                        if old_auth: 
                                            old_id = sri_line_obj.browse(cr,uid,old_auth[0])                                        
                                            if old_id.state == True:
                                                sri_line_obj.write(cr,uid,old_auth[0],{'state':False,'expired':True})
                                            if old_id.ending_number:
                                                if old_id.ending_number == old_id.starting_number == 1:
                                                    starting_number = 1
                                                else:
                                                    starting_number = old_id.ending_number + 1
                                        else:
                                            starting_number = 1
                                        vals = {'name': doc,
                                                'auto_printer':True, 
                                                'authorization_id':w.id,
                                                'ending_number':starting_number,
                                                'shop_id':shop.id,
                                                'pre_printer':False,
                                                'type_printer':'auto',
                                                'expired':False,
                                                'printer_id':printer,
                                                'starting_number':starting_number,
                                                'number_next':starting_number,
                                                'counter':1,
                                                'range':1,
                                                'state':True
                                                }
                                                
                                        if vals:
                                            sri_line_obj.create(cr,uid,vals)
                                            self.write(cr,uid,ids,{'auth_generate':True})
                else:
                    raise osv.except_osv('Error!', _('No se han creado autorizaciones porque no existen puntos de impresión tipo autoimpresor creadas para el punto de emisión seleccionado'))
                
        return True

    def onchange_type(self, cr,uid,ids, type_printer,company_id,name, context=None):
        result = {}
        if type_printer == 'pre':
            result['auto_printer']= False
            if name:
                if not len(name)==10:
                    raise osv.except_osv('Error!', _('La autorización debe contener 10 dígitos cuando son documentos preimpresos'))    
        else:
            result['auto_printer']= True
            if type_printer == 'auto':
                if name:
                    if not len(name)==10:
                        raise osv.except_osv('Error!', _('La autorización debe contener 10 dígitos cuando son documentos autoimpresos'))
                if company_id:
                    partner_id = self.pool.get('res.company').browse(cr,uid,company_id).partner_id.id
                    if partner_id:
                        address_id = self.pool.get('res.partner.address').search(cr,uid,[('partner_id','=',partner_id),('type','=','default')])
                        if address_id:
                            result['address_id'] = address_id[0]
            elif type_printer == 'electronic':
                if not name or len(name)<10:
                    name = '00'+time.strftime('%Y%m%d')
                    result['name']= name
                if company_id:
                    partner_id = self.pool.get('res.company').browse(cr,uid,company_id).partner_id.id
                    if partner_id:
                        address_id = self.pool.get('res.partner.address').search(cr,uid,[('partner_id','=',partner_id),('type','=','default')])
                        if address_id:
                            result['address_id'] = address_id[0]                                   
        return {'value':result}
        
sri_authorization()
