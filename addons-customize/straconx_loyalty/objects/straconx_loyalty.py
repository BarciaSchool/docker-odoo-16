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

class sales_loyalty(osv.osv):

    _name = "sales.loyalty"
    _columns = {                
        'name': fields.char('Name', size=30, help='Un nombre indicativo de la promoción'),
        'active': fields.boolean('Activo'),
        'date_from': fields.date('Desde', help='La fecha desde que será válida la emisión de bonos de la promoción'),
        'date_to': fields.date('Hasta', help='La fecha hasta que será válida la emisión de bonos de la promoción'),
        'date_expired': fields.date('Fecha límite para redimir el bono', help='La fecha hasta que será válida el redimir los bonos de la promoción'),
        'days': fields.integer('Días de validez del bono', help='Los días en que el cliente podrá acceder al premio'),
        'days_start': fields.integer('Días que deben transcurrir', help='Los días que deben transcurrir para empezar a cobrar el premio'),
        'maximun_pay': fields.integer('% Pago Máximo', help='El monto de pago máximo que el cliente podrá realizar con los bonos. Si es 100%, aplica a todo el pago.'),
        'penalization': fields.float('% Penalización', digits_compute=dp.get_precision('Account'), help="El porcentaje de penalización en caso de descuentos u ofertas."),
        'acumuled': fields.boolean('Acumulado', help="Define si el valor a redimir es acumulado o sobre lo que tiene el cliente"),
        'loyalty_ids':fields.one2many('sales.loyalty.line', 'wizard_id', 'Lines', required=False),
        'company_id': fields.many2one('res.company','Compañía')
        }
    
    _defaults = {
        'active': True,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'sales.loyalty', context=c),
                 }
    
    def expired_process_all(self, cr, uid, context=None):
        camp_obj = self.pool.get('sales.loyalty')
        review_date = time.strftime('%Y-%m-%d')
        camp_ids = camp_obj.search(cr, uid, [('active','=',True)], context=context)
        for camp in camp_obj.browse(cr, uid, camp_ids, context=context):
            if camp.date_to < review_date:
                camp.write({'active':False,})
                if camp.loyalty_ids:
                    for lid in camp.loyalty_ids:
                        lid.write(cr,uid,lid.id,{'active':False})
        return True

sales_loyalty()


class sales_loyalty_line(osv.osv):

    _name = "sales.loyalty.line"
    _columns = {                
        'mode_id': fields.selection([
            ('cash','Efectivo'),
            ('credit_card','Tarjeta de Crédito'),
            ('check','Cheques'),
            ('deposit','Depósito'),
            ('credit_note','Nota de Crédito'),
            ],'Modo', select=True, change_default=True),
        'active': fields.boolean('Activo'),
        'from_amount': fields.float('Desde', digits_compute=dp.get_precision('Account')),
        'to_amount': fields.float('Hasta', digits_compute=dp.get_precision('Account')),
        'bank_id': fields.many2one('res.bank','Banco'),
        'bonus': fields.float('% Bono', digits_compute=dp.get_precision('Account')),
        'wizard_id':fields.many2one('sales.loyalty','Wizard')
        }
    
    _defaults = {
        'active': True,
        }
    
sales_loyalty_line()