# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
##############################################################################

from osv import osv
from tools.translate import _


class out_mail(osv.osv_memory):
    _name = "out.mail"
    
    def send_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            raise osv.except_osv('Error!', _("No hay conexión con la Tienda de Destino, por favor guarde el registro e intente en unos minutos."))
        else:
            name = context.get('name',None)
            picking = self.pool.get(context.get('active_model')).browse(cr , uid, context.get('active_id',None))        
            action_id = self.pool.get('ir.actions.server').search(cr, uid, [('name','=',name)])
            data = self.pool.get('ir.actions.server').run(cr, uid, action_id, context)
            note = picking.note or ''
            note += '\n correo enviado a la tienda %s, usuario %s'%(picking.shop_id.name,picking.shop_id.logistics_stock.name)
            picking.write({'note':note})
            return {'type': 'ir.actions.act_window_close'}
    
out_mail()