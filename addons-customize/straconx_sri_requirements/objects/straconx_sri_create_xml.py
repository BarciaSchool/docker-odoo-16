# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields,osv
from tools.translate import _
import time
import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
import base64


class sri_create_xml(osv.osv):
    
    def indent(self,elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
                
    def create_new_authorization_sri(self, cr, uid, autorizacion, w, fecha, context={}):
        if not w.authorization:
            raise osv.except_osv('Error!', _('Por favor, verifique que exista la información sobre la autorización.'))
        SubElement(autorizacion,"numAut").text=w.authorization
        SubElement(autorizacion,"fecha").text=fecha[2]+"/"+fecha[1]+"/"+fecha[0]
        detalles = SubElement(autorizacion,"detalles")
        sri_auth = self.pool.get('sri.authorization').search(cr,uid,[('name','=',w.authorization)])
        if sri_auth:
            auth_ids = self.pool.get('sri.authorization.line').search(cr,uid,[('authorization_id','=',sri_auth),('type_printer','=','auto')], order='shop_id') 
            if auth_ids:                                                                      
                lauthorization_ids = self.pool.get('sri.authorization.line').browse(cr,uid,auth_ids)
        if w.authorization_ids:
            authorization_ids = w.authorization_ids
        else:
            authorization_ids = lauthorization_ids 
        if authorization_ids:
            for auth in authorization_ids:
                detalle = SubElement(detalles,"detalle")
                if auth.name:
                    name_ids = self.pool.get('account.journal.type').search(cr,uid,[('code','=',auth.name),('sri_type_document','!=',False)])
                    if name_ids:
                        name_doc = self.pool.get('account.journal.type').browse(cr,uid,name_ids[0]).sri_type_document.code
                        SubElement(detalle,"codDoc").text=str(int(name_doc))
                        SubElement(detalle,"estab").text=auth.shop_id.number_sri
                        SubElement(detalle,"ptoEmi").text=auth.printer_id.number_sri
                        if context.get('inicio',False):
                            SubElement(detalle,"inicio").text=str(auth.starting_number)
            return True
        else:
            raise osv.except_osv('Error!', _('Por favor, verifique que existan documentos creados en las Tiendas sobre la autorización %s.')%(w.authorization))

    def create_structure_sri(self, cr, uid, autorizacion, w, fecha, context={}):
        if not w.authorization_ids:
            raise osv.except_osv('Error!', _('Por favor, verifique que existan la información sobre la autorización.'))
        SubElement(autorizacion,"numAut").text=w.authorization_ids[0].authorization_id.name
        SubElement(autorizacion,"fecha").text=fecha[2]+"/"+fecha[1]+"/"+fecha[0]
        detalles = SubElement(autorizacion,"detalles")
        for auth in w.authorization_ids:
            detalle = SubElement(detalles,"detalle")
            if w.tipo_documento:
                name_ids = self.pool.get('account.journal.type').search(cr,uid,[('sri_type_document','=',w.tipo_documento.id)])
                if name_ids:
                    name_doc = self.pool.get('account.journal.type').browse(cr,uid,name_ids[0]).sri_type_document.code
                else:
                    name_doc = ""
            SubElement(detalle,"codDoc").text=str(int(name_doc))
            SubElement(detalle,"estab").text=auth.prefix_shop
            SubElement(detalle,"ptoEmi").text=auth.prefix_point
            if context.get('inicio',False):
                SubElement(detalle,"inicio").text=str(auth.starting_number)
            elif context.get('fin',False):
                SubElement(detalle,"fin").text=str(auth.ending_number)
        return True

    def delete_structure_sri(self, cr, uid, autorizacion, w, fecha, context={}):
        if not w.authorization_old_ids:
            raise osv.except_osv('Error!', _('Por favor, verifique que existan la información sobre la autorización.'))
        SubElement(autorizacion,"numAut").text=w.authorization_old_ids[0].authorization_id.name
        SubElement(autorizacion,"fecha").text=fecha[2]+"/"+fecha[1]+"/"+fecha[0]
        detalles = SubElement(autorizacion,"detalles")
        for auth in w.authorization_old_ids:
            detalle = SubElement(detalles,"detalle")
            if auth.name:
                name_ids = self.pool.get('account.journal.type').search(cr,uid,[('code','=',auth.name),('sri_type_document','!=',None)])
                if name_ids:
                    name_doc = self.pool.get('account.journal.type').browse(cr,uid,name_ids[0]).sri_type_document.code
                    if not name_doc:
                        raise osv.except_osv('Error!', _('El tipo de comprobante %s no tiene asignada un tipo de documento del SRI. Por favor revisar .')%(auth.name))
            SubElement(detalle,"codDoc").text=str(int(name_doc))
            SubElement(detalle,"estab").text=auth.prefix_shop
            SubElement(detalle,"ptoEmi").text=auth.prefix_point
            if context.get('inicio',False):
                SubElement(detalle,"inicio").text=str(auth.starting_number)
            elif context.get('fin',False):
                SubElement(detalle,"fin").text=str(auth.ending_number)
        return True

    
    def create_structure_sri_change(self, cr, uid, autorizacion, w, fecha, context={}):
        SubElement(autorizacion,"fecha").text=fecha[2]+"/"+fecha[1]+"/"+fecha[0]
        if not w.authorization_old_ids and w.authorization_ids:
            raise osv.except_osv('Error!', _('Por favor, verifique que existan la nueva y anterior autorización.'))
        if len(w.authorization_old_ids) <> len(w.authorization_ids):
            raise osv.except_osv('Error!', _('Por favor, verifique que el número de autorizaciones nuevas y antiguas coincidan.'))
        SubElement(autorizacion,"autOld").text=w.authorization_old_ids[0].authorization_id.name
        SubElement(autorizacion,"autNew").text=w.authorization_ids[0].authorization_id.name
        detalles = SubElement(autorizacion,"detalles")
        authorization_ids = [w.authorization_ids[-1]]
        for auth in authorization_ids:
            if w.tipo_documento:
                name_ids = self.pool.get('account.journal.type').search(cr,uid,[('sri_type_document','=',w.tipo_documento.id)])
                if name_ids:
                    name_doc = self.pool.get('account.journal.type').browse(cr,uid,name_ids[0]).sri_type_document.code
                else:
                    raise osv.except_osv('Error!', _('Por favor, verifique que exista el tipo de documento definido.'))                        
            for old in w.authorization_old_ids:
                detalle = SubElement(detalles,"detalle")
                SubElement(detalle,"codDoc").text=str(int(name_doc))
                SubElement(detalle,"estab").text=auth.prefix_shop
                SubElement(detalle,"ptoEmi").text=auth.prefix_point
                SubElement(detalle,"finOld").text=str(old.ending_number)
                SubElement(detalle,"iniNew").text=str(old.ending_number+1)
        return True
        
    
    def generate_xml(self, cr, uid, ids, context=None):
        autorizacion = ''
        for w in self.browse(cr, uid, ids, context=context):
            fecha=(str(w.date_report))
            fecha=fecha.split('-')
            autorizacion = Element("autorizacion")
            SubElement(autorizacion,"codTipoTra").text=w.type_transaction_id.code
            SubElement(autorizacion,"ruc").text=w.company_id.partner_id.vat[2:]
            if w.type_transaction_id.code in ('6','27'):
                self.create_new_authorization_sri(cr, uid, autorizacion, w, fecha, {'inicio':True})
            if w.type_transaction_id.code in ('10','23'):
                self.create_new_authorization_sri(cr, uid, autorizacion, w, fecha, {'inicio':True})
            elif w.type_transaction_id.code in ('7','8','24','25'):
                self.create_structure_sri_change(cr, uid, autorizacion, w, fecha, context)
            elif w.type_transaction_id.code in ('11','28'):
                self.create_structure_sri(cr, uid, autorizacion, w, fecha, {'fin':True})
            elif w.type_transaction_id.code in ('9','26'):
                self.delete_structure_sri(cr, uid, autorizacion, w, fecha, {'fin':True})
        self.indent(autorizacion)
        return tostring(autorizacion,encoding="UTF-8")
    
    
    def act_export(self, cr, uid, ids, context={}):
        this = self.browse(cr, uid, ids)[0]
        root = self.generate_xml(cr,uid,ids)
        auth_name = this.type_transaction_id.name+".xml"
        name = auth_name
        out=base64.encodestring(root)
        self.write(cr, uid, ids, {'data':out, 'name':name, 'state': 'get'}, context=context)
        self.pool.get('ir.attachment').create(cr,uid,{'res_model':'sri.generate.xml',
                                              'company_id':this.company_id.id,
                                              'res_name':auth_name,
                                              'datas_fname':auth_name,
                                              'type':'binary',
                                              'res_id':this.id,
                                              'description':'Generación automática de xml de Reporte de Rangos # '+auth_name,
                                              'datas':out,
                                              'name':auth_name,
                                              })

        return True
        
    
    def get_authorization(self, cr, uid, ids, context=None):
        for w in self.browse(cr, uid, ids, context):
            if w.tipo_emision == 'auto_printer':
                type_emision = 'auto'
            elif w.tipo_emision == 'document_electronic':
                type_emision = 'electronic'
            if not w.type_transaction_id:
                raise osv.except_osv('Error!', _('Por favor, elija un tipo de transacción para este asistente'))
            if not w.shop_id and w.printer_id:
                raise osv.except_osv('Error!', _('Por favor seleccione el punto de emisión y punto de impresión'))
            if w.type_transaction_id.code in ('6','27','10','23'):
                auth_id = w.authorization        
                auth_ids=self.pool.get('sri.authorization').search(cr, uid, [('name','=',auth_id),('type_printer','=',type_emision),('state','=',True)])
            elif w.type_transaction_id.code in ('9','26'):
                auth_ids=self.pool.get('sri.authorization').search(cr, uid, [('type_printer','=',type_emision),('state','=',False)])
            if auth_ids:
                auth_lines_ids = self.pool.get('sri.authorization.line').search(cr,uid,[('authorization_id','=',auth_ids[-1])])
                if auth_lines_ids:
                    self.write(cr, uid, [w.id], {'authorization_old_ids':[[6, 0, auth_lines_ids]]})                
                    name_doc = []
                    for docs in w.tipo_documento:
                        name_ids = self.pool.get('account.journal.type').search(cr,uid,[('sri_type_document','=',docs.id)])
                        if name_ids:
                            name_docs = self.pool.get('account.journal.type').browse(cr,uid,name_ids[0]).code
                            if name_docs:
                                name_doc.append(name_docs)
                    if not name_doc:
                        raise osv.except_osv('Error!', _('Por favor, seleccione los tipos de documentos que desea incluir en la autorización'))
                    if w.this_shop:
                        domain_1=[('auto_printer','=',True),('name','in',name_doc),('state','=',True),('authorization_id','=',auth_ids[0])]
                        domain_2=[('auto_printer','=',True),('name','in',name_doc),('state','=',False),('authorization_id','=',auth_ids[0])]                    
                    else:
                        if w.this_printer:
                            domain_1=[('shop_id','=',w.shop_id.id),('auto_printer','=',True),('name','in',name_doc),('state','=',True),('authorization_id','=',auth_ids[0])]
                            domain_2=[('shop_id','=',w.shop_id.id),('auto_printer','=',True),('name','in',name_doc),('state','=',False),('authorization_id','=',auth_ids[0])]                    
                        else:
                            domain_1=[('shop_id','=',w.shop_id.id),('printer_id','=',w.printer_id.id),('auto_printer','=',True),('name','in',name_doc),('state','=',True),('authorization_id','=',auth_ids[0])]
                            domain_2=[('shop_id','=',w.shop_id.id),('printer_id','=',w.printer_id.id),('auto_printer','=',True),('name','in',name_doc),('state','=',False),('authorization_id','=',auth_ids[0])]                                        

                    if w.type_transaction_id.code not in ('9','26'):
                        auth_ids=self.pool.get('sri.authorization.line').search(cr, uid, domain_1)
                    else:
                        auth_ids = []
                    auth_old_ids=[]
                    auth_old_ids=self.pool.get('sri.authorization.line').search(cr, uid, domain_2)
                    self.write(cr, uid, [w.id], {'authorization_ids':[[6, 0, auth_ids]],'authorization_old_ids':[[6, 0, auth_old_ids]]})
        return True
    
    def onchange_shop(self, cr, uid, ids, shop_id=None,context={}):
        res = {'printer_id':None}
        if not shop_id:
            return res
        cash_list=[]
        shop=self.pool.get('sale.shop').browse(cr, uid, shop_id, context)
        for cash in shop.printer_point_ids:
            cash_list.append(cash.id)
        if cash_list:
            res['printer_id']=cash_list[0]
        return {'value':res}
    
    def onchange_transaction(self, cr, uid, ids, transaction_id=None,context={}):
        res = {}
        if not transaction_id:
            return res
        transaction=self.pool.get('sri.type.transaction').browse(cr, uid, transaction_id, context)
        if transaction.code in ('6','27','10','23'):
            res['required_auth_new']= True    
        else:
            res['required_auth_old']=transaction.required_auth_old
            res['authorization_old']=None
        return {'value':res}
       
    _name = 'sri.generate.xml'
    
    _columns = {
                'name':fields.char('name', size=80, readonly=True),
                'date_report': fields.date('Date Report'),
                'company_id': fields.many2one('res.company', 'Company'),
                'shop_id':fields.many2one('sale.shop', 'Shop'),
                'printer_id':fields.many2one('printer.point', 'Printer Point'),
                'type_transaction_id':fields.many2one('sri.type.transaction', 'Type Transaction', required=False),
                'required_auth_old':fields.boolean('required_auth_old', required=False),
                'required_auth_new':fields.boolean('required_auth_new', required=False),
                'authorization_name':fields.char('authorization', size=10),
                'authorization_old':fields.char('authorization old', size=10),
                'authorization_ids': fields.many2many('sri.authorization.line', 'generate_authorization_rel', 'generate_id', 'authorization_id', 'Authorizations', help="Define the authorization for generate document"),
                'authorization_old_ids': fields.many2many('sri.authorization.line', 'generate_authorization_old_rel', 'generate_id', 'authorization_id', 'Authorizations', help="Define the old authorization for generate document"),
                'tipo_documento':fields.many2many('sri.document.type','generate_document_rel' ,'generate_id','name','Tipo de Documento'),                
                'this_shop': fields.boolean('Todos los Puntos de Emisión'),
                'this_printer': fields.boolean('Todos los Puntos de Impresión'),
                'data':fields.binary('File', readonly=True),
                'authorization': fields.char('Nueva Autorización',size=10),
                'tipo_emision':fields.selection([
                    ('auto_printer','Auto Impresor'),
                    ('document_electronic','Documento Electrónico'),
                    ],'Tipo de Emisor', select=True, required=True),                
                'state':fields.selection([
                ('choose','Choose'),
                ('get','Get'),
                ], 'state', required=True, readonly=True),
                 }
    _defaults = {
                 'state': lambda *a: 'choose',
                 'tipo_emision':'auto_printer',
                 'this_shop': True,
                 'this_printer': True,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'sri.generate.xml', context=c),
                 }
    
sri_create_xml()