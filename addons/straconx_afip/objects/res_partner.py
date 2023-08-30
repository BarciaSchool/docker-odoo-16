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
                'tax_sustent': fields.many2one('sri.tax.sustent', 'Tax Sustent')}
    _defaults = {'lang': 'es_AR'}

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