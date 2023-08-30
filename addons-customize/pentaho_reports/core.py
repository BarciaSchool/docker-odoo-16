#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################


# Todo:
#    multiple prpt files for one action - allows for alternate formats.


import io
import os
import logging
import subprocess
import xmlrpclib
import base64

import netsvc
import pooler
import report
from osv import osv, fields
from tools.translate import _
import logging
import time  
from pytz import timezone
import datetime

from tools import config

from .java_oe import JAVA_MAPPING, check_java_list, PARAM_VALUES, RESERVED_PARAMS

_logger = logging.getLogger(__name__)


from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

SERVICE_NAME_PREFIX = 'report.'
DEFAULT_OUTPUT_TYPE = 'pdf'


def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
    return len((datetime.now()).strftime(date_format))


class _format(object):
    def set_value(self, cr, uid, name, object, field, lang_obj):
        self.object = object
        self._field = field
        self.name = name
        self.lang_obj = lang_obj


class _float_format(float, _format):

    def __init__(self, value):
        super(_float_format, self).__init__()
        self.val = value or 0.0

    def __str__(self):
        digits = 2
        if hasattr(self, '_field') and getattr(self._field, 'digits', None):
            digits = self._field.digits[1]
        if hasattr(self, 'lang_obj'):
            return self.lang_obj.format('%.' + str(digits) + 'f', self.name, True)
        return str(self.val)


class _int_format(int, _format):
    def __init__(self, value):
        super(_int_format, self).__init__()
        self.val = value or 0

    def __str__(self):
        if hasattr(self, 'lang_obj'):
            return self.lang_obj.format('%.d', self.name, True)
        return str(self.val)


class _date_format(str, _format):
    def __init__(self, value):
        super(_date_format, self).__init__()
        self.val = value and str(value) or ''

    def __str__(self):
        if self.val:
            if getattr(self, 'name', None):
                date = datetime.strptime(self.name[:get_date_length()], DEFAULT_SERVER_DATE_FORMAT)
                return date.strftime(str(self.lang_obj.date_format))
        return self.val


class _dttime_format(str, _format):
    def __init__(self, value):
        super(_dttime_format, self).__init__()
        self.val = value and str(value) or ''

    def __str__(self):
        if self.val and getattr(self, 'name', None):
            return datetime.strptime(self.name, DEFAULT_SERVER_DATETIME_FORMAT)\
                   .strftime("%s %s" % (str(self.lang_obj.date_format),
                                      str(self.lang_obj.time_format)))
        return self.val


class browse_record_list(list):
    def __init__(self, lst, context):
        super(browse_record_list, self).__init__(lst)
        self.context = context

    def __getattr__(self, name):
        res = browse_record_list([getattr(x, name) for x in self], self.context)
        return res

    def __str__(self):
        return "browse_record_list(" + str(len(self)) + ")"

_fields_process = {
        'float': _float_format,
        'date': _date_format,
        'integer': _int_format,
        'datetime': _dttime_format
    }

def get_proxy_args(cr, uid, prpt_content):
    """Return the arguments needed by Pentaho server proxy.

    @return: Tuple with:
        [0]: Has the url for the Pentaho server.
        [1]: Has dict with basic arguments to pass to Pentaho server. This
             includes the connection settings and report definition but does
             not include any report parameter values.
    """

    pool = pooler.get_pool(cr.dbname)

    current_user = pool.get("res.users").browse(cr, uid, uid)
    config_obj = pool.get('ir.config_parameter')

    proxy_url = config_obj.get_param(cr, uid, 'pentaho.server.url', default='http://localhost:8080/pentaho-reports-for-openerp')

    xml_interface = config_obj.get_param(cr, uid, 'pentaho.openerp.xml.interface', default='').strip() or config["xmlrpc_interface"] or "localhost"
    xml_port = config_obj.get_param(cr, uid, 'pentaho.openerp.xml.port', default='').strip() or str(config["xmlrpc_port"])

    proxy_argument = {
                      "prpt_file_content": xmlrpclib.Binary(prpt_content),
                      "connection_settings": {'openerp': {"host": xml_interface,
                                                          "port": xml_port, 
                                                          "db": cr.dbname,
                                                          "login": current_user.login,
                                                          "password": current_user.password,
                                                          }},
                      }

    postgresconfig_host = config_obj.get_param(cr, uid, 'pentaho.postgres.host', default='localhost')
    postgresconfig_port = config_obj.get_param(cr, uid, 'pentaho.postgres.port', default='5432')
    postgresconfig_login = config_obj.get_param(cr, uid, 'pentaho.postgres.login')
    postgresconfig_password = config_obj.get_param(cr, uid, 'pentaho.postgres.password')

    if postgresconfig_host and postgresconfig_port and postgresconfig_login and postgresconfig_password:
        proxy_argument['connection_settings'].update({'postgres': {'host': postgresconfig_host,
                                                                   'port': postgresconfig_port,
                                                                   'db': cr.dbname,
                                                                   'login': postgresconfig_login,
                                                                   'password': postgresconfig_password,
                                                                   }})

    return proxy_url, proxy_argument


class Report(object):
    def __init__(self, name, cr, uid, ids, data, context):
        self.name = name
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.data = data
        self.context = context or {}
        self.pool = pooler.get_pool(self.cr.dbname)
        self.prpt_content = None
        self.default_output_type = DEFAULT_OUTPUT_TYPE

    def setup_report(self):
        ids_report = self.pool.get("ir.actions.report.xml").search(self.cr, self.uid, [("report_name", "=", self.name[7:]), ("is_pentaho_report", "=", True)], context =self.context)
#         user_name = self.pool.get('res.users').browse(self.cr,self.uid,self.uid).name
#         user_login = self.pool.get('res.users').browse(self.cr,self.uid,self.uid).login
        if not ids_report:
            raise osv.except_osv(_('Error'), _("Report service name '%s' is not a Pentaho report.") % self.name[7:])
        data = self.pool.get("ir.actions.report.xml").read(self.cr, self.uid, ids_report[0], ["pentaho_report_output_type", "pentaho_file", "model","report_name"])
        self.model_data = self.pool.get("ir.actions.report.xml").browse(self.cr,self.uid,ids_report[0]).model
        self.report_name = self.pool.get("ir.actions.report.xml").browse(self.cr,self.uid,ids_report[0]).report_name
        self.default_output_type = data["pentaho_report_output_type"] or DEFAULT_OUTPUT_TYPE
        self.prpt_content = base64.decodestring(data["pentaho_file"])
#         self.user_name = user_name
#         self.user_login = user_login



    def execute(self):
        self.setup_report()
        # returns report and format
        return self.execute_report()

    def fetch_report_parameters(self):
        """Return the parameters object for this report.

        Returns the parameters object as returned by the Pentaho
        server.
        """
        self.setup_report()

        proxy_url, proxy_argument = get_proxy_args(self.cr, self.uid, self.prpt_content)
        proxy = xmlrpclib.ServerProxy(proxy_url)
        return proxy.report.getParameterInfo(proxy_argument)

    def limit_text(self, text, size):
        text = isinstance(text, (float, long, int)) and str(text) or text
        length = len(text)
        if(size > length):
            return text + " "*(size - length)
        if(size < length):
            return text[0:size]
        return text

    def get_invoice_txt(self, cr, uid, ids, output_type, proxy_argument, context=None):
        cr.execute("""
                SELECT
                (select name from res_partner where id=i.partner_id),
                (select street from res_partner_address where id=i.address_invoice_id),
                replace(i.vat,'EC',''),
                replace(i.invoice_number_out,'-',''),
                to_char(i.date_invoice2,'dd/MM/yyyy'),
                i.amount_untaxed,
                i.amount_total_vat,
                i.amount_total,
                i.amount_base_vat_12,
                i.amount_base_vat_00,
                upper(rc.name) as company_name,
                rpc.vat as company_vat,
                rpca.street as company_street,
                upper(rpca.city) as company_city,
                rpca.phone as company_phone,
                ss.name as shop_name,
                upper(rpsa.street) as shop_street,
                upper(rpsa.city) as shop_city,
                rpsa.phone as shop_phone,
                i.invoice_number as invoice_number,
                sa.name as auth_name,
                to_char(sa.start_date,'dd/MM/yyyy'),
                to_char(sa.expiration_date,'dd/MM/yyyy'),
                rc.resolution_sri,
                to_char(rc.date_resolution,'dd/MM/yyyy'),
                i.automatic,
                i.pre_printer,
                ruv.login,
                ruc.login,
                i.nb_print,
                i.pretotal,
                i.electronic,
                i.authorization,
                sa.environment
                FROM account_invoice as i
                left join res_company rc on rc.id = i.company_id
                left join res_partner rpc on rpc.id = rc.partner_id
                left join res_partner rp on rp.id = i.partner_id
                left join res_partner_address rpca on rpca.partner_id = rc.partner_id and rpca.type='default'
                left join res_partner_address rpa on rpa.partner_id = rp.id
                left join sale_shop ss on ss.id = i.shop_id
                left join res_partner_address rpsa on rpsa.id = ss.partner_address_id
                left join sri_authorization sa on sa.id = i.authorization_sales
                left join sri_authorization_line srl on srl.authorization_id=sa.id
                left join salesman_salesman ssl on ssl.id = i.salesman_id
                left join res_users ruv on ruv.id = ssl.user_id
                left join res_users ruc on ruc.id = i.user_id
                WHERE i.id=%s""", (ids))
        invoice = cr.fetchall()
        automatic = False
        pre_printer = True
        electronic = False
        if invoice[0][25]:
            automatic = True
            sri_resolution1 = "        CONTRIBUYENTE ESPECIAL "
            sri_resolution2 = "RESOLUCION #"+invoice[0][23]+" DEL "+invoice[0][24]
        elif invoice[0][26]:
            pre_printer = True
            automatic = False
        elif invoice[0][31]:
            electronic = True
            pre_printer = False
            automatic = False
            sri_resolution1 = "        CONTRIBUYENTE ESPECIAL "
            sri_resolution2 = "RESOLUCION #"+invoice[0][23]+" DEL "+invoice[0][24]
        if invoice[0][29] <= 1 or not invoice[0][29]:
            nb_print = invoice[0][29] or 0.00
            message = ""
        else:
            nb_print = invoice[0][29]
            message = "REIMPRESION - SIN VALIDEZ TRIBUTARIA"
        nb_print = nb_print + 1
        cr.execute("update account_invoice set nb_print =%s where id =%s", (nb_print, tuple(ids)))
        if invoice[0][30] > 0:
            pretotal = invoice[0][30]
        ambiente = 'PRODUCCION'
        if invoice[0][33] == 1:
            ambiente = 'PRUEBAS'
        elif invoice[0][33] == 2:
            ambiente = 'PRODUCCION'
        if invoice[0][0]:
            inv = self.pool.get('account.invoice').browse(cr, uid, ids[0])
            partner_id = inv.partner_id
            company_id = inv.company_id
            email = inv.address_invoice_id.email or 'No registrado'
        if invoice[0][6] and invoice[0][8]:
            amount_total_vat = invoice[0][6]
            amount_base_vat_12 = invoice[0][8]
            tax_code = amount_total_vat / amount_base_vat_12
            if 0.119 <= tax_code <= 0.124:
                codigoPorcentaje = "12%"
            elif 0.125 <= tax_code <= 0.15:
                codigoPorcentaje = "14%"
        invoice = invoice[:]
        cr.execute("""select (select name_template from product_product where id=l.product_id),
            l.quantity,
            l.price_product,
            l.price_subtotal,
            (select default_code from product_product where id=l.product_id),
            l.offer,
            l.discount
            from account_invoice_line as l where l.invoice_id =%s  and l.active=True""", (ids))
        invoice_line = cr.fetchall()
        invoice_line=invoice_line[:]
        SIZE_LINE = 40
        SIZE_COLUMN_DISTANT = 5
        SIZE_CODE = 18
        EACH_LINE = 2
            
