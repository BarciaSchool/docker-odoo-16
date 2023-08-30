# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
#
##############################################################################

import base64
import gc
import platform
import sys
import time

import xmlrpclib
from tools.translate import _
from openerp.addons.pentaho_reports.java_oe import JAVA_MAPPING, check_java_list, PARAM_VALUES, RESERVED_PARAMS
from openerp.addons.pentaho_reports.core import Report, get_proxy_args, DEFAULT_OUTPUT_TYPE

import commands
from osv import osv, fields
from tools import config
import netsvc
import random
import os
import re


# def get_labels_txt(self,cr,uid,ids,output_type,proxy_argument,context=None):
#     wiz = self.pool.get('label.wizard.product').browse(cr,uid,ids)
#     wiz = wiz[0]
#     if wiz.line_ids:
#         for line in wiz.line_ids:
#             name = line.product_id.product_tmpl_id.name
#             default_code = line.product_id.default_code
#             p_net = round(line.product_id.p_net,2) or round(line.product_id.product_tmpl_id.list_price,2)
#             p_net = 'PVP %.2f' % (p_net)
#             company_name = self.pool.get('res.users').browse(cr,uid,uid).company_id.name[:20]
#             qty = line.quantity                                 
#             if wiz.template_id =='label_90x25':
#                 if len(name) > 25:
#                     name1 = name[:25]
#                     name2 = name[25:40]
#                 else:
#                     name1 = name
#                     name2 = "__________"
#                 qty = int(round(qty/3,0)) 
#                 text=("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD10^JUS^MD25^LRN^CI0^XZ^XA^MMT^PW719^LL0200^LS0^BY2,3,45^FT495,120^BCN,,Y,Y^FD%s^FS^BY2,3,45^FT245,120^BCN,,Y,Y^FD%s^FS^BY2,3,45^FT5,120^BCN,,Y,Y^FD%s^FS^FT507,34^A0N,28,28^FH\^FD%s^FS^FT267,34^A0N,28,28^FH\^FD%s^FS^FT27,34^A0N,28,28^FH\^FD%s^FS^FT495,137^A0N,14,14^FH\^FD%s^FS^FT495,156^A0N,14,14^FH\^FD%s^FS^FT252,137^A0N,14,14^FH\^FD%s^FS^FT252,156^A0N,14,14^FH\^FD%s^FS^FT15,137^A0N,14,14^FH\^FD%s^FS^FT145,156^A0N,14,14^FH\^FD%s^FS^FT550,176^A0N,11,12^FH\^FD%s^FS^FT300,176^A0N,11,12^FH\^FD%s^FS^FT30,176^A0N,11,12^FH\^FD%s^FS^PQ%s,0,1,Y^XZ""")% (default_code,default_code,default_code,p_net,p_net,p_net,name1,name2,name1,name2,name1,name2,company_name,company_name,company_name,qty)
#             elif wiz.template_id =='label_58x25dc':
#                 if len(name) > 25:
#                     name1 = name[:25]
#                     name2 = name[25:40]
#                 else:
#                     name1 = name
#                     name2 = "___________"                
#                 text = ("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD15^JUS^LRN^CI0^XZ^XA^MMT^PW448^LL0200^LS0^BY1,3,45^FT263,55^BCN,,Y,N^FD%s^FS^BY1,3,45^FT40,55^BCN,,Y,N^FD%s^FS^FT9,98^A0N,14,14^FH\^FD%s^FS^FT9,118^A0N,14,14^FH\^FD%s^FS^FT232,98^A0N,14,14^FH\^FD%s^FS^FT232,118^A0N,14,14^FH\^FD%s^FS^FT9,149^A0N,28,28^FH\^FD%s^FS^FT232,149^A0N,28,28^FH\^FD%s^FS^FT10,165^A0N,11,12^FH\^FD%sFS^FT242,165^A0N,11,12^FH\^FD%s^FS^PQ%s,0,1,Y^XZ""")% (default_code,default_code,name1,name2,name1,name2,p_net,p_net,company_name,company_name,qty)
#                 print text
#             elif wiz.template_id =='label_56x25an':
#                 if len(name) > 45:
#                     name1 = name[:45]
#                 else:
#                     name1 = name                
#                     text = ("""^CT~~CD,~CC^~CT~^XA~TA000~JSN^LT0^MNW^MTT^PON^PMN^LH0,0^JMA^PR2,2~SD15^JUS^LRN^CI0^XZ^XA^MMC^PW448^LL0200^LS0^BY2,3,68^FT72,79^BCN,,Y,N^FD%s^FS^FT17,120^A0N,25,16^FH\^FD%s^FS^FT150,180^A0N,11,12^FH\^FD%s^FS^FT259,157^A0N,28,28^FH\^FD%s^FS^PQ%s,1,1,Y^XZ""")% (default_code,name1,company_name,p_net,qty)                    
#             else:
#                 raise osv.except_osv(_('Error'), _("Pentaho returned no data for the report '%s'. Check report definition and parameters.") % self.name[7:])                
#     return (text.encode('utf8'), output_type)
# 
# def execute_report_labels(self):
#     proxy_url, proxy_argument = get_proxy_args(self.cr, self.uid, self.prpt_content)
#     proxy = xmlrpclib.ServerProxy(proxy_url)
#     proxy_parameter_info = proxy.report.getParameterInfo(proxy_argument)
#     output_type = self.data and self.data.get('output_type', False) or self.default_output_type or DEFAULT_OUTPUT_TYPE
#     flag = (output_type == "txt")
#     proxy_argument.update({
#                                'output_type' : output_type,
#                                'report_parameters' : dict([(param_name, param_formula(self)) for (param_name, param_formula) in RESERVED_PARAMS.iteritems() if param_formula(self)]),
#                                })
#     if(flag):
#         return get_labels_txt(self,self.cr, self.uid,proxy_argument['report_parameters']["ids"],output_type,proxy_argument,context=self.context)
#     else:
#         rendered_report = proxy.report.execute(proxy_argument).data        
#         if self.data and self.data.get('variables', False):
#             proxy_argument['report_parameters'].update(self.data['variables'])
#             for parameter in proxy_parameter_info:
#                 if parameter['name'] in proxy_argument['report_parameters'].keys():
#                     value_type = parameter['value_type']
#                     java_list, value_type = check_java_list(value_type)
#                     if not value_type == 'java.lang.Object' and PARAM_VALUES[JAVA_MAPPING[value_type](parameter['attributes'].get('data-format', False))].get('convert', False):
#                             # convert from string types to correct types for reporter
#                         proxy_argument['report_parameters'][parameter['name']] = PARAM_VALUES[JAVA_MAPPING[value_type](parameter['attributes'].get('data-format', False))]['convert'](proxy_argument['report_parameters'][parameter['name']])
#                         # turn in to list
#                     if java_list:
#                         proxy_argument['report_parameters'][parameter['name']] = [proxy_argument['report_parameters'][parameter['name']]]
#         parameters=proxy_argument.get('report_parameters',{})
#         parameters.update({'login':self.pool.get("res.users").browse(self.cr,self.uid,self.uid).login})
#         proxy_argument['report_parameters']=parameters        
#         if len(rendered_report) == 0:
#             raise osv.except_osv(_('Error'), _("Pentaho returned no data for the report '%s'. Check report definition and parameters.") % self.name[7:])
#         return (rendered_report, output_type)

