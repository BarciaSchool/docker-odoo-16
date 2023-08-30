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


class straconx_invoice(osv.osv):

    _inherit = 'account.invoice'

    mes_lista = []

    def indent(self, elem, level=0):
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

    def formato_numero(self, valor):
        tup = valor.split('.')
        if len(tup[1]) == 1:
            return valor+"0"
        return valor

    def valor(self, tup):
        if tup:
            return tup[0]
        else:
            return 0.0

    def generate_xml_electronic(self, cr, uid, ids, context=None):
        root = ''
        for inv in self.browse(cr, uid, ids, context=context):
            #  Factura de venta que será convertida en xml
            invoice_ventas = self.pool.get('account.invoice').browse(cr, uid, inv.id, context)
            if invoice_ventas.journal_id.type == 'sale':
                root = Element("factura", id="comprobante", version="1.0.0")
                code = '01'
                if invoice_ventas and invoice_ventas.authorization_sales:
                    info_tributaria = SubElement(root, "infoTributaria")
                    SubElement(info_tributaria, "ambiente").text = invoice_ventas.authorization_sales.environment
                    SubElement(info_tributaria, "tipoEmision").text = invoice_ventas.authorization_sales.type_emision
                    SubElement(info_tributaria, "razonSocial").text = invoice_ventas.company_id.name
                    SubElement(info_tributaria, "nombreComercial").text = invoice_ventas.shop_id.name
                    SubElement(info_tributaria, "ruc").text = invoice_ventas.company_id.vat[2:]
                    SubElement(info_tributaria, "claveAcceso").text = invoice_ventas.authorization
                    SubElement(info_tributaria, "codDoc").text = code
                    SubElement(info_tributaria, "estab").text = invoice_ventas.shop_id.number_sri
                    SubElement(info_tributaria, "ptoEmi").text = invoice_ventas.printer_id.number_sri
                    SubElement(info_tributaria, "secuencial").text = invoice_ventas.invoice_number[8:]
                    SubElement(info_tributaria, "dirMatriz").text = invoice_ventas.company_id.street
                    info_factura = SubElement(root, "infoFactura")
                    SubElement(info_factura, "fechaEmision").text = invoice_ventas.date_invoice[8:10]+'/'+invoice_ventas.date_invoice[5:7]+'/'\
                        + invoice_ventas.date_invoice[:4]
                    SubElement(info_factura, "dirEstablecimiento").text = invoice_ventas.shop_id.partner_address_id.street
                    if invoice_ventas.company_id.property_account_position.name == 'CONTRIBUYENTES ESPECIALES':
                        SubElement(info_factura, "contribuyenteEspecial").text = invoice_ventas.company_id.resolution_sri[3:]
                    SubElement(info_factura, "obligadoContabilidad").text = "SI"
                    if invoice_ventas.partner_id.type_vat == 'ruc':
                        identificacion = '04'
                    elif invoice_ventas.partner_id.type_vat == 'ci':
                        identificacion = '05'
                    elif invoice_ventas.partner_id.type_vat == 'pasaporte':
                        identificacion = '06'
                    elif invoice_ventas.partner_id.type_vat == 'consumidor':
                        identificacion = '07'
                    elif invoice_ventas.partner_id.type_vat == 'exterior':
                        identificacion = '08'
                    elif invoice_ventas.partner_id.type_vat == 'placa':
                        identificacion = '09'
                    else:
                        identificacion = '06'
                    SubElement(info_factura, "tipoIdentificacionComprador").text = identificacion
                    delivery_guide = self.pool.get('stock.delivery').search(cr, uid, [('invoice_id', '=', ids[0])])
                    if code != '05':
                        if delivery_guide:
                            SubElement(info_factura, "guiaRemision").text = invoice_ventas.delivery_number.number
    #                     else:
    #                         SubElement(info_factura, "guiaRemision").text = ""
                    SubElement(info_factura, "razonSocialComprador").text = invoice_ventas.partner_id.name
                    SubElement(info_factura, "identificacionComprador").text = invoice_ventas.partner_id.vat[2:]
                    if code == '01':
                        SubElement(info_factura, "totalSinImpuestos").text = self.formato_numero(str(invoice_ventas.amount_untaxed))
                        SubElement(info_factura, "totalDescuento").text = "0.00"
                    total_impuestos = SubElement(info_factura, "totalConImpuestos")
                    if invoice_ventas.amount_base_vat_12 > 0.00:
                        tax_code = invoice_ventas.amount_total_vat / invoice_ventas.amount_base_vat_12
                        if 0.119 <= tax_code <= 0.124:
                            codigoPorcentaje = "2"
                        elif 0.125 <= tax_code <= 0.149:
                            codigoPorcentaje = "3"
                        totalImpuesto = SubElement(total_impuestos, "totalImpuesto")
                        SubElement(totalImpuesto, "codigo").text = "2"
                        SubElement(totalImpuesto, "codigoPorcentaje").text = codigoPorcentaje
                        SubElement(totalImpuesto, "baseImponible").text = self.formato_numero(str(invoice_ventas.amount_base_vat_12))
                        SubElement(totalImpuesto, "valor").text = self.formato_numero(str(invoice_ventas.amount_total_vat))
                    if invoice_ventas.amount_base_vat_00 > 0.00:
                        totalImpuesto = SubElement(total_impuestos, "totalImpuesto")
                        SubElement(totalImpuesto, "codigo").text = "2"
                        SubElement(totalImpuesto, "codigoPorcentaje").text = "0"
                        SubElement(totalImpuesto, "baseImponible").text = self.formato_numero(str(invoice_ventas.amount_base_vat_00))
                        SubElement(totalImpuesto, "valor").text = "0.00"
                    SubElement(info_factura, "propina").text = "0.00"
                    SubElement(info_factura, "importeTotal").text = self.formato_numero(str(invoice_ventas.amount_total))
                    SubElement(info_factura, "moneda").text = "DOLAR"
                    if code == '01':
                        detalles = SubElement(root, "detalles")
                        for lines in invoice_ventas.invoice_line:
                            detalle = SubElement(detalles, "detalle")
                            if lines.product_id.default_code:
                                SubElement(detalle, "codigoPrincipal").text = lines.product_id.default_code
                            SubElement(detalle, "codigoAuxiliar").text = lines.product_id.default_code or lines.name[:25]
                            SubElement(detalle, "descripcion").text = lines.name
                            SubElement(detalle, "cantidad").text = self.formato_numero(str(round(lines.quantity, 2)))
                            SubElement(detalle, "precioUnitario").text = self.formato_numero(str(round(lines.price_unit, 2)))
                            SubElement(detalle, "descuento").text = "0.00"
                            SubElement(detalle, "precioTotalSinImpuesto").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                            impuestos = SubElement(detalle, "impuestos")
                            impuesto = SubElement(impuestos, "impuesto")
                            if lines.iva_value > 0.00:
                                tax_code = round(lines.iva_value/lines.price_subtotal, 2)
                                if 0.119 <= tax_code <= 0.124:
                                    codigoPorcentaje = "2"
                                    tarifa = "12"
                                elif 0.125 <= tax_code <= 0.144:
                                    codigoPorcentaje = "3"
                                    tarifa = "14"
                                SubElement(impuesto, "codigo").text = "2"
                                SubElement(impuesto, "codigoPorcentaje").text = codigoPorcentaje
                                SubElement(impuesto, "tarifa").text = tarifa
                                SubElement(impuesto, "baseImponible").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                                SubElement(impuesto, "valor").text = self.formato_numero(str(round(lines.iva_value, 2)))
                            elif lines.iva_value == 0.00:
                                SubElement(impuesto, "codigo").text = "2"
                                SubElement(impuesto, "codigoPorcentaje").text = "0"
                                SubElement(impuesto, "tarifa").text = "0"
                                SubElement(impuesto, "baseImponible").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                                SubElement(impuesto, "valor").text = self.formato_numero(str(round(lines.iva_value, 2)))
                    info_adicional = SubElement(root, "infoAdicional")
                    SubElement(info_adicional, "campoAdicional", nombre="rucFirmante").text = invoice_ventas.company_id.vat[2:]
                    SubElement(info_adicional, "campoAdicional", nombre="cedulaFirmante").text = invoice_ventas.partner_id.vat[2:]
                    if invoice_ventas.address_invoice_id.email:
                        SubElement(info_adicional, "campoAdicional", nombre="Email").text = invoice_ventas.address_invoice_id.email
            elif invoice_ventas.journal_id.type == 'sale_refund':
                root = Element("notaCredito", id="comprobante", version="1.0.0")
                code = '04'
                if invoice_ventas and invoice_ventas.authorization_sales:
                    if invoice_ventas.partner_id.type_vat == 'ruc':
                        identificacion = '04'
                    elif invoice_ventas.partner_id.type_vat == 'ci':
                        identificacion = '05'
                    elif invoice_ventas.partner_id.type_vat == 'pasaporte':
                        identificacion = '06'
                    elif invoice_ventas.partner_id.type_vat == 'consumidor':
                        identificacion = '07'
                    elif invoice_ventas.partner_id.type_vat == 'exterior':
                        identificacion = '08'
                    elif invoice_ventas.partner_id.type_vat == 'placa':
                        identificacion = '09'
                    else:
                        identificacion = '06'
                    info_tributaria = SubElement(root, "infoTributaria")
                    SubElement(info_tributaria, "ambiente").text = invoice_ventas.authorization_sales.environment
                    SubElement(info_tributaria, "tipoEmision").text = invoice_ventas.authorization_sales.type_emision
                    SubElement(info_tributaria, "razonSocial").text = invoice_ventas.company_id.name
                    SubElement(info_tributaria, "nombreComercial").text = invoice_ventas.shop_id.name
                    SubElement(info_tributaria, "ruc").text = invoice_ventas.company_id.vat[2:]
                    SubElement(info_tributaria, "claveAcceso").text = invoice_ventas.authorization
                    SubElement(info_tributaria, "codDoc").text = code
                    SubElement(info_tributaria, "estab").text = invoice_ventas.shop_id.number_sri
                    SubElement(info_tributaria, "ptoEmi").text = invoice_ventas.printer_id.number_sri
                    SubElement(info_tributaria, "secuencial").text = invoice_ventas.invoice_number[8:]
                    SubElement(info_tributaria, "dirMatriz").text = invoice_ventas.company_id.street
                    info_factura = SubElement(root, "infoNotaCredito")
                    SubElement(info_factura, "fechaEmision").text = invoice_ventas.date_invoice[8:10]+'/'+invoice_ventas.date_invoice[5:7]+'/'+ invoice_ventas.date_invoice[:4]
                    SubElement(info_factura, "dirEstablecimiento").text = invoice_ventas.shop_id.partner_address_id.street
                    SubElement(info_factura, "tipoIdentificacionComprador").text = identificacion
                    SubElement(info_factura, "razonSocialComprador").text = invoice_ventas.partner_id.name
                    SubElement(info_factura, "identificacionComprador").text = invoice_ventas.partner_id.vat[2:]
                    if invoice_ventas.company_id.resolution_sri:
                        SubElement(info_factura, "contribuyenteEspecial").text = invoice_ventas.company_id.resolution_sri[3:]
                    SubElement(info_factura, "obligadoContabilidad").text = "SI"
                    SubElement(info_factura, "codDocModificado").text = "01"
                    SubElement(info_factura, "numDocModificado").text = invoice_ventas.old_invoice_id.invoice_number
                    SubElement(info_factura, "fechaEmisionDocSustento").text = invoice_ventas.old_invoice_id.date_invoice[8:10]+'/'+ invoice_ventas.old_invoice_id.date_invoice[5:7]+'/'+invoice_ventas.old_invoice_id.date_invoice[:4]
                    SubElement(info_factura, "totalSinImpuestos").text = self.formato_numero(str(invoice_ventas.amount_untaxed))
                    SubElement(info_factura, "valorModificacion").text = self.formato_numero(str(invoice_ventas.amount_total))
                    SubElement(info_factura, "moneda").text = "DOLAR"
                    total_impuestos = SubElement(info_factura, "totalConImpuestos")
                    totalImpuesto = SubElement(total_impuestos, "totalImpuesto")
                    if invoice_ventas.amount_base_vat_12 > 0.00:
                        tax_code = invoice_ventas.amount_total_vat / invoice_ventas.amount_base_vat_12
                        if 0.119 <= tax_code <= 0.124:
                            codigoPorcentaje = "2"
                        elif 0.125 <= tax_code <= 0.144:
                            codigoPorcentaje = "3"
                        #totalImpuesto = SubElement(total_impuestos, "totalImpuesto")
                        SubElement(totalImpuesto, "codigo").text = "2"
                        SubElement(totalImpuesto, "codigoPorcentaje").text = codigoPorcentaje
                        SubElement(totalImpuesto, "baseImponible").text = self.formato_numero(str(invoice_ventas.amount_base_vat_12))
                        SubElement(totalImpuesto, "valor").text = self.formato_numero(str(invoice_ventas.amount_total_vat))
                    if invoice_ventas.amount_base_vat_00 > 0.00:
                        SubElement(totalImpuesto, "codigo").text = "2"
                        SubElement(totalImpuesto, "codigoPorcentaje").text = "0"
                        SubElement(totalImpuesto, "baseImponible").text = self.formato_numero(str(invoice_ventas.amount_base_vat_00))
                        SubElement(totalImpuesto, "valor").text = "0.00"
                    SubElement(info_factura, "motivo").text = invoice_ventas.motive_id.name
                    if code == '04':
                        detalles = SubElement(root, "detalles")
                        for lines in invoice_ventas.invoice_line:
                            detalle = SubElement(detalles, "detalle")
                            if lines.product_id.default_code:
                                SubElement(detalle, "codigoInterno").text = lines.product_id.default_code
                            SubElement(detalle, "codigoAdicional").text = lines.product_id.default_code or lines.name[:25]
                            SubElement(detalle, "descripcion").text = lines.name
                            SubElement(detalle, "cantidad").text = self.formato_numero(str(round(lines.quantity, 2)))
                            SubElement(detalle, "precioUnitario").text = self.formato_numero(str(round(lines.price_unit, 2)))
                            SubElement(detalle, "descuento").text = "0.00"
                            SubElement(detalle, "precioTotalSinImpuesto").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                            impuestos = SubElement(detalle, "impuestos")
                            impuesto = SubElement(impuestos, "impuesto")
                            if lines.iva_value > 0.00:
                                tax_code = round(lines.iva_value/lines.price_subtotal, 2)
                                if 0.119 <= tax_code <= 0.124:
                                    codigoPorcentaje = "2"
                                    tarifa = "12"
                                elif 0.125 <= tax_code <= 0.144:
                                    codigoPorcentaje = "3"
                                    tarifa = "14"
                                SubElement(impuesto, "codigo").text = "2"
                                SubElement(impuesto, "codigoPorcentaje").text = codigoPorcentaje
                                SubElement(impuesto, "tarifa").text = tarifa
                                SubElement(impuesto, "baseImponible").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                                SubElement(impuesto, "valor").text = self.formato_numero(str(round(lines.iva_value, 2)))
                            elif lines.iva_value == 0.00:
                                SubElement(impuesto, "codigo").text = "2"
                                SubElement(impuesto, "codigoPorcentaje").text = "0"
                                SubElement(impuesto, "tarifa").text = "0"
                                SubElement(impuesto, "baseImponible").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                                SubElement(impuesto, "valor").text = self.formato_numero(str(round(lines.iva_value, 2)))
                    info_adicional = SubElement(root, "infoAdicional")
                    SubElement(info_adicional, "campoAdicional", nombre="rucFirmante").text = invoice_ventas.company_id.vat[2:]
                    SubElement(info_adicional, "campoAdicional", nombre="cedulaFirmante").text = invoice_ventas.partner_id.vat[2:]
                    if invoice_ventas.address_invoice_id.email:
                        SubElement(info_adicional, "campoAdicional", nombre="Email").text = invoice_ventas.address_invoice_id.email
            elif invoice_ventas.journal_id.type == 'debit_note':
                root = Element("notaDebito", id="comprobante", version="1.0.0")
                code = '05'
                if invoice_ventas and invoice_ventas.authorization_sales:
                    if invoice_ventas.partner_id.type_vat == 'ruc':
                        identificacion = '04'
                    elif invoice_ventas.partner_id.type_vat == 'ci':
                        identificacion = '05'
                    elif invoice_ventas.partner_id.type_vat == 'pasaporte':
                        identificacion = '06'
                    elif invoice_ventas.partner_id.type_vat == 'consumidor':
                        identificacion = '07'
                    elif invoice_ventas.partner_id.type_vat == 'exterior':
                        identificacion = '08'
                    elif invoice_ventas.partner_id.type_vat == 'placa':
                        identificacion = '09'
                    else:
                        identificacion = '06'
                    info_tributaria = SubElement(root, "infoTributaria")
                    SubElement(info_tributaria, "ambiente").text = invoice_ventas.authorization_sales.environment
                    SubElement(info_tributaria, "tipoEmision").text = invoice_ventas.authorization_sales.type_emision
                    SubElement(info_tributaria, "razonSocial").text = invoice_ventas.company_id.name
                    SubElement(info_tributaria, "nombreComercial").text = invoice_ventas.shop_id.name
                    SubElement(info_tributaria, "ruc").text = invoice_ventas.company_id.vat[2:]
                    SubElement(info_tributaria, "claveAcceso").text = invoice_ventas.authorization
                    SubElement(info_tributaria, "codDoc").text = code
                    SubElement(info_tributaria, "estab").text = invoice_ventas.shop_id.number_sri
                    SubElement(info_tributaria, "ptoEmi").text = invoice_ventas.printer_id.number_sri
                    SubElement(info_tributaria, "secuencial").text = invoice_ventas.invoice_number[8:]
                    SubElement(info_tributaria, "dirMatriz").text = invoice_ventas.company_id.street
                    info_factura = SubElement(root, "infoNotaDebito")
                    SubElement(info_factura, "fechaEmision").text = invoice_ventas.date_invoice[8:10]+'/'+invoice_ventas.date_invoice[5:7]+'/'\
                        + invoice_ventas.date_invoice[:4]
                    SubElement(info_factura, "dirEstablecimiento").text = invoice_ventas.shop_id.partner_address_id.street
                    SubElement(info_factura, "tipoIdentificacionComprador").text = identificacion
                    SubElement(info_factura, "razonSocialComprador").text = invoice_ventas.partner_id.name
                    SubElement(info_factura, "identificacionComprador").text = invoice_ventas.partner_id.vat[2:]
                    SubElement(info_factura, "contribuyenteEspecial").text = invoice_ventas.company_id.resolution_sri[3:]
                    SubElement(info_factura, "obligadoContabilidad").text = "SI"
                    if invoice_ventas.old_invoice_id:
                        SubElement(info_factura, "codDocModificado").text = "01"
                        SubElement(info_factura, "numDocModificado").text = invoice_ventas.old_invoice_id.invoice_number
                        SubElement(info_factura, "fechaEmisionDocSustento").text = invoice_ventas.old_invoice_id.date_invoice[8:10]+'/'
                        +invoice_ventas.old_invoice_id.date_invoice[5:7]+'/'+invoice_ventas.old_invoice_id.date_invoice[:4]
                    SubElement(info_factura, "totalSinImpuestos").text = self.formato_numero(str(invoice_ventas.amount_untaxed))
                    total_impuestos = SubElement(info_factura, "impuestos")
                    totalImpuesto = SubElement(total_impuestos, "impuesto")
                    if invoice_ventas.amount_total_vat > 0.00:
                        tax_code = invoice_ventas.amount_total_vat / invoice_ventas.amount_base_vat_12
                        if 0.11 <= tax_code <= 0.124:
                            codigoPorcentaje = "2"
                        elif 0.125 <= tax_code <= 0.144:
                            codigoPorcentaje = "3"
                        totalImpuesto = SubElement(total_impuestos, "totalImpuesto")
                        SubElement(totalImpuesto, "codigo").text = "2"
                        SubElement(totalImpuesto, "codigoPorcentaje").text = codigoPorcentaje
                        SubElement(totalImpuesto, "baseImponible").text = self.formato_numero(str(invoice_ventas.amount_base_vat_12))
                        SubElement(totalImpuesto, "valor").text = self.formato_numero(str(invoice_ventas.amount_total_vat))
                    if invoice_ventas.amount_base_vat_00 > 0.00:
                        SubElement(totalImpuesto, "codigo").text = "2"
                        SubElement(totalImpuesto, "codigoPorcentaje").text = "0"
                        SubElement(totalImpuesto, "baseImponible").text = self.formato_numero(str(invoice_ventas.amount_base_vat_00))
                        SubElement(totalImpuesto, "valor").text = "0.00"
                    SubElement(info_factura, "valorTotal").text = self.formato_numero(str(invoice_ventas.amount_total))
                    if code == '05':
                        detalles = SubElement(root, "motivos")
                        for lines in invoice_ventas.invoice_line:
                            detalle = SubElement(detalles, "motivo")
                            SubElement(detalle, "razon").text = lines.name
                            SubElement(detalle, "valor").text = self.formato_numero(str(round(lines.price_subtotal, 2)))
                    info_adicional = SubElement(root, "infoAdicional")
                    SubElement(info_adicional, "campoAdicional", nombre="rucFirmante").text = invoice_ventas.company_id.vat[2:]
                    SubElement(info_adicional, "campoAdicional", nombre="cedulaFirmante").text = invoice_ventas.partner_id.vat[2:]
                    if invoice_ventas.address_invoice_id.email:
                        SubElement(info_adicional, "campoAdicional", nombre="Email").text = invoice_ventas.address_invoice_id.email
        return tostring(root, encoding="UTF-8")

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

    def action_number(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        result = super(straconx_invoice, self).action_number(cr, uid, ids, context)
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.electronic and ((invoice.type in ('out_invoice', 'out_refund')) or (invoice.type in ('in_refund') and
                                                                                           invoice.journal_id.type == 'debit_note')):

                date_inv = invoice.date_invoice[8:10]+invoice.date_invoice[5:7]+invoice.date_invoice[0:4]
                if invoice.journal_id.type == 'sale':
                    code = '01'
                elif invoice.journal_id.type == 'sale_refund':
                    code = '04'
                elif invoice.journal_id.type == 'debit_note':
                    code = '05'
                context.update({'code_sri': code})
                vat = invoice.company_id.vat[2:]
                environment = invoice.authorization_sales.environment
                type_emision = invoice.authorization_sales.type_emision
                serie = invoice.shop_id.number_sri+invoice.printer_id.number_sri
                secuencial = invoice.invoice_number[8:]
                if invoice.date_invoice:
                    n_code = invoice.date_invoice[8:10]+invoice.date_invoice[5:7]+invoice.date_invoice[0:4]
                else:
                    n_code = time.strftime('%d%Y%m')
                numeric_code = date_inv+code+str(vat)+str(environment)+str(serie)+str(secuencial)+str(n_code)+type_emision
                lst = [int(i) for i in str(numeric_code)]
                digit = self.mod11(lst, 7)
                if not invoice.authorization or len(invoice.authorization) != 49:
                    authorization = str(numeric_code)+str(digit)
                    if len(authorization) != 49:
                        raise osv.except_osv(_('Error!'),
                                             _('La clave de autorización es diferente a 48 dígitos, que es el valor requerido por el SRI.'))
                    self.write(cr, uid, [invoice.id], {'authorization': authorization})
                self.act_export_electronic(cr, uid, ids, context)
        return result

    def act_export_electronic(self, cr, uid, ids, context={}):
        this = self.browse(cr, uid, ids)[0]
        if context:
            code_sri = context.get('code_sri', False)
        if not code_sri:
            raise osv.except_osv(_('Error!'), _('No se ha definido el tipo de documento del SRI.'))
        if ((this.type in ('out_invoice', 'out_refund')) or (this.type in ('in_refund') and this.journal_id.type == 'debit_note')):
            root = self.generate_xml_electronic(cr, uid, ids)
            inv_name = this.invoice_number+".xml"
            out = base64.encodestring(root)
            company_path = this.company_id.electronic_path
            self.write(cr, uid, ids, {'name': inv_name, 'access_key': this.authorization}, context=context)
            if this.type == 'out_invoice':
                type_model = '01'
                pref = 'FACT_'
            elif this.type == 'out_refund':
                type_model = '04'
                pref = 'N_CRED_'
            elif this.type == 'in_refund' and this.journal_id.type == 'debit_note':
                type_model = '05'
                pref = 'N_DEBIT_'

            att_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_id', '=', this.id)])
            if not att_ids:
                att_id = self.pool.get('ir.attachment').create(cr, uid, {'res_model': 'account.invoice',
                                                                         'company_id': this.company_id.id,
                                                                         'res_name': inv_name,
                                                                         'datas_fname': pref+inv_name,
                                                                         'type': 'binary',
                                                                         'res_id': this.id,
                                                                         'description': 'Generación automática de xml de la factura ' + inv_name,
                                                                         'sri_code': code_sri,
                                                                         'access_key': this.authorization,
                                                                         'datas_unsigned': out,
                                                                         'partner_id': this.partner_id.id,
                                                                         'name': inv_name,
                                                                         'electronic': True,
                                                                         'type_model': type_model,
                                                                         'sign_state': '0',
                                                                         })
            else:
                att_id = att_ids[-1]
                self.pool.get('ir.attachment').write(cr, uid, [att_id], {'res_model':  'account.invoice',
                                                                         'company_id': this.company_id.id,
                                                                         'res_name': inv_name,
                                                                         'datas_fname': inv_name,
                                                                         'type': 'binary',
                                                                         'res_id': this.id,
                                                                         'description': 'Generación automática de xml de la factura ' + inv_name,
                                                                         'sri_code': code_sri,
                                                                         'access_key': this.authorization,
                                                                         'datas_unsigned': out,
                                                                         'partner_id': this.partner_id.id,
                                                                         'name': inv_name,
                                                                         'electronic': True,
                                                                         'type_model': type_model,
                                                                         'sign_state': '0',
                                                                         })
            cr.commit()
        return True

    def action_open_draft(self, cr, uid, ids, context=None):
        attach_obj = self.pool.get('ir.attachment')
        for invoice in self.browse(cr, uid, ids):
            attach_ids = attach_obj.search(cr, uid, [('res_model', '=', 'account.invoice'), ('res_id', '=', invoice.id)])
            if attach_ids:
                attach_obj.unlink(cr, uid, attach_ids)
            self.write(cr, uid, ids, {'name': ''})
        super(straconx_invoice, self).action_open_draft(cr, uid, ids, context)
        return True

    _columns = {'electronic': fields.boolean('electronic'),
                'authorization': fields.char('Authorization', size=50),
                'sri_authorization': fields.char('SRI Autorización', size=50),
                'sri_date': fields.datetime('Fecha Autorización')}

    def onchange_cash(self, cr, uid, ids, company=None, shop=None, type=None, printer_id=None, journal=None, context=None):
        authorization_obj = self.pool.get('sri.authorization')
        values = {'value': {}}
        user = None
        user = self.browse(cr, uid, uid)
        refund_mode = context.get('refund_mode', None)
        if context is None:
            context = {}
        if not (journal and shop):
            warning = {'title': _('Verify data!'), 'message': _("you must select the shop and Journal.")}
            return {'value': {'printer_id': None}, 'warning': warning}
        if printer_id:
            values['value']['shop_id'] = shop
            values['value']['printer_id'] = printer_id
            if type in ('out_invoice', 'out_refund') or (type == 'in_invoice' and context.get('journal_type', False) ==
                                                         'purchase_liquidation') or self.validate(type, context.get('journal_type', None)):
                values['value']['pre_printer'] = False
                values['value']['automatic'] = False
                values['value']['electronic'] = False
                type_journal = self.pool.get('account.journal').browse(cr, uid, journal, context).type
                dic_auth = authorization_obj.get_auth_only(cr, uid, type_journal, company, shop, printer_id, context=context)
                if refund_mode == 'internal':
                    values['value']['authorization'] = None
                    values['value']['authorization_sales'] = None
                    return values

                if not dic_auth['type_printer']:
                    raise osv.except_osv(_('No Authorization!'), _('La Caja seleccionada no tiene autorización para emitir documentos.'))
                elif dic_auth['type_printer']:
                    if dic_auth['type_printer'] == 'auto':
                        values['value']['pre_printer'] = False
                        values['value']['automatic'] = True
                        values['value']['electronic'] = False
                        values['value']['date_invoice2'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        values['value']['date_invoice'] = time.strftime('%Y-%m-%d')
                    elif dic_auth['type_printer'] == 'electronic':
                        values['value']['pre_printer'] = False
                        values['value']['automatic'] = False
                        values['value']['electronic'] = True
                        values['value']['date_invoice2'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        values['value']['date_invoice'] = time.strftime('%Y-%m-%d')
                    elif dic_auth['type_printer'] == 'pre':
                        values['value']['pre_printer'] = True
                        values['value']['automatic'] = False
                        values['value']['electronic'] = False
                        values['value']['date_invoice2'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        values['value']['date_invoice'] = time.strftime('%Y-%m-%d')
                    else:
                        values['value']['pre_printer'] = False
                        values['value']['automatic'] = False
                        values['value']['electronic'] = False
                else:
                    curr_user = self.pool.get('res.users').browse(cr, uid, uid, context)
                    if curr_user.old_auth and printer_id:
                        values['value']['printer_id'] = printer_id
                        values['value']['pre_printer'] = False
                    else:
                        raise osv.except_osv(_('No Authorization!'), _('Shop not have authorization for invoice! Please, create before continue.'))

                if dic_auth['authorization']:
                    values['value']['authorization'] = authorization_obj.browse(cr, uid, dic_auth['authorization'], context).name
                    values['value']['authorization_sales'] = dic_auth['authorization']
                else:
                    values['value']['authorization'] = None
                    values['value']['authorization_sales'] = None
                    values['value']['date_invoice'] = None
                    values['value']['date_invoice2'] = None
                values['value']['invoice_number_out'] = None

        return values

    def print_invoice_electronic_ride(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            nb_print = invoice.nb_print + 1
            self.write(cr, uid, [invoice.id], {'nb_print': nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id'] = invoice.id
                context['active_ids'] = ids
                return {'type': 'ir.actions.report.xml',
                        'report_name': 'invoice_ride_id',
                        'datas': data,
                        'context': context,
                        'nodestroy': True,
                        }
            return True

    def print_credit_notes_electronic(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.nb_print + 1
            self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'credit_note_ride_id',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 

    def print_debit_note_electronic(self, cr, uid, ids, context=None):      
        if context is None:
            context={}
        for invoice in self.browse(cr, uid, ids, context=context): 
            nb_print = invoice.nb_print + 1
            self.write(cr,uid,[invoice.id],{'nb_print':nb_print})
            if invoice:
                data = {}
                data['model'] = 'account.invoice'
                data['ids'] = ids
                context['active_id']=invoice.id
                context['active_ids']=ids
                return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'debit_note_ride_id',
                   'datas' : data,
                   'context': context,
                   'nodestroy': True,
                   }
            return True 

straconx_invoice()



class account_invoice_refund(osv.osv_memory):
    _inherit = "account.invoice.refund"
    
    def compute_refund(self, cr, uid, ids, mode='refund', context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: the account invoice refund’s ID or list of IDs

        """
        inv_obj = self.pool.get('account.invoice')
        reconcile_obj = self.pool.get('account.move.reconcile')
        account_m_line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        wf_service = netsvc.LocalService('workflow')
        inv_tax_obj = self.pool.get('account.invoice.tax')
        inv_line_obj = self.pool.get('account.invoice.line')
        res_users_obj = self.pool.get('res.users')
        if context is None:
            context = {}

        for form in self.browse(cr, uid, ids, context=context):
            created_inv = []
            date = False
            period = False
            description = False
            company = res_users_obj.browse(cr, uid, uid, context=context).company_id
            if not form.line_ids and form.filter_refund <> 'cancel':
                raise osv.except_osv(_('Error !'), _('Usted debe ingresar por lo menos un producto de devolución'))
            journal_id = form.journal_id.id
            for inv in inv_obj.browse(cr, uid, context.get('active_ids'), context=context):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise osv.except_osv(_('Error !'), _('Can not %s draft/proforma/cancel invoice.') % (mode))
#                 if inv.reconciled and mode in ('cancel'):
#                     raise osv.except_osv(_('Error !'), _('No se puede cancelar una factura que ha sido pagada, excepto que sea reversado primero el pago para proceder a crear la Nota de Crédito'))
                if form.period.id:
                    period = form.period.id
                else:
                    period = inv.period_id and inv.period_id.id or False

                if not journal_id:
                    journal_id = inv.journal_id.id
                id_ant = inv.id
                if form.date:
                    date = form.date2
                    if not form.period.id:
                            cr.execute("select name from ir_model_fields \
                                            where model = 'account.period' \
                                            and name = 'company_id'")
                            result_query = cr.fetchone()
                            if result_query:
                                cr.execute("""select p.id from account_fiscalyear y, account_period p where y.id=p.fiscalyear_id \
                                    and date(%s) between p.date_start AND p.date_stop and y.company_id = %s limit 1""", (date, company.id,))
                            else:
                                cr.execute("""SELECT id
                                        from account_period where date(%s)
                                        between date_start AND  date_stop  \
                                        limit 1 """, (date,))
                            res = cr.fetchone()
                            if res:
                                period = res[0]
                else:
                    date = inv.date_invoice
                if form.description:
                    description = form.description
                else:
                    description = inv.name

                if not period:
                    raise osv.except_osv(_('Data Insufficient !'), \
                                            _('No Period found on Invoice!'))
                
                cr.execute("SELECT product_id from account_invoice_line where invoice_id = %s", (inv.id,))
                res = cr.fetchall()
                res = [r[0] for r in res]
                dict_refund={}
                context.update({'refund_mode':mode})
                for l in form.line_ids:
                    if l.product_id.id not in res:
                        raise osv.except_osv(_('Invalid Action !'), _('The product %s not exist in the invoice, please check!') %(l.product_id.name,))
                    dict_refund[l.product_id.id]=l.quantity
                refund_id = inv_obj.refund(cr, uid, [inv.id], date, period, description, journal_id, dict_refund,context)
                refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
                if form.user_authorized:
                    refund.write({'user_authorized_refund':form.user_authorized.id})

                if mode == 'internal' and id_ant:
                    number = 'NCI-'+inv.number
                    verify = self.pool.get('account.invoice').search(cr,uid,[('number','like',number)])
                    if verify: 
                        name = int(len(verify)) + 1
                        number = 'NCI '+inv.number + '-'+str(name)
                        invoice_number_out = number
                    else:
                        number = 'NCI '+inv.number
                        invoice_number_out = number
                        invoice_number_in = number
                else:
                    number = False
                    invoice_number_out = False    
                    invoice_number_in = False                    
                
                inv_obj.write(cr, uid, [refund.id], {'date_due': date[:10],
                                                'check_total': inv.check_total,
                                                'old_invoice_id':id_ant,
                                                'motive_id':form['motive'].id,
                                                'refund_type':mode,
                                                'number': number,
                                                'invoice_number_out': invoice_number_out,
                                                'invoice_number_in':invoice_number_in,
                                                'date_invoice2': form['date2']})
                inv_obj.button_compute(cr, uid, refund_id)

                created_inv.append(refund_id[0])
                if mode in ('internal','refund'):
                    wf_service.trg_validate(uid, 'account.invoice', refund.id, 'invoice_open', cr)
                elif mode in ('cancel'):
                    inv_obj.annuled_voucher(cr, uid, inv, context)
                    movelines = inv.move_id.line_id
                    to_reconcile_ids = {}
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            if not to_reconcile_ids.has_key(line.account_id.id):
                                to_reconcile_ids[line.account_id.id] = [line.id]
                            else:
                                to_reconcile_ids[line.account_id.id] += [line.id]
                        if type(line.reconcile_id) != osv.orm.browse_null:
                            reconcile_obj.unlink(cr, uid, line.reconcile_id.id)
                    wf_service.trg_validate(uid, 'account.invoice', \
                                        refund.id, 'invoice_open', cr)
                    refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
                    for tmpline in  refund.move_id.line_id:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                    context['comment']=_(('Write-Off invoice number %s')% inv.number)
                    for account in to_reconcile_ids:
                        account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                                        writeoff_period_id=period,
                                        writeoff_journal_id = inv.journal_id.id,
                                        writeoff_acc_id=inv.account_id.id,
                                        context=context
                                        )
                    if mode == 'refund':
                        invoice = inv_obj.read(cr, uid, [inv.id],
                                    ['name', 'type', 'number', 'reference',
                                    'comment', 'date_due', 'partner_id',
                                    'address_contact_id', 'address_invoice_id',
                                    'partner_insite', 'partner_contact',
                                    'partner_ref', 'payment_term', 'account_id',
                                    'currency_id', 'invoice_line', 'tax_line',
                                    'journal_id', 'period_id', 'shop_id','printer_id','company_id'], context=context)
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.read(cr, uid, invoice['invoice_line'], context=context)
                        invoice_lines = inv_obj._refund_cleanup_lines(cr, uid, invoice_lines)
                        tax_lines = inv_tax_obj.read(cr, uid, invoice['tax_line'], context=context)
                        tax_lines = inv_obj._refund_cleanup_lines(cr, uid, tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': date,
                            'state': 'draft',
                            'number': False,
                            'invoice_line': invoice_lines,
                            'tax_line': tax_lines,
                            'period_id': period,
                            'name': description
                        })
                        for field in ('address_contact_id', 'address_invoice_id', 'partner_id',
                                'account_id', 'currency_id', 'payment_term', 'journal_id',
                                'shop_id','printer_id','company_id'):
                                invoice[field] = invoice[field] and invoice[field][0]
                        inv_id = inv_obj.create(cr, uid, invoice, {})
                        if inv.payment_term.id:
                            data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv.payment_term.id, date)
                            if 'value' in data and data['value']:
                                inv_obj.write(cr, uid, [inv_id], data['value'])
                        created_inv.append(inv_id)
            xml_id = (inv.type == 'out_refund') and 'account.action_invoice_tree3_view2' or \
                     (inv.type == 'in_refund') and 'action_invoice_tree4_view2' or \
                     (inv.type == 'out_invoice') and 'action_invoice_tree3' or \
                     (inv.type == 'in_invoice') and 'action_invoice_tree4'
            result = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
            id = result and result[1] or False
            result = act_obj.read(cr, uid, id, context=context)
            invoice_domain = eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result

account_invoice_refund()
    