# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2012-present STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved
#
#
##############################################################################

from osv import fields,osv
from tools.translate import _
import time
from xml.etree.ElementTree import Element, SubElement, tostring
import base64
from datetime import date
import datetime
import unicodedata



class sri_ats(osv.osv_memory):

    _name = 'sri.ats'

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

    def tipo_identificacion(self, vat, transaction):
        if vat[:2] == 'EC':
            len_vat = len(vat[2:])
            if len_vat == 10:
                type = 'ci'
            elif vat[2:] == '9999999999999':
                type = 'consumidor'
            elif len_vat == 13:
                type = 'ruc'
            else:
                type = 'passport'
        else:
            type = 'passport'

        if transaction == 'compra':
            if type == 'ruc':
                return '01'
            elif type == 'ci':
                return '02'
            elif type == 'passport':
                return '03'
        elif transaction == 'venta':
            if type == 'ruc':
                return '04'
            elif type == 'ci':
                return '05'
            elif type == 'passport':
                return '06'
            elif type == 'consumidor':
                return '07'

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
   

    def agree_ventas(self, xml, vat, type_doc,type_emi, number_doc, base_no_apl, base_0, base_12, iva, ret_iva, ret_renta, sri_code, cliente):
        tpIdCliente = self.tipo_identificacion(vat, 'venta')
        try:
            detalle = SubElement(xml, "detalleVentas")
            SubElement(detalle, "tpIdCliente").text = tpIdCliente
            SubElement(detalle, "idCliente").text = vat[2:]
            #if vat != 'EC9999999999999':
            if tpIdCliente in ('04','05','06'):
                SubElement(detalle, "parteRelVtas").text = 'NO'
            if tpIdCliente == '06':
                SubElement(detalle, "tipoCliente").text = '01'
                SubElement(detalle, "denoCli").text = cliente
            SubElement(detalle, "tipoComprobante").text = type_doc
            SubElement(detalle, "tipoEmision").text = type_emi
            SubElement(detalle, "numeroComprobantes").text = str(int(number_doc))
            SubElement(detalle, "baseNoGraIva").text = self.formato_numero(str(base_no_apl))
            SubElement(detalle, "baseImponible").text = self.formato_numero(str(base_0))
            SubElement(detalle, "baseImpGrav").text = self.formato_numero(str(base_12))
            SubElement(detalle, "montoIva").text = self.formato_numero(str(iva))
            SubElement(detalle, "montoIce").text ="0.00"
            SubElement(detalle, "valorRetIva").text = self.formato_numero(str(ret_iva))
            SubElement(detalle, "valorRetRenta").text = self.formato_numero(str(ret_renta))
            if type_doc == "18":
                formasDePago= SubElement(detalle, "formasDePago")
                if sri_code:
                    for sri_c in sri_code:
                        SubElement(formasDePago, "formaPago").text = str(sri_c)
                else:
                    SubElement(formasDePago, "formaPago").text = "20"
            return True
        except:
            raise osv.except_osv('Error!',
                                 _(('No existen datos para la empresa con Identificación %s. Comunicarse con el área de sistemas.') % (vat)))

    def generate_xml(self, cr, uid, ids, context=None):
        root = ''
        for anexo in self.browse(cr, uid, ids, context=context):
            # Establecimientos:
            journal_sale = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale')])
            if journal_sale:
                journal_sale = journal_sale[-1]
            else:
                raise osv.except_osv('Error!', _(('No existen diarios de Ventas creados')))
            journal_refund = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale_refund')])
            if journal_refund:
                journal_refund = journal_refund[-1]
            else:
                raise osv.except_osv('Error!', _(('No existen diarios de Notas de Crédito de Ventas creados')))
            journal_debit_notes = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'debit_note')])
            if journal_debit_notes:
                journal_debit_notes = journal_debit_notes[-1]
            else:
                raise osv.except_osv('Error!', _(('No existen diarios de Notas de Débito creados')))

            cr.execute("""select count(id) from sale_shop where emision_point=True and company_id=%s""", (anexo.company_id.id,))
            number = cr.fetchall()
            if number[0]:
                number = number[0][0]
                if len(str(number)) == 1:
                    estabruc = "00"+str(number)
                elif len(str(number)) > 1 and len(str(number)) <= 99:
                    estabruc = "0"+str(number)
                else:
                    estabruc = str(number)

            cr.execute("""select coalesce((sum(t.base_un) +sum(t.base_00) + sum(t.base_12)),0) as sales_month from
                        (select sum(i.amount_base_vat_untaxes)*-1 as base_un, (sum(i.amount_base_vat_00)*-1) as base_00,(sum(i.amount_base_vat_12)*-1)
                        as base_12 from account_invoice i
                        where i.period_id = %s and i.type in ('out_refund') and i.state in ('open','paid') and i.journal_id = %s
                        and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                        group by i.period_id, i.type
                        UNION ALL
                        select sum(i.amount_base_vat_untaxes) as base_un, sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12
                        from account_invoice i
                        where i.period_id = %s and i.type in ('out_invoice') and i.state in ('open','paid') and i.journal_id = %s
                        and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                        group by i.period_id, i.type) as t""", (anexo.period_id.id, journal_refund, anexo.period_id.id, journal_sale))

            sales = cr.fetchone()
            if sales:
                total_sales = sales[0]
            else:
                total_sales = 0.00

            # Facturas en compras que pertenecen al periodo
            invoice_compras_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id', '=', anexo.period_id.id),
                                                                                    ('type', 'in', ('in_invoice', 'in_refund')),
                                                                                    ('state', 'in', ('open', 'paid')),
                                                                                    ('journal_id.type', 'in', ('purchase', 'purchase_liquidation',
                                                                                                               'purchase_refund', 'debit_note',
                                                                                                               'other_moves', 'sale_note')),
                                                                                    ('document_type.code', '!=', 'TI')])
            invoice_compras = self.pool.get('account.invoice').browse(cr, uid, invoice_compras_ids, context)

            # Facturas en ventas que pertenecen al periodo
            invoice_ventas_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('type','=','out_invoice'),('state','in',('open','paid'))])
            invoice_ventas = self.pool.get('account.invoice').browse(cr, uid, invoice_ventas_ids, context)
 
            #Notas de Credito en ventas que pertenecen al periodo
            refund_ventas_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('type','=','out_refund'),('state','in',('open','paid')),('journal_id.type','=','sale_refund')])
            refund_ventas = self.pool.get('account.invoice').browse(cr, uid, refund_ventas_ids, context)
            
            #Notas de debito en ventas que pertenecen al periodo
            note_ventas_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('type','=','out_refund'),('state','in',('open','paid')),('journal_id.type','=','debit_note')])
            debit_note_ventas = self.pool.get('account.invoice').browse(cr, uid, note_ventas_ids, context)
            
            #Retenciones en ventas que pertenecen al periodo pero que la factura pertenece a un periodo anterior
