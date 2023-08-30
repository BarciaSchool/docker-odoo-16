# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-presente STRACONX S.A. 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv
from datetime import datetime
from tools.translate import _
import time
from xml.etree.ElementTree import Element, SubElement, tostring
import base64

class straconx_invoice(osv.osv):
    
    _inherit = 'account.invoice'
    
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
        for inv in self.browse(cr, uid, ids, context=context):
            #Factura de venta que será convertida en xml 
            invoice_ventas = self.pool.get('account.invoice').browse(cr, uid, inv.id, context)
            if invoice_ventas.journal_id.type == 'sale':                
                root = Element("factura")
                code = '1'
            elif invoice_ventas.journal_id.type == 'sale_refund':
                root = Element("notaCredito")
                code = '4'
            elif invoice_ventas.journal_id.type == 'debit_note':
                root = Element("notaDebito")
                code = '5'
                            
            if invoice_ventas and invoice_ventas.authorization_sales:
                info_tributaria = SubElement(root,"infoTributaria")
                SubElement(info_tributaria,"razonSocial").text=invoice_ventas.company_id.name
                SubElement(info_tributaria,"ruc").text = invoice_ventas.company_id.vat[2:]
                SubElement(info_tributaria,"numAut").text = invoice_ventas.authorization
                SubElement(info_tributaria,"codDoc").text = code
                SubElement(info_tributaria,"estab").text = invoice_ventas.shop_id.number_sri
                SubElement(info_tributaria,"ptoEmi").text = invoice_ventas.printer_id.number_sri
                SubElement(info_tributaria,"secuencial").text = invoice_ventas.invoice_number[8:]
                SubElement(info_tributaria,"fechaAutorizacion").text = invoice_ventas.authorization_sales.start_date[8:10]+'/'+invoice_ventas.authorization_sales.start_date[5:7]+'/'+invoice_ventas.authorization_sales.start_date[:4]
                SubElement(info_tributaria,"caducidad").text = invoice_ventas.authorization_sales.expiration_date[8:10]+'/'+invoice_ventas.authorization_sales.expiration_date[5:7]+'/'+invoice_ventas.authorization_sales.expiration_date[:4]
                SubElement(info_tributaria,"fechaEmision").text = invoice_ventas.date_invoice[8:10]+'/'+invoice_ventas.date_invoice[5:7]+'/'+invoice_ventas.date_invoice[:4]
                SubElement(info_tributaria,"dirMatriz").text = invoice_ventas.company_id.street
                SubElement(info_tributaria,"razonSocialComprador").text = invoice_ventas.partner_id.name
                if invoice_ventas.partner_id.type_vat <> 'consumidor':
                    SubElement(info_tributaria,"rucCedulaComprador").text = invoice_ventas.partner_id.vat[2:]                                
                delivery_guide = self.pool.get('stock.delivery').search(cr,uid,[('invoice_id','=',ids[0])])
                if code<>'5':
                    if delivery_guide:
                        SubElement(info_tributaria,"guiaRemision").text = invoice_ventas.delivery_number.number
                    else:
                        SubElement(info_tributaria,"guiaRemision").text = " "
                SubElement(info_tributaria,"contribuyenteEspecial").text = invoice_ventas.company_id.resolution_sri
                SubElement(info_tributaria,"obligado").text = "Obligado a Llevar Contabilidad"
                if code in ('4','5'):
                    SubElement(info_tributaria,"codDocModificado").text = "1"
                    SubElement(info_tributaria,"numDocModificado").text = invoice_ventas.old_invoice_id.invoice_number
                    SubElement(info_tributaria,"numAutDocSustento").text = invoice_ventas.old_invoice_id.authorization
                    SubElement(info_tributaria,"fechaEmisionDocSustento").text = invoice_ventas.old_invoice_id.date_invoice[8:10]+'/'+invoice_ventas.old_invoice_id.date_invoice[5:7]+'/'+invoice_ventas.old_invoice_id.date_invoice[:4]
                    SubElement(info_tributaria,"valorModificacion").text = self.formato_numero(str(invoice_ventas.amount_untaxed))
                if code=='1':
                    SubElement(info_tributaria,"totalSinImpuestos").text = self.formato_numero(str(invoice_ventas.amount_untaxed))                                                
                SubElement(info_tributaria,"ICE").text = "0.00"
                SubElement(info_tributaria,"baseNoObjetoIVA").text = self.formato_numero(str(invoice_ventas.amount_base_vat_untaxes))                                                
                SubElement(info_tributaria,"baseIVA0").text = self.formato_numero(str(invoice_ventas.amount_base_vat_00))
                SubElement(info_tributaria,"baseIVA12").text = self.formato_numero(str(invoice_ventas.amount_base_vat_12))
                SubElement(info_tributaria,"IVA12").text = self.formato_numero(str(invoice_ventas.amount_total_vat))
                if code=='1':
                    SubElement(info_tributaria,"propina").text = "0.00"
                    SubElement(info_tributaria,"totalConImpuestos").text = self.formato_numero(str(invoice_ventas.amount_total))
                    SubElement(info_tributaria,"moneda").text = "Dólares"
                if code in ('4','5'):
                    SubElement(info_tributaria,"ValorTotal").text = self.formato_numero(str(invoice_ventas.amount_total))
                    motivo = SubElement(root,"motivo")
                    SubElement(motivo,"motivo").text = invoice_ventas.motive_id.name                                                                    
                if code=='1':
                    detalle = SubElement(root,"detalle")
                    for lines in invoice_ventas.invoice_line:
                        SubElement(detalle,"concepto").text = lines.name
                        SubElement(detalle,"cantidad").text = self.formato_numero(str(round(lines.quantity,2)))
                        SubElement(detalle,"precioUnitario").text = self.formato_numero(str(round(lines.price_product,2)))
                        SubElement(detalle,"descuentos").text = self.formato_numero(str(round(lines.price_product - lines.price_unit,2)))
                        SubElement(detalle,"precioTotal").text = self.formato_numero(str(round(lines.price_unit,2)))
                        SubElement(detalle,"detAdicional01").text = " "
                        SubElement(detalle,"detAdicional02").text = " "
                        SubElement(detalle,"detAdicional03").text = " "                                        
                info_adicional = SubElement(root,"infoAdicional")
                SubElement(info_adicional,"campoAdicional", nombre="DirecionEstablecimiento").text = invoice_ventas.shop_id.partner_address_id.street
                SubElement(info_adicional,"campoAdicional", nombre="NombreComercial").text = invoice_ventas.shop_id.name                    
                SubElement(info_adicional,"campoAdicional",nombre="rucFirmante").text = invoice_ventas.company_id.vat[2:]                 
                SubElement(info_adicional,"campoAdicional", nombre="cedulaFirmante").text = invoice_ventas.partner_id.vat[2:]
                SubElement(info_adicional,"campoAdicional", nombre="ImpuestoISD").text ="0.00"                                
            self.indent(root)
        return tostring(root,encoding="UTF-8")    

    def action_number(self, cr, uid, ids, context=None):
        result = super(straconx_invoice, self).action_number(cr, uid, ids, context)
        for invoice in self.browse(cr,uid,ids,context):
            if invoice.automatic:
                self.act_export(cr,uid,ids,context)
        return result

    def act_export(self, cr, uid, ids, context={}):        
        this = self.browse(cr, uid, ids)[0]
        if this.type in ('out_invoice','out_refund'):
            root = self.generate_xml(cr,uid,ids)
            inv_name = this.invoice_number+".xml"
            out=base64.encodestring(root)
            self.write(cr, uid, ids, {'xml_file':out, 'name':inv_name}, context=context)
            self.pool.get('ir.attachment').create(cr,uid,{'res_model':'account.invoice',
                                                          'company_id':this.company_id.id,
                                                          'res_name':inv_name,
                                                          'datas_fname':inv_name,
                                                          'type':'binary',
                                                          'res_id':this.id,
                                                          'description':'Generación automática de xml de la factura '+inv_name,
                                                          'datas':out,
                                                          'name':inv_name,
                                                          })
        return True

    def action_open_draft(self, cr, uid, ids, context=None):
        attach_obj = self.pool.get('ir.attachment')
        for invoice in self.browse(cr, uid, ids):
            attach_ids = attach_obj.search(cr, uid, [('res_model', '=', 'account.invoice'), ('res_id', '=', invoice.id)])
            if attach_ids:
                attach_obj.unlink(cr,uid,attach_ids)
            self.write(cr,uid,ids,{'name':''})           
        super(straconx_invoice, self).action_open_draft(cr, uid, ids, context)
        return True

straconx_invoice()
