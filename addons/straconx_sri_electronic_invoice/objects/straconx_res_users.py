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

from osv import osv, fields



class res_users(osv.osv):
    _inherit = 'res.users'

    def cron_create_users(self, cr, uid, context=None):
        ir_attachment = self.pool.get('ir.attachment')
        cr.execute("""select distinct ia.partner_id from ir_attachment ia
                    left join res_users ru on ru.partner_id = ia.partner_id 
                    where ia.electronic=True and ia.active = True
                    and (ia.partner_id <> ru.partner_id or ru.partner_id is null)""")
        send_ids = cr.fetchall()
        context=({'direct':True})
        partner_obj = self.pool.get('res.partner')
        
        if send_ids:
            for att_id in send_ids:
                try:
                    partner_id = partner_obj.browse(cr,uid,att_id[0])
                    if partner_id:
                        vat = partner_id.vat[2:]
                    if vat: 
                        user_id = self.pool.get('res.users').search(cr,uid,[('login','=',vat)])
                        if not user_id:
                            self.pool.get('res.portal.wizard').action_create(cr,uid,att_id[0],context)
                except:
                    continue
        return True
 
res_users()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
