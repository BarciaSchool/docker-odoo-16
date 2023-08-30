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

import itertools

from osv import fields,osv
from osv.orm import except_orm
import tools
from tools.translate import _
from datetime import datetime
import time
# import nodes
import os,base64,urllib
import netsvc

class ir_attachment(osv.osv):


    def get_document_file(self,url):
        if not os.path.isfile(url):
            return False
        file=False        
        (filename, header) = urllib.urlretrieve(url)        
        with open(filename , 'rb') as f:
            file = base64.b64encode(f.read())
        return file

    def get_doc(self, cr, uid, ids, context=None):
        ext = context.get('type_file','.xml')
        fl=False
        pref = ''
        file = self.browse(cr, uid, ids, context=context)
        files_path = self.pool.get('res.users').browse(cr,uid,uid).company_id.files_path
        if file.type_model == '01':
            pref = 'FACT_'
        elif file.type_model == '04':
            pref = 'N_CRED_'
        elif file.type_model == '05':
            pref = 'N_DEBIT_'
        elif file.type_model == '06':
            pref = 'GR_'
        elif file.type_model == '07':
            pref = 'RET_'
        if not files_path:
            raise osv.except_osv(_("Error!"),_("Necesita configurar un directorio para los archivos de firma electrónica."))
        else:
            if not ext:
                ext = '.xml'
        try:
            url = files_path+'/'+pref+file.res_name+ext
            fl=self.get_document_file(url)
        except:
            return True
            #raise osv.except_osv(_("¡Error!"),_("Por favor revisar el documento, ya que no existe en el directorio predeterminado."))
        return fl

    def _get_document(self, cr, uid, ids, field_name, arg, context=None):
        if not context:
            context = {}
        res = {}
        if field_name=='ride_url':
            context.update({'type_file':'.pdf'})
        else:
            context.update({'type_file':'.xml'})
        for each in ids:
            res[each] = self.get_doc(cr, uid, each, context=context)
        return res

    _inherit = 'ir.attachment'
    _columns = {
        'datas_unsigned': fields.binary('Data Unsigned'),
        'datas_signed': fields.binary('Data Signed'),
        'sri_code': fields.selection([('01','FACTURA'),
                                      ('02','NOTA DE CRÉDITO'),
                                      ('03','NOTA DE DÉBITO'),
                                      ('04','GUIA DE REMISIÓN'),
                                      ('05','COMPROBANTE DE RETENCIÓN')],'Código'),
        'sign_state': fields.selection([('0','EMITIDO'),
                                      ('1','FIRMADO'),
                                      ('2','AUTORIZADO'),
                                      ('3','RECHAZADO'),
                                      ('4','NO AUTORIZADO')],
                                      'Estado Comprobante'),
        'number_auth':fields.char('Número de Autorización',size=50),
        'access_key': fields.char('Clave de acceso', size=50),
        'partner_id': fields.many2one('res.partner','Empresa'),
        'electronic': fields.boolean('Electronic'),
        'type_model': fields.selection([('01','FACTURA'),
                                      ('04','NOTA DE CRÉDITO'),
                                      ('05','NOTA DE DÉBITO'),
                                      ('06','GUIA DE REMISIÓN'),
                                      ('07','COMPROBANTE DE RETENCIÓN')],'Código SRI'),
        'sri_date': fields.char('SRI Date',size=50),
        'xmlbase_url': fields.function(_get_document, string='Archivo Base', type="binary", method=True),
        'signed_url': fields.function(_get_document,  string='Archivo Firmado', type="binary", method=True),
        'authorized_url':fields.function(_get_document, string='Archivo Autorizado', type="binary", method=True),
        'ride_url':fields.function(_get_document, string='Archivo RIDE', type="binary", method=True),
        'ride_name':fields.char('Filename',size=80),
    }

    def print_document(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        withhold_obj = self.pool.get('account.withhold')
        delivery_obj = self.pool.get('stock.delivery')
        debit_obj = self.pool.get('account.debit.note') 
        for data_id in self.browse(cr,uid,ids,context):
            res_id = data_id.res_id
            model = data_id.res_model
            type_model = data_id.type_model
            if model=='account.invoice' and res_id and type_model=='01':
                return invoice_obj.print_invoice_electronic_ride(cr,uid,[res_id],context)
            elif model=='account.invoice' and res_id and type_model=='04':
                return  invoice_obj.print_credit_notes_electronic(cr,uid,[res_id],context)
            elif model=='account.withhold' and res_id and type_model=='07':
                return withhold_obj.print_withhold_electronic(cr,uid,[res_id],context)
            elif model=='stock.delivery' and res_id and type_model=='06':
                return delivery_obj.print_delivery_electronic(cr,uid,[res_id],context)
            elif model=='account.invoice' and res_id and type_model=='05':
                return  invoice_obj.print_debit_note_electronic(cr,uid,[res_id],context)
            else:
                return True
        
    def send_partner_electronic(self, cr, uid, ids, context=None):

        return True                    
    
    def send_email_electronic(self, cr, uid, template_id, res_id, doc_id, context=None):
            
        tp_doc = context.get('tp_doc','FACT')
        values = {
                  'subject': False,
                  'body_text': False,
                  'body_html': False,
                  'email_from': False,
                  'email_to': False,
                  'email_cc': False,
                  'email_bcc': False,
                  'reply_to': False,
                  'auto_delete': False,
                  'model': False,
                  'res_id': False,
                  'mail_server_id': False,
                  'attachments': False,
                  'attachment_ids': False,
                  'message_id': False,
                  'state': 'outgoing',
                  'subtype': 'plain',
        }
        if not template_id:
            return values

        report_xml_pool = self.pool.get('ir.actions.report.xml')
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')
        email_template_obj = self.pool.get('email.template')
        template = email_template_obj.get_email_template(cr, uid, template_id, res_id, context)
        template_context = email_template_obj._prepare_render_template_context(cr, uid, template.model, res_id, context)

        for field in ['subject', 'body_text', 'body_html', 'email_from',
                      'email_to', 'email_cc', 'email_bcc', 'reply_to',
                      'message_id']:
            values[field] = email_template_obj.render_template(cr, uid, getattr(template, field),
                                                 template.model, res_id, context=template_context) \
                                                 or False

        if values['body_html']:
            values.update(subtype='html')

        if template.user_signature:
            signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
            values['body_text'] += '\n\n' + signature

        values.update(mail_server_id = template.mail_server_id.id,
                      auto_delete = template.auto_delete,
                      model=template.model,
                      res_id=res_id or False)

        attachments = {}
        # Add report as a Document
        if doc_id:
            doc_data_id = ir_attachment.browse(cr,uid,doc_id)
            attachments[doc_data_id.datas_fname] = doc_data_id.datas_signed
        if template.report_template:
            report_name = email_template_obj.render_template(cr, uid, template.report_name, template.model, res_id, context=context)
            report_service = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
            # Ensure report is rendered using template's language
            ctx = context.copy()
            if template.lang:
                ctx['lang'] = email_template_obj.render_template(cr, uid, template.lang, template.model, res_id, context)
            service = netsvc.LocalService(report_service)
            (result, format) = service.create(cr, uid, [res_id], {'model': template.model}, ctx)
            result = base64.b64encode(result)
            if not report_name:
                report_name = doc_data_id.res_name
            ext = "." + format
            if not report_name.endswith(ext):
                report_name += ext
            attachments[report_name] = result
            try:
                if doc_data_id.datas_unsigned:
                    b64_file = doc_data_id.datas_unsigned
                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id).res_name +'_unsigned.xml'
                    self._save_file(cr,uid,doc_id,path,b64_file)
                    osv._logger.warning('Creado el archivo  %s a las %s',path, time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado'))

                if doc_data_id.datas:
                    b64_file = doc_data_id.datas
                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id).res_name +'_signed.xml'
                    self._save_file(cr,uid,doc_id,path,b64_file)
                    osv._logger.warning('Creado el archivo  %s a las %s',path, time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado'))


                if doc_data_id.datas_signed:
                    b64_file = doc_data_id.datas_signed
                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id).res_name +'.xml'
                    self._save_file(cr,uid,doc_id,path,b64_file)
                    osv._logger.warning('Creado el archivo  %s a las %s',path, time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado'))

                if result:
                    b64_file = result
                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id).res_name +'.pdf'
                    self._save_file(cr,uid,doc_id,path,b64_file)
                    osv._logger.warning('Creado el archivo  %s a las %s',path, time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado'))

            except OSError, e:
                #raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado, %s'%e))            
                osv._logger.warning('El archivo correspondiente al id %s no puede ser creado', doc_id.id)
        # Add document attachments
        for attach in template.attachment_ids:
            # keep the bytes as fetched from the db, base64 encoded
            attachments[attach.datas_fname] = attach.datas

        values['attachments'] = attachments
#        return values
        assert 'email_from' in values, 'email_from is missing or empty after template rendering, send_mail() cannot proceed'
        attachments = values.pop('attachments') or {}
        cr.commit()
        msg_id = mail_message.create(cr, uid, values, context=context)
        # link attachments
        attachment_ids = []
        for fname, fcontent in attachments.iteritems():
            attachment_data = {
                    'name': fname,
                    'datas_fname': fname,
                    'datas': fcontent,
                    'res_model': mail_message._name,
                    'res_id': msg_id,
            }
            context.pop('default_type', None)
            ride_id = ir_attachment.create(cr, uid, attachment_data, context=context)
            attachment_ids.append(ride_id)
                                
        if attachment_ids:
            mail_message.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)
        ir_attachment.write(cr,uid,doc_id,{'datas_unsigned':False, 'datas_signed':False, 'datas':False, 'ride_name':tp_doc+'_'+report_name, 'datas_fname': tp_doc+'_'+doc_data_id.res_name+'.xml'})        
        proof = mail_message.send(cr, uid, [msg_id], context=context)
        if proof:
            for at_id in attachment_ids:
                cr.execute("""delete from ir_attachment where id = %s""",(at_id,))
                osv._logger.warning('enviado mail para adjunto de id # %s ',doc_id)            
        return True
        
    def send_document(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data') 
        send_document = self.pool.get('sri.send.document')
        inv = self.browse(cr,uid,ids[0])
        osv._logger.warning('El proceso de envío de correo electrónico empezó a las %s corresponde al # %s',time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)
        if inv.sign_state == '2' and inv.sri_code in ('01') and inv.number_auth and inv.res_model=='account.invoice':                    
            xml_id = 'email_electronic_invoice'
            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
            if not template_ids:
                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
            else:
                template_id = template_ids[1]
                tp_doc='FACT'
                context.update({'tp_doc':tp_doc})
            #cr.commit()
            self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
        elif inv.sign_state == '2' and inv.sri_code in ('02') and inv.number_auth and inv.res_model=='account.invoice':                    
            xml_id = 'email_electronic_credit_note'
            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
            if not template_ids:
                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
            else:
                template_id = template_ids[1]
                tp_doc='N_CRED'
                context.update({'tp_doc':tp_doc})
            #cr.commit()
            self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
        elif inv.sign_state == '2' and inv.sri_code in ('03') and inv.number_auth and inv.res_model=='account.invoice':                    
            xml_id = 'email_electronic_debit_note'
            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
            if not template_ids:
                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
            else:
                template_id = template_ids[1]
                tp_doc='N_DEBIT'
                context.update({'tp_doc':tp_doc})
            #cr.commit()
            self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
        elif inv.sign_state == '2' and inv.sri_code in ('04') and inv.number_auth and inv.res_model=='stock.delivery':                    
            xml_id = 'email_electronic_delivery'
            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
            if not template_ids:
                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
            else:
                template_id = template_ids[1]
                tp_doc='GR'
                context.update({'tp_doc':tp_doc})
            #cr.commit()
            self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)
        elif inv.sign_state == '2' and inv.sri_code in ('05') and inv.number_auth and inv.res_model=='account.withhold':                    
            xml_id = 'email_electronic_withhold'
            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
            if not template_ids:
                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
            else:
                template_id = template_ids[1]
                tp_doc='RET'
                context.update({'tp_doc':tp_doc})
            self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)
        return True
    
    
    
    def generate_email_electronic(self, cr, uid, template_id, res_id, doc_id, context=None):

        if context is None:
            context = {}
        send = self.pool.get('sri.send.document')    
        tp_doc = context.get('tp_doc','FACT')
        values = {
                  'subject': False,
                  'body_text': False,
                  'body_html': False,
                  'email_from': False,
                  'email_to': False,
                  'email_cc': False,
                  'email_bcc': False,
                  'reply_to': False,
                  'auto_delete': False,
                  'model': False,
                  'res_id': False,
                  'mail_server_id': False,
                  'attachments': False,
                  'attachment_ids': False,
                  'message_id': False,
                  'state': 'outgoing',
                  'subtype': 'plain',
        }
        if not template_id:
            return values

        report_xml_pool = self.pool.get('ir.actions.report.xml')
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')
        email_template_obj = self.pool.get('email.template')
        template = email_template_obj.get_email_template(cr, uid, template_id, res_id, context)
        template_context = email_template_obj._prepare_render_template_context(cr, uid, template.model, res_id, context)

        for field in ['subject', 'body_text', 'body_html', 'email_from',
                      'email_to', 'email_cc', 'email_bcc', 'reply_to',
                      'message_id']:
            values[field] = email_template_obj.render_template(cr, uid, getattr(template, field),
                                                 template.model, res_id, context=template_context) \
                                                 or False

        if values['body_html']:
            values.update(subtype='html')

        if template.user_signature:
            signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
            values['body_text'] += '\n\n' + signature

        values.update(mail_server_id = template.mail_server_id.id,
                      auto_delete = template.auto_delete,
                      model=template.model,
                      res_id=res_id or False)

        attachments = {}
        # Add report as a Document
        if doc_id:
            doc_data_id = ir_attachment.browse(cr,uid,doc_id)
            attachments[doc_data_id.datas_fname] = doc_data_id.authorized_url
        if template.report_template:
            report_name = email_template_obj.render_template(cr, uid, template.report_name, template.model, res_id, context=context)
            report_service = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
            # Ensure report is rendered using template's language
            ctx = context.copy()
            if template.lang:
                ctx['lang'] = email_template_obj.render_template(cr, uid, template.lang, template.model, res_id, context)
            service = netsvc.LocalService(report_service)
            (result, format) = service.create(cr, uid, [res_id], {'model': template.model}, ctx)
            result = base64.b64encode(result)
            if not report_name:
                report_name = doc_data_id.res_name
            ext = "." + format
            if not report_name.endswith(ext):
                report_name += ext
            attachments[report_name] = result
        # Add document attachments
        for attach in template.attachment_ids:
            # keep the bytes as fetched from the db, base64 encoded
            attachments[attach.datas_fname] = attach.datas

        values['attachments'] = attachments
