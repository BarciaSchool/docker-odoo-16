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
        for dlgd in self.browse(cr, uid, ids, context=context):
            #Guía de Remisión que será convertida en xml 
            delivery_guide = self.pool.get('stock.delivery').browse(cr, uid, dlgd.id, context)
            ir_attachment_obj =  self.pool.get('ir.attachment')
            if delivery_guide:                
                root = Element("guiaRemision", id="comprobante", version="1.0.0")
                code = "06"
                            
            if delivery_guide:
                info_tributaria = SubElement(root,"infoTributaria")
                SubElement(info_tributaria,"ambiente").text=delivery_guide.authorization_id.environment
                SubElement(info_tributaria,"tipoEmision").text=delivery_guide.authorization_id.type_emision                
                SubElement(info_tributaria,"razonSocial").text=delivery_guide.picking_id.company_id.name
                SubElement(info_tributaria,"ruc").text = delivery_guide.picking_id.company_id.vat[2:]
                SubElement(info_tributaria,"claveAcceso").text = delivery_guide.authorization
                SubElement(info_tributaria,"codDoc").text = code
                SubElement(info_tributaria,"estab").text = delivery_guide.number[0:3]
                SubElement(info_tributaria,"ptoEmi").text = delivery_guide.number[4:7   ]
                SubElement(info_tributaria,"secuencial").text = delivery_guide.number[8:]
                SubElement(info_tributaria,"dirMatriz").text = delivery_guide.picking_id.company_id.street
                infoGuiaRemision = SubElement(root,"infoGuiaRemision")
                SubElement(infoGuiaRemision,"dirEstablecimiento").text = delivery_guide.picking_id.shop_id.partner_address_id.street
                SubElement(infoGuiaRemision,"dirPartida").text = delivery_guide.picking_id.shop_id.partner_address_id.street
                SubElement(infoGuiaRemision,"razonSocialTransportista").text = delivery_guide.picking_id.carrier_id.partner_id.name
                if delivery_guide.picking_id.carrier_id.partner_id.type_vat == 'ruc':
                    identificacion = '04'
                elif delivery_guide.picking_id.carrier_id.partner_id.type_vat == 'ci':
                    identificacion = '05'
                elif delivery_guide.picking_id.carrier_id.partner_id.type_vat == 'pasaporte':
                    identificacion = '06'
                elif delivery_guide.picking_id.carrier_id.partner_id.type_vat == 'consumidor':
                    identificacion = '07'
                elif delivery_guide.picking_id.carrier_id.type_vat == 'exterior':
                    identificacion = '08'
                elif delivery_guide.picking_id.carrier_id.type_vat == 'placa':
                    identificacion = '09'
                else:
                    identificacion = '06'
                SubElement(infoGuiaRemision,"tipoIdentificacionTransportista").text = identificacion
                SubElement(infoGuiaRemision,"rucTransportista").text = delivery_guide.picking_id.carrier_id.partner_id.vat[2:]
                SubElement(infoGuiaRemision,"obligadoContabilidad").text = "SI"                
                SubElement(infoGuiaRemision,"contribuyenteEspecial").text = delivery_guide.picking_id.company_id.resolution_sri[3:]
                SubElement(infoGuiaRemision,"fechaIniTransporte").text = delivery_guide.date[8:10]+'/'+delivery_guide.date[5:7]+'/'+delivery_guide.date[:4]
                SubElement(infoGuiaRemision,"fechaFinTransporte").text = delivery_guide.date[8:10]+'/'+delivery_guide.date[5:7]+'/'+delivery_guide.date[:4]
                SubElement(infoGuiaRemision,"placa").text = delivery_guide.placa
                destinatarios = SubElement(root,"destinatarios")
                destinatario = SubElement(destinatarios,"destinatario")
                SubElement(destinatario,"identificacionDestinatario").text = delivery_guide.picking_id.partner_id.vat[2:]
                SubElement(destinatario,"razonSocialDestinatario").text = delivery_guide.picking_id.partner_id.name
                SubElement(destinatario,"dirDestinatario").text = delivery_guide.picking_id.address_id.street
                SubElement(destinatario,"motivoTraslado").text = delivery_guide.motivo
                SubElement(destinatario,"codEstabDestino").text = "001"
                SubElement(destinatario,"ruta").text = delivery_guide.picking_id.shop_id.partner_address_id.location_id.name +" - " +delivery_guide.picking_id.address_id.location_id.name
                if delivery_guide.invoice_id:
                    SubElement(destinatario,"codDocSustento").text = "01"
                    SubElement(destinatario,"numDocSustento").text = delivery_guide.invoice_id.invoice_number
                    if delivery_guide.invoice_id.electronic:
                        if delivery_guide.invoice_id.sri_authorization:
                            SubElement(destinatario,"numAutDocSustento").text = delivery_guide.invoice_id.sri_authorization
                        else:
                            ia_ids = ir_attachment_obj.search(cr,uid,[('res_id','=',delivery_guide.invoice_id.id),('res_model','=','account.invoice'),('active','=',True)])
                            if ia_ids:
                                ia_authorization = ir_attachment_obj.browse(cr,uid,ia_ids[0]).number_auth
                                if ia_authorization:
                                    SubElement(destinatario,"numAutDocSustento").text = ia_authorization                                
                    else:
                        SubElement(destinatario,"numAutDocSustento").text = delivery_guide.invoice_id.authorization
                    SubElement(destinatario,"fechaEmisionDocSustento").text = delivery_guide.invoice_id.date_invoice[8:10]+'/'+delivery_guide.invoice_id.date_invoice[5:7]+'/'+delivery_guide.invoice_id.date_invoice[:4]
                detalles = SubElement(destinatario,"detalles")                
                for lines in delivery_guide.picking_id.move_lines:
                    detalle = SubElement(detalles,"detalle")
                    SubElement(detalle,"codigoInterno").text = lines.ref_product
                    SubElement(detalle,"descripcion").text = lines.product_id.name
                    SubElement(detalle,"cantidad").text = self.formato_numero(str(round(lines.product_qty,2)))
                info_adicional = SubElement(root,"infoAdicional")
                if delivery_guide.picking_id.warehouse_id.partner_id:
                    SubElement(info_adicional,"campoAdicional", nombre="identificacionRemitente").text = delivery_guide.picking_id.warehouse_id.partner_id.vat[2:]
                else:
                    raise osv.except_osv(_('Información requerida!'), _('El despachador %s de esta guía de remisión no tiene identificación. Verifique que este creado como Empresa.')%(delivery_guide.picking_id.warehouse_id.partner_id.name))
                SubElement(info_adicional,"campoAdicional", nombre="nombreRemitente").text = delivery_guide.picking_id.warehouse_id.partner_id.name            
            self.indent(root)
        return tostring(root,encoding="UTF-8")
        
    
    def action_delivery_create(self, cr, uid, ids, datos=None, context=None):
        if context is None:
            context = {}
        warning={}
        delivery_obj = self.pool.get('stock.picking')
        invoice_id_obj = self.pool.get('account.invoice')
        authorization_obj = self.pool.get('sri.authorization')
        code = '06'
        res = {}
        invoice_id = False
        if datos:
            authorization_id = datos.get('authorization_id',False)
            if authorization_id:
                authorization_id = authorization_id[0]
                authorization_sales = authorization_obj.browse(cr,uid,authorization_id,context)
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
                'authorization': authorization_sales.name,
                'picking_id':picking_id,
                'invoice_id':invoice_id,
                'carrier_id': carrier_id[0],
                'driver':datos.get('driver',False),
                'placa':datos.get('placa',False),
                'name':datos.get('delivery_number',False),
                'motivo':motivo,
                'date_due':date_due,
                'comment':datos.get('comment',False),       
            }
            delivery = self.create(cr, uid, delivery_vals, context=context)            
            res = [delivery]
            delivery_id = self.browse(cr,uid,delivery)
            if invoice_id:
                invoice_id_obj.write(cr,uid,[invoice_id],{'delivery_status':datos.get('delivery_status',False),'delivery_number':delivery})
            delivery_obj.write(cr,uid,[picking_id],{'delivery_status':datos.get('delivery_status',False),
                                                  'delivery_number':datos.get('delivery_number',False),
                                                  'delivery_date':datos.get('delivery_date',False),
                                                  'warehouse_id_delivery':uid,
                                                  'delivery_guide_id':delivery,
                                                  'authorization_id':authorization_id})                     
            if authorization_sales.type_printer == 'electronic':
                vat = delivery_id.picking_id.company_id.partner_id.vat[2:]
                environment = authorization_sales.environment
                type_emision = authorization_sales.type_emision
                serie = datos.get('delivery_number',False)[0:3]+datos.get('delivery_number',False)[4:7]
                secuencial = datos.get('delivery_number',False)[8:]
                delivery_date = datos.get('delivery_date',False)
                if delivery_date:
                    n_code = delivery_date[8:10]+delivery_date[5:7]+delivery_date[0:4]
                else:
                    n_code = time.strftime('%d%Y%m')
                date_inv = time.strftime('%d%m%Y')
                numeric_code = date_inv+code+str(vat)+str(environment)+str(serie)+str(secuencial)+str(n_code)+type_emision
                lst = [int(i) for i in str(numeric_code)]
                digit = self.mod11(lst, 7)
                if not delivery_id.authorization or len(delivery_id.authorization)<>49:
                    authorization = str(numeric_code)+str(digit)
                    if len(authorization)<>49:
                        raise osv.except_osv(_('Error!'), _('La clave de autorización es diferente a 48 dígitos, que es el valor requerido por el SRI.'))
                    self.write(cr,uid,[delivery],{'authorization':authorization,'electronic':True, 'access_key':authorization})
                context['code_sri']='04'
                self.act_export_electronic(cr,uid,[delivery],context)
            else:                
                self.act_export(cr,uid,[delivery],context)
        return res

    def act_export_electronic(self, cr, uid, ids, context={}):        
        this = self.browse(cr, uid, ids)[0]
        if context:
            code_sri = context.get('code_sri',False)
        if not code_sri:
            raise osv.except_osv(_('Error!'), _('No se ha definido el tipo de documento del SRI.'))
        root = self.generate_xml_electronic(cr,uid,ids)
        company_path = this.picking_id.company_id.electronic_path
        delivery_name = this.number+".xml"
        out=base64.encodestring(root)
        type_model='06'
        pref = 'GR_'
        self.write(cr, uid, ids, {'xml_file':out, 'name':delivery_name, 'access_key': this.authorization}, context=context)
        att_id = self.pool.get('ir.attachment').create(cr,uid,{
                                                      'res_model':'stock.delivery',
                                                      'company_id':this.company_id.id,
                                                      'res_name':delivery_name,
                                                      'datas_fname':pref+delivery_name,
                                                      'type':'binary',
                                                      'res_id':this.id,
                                                      'description':'Generación automática de xml de Guía de Remisión # '+delivery_name,
                                                      'sri_code': code_sri,
                                                      'datas_unsigned':out,
                                                      'datas':out,
                                                      'access_key': this.authorization,
                                                      'name':delivery_name,
                                                      'partner_id': this.picking_id.partner_id.id,
                                                      'electronic': True,
                                                      'type_model':type_model,
                                                      'sign_state': '0',
                                                          })
        self.pool.get('ir.attachment').write(cr,uid,[att_id],{})
        cr.commit()
        att_id = att_id
