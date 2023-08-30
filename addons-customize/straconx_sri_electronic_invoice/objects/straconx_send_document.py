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
import subprocess
from random import randrange
import os
import netsvc

import suds
from suds.client import Client
from suds.sax.text import Raw
from suds.sax.element import Element
from suds.wsse import *
import re
import base64,os,shutil,tarfile,StringIO,urllib


class straconx_sri_send_document(osv.osv):

    _name = 'sri.send.document'

    def sri_send_document(self, cr, uid, context=None):

        if not context:
            context = {}
        name = cr.dbname
        date_inv = time.strftime('%Y-%m-%d')
        user_id = self.pool.get('res.users').browse(cr, uid, uid)
        shop_obj = self.pool.get('sale.shop')
        ir_attachment = self.pool.get('ir.attachment')

        if user_id.company_id.only_principal_shop:
            shop_ids = shop_obj.search(cr, uid, [('emision_point', '=', 'True'),
                                                 ('company_id', '=', user_id.company_id.id),
                                                 ('server_db', '=', name)])
        else:
            shop_ids = shop_obj.search(cr, uid, [('emision_point', '=', 'True'),
                                                 ('company_id', '=', user_id.company_id.id)])
        if user_id.company_id.sri_url:
            url2 = user_id.company_id.sri_url
            client2 = Client(url2)
        else:
            raise osv.except_osv(_('Error!'),
                                 _('Debe definir el servidor de autorización para Documentos Electrónicos en Configuración/Compañia.'))

        if shop_ids:
            for shop_id in shop_ids:
                cr.execute("""select id
                        from ir_attachment
                        where res_id in
                        (
                        (select id from account_invoice where electronic=True and shop_id = %s and date_invoice <=%s)
                        union all
                        (select id from stock_delivery where electronic=True and picking_id in (select id from stock_picking where shop_id= %s
                        and date(date) <=%s))
                        union all
                        (select id from account_withhold where electronic = True and shop_id = %s and date <=%s)
                        )
                        and sign_state in ('0','1','4')
                        and sri_code is not null
                        and res_model in ('account.invoice','account.withhold','stock.delivery')
                        and active = True
                        order by id; """, (shop_id, date_inv, shop_id, date_inv, shop_id, date_inv))

                send_ids = cr.fetchall()
                company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'sri.send.document', context=context),
                company_path = self.pool.get('res.company').browse(cr, uid, company_id[0]).electronic_path
                mod_obj = self.pool.get('ir.model.data')
                ret = 0
                if send_ids:
                    for att_id in send_ids:
                        cr.execute("""select access_key from ir_attachment where id=%s""", (att_id[0],))
                        access_key = cr.fetchone()
                        if access_key:
                            osv._logger.warning('Verificando la clave de acceso %s del id # %s', access_key, att_id[0])
                            client2.service.autorizacionComprobante(access_key)
                            try:
                                osv._logger.warning('Documento con id # %s pasa a aprobación ', att_id[0])
                                numeroAutorizacion = client2.last_received().getChild(name="Envelope").getChild(name="Body").getChild(name="autorizacionComprobanteResponse").getChild("RespuestaAutorizacionComprobante").getChild("autorizaciones").getChild("autorizacion").getChild("numeroAutorizacion").getText()
                                fechaAutorizacion = client2.last_received().getChild(name="Envelope").getChild(name="Body").getChild(name="autorizacionComprobanteResponse").getChild("RespuestaAutorizacionComprobante").getChild("autorizaciones").getChild("autorizacion").getChild("fechaAutorizacion").getText()
                                estado = client2.last_received().getChild(name="Envelope").getChild(name="Body").getChild(name="autorizacionComprobanteResponse").getChild("RespuestaAutorizacionComprobante").getChild("autorizaciones").getChild("autorizacion").getChild("estado").getText()
                                xml = client2.last_received().getChild(name="Envelope").getChild(name="Body").getChild(name="autorizacionComprobanteResponse").getChild("RespuestaAutorizacionComprobante").getChild("autorizaciones").getChild("autorizacion")
                                xml = Raw(xml)
                                uno = base64.b64decode(xml)
                                uno = base64.b64encode(xml)
                                if estado == 'AUTORIZADO':
                                    estado = "2"
                                    cr.execute("update ir_attachment set write_date=now(), datas_signed=%s, number_auth=%s, sri_date=%s,"
                                               "sign_state=%s where id=%s", (uno, numeroAutorizacion, fechaAutorizacion, estado, att_id[0]))
                                    cr.commit()
                                    ret == 255
                            except:
                                osv._logger.warning('El proceso del documento inició a las %s corresponde al id # %s',
                                                    time.strftime('%Y-%m-%d %H:%M:%S'), att_id[0])
                                cmd = "java -jar %sfirmante.jar %s" % (company_path, att_id[0])
                                osv._logger.warning('Tratando de ejecutar %s', cmd)
                                cmd = str(cmd)
                                call = ["/bin/bash", "-c", cmd]
                                ret = subprocess.call(call, stdout=None, stderr=None)
                                osv._logger.warning('Ejecutando el subproceso %s', ret)
                                if ret != 255:
                                    osv._logger.warning('Aviso - el resultado fue %s revise el id %s', ret, att_id[0])
                                else:
                                    ret = 255
                                osv._logger.warning('El proceso finalizó a las %s corresponde al id # %s',
                                                    time.strftime('%Y-%m-%d %H:%M:%S'), att_id[0])
                                cr.commit()
                        if ret == 255:
                            inv = ir_attachment.browse(cr, uid, att_id[0])
                            osv._logger.warning('El proceso de envío de correo electrónico empezó a las %s corresponde al # %s',
                                                time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)
                            if inv.sign_state == '2' and inv.sri_code in ('01') and inv.number_auth and inv.res_model == 'account.invoice':
                                cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s,
                                            sri_authorization=%s where id=%s""", (inv.number_auth, inv.access_key, inv.number_auth, inv.res_id))
                                xml_id = 'email_electronic_invoice'
                                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                                if not template_ids:
                                    raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico'
                                                                        ' para Documentos Electrónicos.'))
                                else:
                                    template_id = template_ids[1]
                                    tp_doc = 'FACT'
                                    context.update({'tp_doc': tp_doc})
                                cr.commit()
                                self.generate_email_electronic(cr, uid, template_id, inv.res_id, inv.id, context)
                            elif inv.sign_state == '2' and inv.sri_code in ('02') and inv.number_auth and inv.res_model == 'account.invoice':
                                cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s
                                            where id=%s""", (inv.number_auth, inv.access_key, inv.number_auth, inv.res_id))
                                xml_id = 'email_electronic_credit_note'
                                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                                if not template_ids:
                                    raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico'
                                                                        ' para Documentos Electrónicos.'))
                                else:
                                    template_id = template_ids[1]
                                    tp_doc = 'N_CRED'
                                    context.update({'tp_doc':tp_doc})
                                cr.commit()
                                self.generate_email_electronic(cr, uid, template_id, inv.res_id,inv.id, context)
                            elif inv.sign_state == '2' and inv.sri_code in ('03') and inv.number_auth and inv.res_model == 'account.invoice':
                                cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                                xml_id = 'email_electronic_debit_note'
                                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                                if not template_ids:
                                    raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                                else:
                                    template_id = template_ids[1]
                                    tp_doc='N_DEBIT'
                                    context.update({'tp_doc':tp_doc})
                                cr.commit()
                                self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
                            elif inv.sign_state == '2' and inv.sri_code in ('04') and inv.number_auth and inv.res_model=='stock.delivery':                    
                                cr.execute("""update stock_delivery set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                                xml_id = 'email_electronic_delivery'
                                template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                                if not template_ids:
                                    raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))
                                else:
                                    template_id = template_ids[1]
                                    tp_doc='GR'
                                    context.update({'tp_doc':tp_doc})
                                cr.commit()
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
                                cr.execute("""update account_withhold set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                                cr.commit()
                                self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)
                            cr.commit()
                            cr.execute("""update ir_attachment set write_date=now() where id =%s """,(inv.id,))                        
        return True

    def sri_send_document_ids(self, cr, uid, ids, context=None):

        if not context:
            context = {}
        date_inv = time.strftime('%Y-%m-%d')
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        shop_obj = self.pool.get('sale.shop')
        ir_attachment = self.pool.get('ir.attachment')        
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'sri.send.document', context=context),
        company_path = self.pool.get('res.company').browse(cr,uid,company_id[0]).electronic_path
        mod_obj = self.pool.get('ir.model.data') 
        if ids:
            for att_id in ids:
                osv._logger.warning('El proceso del documento inició a las %s corresponde al id # %s',time.strftime('%Y-%m-%d %H:%M:%S'), att_id)                
                cmd = "java -jar %sfirmante.jar %s"%(company_path,att_id)
                osv._logger.warning('Tratando de ejecutar %s',cmd)     
                cmd = str(cmd) 
                call = ["/bin/bash", "-c", cmd]
                ret = subprocess.call(call, stdout=None, stderr=None)
                osv._logger.warning('Ejecutando el subproceso %s',ret)
                if ret <> 255:
                    osv._logger.warning('Aviso - el resultado fue %s revise el id %s',ret, att_id)
                osv._logger.warning('El proceso finalizó a las %s corresponde al id # %s',time.strftime('%Y-%m-%d %H:%M:%S'), att_id)            
                cr.commit()
                if ret==255:
                    inv = ir_attachment.browse(cr,uid,att_id)
                    osv._logger.warning('El proceso de envío de correo electrónico empezó a las %s corresponde al # %s',time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)
                    if inv.sign_state == '2' and inv.sri_code in ('01') and inv.number_auth and inv.res_model=='account.invoice':                    
                        cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                        xml_id = 'email_electronic_invoice'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        if not template_ids:
                            raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                        else:
                            template_id = template_ids[1]
                            tp_doc='FACT'
                            context.update({'tp_doc':tp_doc})
                        cr.commit()
                        self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
                    elif inv.sign_state == '2' and inv.sri_code in ('02') and inv.number_auth and inv.res_model=='account.invoice':                    
                        cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                        xml_id = 'email_electronic_credit_note'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        if not template_ids:
                            raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                        else:
                            template_id = template_ids[1]
                            tp_doc='N_CRED'
                            context.update({'tp_doc':tp_doc})
                        cr.commit()
                        self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
                    elif inv.sign_state == '2' and inv.sri_code in ('03') and inv.number_auth and inv.res_model=='account.invoice':                    
                        cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                        xml_id = 'email_electronic_debit_note'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        if not template_ids:
                            raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                        else:
                            template_id = template_ids[1]
                            tp_doc='N_DEBIT'
                            context.update({'tp_doc':tp_doc})
                        cr.commit()
                        self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
                    elif inv.sign_state == '2' and inv.sri_code in ('04') and inv.number_auth and inv.res_model=='stock.delivery':                    
                        cr.execute("""update stock_delivery set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                        xml_id = 'email_electronic_delivery'
                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                        if not template_ids:
                            raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                        else:
                            template_id = template_ids[1]
                            tp_doc='GR'
                            context.update({'tp_doc':tp_doc})
                        cr.commit()
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
                        cr.execute("""update account_withhold set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                        cr.commit()
                        self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)
                    cr.commit()
                    cr.execute("""update ir_attachment set write_date=now() where id =%s """,(inv.id,))                        
        return True


    def generate_email_electronic(self, cr, uid, template_id, res_id, doc_id, context=None):
        """Generates an email from the template for given (model, res_id) pair.

           :param template_id: id of the template to render.
           :param res_id: id of the record to use for rendering the template (model
                          is taken from template definition)
           :returns: a dict containing all relevant fields for creating a new
                     mail.message entry, with the addition one additional
                     special key ``attachments`` containing a list of
        """
        if context is None:
            context = {}
            
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

    def _save_file(self, cr,uid, ids, path, b64_file):
        """Save a file encoded in base 64"""
        dir_path = self.pool.get('res.users').browse(cr,uid,uid).company_id.files_path