#        return values
        assert 'email_from' in values, 'email_from is missing or empty after template rendering, send_mail() cannot proceed'
        attachments = values.pop('attachments') or {}
        cr.commit()
        msg_id = mail_message.create(cr, uid, values, context=context)
        # link attachments
        attachment_ids = []
        for fname, fcontent in attachments.iteritems():
            attachment_data = {
                    'name': fname,
                    'datas_fname': fname,
                    'datas': fcontent,
                    'res_model': mail_message._name,
                    'res_id': msg_id,
            }
            context.pop('default_type', None)
            ride_id = ir_attachment.create(cr, uid, attachment_data, context=context)
            attachment_ids.append(ride_id)
                                
        if attachment_ids:
            mail_message.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)
            #mail_message.browse(cr,uid, msg_id).attachment_ids
        ir_attachment.write(cr,uid,doc_id,{'datas_unsigned':False, 'datas_signed':False, 'datas':False, 'ride_name':tp_doc+'_'+report_name, 'datas_fname': tp_doc+'_'+doc_data_id.res_name+'.xml'})        
        proof = mail_message.send(cr, uid, [msg_id], context=context)
        if proof:
            for at_id in attachment_ids:
                cr.execute("""delete from ir_attachment where id = %s""",(at_id,))
                osv._logger.warning('enviado mail para adjunto de id # %s ',doc_id)       
            raise osv.except_osv(_("Enviado!"), _("Correo enviado exitosamente!"))  
        return 

