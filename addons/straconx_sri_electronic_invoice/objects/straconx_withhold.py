# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

from osv import fields,osv
from datetime import datetime
from tools.translate import _
import time
from xml.etree.ElementTree import Element, SubElement, tostring
import base64
import subprocess
from random import randrange
import netsvc
from account_voucher import account_voucher

class account_withhold(osv.osv):
    
    _inherit = 'account.withhold'
    
    mes_lista=[]
    
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
       
    def formato_numero(self,valor):
        tup= valor.split('.')
        if len(tup[1])== 1:
            return valor+"0"
        return valor
    
    def valor(self,tup):
        if tup:
            return tup[0]
        else:
            return 0.0
        
    def mod11(self, list, max_weight=7):

        sum = 0
        weight = 2

        for item in reversed(list):
            sum += item * weight
            weight += 1
    
            if weight > max_weight:
                weight = 2

        mod = 11 - sum % 11

        if mod == 11:
            return 0
        elif mod == 10:
            return 1
        else:
            return mod


    def generate_xml_electronic(self, cr, uid, ids, context=None):
        root = ''
        for withhold in self.browse(cr, uid, ids, context=context):
            #Retención que será convertida en xml 
            withhold_id = self.pool.get('account.withhold').browse(cr, uid, withhold.id, context)
            if withhold_id:                
                root = Element("comprobanteRetencion", id="comprobante", version="1.0.0")
                code = "07"
                            
            if withhold_id:
                info_tributaria = SubElement(root,"infoTributaria")
                SubElement(info_tributaria,"ambiente").text=withhold_id.authorization_purchase.environment
                SubElement(info_tributaria,"tipoEmision").text=withhold_id.authorization_purchase.type_emision                
                SubElement(info_tributaria,"razonSocial").text=withhold_id.company_id.name
                SubElement(info_tributaria,"nombreComercial").text = withhold_id.shop_id.name
                SubElement(info_tributaria,"ruc").text = withhold_id.company_id.vat[2:]
                SubElement(info_tributaria,"claveAcceso").text = withhold_id.authorization
                SubElement(info_tributaria,"codDoc").text = code
                SubElement(info_tributaria,"estab").text = withhold_id.shop_id.number_sri
                SubElement(info_tributaria,"ptoEmi").text = withhold_id.printer_id.number_sri
                SubElement(info_tributaria,"secuencial").text = withhold_id.number[8:]
                SubElement(info_tributaria,"dirMatriz").text = withhold_id.company_id.street
                info_factura = SubElement(root,"infoCompRetencion")
                SubElement(info_factura,"fechaEmision").text = withhold_id.date[8:10]+'/'+withhold_id.date[5:7]+'/'+withhold_id.date[:4]                                
                SubElement(info_factura,"dirEstablecimiento").text = withhold_id.shop_id.partner_address_id.street
                if withhold_id.company_id.property_account_position.name=='CONTRIBUYENTES ESPECIALES':
                    SubElement(info_factura,"contribuyenteEspecial").text = withhold_id.company_id.resolution_sri[3:]
                SubElement(info_factura,"obligadoContabilidad").text = "SI"
                if withhold_id.partner_id.type_vat == 'ruc':
                    identificacion = '04'
                elif withhold_id.partner_id.type_vat == 'ci':
                    identificacion = '05'
                elif withhold_id.partner_id.type_vat == 'pasaporte':
                    identificacion = '06'
                elif withhold_id.partner_id.type_vat == 'consumidor':
                    identificacion = '07'
                elif withhold_id.partner_id.type_vat == 'exterior':
                    identificacion = '08'
                elif withhold_id.partner_id.type_vat == 'placa':
                    identificacion = '09'
                SubElement(info_factura,"tipoIdentificacionSujetoRetenido").text =identificacion                
                SubElement(info_factura,"razonSocialSujetoRetenido").text = withhold_id.partner_id.name
                SubElement(info_factura,"identificacionSujetoRetenido").text = withhold_id.partner_id.vat[2:]                
                SubElement(info_factura,"periodoFiscal").text = withhold_id.period_id.name                

                impuestos = SubElement(root,"impuestos")                
                for lines in withhold_id.withhold_line_ids:
                    impuesto = SubElement(impuestos,"impuesto")                    
                    if lines.tax_id.base_code_id.tax_type == 'withhold_vat':
                        SubElement(impuesto,"codigo").text = '2'
                        if lines.percentage== 10:
                            SubElement(impuesto,"codigoRetencion").text = "9"
                        elif lines.percentage== 20:
                            SubElement(impuesto,"codigoRetencion").text = "10"                                                
                        elif lines.percentage== 30:
                            SubElement(impuesto,"codigoRetencion").text = "1"
                        elif lines.percentage== 70:
                            SubElement(impuesto,"codigoRetencion").text = "2"
                        elif lines.percentage== 100:
                            SubElement(impuesto,"codigoRetencion").text = "3"                            
                    elif lines.tax_id.base_code_id.tax_type == 'withhold':
                        SubElement(impuesto,"codigo").text = '1'
                        SubElement(impuesto,"codigoRetencion").text = lines.tax_id.description
                    elif lines.tax_id.base_code_id.tax_type == 'isd':
                        SubElement(impuesto,"codigo").text = '6'
                        SubElement(impuesto,"codigoRetencion").text = lines.tax_id.description                    
                    SubElement(impuesto,"baseImponible").text = self.formato_numero(str(round(lines.tax_base,2)))
                    SubElement(impuesto,"porcentajeRetener").text = self.formato_numero(str(round(lines.percentage,2)))
                    SubElement(impuesto,"valorRetenido").text = self.formato_numero(str(round(lines.retained_value,2)))
                    SubElement(impuesto,"codDocSustento").text = "01"            
                    SubElement(impuesto,"numDocSustento").text=lines.invoice_id.invoice_number.replace('-','')                                                   
                info_adicional = SubElement(root,"infoAdicional")
                SubElement(info_adicional,"campoAdicional", nombre="DirecionEstablecimiento").text = withhold_id.shop_id.partner_address_id.street
                SubElement(info_adicional,"campoAdicional", nombre="NombreComercial").text = withhold_id.shop_id.name                    
                SubElement(info_adicional,"campoAdicional", nombre="rucFirmante").text = withhold_id.partner_id.vat[2:]
                SubElement(info_adicional,"campoAdicional", nombre="cedulaFirmante").text = withhold_id.partner_id.vat[2:]                            
            self.indent(root)
        return tostring(root,encoding="UTF-8")    
    
    def action_aprove(self,cr,uid,ids,context=None):
        result = super(account_withhold, self).action_aprove(cr,uid,ids,context)
        if not context:
            context = {}        
        for witthold in self.browse(cr,uid,ids,context):
            if witthold.electronic and witthold.transaction_type=='purchase':
                date_inv = time.strftime('%d%m%Y')                
                code = '07'
                context.update({'code_sri':code})
                vat = witthold.company_id.vat[2:]
                environment = witthold.authorization_purchase.environment
                type_emision = witthold.authorization_purchase.type_emision
                serie = witthold.shop_id.number_sri+witthold.printer_id.number_sri
                secuencial = witthold.number_purchase[8:]
                n_code = time.strftime('%d%Y%m')
                numeric_code = date_inv+code+str(vat)+str(environment)+str(serie)+str(secuencial)+str(n_code)+type_emision
                lst = [int(i) for i in str(numeric_code)]
                digit = self.mod11(lst, 7)
                authorization = str(numeric_code)+str(digit)
                if len(authorization)<>49:
                    raise osv.except_osv(_('Error!'), _('La clave de autorización es diferente a 48 dígitos, que es el valor requerido por el SRI.'))
                self.write(cr,uid,[witthold.id],{'authorization':authorization})
                self.act_export_electronic(cr,uid,ids,context)
        return result

    def act_export_electronic(self, cr, uid, ids, context={}):        
        this = self.browse(cr, uid, ids)[0]
        if context:
            code_sri = context.get('code_sri',False)
        if not code_sri:
            raise osv.except_osv(_('Error!'), _('No se ha definido el tipo de documento del SRI.'))
        root = self.generate_xml_electronic(cr,uid,ids)
        company_path = this.company_id.electronic_path
        withhold_name = this.number+".xml"
        out=base64.encodestring(root)
        type_model = '05'
        pref = 'RET_'
        self.write(cr, uid, ids, {'name':withhold_name, 'access_key': this.authorization, 'electronic':True}, context=context)
        att_id = self.pool.get('ir.attachment').create(cr,uid,{'res_model':'account.withhold',
                                                      'company_id':this.company_id.id,
                                                      'res_name':withhold_name,
                                                      'datas_fname':pref+withhold_name,
                                                      'type':'binary',
                                                      'res_id':this.id,
                                                      'description':'Generación automática de xml de Comprobante de Retención # '+withhold_name,
                                                      'sri_code':type_model,
                                                      'access_key': this.authorization,
                                                      'partner_id': this.partner_id.id,
                                                      'datas_unsigned':out,
                                                      'name':withhold_name,
                                                      'electronic': True,
                                                      'type_model':code_sri,
                                                      'sign_state': '0',
                                                          })
        self.pool.get('ir.attachment').write(cr,uid,[att_id],{})
        cr.commit()
        self.pool.get('sri.send.document').sri_send_document_ids(cr, uid, [att_id], context)                        
        return True


    def print_withhold(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for withhold in self.browse(cr, uid, ids, context=context): 
            if not withhold.electronic:
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

            else:
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
                       'report_name': 'account_withhold_ride_id',
                       'datas' : data,
                       'context': context,
                       'nodestroy': True,
                       }                
            return True 

    def print_withhold_electronic(self, cr, uid, ids, context=None):      
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
                   'report_name': 'account_withhold_ride_id',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 


    def action_annulled(self,cr,uid,ids,context=None):
        attach_obj = self.pool.get('ir.attachment')
        for withhold in self.browse(cr, uid, ids):
            attach_ids = attach_obj.search(cr, uid, [('res_model', '=', 'account.withhold'), ('res_id', '=', withhold.id)])
            if attach_ids:
                attach_obj.unlink(cr,uid,attach_ids)           
        res = super(account_withhold,self).action_annulled(cr,uid,ids,context)
        return True

    _columns = {
                'electronic':fields.boolean('electronic'),
                'authorization':fields.char('Authorization', size=50, readonly=True),
                'access_key':fields.char('Clave de Acceso', size=50),
                'sri_authorization':fields.char('SRI Autorización', size=50, readonly=True),
                'sri_date':fields.datetime('Fecha Autorización')
                }
    
account_withhold()