#            withhold_ids = self.pool.get('account.withhold').search(cr, uid, [('period_id','=',anexo.period_id.id),('transaction_type','=','sale'),('state','=','approved'),'|',('invoice_id.period_id.id','!=',anexo.period_id.id),('deposit_id','!=',False)])
            withhold_ids = self.pool.get('account.withhold').search(cr, uid, [('period_id','=',anexo.period_id.id),('transaction_type','=','sale'),('state','=','approved'),('invoice_id.period_id.id','!=',anexo.period_id.id)])
            withhold_ventas = self.pool.get('account.withhold').browse(cr, uid, withhold_ids, context)
            
            #Facturas de Ventas y notas de credito Canceladas
            document_canceled_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('type','in',('out_invoice','out_refund')),('state','=','cancel'),])
            
            #Liquidaciones Canceladas
            document_canceled_ids += self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('type','=','in_invoice'),('state','=','cancel'),('journal_id.type','=','purchase_liquidation')])
            #Notas de debito Canceladas
            document_canceled_ids += self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('state','=','cancel'),('journal_id.type','=','debit_note')])
            invoice_canceled_ids=list(set(document_canceled_ids))
            invoice_canceled = self.pool.get('account.invoice').browse(cr, uid, invoice_canceled_ids, context)
            mode_withhold = self.pool.get('payment.mode').search(cr,uid,[('mode_withhold','=',True),('active','=',True)])
            mode_withhold_vat = self.pool.get('payment.mode').search(cr,uid,[('mode_withhold_vat','=',True),('active','=',True)])

            company = self.pool.get('res.users').browse(cr, uid, [uid,], context)[0].company_id.partner_id
            root = Element("iva")
            mes= anexo.period_id.name
            self.mes_lista=mes.split('/')
            if not company.type_vat:
                raise osv.except_osv('Error!', _(('Debe definir el tipo de identificación de la compañía')))
            if company.type_vat == 'ruc':
                identificacion = 'R'
            elif company.type_vat == 'cedula':
                company = 'C'
            elif company.type_vat == 'pasaporte':
                identificacion = 'P'
            elif company.type_vat == 'consumidor':
                identificacion = 'F'
            SubElement(root,"TipoIDInformante").text=identificacion
            SubElement(root,"IdInformante").text=company.vat[2:]
            SubElement(root,"razonSocial").text=company.name.replace('.','')
            SubElement(root,"Anio").text=anexo.period_id.fiscalyear_id.name
            SubElement(root,"Mes").text=self.mes_lista[0]
            SubElement(root,"numEstabRuc").text=estabruc
            SubElement(root,"totalVentas").text= self.formato_numero(str(round(total_sales,2)))
            SubElement(root,"codigoOperativo").text="IVA"
            #FACTURAS DE COMPRAS, NOTAS DE DEBITO Y CREDITO A PROVEEDORES
            compras = SubElement(root,"compras")
            if invoice_compras:
                for inv in invoice_compras:
                    if ((inv.journal_id.type in ('purchase_liquidation','debit_note','other_moves','sale_note')) or (inv.journal_id.type in ('purchase','purchase_refund') and inv.origin_transaction != 'international')) and inv.document_type.code not in('44'):
                        try:
                            if inv.invoice_number:
                                numero_factura=inv.invoice_number.split('-')
                            elif inv.invoice_number_in:
                                numero_factura=inv.invoice_number_in.split('-')
                            else:
                                raise osv.except_osv('Error!', _(('El documento %s con número  %s de %s emitido el %s por el usuario %s y id = %s contiene información incompleta. Revise por favor.') %(inv.journal_id.name, inv.invoice_number, inv.partner_id.name,  inv.date_invoice, inv.user_id.name, inv.id)))
                            fecha_emision=(str(inv.date_invoice))
                            fecha_emision=fecha_emision.split('-')
                            fecha_registro=(str(inv.create_date))
                            fecha_registro=fecha_registro.split(' ')
                            fecha_registro=fecha_registro[0].split('-')
                            detalle = SubElement(compras,"detalleCompras")
                            SubElement(detalle, "codSustento").text = inv.tax_sustent.code
                            try: 
                                if inv.vat:
                                    tipo_id = self.tipo_identificacion(inv.vat, 'compra')
                            except:
                                raise osv.except_osv('Error!', _(('Agrege el tipo de identificación en el proveedor %s.')%(inv.partner_id.vat)))
                            SubElement(detalle, "tpIdProv").text = tipo_id 
                            SubElement(detalle, "idProv").text = inv.partner_id.vat[2:15]
                            SubElement(detalle, "tipoComprobante").text = inv.document_type.code
                            if inv.country_id.iso_code <> '593' or tipo_id == '03':
                                SubElement(detalle, "tipoProv").text = '02'
                                SubElement(detalle, "denoProv").text = inv.partner_id.name
                            if inv.partner_id.type_vat == 'pasaporte':
                                SubElement(detalle, "parteRel").text = 'NO'
                            else:
                                SubElement(detalle, "parteRel").text = 'NO'
                            SubElement(detalle, "fechaRegistro").text = fecha_emision[2]+"/"+fecha_emision[1]+"/"+fecha_emision[0]
                            SubElement(detalle, "establecimiento").text = numero_factura[0]
                            SubElement(detalle, "puntoEmision").text = numero_factura[1]
                            SubElement(detalle, "secuencial").text = numero_factura[2]
                            SubElement(detalle, "fechaEmision").text = fecha_emision[2]+"/"+fecha_emision[1]+"/"+fecha_emision[0]
                            if inv.journal_id.type in ('purchase','purchase_refund','purchase_liquidation','debit_note','sale_note'):
                                SubElement(detalle, "autorizacion").text = inv.authorization
                            else:
                                SubElement(detalle, "autorizacion").text = '999'                          
                            if inv.amount_base_vat_untaxes > 0.01 or inv.amount_base_vat_untaxes != -0.01:          
                                SubElement(detalle, "baseNoGraIva").text = self.formato_numero(str(round(inv.amount_base_vat_untaxes,2)))
                            else:
                                SubElement(detalle, "baseNoGraIva").text = "0.00"
                            SubElement(detalle, "baseImponible").text = self.formato_numero(str(round(inv.amount_base_vat_00,2)))
                            SubElement(detalle, "baseImpGrav").text = self.formato_numero(str(round(inv.amount_base_vat_12,2)))
                            if inv.amount_base_vat_untaxes > 0.01 or inv.amount_base_vat_untaxes != -0.01:
                                SubElement(detalle, "baseImpExe").text = self.formato_numero(str(round(inv.amount_base_vat_untaxes,2)))
                            else:
                                SubElement(detalle, "baseImpExe").text = "0.00"
                            SubElement(detalle, "montoIce").text ="0.00"
                            SubElement(detalle, "montoIva").text = self.formato_numero(str(round(inv.amount_total_vat,2)))
                            ret_bienes = 0.00
                            ret_servicios = 0.00
                            ret_bienes_10 = 0.00
                            ret_servicios_20 = 0.00
                            ret_servicios_50 = 0.00
                            total_base = 0.00
                            ret_100 = 0.00
                            if inv.withhold_lines_ids:
                                for line in inv.withhold_lines_ids:
                                    if line.state=='approved' and line.tax_id.tax_type=='withhold_vat':
                                        if line.percentage in (10, 30):
                                            total_base += line.tax_base
                                            if line.percentage == 10:
                                                ret_bienes_10 = line.retained_value
                                            else:
                                                ret_bienes = line.retained_value
                                        elif line.percentage in (20, 70, 50):
                                            total_base += line.tax_base
                                            if line.percentage == 20:
                                                ret_servicios_20 = line.retained_value
                                            elif line.percentage == 50:
                                                ret_servicios_50 = line.retained_value
                                            else:
                                                ret_servicios = line.retained_value
                                        elif line.percentage == 100:
                                            total_base += line.tax_base
                                            ret_100 = line.retained_value
                            regimen = inv.partner_id.type_reg or '01'
                            SubElement(detalle, "valRetBien10").text = self.formato_numero(str(abs(round(ret_bienes_10,2))))
                            SubElement(detalle, "valRetServ20").text = self.formato_numero(str(abs(round(ret_servicios_20,2))))
                            SubElement(detalle, "valorRetBienes").text = self.formato_numero(str(abs(round(ret_bienes,2))))
                            SubElement(detalle, "valRetServ50").text = self.formato_numero(str(abs(round(ret_servicios_50,2))))
                            SubElement(detalle, "valorRetServicios").text = self.formato_numero(str(abs(round(ret_servicios,2))))
                            SubElement(detalle, "valRetServ100").text = self.formato_numero(str(abs(round(ret_100,2))))
                            if inv.tax_sustent.code in ('08','09'):       
                                SubElement(detalle, "totbasesImpReemb").text = self.formato_numero(str(abs(round(total_base,2))))
                            else:                        
                                SubElement(detalle, "totbasesImpReemb").text ="0.00"
                            pagoExterior=SubElement(detalle,"pagoExterior")
                            if inv.origin_transaction=='local':
                                SubElement(pagoExterior, "pagoLocExt").text ="01"
                                SubElement(pagoExterior, "paisEfecPago").text ="NA"
                                SubElement(pagoExterior, "aplicConvDobTrib").text ="NA"
                                SubElement(pagoExterior, "pagExtSujRetNorLeg").text ="NA"
                            else:
                                SubElement(pagoExterior, "pagoLocExt").text ="02"
                                SubElement(pagoExterior, "tipoRegi").text =str(regimen)
                                SubElement(pagoExterior, "paisEfecPagoGen").text =inv.country_id.iso_code
                                SubElement(pagoExterior, "paisEfecPago").text =inv.country_id.iso_code
                                SubElement(pagoExterior, "aplicConvDobTrib").text ="NO"
                                SubElement(pagoExterior, "pagExtSujRetNorLeg").text ="NO"
                            if inv.amount_total >= 1000 and inv.payment_ids:
                                formasDePago=SubElement(detalle,"formasDePago")
                                SubElement(formasDePago, "formaPago").text ="20"
                            elif inv.amount_total >= 1000 and not inv.payment_ids:
                                formasDePago=SubElement(detalle,"formasDePago")
                                SubElement(formasDePago, "formaPago").text ="20"
                        except:
                            raise osv.except_osv('Error!', _(('El documento %s con número  %s de %s emitido el %s por el usuario %s y id = %s contiene información incompleta. Revise por favor.') %(inv.journal_id.name, inv.invoice_number, inv.partner_id.name,  inv.date_invoice, inv.user_id.name, inv.id)))

                        #Retenciones en Compras
                        retencion = SubElement(detalle, "air")

                        try:
                            for line in inv.withhold_lines_ids:
                                if line.tax_id.tax_type == 'withhold':
                                    if line.state == 'approved':
                                        detalle_retencion = SubElement(retencion, "detalleAir")
                                        SubElement(detalle_retencion, "codRetAir").text = line.tax_id.description
                                        tax_base = round(line.tax_base,2)
                                        SubElement(detalle_retencion, "baseImpAir").text = self.formato_numero(str(round(tax_base,2)))
                                        SubElement(detalle_retencion, "porcentajeAir").text = self.formato_numero(str(round(line.percentage,2)))
                                        SubElement(detalle_retencion, "valRetAir").text = self.formato_numero(str(round(line.retained_value,2)))
                                        if line.tax_id.description in ('327','330','504A','504D'):
                                            SubElement(detalle_retencion, "fechaPagoDiv").text = fecha_emision[2]+"/"+fecha_emision[1]+"/"+fecha_emision[0]
                                            SubElement(detalle_retencion, "imRentaSoc").text = self.formato_numero(str(round(line.retained_value,2)))
                                            SubElement(detalle_retencion, "anioUtDiv").text = fecha_emision[0]
                                        if line.tax_id.description in ('340','338','341','342','342A','342B'):
                                            SubElement(detalle_retencion, "numCajBan").text ="0"
                                            SubElement(detalle_retencion, "precCajBan").text ="0.00"
                            if inv.withhold_id:
                                withhold = inv.withhold_id    
                                if withhold and withhold.state == 'approved':
                                    fecha_ret=(str(withhold.date))
                                    fecha_ret=fecha_ret.split('-')
                                    numero_retencion=withhold.number.split('-')
                                    SubElement(detalle, "estabRetencion1").text = numero_retencion[0]
                                    SubElement(detalle, "ptoEmiRetencion1").text = numero_retencion[1]
                                    SubElement(detalle, "secRetencion1").text = numero_retencion[2]
                                    SubElement(detalle, "autRetencion1").text = withhold.authorization
                                    SubElement(detalle, "fechaEmiRet1").text = fecha_ret[2]+"/"+fecha_ret[1]+"/"+fecha_ret[0]
                        except:
                            continue
                        if inv.type == 'in_refund' or inv.old_invoice_id:
                            numero_nota_debito = inv.old_invoice_id.invoice_number.split('-')
                            SubElement(detalle, "docModificado").text = inv.old_invoice_id.document_type.code
                            SubElement(detalle, "estabModificado").text = numero_nota_debito[0] or "000"
                            SubElement(detalle, "ptoEmiModificado").text = numero_nota_debito[1] or "000"
                            SubElement(detalle, "secModificado").text = numero_nota_debito[2] or "0"
                            SubElement(detalle, "autModificado").text = inv.old_invoice_id.authorization

            #FACTURAS DE VENTAS, NOTAS DE CREDITO Y DEBITO EN VENTAS
            if invoice_ventas or refund_ventas or debit_note_ventas or withhold_ventas:
                ventas = SubElement(root,"ventas")
                #FACTURAS PREIMPRESAS
                tipo_fact = ('electronicas','fisicas')
                for type in tipo_fact:
                    if type == 'electronicas':
                        type_emi = 'E'
                        cr.execute("""select t.vat, sum(t.docs), sum(t.base_un), sum(t.base_00),sum(t.base_12),sum(t.iva_12) from  
                                (select i.vat, count(i.id) as docs,sum(i.amount_base_vat_untaxes) as base_un ,sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12,sum(i.amount_total_vat) as iva_12 from account_invoice i 
                                where i.period_id = %s and i.type in ('out_invoice') and i.state in ('open','paid') and i.journal_id = %s
                                and char_length(i.authorization) > 10
                                group by i.period_id, i.vat, i.type)
                                as t group by t.vat, t.docs""",(anexo.period_id.id, journal_sale,))
                    else:
                        type_emi = 'F'
                        cr.execute("""select t.vat, sum(t.docs), sum(t.base_un), sum(t.base_00),sum(t.base_12),sum(t.iva_12) from  
                                (select i.vat, count(i.id) as docs,sum(i.amount_base_vat_untaxes) as base_un ,sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12,sum(i.amount_total_vat) as iva_12 from account_invoice i 
                                where i.period_id = %s and i.type in ('out_invoice') and i.state in ('open','paid') and i.journal_id = %s
                                and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                                group by i.period_id, i.vat, i.type)
                                as t group by t.vat, t.docs""",(anexo.period_id.id, journal_sale,))
                   

                    sales_month = cr.fetchall()
                    inv = []
                    if sales_month:
                        for pt in sales_month:
                            iva_ret = 0.00
                            renta_ret = 0.00
                            sri_code = []
                            move_ids = []
                            voucher_ids = []
                            vat = pt[0]
                            for inv_br in invoice_ventas:
                                if inv_br.vat == pt[0]:
                                    cliente= str(inv_br.partner_id.name.upper())
                                    cliente = cliente.replace('Ñ','N')
                                    cliente = cliente.replace('Á','A')
                                    cliente = cliente.replace('É','E')
                                    cliente = cliente.replace('Í','I')
                                    cliente = cliente.replace('Ó','O')
                                    cliente = cliente.replace('Ú','U')
                                    if inv_br.move_id:
                                        for move in inv_br.move_id.line_id:
                                            move_ids.append(move.id)
                            vouch_line_ids = self.pool.get('account.voucher.line').search(cr, uid, [('move_line_id','in',move_ids)])
                            for vouch in vouch_line_ids:
                                voucher_ids.append(self.pool.get('account.voucher.line').browse(cr, uid, vouch).voucher_id.id)
                            pay_ids = self.pool.get('account.payments').search(cr, uid, [('vouch_id','in',voucher_ids)])
                            for pay in self.pool.get('account.payments').browse(cr, uid, pay_ids):
                                if not pay.mode_id.sri_code in sri_code:
                                    sri_code.append(pay.mode_id.sri_code)
    #                         cli = self.pool.get('res.partner').browse(cr,uid,pt[0])
    #                         if not cli:
    #                             raise osv.except_osv('Error!', _(('No existen datos para la empresa con id %s. Comunicarse con el área de sistemas.')%(pt[0])))                            
                            num_comprobantes_facturas = pt[1]
                            if pt[2]>0.01 or pt[2]!=-0.01:
                                base_untax = pt[2]
                            else:
                                base_untax = 0.00
                            if pt[3]>0.01 or pt[3]!=-0.01:
                                base_00 = pt[3]
                            else:
                                base_00 = 0.00
    
                            base_12 = pt[4]
                            iva = pt[5]
                            inv = self.pool.get('account.invoice').search(cr,uid,[('partner_id','=',pt[0]),('period_id','=',anexo.period_id.id), ('type', '=', 'out_invoice'), ('state', 'in', ('paid','open')), ('journal_id', '=', journal_sale)])
                            # SI HAY RETENCIONES 
                            withhold_ids = self.pool.get('account.withhold').search(cr, uid, [('period_id','=',anexo.period_id.id),('transaction_type','=','sale'),('state','=','approved'),('partner_id.vat','=',vat)])
                            withhold_ventas = self.pool.get('account.withhold').browse(cr, uid, withhold_ids, context)
                            if withhold_ventas:
                                for w_id in withhold_ventas:
                                    for w_line in w_id.withhold_line_ids:
                                            if w_line.name=='RENTA':
                                                renta_ret += w_line.retained_value
                                            if w_line.name=='IVA':
                                                iva_ret += w_line.retained_value
                            # SI HAY PAGOS DE RETENCIONES EN LA FUENTE
                            if mode_withhold:
                                for mw in mode_withhold: 
                                    withhold_fuente = self.pool.get('account.payments').search(cr,uid,[('mode_id','=',mw),('partner_id.vat','=',vat),('deposit_date','>=',anexo.period_id.date_start),('deposit_date','<=',anexo.period_id.date_stop)])
                                    if withhold_fuente:
                                        for w_fuente in withhold_fuente:
                                            renta_ret += self.pool.get('account.payments').browse(cr,uid,w_fuente).amount
                            if mode_withhold_vat: 
                                for mwi in mode_withhold_vat:                             
                                    withhold_iva = self.pool.get('account.payments').search(cr,uid,[('mode_id','=',mwi),('partner_id.vat','=',vat),('deposit_date','>=',anexo.period_id.date_start),('deposit_date','<=',anexo.period_id.date_stop)])
                                    if withhold_iva:
                                        for w_iva in withhold_iva:
                                            iva_ret += self.pool.get('account.payments').browse(cr,uid,w_iva).amount
    
                            # SI HAY PAGOS DE RETENCIONES DE IVA
    
    #                         tax_ids = self.pool.get ('account.invoice.tax').search(cr, uid, [('invoice_id', 'in', inv)])
    #                         for tax in self.pool.get('account.invoice.tax').browse(cr, uid, tax_ids):
    #                             if tax.tax_code_id.tax_type == 'withhold_vat':
    #                                 iva_ret += (tax.amount * -1)
    #                             if tax.tax_code_id.tax_type == 'withhold':
    #                                 renta_ret += (tax.amount * -1)                        
                            self.agree_ventas(ventas, vat, "18", type_emi,num_comprobantes_facturas, base_untax, base_00, base_12, iva, iva_ret, renta_ret, sri_code, cliente)
                for type in tipo_fact:    
                    if type == 'electronicas':
                        type_emi = 'E'
                        cr.execute("""select t.vat, sum(t.docs), sum(t.base_un), sum(t.base_00),sum(t.base_12),sum(t.iva_12) from 
                                    (select i.vat, count(i.id) as docs,sum(i.amount_base_vat_untaxes) as base_un ,sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12,sum(i.amount_total_vat) as iva_12 from account_invoice i 
                                    where i.period_id = %s and i.type in ('out_refund') and i.state in ('open','paid') and i.journal_id = %s
                                    and char_length(i.authorization) > 10
                                    group by i.period_id, i.vat, i.type)
                                    as t group by t.vat, t.docs""",(anexo.period_id.id, journal_refund))
                    else:
                        type_emi = 'F'
                        cr.execute(""" select t.vat, sum(t.docs), sum(t.base_un), sum(t.base_00),sum(t.base_12),sum(t.iva_12) from 
                                    (select i.vat, count(i.id) as docs,sum(i.amount_base_vat_untaxes) as base_un ,sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12,sum(i.amount_total_vat) as iva_12 from account_invoice i 
                                    where i.period_id = %s and i.type in ('out_refund') and i.state in ('open','paid') and i.journal_id = %s
                                    and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                                    group by i.period_id, i.vat, i.type)
                                    as t group by t.vat, t.docs""",(anexo.period_id.id, journal_debit_notes))
                    refund_month = cr.fetchall()
                    if refund_month:
                        for pt in refund_month:
                            sri_code = []
                            inv_ids = []
                            vat = pt[0]                
                            for inv_br in refund_ventas:
                                if inv_br.vat == pt[0]:
                                    cliente=inv_br.partner_id.name
                                    cliente= str(inv_br.partner_id.name.upper())
                                    cliente = cliente.replace('Ñ','N')
                                    cliente = cliente.replace('Á','A')
                                    cliente = cliente.replace('É','E')
                                    cliente = cliente.replace('Í','I')
                                    cliente = cliente.replace('Ó','O')
                                    cliente = cliente.replace('Ú','U')
                                    if not pay.mode_id.sri_code in sri_code:
                                        inv_ids.append(inv_br.id)
                            voucher_ids = self.pool.get('account.voucher').search(cr, uid, [('invoice_id','in',inv_ids)])
                            pay_ids = self.pool.get('account.payments').search(cr, uid, [('vouch_id','in',voucher_ids)])
                            for pay in self.pool.get('account.payments').browse(cr, uid, pay_ids):
                                sri_code.append(pay.mode_id.sri_code)
                            #cli = self.pool.get('res.partner').browse(cr,uid,pt[0])
                            num_comprobantes_nc = pt[1]
                            if pt[2]>0.01 or pt[2]!=-0.01:
                                base_nc_untax = pt[2]
                            else:
                                base_nc_untax = 0.00
                            if pt[3]>0.01 or pt[3]!=-0.01:
                                base_nc_00 = pt[3]
                            else:
                                base_nc_00 = 0.00
                            base_nc_12 = pt[4]
                            iva_nc = pt[5]
                            iva_ret_nc = 0.00
                            renta_ret_nc = 0.00        
                            self.agree_ventas(ventas, vat, "04",  type_emi,num_comprobantes_nc, base_nc_untax, base_nc_00, base_nc_12, iva_nc, iva_ret_nc, renta_ret_nc, sri_code, cliente)
                for type in tipo_fact:    
                    if type == 'electronicas':
                        type_emi = 'E'
                        cr.execute("""select t.vat, sum(t.docs), sum(t.base_un), sum(t.base_00),sum(t.base_12),sum(t.iva_12) from 
                                    (select i.vat, count(i.id) as docs,sum(i.amount_base_vat_untaxes) as base_un ,sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12,sum(i.amount_total_vat) as iva_12 from account_invoice i 
                                    where i.period_id = %s and i.type in ('in_refund') and i.state in ('open','paid') and i.journal_id = %s
                                    and char_length(i.authorization) > 10
                                    group by i.period_id, i.vat, i.type)
                                    as t group by t.vat, t.docs""",(anexo.period_id.id, journal_sale))
                    else:
                        type_emi = 'F'
                        cr.execute("""select t.vat, sum(t.docs), sum(t.base_un), sum(t.base_00),sum(t.base_12),sum(t.iva_12) from 
                                    (select i.vat, count(i.id) as docs,sum(i.amount_base_vat_untaxes) as base_un ,sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12,sum(i.amount_total_vat) as iva_12 from account_invoice i 
                                    where i.period_id = %s and i.type in ('in_refund') and i.state in ('open','paid') and i.journal_id = %s
                                    and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                                    group by i.period_id, i.vat, i.type)
                                    as t group by t.vat, t.docs""",(anexo.period_id.id, journal_sale))
                    debit_month = cr.fetchall()
                    if debit_month:
                        for pt in debit_month:
                            sri_code = []
                            inv_ids = []
                            vat = pt[0]                    
                            for inv_br in debit_note_ventas:
                                if inv_br.vat == pt[0]:
                                    cliente=inv_br.partner_id.name
                                    cliente= str(inv_br.partner_id.name.upper())
                                    cliente = cliente.replace('Ñ','N')
                                    cliente = cliente.replace('Á','A')
                                    cliente = cliente.replace('É','E')
                                    cliente = cliente.replace('Í','I')
                                    cliente = cliente.replace('Ó','O')
                                    cliente = cliente.replace('Ú','U')                                                                        
                                    if not pay.mode_id.sri_code in sri_code:
                                        inv_ids.append(inv_br.id)
                            voucher_ids = self.pool.get('account.voucher').search(cr, uid, [('invoice_id','in',inv_ids)])
                            pay_ids = self.pool.get('account.payments').search(cr, uid, [('vouch_id','in',voucher_ids)])
                            for pay in self.pool.get('account.payments').browse(cr, uid, pay_ids):
                                sri_code.append(pay.mode_id.sri_code)
                            #cli = self.pool.get('res.partner').browse(cr,uid,pt[0])
                            num_comprobantes_nd = pt[1]
                            if pt[2]>0.01 or pt[2]!=-0.01:
                                base_nd_untax = pt[2]
                            else:
                                base_nd_untax = 0.00
                            if pt[3]>0.01 or pt[3]!=-0.01:
                                base_nd_00 = pt[3]
                            else:
                                base_nd_00 = 0.00
                            base_nd_12 = pt[4]
                            iva_nd = pt[5]
                            iva_ret_nd = 0.00
                            renta_ret_nd = 0.00
                            self.agree_ventas(ventas, vat, "05",  type_emi,num_comprobantes_nd, base_nd_untax, base_nd_00, base_nd_12, iva_nd, iva_ret_nd, renta_ret_nd, sri_code, cliente)

