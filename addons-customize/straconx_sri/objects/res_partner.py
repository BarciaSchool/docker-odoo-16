# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#
##############################################################################

from osv import fields, osv
import method
from tools.translate import _

class res_partner(osv.osv): 
    _inherit = "res.partner"
    _columns = {'type_company_id': fields.many2one('res.partner.type.company', 'Type company', required=False),
                'tax_sustent': fields.many2one('sri.tax.sustent', 'Tax Sustent', readonly=True)}

#     def vat_change(self, cr, uid, ids, vat = None, context = None):
#         type_company_obj=self.pool.get('res.partner.type.company')
#         result=super(res_partner, self).vat_change(cr, uid, ids, vat, context)
#         type_company_ids=[]
#         fiscal_position=[]
#         origin=result['value']['origin']
#         type_vat=result['value']['type_vat']
#         if vat:
#             if origin == 'international':
#                 type_company_ids=type_company_obj.search(cr, uid, [('shortcut','=','FC')])
#                 fiscal_position = [5]
#                 result['value']['property_account_position']=fiscal_position[0]
#             else:
#                 if type_vat == 'consumidor':
#                     type_company_ids=type_company_obj.search(cr, uid, [('shortcut','=','NP')])
#                     fiscal_position  = [1]
#                     result['value']['property_account_position']=fiscal_position[0]
#                 elif type_vat == 'ci':
#                     type_company_ids=type_company_obj.search(cr, uid, [('shortcut','=','NP')])
#                     fiscal_position = [1,2]
#                     result['value']['property_account_position']=fiscal_position[0]
#                 else:
#                     fiscal_position =[2,3,4,6,1]
#                     if len(vat)>=12 and vat[4] == '6':
#                         type_company_ids=type_company_obj.search(cr, uid, [('shortcut','=','SC')])
#                         result['value']['property_account_position']=fiscal_position[3]
#                     elif len(vat)>=12 and vat[4] == '9':
#                         type_company_ids=type_company_obj.search(cr, uid, [('shortcut','in',('AC','LC','MC'))])
#                         result['value']['property_account_position']=fiscal_position[1]
#                     else:
#                         type_company_ids=type_company_obj.search(cr, uid, [('shortcut','=','NP')])
#                         result['value']['property_account_position']=fiscal_position[0]
#             result['value']['type_company_id']=type_company_ids and type_company_ids[0] or None
#             result['domain']={'property_account_position':[('id','in',fiscal_position)],'type_company_id':[('id','in',type_company_ids)]}
#         return result
res_partner()

class res_partner_address(osv.osv): 
    _inherit = "res.partner.address"
    
    def _check_address_default(self, cr, uid, ids, context=None):
        """ Checks exist only one address type default.
        @return: True or False
        """
        for address in self.browse(cr, uid, ids, context=context):
            if address.type=='default' and address.partner_id:
                add_ids=self.search(cr, uid, [('type','=','default'),('partner_id','=',address.partner_id.id),('id','not in',tuple(ids))])
                if add_ids:
                    return False
        return True
    
    def _check_number(self,cr,uid,ids):
        for address in self.browse(cr, uid, ids):
            cadena=address['number_sri']
            return method.check_only_number(cadena)
    
    _columns = {
                'number_sri':fields.char('SRI Number', size=3, help='This number is assigned by the SRI by each warehouse'),
                'ag_state': fields.selection([('open', 'Open'),('close', 'Close')],'State', required=True, help="State of Agency"),
                'date':fields.date('Open since'),
                'authorizations_ids':fields.one2many('sri.authorization', 'address_id', 'Authorizations', required=False),
                }
    
    _defaults={'ag_state':'open',
              }

    _sql_constraints = [
        ('number_uniq', 'unique (number_sri,partner_id)',
            'The number of SRI must be unique !'),
    ]
    _constraints =  [(_check_address_default,'Por cada empresa, solo puede existir una dirección tipo',['type']),
                     (_check_number,'Los Punto de Emisión del SRI solo pueden contener números y ser mayores 000.',['number_sri']),
                     ]
    
    def create(self, cr, uid, values, context=None):
        if values.has_key('number_sri'):
            number=values['number_sri']
            values['number_sri'] = method.crear_sufijo(number)
        return super(res_partner_address, self).create(cr, uid, values, context)
        
    def write(self, cr, uid, ids, values, context=None):
        type_printer = False
        if values.has_key('number_sri'):
            number=values['number_sri']
            values['number_sri'] = method.crear_sufijo(number)
        return super(res_partner_address, self).write(cr, uid, ids, values, context)

res_partner_address()