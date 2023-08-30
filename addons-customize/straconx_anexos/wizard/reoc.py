# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
import decimal_precision as dp
from tools.translate import _
import time
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
import base64

class sri_reoc(osv.osv_memory):
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
    
    
    def tipo_identificacion(self, type, transaction):
        if transaction == 'compra':
            if type=='ruc':
                return '01'
            elif type=='ci':
                return '02'
            elif type=='passport':
                return '03'
        elif transaction == 'venta':
            if type=='ruc':
                return '04'
            elif type=='ci':
                return '05'
            elif type=='passport':
                return '06'
            elif type=='consumidor':
                return '07'
        
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
        for anexo in self.browse(cr, uid, ids, context=context):
            invoice_compras_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',anexo.period_id.id),('type','in',('in_invoice','in_refund')),('origin_transaction','=','local'),('state','in',('open','paid')),('journal_id.type','in',('purchase','purchase_liquidation','purchase_refund','debit_note'))])
            invoice_compras = self.pool.get('account.invoice').browse(cr, uid, invoice_compras_ids, context)
            company = self.pool.get('res.users').browse(cr, uid, [uid,], context)[0].company_id.partner_id
            root = Element("reoc")
            mes= anexo.period_id.name
            self.mes_lista=mes.split('/')
            SubElement(root,"numeroRuc").text=company.vat[2:]
            SubElement(root,"anio").text=anexo.fiscalyear_id.name
            SubElement(root,"mes").text=self.mes_lista[0]
            
            compras = SubElement(root,"compras")
            if invoice_compras:
                for inv in invoice_compras:
                    try:
                        numero_factura=inv.number.split('-')
                        fecha=(str(inv.date_invoice))
                        fecha=fecha.split('-')
                        detalle = SubElement(compras,"detalleCompras")
                        SubElement(detalle, "tpIdProv").text = self.tipo_identificacion(inv.partner_id.type_vat, 'compra')
                        SubElement(detalle, "idProv").text = inv.partner_id.vat[2:]
                        SubElement(detalle, "tipoComp").text = inv.tax_documents.code
                        if inv.journal_id.type in ('purchase','purchase_refund'):
                            SubElement(detalle, "aut").text = inv.authorization_purchase.name
                        else:
                            SubElement(detalle, "aut").text = inv.authorization_sales.name
                        SubElement(detalle, "estab").text = numero_factura[0]
                        SubElement(detalle, "ptoEmi").text = numero_factura[1]
                        SubElement(detalle, "sec").text = numero_factura[2]
                        SubElement(detalle, "fechaEmiCom").text = fecha[2]+"/"+fecha[1]+"/"+fecha[0]
                        retencion = SubElement(detalle, "air")
                        withhold=None
                        for ret in inv.withhold_ids:
                            if ret.state == 'approved':
                                withhold=ret
                                for line in ret.withhold_line_ids:
                                    if line.name_witthold == 'RETENCION IVA':
                                        continue
                                    detalle_retencion = SubElement(retencion, "detalleAir")
                                    SubElement(detalle_retencion, "codRetAir").text = line.tax_id.code
                                    SubElement(detalle_retencion, "porcentaje").text = self.formato_numero(str(line.percentage))
                                    SubElement(detalle_retencion, "base0").text = self.formato_numero(str(inv.amount_base_vat_00))
                                    SubElement(detalle_retencion, "baseGrav").text = self.formato_numero(str(inv.amount_base_vat_12))
                                    SubElement(detalle_retencion, "baseNoGrav").text = self.formato_numero(str(inv.amount_base_vat_untaxes))
                                    SubElement(detalle_retencion, "valRetAir").text = self.formato_numero(str(line.retained_value))
                        if withhold:
                            fecha_ret=(str(withhold.date))
                            fecha_ret=fecha_ret.split('-')
                            numero_retencion=withhold.number.split('-')
                            SubElement(detalle, "autRet").text = withhold.authorization_purchase.name
                            SubElement(detalle, "estabRet").text = numero_retencion[0]
                            SubElement(detalle, "ptoEmiRet").text = numero_retencion[1]
                            SubElement(detalle, "secRet").text = numero_retencion[2]
                            SubElement(detalle, "fechaEmiRet").text = fecha_ret[2]+"/"+fecha_ret[1]+"/"+fecha_ret[0]
                    except:
                        raise osv.except_osv('Error!', _(('The invoice number=%s, partner=%s, journal=%s, date=%s, user=%s does not contain correct information. Please check') %(inv.number, inv.partner_id.name, inv.journal_id.name, inv.date_invoice, inv.user_id.name)))
        self.indent(root)
        return tostring(root,encoding="ISO-8859-1")
    
    
    def act_export(self, cr, uid, ids, context={}):
        this = self.browse(cr, uid, ids)[0]
        root = self.generate_xml(cr,uid,ids)
        this.name = "REOC"+self.mes_lista[0]+self.mes_lista[1]+".xml"
        out=base64.encodestring(root)
        return self.write(cr, uid, ids, {'data':out, 'name':this.name, 'state': 'get'}, context=context)
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id)])
        return period_ids and period_ids[0] or None
    
    def _get_fiscalyear(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id),('state', '=', 'draft')])
        return fiscalyear_ids and fiscalyear_ids[0] or None
        
        
    _name = 'sri.reoc'
    
    _columns = {
                'name':fields.char('name', size=20, readonly=True), 
                'fiscalyear_id':fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
                'period_id':fields.many2one('account.period', 'Period', required=True, domain="[('fiscalyear_id', '=', fiscalyear_id)]"),
                'data':fields.binary('File', readonly=True),
                'state':fields.selection([
                ('choose','Choose'),
                ('get','Get'),
                ],  'state', required=True, readonly=True),
                 }
    _defaults = {
                 'state': lambda *a: 'choose',
                 "period_id": _get_period,
                 "fiscalyear_id": _get_fiscalyear,
                 }
    
sri_reoc()
