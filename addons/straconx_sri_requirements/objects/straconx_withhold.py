# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-presente STRACONX S.A. 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv
from tools.translate import _
import time
from xml.etree.ElementTree import Element, SubElement, tostring
import base64

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
        

    def generate_xml(self, cr, uid, ids, context=None):
        root = ''
        for withhold in self.browse(cr, uid, ids, context=context):
            #Retención que será convertida en xml 
            withhold_id = self.pool.get('account.withhold').browse(cr, uid, withhold.id, context)
            if withhold_id:                
                root = Element("comprobanteRetencion")
                code = "7"
                            
            if withhold_id:
                info_tributaria = SubElement(root,"infoTributaria")
                SubElement(info_tributaria,"razonSocial").text=withhold_id.company_id.name
                SubElement(info_tributaria,"ruc").text = withhold_id.company_id.vat[2:]
                SubElement(info_tributaria,"numAut").text = withhold_id.authorization_purchase.name
                SubElement(info_tributaria,"codDoc").text = code
                SubElement(info_tributaria,"estab").text = withhold_id.shop_id.number_sri
                SubElement(info_tributaria,"ptoEmi").text = withhold_id.printer_id.number_sri
                SubElement(info_tributaria,"secuencial").text = withhold_id.number[8:]
                SubElement(info_tributaria,"fechaAutorizacion").text = withhold_id.authorization_purchase.start_date[8:10]+'/'+withhold_id.authorization_purchase.start_date[5:7]+'/'+withhold_id.authorization_purchase.start_date[:4]
                SubElement(info_tributaria,"fechaEmision").text = withhold_id.date[8:10]+'/'+withhold_id.date[5:7]+'/'+withhold_id.date[:4]                                
                SubElement(info_tributaria,"dirMatriz").text = withhold_id.company_id.street
                SubElement(info_tributaria,"razonSocialSujetoRetenido").text = withhold_id.partner_id.name
                SubElement(info_tributaria,"rucCedulaSujetoRetenido").text = withhold_id.partner_id.vat[2:]                
                SubElement(info_tributaria,"ejercicioFiscal").text = withhold_id.fiscalyear_id.name                
                SubElement(info_tributaria,"caducidad").text = withhold_id.authorization_purchase.expiration_date[8:10]+'/'+withhold_id.authorization_purchase.expiration_date[5:7]+'/'+withhold_id.authorization_purchase.expiration_date[:4]
                if withhold_id.company_id.property_account_position.name=='CONTRIBUYENTES ESPECIALES':
                    SubElement(info_tributaria,"contribuyenteEspecial").text = withhold_id.company_id.resolution_sri[3:]
                SubElement(info_tributaria,"obligado").text = "Obligado a Llevar Contabilidad"

                
                impuestos = SubElement(root,"impuestos")
                impuesto = SubElement(impuestos,"impuesto")
                for lines in withhold_id.withhold_line_ids:
                    SubElement(impuesto,"nombre").text = lines.tax_id.name
                    SubElement(impuesto,"baseImponible").text = self.formato_numero(str(round(lines.tax_base,2)))
                    SubElement(impuesto,"porcentajeRetener").text = self.formato_numero(str(round(lines.percentage,2)))
                    SubElement(impuesto,"valorRetenido").text = self.formato_numero(str(round(lines.retained_value,2)))
                    SubElement(impuesto,"codDocSustento").text = "1"
                    SubElement(impuesto,"numDocSustento").text = lines.invoice_id.invoice_number                                                                
                info_adicional = SubElement(root,"infoAdicional")
                SubElement(info_adicional,"campoAdicional", nombre="DirecionEstablecimiento").text = withhold_id.invoice_id.shop_id.partner_address_id.street
                SubElement(info_adicional,"campoAdicional", nombre="NombreComercial").text = withhold_id.shop_id.name                    
                SubElement(info_adicional,"campoAdicional", nombre="rucFirmante").text = withhold_id.partner_id.vat[2:]
                SubElement(info_adicional,"campoAdicional", nombre="cedulaFirmante").text = withhold_id.partner_id.vat[2:]                
                SubElement(info_adicional,"campoAdicional", nombre="ConvenioDobleTributacion").text = " "                 
                SubElement(info_adicional,"campoAdicional", nombre="documentoIFIS").text = " "
                SubElement(info_adicional,"campoAdicional", nombre="valorpagadoIRsociedaddividendos").text = " "

            
            self.indent(root)
        return tostring(root,encoding="UTF-8")    
    
    def action_aprove(self,cr,uid,ids,context=None):
        result = super(account_withhold, self).action_aprove(cr,uid,ids,context)        
        if not context:
            context = {}        
        for witthold in self.browse(cr,uid,ids,context):
            if witthold.automatic and witthold.transaction_type=='purchase':
                self.act_export(cr,uid,ids,context)
        return result

    def act_export(self, cr, uid, ids, context={}):        
        this = self.browse(cr, uid, ids)[0]
        if this.transaction_type=='purchase' and this.invoice_id.automatic:
            root = self.generate_xml(cr,uid,ids)
            withhold_name = this.number+".xml"
            out=base64.encodestring(root)
            self.write(cr, uid, ids, {'name':withhold_name}, context=context)
            self.pool.get('ir.attachment').create(cr,uid,{'res_model':'account.withhold',
                                                          'company_id':this.company_id.id,
                                                          'res_name':withhold_name,
                                                          'datas_fname':withhold_name,
                                                          'type':'binary',
                                                          'res_id':this.id,
                                                          'description':'Generación automática de xml de Comprobante de Retención # '+withhold_name,
                                                          'datas':out,
                                                          'name':withhold_name,
                                                          })
        return True
            

    def action_annulled(self,cr,uid,ids,context=None):
        attach_obj = self.pool.get('ir.attachment')
        for withhold in self.browse(cr, uid, ids):
            attach_ids = attach_obj.search(cr, uid, [('res_model', '=', 'account.withhold'), ('res_id', '=', withhold.id)])
            if attach_ids:
                attach_obj.unlink(cr,uid,attach_ids)           
        res = super(account_withhold,self).action_annulled(cr,uid,ids,context)
        return True

    
account_withhold()