#                            #Retenciones del periodo actual
#                                self.agree_ventas(ventas, cli, "18", num_comprobantes_with, base_with_untax, base_with_0, base_with, iva_with, iva_ret_with, renta_ret_with)

            sale_shop = self.pool.get('sale.shop').search(cr,uid,[('emision_point','=',True)])
            ventasEstablecimiento = SubElement(root,"ventasEstablecimiento")        
            for shop in sale_shop:
                shop = self.pool.get('sale.shop').browse(cr,uid,shop)
                cr.execute("""select coalesce((sum(t.base_un) +sum(t.base_00) + sum(t.base_12)),0) as sales_month from 
                        (select i.shop_id, sum(i.amount_base_vat_untaxes)*-1 as base_un, (sum(i.amount_base_vat_00)*-1) as base_00,(sum(i.amount_base_vat_12)*-1) as base_12 from account_invoice i 
                        where i.period_id = %s and i.type in ('out_refund') and i.state in ('open','paid') and i.journal_id = %s and i.shop_id =%s
                        and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                        group by i.period_id,i.shop_id, i.type
                        UNION ALL
                        select i.shop_id, sum(i.amount_base_vat_untaxes) as base_un, sum(i.amount_base_vat_00) as base_00,sum(i.amount_base_vat_12) as base_12 from account_invoice i 
                        where i.period_id = %s and i.type in ('out_invoice') and i.state in ('open','paid') and i.journal_id = %s and i.shop_id =%s
                        and char_length(i.authorization) > 0 and char_length(i.authorization) <= 10
                        group by period_id, shop_id, type) as t""",(anexo.period_id.id,journal_refund,shop.id,anexo.period_id.id,journal_sale,shop.id,))
 
                amount = cr.fetchone()
                ventaEst = SubElement(ventasEstablecimiento,"ventaEst")
                SubElement(ventaEst, "codEstab").text = shop.number_sri
                SubElement(ventaEst, "ventasEstab").text = self.formato_numero(str(round(amount[0],2)))
 