#          
#         if this.id:
#             cmd = "java -jar %s/dist/firmante.jar %s"%(company_path,att_id)
#         cmd = str(cmd) 
#         call = ["/bin/bash", "-c", cmd]
#         ret = subprocess.call(call, stdout=None, stderr=None)
#         if ret > 0:
#             print "Warning - result was %d" % ret            
        return True


    def unlink(self, cr, uid, ids, context=None):
        sri_obj = self.pool.get('sri.authorization')
        for delivery in self.browse(cr, uid, ids, context=context):
            authorization_id = self.browse(cr,uid,delivery.id).authorization_id.id
            type_printer = sri_obj.browse(cr,uid,authorization_id).type_printer
            if type_printer == 'electronic':
                raise osv.except_osv(_('Error!'), _('No se puede anular una Guía de Remisión Electrónica. Por favor, solicite al área de contabilidad su eliminación en el sitio del SRI primero.'))                
            picking_id = self.browse(cr,uid,delivery.id).picking_id.id
            invoice_id = self.browse(cr,uid,delivery.id).invoice_id.id
            self.pool.get('stock.picking').write(cr, uid,picking_id, {
                                'delivery_status':'draft',
                                'delivery_number':None,
                                'delivery_date':None,
                                'warehouse_id_delivery':None,
                                'delivery_guide_id':False,
                                'dn_invoiced':None,
                                'authorization_id':False,
                                })
            self.pool.get('account.invoice').write(cr,uid,invoice_id,{
                                'delivery_status':'draft',
                                'delivery_number': False
                                })
