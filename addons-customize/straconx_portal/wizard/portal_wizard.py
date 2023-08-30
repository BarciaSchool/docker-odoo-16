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

import logging
import random

from osv import osv, fields
from tools.misc import email_re
from tools.translate import _

from base.res.res_users import _lang_get



# welcome email sent to new portal users (note that calling tools.translate._
# has no effect except exporting those strings for translation)
WELCOME_EMAIL_SUBJECT = _("Your OpenERP account at %(company)s")
WELCOME_EMAIL_BODY = _("""Dear %(name)s,

You have been created an OpenERP account at %(url)s.

Your login account data is:
Database: %(db)s
User:     %(login)s
Password: %(password)s

%(message)s

--
OpenERP - Open Source Business Applications
http://www.openerp.com
""")

ROOT_UID = 1

# character sets for passwords, excluding 0, O, o, 1, I, l
_PASSU = 'ABCDEFGHIJKLMNPQRSTUVWXYZ'
_PASSL = 'abcdefghijkmnpqrstuvwxyz'
_PASSD = '23456789'

def random_password():
    # get 3 uppercase letters, 3 lowercase letters, 2 digits, and shuffle them
    chars = map(random.choice, [_PASSU] * 3 + [_PASSL] * 3 + [_PASSD] * 2)
    random.shuffle(chars)
    return ''.join(chars)

def extract_email(user_email):
    """ extract the email address from a user-friendly email address """
    m = email_re.search(user_email or "")
    return m and m.group(0) or ""



class wizard(osv.osv_memory):
    """
        A wizard to create portal users from instances of either 'res.partner'
        or 'res.partner.address'.  The purpose is to provide an OpenERP database
        access to customers or suppliers.
    """
    _name = 'res.portal.wizard'
    _description = 'Portal Wizard'
    
    _columns = {
        'portal_id': fields.many2one('res.portal', required=True,
            string='Portal',
            help="The portal in which new users must be added"),
        'user_ids': fields.one2many('res.portal.wizard.user', 'wizard_id',
            string='Users'),
        'message': fields.text(string='Invitation message',
            help="This text is included in the welcome email sent to the users"),
    }

    def prepare_new_user_data(self, u, wiz):
        return {
                    'name': u.partner_id.name,
                    'login': u.partner_id.vat[2:],
                    'password': u.partner_id.vat[2:],
                    'user_email': u.user_email,
                    'context_lang': u.lang,
                    'partner_id': u.partner_id and u.partner_id.id,
                    'groups_id': [(5,)], # prevent default groups!
                }
        
    def _default_portal_id(self,cr,uid,context):
        portal_obj = self.pool.get('res.portal')
        group_obj = self.pool.get('res.groups')
        group_ids = group_obj.search(cr,uid,[('name','=','Facturación Electrónica')])
        portal_id = False
        if group_ids:
            group_id = group_ids[0]
            portal_ids = portal_obj.search(cr,uid,[('group_id','=',group_id)])
            if portal_ids:
                portal_id = portal_ids[-1]  
        return portal_id
        

    def _default_user_ids(self, cr, uid, context):
        """ determine default user_ids from the active records """
        def create_user_from_address(address):
            if not extract_email(address.email):
                raise osv.except_osv(_('Correo Electrónico Requerido'),
                _('Se requiere configurar un correo electrónico para el envío de mensajes.'))
            return {    # a user config based on a contact (address)
                'name': address.partner_id.vat[2:],
                'user_email': extract_email(address.email),
                'lang': address.partner_id and address.partner_id.lang or 'es_EC',
                'partner_id': address.partner_id and address.partner_id.id,
            }
        
        user_ids = []
        
        if context.get('active_model') == 'res.partner':
            partner_obj = self.pool.get('res.partner')
            partner_ids = context.get('active_ids', [])
            partners = partner_obj.browse(cr, uid, partner_ids, context)
            for p in partners:
                if p.address:
                    user_ids.extend(map(create_user_from_address, p.address))