#            FACTURAS ANULADAS
            if invoice_canceled:
                anulados = SubElement(root,"anulados")
                for inv in invoice_canceled:
                    if inv.number:
                        try:
                            numero_factura=inv.number.split('-')
                            detalle = SubElement(anulados,"detalleAnulados")
                            SubElement(detalle, "tipoComprobante").text = inv.document_type.code
                            SubElement(detalle, "establecimiento").text = numero_factura[0]
                            SubElement(detalle, "puntoEmision").text = numero_factura[1]
                            SubElement(detalle, "secuencialInicio").text = numero_factura[2]
                            SubElement(detalle, "secuencialFin").text = numero_factura[2]
                            SubElement(detalle, "autorizacion").text = inv.authorization_sales.name
                        except:
                            raise osv.except_osv('Error!', _(('The invoice canceled number=%s, partner=%s, journal=%s, date=%s contain incorrect information. Please check') %(inv.number, inv.partner_id.name, inv.journal_id.name, inv.date_invoice)))
            self.indent(root)
        return tostring(root,encoding="UTF-8")
    
    
    def act_export(self, cr, uid, ids, context={}):
        this = self.browse(cr, uid, ids)[0]
        root = self.generate_xml(cr,uid,ids)
        osv._logger.warning('Generado el ATS del mes %s - %s',self.mes_lista[0],self.mes_lista[1])
        name_file = "AT"+self.mes_lista[0]+self.mes_lista[1]+".xml"
        this.name = name_file 
        out=base64.encodestring(root)
        return self.write(cr, uid, ids, {'data':out, 'name':this.name, 'state': 'get'}, context=context)
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        hoy = datetime.date.today()
        if (hoy.month - 1) >0:
            nuevo_mes = hoy.month - 1
        else:
            nuevo_mes = hoy.month
        date_today = hoy.replace(hoy.year, nuevo_mes, 28)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',date_today),('date_stop','>=',date_today), ('company_id', '=', user.company_id.id)])
        return period_ids and period_ids[0] or None
    
    _columns = {
                'name':fields.char('name', size=20, readonly=True), 
                'period_id':fields.many2one('account.period', 'Period', required=True, domain="[('fiscalyear_id', '=', fiscalyear_id)]"),
                'company_id':fields.many2one('res.company','Company'),
                'data':fields.binary('File', readonly=True),
                'state':fields.selection([
                ('choose','Choose'),
                ('get','Get'),
                ],  'state', required=True, readonly=True),
                 }
    _defaults = {
                 'state': lambda *a: 'choose',
                 "period_id": _get_period,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'sri.ats', context=c),
                 }
    
sri_ats()
