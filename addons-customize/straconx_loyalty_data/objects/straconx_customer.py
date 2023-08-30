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
import os, time
#from datetime import datetime
import datetime as dt 
from dateutil.relativedelta import relativedelta
from datetime import datetime
import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
import netsvc
import binascii
import os
import uuid
from string import upper

# Crear dos cron: a) Expira la promoción, b) Expira las líneas del cliente, c) Correo electrónico par el cliente.    

class sales_partner(osv.osv):

    _inherit = "sales.loyalty.partner"

    def sales_partner_send_document(self, cr, uid, context=None):

        if not context:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        date_to = datetime.now().strftime('%Y-%m-%d')
            
        partner_ids = self.search(cr,uid,[('email_send','=',False),('active','=',True)], limit=20)
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
        
        if partner_ids:        
            for p in partner_ids:
                expired_bonus = 0.00
                received_bonus = 0.00
                redeem_bonus = 0.00
                saldo = 0.00
                actual_bonus = 0.00
                total_invoices = 0.00
                bonus_ids = False
                p = self.browse(cr,uid,p)
                if p.partner_id.id:
                    partner_id = p.partner_id.id
                    bon_ids = self.pool.get('sales.loyalty.partner.line').search(cr,uid,[('partner_id','=',partner_id),('active','=',True)])
                    bonus_ids = self.pool.get('sales.loyalty.partner.line').browse(cr,uid,bon_ids)

                for line in bonus_ids:
                    if line.state=='expired':                    
                        expired_bonus += round((line.bonus),di)
                    if line.type=='add' and line.active and line.state=='pending':                
                        received_bonus += round((line.bonus),di)
                    if line.type=='subtract' and line.active and line.state=='redimed':
                        redeem_bonus += round((line.bonus),di)  
                    if line.amount_invoice:
                        total_invoices += round((line.amount_invoice),di)
                    if line.type=='add' and line.active and line.state=='pending':                
                        saldo += round((line.pending),di)
    
                actual_bonus = received_bonus - expired_bonus -  redeem_bonus
                actual_bonus = saldo                
                self.write(cr,uid,p.id, {
                    'received_bonus':received_bonus,
                    'redeem_bonus':redeem_bonus,
                    'expired_bonus': expired_bonus,
                    'actual_bonus': actual_bonus,
                    'total_invoices': total_invoices
                    })        
                cr.commit()
                if actual_bonus > 0:
                    print p.actual_bonus
                    xml_id = 'data_customer'
                    template_ids = mod_obj.get_object_reference(cr, uid, 'straconx_loyalty', xml_id)
                    if not template_ids:
                        raise osv.except_osv(_('Error!'), _('No existe una plantilla para el envío del correo electrónico para Promociones.'))            
                    else:
                        template_id = template_ids[1]
                        print p.partner_id.name
                        self.generate_email_partner_electronic(cr,uid,template_id,p.id,context)
                        self.write(cr,uid,[p.id],{'email_send':True})                      
        return True

    def generate_email_partner_electronic(self, cr, uid, template_id, res_id, context=None):
        if context is None:
            context = {}
            
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

        email = self.browse(cr,uid,res_id).partner_id.address[0].email
        values.update(mail_server_id = template.mail_server_id.id,
                      auto_delete = template.auto_delete,
                      model=template.model,
                      res_id=res_id or False)

        attachments = {}

        values['attachments'] = attachments
#        return values
        assert 'email_from' in values, 'email_from is missing or empty after template rendering, send_mail() cannot proceed'
        attachments = values.pop('attachments') or {}
        cr.commit()
        msg_id = mail_message.create(cr, uid, values, context=context)
        # link attachments
#         mail_message.send(cr, uid, [msg_id], context=context)
        return True


sales_partner()


