# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A 
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

from osv import fields, osv
from tools.translate import _

class create_partner_from_user(osv.osv_memory):
    _name="create.partner.from.user"
    
    _columns={
              'vat': fields.char('VAT',size=32 ,help="CI, RUC or passport. Please enter the number with the 2 first letters of your country at the beginning"),
              'exists': fields.boolean('Empresa existe')
              }
    
    _defaults={'exists':False}

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res={}
        user = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
        employee_obj = self.pool.get('hr.employee')
        pt_ids = employee_obj.search(cr,uid,[('user_id','=',user.id)])
        if pt_ids:
            pt_id = employee_obj.browse(cr,uid,pt_ids[0])
            res['exists']=True
            res['vat']= pt_id.vat
        return res
    
    def create_partner_from_user(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        partner_obj = self.pool.get('res.partner')
        user = self.pool.get(context['active_model']).browse(cr , uid, context['active_id'])
        employee_obj = self.pool.get('hr.employee')
        wizard=ids and self.browse(cr,uid, ids, context)[0] or None
        if user.partner_id:
            raise osv.except_osv(_('Invalid action!'), _('This user has created a partner, please check'))
        if wizard.exists:
            pt_ids = employee_obj.search(cr,uid,[('user_id','=',user.id)])
            if pt_ids:
                pt_id = employee_obj.browse(cr,uid,pt_ids[0])
                partner_id = pt_id.partner_id.id
                address_id = pt_id.address_home_id.id
                vat = pt_id.vat         
                user.write({'partner_id':partner_id, 'address_id':address_id,'vat':vat})        
        else:
            vat=wizard and wizard.vat or user.vat_migrate or None
            res=partner_obj.vat_change(cr, uid, [user.id], vat, {})
            segment_ids=self.pool.get('res.partner.segmento').search(cr, uid, [('is_default','=',True)])
            vals=res.get('value',{})
            vals.update({'name': user.name,
                         'vat': vat,
                         'employee':True,
                         'customer':True,
                         'segmento_id':segment_ids and segment_ids[0] or None,
                         })
            partner_id=partner_obj.create(cr, uid, vals, context)
            address_id = self.pool.get('res.partner.address').create(cr, 1, {'name': user.name,
                                                                             'type': 'default', 
                                                                             'partner_id': partner_id, 
                                                                             'email': user.user_email or None,
                                                                             'location_id':user.company_id.location_id.id})
            user.write({'partner_id':partner_id, 'address_id':address_id})
        return {'type': 'ir.actions.act_window_close'}
    
create_partner_from_user()