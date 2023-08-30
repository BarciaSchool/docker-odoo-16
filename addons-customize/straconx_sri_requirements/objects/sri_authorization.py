# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv
from tools.translate import _
import time
import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
import base64


class sri_type_transaction(osv.osv):
    
    _name = 'sri.type.transaction' 
    
    _columns = {
                'code':fields.char('code', size=2, required=True,),
                'name':fields.char('name', size=128, required=True),
                'required_auth_old':fields.boolean('required auth old', required=False),
                'type':fields.selection([
                    ('auto_printer','Auto Impresor'),
                    ('document_electronic','Documento Electrónico'),
                    ],'type', select=True, required=True),
                'electronic_type':fields.selection([
                    ('1','Producción'),
                    ('2','Prueba'),
                    ],'type', select=True),
                'emision_type':fields.selection([
                    ('1','Emisión Normal'),
                    ('2','Emisión por Indisponibilidad del Sistema'),
                    ],'type', select=True),                
                }
sri_type_transaction()