#        MAX_LINES = 23  PARA URDESA ES 23
        message1 = "\nFACTURA ELECTRONICA \nDOCUMENTO SIN VALIDEZ TRIBUTARIA\nAMBIENTE: "+ ambiente +"\n"
        
        portal_active = inv.company_id.portal_active
        
        if portal_active:        
            message2 = "PARA REVISAR SU FACTURA ELECTRONICA \nINGRESE A:\nhttp://efactura.almacenesbuenhogar.com\nSU USUARIO ES:" + invoice[0][2]+ "\nSU CLAVE ES: " + invoice[0][2]
        else:
            message2 = "RECIBIRA EN ESTE EMAIL %s LA FACTURA ELECTRONICA. POR FAVOR AGREGUE A admin@buenhogar.com.ec A SUS REMITENTES PERMITIDOS."%email
            
        cr.execute("""select period_id, sum(pending),campaing_id from sales_loyalty_partner_line where state='pending' and partner_id=%s group by campaing_id,period_id""",(partner_id.id,))
        loyalty = cr.fetchall()
        loyalty_customer = False
        bonus_accumuled = False
        if loyalty:
            data_loyalty = "DESDE         HASTA    \n"
            loyalty_obj = self.pool.get('sales.loyalty').browse(cr,uid,loyalty[0][2])
            maximun_pay = loyalty_obj.maximun_pay
            date_expired = loyalty_obj.date_expired
            loyalty_customer = True
            for l in loyalty:
                period_id = self.pool.get('account.period').browse(cr,uid,l[0])
                date_start = period_id.date_start
                if period_id.date_stop > date_expired:
                    date_stop = date_expired
                else:
                    date_stop = period_id.date_stop
                amount = l[1]
                data_loyalty = data_loyalty + date_start+ " | "+ date_stop +":USE $"+str(round(amount,2)) +" EN COMPRAS DESDE $"+str(round(amount/(maximun_pay*0.01),0))+"\n"
            bonus_obj = self.pool.get('sales.loyalty.partner.line')        
            bonus_search = bonus_obj.search(cr,uid,[('invoice_id','=', ids[0])])
            if bonus_search:
                bonus_accumuled = bonus_obj.browse(cr,uid,bonus_search[-1]) 
        
        if loyalty_customer and bonus_accumuled:
            message3="USTED HA ACUMULADO EN BONOHOGAR EN ESTA COMPRA $%s \n"%round(bonus_accumuled.bonus,2)+"\n"+data_loyalty                            
        else:
            message3= """AGRADECEMOS REVISAR SU MERCADERIA, NO SE
    ACEPTAN DEVOLUCIONES. 
    EN TEXTILES Y ARTICULOS EN OFERTA NO SE
    ACEPTAN CAMBIOS.
    EN OTROS ARTICULOS CAMBIOS HASTA 72 
    HORAS PRESENTANDO ESTE DOCUMENTO, 
    POR FAVOR REVISAR QUE LOS DATOS DE SU
    FACTURA SEAN CORRECTOS. NO SE ACEPTARAN
    MODIFICACIONES POSTERIORES.
    PARA NUESTRAS POLITICAS DE GARANTIA
    VISITAR:
    www.almacenesbuenhogar.com/garantia""" 
        message4 = """\n\n             ___________________\n
                Firma Cliente"""

        if automatic:
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n%s\n%s\n%s" % (
                                     message+'\n'+self.limit_text(INDENTATION_HEADER + invoice[0][10], SIZE_LINE), #COMPANY_NAME
                                     self.limit_text(INDENTATION_HEADER*4 + invoice[0][11][2:19], SIZE_LINE), #COMPANY_RUC
                                     self.limit_text("MATRIZ:" + invoice[0][12], SIZE_LINE), #COMPANY_STREET
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][13], SIZE_LINE), #COMPANY_CITY
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][14], SIZE_LINE), #COMPANY_PHONE
                                     self.limit_text(sri_resolution1, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text(sri_resolution2, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text("SUCURSAL: BUENHOGAR "+invoice[0][15], SIZE_LINE), #SHOP_NAME
                                     "DIRECCION: "+invoice[0][16], #SHOP_STREET
                                     self.limit_text("CIUDAD: "+invoice[0][17], SIZE_LINE), #SHOP_CITY
                                     self.limit_text("TELEFONO: "+invoice[0][18], SIZE_LINE), #SHOP_PHONE
                                     self.limit_text("FACTURA # "+invoice[0][19], SIZE_LINE), #INVOICE_NUMBER
                                     self.limit_text("AUTORIZACION: "+invoice[0][20], SIZE_LINE), #INVOICE_AUTHORIZATION
                                     self.limit_text("VALIDA DESDE "+invoice[0][21]+" AL "+invoice[0][22], SIZE_LINE), #DATE_AUTHORIZATION
                                     "CLIENTE: "+ invoice[0][0], #PARTNER
                                     "DIRECCION: "+invoice[0][1], #ADDRESS
                                     self.limit_text("IDENT.: " + invoice[0][2] +  " FECHA: " + invoice[0][4], SIZE_LINE))#DATE
            detail = "\n----------------------------------------\nProducto   Cant.  Precio  Desc. Subtotal\n----------------------------------------\n"
            for line in invoice_line:
                new_detail = "%s\n%s" % (line[4]+ ' | '+line[0] ,
                                         self.limit_text("      " +self.limit_text("{:,.2f}".format(line[1]), SIZE_COLUMN_DISTANT) +"   " +self.limit_text("{:,.4f}".format(line[2]), SIZE_COLUMN_DISTANT) +"   " + self.limit_text(str(int(line[5]+line[6])), 2) + "%   " + str("{:,.4f}".format(line[3])), SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            base_0 = ("{:,.2f}".format(invoice[0][9])).rjust(12)
            base_12 = ("{:,.2f}".format(invoice[0][8])).rjust(12)
            subtotal = ("{:,.2f}".format(invoice[0][5])).rjust(12) + " ___________________"
            iva = ("{:,.2f}".format(invoice[0][6])).rjust(12)+ " Firma Cliente"
            total =("{:,.2f}".format(invoice[0][7])).rjust(12)

            sum_invoice = "\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n\n%s" % (
                                message3+'\n'+
                                self.limit_text("BASE 0%  :" + base_0, SIZE_LINE), #BASE 0
                                self.limit_text("BASE "+codigoPorcentaje+" :" + base_12, SIZE_LINE), #BASE 12
                                self.limit_text("SUBTOTAL     :" + subtotal, SIZE_LINE), #SUBTOTAL 
                                self.limit_text("IVA "+codigoPorcentaje+"      :" + iva, SIZE_LINE), #IVA
                                self.limit_text("TOTAL        :" + total, SIZE_LINE), #IVA 
                                self.limit_text("DI " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE),#TOTAL,NUMERO INTERNO
                                self.limit_text("CAJERO: " +  invoice[0][27], SIZE_LINE),#CAJERO
                                self.limit_text("VENDEDOR: " , SIZE_LINE),#VENDEDOR
                                self.limit_text("ORIGINAL: ADQUIRIENTE - COPIA: EMISOR ",SIZE_LINE ))            

            text = "\n"+header+"\n"+"\n"+ detail+"\n\n----------------------------------------" + sum_invoice
            return (text.encode('utf8'), output_type)

        elif pre_printer:
            MAX_LINES = 25 
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s" % (self.limit_text(INDENTATION_HEADER + invoice[0][0], SIZE_LINE), #PARTNER
                                     self.limit_text(INDENTATION_HEADER + invoice[0][1], SIZE_LINE), #ADDRESS
                                     self.limit_text(INDENTATION_HEADER + invoice[0][2] + INDENTATION_HEADER + INDENTATION_HEADER + INDENTATION_HEADER + "  " + invoice[0][4], SIZE_LINE))#DATE
            detail = "\n\n"
            for line in invoice_line:
                new_detail = "%s\n%s" % (line[4]+ ' | '+line[0] ,
                                         self.limit_text("      " +self.limit_text("{:,.2f}".format(line[1]), SIZE_COLUMN_DISTANT) +"   " +self.limit_text("{:,.4f}".format(line[2]), SIZE_COLUMN_DISTANT) +"   " + self.limit_text(str(int(line[5]+line[6])), 2) + "%   " + str("{:,.4f}".format(line[3])), SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            rows_empty = MAX_LINES - len(invoice_line)-1
            for each in range(0, (rows_empty > 0) and rows_empty or 0):#EMPTY LINES
                detail += "\n"*EACH_LINE
            base_0 = ("{:,.2f}".format(invoice[0][9])).rjust(12)
            base_12 = ("{:,.2f}".format(invoice[0][8])).rjust(12)
            subtotal = ("{:,.2f}".format(invoice[0][5])).rjust(12) + " ________________"
            iva = ("{:,.2f}".format(invoice[0][6])).rjust(12)+ "   Firma Cliente"
            total =("{:,.2f}".format(invoice[0][7])).rjust(12)
            sum_invoice = "%s\n%s\n%s\n%s\n%s\n%s\n" % (
                                self.limit_text("BASE 0%  :" + base_0, SIZE_LINE), #BASE 0
                                self.limit_text("BASE "+codigoPorcentaje+" :" + base_12, SIZE_LINE), #BASE 12
                                self.limit_text("SUBTOTAL     :" + subtotal, SIZE_LINE), #SUBTOTAL 
                                self.limit_text("IVA "+codigoPorcentaje+" :     " + iva, SIZE_LINE), #IVA
                                self.limit_text("TOTAL    :" + total, SIZE_LINE), #IVA 
                                self.limit_text("REF. " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE))#TOTAL,NUMERO INTERNO
            text = "\n"+header+"\n"+"\n"+ detail + sum_invoice
            return (text.encode('utf8'), output_type)

        elif electronic:
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n%s\n%s\n%s" % (
                                     message1+'\n'+self.limit_text(INDENTATION_HEADER + invoice[0][10], SIZE_LINE), #COMPANY_NAME
                                     self.limit_text(INDENTATION_HEADER*4 + invoice[0][11][2:19], SIZE_LINE), #COMPANY_RUC
                                     self.limit_text("MATRIZ:" + invoice[0][12], SIZE_LINE), #COMPANY_STREET
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][13], SIZE_LINE), #COMPANY_CITY
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][14], SIZE_LINE), #COMPANY_PHONE
                                     self.limit_text(sri_resolution1, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text(sri_resolution2, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text("SUCURSAL: BUENHOGAR "+invoice[0][15], SIZE_LINE), #SHOP_NAME
                                     "DIRECCION: "+invoice[0][16], #SHOP_STREET
                                     self.limit_text("CIUDAD: "+invoice[0][17], SIZE_LINE), #SHOP_CITY
                                     self.limit_text("TELEFONO: "+invoice[0][18], SIZE_LINE), #SHOP_PHONE
                                     self.limit_text("FACTURA # "+invoice[0][19], SIZE_LINE), #INVOICE_NUMBER
                                     "CLAVE: "+invoice[0][32], #INVOICE_AUTHORIZATION
                                     "CLIENTE: "+ invoice[0][0], #PARTNER
                                     "DIRECCION: "+invoice[0][1], #ADDRESS
                                     self.limit_text("IDENT.: " + invoice[0][2] +  " FECHA: " + invoice[0][4], SIZE_LINE))#DATE
            detail = "\n----------------------------------------\nProducto   Cant.  Precio  Desc. Subtotal\n----------------------------------------\n"
            for line in invoice_line:
                new_detail = "%s\n%s" % (line[4]+ ' | '+line[0] ,
                                         self.limit_text("      " +self.limit_text("{:,.2f}".format(line[1]), SIZE_COLUMN_DISTANT) +"   " +self.limit_text("{:,.4f}".format(line[2]), SIZE_COLUMN_DISTANT) +"   " + self.limit_text(str(int(line[5]+line[6])), 2) + "%   " + str("{:,.4f}".format(line[3])), SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            base_0 = ("{:,.2f}".format(invoice[0][9])).rjust(12)
            base_12 = ("{:,.2f}".format(invoice[0][8])).rjust(12)
            subtotal = ("{:,.2f}".format(invoice[0][5])).rjust(12) 
            iva = ("{:,.2f}".format(invoice[0][6])).rjust(12)
            total =("{:,.2f}".format(invoice[0][7])).rjust(12)

            sum_invoice = "\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n\n%s\n%s\n%s" % (
                                self.limit_text("SUBTOTAL 0%  :" + base_0, SIZE_LINE), #BASE 0
                                self.limit_text("SUBTOTAL "+codigoPorcentaje+" :" + base_12, SIZE_LINE), #BASE 12
                                self.limit_text("SUBTOTAL     :" + subtotal, SIZE_LINE), #SUBTOTAL 
                                self.limit_text("IVA "+codigoPorcentaje+"      :" + iva, SIZE_LINE), #IVA
                                self.limit_text("TOTAL        :" + total, SIZE_LINE), #IVA 
                                self.limit_text("DI " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE),#TOTAL,NUMERO INTERNO
                                self.limit_text("VENDEDOR: " +  invoice[0][27], SIZE_LINE),#CAJERO
                                message2,
                                message3, 
                                message4 )

            text = "\n"+header+"\n"+"\n"+ detail+"\n\n----------------------------------------" + sum_invoice
            return (text.encode('utf8'), output_type)

    def get_delivery_txt(self, cr, uid, ids, output_type, proxy_argument, context=None):
        cr.execute("""
                SELECT
                (select name from res_partner where id=i.partner_id),
                (select street from res_partner_address where id=i.address_invoice_id),
                replace(i.vat,'EC',''),
                replace(i.invoice_number_out,'-',''),
                to_char(i.date_invoice,'dd/MM/yyyy'),
                i.amount_untaxed,
                i.amount_total_vat,
                i.amount_total,
                i.amount_base_vat_12,
                i.amount_base_vat_00,
                upper(rc.name) as company_name,
                rpc.vat as company_vat,
                rpca.street as company_street,
                upper(rpca.city) as company_city,
                rpca.phone as company_phone,
                ss.name as shop_name,
                upper(rpsa.street) as shop_street,
                upper(rpsa.city) as shop_city,
                rpsa.phone as shop_phone,
                i.invoice_number as invoice_number,
                sa.name as auth_name,
                to_char(sa.start_date,'dd/MM/yyyy'),
                to_char(sa.expiration_date,'dd/MM/yyyy'),
                rc.resolution_sri,
                to_char(rc.date_resolution,'dd/MM/yyyy'),
                i.automatic,
                i.pre_printer,
                ruv.login,
                ruc.login,
                sd.number,
                to_char(sd.date,'dd/MM/yyyy'),
                sd.motivo,
                to_char(sp.date,'dd/MM/yyyy'),
                to_char(sp.date_expected,'dd/MM/yyyy'),
                sp.address_id,
                i.authorization,
                dc.name,
                dc.placa,
                rpd.vat,
                rpdv.name,
                sd.nb_print,
                i.delivery_number
                FROM account_invoice as i
                left join res_company rc on rc.id = i.company_id
                left join res_partner rpc on rpc.id = rc.partner_id
                left join res_partner rp on rp.id = i.partner_id
                left join res_partner_address rpca on rpca.partner_id = rc.partner_id and rpca.type='default'
                left join res_partner_address rpa on rpa.partner_id = rp.id
                left join sale_shop ss on ss.id = i.shop_id
                left join res_partner_address rpsa on rpsa.id = ss.partner_address_id
                left join salesman_salesman ssl on ssl.id = i.salesman_id
                left join res_users ruv on ruv.id = ssl.user_id
                left join res_users ruc on ruv.id = i.user_id
                left join stock_picking sp on sp.id = i.picking_id
                left join stock_delivery sd on sd.picking_id = i.picking_id
                left join sri_authorization sa on sa.id = sd.authorization_id
                left join sri_authorization_line srl on srl.authorization_id=sa.id
                left join delivery_carrier dc on dc.id = sp.carrier_id
                left join res_partner rpd on rpd.id = dc.partner_id
                left join res_partner rpdv on rpdv.id = sp.driver_int
                WHERE i.id=%s""", (ids))
        invoice = cr.fetchall()
        if invoice[0][25] == True:
            automatic = True
            pre_printer = False            
            sri_resolution1 = "        CONTRIBUYENTE ESPECIAL "
            sri_resolution2 = "RESOLUCION #"+invoice[0][23]+" DEL "+invoice[0][24]
        elif invoice[0][26]==True:
            pre_printer = True
            automatic = False
            sri_resolution1 = "        CONTRIBUYENTE ESPECIAL "
            sri_resolution2 = "RESOLUCION #"+invoice[0][23]+" DEL "+invoice[0][24]

      
        if invoice[0][36]:
            carrier_id = invoice[0][36]
        else:
            carrier_id = " "

        if invoice[0][37]:
            placa = invoice[0][37]
        else:
            placa = " "

        if invoice[0][38]:
            carrier_vat = invoice[0][38][2:]
        else:
            carrier_vat = " "

        if invoice[0][39]:
            driver = invoice[0][39]
        else:
            driver = " "

        if invoice[0][40]==0 or not invoice[0][40]:
            nb_print = invoice[0][40] or 0.00
            message = ""                
        else:
            nb_print = invoice[0][40]
            message = "REIMPRESION - SIN VALIDEZ TRIBUTARIA"
        nb_print = nb_print + 1
        cr.execute("update stock_delivery set nb_print =%s where id =%s",(nb_print,invoice[0][41]))

        invoice=invoice[:]
        cr.execute("""select (select name_template from product_product where id=l.product_id),
            l.quantity,
            l.price_product,
            l.price_subtotal,
            (select default_code from product_product where id=l.product_id),
            l.offer,
            pu.name
            from account_invoice_line as l 
            left join product_uom pu on pu.id = l.uos_id
            where l.invoice_id =%s and l.active = True
            """, (ids))
        invoice_line = cr.fetchall()
        invoice_line=invoice_line[:]
        SIZE_LINE = 40
        SIZE_COLUMN_DISTANT = 5
        SIZE_CODE = 12
        EACH_LINE = 2
        if invoice_line[0][6]:                
            product_uom = invoice_line[0][6]
            if product_uom == 'PCE':
                product_uom = 'Unidad(es)'
            elif product_uom == 'Meters':
                product_uom = 'Metros'
            else:
                product_uom = product_uom
            product_uom = self.limit_text(product_uom,10)
        if automatic:
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n%s\n%s\n%s" % (
                                     message+'\n'+self.limit_text(INDENTATION_HEADER + invoice[0][10], SIZE_LINE), #COMPANY_NAME
                                     self.limit_text(INDENTATION_HEADER*4 + invoice[0][11][2:19], SIZE_LINE), #COMPANY_RUC
                                     self.limit_text("MATRIZ:" + invoice[0][12], SIZE_LINE), #COMPANY_STREET
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][13], SIZE_LINE), #COMPANY_CITY
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][14], SIZE_LINE), #COMPANY_PHONE
                                     self.limit_text(sri_resolution1, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text(sri_resolution2, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text("SUCURSAL: BUENHOGAR "+invoice[0][15], SIZE_LINE), #SHOP_NAME
                                     "DIRECCION: "+invoice[0][16], #SHOP_STREET
                                     self.limit_text("CIUDAD: "+invoice[0][17], SIZE_LINE), #SHOP_CITY
                                     self.limit_text("TELEFONO: "+invoice[0][18], SIZE_LINE), #SHOP_PHONE
                                     self.limit_text("GUIA DE REMISION # "+invoice[0][29], SIZE_LINE), #INVOICE_NUMBER
                                     self.limit_text("AUTORIZACION: "+invoice[0][20], SIZE_LINE), #INVOICE_AUTHORIZATION
                                     self.limit_text("VALIDA DESDE "+invoice[0][21]+" AL "+invoice[0][22], SIZE_LINE), #DATE_AUTHORIZATION
                                     self.limit_text("CLIENTE: "+ invoice[0][0], SIZE_LINE), #PARTNER
                                     "DIRECCION: "+invoice[0][1], #ADDRESS
                                     self.limit_text("IDENT.: " + invoice[0][2] +  " FECHA: " + invoice[0][30], SIZE_LINE))#DATE
            detail = "\n----------------------------------------\nProducto                     Cantidad  \n----------------------------------------\n"
            for line in invoice_line:
                new_detail = "%s\n%s" % (self.limit_text(line[0], SIZE_LINE),
                                         self.limit_text(self.limit_text(line[4], SIZE_CODE)+"      "+ str(line[1])+" "+product_uom, SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            sum_invoice = "\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s" % (
                                message+'\n'+self.limit_text("FACTURA #:" + invoice[0][19], SIZE_LINE), #FACTURA
                                self.limit_text("EMISION  :" + invoice[0][4], SIZE_LINE), #EMISION
                                self.limit_text("AUTORIZ. :" + invoice[0][35], SIZE_LINE), #AUTORIZACION                                
                                self.limit_text("MOTIVO   :" + invoice[0][31], SIZE_LINE), #MOTIVO
                                "PARTIDA  :" + invoice[0][30]+"  "+invoice[0][16], #PARTIDA
                                "LLEGADA  :" + invoice[0][33]+"  "+invoice[0][1],  #LLEGADA
                                self.limit_text("TRANSPOR.:" + carrier_id, SIZE_LINE), #TRANSPORTE
                                self.limit_text("IDENTIF. :" + carrier_vat, SIZE_LINE), #IDENTIFICACION
                                self.limit_text("CONDUCTOR:" + driver, SIZE_LINE), #CONDUCTOR
                                self.limit_text("PLACA:" + placa, SIZE_LINE))#PLACA)             

            footer_1 = "_________________________" 
            footer_2 = "       Recibido por      "
            footer_3 = "Nombre:                  " 
            footer_4 = "Ident.:                  " 
            footer_5 = "_________________________"
            footer_6 = "      Enviado por        "
            footer_7 = "ORIGINAL: DESTINATARIO " 
            footer_8 = "PRIMERA COPIA: EMISOR "
            footer_9 = "SEGUNDA COPIA: SRI"        
            footer = "\n\n\n%s\n%s\n%s\n%s\n\n\n%s\n%s\n\n%s\n%s\n%s"%(footer_1,footer_2,footer_3,footer_4,footer_5,footer_6,footer_7,footer_8,footer_9)                    
            text = "\n"+header+"\n\n"+detail+"\n\n"+"----------------------------------------" +"\n"+"        DATOS DEL COMPROBANTE           "+"\n"+"----------------------------------------" +sum_invoice+footer

            return (text.encode('utf8'), output_type)

        elif pre_printer:
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n%s\n%s\n%s" % (self.limit_text(INDENTATION_HEADER + invoice[0][10], SIZE_LINE), #COMPANY_NAME
                                     self.limit_text(INDENTATION_HEADER*4 + invoice[0][11][2:19], SIZE_LINE), #COMPANY_RUC
                                     self.limit_text("MATRIZ:" + invoice[0][12], SIZE_LINE), #COMPANY_STREET
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][13], SIZE_LINE), #COMPANY_CITY
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][14], SIZE_LINE), #COMPANY_PHONE
                                     self.limit_text(sri_resolution1, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text(sri_resolution2, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text("SUCURSAL: BUENHOGAR "+invoice[0][15], SIZE_LINE), #SHOP_NAME
                                     "DIRECCION: "+invoice[0][16], #SHOP_STREET
                                     self.limit_text("CIUDAD: "+invoice[0][17], SIZE_LINE), #SHOP_CITY
                                     self.limit_text("TELEFONO: "+invoice[0][18], SIZE_LINE), #SHOP_PHONE
                                     self.limit_text("GUIA DE REMISION # "+invoice[0][29], SIZE_LINE), #INVOICE_NUMBER
                                     self.limit_text("AUTORIZACION: "+invoice[0][20], SIZE_LINE), #INVOICE_AUTHORIZATION
                                     self.limit_text("VALIDA DESDE "+invoice[0][21]+" AL "+invoice[0][22], SIZE_LINE), #DATE_AUTHORIZATION
                                     self.limit_text("CLIENTE: "+ invoice[0][0], SIZE_LINE), #PARTNER
                                     "DIRECCION: "+invoice[0][1], #ADDRESS
                                     self.limit_text("IDENT.: " + invoice[0][2] +  " FECHA: " + invoice[0][30], SIZE_LINE))#DATE
            detail = "\n----------------------------------------\nProducto                     Cantidad  \n----------------------------------------\n"
            for line in invoice_line:
                new_detail = "%s\n%s" % (self.limit_text(line[0], SIZE_LINE),
                                         self.limit_text(self.limit_text(line[4], SIZE_CODE)+"      "+ str(line[1])+" "+product_uom, SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            sum_invoice = "\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s" % (
                                self.limit_text("FACTURA #:" + invoice[0][19], SIZE_LINE), #FACTURA
                                self.limit_text("EMISION  :" + invoice[0][4], SIZE_LINE), #EMISION
                                self.limit_text("AUTORIZ. :" + invoice[0][35], SIZE_LINE), #AUTORIZACION                                
                                self.limit_text("MOTIVO   :" + invoice[0][31], SIZE_LINE), #MOTIVO
                                "PARTIDA  :" + invoice[0][30]+"  "+invoice[0][16], #PARTIDA
                                "LLEGADA  :" + invoice[0][33]+"  "+invoice[0][1],  #LLEGADA
                                self.limit_text("TRANSPOR.:" + carrier_id, SIZE_LINE), #TRANSPORTE
                                self.limit_text("IDENTIF. :" + carrier_vat, SIZE_LINE), #IDENTIFICACION
                                self.limit_text("CONDUCTOR:" + driver, SIZE_LINE), #CONDUCTOR
                                self.limit_text("PLACA:" + placa, SIZE_LINE))#PLACA)             

            footer_1 = "_________________________" 
            footer_2 = "       Recibido por      "
            footer_3 = "Nombre:                  " 
            footer_4 = "Ident.:                  " 
            footer_5 = "_________________________"
            footer_6 = "      Enviado por        "
            footer_7 = "ORIGINAL: DESTINATARIO " 
            footer_8 = "PRIMERA COPIA: EMISOR "
            footer_9 = "SEGUNDA COPIA: SRI"        
            footer = "\n\n\n%s\n%s\n%s\n%s\n\n\n%s\n%s\n\n%s\n%s\n%s"%(footer_1,footer_2,footer_3,footer_4,footer_5,footer_6,footer_7,footer_8,footer_9)                    
            text = "\n"+header+"\n\n"+detail+"\n\n"+"----------------------------------------" +"\n"+"        DATOS DEL COMPROBANTE           "+"\n"+"----------------------------------------" +sum_invoice+footer
            return (text.encode('utf8'), output_type)

    def get_invoice_credit_txt(self, cr, uid, ids, output_type, proxy_argument, context=None):
        cr.execute("""
                SELECT
                (select name from res_partner where id=i.partner_id),
                (select street from res_partner_address where id=i.address_invoice_id),        
                replace(i.vat,'EC',''),
                replace(i.invoice_number_out,'-',''),
                to_char(i.date_invoice2,'dd/MM/yyyy'),
                i.amount_untaxed,
                i.amount_total_vat,
                i.amount_total,
                i.amount_base_vat_12,
                i.amount_base_vat_00,
                (select city from res_partner_address where id=i.address_invoice_id),
                (select phone from res_partner_address where id=i.address_invoice_id),
                i.state
                FROM account_invoice as i WHERE i.id=%s""", (ids))
        invoice = cr.fetchall()
        invoice=invoice[:]
        if invoice[0][12] not in ('paid','open'):
            raise osv.except_osv(_('Error'), _("La factura debe estar aprobada o pagada para poder imprimirla. Puede usar la cotización si desea visualizarla"))
        if invoice[0][6] and invoice[0][8]:
            amount_total_vat = invoice[0][6]
            amount_base_vat_12 = invoice[0][8]
            tax_code = amount_total_vat / amount_base_vat_12
            if 0.119 <= tax_code <= 0.124:
                codigoPorcentaje = "12%"
            elif 0.125 <= tax_code <= 0.144:
                codigoPorcentaje = "14%"
        cr.execute("""select (select name_template from product_product where id=l.product_id),
            l.quantity,
            l.price_product,
            l.price_subtotal,
            (select default_code from product_product where id=l.product_id),
            l.offer,
            l.name
            from account_invoice_line as l where l.invoice_id =%s and l.active=True""", (ids))
        invoice_line = cr.fetchall()
        invoice_line = invoice_line[:]
        SIZE_LINE = 90
        SIZE_COLUMN_DISTANT = 5
        SIZE_CODE = 16
        EACH_LINE = 1
        LEFT_SPACE = " "
#        MAX_LINES = 23  PARA URDESA ES 23
        MAX_LINES = 48 
        SIZE_INDENTATION_HEADER = 3
        INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
        spaces_a = (SIZE_LINE-len(str(invoice[0][0]))-len(str(invoice[0][2]))-SIZE_INDENTATION_HEADER-12)*" "        
        spaces_b = (SIZE_LINE-len(str(invoice[0][1]))-len(str(invoice[0][4]))-SIZE_INDENTATION_HEADER-12)*" "
        header = "\n\n\n\n\n\n\n%s\n%s\n%s" % (LEFT_SPACE*10+self.limit_text(INDENTATION_HEADER + invoice[0][0] + spaces_a+"  " + invoice[0][2], SIZE_LINE), #PARTNER
                                 LEFT_SPACE*11+self.limit_text(INDENTATION_HEADER + invoice[0][1][:50] + spaces_b + invoice[0][4], SIZE_LINE), #ADDRESS
                                 LEFT_SPACE*11+self.limit_text(INDENTATION_HEADER + str(invoice[0][10]) + INDENTATION_HEADER*17 + str(invoice[0][11]), SIZE_LINE))#DATE
        detail = ""
        for line in invoice_line:
            if line[4]:
                product_id = self.limit_text(line[4]+" - "+ line[0], 55)
            else:
                product_id = self.limit_text(line[6], 55)
            product_qty = self.limit_text(str('%.2f' % line[1]).rjust(8),8)
            price_unit = self.limit_text(str('%.2f' % line[2]).rjust(8),8)
            if line[5]:
                discount = self.limit_text(str('%.2f' % line[5]).rjust(4), 4) + "% " 
            else:
                discount = '0.00%'
            price_subtotal = self.limit_text(("{:,.2f}".format(line[3])).rjust(8),8)
            line_imp = self.limit_text(" "+product_id +" "+ product_qty +" "+price_unit+" "+ discount+ price_subtotal, SIZE_LINE)
            new_detail = "\n%s" % (line_imp)
            detail += new_detail
        rows_empty = MAX_LINES - len(invoice_line)
        for each in range(0, (rows_empty > 0) and rows_empty or 0):#EMPTY LINES
            detail += "\n"*EACH_LINE
        base_0 = ("{:,.2f}".format(invoice[0][9])).rjust(10)
        base_12 = ("{:,.2f}".format(invoice[0][8])).rjust(10)
        subtotal = ("{:,.2f}".format(invoice[0][5])).rjust(10)
        iva = ("{:,.2f}".format(invoice[0][6])).rjust(10)
        total =("{:,.2f}".format(invoice[0][7])).rjust(10)
        sum_invoice = "%s\n%s\n%s\n%s\n%s\n%s\n\n\n%s\n%s\n%s" % (""*SIZE_LINE,
                            self.limit_text(INDENTATION_HEADER*22  +"SUBTOTAL 0% :" + base_0, SIZE_LINE), #BASE 0
                            self.limit_text(INDENTATION_HEADER*22  +"SUBTOTAL "+codigoPorcentaje+" :" + base_12, SIZE_LINE), #BASE 12
                            self.limit_text(INDENTATION_HEADER*22  +"SUBTOTAL    :" + subtotal, SIZE_LINE), #SUBTOTAL 
                            self.limit_text(INDENTATION_HEADER*22  +"IVA "+codigoPorcentaje+" :     " + iva, SIZE_LINE), #IVA
                            self.limit_text(INDENTATION_HEADER*22  +"TOTAL       :" + total, SIZE_LINE),
                            self.limit_text(INDENTATION_HEADER*21 + "   __________________", SIZE_LINE), #FIRMA
                            self.limit_text(INDENTATION_HEADER*21 + "     Firma Cliente"+"\n" , SIZE_LINE),
                            self.limit_text(INDENTATION_HEADER*22 + " DI " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE) #FIRMA #FIRMA
                            )#TOTAL,NUMERO INTERNO
        text = "\n"+header+"\n\n\n"+ detail + sum_invoice
        return (text.encode('utf8'), output_type)

    def get_credit_note_txt(self, cr, uid, ids, output_type, proxy_argument, context=None):
        cr.execute("""
                SELECT
                (select name from res_partner where id=i.partner_id),
                (select street from res_partner_address where id=i.address_invoice_id),
                replace(i.vat,'EC',''),
                replace(i.invoice_number_out,'-',''),
                to_char(i.date_invoice2,'dd/MM/yyyy'),
                i.amount_untaxed,
                i.amount_total_vat,
                i.amount_total,
                i.amount_base_vat_12,
                i.amount_base_vat_00,
                upper(rc.name) as company_name,
                rpc.vat as company_vat,
                rpca.street as company_street,
                upper(rpca.city) as company_city,
                rpca.phone as company_phone,
                ss.name as shop_name,
                upper(rpsa.street) as shop_street,
                upper(rpsa.city) as shop_city,
                rpsa.phone as shop_phone,
                i.invoice_number as invoice_number,
                sa.name as auth_name,
                to_char(sa.start_date,'dd/MM/yyyy'),
                to_char(sa.expiration_date,'dd/MM/yyyy'),
                rc.resolution_sri,
                to_char(rc.date_resolution,'dd/MM/yyyy'),                
                i.automatic,
                i.pre_printer,
                ruv.login,
                ruc.login, 
                aio.invoice_number,
                i.refund_type,
                i.name,
                afr.name,
                i.amount_base_vat_untaxes,
                i.nb_print
                FROM account_invoice as i
                left join res_company rc on rc.id = i.company_id
                left join res_partner rpc on rpc.id = rc.partner_id
                left join res_partner rp on rp.id = i.partner_id
                left join res_partner_address rpca on rpca.partner_id = rc.partner_id and rpca.type='default'
                left join res_partner_address rpa on rpa.partner_id = rp.id
                left join sale_shop ss on ss.id = i.shop_id
                left join res_partner_address rpsa on rpsa.id = ss.partner_address_id
                left join sri_authorization sa on sa.id = i.authorization_sales
                left join sri_authorization_line srl on srl.authorization_id=sa.id
                left join salesman_salesman ssl on ssl.id = i.salesman_id
                left join res_users ruv on ruv.id = ssl.user_id
                left join res_users ruc on ruc.id = i.user_id                               
                left join account_invoice aio on aio.id = i.old_invoice_id
                left join account_refund_motive afr on afr.id = i.motive_id
                WHERE i.id=%s""", (ids))
        invoice = cr.fetchall()

        if invoice[0][32]:
            motivo = "MOTIVO:" + invoice[0][32]
        else:            
            motivo = "MOTIVO:" + invoice[0][31]            
        
        if invoice[0][30]=='internal':
            authorization = "N/C INTERNA "
            validated = "SIN VALOR TRIBUTARIO "
        else:            
            authorization = "AUTORIZACION: "+invoice[0][20]
            validated = "VALIDA DESDE "+invoice[0][21]+" AL "+invoice[0][22]            

        if invoice[0][29]:
            old_invoice = "APLICA A FACTURA: "+ invoice[0][29]
        else:
            old_invoice = "APLICA A FACTURA: N/A " 
        if invoice[0][25]==True:
            automatic = True
            pre_printer = False
            sri_resolution1 = "        CONTRIBUYENTE ESPECIAL "
            sri_resolution2 = "RESOLUCION #"+invoice[0][23]+" DEL "+invoice[0][24]
#        elif invoice[0][26]==True:
        else:
            pre_printer = True
            automatic = True

        if invoice[0][34]<1 or not invoice[0][34]:
            nb_print = invoice[0][34] or 0.00
            message = ""
        else:
            nb_print = invoice[0][34]
            message = "REIMPRESION - SIN VALIDEZ TRIBUTARIA"
        nb_print = nb_print + 1
        cr.execute("update account_invoice set nb_print =%s where id =%s", (nb_print, tuple(ids)))

        if invoice[0][6] and invoice[0][8]:
            amount_total_vat = invoice[0][6]
            amount_base_vat_12 = invoice[0][8]
            tax_code = amount_total_vat / amount_base_vat_12
            if 0.119 <= tax_code <= 0.124:
                codigoPorcentaje = "12%"
            elif 0.125 <= tax_code <= 0.144:
                codigoPorcentaje = "14%"

        invoice = invoice[:]
        cr.execute("""select (select name_template from product_product where id=l.product_id),
            l.quantity,
            l.price_product,
            l.price_subtotal,
            (select default_code from product_product where id=l.product_id),
            l.offer,
            l.name,
            l.discount
            from account_invoice_line as l where l.invoice_id =%s and l.active=True""", (ids))
        invoice_line = cr.fetchall()
        invoice_line=invoice_line[:]
        SIZE_LINE = 40
        SIZE_COLUMN_DISTANT = 5
        SIZE_CODE = 12
        EACH_LINE = 2
#        MAX_LINES = 23  PARA URDESA ES 23
        if pre_printer:
            MAX_LINES = 25 
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s" % (self.limit_text(INDENTATION_HEADER + invoice[0][0], SIZE_LINE), #PARTNER
                                     self.limit_text(INDENTATION_HEADER + invoice[0][1], SIZE_LINE), #ADDRESS
                                     self.limit_text(INDENTATION_HEADER + invoice[0][2] + INDENTATION_HEADER + INDENTATION_HEADER + INDENTATION_HEADER + "  " + invoice[0][4], SIZE_LINE))#DATE
            detail = "\n\n"
            for line in invoice_line:
                new_detail = "%s\n%s" % (self.limit_text(line[0], SIZE_LINE),
                                         self.limit_text(self.limit_text(line[4], SIZE_CODE) + self.limit_text(line[1], SIZE_COLUMN_DISTANT) +"   " +self.limit_text(line[2], SIZE_COLUMN_DISTANT) +"   " + self.limit_text(str(int(line[5]+line[7])), 2) + "%   " + str(line[3]), SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            rows_empty = MAX_LINES - len(invoice_line)-1
            for each in range(0, (rows_empty > 0) and rows_empty or 0):#EMPTY LINES
                detail += "\n"*EACH_LINE
            base_0 = ("{:,.2f}".format((invoice[0][9]+invoice[0][33]))).rjust(12)
            base_12 = ("{:,.2f}".format(invoice[0][8])).rjust(12)
            subtotal = ("{:,.2f}".format(invoice[0][5])).rjust(12) + " ________________"
            iva = ("{:,.2f}".format(invoice[0][6])).rjust(12)+ " Firma Cliente"
            total =("{:,.2f}".format(invoice[0][7])).rjust(12)
            sum_invoice = "%s\n%s\n%s\n%s\n%s\n%s" % (
                                self.limit_text("BASE 0%  :" + base_0, SIZE_LINE), #BASE 0
                                self.limit_text("SUBTOTAL "+ codigoPorcentaje +" :" + base_12, SIZE_LINE), #BASE 12
                                self.limit_text("SUBTOTAL     :" + subtotal, SIZE_LINE), #SUBTOTAL 
                                self.limit_text("IVA "+codigoPorcentaje+" :     " + iva, SIZE_LINE), #IVA
                                self.limit_text("TOTAL        :" + total, SIZE_LINE), #IVA 
                                self.limit_text("REF. " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE))#TOTAL,NUMERO INTERNO
            text = "\n"+header+"\n"+"\n"+ detail + sum_invoice
            return (text.encode('utf8'), output_type)

        elif automatic:
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            header = "%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n\n%s\n%s\n%s" % (
                                     message+'\n'+self.limit_text(INDENTATION_HEADER + invoice[0][10], SIZE_LINE), #COMPANY_NAME
                                     self.limit_text(INDENTATION_HEADER*4 + invoice[0][11][2:19], SIZE_LINE), #COMPANY_RUC
                                     self.limit_text("MATRIZ:"+ invoice[0][12], SIZE_LINE), #COMPANY_STREET
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][13], SIZE_LINE), #COMPANY_CITY
                                     self.limit_text(INDENTATION_HEADER*5 + invoice[0][14], SIZE_LINE), #COMPANY_PHONE
                                     self.limit_text(sri_resolution1, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text(sri_resolution2, SIZE_LINE),#RESOLUCION SRI
                                     self.limit_text("SUCURSAL: BUENHOGAR "+invoice[0][15], SIZE_LINE), #SHOP_NAME
                                     "DIRECCION: "+invoice[0][16], #SHOP_STREET
                                     self.limit_text("CIUDAD: "+invoice[0][17], SIZE_LINE), #SHOP_CITY
                                     self.limit_text("TELEFONO: "+invoice[0][18], SIZE_LINE), #SHOP_PHONE
                                     self.limit_text("NOTA DE CREDITO # "+invoice[0][19], SIZE_LINE), #INVOICE_NUMBER
                                     self.limit_text(authorization, SIZE_LINE), #INVOICE_AUTHORIZATION
                                     self.limit_text(validated, SIZE_LINE), #DATE_AUTHORIZATION
                                     self.limit_text(old_invoice, SIZE_LINE), #PARTNER
                                     self.limit_text(motivo, SIZE_LINE), #PARTNER
                                     self.limit_text("CLIENTE: "+ invoice[0][0], SIZE_LINE), #PARTNER
                                     "DIRECCION: "+invoice[0][1], #ADDRESS
                                     self.limit_text("IDENT.: " + invoice[0][2] +  " FECHA: " + invoice[0][4], SIZE_LINE))#DATE
            detail = "\n----------------------------------------\nProducto   Cant.  Precio  Desc. Subtotal\n----------------------------------------\n"
            for line in invoice_line:
                if not line[0]:
                    detalle_fact = line[6]
                    cod_fact = ' '
                else:
                    detalle_fact = line[0]
                    cod_fact = line[4]
                if not line[5]:
                    disc = 0.00
                else:
                    disc = line[5]
                    
                if not line[7]:
                    offer = 0.00
                else:
                    offer = line[7]
                new_detail = "%s\n%s" % (self.limit_text(detalle_fact, SIZE_LINE),
                                         self.limit_text(self.limit_text(cod_fact, SIZE_CODE) + self.limit_text(line[1], SIZE_COLUMN_DISTANT) +"   " +self.limit_text(line[2], SIZE_COLUMN_DISTANT) +"   " + self.limit_text(str(int(disc+offer)), 2) + "%   " + str(line[3]), SIZE_LINE))#DESCRIPTION
                detail += "\n" + new_detail
            base_0 = ("{:,.2f}".format(invoice[0][9])).rjust(12)
            base_12 = ("{:,.2f}".format(invoice[0][8])).rjust(12)
            subtotal = ("{:,.2f}".format(invoice[0][5])).rjust(12) + " ___________________"
            iva = ("{:,.2f}".format(invoice[0][6])).rjust(12)+ " Firma Cliente"
            total =("{:,.2f}".format(invoice[0][7])).rjust(12)
            sum_invoice = "\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s" % (
                                message+'\n'+self.limit_text("SUBTOTAL 0%  :" + base_0, SIZE_LINE), #BASE 0
                                self.limit_text("SUBTOTAL "+ codigoPorcentaje +" :" + base_12, SIZE_LINE), #BASE 12
                                self.limit_text("SUBTOTAL     :" + subtotal, SIZE_LINE), #SUBTOTAL 
                                self.limit_text("IVA "+codigoPorcentaje+" :     " + iva, SIZE_LINE), #IVA
                                self.limit_text("TOTAL        :" + total, SIZE_LINE), #IVA 
                                self.limit_text("DI " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE),#TOTAL,NUMERO INTERNO
                                self.limit_text("CAJERO: " +  invoice[0][27], SIZE_LINE),#CAJERO
                                self.limit_text("VENDEDOR: " +  invoice[0][28], SIZE_LINE),
                                self.limit_text("ORIGINAL: CLIENTE - COPIA: EMISOR", SIZE_LINE))#CAJERO            

            text = "\n"+header+"\n"+"\n"+ detail+"\n\n----------------------------------------" + sum_invoice
            return (text.encode('utf8'), output_type)



    def get_invoice_txt_tf(self,cr,uid,ids,output_type,proxy_argument,context=None):        
        cr.execute("""
                SELECT
                (select name from res_partner where id=i.partner_id),
                (select street from res_partner_address where id=i.address_invoice_id),
                replace(i.vat,'EC',''),
                replace(i.invoice_number_out,'-',''),
                to_char(i.date_invoice2,'dd/MM/yyyy'),
                i.amount_untaxed,
                i.amount_total_vat,
                i.amount_total,
                i.amount_base_vat_12,
                i.amount_base_vat_00
                FROM account_invoice as i WHERE i.id=%s""", (ids))
        invoice = cr.fetchall()
        invoice=invoice[:]
        cr.execute("""select (select name_template from product_product where id=l.product_id),
            l.quantity,
            l.price_product,
            l.price_subtotal,
            (select default_code from product_product where id=l.product_id),
            l.offer,
            l.name
            from account_invoice_line as l where l.invoice_id =%s and l.active=True""", (ids))
        invoice_line = cr.fetchall()
        invoice_line=invoice_line[:]
        SIZE_LINE = 40
        SIZE_COLUMN_DISTANT = 5
        SIZE_CODE = 12
        EACH_LINE = 2
        MAX_LINES = 23
        SIZE_INDENTATION_HEADER = 3        
        INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
        header = "%s\n%s\n%s\n%s" % (self.limit_text("NOMBRE:" +invoice[0][0], SIZE_LINE), #PARTNER
                                 self.limit_text("DIRECCION:" + invoice[0][1], SIZE_LINE), #ADDRESS
                                 self.limit_text("CI/RUC:" + invoice[0][2] , SIZE_LINE),
                                 self.limit_text("FECHA:" + invoice[0][4], SIZE_LINE))#DATE
        detalle_cant = self.limit_text("Nombre  Cant. Precio  %Desc  Subtotal", SIZE_LINE)         
        detail = "\n"
        for line in invoice_line:
            new_detail = "%s\n%s" % (self.limit_text(line[0], SIZE_LINE),
                                     self.limit_text(self.limit_text(line[4], SIZE_CODE) + self.limit_text(line[1], SIZE_COLUMN_DISTANT) +" " +self.limit_text(line[2], SIZE_COLUMN_DISTANT) +" " + self.limit_text(str(int(line[5])), 2) + " " + str(line[3]), SIZE_LINE))#DESCRIPTION
            detail += "\n" + new_detail
        rows_empty = MAX_LINES - len(invoice_line)
        for each in range(0, (rows_empty > 0) and rows_empty or 0):#EMPTY LINES
            detail += "\n"*EACH_LINE
        iva = str('%.2f' % (invoice[0][6]))+ "     Firma Cliente"
        sum_invoice = "%s\n%s\n%s\n%s\n%s\n%s" % ("*"*SIZE_LINE,
                            self.limit_text(INDENTATION_HEADER +"SUBTOTAL  0%:" + str(invoice[0][9]), SIZE_LINE), #BASE 0
                            self.limit_text(INDENTATION_HEADER +"SUBTOTAL 12%:" + str(invoice[0][8]), SIZE_LINE), #BASE 12
                            self.limit_text(INDENTATION_HEADER +"SUBTOTAL    :" + str(invoice[0][5]), SIZE_LINE), #SUBTOTAL 
                            self.limit_text(INDENTATION_HEADER +"IVA 12%     :" + iva, SIZE_LINE), #IVA
                            self.limit_text(INDENTATION_HEADER +"TOTAL       :" + str(invoice[0][7]) +"\n" +" DI " + ((invoice[0][3] is None or not invoice[0][3]) and context.get('invoice_number_out', "") or invoice[0][3]), SIZE_LINE))#TOTAL,NUMERO INTERNO
        text = "\n\n\n\n" + header + "\n"+detalle_cant+ detail + sum_invoice
        return (text.encode('utf8'), output_type)

    def get_print_cheques(self,cr,uid,ids,output_type,proxy_argument,context=None):
        cr.execute("""
                SELECT 
                round(AP.AMOUNT,2) AS AMOUNT,
                (rpad('', 10 , ' ') ||f_convnl(AP.AMOUNT)) AS AMOUNT_LETTER,
                RC.CITY AS CITY,
                date_part('day', AP.PAYMENT_DATE)||' DE '||upper(to_char((AP.PAYMENT_DATE), 'TMMonth'))||' DEL '||date_part('year', AP.PAYMENT_DATE) AS DATE_PAYMENT,
                AP.BENEFICIARY AS BENEFICIARY,
                RP.NAME AS PARTNER_NAME
                FROM ACCOUNT_PAYMENTS AP
                LEFT JOIN RES_PARTNER RP ON RP.ID = AP.PARTNER_ID
                LEFT JOIN RES_COMPANY RC ON RC.ID = AP.COMPANY_ID
                LEFT JOIN PAYMENT_MODE PM ON PM.ID = AP.MODE_ID
                where PM.CHECK = True and ap.vouch_id in (%s)""", (ids))          
        cheque = cr.fetchall()
        cheque=cheque[:]
        SIZE_LINE = 82        
        amount = ("{:,.2f}".format(cheque[0][0])).rjust(12)         
        if len('           '+ cheque[0][1])<=SIZE_LINE:            
            amount_letter = cheque[0][1] +'\n\n\n'
        else:
            amount_letter = cheque[0][1] +'\n\n'
        city_date = '  '+cheque[0][2]+', '+cheque[0][3]
        if cheque[0][4]:
            benef = cheque[0][4] 
        else:
            benef = cheque[0][5]
        if (len('           '+benef)+len(amount))<=SIZE_LINE:
            dato = 72 - len('           '+benef) - len(amount)
            new_space = ' '*dato
            beneficiary = '           '+benef+new_space+amount
        
        header = "\n\n\n\n%s\r%s%s\n\f" % (self.limit_text(beneficiary, SIZE_LINE), #BENEFICIARIO + VALOR
                                 amount_letter, #VALOR
                                 self.limit_text(city_date , SIZE_LINE))#FECHA
        text = header
        return (text.encode('utf8'), output_type)

    
    def get_labels_txt(self,cr,uid,ids,output_type,proxy_argument,context=None):
        wiz = self.pool.get('label.wizard.product').browse(self.cr,self.uid,ids)
        wiz = wiz[0]
        text = ''
        if wiz.line_ids:
            text_image=("""rN
S2
D7
ZT
JF
O
R5,0
Q200
q831
N

A740,30,1,2,1,1,N,"%s"
A720,30,1,2,1,1,N,"%s"
A700,30,1,2,1,1,N,"%s"
A680,30,1,3,1,1,N,"%s"
B650,30,1,2,2,5,50,N,"%s"
A590,30,1,4,1,1,N,"%s"

A510,30,1,2,1,1,N,"%s"
A490,30,1,2,1,1,N,"%s"
A470,30,1,2,1,1,N,"%s"
A450,30,1,3,1,1,N,"%s"
B420,30,1,2,2,5,50,N,"%s"
A360,30,1,4,1,1,N,"%s"

A240,30,1,2,1,1,N,"%s"
A220,30,1,2,1,1,N,"%s"
A200,30,1,2,1,1,N,"%s"
A180,30,1,3,1,1,N,"%s"
B150,30,1,2,2,5,50,N,"%s"
A80,30,1,4,1,1,N,"%s"
P%s""")
                
            text_image_discount =("""rN
S2
D7
ZT
JF
O
R5,0
Q200
q831
N

A760,30,1,2,1,1,N,"%s"
A740,30,1,2,1,1,N,"%s"
A720,30,1,2,1,1,N,"%s"
A700,30,1,3,1,1,N,"%s"
B670,30,1,2,2,5,50,N,"%s"
A630,30,1,4,1,1,N,"%s"
A600,30,1,5,1,1,B,"%s"

A520,30,1,2,1,1,N,"%s"
A500,30,1,2,1,1,N,"%s"
A480,30,1,2,1,1,N,"%s"
A460,30,1,3,1,1,N,"%s"
B430,30,1,2,2,5,50,N,"%s"
A390,30,1,4,1,1,N,"%s"
A360,30,1,5,1,1,B,"%s"

A290,30,1,2,1,1,N,"%s"
A270,30,1,2,1,1,N,"%s"
A250,30,1,2,1,1,N,"%s"
A230,30,1,3,1,1,N,"%s"
B210,30,1,2,2,5,50,N,"%s"
A170,30,1,4,1,1,N,"%s"
A140,30,1,5,1,1,B,"%s"
P%s""")
            text_image_big=("""rN
S4
D7
Q320
q831
ZT
JB
OD
R215,0
f100
N
A320,30,1,2,1,1,N,"%s"
A300,30,1,2,1,1,N,"%s"
A280,30,1,2,1,1,N,"%s"
A250,40,1,4,1,1,N,"%s"
B220,40,1,2,2,5,50,N,"%s"
A160,30,1,4,2,1,N,"%s"
P%s""")
            text_image_big_discount=("""rN
S4
D7
Q320
q831
ZT
JB
OD
R215,0
f100
N
A330,30,1,2,1,1,N,"%s"
A310,30,1,2,1,1,N,"%s"
A290,30,1,2,1,1,N,"%s"
A260,40,1,4,1,1,N,"%s"
B230,40,1,2,2,5,50,N,"%s"
A170,30,1,4,2,1,N,"%s"
A110,60,1,4,2,1,B,"%s"
P%s""")
            
            text_image_big_discount_new=("""rN
S4
D7
Q304,024
q831
ZT
JF
OD
R183,0
f100
N
A316,294,2,4,1,1,N,"%s"
A447,243,2,4,1,1,N,"%s"
A451,211,2,4,1,1,N,"%s"
B396,180,2,1,2,6,80,B,"%s"
A415,68,2,3,2,2,N,"%s"
P%s""")           

            for line in wiz.line_ids:
                name = (line.product_id.product_tmpl_id.name).encode("utf-8")              
                name = unicode(name, 'utf-8')
                default_code = line.product_id.default_code
                p_net = round(line.product_id.p_net,2) or round(line.product_id.product_tmpl_id.list_price,2)
                p_net = str('PVP %.2f' % (p_net))
                discount = str('- %.0f' % (line.product_id.discount_percent))+'%'
                discount = discount[:4]
                company_name = "BUENHOGAR" or self.pool.get('res.users').browse(cr,uid,uid).company_id.name[:20]
                qty = line.quantity                                                 
                if wiz.template_id =='label_90x25':
                    if len(name) > 15:
                        name1 = name[:25]+" "
                        name2 = name[25:30]+" "
                    else:
                        name1 = name
                        name2 = "__________"
                    qty_n = int(qty/3)
                    if (qty - (qty_n*3)) == 0:
                        qty = qty_n
                    else:
                        qty = qty_n + 1                    
                    if wiz.printer_id =='ZebraZM400':
                        text=("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNM^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD10^JUS^MD15^LRN^CI0^XZ^XA^MMT^PW719^LL0200^LS0^BY1,3,45^FT505,110^BCN,,N,N^FD%s^FS^BY1,3,45^FT270,110^BCN,,N,N^FD%s^FS^BY1,3,45^FT30,110^BCN,,N,N^FD%s^FS^FT507,25^A0N,28,28^FH^FD %s^FS^FT267,25^A0N,28,28^FH^FD%s ^FS^FT27,25^A0N,28,28^FH^FD%s  ^FS^FT495,130^A0N,14,14^FH\^FD%s ^FS^FT495,150^A0N,14,14^FH\^FD%s ^FS^FT252,130^A0N,14,14^FH\^FD%s ^FS^FT252,150^A0N,14,14^FH\^FD%s ^FS^FT15,130^A0N,14,14^FH\^FD%s ^FS^FT15,150^A0N,14,14^FH\^FD%s ^FS^FT550,170^A0N,11,12^FH\^FD%s ^FS^FT300,170^A0N,11,12^FH\^FD%s ^FS^FT30,170^A0N,11,12^FH\^FD%s ^FS^FT527,55^A0N,28,28^FH\^FD%s ^FS^FT287,55^A0N,28,28^FH\^FD%s ^FS^FT47,55^A0N,28,28^FH\^FD%s ^FS^PQ%s,0,1,Y^XZ""")% (default_code,default_code,default_code,p_net,p_net,p_net,name1,name2,name1,name2,name1,name2,company_name,company_name,company_name,default_code,default_code,default_code,qty) +"\n"+ text
                    elif wiz.printer_id == 'ZebraGC420':
                        text=("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNM^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD10^JUS^MD6^LRN^CI0^XZ^XA^MMT^PW719^LL0200^LS0^BY1,3,45^FT505,110^BCN,,N,N^FD%s^FS^BY1,3,45^FT270,110^BCN,,N,N^FD%s^FS^BY1,3,45^FT30,110^BCN,,N,N^FD%s^FS^FT507,25^A0N,28,28^FH^FD %s^FS^FT267,25^A0N,28,28^FH^FD%s ^FS^FT27,25^A0N,28,28^FH^FD%s^FS^FT505,130^A0N,14,14^FH\^FD%s ^FS^FT505,150^A0N,14,14^FH\^FD%s ^FS^FT265,130^A0N,14,14^FH\^FD%s ^FS^FT265,150^A0N,14,14^FH\^FD%s ^FS^FT15,130^A0N,14,14^FH\^FD%s ^FS^FT15,150^A0N,14,14^FH\^FD%s ^FS^FT550,170^A0N,11,12^FH\^FD%s ^FS^FT300,170^A0N,11,12^FH\^FD%s ^FS^FT30,170^A0N,11,12^FH\^FD%s ^FS^FT527,55^A0N,28,28^FH\^FD%s ^FS^FT287,55^A0N,28,28^FH\^FD%s ^FS^FT47,55^A0N,28,28^FH\^FD%s ^FS^PQ%s,0,1,Y^XZ""")% (default_code,default_code,default_code,p_net,p_net,p_net,name1,name2,name1,name2,name1,name2,company_name,company_name,company_name,default_code,default_code,default_code,qty) +"\n"+ text
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        return True                      
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                elif wiz.template_id =='label_58x25dc':
                    if len(name) > 25:
                        name1 = name[:30]+" "
                        name2 = name[30:55]+" "
                    else:
                        name1 = name
                        name2 = "___________"
                    if wiz.printer_id =='ZebraZM400':
                        text = ("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNM^MTD^PON^PMN^LH0,0^JMA^PR2,2~SD15^JUS^LRN^CI0^XZ^XA^MMT^PW464^LL0200^LS0^BY1,3,45^FT263,54^BCN,,N,N^FD>:%s^FS^BY1,3,45^FT40,56^BCN,,N,N^FD>:%s^FS^FT232,120^A0N,14,14^FH\^FD%s^FS^FT293,79^A0N,25,20^FH\^FD%s^FS^FT232,100^A0N,14,14^FH\^FD%s^FS^FT10,120^A0N,14,14^FH\^FD%s^FS^FT40,79^A0N,25,20^FH\^FD%s^FS^FT10,100^A0N,14,14^FH\^FD%s^FS^FT332,146^A0N,28,28^FH\^FD%s^FS^FT311,167^A0N,11,12^FH\^FD%s^FS^FT55,147^A0N,28,28^FH\^FD%s^FS^FT89,169^A0N,11,12^FH\^FD%s^FS^PQ%s,0,1,Y^XZ""")%(default_code,default_code,name2,default_code,name1,name2,default_code,name1,p_net,company_name,p_net,company_name,qty) +"\n"+ text
                    elif wiz.printer_id == 'ZebraGC420':
                        text = ("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNM^MTD^PON^PMN^LH0,0^JMA^PR2,2~SD15^JUS^LRN^CI0^XZ^XA^MMT^PW464^LL0200^LS0^BY1,3,45^FT263,54^BCN,,N,N^FD>:%s^FS^BY1,3,45^FT40,56^BCN,,N,N^FD>:%s^FS^FT232,120^A0N,14,14^FH\^FD%s^FS^FT293,79^A0N,25,20^FH\^FD%s^FS^FT232,100^A0N,14,14^FH\^FD%s^FS^FT10,120^A0N,14,14^FH\^FD%s^FS^FT40,79^A0N,25,20^FH\^FD%s^FS^FT10,100^A0N,14,14^FH\^FD%s^FS^FT332,146^A0N,28,28^FH\^FD%s^FS^FT311,167^A0N,11,12^FH\^FD%s^FS^FT55,147^A0N,28,28^FH\^FD%s^FS^FT89,169^A0N,11,12^FH\^FD%s^FS^PQ%s,0,1,Y^XZ""")%(default_code,default_code,name2,default_code,name1,name2,default_code,name1,p_net,company_name,p_net,company_name,qty) +"\n"+ text
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        return True
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                elif wiz.template_id =='label_56x25an':
                    if len(name) > 45:
                        name1 = name[:45]
                    else:
                        name1 = name                                                        
                    if wiz.printer_id =='ZebraZM400':
                        text = ("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNM^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD15^JUS^LRN^CI0^XZ^XA^MMC^PW448^LL0200^LS0^BY2,3,68^FT72,79^BCN,,Y,N^FD%s^FS^FT17,120^A0N,25,16^FH\^FD%s^FS^FT150,180^A0N,11,12^FH\^FD%s^FS^FT259,157^A0N,28,28^FH\^FD%s^FS^PQ%s,1,1,Y^XZ""")% (default_code,name1,company_name,p_net,qty) +"\n"+ text
                    elif wiz.printer_id == 'ZebraGC420':
                        text = ("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNM^MTt^PON^PMN^LH0,0^JMA^PR2,2~SD15^JUS^LRN^CI0^XZ^XA^MMC^PW448^LL0200^LS0^BY2,3,68^FT72,79^BCN,,Y,N^FD%s^FS^FT17,120^A0N,25,16^FH\^FD%s^FS^FT150,180^A0N,11,12^FH\^FD%s^FS^FT259,157^A0N,28,28^FH\^FD%s^FS^PQ%s,1,1,Y^XZ""")% (default_code,name1,company_name,p_net,qty) +"\n"+text
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        return True
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                elif wiz.template_id =='label_90x25_offer_image':
                    if len(name) > 16:
                        name1 = name[:12]+" "
                        name2 = name[12:24]+" "
                    else:
                        name1 = name
                        name2 = "__________"
                    qty_n = int(qty/3)
                    if (qty - (qty_n*3)) == 0:
                        qty = qty_n
                    else:
                        qty = qty_n + 1                    
                    if wiz.printer_id =='ZebraZM400':
                        text= text_image % (company_name, name1,name2,default_code,default_code,p_net,company_name,name1,name2,default_code,default_code,p_net,company_name,name1,name2,default_code,default_code,p_net,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraGC420':
                        text= text_image % (company_name, name1,name2,default_code,default_code,p_net,company_name,name1,name2,default_code,default_code,p_net,company_name,name1,name2,default_code,default_code,p_net,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        text= text_image % (company_name, name1,name2,default_code,default_code,p_net,company_name,name1,name2,default_code,default_code,p_net,company_name,name1,name2,default_code,default_code,p_net,qty) +"\n"+ text                        
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                elif wiz.template_id =='label_90x25_offer_discount':
                    if len(name) > 16:
                        name1 = name[:12]+" "
                        name2 = name[12:24]+" "
                    else:
                        name1 = name
                        name2 = "__________"
                    qty_n = int(qty/3)
                    if (qty - (qty_n*3)) == 0:
                        qty = qty_n
                    else:
                        qty = qty_n + 1                    
                    if wiz.printer_id =='ZebraZM400':
                        text= text_image_discount % (company_name, name1,name2,default_code,default_code,p_net,discount,company_name,name1,name2,default_code,default_code,p_net,discount,company_name,name1,name2,default_code,default_code,p_net,discount,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraGC420':
                        text= text_image_discount % (company_name, name1,name2,default_code,default_code,p_net,discount,company_name,name1,name2,default_code,default_code,p_net,discount,company_name,name1,name2,default_code,default_code,p_net,discount,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        text= text_image_discount % (company_name, name1,name2,default_code,default_code,p_net,discount,company_name,name1,name2,default_code,default_code,p_net,discount,company_name,name1,name2,default_code,default_code,p_net,discount,qty) +"\n"+ text                        
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                    
                elif wiz.template_id =='label_58x25_offer_image':
                    if len(name) > 25:
                        name1 = name[:25]+" "
                        name2 = name[25:50]+" "
                    else:
                        name1 = name
                        name2 = "__________"
                    qty_n = int(qty/1)
                    if (qty - (qty_n*1)) == 0:
                        qty = qty_n
                    else:
                        qty = qty_n + 1                    
                    if wiz.printer_id =='ZebraZM400':
                        text= text_image_big % (company_name,name1,name2,default_code,default_code,p_net,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraGC420':
                        text= text_image_big % (company_name,name1,name2,default_code,default_code,p_net,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        text= text_image_big_discount_new % (company_name,name1,name2,default_code,p_net,qty) +"\n"+ text
                    #elif wiz.printer_id == 'ZebraTLP-2844':
                    # text= text_image_big_discount_new % (company_name,name1,name2,default_code,default_code,p_net,discount,qty) +"\n"+ text                          
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                
                elif wiz.template_id =='label_58x25_offer_discount':
                    if len(name) > 20:
                        name1 = name[:20]+" "
                        name2 = name[20:40]+" "
                    else:
                        name1 = name
                        name2 = "__________"
                    qty_n = int(qty/1)
                    if (qty - (qty_n*1)) == 0:
                        qty = qty_n
                    else:
                        qty = qty_n + 1                    
                    if wiz.printer_id =='ZebraZM400':
                        text= text_image_big_discount % (company_name,name1,name2,default_code,default_code,p_net,discount,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraGC420':
                        text= text_image_big_discount % (company_name,name1,name2,default_code,default_code,p_net,discount,qty) +"\n"+ text                        
                    elif wiz.printer_id == 'ZebraTLP-2488':
                        text= text_image_big_discount_new % (company_name,name1,name2,default_code,p_net,discount,qty) +"\n"+ text
                    #elif wiz.printer_id == 'ZebraTLP-2844':
                        #text= text_image_big_discount_new % (company_name,name1,name2,default_code,p_net,discount,qty) +"\n"+ text                            
                    else:
                        raise osv.except_osv(_('Error'), _("Printer is not supported."))
                    
                else:
                    raise osv.except_osv(_('Error'), _("Pentaho returned no data for the report '%s'. Check report definition and parameters.") % self.name[7:])                
#        return (text.encode('ISO8859-1'), output_type)
        return (text.encode('utf8'), output_type)

    def get_print_statement(self,cr,uid,ids,output_type,proxy_argument,context=None):        
        bank_id = self.pool.get('account.bank.statement')
        bank = bank_id.browse(cr, uid, ids[0], context)
        bank_lines = bank.line_ids
        bank_moves = bank.total_ids
        bank_account = bank.move_line_ids
        credit_notes_app = bank.line_ids
        cash_moves=0
        cash_changed=0
        cash_payment=0
        cia_data = bank.company_id
        max_diff = 0
        g={}
        modes_ids=[]
        withholds=[]        
        sales_obj = self.pool.get('account.invoice')     
        printer_id = bank.printer_id.id 
        date_cash = bank.date
        if bank.closing_date:
            date_close = bank.closing_date
        else:
            date_close = bank.date
        sales_id = sales_obj.search(cr,uid,[('user_id','=',bank.user_id.id),('printer_id','=',printer_id),('date_invoice2','>=',date_cash),('date_invoice2','<=',date_close),('state','not in',('draft',))],context=None, order = 'number')                            
        account_customer = bank.company_id.property_account_advance_customer.id
#        sl = sales_obj.browse(cr,uid,sales_id,context=None)
        advances=[]
        for sales in sales_id:
            s = sales_obj.browse(cr,uid,sales,context=None)
            if s.withhold_id:
#                for w in s.withhold_id:
                if s.withhold_id.state=='approved' and s.withhold_id.transaction_type=='sale':
                    withholds.append(s.withhold_id)
        
        for ad in bank_account:
            if ad.account_id.id==account_customer:
                advances.append(ad)
                
        for u in bank_lines:
            if u.type not in ('changed'):
                if not g.has_key(u.payment_id.mode_id.name):
                    g[u.payment_id.mode_id.name]=[u]
                else:
                    g[u.payment_id.mode_id.name]+=[u]
        
        for i in g.keys():
            modes_ids.append((i,g[i]))
        
        for u in bank_lines:
            if u.type=='customer' and u.payment_id.mode_id.cash==True:
                cash_moves+=u.amount
            if u.type=='supplier' and u.payment_id.mode_id.cash==True:
                cash_payment+=u.amount
            if u.type=='changed':
                cash_changed+=u.amount
        SIZE_LINE = 40
        SIZE_COLUMN_DISTANT = 5
#        SIZE_CODE = 12
#        EACH_LINE = 2
#        MAX_LINES = 18
        SIZE_INDENTATION_HEADER = 3
        INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER        


        header = "%s\n%s\n%s\n%s\n%s" % (self.limit_text(str("COMPAÑIA:").decode('utf-8') +bank.company_id.name, SIZE_LINE), #PARTNER
                                 self.limit_text("TIENDA:" + bank.shop_id.name, SIZE_LINE), #ADDRESS
                                 self.limit_text("CAJA:" + bank.printer_id.name , SIZE_LINE),
                                 self.limit_text("USUARIO:" + bank.user_id.name, SIZE_LINE),#DATE
                                 self.limit_text("FECHA:" + date_cash, SIZE_LINE))#DATE
        header_sales = "TRANSACCIONES COMERCIALES"+"\n"+"Identif." +" "+"Cliente" +" "+"Documento" +" " +"Valor"+" " +" Saldo" 
        ventas = ""
        notas = ""
        ventas_totales = 0.00
        credit_totales = 0.00
        if sales_id:
            for s in sales_id:
                sales = sales_obj.browse(cr,uid,s,context=None)          
                type_factura = "FACTURAS"
                if sales.type =='out_invoice':
                    ventas = ventas + (self.limit_text(sales.vat[2:15], 18) +self.limit_text(sales.partner_id.name[:20], 22)+"\n" +self.limit_text(str(sales.invoice_number), 26) +self.limit_text(str('%.2f' % (sales.amount_total)), 10)+self.limit_text(str('%.2f' % (sales.residual)), 10)+"\n")
                    ventas_totales += sales.amount_total
                type_notas = "NOTAS DE CREDITO"
                if sales.type =='out_refund':
                    notas = notas + (self.limit_text(sales.vat[2:15], 18) +self.limit_text(sales.partner_id.name[:20], 30) +"\n" +self.limit_text(str(sales.invoice_number), 26)+"\n"+self.limit_text(str('%.2f' % (sales.amount_total)), 10)+self.limit_text(str('%.2f' % (sales.residual)), 10)+"\n")                
                    credit_totales += sales.amount_total
            total_ventas =   "TOTAL VENTAS    $"+ str(ventas_totales) + "\n\n"
            total_creditos = "TOTAL N/CREDITO $"+str(credit_totales) + "\n\n"
        else:
            type_factura = ""
            type_notas = ""
            ventas = ""
            total_ventas =   "TOTAL VENTAS    $"+ str(ventas_totales) + "\n\n"
            total_creditos = "TOTAL N/CREDITO $"+str(credit_totales) + "\n\n"
        header_modo = "TRANSACCIONES DE PAGOS"+"\n"+"Id Cliente " +" "+"Pago  " +" " +"Banco  "+" Cuenta " +"  Doc.  "+" Monto" +"\n"
        total_payment = 0.00
        detalle=""
        if modes_ids:
            for m in modes_ids:
#                modo=(m[0]).decode("utf-8", "replace")                
                for l in m[1]:
                    modo=str(m[0].decode('utf-8'))
                    modo = "\n" + modo 
                    if l:
                        if l.payment_id.bank_account_id.acc_number:
                            acc_number = " "+self.limit_text((l.payment_id.bank_account_id.acc_number),10) 
                        else:
                            acc_number = " "
                        if l.payment_id.name:                            
                            payment_name = self.limit_text((l.payment_id.name),10)
                        else:
                            payment_name = " "
                        if l.payment_id.bank_id.name:
                            bank_name = self.limit_text((l.payment_id.bank_id.name),10)
                        else:
                            bank_name = " "                                                                            
                        a = (self.limit_text(l.partner_id.vat[2:15], 17))+(self.limit_text(l.name[6:], 15))
                        b = bank_name + acc_number + payment_name +self.limit_text(str(' %.2f' % (l.amount)), 9)+"\n"
                    total_payment += l.amount
                    total_pagos = "\n"+"Subtotal "+str(m[0])+" "+str('$ %.2f' % (total_payment))+" en "+ str(len(m[1]))+" trans."
                    detalle = detalle + "%s %s %s" % (modo,a,b)
                detalle = detalle + total_pagos+"\n"                 
        else:
            modo = ""
            detalle = ""
        estado = "%s\n%s\n%s\n%s\n%s" % (self.limit_text("SALDO INICIAL:" +INDENTATION_HEADER+ str('%.2f' % (bank.balance_start)), SIZE_LINE), #PARTNER
                                         self.limit_text("EFECTIVO     :" +INDENTATION_HEADER+ str('%.2f' % (bank.total_entry_encoding)), SIZE_LINE), #ADDRESS
                                         self.limit_text("OTRAS TRANS. :" +INDENTATION_HEADER+ str('%.2f' % (bank.total_other_incomes)) , SIZE_LINE),
                                         self.limit_text("SALDO FINAL  :" +INDENTATION_HEADER+ str('%.2f' % (bank.balance_end_cash)), SIZE_LINE),#DATE
                                         self.limit_text("A DEPOSITAR  :" +INDENTATION_HEADER+ str('%.2f' % (bank.total_deposit)), SIZE_LINE))#DATE
        total_ingresos =  str('VENTAS NETAS: $%.2f' % (ventas_totales - credit_totales))
        total_cobros = "TOTAL COBROS: $"+str('%.2f' % (total_payment))+"\n"
        text = "\n"+ header + "\n\n"+header_sales + "\n"+type_factura +"\n" +ventas + total_ventas +type_notas+"\n"+notas+"\n"+total_creditos+"\n"+header_modo + detalle +"\n"+ total_ingresos+"\n"+total_cobros +"\n"+"RESUMEN "+"\n"+estado
        return (text.encode('utf8'), output_type)

    def get_internal_transfer(self,cr,uid,ids,output_type,proxy_argument,context=None):        
        cr.execute("""
                select 
                rc.name as company_id,
                sp.name,
                sp.state,
                ss1.name as shop_id,
                ss2.name as shop_dest,
                ll1.name as loc_id,
                ll2.name as loc_dest,
                ru1.name as digiter_id,
                ru2.name as warehouse_id,
                sp.date as date,
                dc.name as carrier_id
                from stock_picking as sp
                left join stock_location as sl1 on sl1.id = sp.location_id
                left join stock_location as sl2 on sl2.id = sp.location_dest_id
                left join sale_shop ss1 on ss1.id = sp.shop_id
                left join sale_shop ss2 on ss2.id = sp.shop_id_dest
                left join stock_location ll1 on ll1.id = sp.location_id
                left join stock_location ll2 on ll2.id = sp.location_dest_id
                left join res_company rc on rc.id = sp.company_id
                left join res_users ru1 on ru1.id = sp.digiter_id
                left join res_users ru2 on ru2.id= sp.warehouse_id
                left join delivery_carrier dc on dc.id = sp.carrier_id
                where sp.id = %s""", (ids))
        invoice = cr.fetchall()
        invoice=invoice[:]
        company_id = invoice[0][0]
        picking = invoice[0][1]
        state = invoice[0][2]
        if state=='draft':
            state = 'Borrador'
            nname = 'SOLICITUD DE '
        elif state == 'confirmed':
            state = 'En Ejecucción'
            nname = ''
        elif state == 'done':
            state = 'Realizado'
            nname = ''
        elif state == 'cancel':
            state = 'Anulado'
            nname = ''
        else:
            state = 'Sin Estado'
        ubi_id = invoice[0][5]
        ubi_dest = invoice[0][6]
        shop_id = invoice[0][3]
        if shop_id:
            cr.execute("""select street from res_partner_address where id = (select partner_address_id from sale_shop where name =%s)""",(shop_id,))
            address_id = cr.fetchall()
            if address_id:
                address_id= address_id[0][0]
            shop_id = shop_id + ' - '+ address_id
        shop_dest = invoice[0][4]
        if shop_dest:
            cr.execute("""select street from res_partner_address where id = (select partner_address_id from sale_shop where name =%s)""",(shop_dest,))
            address_id_dest = cr.fetchall()
            if address_id_dest:
                address_id_dest = address_id_dest[0][0]
            shop_dest = shop_dest + ' - '+ address_id_dest
        digiter_id = invoice[0][7]
        warehouse_id = invoice[0][8]
        if not digiter_id: 
            digiter_id = " "
        if not warehouse_id:
            warehouse_id = " "
        date = invoice[0][9]
        if date:
            date = date[8:10]+'-'+date[5:7]+'-'+date[0:4]
        now = time.strftime('%d-%m-%Y')
        carrier_id = invoice[0][10]
        if not carrier_id:
            carrier_id = "No hay transportista definido"
        cr.execute("""select login from res_users where id =%s""",(uid,))
        users= cr.fetchall()
        usuario = users[0][0]
        SIZE_INDENTATION_HEADER = 3
        LEFT_SPACE = " "
        SIZE_LINE = 80
        MAX_LINES = 75
        INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
        a = self.limit_text(company_id + LEFT_SPACE*7 + 'Impreso el:' +now + LEFT_SPACE*2 + 'por:' + usuario, SIZE_LINE) 
        b = self.limit_text(LEFT_SPACE*20+nname+' TRANSFERENCIA # '+picking+'('+state+')', SIZE_LINE) #PICKING
        c = self.limit_text(('TIENDA ORIGEN : '+shop_id ), SIZE_LINE)
        d = self.limit_text(('UBICACION ORIGEN : '+ubi_id ), SIZE_LINE)
        e = self.limit_text(('TIENDA DESTINO: '+shop_dest), SIZE_LINE)
        f = self.limit_text(('UBICACION DESTINO : '+ubi_dest ), SIZE_LINE)
        g = self.limit_text(('SOLICITADO POR: '+digiter_id), SIZE_LINE) 
        h = self.limit_text(('DESPACHADO POR: '+warehouse_id), SIZE_LINE)
        i = self.limit_text(('FECHA         : '+date[:10] +LEFT_SPACE*20+'TRANSPORTISTA: '+carrier_id), SIZE_LINE)
        j = "---------------------------------------------------------------------------------"
        k = "         PRODUCTO                                                  CANTIDAD      "
        l = "---------------------------------------------------------------------------------"
        header = "\n%s\n\n%s\n\n%s\n%s\n%s\n%s\n%s\n\n%s\n\n%s\n" % (a,b,c,d,e,f,g,h,i)
        header_report = "\n%s\n%s\n%s" % (j,k,l)
        cr.execute("""
                    select 
                    sm.id,
                    u.name as ubication_id,
                    sl.name as location_id,
                    pp.default_code as default_code,
                    pp.name_template as name_template,
                    pc.name as categ_id,
                    pu.name as product_uom,
                    sm.product_qty as product_qty,
                    picking_id as picking_id
                    from stock_move as sm
                    left join product_product as pp on pp.id = sm.product_id
                    left join product_template as pt on pt.id = pp.product_tmpl_id
                    left join product_category as pc on pc.id = pt.categ_id
                    left join ubication as u on u.id = sm.ubication_id
                    left join stock_location as sl on sl.id = sm.location_id
                    left join product_uom as pu on pu.id = sm.product_uom
                    where sm.picking_id = %s
                    and sm.state <> 'cancel'
                    order by pp.default_code""", (ids))
        invoice_line = cr.fetchall()
        invoice_line=invoice_line[:]
        detail = ""
        n_line = 0
        n_page = 1
        for line in invoice_line:
            if line:
                ubication_id = line[1] 
                location_id = line[2]
                default_code = self.limit_text(line[3],18)
                name_template = self.limit_text(line[4],40)
                categ_id = "  "+self.limit_text(line[5],10)+" "
                product_uom = line[6]
                if product_uom == 'PCE':
                    product_uom = 'Unidad(es)'
                elif product_uom == 'Meters':
                    product_uom = 'Metros'
                else:
                    product_uom = product_uom
                product_uom = self.limit_text(product_uom,10)
                product_qty = self.limit_text(("{:,.2f}".format(line[7])).rjust(10),10)
                n_line = n_line + 1
                new_detail = "\n%s" % (self.limit_text(default_code+name_template+product_qty+' '+product_uom,SIZE_LINE))
            if n_page == 1:
                if (MAX_LINES - 14 - n_line ) == 0:
                    n_page = n_page + 1
                    new_detail ="\f\n                                                                      Página #%s\n%s"%(n_page,header_report)                    
                    n_line = 0
            else:
                if (MAX_LINES - n_line - 5 ) == 0:
                    n_page = n_page + 1
                    new_detail ="\f\n                                                                      Página #%s\n%s"%(n_page,header_report)            
            detail += new_detail
        footer_0 = " TOTAL : " + str(len(invoice_line)) + " ARTÍCULOS" 
        footer_1 = " ________________________" +"  "+" ________________________"+"  "+"_______________________" 
        footer_2 = "       Recibido por      " +"  "+"       Despachado por    "+"  "+"    Supervisado por    "
        footer_3 = "Nombre:                  " 
        footer_4 = "Ident.:                  " 

        footer = "\n\n\n%s\n\n\n%s\n%s\n%s\n%s"%(footer_0,footer_1,footer_2,footer_3,footer_4)        
        text = header+"\n"+header_report+ detail + footer
        return (text.encode('utf8'), output_type)


    def get_customer_transfer(self,cr,uid,ids,output_type,proxy_argument,context=None):        
        cr.execute("""
                select 
                rc.name as company_id,
                rp.name as partner_id,
                rp.vat as vat,
                rpa.street as street,
                cc.name as city,
                rcs.name as state_id,
                rco.name as country_id,
                ss.name as shop_id,
                sp.date as date,
                dc.name as carrier_id,
                ai.number as number,
                rpa.phone as phone,
                sp.name as picking,
                ai.automatic,
                ai.pre_printer,
                ruv.login,
                ruc.login,
                to_char(sa.start_date,'dd/MM/yyyy'),
                to_char(sa.expiration_date,'dd/MM/yyyy'),
                rc.resolution_sri,
                to_char(rc.date_resolution,'dd/MM/yyyy')            
                from account_invoice as ai
                left join stock_picking as sp on sp.id = ai.picking_id
                left join res_partner as rp on rp.id = ai.partner_id
                left join res_partner_address as rpa on rpa.partner_id = rp.id
                left join city_city as cc on cc.id = rpa.location_id
                left join res_country_state as rcs on rcs.id = cc.state_id
                left join res_country as rco on rco.id = rcs.country_id 
                left join sale_shop ss on ss.id = ai.shop_id
                left join res_company rc on rc.id = ai.company_id
                left join delivery_carrier dc on dc.id = sp.carrier_id
                left join res_users ruv on ruv.id = ai.salesman_id
                left join res_users ruc on ruc.id = ai.user_id
                left join sri_authorization sa on sa.id = ai.authorization_sales
                left join sri_authorization_line srl on srl.authorization_id=sa.id
                where ai.id = %s""", (ids))
        invoice = cr.fetchall()
        invoice=invoice[:]
        if invoice[0][13]:
            automatic = True
            pre_printer = False
            sri_resolution1 = "        CONTRIBUYENTE ESPECIAL "
            sri_resolution2 = "RESOLUCION #"+invoice[0][19]+" DEL "+invoice[0][20]
        else:
            pre_printer = True
            automatic = False
        
        company_id = invoice[0][0]
        partner_id = invoice[0][1]
        vat = invoice[0][2]
        street = invoice[0][3]
        if len(street):
            street1=street[0:25]
            street2=street[25:60]
        city = invoice[0][4]
        state_id = invoice[0][5]
        country_id = invoice[0][6]
        shop_id = invoice[0][7]
        if shop_id:
            cr.execute("""select street from res_partner_address where id = (select partner_address_id from sale_shop where name =%s)""",(shop_id,))
            address_id = cr.fetchall()
            if address_id:
                address_id= address_id[0][0]
            shop_id = shop_id
        date = invoice[0][8]
        if date:
            date = date[8:10]+'-'+date[5:7]+'-'+date[0:4]
        now = time.strftime('%d-%m-%Y')
        carrier_id = invoice[0][9]
        number = invoice[0][10]
        phone = invoice[0][11]
        if phone:
            phone = phone
        else:
            phone = " "
        if invoice[0][12]:
            picking = invoice[0][12]
        else:
            picking = ' '
        
        cr.execute("""select login from res_users where id =%s""",(uid,))
        users= cr.fetchall()
        usuario = users[0][0]
        LEFT_SPACE = " "
        if pre_printer:
            SIZE_LINE = 80
            MAX_LINES = 60
            a = self.limit_text(company_id + LEFT_SPACE*7 + 'Impreso el:' +now + LEFT_SPACE*2 + 'por:' + usuario, SIZE_LINE) 
            b = self.limit_text(LEFT_SPACE*20+'ORDEN DE ENTREGA # '+picking, SIZE_LINE) #PICKING
            c = self.limit_text(('FACTURA       : '+number), SIZE_LINE)
            d = self.limit_text(('TIENDA        : '+shop_id), SIZE_LINE)
            e = self.limit_text(('CLIENTE       : '+partner_id ), SIZE_LINE)
            f = self.limit_text(('DIRECCION     : '+street), SIZE_LINE)
            g = self.limit_text(('CIUDAD        : '+city+' - '+ state_id+' - '+country_id), SIZE_LINE) 
            h = self.limit_text(('IDENTIFICACION: '+vat +LEFT_SPACE*20+'TELEFONO     : '+phone), SIZE_LINE)
            i = self.limit_text(('FECHA         : '+date[:10] +LEFT_SPACE*20+'TRANSPORTISTA: '+carrier_id), SIZE_LINE)
            j = "---------------------------------------------------------------------------------"
            k = "         PRODUCTO                                                  CANTIDAD      "
            l = "---------------------------------------------------------------------------------"
            header = "\n%s\n\n%s\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n" % (a,b,c,d,e,f,g,h,i)
            header_report = "\n%s\n%s\n%s" % (j,k,l)
            cr.execute("""
                        select 
                        sm.id,
                        u.name as ubication_id,
                        sl.name as location_id,
                        pp.default_code as default_code,
                        pp.name_template as name_template,
                        pc.name as categ_id,
                        pu.name as product_uom,
                        sm.product_qty as product_qty,
                        sm.picking_id as picking_id
                        from stock_move as sm
                        left join product_product as pp on pp.id = sm.product_id
                        left join product_template as pt on pt.id = pp.product_tmpl_id
                        left join product_category as pc on pc.id = pt.categ_id
                        left join ubication as u on u.id = sm.ubication_id
                        left join stock_location as sl on sl.id = sm.location_id
                        left join product_uom as pu on pu.id = sm.product_uom
                        left join account_invoice as ai on ai.picking_id = sm.picking_id
                        where ai.picking_id = sm.picking_id
                        and ai.id  = %s
                        order by pp.default_code""", (ids))
            invoice_line = cr.fetchall()
            invoice_line=invoice_line[:]
            detail = ""
            n_line = 0
            n_page = 1
            for line in invoice_line:
                if line:
                    default_code = self.limit_text(line[3],18)
                    name_template = self.limit_text(line[4],40)
                    product_uom = line[6]
                    if product_uom == 'PCE':
                        product_uom = 'Unidad(es)'
                    elif product_uom == 'Meters':
                        product_uom = 'Metros'
                    else:
                        product_uom = product_uom
                    product_uom = self.limit_text(product_uom,10)
                    product_qty = self.limit_text(("{:,.2f}".format(line[7])).rjust(10),10)
                    n_line = n_line + 1
                    new_detail = "\n%s" % (self.limit_text(default_code+name_template+product_qty+' '+product_uom,SIZE_LINE))
                if n_page == 1:
                    if (MAX_LINES - 14 - n_line ) == 0:
                        n_page = n_page + 1
                        new_detail ="\f\n                                                                      Página #%s\n%s"%(n_page,header_report)                    
                        n_line = 0
                else:
                    if (MAX_LINES - n_line - 5 ) == 0:
                        n_page = n_page + 1
                        new_detail ="\f\n                                                                      Página #%s\n%s"%(n_page,header_report)            
                detail += new_detail
            footer_0 = " TOTAL : " + str(len(invoice_line)) + " ARTÍCULOS" 
            footer_1 = " ________________________" +"  "+" ________________________"+"  "+"_______________________" 
            footer_2 = "       Recibido por      " +"  "+"       Enviado por       "+"  "+"    Supervisado por    "
            footer_3 = "Nombre:                  " 
            footer_4 = "Ident.:                  " 
    
            footer = "\n\n\n%s\n\n\n%s\n%s\n%s\n%s"%(footer_0,footer_1,footer_2,footer_3,footer_4)        
            text = header+"\n"+header_report+ detail + footer
            return (text.encode('utf8'), output_type)

        elif automatic:
            SIZE_LINE = 40
            SIZE_COLUMN_DISTANT = 5
            SIZE_CODE = 12
            EACH_LINE = 2
            SIZE_INDENTATION_HEADER = 3
            INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
            streetf = self.limit_text(('DIRECCION : '+street1), SIZE_LINE)+"\n"+self.limit_text((street2), SIZE_LINE)
            a = self.limit_text(company_id,SIZE_LINE) 
            b = self.limit_text('ORDEN DE ENTREGA # '+picking, SIZE_LINE) #PICKING
            c = self.limit_text(('FACTURA   : '+number), SIZE_LINE)
            d = self.limit_text(('TIENDA    : '+shop_id), SIZE_LINE)
            e = self.limit_text(('CLIENTE   : '+partner_id ), SIZE_LINE)
            f = streetf
            g = self.limit_text(('CIUDAD    : '+city+' - '+ state_id+' - '+country_id), SIZE_LINE) 
            h = self.limit_text(('IDENTIF   : '+vat), SIZE_LINE)
            i = self.limit_text(('TELEFONO  : '+phone), SIZE_LINE)
            j = self.limit_text(('FECHA     : '+date[:10]), SIZE_LINE)
            k = self.limit_text(('TRANSPORTE: '+carrier_id), SIZE_LINE)
            l = "----------------------------------------"
            m = "  PRODUCTO                   CANTIDAD   "
            n = "----------------------------------------"
            header = "\n%s\n\n%s\n\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n" % (a,b,c,d,e,f,g,h,i,j,k,)
            header_report = "\n%s\n%s\n%s\n" % (l,m,n)
            cr.execute("""
                        select 
                        sm.id,
                        u.name as ubication_id,
                        sl.name as location_id,
                        pp.default_code as default_code,
                        pp.name_template as name_template,
                        pc.name as categ_id,
                        pu.name as product_uom,
                        sm.product_qty as product_qty,
                        sm.picking_id as picking_id
                        from stock_move as sm
                        left join product_product as pp on pp.id = sm.product_id
                        left join product_template as pt on pt.id = pp.product_tmpl_id
                        left join product_category as pc on pc.id = pt.categ_id
                        left join ubication as u on u.id = sm.ubication_id
                        left join stock_location as sl on sl.id = sm.location_id
                        left join product_uom as pu on pu.id = sm.product_uom
                        left join account_invoice as ai on ai.picking_id = sm.picking_id
                        where ai.picking_id = sm.picking_id
                        and ai.id  = %s
                        order by pp.default_code""", (ids))
            invoice_line = cr.fetchall()
            invoice_line=invoice_line[:]
            detail = ""
            n_line = 0
            n_page = 1
            for line in invoice_line:
                if line:
                    default_code = self.limit_text(line[3],18)
                    name_template = self.limit_text(line[4],40)
                    product_uom = line[6]
                    if product_uom == 'PCE':
                        product_uom = 'Unidad(es)'
                    elif product_uom == 'Meters':
                        product_uom = 'Metros'
                    else:
                        product_uom = product_uom
                    product_uom = self.limit_text(product_uom,10)
                    product_qty = self.limit_text(("{:,.2f}".format(line[7])).rjust(10),10)
                    new_detail = "\n%s" % (self.limit_text(name_template,SIZE_LINE)+"\n"+self.limit_text(default_code+product_qty+' '+product_uom,SIZE_LINE))
                detail += new_detail
            footer_0 = " TOTAL : " + str(len(invoice_line)) + " ARTÍCULOS" 
            footer_1 = "_________________________" 
            footer_2 = "       Recibido por      "
            footer_3 = "Nombre:                  " 
            footer_4 = "Ident.:                  " 
            footer_5 = "_________________________"
            footer_6 = "      Enviado por        "
            footer_7 = "_________________________"
            footer_8 = "    Supervisado por      "
            footer = "\n\n\n%s\n\n\n%s\n%s\n%s\n%s\n\n\n%s\n%s\n\n\n%s\n%s"%(footer_0,footer_1,footer_2,footer_3,footer_4,footer_5,footer_6,footer_7,footer_8)        
            text = header+"\n"+header_report+ detail + footer
            return (text.encode('utf8'), output_type)


    def get_picking(self,cr,uid,ids,output_type,proxy_argument,context=None):        
        cr.execute("""
                select 
                rc.name as company_id,
                sp.name,
                sp.state,
                ss1.name as shop_id,
                ss2.name as shop_dest,
                ru1.name as digiter_id,
                ru2.name as warehouse_id,
                sp.date as date,
                dc.name as carrier_id,
                rp.name as partner_id,
                cc.name as address_id,
                rcs.name as state_id
                from stock_picking as sp
                left join stock_location as sl1 on sl1.id = sp.location_id
                left join stock_location as sl2 on sl2.id = sp.location_dest_id
                left join sale_shop ss1 on ss1.id = sp.shop_id
                left join sale_shop ss2 on ss2.id = sp.shop_id_dest
                left join res_company rc on rc.id = sp.company_id
                left join res_users ru1 on ru1.id = sp.digiter_id
                left join res_users ru2 on ru2.id= sp.warehouse_id
                left join delivery_carrier dc on dc.id = sp.carrier_id
                left join res_partner rp on rp.id = sp.partner_id
                left join res_partner_address rpa on rpa.partner_id = sp.partner_id
                left join city_city cc on cc.id = rpa.location_id
                left join res_country_state rcs on rcs.id = cc.state_id
                where sp.id = %s""", (ids))
        invoice = cr.fetchall()
        invoice=invoice[:]
        company_id = invoice[0][0]
        picking = invoice[0][1]
        state = invoice[0][2]
        if state=='draft':
            state = 'Borrador'
        elif state == 'confirmed':
            state = 'En Ejecucción'
        elif state == 'done':
            state = 'Realizado'
        elif state == 'cancel':
            state = 'Anulado'
        else:
            state = 'Sin Estado'
        shop_id = invoice[0][3]
        if shop_id:
            cr.execute("""select street from res_partner_address where id = (select partner_address_id from sale_shop where name =%s)""",(shop_id,))
            address_id = cr.fetchall()
            if address_id:
                address_id= address_id[0][0]
            shop_id = shop_id + ' - '+ address_id
        shop_dest = invoice[0][4]
        if shop_dest:
            cr.execute("""select street from res_partner_address where id = (select partner_address_id from sale_shop where name =%s)""",(shop_dest,))
            address_id_dest = cr.fetchall()
            if address_id_dest:
                address_id_dest = address_id_dest[0][0]
            shop_dest = shop_dest + ' - '+ address_id_dest
        digiter_id = invoice[0][5]
        warehouse_id = invoice[0][6]
        if not digiter_id: 
            digiter_id = " "
        if not warehouse_id:
            warehouse_id = " "
        date_local = invoice[0][7]
        if uid:
            tz_id = self.pool.get('res.users').browse(cr,uid,uid).context_tz
            if tz_id:
                tz_id = tz_id
            else:
                tz_id = 'America/Guayaquil'
        local = timezone(tz_id)
        if date_local:
            date_local = datetime.datetime.strptime (date_local, "%Y-%m-%d %H:%M:%S")
            date_local = (local.localize(date_local)).strftime("%d-%m-%Y %H:%M")
                         
        carrier_id = invoice[0][8] or " "
        partner_id = invoice[0][9] or " "
        city = invoice[0][10]
        state_id = invoice[0][11]
        if city and state_id:
            city_id = city + ' - '+state_id
        else:
            city_id = " " 
        
        cr.execute("""select login from res_users where id =%s""",(uid,))
        users= cr.fetchall()
        usuario = users[0][0]
        SIZE_INDENTATION_HEADER = 3
        LEFT_SPACE = " "
        SIZE_LINE = 80
        MAX_LINES = 60
        INDENTATION_HEADER = " "*SIZE_INDENTATION_HEADER
        a = self.limit_text(LEFT_SPACE*5+'PICKINGLIST # '+picking, SIZE_LINE) #PICKING  
        b = self.limit_text(('CLIENTE   : '+partner_id ), SIZE_LINE)
        c = self.limit_text(('DIRECCION : '+shop_dest), SIZE_LINE)
        d = self.limit_text(('CIUDAD    : '+city_id), SIZE_LINE) 
        e = self.limit_text(('FECHA     : '+date_local), SIZE_LINE) 
        f = self.limit_text(('TRANSPORTE: '+carrier_id), SIZE_LINE)
        h = "-------------------------------------------------------------------------------"
        i = "UBICACION            PRODUCTO                      PEDIDO          DESPACHADO  "
        j = "-------------------------------------------------------------------------------"
        header = "\n%s\n%s\n%s\n%s\n%s\n%s\n" % (a,b,c,d,e,f)
        header_report = "\n%s\n%s\n%s" % (h,i,j)
        cr.execute("""
                    select 
                    sm.id,
                    u.name as ubication_id,
                    sl.name as location_id,
                    pp.default_code as default_code,
                    pp.name_template as name_template,
                    pc.name as categ_id,
                    pu.name as product_uom,
                    sm.product_qty as product_qty,
                    picking_id as picking_id
                    from stock_move as sm
                    left join product_product as pp on pp.id = sm.product_id
                    left join product_template as pt on pt.id = pp.product_tmpl_id
                    left join product_category as pc on pc.id = pt.categ_id
                    left join ubication as u on u.id = sm.ubication_id
                    left join stock_location as sl on sl.id = sm.location_id
                    left join product_uom as pu on pu.id = sm.product_uom
                    where sm.picking_id = %s
                    and sm.state != 'cancel'
                    order by u.name, pp.default_code""", (ids))
        invoice_line = cr.fetchall()
        invoice_line=invoice_line[:]
        detail = ""
        n_line = 0
        n_page = 1
        for line in invoice_line:
            if line:
                ubication_id = self.limit_text(line[1],10) 
                location_id = line[2]
                default_code = self.limit_text(line[3] +' -' + line[4] ,40)
                categ_id = "  "+self.limit_text(line[5],8)+" "
                product_uom = line[6]
                if product_uom == 'PCE':
                    product_uom = 'Unidad(es)'
                elif product_uom == 'Meters':
                    product_uom = 'Metros'
                else:
                    product_uom = product_uom
                product_uom = self.limit_text(product_uom,4)
                product_qty = self.limit_text(("{:,.2f}".format(line[7])).rjust(12),12)
                n_line = n_line + 1
                new_detail = "\n%s" % (self.limit_text(ubication_id+" "+default_code+" "+ product_qty+" "+ product_uom+' _________',SIZE_LINE))
            if n_page == 1:
                if (MAX_LINES - 14 - n_line ) == 0:
                    n_page = n_page + 1
                    new_detail ="\f\n                 Página #%s\n%s"%(n_page,header_report)                    
                    n_line = 0
            else:
                if (MAX_LINES - n_line - 5 ) == 0:
                    n_page = n_page + 1
                    new_detail ="\f\n                 Página #%s\n%s"%(n_page,header_report)            
            detail += new_detail
        footer_0 = " TOTAL : " + str(len(invoice_line)) + " ARTÍCULOS" 
        footer_1 = "Despachado por:" + warehouse_id 
        footer_2 = "Fecha Entrega:___________" 

        footer = "\n\n\n%s\n\n%s\n%s\n"%(footer_0,footer_1,footer_2)        
        text = header+"\n"+header_report+ detail + footer
        return (text.encode('utf8'), output_type)

    def execute_report(self):
        proxy_url, proxy_argument = get_proxy_args(self.cr, self.uid, self.prpt_content)
        proxy = xmlrpclib.ServerProxy(proxy_url)
        proxy_parameter_info = proxy.report.getParameterInfo(proxy_argument)

        output_type = self.data and self.data.get('output_type', False) or self.default_output_type or DEFAULT_OUTPUT_TYPE

        proxy_argument.update({
                               'output_type': output_type,
                               'report_parameters': dict([(param_name, param_formula(self)) for (param_name, param_formula) in RESERVED_PARAMS.iteritems() if param_formula(self)]),
                               })

        # Agregado para compatibilidad con otros reportes que requieren impresoras de texto directas.
        modules_search = self.pool.get('ir.module.module')
        
#        invoice_txt = modules_search.search(self.cr,self.uid,[('name','=','straconx_bh'),('state','=','installed')]) 
        invoice_txt_tf = modules_search.search(self.cr,self.uid,[('name','=','straconx_tf_data'),('state','=','installed')])
        
        if self.model_data=='account.invoice' and output_type == 'txt' and self.report_name == 'invoice_report_pos_id':
            return self.get_invoice_credit_txt(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='account.invoice' and output_type == 'txt' and self.report_name == 'invoice_report_pos_id':
            return self.get_invoice_credit_txt(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='stock.picking' and output_type == 'txt' and self.report_name == 'picking_txt':
            return self.get_picking(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='account.invoice' and output_type == 'txt' and self.report_name == 'orden_customer':
            return self.get_customer_transfer(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='stock.picking' and output_type == 'txt' and self.report_name == 'internal_transfer':
            return self.get_internal_transfer(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='account.invoice' and output_type == 'txt' and self.report_name == 'delivery_guide_invoiced_pos':
            return self.get_delivery_txt(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='stock.delivery' and output_type == 'txt' and self.report_name == 'delivery_guide_txt':
            report_ids = proxy_argument['report_parameters']["ids"]
            ids = self.pool.get('stock.delivery').browse(self.cr,self.uid,report_ids)
            for idl in ids:
                return self.get_delivery_txt(self.cr, self.uid,[idl.invoice_id.id],output_type,proxy_argument)
        elif self.model_data=='account.invoice' and output_type == 'txt' and self.report_name == 'nota_de_credito_pos':
            return self.get_credit_note_txt(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='account.voucher' and output_type == 'txt' and self.report_name == 'cheque_proveedor':
            return self.get_print_cheques(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='account.invoice' and output_type == 'txt':
            return self.get_invoice_txt(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif self.model_data=='account.bank.statement' and output_type == 'txt':
            return self.get_print_statement(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        if invoice_txt_tf and self.model_data=='account.invoice' and output_type == 'txt':
            return self.get_invoice_txt_tf(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        elif invoice_txt_tf and self.model_data=='account.bank.statement' and output_type == 'txt':
            return self.get_print_statement(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)
        
        label = modules_search.search(self.cr,self.uid,[('name','=','straconx_labels'),('state','=','installed')])
        if label and self.model_data=='label.wizard.product' and output_type == 'txt':
            return self.get_labels_txt(self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument)

        if self.data and self.data.get('variables', False):
            proxy_argument['report_parameters'].update(self.data['variables'])
            for parameter in proxy_parameter_info:
                if parameter['name'] in proxy_argument['report_parameters'].keys():
                    value_type = parameter['value_type']
                    java_list, value_type = check_java_list(value_type)
                    if not value_type == 'java.lang.Object' and PARAM_VALUES[JAVA_MAPPING[value_type](parameter['attributes'].get('data-format', False))].get('convert', False):
                        # convert from string types to correct types for reporter
                        proxy_argument['report_parameters'][parameter['name']] = PARAM_VALUES[JAVA_MAPPING[value_type](parameter['attributes'].get('data-format', False))]['convert'](proxy_argument['report_parameters'][parameter['name']])
                    # turn in to list
                    if java_list:
                        proxy_argument['report_parameters'][parameter['name']] = [proxy_argument['report_parameters'][parameter['name']]]

        rendered_report = proxy.report.execute(proxy_argument).data
        if len(rendered_report) == 0:
            raise osv.except_osv(_('Error'), _("Pentaho returned no data for the report '%s'. Check report definition and parameters.") % self.name[7:])
        return (rendered_report, output_type)


class PentahoReportOpenERPInterface(report.interface.report_int):

    def __init__(self, name):
        if name in netsvc.Service._services:
            del netsvc.Service._services[name]
        super(PentahoReportOpenERPInterface, self).__init__(name)

    def create(self, cr, uid, ids, data, context):
        name = self.name
        report_instance = Report(name, cr, uid, ids, data, context)

        pool = pooler.get_pool(cr.dbname)
        ir_pool = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_pool.search(cr, uid,
                [('report_name', '=', name[7:])], context=context)

        rendered_report, output_type = report_instance.execute()
        if report_xml_ids:
            report_xml = ir_pool.browse(cr, uid, report_xml_ids[0], context=context)
            model = context.get('active_model')
            if report_xml.attachment and model:
                crtemp = pooler.get_db(cr.dbname).cursor()  # Creating new cursor to prevent TransactionRollbackError
                                                            # when creating attachments, concurrency update have place otherwise
                self.create_attachment(crtemp, uid, ids, report_xml.attachment, rendered_report, output_type, model, context=context)

                # TODO: Will remodel bellow functionality as its causes a lot of bugs, it returns previous filename
                # Error in report registration

                # service_name = check_report_name(report_name)
                # if check_report_name(report_name) != self.name:
                    # Changing report stored filename

                    # report_xml = ir_pool.browse(crtemp, uid, report_xml_ids[0], context=context)
                    # report_xml.write({'report_name': report_name})
                    # change_service_name(self.name, service_name)
                    # self.name = service_name

                crtemp.commit()  # It means attachment will be created even if error occurs
                crtemp.close()
        return rendered_report, output_type

    def getObjects(self, cr, uid, ids, model, context):
        pool = pooler.get_pool(cr.dbname)
        return pool.get(model).browse(cr, uid, ids, list_class=browse_record_list, context=context, fields_process=_fields_process)

    def create_attachment(self, cr, uid, ids, attachment, rendered_report, output_type, model, context):
        """Generates attachment when report is called and links to object it is called from
        Returns: True """
        objs = self.getObjects(cr, uid, ids, model, context)
        pool = pooler.get_pool(cr.dbname)
        attachment_pool = pool.get('ir.attachment')
        for obj in objs:
            attachment_ids = attachment_pool.search(cr, uid, [('res_id', '=', obj.id), ('res_model', '=', model)], context=context)
            aname = eval(attachment, {'object': obj, 'version': str(len(attachment_ids)), 'time': time.strftime('%Y-%m-%d')})
            if aname:
                try:
                    name = '%s%s' % (aname, '' if aname.endswith(output_type) else '.' + output_type)
                    # Remove the default_type entry from the context: this
                    # is for instance used on the account.account_invoices
                    # and is thus not intended for the ir.attachment type
                    # field.
                    ctx = dict(context)
                    ctx.pop('default_type', None)
                    attachment_pool.create(cr, uid, {
                        'name': name,
                        'datas': base64.encodestring(rendered_report),
                        'datas_fname': name,
                        'res_model': model,
                        'res_name': aname,
                        'res_id': obj.id,
                        }, context={}
                    )
                except Exception:
                    #TODO: should probably raise a proper osv_except instead, shouldn't we? see LP bug #325632
                    _logger.error('Could not create saved report attachment', exc_info=True)
        return True


def check_report_name(report_name):
    """Adds 'report.' prefix to report name if not present already
    Returns: full report name
    """
    if not report_name.startswith(SERVICE_NAME_PREFIX):
        name = "%s%s" % (SERVICE_NAME_PREFIX, report_name)
    else:
        name = report_name
    return name


def change_service_name(old_name, new_name):
    """Deletes service with old name and register
    one with new name.
    """
    if old_name in netsvc.Service._services:
        del netsvc.Service._services[old_name]
    PentahoReportOpenERPInterface(new_name)


def register_pentaho_report(report_name):
    name = check_report_name(report_name)
    if name in netsvc.Service._services:
        del netsvc.Service._services[name]
    PentahoReportOpenERPInterface(name)


def fetch_report_parameters(cr, uid, report_name, context=None):
    """Return the parameters object for this report.

    Returns the parameters object as returned by the Pentaho
    server.

    @param report_name: The service name for the report.
    """
    name = check_report_name(report_name)
    return Report(name, cr, uid, [1], {}, context).fetch_report_parameters()


#Following OpenERP's (messed up) naming convention
class ir_actions_report_xml(osv.osv):
    _inherit = "ir.actions.report.xml"

    def register_all(self, cr):
        cr.execute("SELECT * FROM ir_act_report_xml WHERE is_pentaho_report = 'TRUE' ORDER BY id")
        records = cr.dictfetchall()
        for record in records:
            register_pentaho_report(record["report_name"])

        return super(ir_actions_report_xml, self).register_all(cr)

ir_actions_report_xml()