#Report.execute_report = execute_report_labels

class label_wizard_template(osv.osv):
    _name = 'label.wizard.template'

    _columns = {
                'name': fields.char('Name',size=20),                
                }                
                
label_wizard_template()

class label_wizard_product(osv.osv_memory):
    _name = 'label.wizard.product'

    _columns = {
        'printer_id':fields.selection([('ZebraZM400','Zebra ZM-400'),
                                         ('ZebraGC420','Zebra GC420'),
                                         ('ZebraTLP-2488','Zebra TLP-2488')],'Printer',required=True),    
        'template_id': fields.selection([('label_90x25','Etiqueta 9.00cmx2.50cm (productos con código númerico)'),
                                         ('label_58x25dc','Etiqueta 5.60cmx2.50cm (productos con doble cara) '),
                                         ('label_56x25an','Etiqueta 5.60cmx2.50cm (productos con código alfanúmerico)'),
                                         ('label_90x25_offer_image','Etiqueta 9.00cmx2.50cm (etiqueta pequeña con logo)'),
                                         ('label_90x25_offer_discount','Etiqueta 9.00cmx2.50cm (etiqueta pequeña con descuento y logo)'),
                                         ('label_58x25_offer_image','Etiqueta 4.00cmx5.00cm (etiqueta grande con logo)'),
                                         ('label_58x25_offer_discount','Etiqueta 4.00cmx5.00cm (etiqueta grande con descuento y logo)'),
                                         ],'Label Template',required=True),
        'line_ids': fields.one2many('label.wizard.product.line', 'wizard_id','Items'),
    }
                      
    _defaults = {
        'template_id': lambda *a: 'label_90x25',
    }
                      
                      
label_wizard_product()

class label_wizard_product_line(osv.osv_memory):
    _name = 'label.wizard.product.line'

    _columns = {
        'wizard_id': fields.many2one('label.wizard.product', 'Wizard',
            required=True),
        'product_id' : fields.many2one('product.product', 'Product',
            required=True),
        'quantity': fields.integer('Qty'),

    }

    _defaults = {
        'quantity': lambda *a: 1,
    }

label_wizard_product_line()