#                 user_ids.append({    
#                             'name': p.vat[2:],
#                             'lang': p.lang or 'es_EC',
#                             'partner_id': p.id,
#                             })             
        return user_ids

    _defaults = {
        'user_ids': _default_user_ids,
        'portal_id': _default_portal_id
    }

    def action_create(self, cr, uid, ids, context=None):
        """ create new users in portal(s), and notify them by email """
        context = dict(context or {})
        context['noshortcut'] = True           # prevent shortcut creation
        
        user_obj = self.pool.get('res.users')
        user = user_obj.browse(cr, ROOT_UID, uid, context)
#         if not user.user_email:
#             raise osv.except_osv(_('Email required'),
#                 _('You must have an email address in your User Preferences'
#                   ' to send emails.'))
        
        portal_obj = self.pool.get('res.portal')
        if context:
                direct = context.get('direct',False)
                user_ids = {}    
        
        if direct:
            portal_obj = self.pool.get('res.portal')
            group_obj = self.pool.get('res.groups')
            group_ids = group_obj.search(cr,uid,[('name','=','Facturación Electrónica')])
            portal_id = False
            if group_ids:
                group_id = group_ids[0]
                portal_ids = portal_obj.search(cr,uid,[('group_id','=',group_id)])
                if portal_ids:
                    portal_id = portal_ids[-1]              
            partner_id = self.pool.get('res.partner').browse(cr,uid,ids)
            user_ids=({ 
                'name': partner_id.name,
                'login': partner_id.vat[2:],
                'password': partner_id.vat[2:],
                'context_lang': partner_id.lang or 'es_EC',
                'partner_id': partner_id.id,
                'groups_id': [(5,)], # prevent default groups!
                'user_email': False,                
                        })
            
            login_cond = [('login', '=', partner_id.vat)]
            existing_uids = user_obj.search(cr, ROOT_UID, login_cond)
            existing_users = user_obj.browse(cr, ROOT_UID, existing_uids)
            if not existing_users:
                new_users_data = [user_ids]     
                new_user = user_obj.create(cr,uid,user_ids,context)            
                cr.execute("""insert into res_groups_users_rel(uid,gid)values(%s,%s) """,(new_user,group_id))
                cr.commit()
                return True
            else:
                return True
            
        else:
                
            for wiz in self.browse(cr, uid, ids, context):
                # determine existing users
                login_cond = [('login', 'in', [u.partner_id.vat[2:] for u in wiz.user_ids])]
                existing_uids = user_obj.search(cr, ROOT_UID, login_cond)
                existing_users = user_obj.browse(cr, ROOT_UID, existing_uids)
                existing_logins = [u.login for u in existing_users]
                
                # create new users in portal (skip existing logins)
                new_users_data = [ self.prepare_new_user_data(u, wiz)
                    for u in wiz.user_ids if u.partner_id.vat[2:] not in existing_logins ]
                portal_obj.write(cr, ROOT_UID, [wiz.portal_id.id],
                    {'users': [(0, 0, data) for data in new_users_data]}, context)        
                cr.commit()
            return {'type': 'ir.actions.act_window_close'}

wizard()



class wizard_user(osv.osv_memory):
    """
        A model to configure users in the portal wizard.
    """
    _name = 'res.portal.wizard.user'
    _description = 'Portal User Config'

    _columns = {
        'wizard_id': fields.many2one('res.portal.wizard', required=True,
            string='Wizard'),
        'name': fields.char(size=64, required=True,
            string='User Name',
            help="The user's real name"),
        'user_email': fields.char(size=64, required=False,
            string='E-mail',
            help="Will be used as user login.  "  
                 "Also necessary to send the account information to new users"),
        'lang': fields.selection(_lang_get, required=True,
            string='Language',
            help="The language for the user's user interface"),
        'partner_id': fields.many2one('res.partner',
            string='Partner'),
    }

    def _check_email(self, cr, uid, ids):
        """ check syntax of email address """
        for wuser in self.browse(cr, uid, ids):
            if not email_re.match(wuser.user_email): return False
        return True

    _constraints = [
        (_check_email, 'Invalid email address', ['email']),
    ]

wizard_user()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