ir_attachment()


class mail_compose_message(osv.osv_memory):
    _inherit = 'mail.compose.message'

    def default_get(self, cr, uid, fields, context=None):
        """Overridden to provide specific defaults depending on the context
           parameters.

           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
        """
        if context is None:
            context = {}
        result = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)

        if context is None:
            context = {}        
        mod_obj = self.pool.get('ir.model.data')
        active_model = context.get('active_model')                
        active_id = context.get('active_id')
        report_xml_pool = self.pool.get('ir.actions.report.xml')
        template_ids = False        
        if active_model == 'ir.attachment':
            for inv in self.pool.get(active_model).browse(cr,uid,[active_id],context):
                    if inv.sign_state == '2' and inv.sri_code in ('01') and inv.number_auth and inv.res_model=='account.invoice':                    
                        xml_id = 'email_electronic_invoice'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        tp_doc='FACT'
                        context.update({'tp_doc':tp_doc})
                    elif inv.sign_state == '2' and inv.sri_code in ('02') and inv.number_auth and inv.res_model=='account.invoice':                    
                        xml_id = 'email_electronic_credit_note'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        tp_doc='N_CRED'
                        context.update({'tp_doc':tp_doc})
                    elif inv.sign_state == '2' and inv.sri_code in ('03') and inv.number_auth and inv.res_model=='account.invoice':                    
                        xml_id = 'email_electronic_debit_note'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        tp_doc='N_DEBIT'
                        context.update({'tp_doc':tp_doc})
                    elif inv.sign_state == '2' and inv.sri_code in ('04') and inv.number_auth and inv.res_model=='stock.delivery':                    
                        cr.execute("""update stock_delivery set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                        xml_id = 'email_electronic_delivery'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        tp_doc='GR'
                        context.update({'tp_doc':tp_doc})
                    elif inv.sign_state == '2' and inv.sri_code in ('05') and inv.number_auth and inv.res_model=='account.withhold':                    
                        xml_id = 'email_electronic_withhold'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        tp_doc='RET'
                        context.update({'tp_doc':tp_doc})
                    if not template_ids:
                        raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                    else:
                        template_id = template_ids[1]

                    if template_id:
                    
                        values = {
                          'subject': False,
                          'body_text': False,
                          'body_html': False,
                          'email_from': False,
                          'email_to': False,
                          'email_cc': False,
                          'email_bcc': False,
                          'reply_to': False,
                          'auto_delete': False,
                          'model': False,
                          'res_id': False,
                          'mail_server_id': False,
                          'attachments': False,
                          'attachment_ids': False,
                          'message_id': False,
                          'state': 'outgoing',
                          'subtype': 'plain',
                          }
                        
                        
                        email_template_obj = self.pool.get('email.template')
                        template = email_template_obj.get_email_template(cr, uid, template_id, inv.res_id, context)
                        template_context = email_template_obj._prepare_render_template_context(cr, uid, template.model, inv.res_id, context)
                
                        for field in ['subject', 'body_text', 'body_html', 'email_from',
                                      'email_to', 'email_cc', 'email_bcc', 'reply_to',
                                      'message_id']:
                            values[field] = email_template_obj.render_template(cr, uid, getattr(template, field), template.model, inv.res_id, context=template_context) 
                        
                        if template.user_signature:
                            signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
                            values['body_text'] += '\n\n' + signature
                
                        values.update(mail_server_id = template.mail_server_id.id, auto_delete = template.auto_delete,model=template.model,res_id=inv.res_id)
                
                        attachments = {}
                        # Add report as a Document
                        if inv.authorized_url:
                            attachments[inv.datas_fname] = inv.authorized_url 
                        elif inv.datas_fname:                            
                            attachments[inv.datas_fname] =  inv.datas_signed and inv.datas_signed.decode('base64')
                            
                        if template.report_template:
                            report_name = email_template_obj.render_template(cr, uid, template.report_name, template.model, inv.res_id, context=context)
                            report_service = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
                            # Ensure report is rendered using template's language
                            ctx = context.copy()
                            if template.lang:
                                ctx['lang'] = email_template_obj.render_template(cr, uid, template.lang, template.model, inv.res_id, context)
                            service = netsvc.LocalService(report_service)
                            (result, format) = service.create(cr, uid, [inv.res_id], {'model': template.model}, ctx)
                            result = base64.b64encode(result)
                            if not report_name:
                                report_name = inv.res_name
                            ext = "." + format
                            if not report_name.endswith(ext):
                                report_name += ext
                            attachments[report_name] = result

                            attachment_ids = []
                            for fname, fcontent in attachments.iteritems():
                                attachment_data = {
                                        'name': fname,
                                        'datas_fname': fname,
                                        'datas': fcontent,
                                        'res_model': template.model,
                                        }
                                context.pop('default_type', None)
                                ride_id = self.pool.get(active_model).create(cr, uid, attachment_data, context=context)
                                attachment_ids.append(ride_id)                                                    
                            
                        result = ({
                                'subtype' : 'plain', # default to the text version due to quoting
                                'body_text' : values['body_text'],
                                'subject' : values['subject'],
                                'attachment_ids' : attachment_ids,
                                'model' : template.model,
                                'res_id' : inv.res_id,
                                'email_from' : values['email_from'],
                                'email_to' : values['email_to'],
                                'email_cc' : values['email_from'],
                                'user_id' : uid,
                            })
    
                        return result
mail_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

