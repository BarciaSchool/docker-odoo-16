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

class stock_delivery(osv.osv):
    
    _inherit = 'stock.delivery'
    
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
        for dlgd in self.browse(cr, uid, ids, context=context):
            #Guía de Remisión que será convertida en xml 
            delivery_guide = self.pool.get('stock.delivery').browse(cr, uid, dlgd.id, context)
            if delivery_guide:                
                root = Element("guiaRemision")
                code = "6"
                            
            if delivery_guide:
                info_tributaria = SubElement(root,"infoTributaria")
                SubElement(info_tributaria,"razonSocial").text=delivery_guide.picking_id.company_id.name
                SubElement(info_tributaria,"ruc").text = delivery_guide.picking_id.company_id.vat[2:]
                SubElement(info_tributaria,"numAut").text = delivery_guide.authorization_id.name
                SubElement(info_tributaria,"codDoc").text = code
                SubElement(info_tributaria,"estab").text = delivery_guide.picking_id.shop_id.number_sri
                SubElement(info_tributaria,"ptoEmi").text = delivery_guide.picking_id.printer_id.number_sri
                SubElement(info_tributaria,"secuencial").text = delivery_guide.number[8:]
                SubElement(info_tributaria,"fechaAutorizacion").text = delivery_guide.authorization_id.start_date[8:10]+'/'+delivery_guide.authorization_id.start_date[5:7]+'/'+delivery_guide.authorization_id.start_date[0:4]
                SubElement(info_tributaria,"dirMatriz").text = delivery_guide.picking_id.company_id.street
                SubElement(info_tributaria,"dirPartida").text = delivery_guide.picking_id.shop_id.partner_address_id.street
                SubElement(info_tributaria,"razonSocialTransportista").text = delivery_guide.picking_id.carrier_id.partner_id.name
                SubElement(info_tributaria,"rucTransportista").text = delivery_guide.picking_id.carrier_id.partner_id.vat[2:]
                SubElement(info_tributaria,"caducidad").text = delivery_guide.picking_id.authorization_id.expiration_date[8:10]+'/'+delivery_guide.authorization_id.expiration_date[5:7]+'/'+delivery_guide.authorization_id.expiration_date[:4]
                SubElement(info_tributaria,"contribuyenteEspecial").text = delivery_guide.picking_id.company_id.resolution_sri
                SubElement(info_tributaria,"obligado").text = "Obligado a Llevar Contabilidad"
                SubElement(info_tributaria,"motivoTraslado").text = delivery_guide.motivo
                SubElement(info_tributaria,"fechaIniTransporte").text = delivery_guide.date[8:10]+'/'+delivery_guide.date[5:7]+'/'+delivery_guide.date[:4]
                SubElement(info_tributaria,"fechaFinTransporte").text = delivery_guide.date[8:10]+'/'+delivery_guide.date[5:7]+'/'+delivery_guide.date[:4]
                SubElement(info_tributaria,"placa").text = delivery_guide.picking_id.carrier_id.placa
                destinatarios = SubElement(root,"destinatarios")
                destinatario = SubElement(destinatarios,"destinatarios")
                if delivery_guide.picking_id.partner_id:
                    SubElement(destinatario,"rucCedulaDestinatario").text = delivery_guide.picking_id.partner_id.vat[2:]
                    SubElement(destinatario,"razonSocialComprador").text = delivery_guide.picking_id.partner_id.name
                else:
                    SubElement(destinatario,"rucCedulaDestinatario").text = delivery_guide.picking_id.address_id.partner_id.vat[2:]
                    SubElement(destinatario,"razonSocialComprador").text = delivery_guide.picking_id.address_id.partner_id.name
                SubElement(destinatario,"dirDestinatario").text = delivery_guide.picking_id.address_id.street
                SubElement(destinatario,"codEstbDestino").text = "001"
                SubElement(destinatario,"ruta").text = delivery_guide.picking_id.shop_id.partner_address_id.location_id.name +" - " +delivery_guide.picking_id.address_id.location_id.name
                if delivery_guide.invoice_id:
                    SubElement(destinatario,"codDocSustento").text = "1"
                    SubElement(destinatario,"numDocSustento").text = delivery_guide.invoice_id.invoice_number
                    SubElement(destinatario,"numAutSustento").text = delivery_guide.invoice_id.authorization
                    SubElement(destinatario,"fechaEmisionDocSustento").text = delivery_guide.invoice_id.date_invoice[8:10]+'/'+delivery_guide.invoice_id.date_invoice[5:7]+'/'+delivery_guide.invoice_id.date_invoice[:4]
                detalles = SubElement(root,"detalles")
                detalle = SubElement(detalles,"detalle")
                for lines in delivery_guide.picking_id.move_lines:
                    SubElement(detalle,"concepto").text = lines.name
                    SubElement(detalle,"cantidad").text = self.formato_numero(str(round(lines.product_qty,2)))
                    SubElement(detalle,"detAdicional01",nombre="Código").text = lines.ref_product
                    SubElement(detalle,"detAdicional02",nombre="Categoría").text = lines.product_id.categ_id.name
                    SubElement(detalle,"detAdicional03",nombre="Clasificación").text = lines.product_id.clasification_cat.name                                        
                info_adicional = SubElement(root,"infoAdicional")
                SubElement(info_adicional,"campoAdicional", nombre="DirecionEstablecimiento").text = delivery_guide.picking_id.shop_id.partner_address_id.street
                SubElement(info_adicional,"campoAdicional", nombre="NombreComercial").text = delivery_guide.picking_id.shop_id.name                    
                SubElement(info_adicional,"campoAdicional", nombre="Dirección Transportista").text = delivery_guide.picking_id.carrier_id.partner_id.address[0].street                 
                if delivery_guide.picking_id.warehouse_id.partner_id:
                    SubElement(info_adicional,"campoAdicional", nombre="identificacionRemitente").text = delivery_guide.picking_id.warehouse_id.partner_id.vat[2:]
                else:
                    raise osv.except_osv(_('Información requerida!'), _('El despachador %s de esta guía de remisión no tiene identificación. Verifique que este creado como Empresa.')%(delivery_guide.picking_id.warehouse_id.partner_id.name))
                SubElement(info_adicional,"campoAdicional", nombre="rucFirmante").text = delivery_guide.picking_id.address_id.partner_id.vat[2:]
                SubElement(info_adicional,"campoAdicional", nombre="cedulaFirmante").text = delivery_guide.picking_id.address_id.partner_id.vat[2:]            
            self.indent(root)
        return tostring(root,encoding="UTF-8")
        
    
    def action_delivery_create(self, cr, uid, ids, datos=None, context=None):
        if context is None:
            context = {}
        warning={}
        delivery_obj = self.pool.get('stock.picking')
        invoice_id_obj = self.pool.get('account.invoice')
        res = {}
        if datos:
            authorization_id = datos.get('authorization_id',False)
            if authorization_id:
                authorization_id = authorization_id[0]
            else:
                raise osv.except_osv(_('Invalid Action!'), _('Need a authorization for create delivery guide.'))
            picking_id = datos.get('picking_id',False)
            if picking_id:
                picking_id = picking_id
                invoice_obj = invoice_id_obj.search(cr,uid,([]))
            else:
                raise osv.except_osv(_('Invalid Action!'), _('Need a picking for create delivery guide.')) 
            number = datos.get('delivery_number',False)
            carrier_id = datos.get('carrier_id',False)
            invoice_id = datos.get('invoice_id',False)
            if invoice_id:
                invoice_id = invoice_id
            else:
                invoice_id = False

            picking_data = self.pool.get('stock.picking').browse(cr,uid,picking_id)
            if picking_data.type == 'out':
                motivo = 'VENTA'
            elif picking_data.type == 'internal':
                motivo = 'TRASLADO ENTRE SUCURSALES' 
            elif picking_data.type == 'in':
                motivo = 'RECEPCION DE MERCADERÍA DE PROVEEDORES'
            
            date_due = delivery_obj.browse(cr,uid,picking_id).date_expected           

            delivery_vals = {
                'digiter_id':uid,
                'date':datos.get('delivery_date',False),
                'state':datos.get('delivery_status',False),
                'number':datos.get('delivery_number',False),
                'authorization_id':authorization_id,
                'picking_id':picking_id,
                'invoice_id':invoice_id,
                'carrier_id': carrier_id[0],
                'name':datos.get('delivery_number',False),
                'motivo':motivo,
                'date_due':date_due,
                'comment':datos.get('comment',False),
            }
            delivery = self.create(cr, uid, delivery_vals, context=context)            
            res = [delivery]
            if invoice_id:
                invoice_id_obj.write(cr,uid,[invoice_id],{'delivery_status':datos.get('delivery_status',False),'delivery_number':delivery})
            delivery_obj.write(cr,uid,[picking_id],{'delivery_status':datos.get('delivery_status',False),
                                                  'delivery_number':datos.get('delivery_number',False),
                                                  'delivery_date':datos.get('delivery_date',False),
                                                  'warehouse_id_delivery':uid,
                                                  'delivery_guide_id':delivery,
                                                  'authorization_id':authorization_id})         
            self.act_export(cr,uid,[delivery],context)
        return res

    def act_export(self, cr, uid, ids, context={}):        
        this = self.browse(cr, uid, ids)[0]
        root = self.generate_xml(cr,uid,ids)
        delivery_name = this.number+".xml"
        out=base64.encodestring(root)
        self.write(cr, uid, ids, {'xml_file':out, 'name':delivery_name}, context=context)
        self.pool.get('ir.attachment').create(cr,uid,{'res_model':'stock.delivery',
                                                      'company_id':this.picking_id.company_id.id,
                                                      'res_name':delivery_name,
                                                      'datas_fname':delivery_name,
                                                      'type':'binary',
                                                      'res_id':this.id,
                                                      'description':'Generación automática de xml de Guía de Remisión # '+delivery_name,
                                                      'datas':out,
                                                      'name':delivery_name,
                                                      })
        return True
            
    _columns = {
                'xml_file':fields.binary('Archivo'),
                 }


    
stock_delivery()
