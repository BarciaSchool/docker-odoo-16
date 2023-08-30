# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution   
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2012-2013 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved
#
##############################################################################

from osv import osv, fields
import re

class salesman_salesman(osv.osv):
    
    def _get_user_data(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        user_obj = self.pool.get('res.users')
        for salesman in self.browse(cr, uid, ids, context=context):
            result[salesman.id] = {}.fromkeys(field_names, False)
            if salesman.user_id:
                user = user_obj.read(cr, uid, salesman.user_id.id, field_names, context=context)
                for field in field_names:
                    result[salesman.id][field] = user[field] or False
        return result
    
    def _set_user_data(self, cr, uid, salesman_id, name, value, arg, context=None):
        salesman = self.browse(cr, uid, salesman_id, context=context)
        if salesman.user_id:
            self.pool.get('res.users').write(cr, uid, [salesman.user_id.id], {name: value or False})
        return True

    _name = 'salesman.salesman'
    _description = 'salesman'
#    _rec_name= 'user_id'
    _rec_name= 'code'
    _columns = {
        'zone_id': fields.many2one('res.region.zone', 'zone', required=True, select=1, ondelete='restrict'),
        'segmento_ids': fields.many2many('res.partner.segmento', 'salesman_segmento_rel', 'salesman_id', 'segmento_id', 'Segmentos',ondelete='restrict'),
        'user_id': fields.many2one('res.users', 'User', required=True, help='The internal user that is in charge of communicating with this partner if any.', ondelete='cascade'),
        'code': fields.char('salesman code', size=16, required=True, select=1),
        'is_buyer': fields.function(_get_user_data, fnct_inv=_set_user_data, type='boolean', relation='res.users', string="Is a Buyer?", multi='user', store=True),
        'is_collector': fields.function(_get_user_data, fnct_inv=_set_user_data, type='boolean', relation='res.users', string="Is a Collector?", multi='user', store=True),
        'is_seller': fields.function(_get_user_data, fnct_inv=_set_user_data, type='boolean', relation='res.users', string="Is a Seller?", multi='user', store=True),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (user_id)',
            'The name of the salesman must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the salesman must be unique !')
    ]


    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        code=None
        zone=False
        salesm=False
        res = []
        for line in self.browse(cr, uid, ids):
            if line.zone_id and line.user_id:
                code = line.code
                zone = line.zone_id.name
                if line.user_id.name:
                    salesm = line.user_id.login
                else:
                    raise osv.except_osv(_('¡Acción Inválida!'), _('El Usuario asignado con el id = %s no existe')%(line.user_id.id))
            salesman_assigned = "%s - %s" %(code, salesm)
            res.append((line['id'], salesman_assigned))
        return res
        
    def onchange_user_id(self, cr, uid, ids, user_id=None, context=None):
        values={}
        if user_id:
            values['is_seller']=self.pool.get('res.users').browse(cr, uid, user_id).is_seller
            values['is_buyer']=self.pool.get('res.users').browse(cr, uid, user_id).is_buyer
            values['is_collector']=self.pool.get('res.users').browse(cr, uid, user_id).is_collector
        return {'value':values}

salesman_salesman()