#         dir_path = os.path.dirname(image_filestore)
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        except OSError, e:
            raise osv.except_osv(_('Error'), _('The image filestore can not be created, %s'%e))
        full_path = os.path.join(dir_path,path)
        with open(full_path, 'w') as ofile:
            ofile.write(base64.b64decode(b64_file))
        return True


    def sri_send_migrate_files(self, cr, uid, context=None):                
        if not context:
            context = {}
        name = cr.dbname
        date_inv = time.strftime('%Y-%m-%d')
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        shop_obj = self.pool.get('sale.shop')
        ir_attachment = self.pool.get('ir.attachment')
        email_template_obj = self.pool.get('email.template')        
        report_xml_pool = self.pool.get('ir.actions.report.xml')
        
        if user_id.company_id.only_principal_shop:
            shop_ids = shop_obj.search(cr,uid,[('emision_point','=','True'),('company_id','=',user_id.company_id.id),('server_db','=',name)])
        else:
            shop_ids = shop_obj.search(cr,uid,[('emision_point','=','True'),('company_id','=',user_id.company_id.id)])
        
        if shop_ids:
            for shop_id in shop_ids:
                cr.execute("""select id
                        from ir_attachment
                        where 
                        res_id in 
                        (
                        (select id from account_invoice where electronic=True and shop_id = %s and date_invoice <=%s)
                        union all
                        (select id from stock_delivery where electronic=True and picking_id in (select id from stock_picking where shop_id= %s and date(date) <=%s))
                        union all
                        (select id from account_withhold where electronic = True and shop_id = %s and date <=%s)
                        )
                        and sign_state = '2'
                        and datas_signed is not null
                        and sri_code is not null 
                        and res_model in ('account.invoice','account.withhold','stock.delivery')
                        and active = True                    
                        order by id; """,(shop_id,date_inv,shop_id,date_inv,shop_id,date_inv))

                send_ids = cr.fetchall()
                company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'sri.send.document', context=context),
                company_path = self.pool.get('res.company').browse(cr,uid,company_id[0]).electronic_path
                mod_obj = self.pool.get('ir.model.data') 
                if send_ids:
                    for doc_id in send_ids:
                        doc_id = ir_attachment.browse(cr,uid,doc_id[0])
                        if doc_id.sign_state == '2' and doc_id.sri_code in ('01') and doc_id.number_auth and doc_id.res_model=='account.invoice':                    
                            xml_id = 'email_electronic_invoice'
                            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                            if not template_ids:
                                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                            else:
                                template_id = template_ids[1]
                                tp_doc='FACT'                        
                        elif doc_id.sign_state == '2' and doc_id.sri_code in ('02') and doc_id.number_auth and doc_id.res_model=='account.invoice':                    
                            xml_id = 'email_electronic_credit_note'
                            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                            if not template_ids:
                                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                            else:
                                template_id = template_ids[1]
                                tp_doc='N_CRED'                        
                        elif doc_id.sign_state == '2' and doc_id.sri_code in ('03') and doc_id.number_auth and doc_id.res_model=='account.invoice':                    
                            xml_id = 'email_electronic_debit_note'
                            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                            if not template_ids:
                                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                            else:
                                template_id = template_ids[1]
                                tp_doc='N_DEBIT'
                        elif doc_id.sign_state == '2' and doc_id.sri_code in ('04') and doc_id.number_auth and doc_id.res_model=='stock.delivery':                    
                            xml_id = 'email_electronic_delivery'
                            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                            if not template_ids:
                                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                            else:
                                template_id = template_ids[1]
                                tp_doc='GR'
                        elif doc_id.sign_state == '2' and doc_id.sri_code in ('05') and doc_id.number_auth and doc_id.res_model=='account.withhold':                    
                            xml_id = 'email_electronic_withhold'
                            template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                            if not template_ids:
                                raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                            else:
                                template_id = template_ids[1]
                                tp_doc='RET'
                        if template_id:
                            template = email_template_obj.get_email_template(cr, uid, template_id, doc_id, context)                        
                            report_name = email_template_obj.render_template(cr, uid, template.report_template.name, template.model, doc_id, context=context)
                            doc_data_id = ir_attachment.browse(cr,uid,doc_id.id)
                            report_service = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
                            service = netsvc.LocalService(report_service)
                            context.update({'active_model':doc_id.res_model})
                            cr.commit()
                            (result, format) = service.create(cr, uid, [doc_id.res_id], {'model': template.model}, context)
                            result = base64.b64encode(result)
                            if not report_name:
                                report_name = tp_doc+'_'+doc_data_id.res_name
                            ext = "." + format
                            if not report_name.endswith(ext):
                                report_name += ext
                            try:
                                if doc_data_id.datas_unsigned:
                                    b64_file = doc_data_id.datas_unsigned
                                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id.id).res_name +'_unsigned.xml'
                                    self._save_file(cr,uid,doc_id.id,path,b64_file)
                                if doc_data_id.datas:
                                    b64_file = doc_data_id.datas
                                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id.id).res_name +'_signed.xml'
                                    self._save_file(cr,uid,doc_id.id,path,b64_file)
                                if doc_data_id.datas_signed:
                                    b64_file = doc_data_id.datas_signed
                                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id.id).res_name +'.xml'
                                    self._save_file(cr,uid,doc_id.id,path,b64_file)
                                else:
                                    raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado'))            
                                if result:
                                    b64_file = result
                                    path = tp_doc+'_'+ir_attachment.browse(cr,uid,doc_id.id).res_name +'.pdf'
                                    self._save_file(cr,uid,doc_id.id,path,b64_file)
                                else:
                                    raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado'))
                            except OSError, e:
                                #raise osv.except_osv(_('¡Error!'), _('El archivo no puede ser creado, %s'%e))  
                                osv._logger.warning('El archivo correspondiente al id %s no puede ser creado', doc_id.id)                        
                            cr.commit()        
                            cr.execute("update ir_attachment set datas=Null, datas_unsigned=Null, datas_signed=Null, ride_name=%s, datas_fname=%s where id=%s",(tp_doc+'_'+doc_id.res_name+'.pdf', tp_doc+'_'+doc_id.res_name+'.xml', doc_id.id))                        
        return True
    


    def sri_send_document_correct(self, cr, uid, context=None):                
        name = cr.dbname
        date_inv = time.strftime('%Y-%m-%d')
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        shop_obj = self.pool.get('sale.shop')
        ir_attachment = self.pool.get('ir.attachment')
        invoice_obj = self.pool.get('account.invoice')  
        mod_obj = self.pool.get('ir.model.data')              
        if user_id.company_id.only_principal_shop:
            shop_ids = shop_obj.search(cr,uid,[('emision_point','=','True'),('company_id','=',user_id.company_id.id),('server_db','=',name)])
        else:
            shop_ids = shop_obj.search(cr,uid,[('emision_point','=','True'),('company_id','=',user_id.company_id.id)])
        
        if shop_ids:
            for shop_id in shop_ids:
                cr.execute("""select id from account_invoice where electronic = True and state in ('open','paid') and shop_id=%s and migrate=True""",(shop_id,))
                invoice_ids = cr.fetchall()
                company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'sri.send.document', context=context),
                company_path = self.pool.get('res.company').browse(cr,uid,company_id[0]).electronic_path
                
                if invoice_ids:
                    for invoice in invoice_ids:
                        invoice = invoice_obj.browse(cr,uid,invoice[0])
                        if invoice.electronic and invoice.type in ('out_invoice','out_refund','debit_note'):
                            date_inv = time.strftime('%d%m%Y')
                            if invoice.journal_id.type == 'sale':                
                                code = '01'
                            elif invoice.journal_id.type == 'sale_refund':
                                code = '04'
                            elif invoice.journal_id.type == 'debit_note':
                                code = '05'                
                            context=({'code_sri':code})
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
                            digit = invoice_obj.mod11(lst, 7)
                            authorization = str(numeric_code)+str(digit)
                            if len(authorization)<>49:
                                raise osv.except_osv(_('Error!'), _('La clave de autorización es diferente a 48 dígitos, que es el valor requerido por el SRI.'))
                            invoice_obj.write(cr,uid,[invoice.id],{'authorization':authorization})
                            invoice_obj.act_export_electronic(cr,uid,[invoice.id],context)                
                            att_id = ir_attachment.search(cr,uid,[('res_id','=',invoice.id),('active','=',True)])
                            if att_id:
                                inv = ir_attachment.browse(cr,uid,att_id[-1])
                                osv._logger.warning('El proceso del documento inició a las %s corresponde al # %s',time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)                
                                cmd = "%s %s"%(company_path,att_id[0])    
                                cmd = str(cmd) 
                                call = ["/bin/bash", "-c", cmd]
                                ret = subprocess.call(call, stdout=None, stderr=None)
                                osv._logger.warning('Ejecutando id %s',ret)
                                if ret <> 255:
                                    osv._logger.warning('Aviso - el resultado fue %s revise el id %s',ret, att_id)
                                osv._logger.warning('El proceso finalizó a las %s corresponde al id # %s',time.strftime('%Y-%m-%d %H:%M:%S'), att_id)            
                                cr.commit()
                                if ret==255:
                                    inv = ir_attachment.browse(cr,uid,att_id)
                                    osv._logger.warning('El proceso de envío de correo electrónico empezó a las %s corresponde al # %s',time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)
                                    if inv.sign_state == '2' and inv.sri_code in ('01') and inv.number_auth and inv.res_model=='account.invoice':                    
                                        cr.execute("""update account_invoice set write_date=now(), "authorization"=%s, access_key=%s, sri_authorization=%s where id=%s""",(inv.number_auth,inv.access_key,inv.number_auth,inv.res_id))
                                        xml_id = 'email_electronic_invoice'
                                        template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_sri_electronic_invoice', xml_id)
                                        if not template_ids:
                                            raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Documentos Electrónicos.'))            
                                        else:
                                            template_id = template_ids[1]
                                            tp_doc='FACT'
                                            context.update({'tp_doc':tp_doc})
                                        cr.commit()
                                        self.generate_email_electronic(cr,uid,template_id,inv.res_id,inv.id,context)                        
                    return True

    def sri_delivery_document_correct(self,  cr, uid, context=None):
        ir_attachment = self.pool.get('ir.attachment')
        delivery_obj = self.pool.get('stock.delivery')

        cr.execute("""select res_id, id from ir_attachment where res_model='stock.delivery' and electronic = True and active=True and
        (number_auth is null or number_auth ='')""")
        delivery_ids = cr.fetchall()
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'sri.send.document', context=context),
        company_path = self.pool.get('res.company').browse(cr, uid, company_id[0]).electronic_path
        delivery_date = time.strftime('%Y-%m-%d %H:%M:%S')
        code = '06'
        context = ({'code_sri': '04'})
        if delivery_ids:
            for delivery in delivery_ids:
                att_del = delivery[1]
                delivery = delivery_obj.browse(cr, uid, delivery[0])
                if len(delivery.authorization) > 37:
                    delivery_obj.act_export_electronic(cr, uid, [delivery.id], context)
                    cr.execute("""update ir_attachment set active = False, write_date = now() where id =%s """, (att_del,))
                    att_id = ir_attachment.search(cr, uid, [('res_id', '=', delivery.id), ('active', '=', True)])
                    if att_id:
                        inv = ir_attachment.browse(cr, uid, att_id[-1])
                        osv._logger.warning('El proceso del documento inició a las %s corresponde al # %s',time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)                
                        cmd = "%s %s"%(company_path,att_id[-1])    
                        cmd = str(cmd) 
                        call = ["/bin/bash", "-c", cmd]
                        ret = subprocess.call(call, stdout=None, stderr=None)
                        osv._logger.warning('Ejecutando id %s',ret)
                        if ret > 0:
                            osv._logger.warning('Warning - result was %s ',ret)
                    osv._logger.warning('El proceso finalizó a las %s corresponde al # %s',time.strftime('%Y-%m-%d %H:%M:%S'), inv.name)            
                    cr.execute("""update ir_attachment set write_date=now() where id =%s """,(att_id[0],))
                    if inv.sign_state == '2' and inv.sri_code in ('04') and inv.number_auth:
                        cr.execute("""update stock_delivery set write_date=now(), sri_authorization=%s, sri_date=%s where id=%s""",(delivery_date,inv.number_auth,inv.res_id))        
                else:
                    vat = delivery.picking_id.company_id.partner_id.vat[2:]
                    environment = delivery.authorization_id.environment
                    type_emision = delivery.authorization_id.type_emision
                    serie = delivery.number[0:3]+delivery.number[4:7]
                    secuencial = delivery.number[8:]
                    delivery_date = delivery.date
                    if delivery_date:
                        n_code = delivery_date[8:10]+delivery_date[5:7]+delivery_date[0:4]
                    date_inv = n_code
                    numeric_code = date_inv+code+str(vat)+str(environment)+str(serie)+str(secuencial)+str(n_code)+type_emision
                    lst = [int(i) for i in str(numeric_code)]
                    digit = delivery_obj.mod11(lst, 7)
                    cr.execute("""update ir_attachment set active = False, write_date = now() where id =%s """,(att_del,))
                    if len(delivery.authorization)<>49:
                        authorization = str(numeric_code)+str(digit)
                        delivery_obj.write(cr,uid,[delivery.id],{'authorization':authorization})
                    context['code_sri']='04'
                    delivery_obj.act_export_electronic(cr,uid,[delivery.id],context)                  
            return True

straconx_sri_send_document()