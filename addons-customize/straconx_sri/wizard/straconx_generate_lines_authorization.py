# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A  
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import fields,osv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from tools.translate import _

class sri_generate_lines(osv.osv_memory):
            
    _name = 'sri.generate.lines.authorization'

    _columns = {
            'company_id':fields.many2one('res.company', 'Company', required=False),
            'name':fields.many2one('sri.authorization','Authorization',required=True),
            'printer_point_ids': fields.many2many('printer.point','generate_sri_lines_printer_auth', 'wizard_id', 'printer_id', 'Puntos de Impresión'),
            'journal_ids': fields.many2many('account.journal.type','generate_sri_lines_journal_auth','wizard_id', 'journal_id', 'Documentos'),
    }
        
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        objs = self.pool.get(context['active_model']).browse(cr , uid, context['active_ids'])
        res ={}
        if 'value' not in context.keys():
            for obj in objs:
                res['name']=obj.id
                res['company_id']= obj.company_id.id
        return res       
    
    
    def create_authorization(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        printer_obj = self.pool.get('printer.point')
        doc_obj = self.pool.get('account.journal.type')
        sri_line_obj = self.pool.get('sri.authorization.line')
        sri_obj = self.pool.get('sri.authorization')
        doc_ids = []
        for w in self.browse(cr, uid, ids, context):
            if not w.name:
                raise osv.except_osv('Error!', _('Necesita ingresar la autorización para continuar'))
            if not w.company_id:
                raise osv.except_osv('Error!', _('Seleccione la compañía que se le otorgo la autorización'))
            if not w.printer_point_ids:
                raise osv.except_osv('Error!', _('Seleccione por lo menos un punto de emisión e impresión para continuar'))
            if not w.journal_ids:
                raise osv.except_osv('Error!', _('Seleccione por lo menos un tipo de documento para la autorización'))
            else:
                if w.printer_point_ids and w.journal_ids and w.name:
                    for printer_id in w.printer_point_ids:
                        for doc in w.journal_ids:
                            old_auth = sri_line_obj.search(cr,uid,[('printer_id','=',printer_id.id),('name','=',doc.code),('state','=',True)])
                            if not old_auth: 
                                starting_number = 1
                                vals = {'name': doc.code,
                                        'auto_printer':True, 
                                        'authorization_id':w.name.id,
                                        'ending_number':starting_number,
                                        'shop_id':printer_id.shop_id.id,
                                        'pre_printer':False,
                                        'type_printer':'electronic',
                                        'expired':False,
                                        'printer_id':printer_id.id,
                                        'starting_number':starting_number,
                                        'number_next':starting_number,
                                        'counter':1,
                                        'range':1,
                                        'state':True
                                        }
                                        
                                if vals:
                                    sri_line_obj.create(cr,uid,vals)
                                    sri_obj.write(cr,uid,[w.name.id],{'auth_generate':True})
                            else:
                                old_auth_id = sri_line_obj.browse(cr,uid,old_auth[0])
                                vals = {'name': doc.code,
                                        'auto_printer':True, 
                                        'authorization_id':w.name.id,
                                        'ending_number':old_auth_id.ending_number+1,
                                        'shop_id':printer_id.shop_id.id,
                                        'pre_printer':False,
                                        'type_printer':'electronic',
                                        'expired':False,
                                        'printer_id':printer_id.id,
                                        'starting_number':old_auth_id.ending_number+1,
                                        'number_next':old_auth_id.ending_number+1,
                                        'counter':1,
                                        'range':1,
                                        'state':True
                                        }
                                        
                                if vals:
                                    sri_line_obj.write(cr,uid,[old_auth_id.id],{'expired':True,'state':False})
                                    sri_line_obj.create(cr,uid,vals)
                                    sri_obj.write(cr,uid,[w.name.id],{'auth_generate':True})
                                 
                                
                else:
                    raise osv.except_osv('Error!', _('No se han creado autorizaciones porque no existen puntos de impresión tipo autoimpresor creadas para el punto de emisión seleccionado'))
            
        return {'type': 'ir.actions.act_window_close'}
        
sri_generate_lines()