#        self.unlink(cr,uid,delivery)
        cr.execute("""update stock_delivery set write_date =now(), state='cancel' where id in %s""",(tuple(ids),))
#        return super(stock_delivery, self).unlink(cr, uid, ids, context=context)



    def print_delivery(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for delivery in self.browse(cr, uid, ids, context=context): 
            if delivery:
                nb_print = delivery.nb_print + 1
                self.write(cr,uid,[delivery.id],{'nb_print':nb_print})    
                data = {}
                data['model'] = 'stock.delivery'
                data['ids'] = ids
                context['active_id']=delivery.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'delivery_guide_not_invoiced',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
        return True       


    def print_delivery_electronic(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for delivery in self.browse(cr, uid, ids, context=context): 
            nb_print = delivery.nb_print + 1
            self.write(cr,uid,[delivery.id],{'nb_print':nb_print})
            if delivery:
                data = {}
                data['model'] = 'stock.delivery'
                data['ids'] = ids
                context['active_id']=delivery.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'delivery_guide_ride_id',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
        return True   

            
    _columns = {
                'electronic':fields.boolean('electronic'),
                'authorization':fields.char('Authorization', size=50, readonly=True),
                'access_key':fields.char('Clave de Acceso', size=50),                
                'sri_authorization':fields.char('SRI Autorización', size=50, readonly=True),
                'sri_date':fields.datetime('Fecha Autorización')                
                }

    
stock_delivery()
