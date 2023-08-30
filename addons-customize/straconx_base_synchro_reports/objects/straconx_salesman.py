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

from osv import fields, osv
from tools.translate import _
from datetime import datetime
import time
import decimal_precision as dp
import psycopg2


class salesman_shops(osv.osv):
    _name= 'reports.salesman.shop'
    _rec_name ='from_date'
    _columns = {
                'report_type':fields.selection([('all', 'Todas las tiendas'), ('this_shop', 'Esta Tienda'), ], 'Seleccionar', select=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                'user_id': fields.many2one('res.users', 'Usuario'),
                'from_date': fields.date('Desde'),
                'to_date': fields.date('Hasta'),
                'lines_invoice_ids':fields.one2many('reports.invoice.salesman.line','wizard_id','Vendedor'),
                }

    _defaults={
        'user_id': lambda obj, cr, uid, context: uid,
        'from_date':lambda *a: time.strftime('%Y-%m-%d'),
        'to_date':lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        'report_type':'all'
    }

    def do_shop_conection(self, cr, uid, ids, shop_id,from_date, to_date, context=None):
            shop_obj = self.pool.get('sale.shop')
            shop = shop_obj.browse(cr,uid,shop_id)
            salesman_obj = self.pool.get('salesman.salesman')
            sql="""select ss.id,
                    coalesce((select sum(x.price_subtotal*x.coeff)  as price_subtotal from 
                    (select ru.login as login, ail.salesman_id as salesman, ai.shop_id as shop_id, 1.0 as coeff, sum(ail.price_subtotal) as price_subtotal
                    from account_invoice_line ail
                    left join account_invoice ai on ai.id = ail.invoice_id
                    left join salesman_salesman ssa on ssa.id = ail.salesman_id
                    left join sale_shop ssl on ssl.id = ai.shop_id
                    left join res_users ru on ru.id = ssa.user_id
                    where 
                    ai.type in ('out_invoice')
                    and ssl.id = %s
                    and ssa.id = ss.id
                    and ai.state in ('open','paid')
                    and ai.date_invoice between %s and %s                    
                    group by ru.login , ail.salesman_id, ai.shop_id
                    union 
                    select ru.login as login, ail.salesman_id as salesman, ai.shop_id as shop_id, -1.0 as coeff, sum(ail.price_subtotal) as price_subtotal
                    from account_invoice_line ail
                    left join account_invoice ai on ai.id = ail.invoice_id
                    left join salesman_salesman ssa on ssa.id = ail.salesman_id
                    left join sale_shop ssl on ssl.id = ai.shop_id
                    left join res_users ru on ru.id = ssa.user_id
                    where 
                    ai.type in ('out_refund')
                    and ssl.id = %s
                    and ssa.id = ss.id
                    and ai.state in ('open','paid')
                    and ai.date_invoice between %s and %s
                    group by ru.login , ail.salesman_id, ai.shop_id
                    ) as x),0) as subtotal_invoice
                    from salesman_salesman ss
                    left join res_users ru on ru.id = ss.user_id
                    order by subtotal_invoice desc"""
            
            if shop:          
                database = shop_obj.browse(cr,uid,shop.id).server_db
                port = shop_obj.browse(cr,uid,shop.id).server_port
                host = shop_obj.browse(cr,uid,shop.id).server_url
                user = shop_obj.browse(cr,uid,shop.id).login
                password= shop_obj.browse(cr,uid,shop.id).password
                date = time.strftime('%Y-%m-%d %H:%M:%S')                
                if not database or not port or not host or not user or not password:
                    raise osv.except_osv('Error!', _("La tienda %s no tiene configurada toda la información de conexión.")%(shop.name))
                try:
                    conection = psycopg2.connect(database=database, user=user, password=password, host=host, port=port, options='-c statement_timeout=15s')
                    if conection:
                        conect = conection.cursor()
                        conect.execute(sql,(shop.id,from_date, to_date,shop.id,from_date, to_date))
                        il_ids = conect.fetchall()
                        if il_ids:
                            for il in il_ids:
                                cr.execute("""INSERT INTO reports_invoice_salesman_line(shop_id,salesman_id, amount_untaxed_s, wizard_id, create_date, create_uid)
                                values(%s,%s,%s,%s,%s,%s)""",(shop_id, il[0],il[1],ids[0],date,uid))
                except psycopg2.Error, e:
                    pass                        
            return True
                                                                        
    def do_search_invoices(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        cr.execute("""delete from reports_invoice_salesman_line where wizard_id = %s""",(ids[0],))
        for rp in self.browse(cr,uid,ids):
            if rp.report_type =='all':
                company_id = self.pool.get('res.company').browse(cr,uid,rp.company_id.id)
                shop_ids = shop_obj.search(cr,uid,[('company_id','=',company_id.id)])
                if shop_ids:
                    for shop in shop_ids:
                        self.do_shop_conection(cr,uid,ids,shop,rp.from_date, rp.to_date, context)
            elif rp.report_type =='this_shop':
                shop = shop_obj.browse(cr,uid,rp.shop_id.id)
                self.do_shop_conection(cr,uid,ids,shop.id,rp.from_date, rp.to_date, context)
        return True                
salesman_shops()
    
class reports_invoice_salesman_line(osv.osv):
    _name= 'reports.invoice.salesman.line'
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Tienda', readonly=True),
                'salesman_id': fields.many2one('salesman.salesman', 'Vendedor', readonly=True),
                'quantity': fields.integer('Cantidad'),
                'amount_untaxed_s': fields.float('Base Imponible'),
                'amount_total_vat_s': fields.float('Impuestos'),
                'amount_total_s': fields.float('Valor total'),
                'residual_s': fields.float('Pendiente'),
                'wizard_id': fields.many2one('reports.salesman.shop', 'Asistente'),                                
                }
reports_invoice_salesman_line()
    