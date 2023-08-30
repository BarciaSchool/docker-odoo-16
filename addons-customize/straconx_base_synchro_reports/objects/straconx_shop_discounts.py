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
import re



class invoice_discounts_shops(osv.osv):
    _name= 'reports.discounts.shop'
    _rec_name ='from_date'
    _columns = {
                'report_type':fields.selection([('all', 'Todas las tiendas'), ('this_shop', 'Esta Tienda'), ], 'Seleccionar', select=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                'user_id': fields.many2one('res.users', 'Usuario'),
                'from_date': fields.date('Desde'),
                'to_date': fields.date('Hasta'),
                'lines_discounts_ids':fields.one2many('reports.discounts.shop.line','wizard_id','Cobros'),
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
            if from_date and to_date:
                from_date = from_date
                to_date = to_date
                
            sql=""" 
                select distinct
                round(discount_total,2) as discount,
                round(sum(pos),2) as pos,
                round(sum(credit),2) as credit,
                round(sum(refund),2) as refund,
                round(sum(price_subtotal),2) as total,
                shop_id
                from 
                (select distinct
                ss.id as shop_id, 
                round((100-(((100-discount)*(100-offer))/100)),2) as discount_total,
                (case when ai.type = 'out_invoice' and ai.credit = True and ail.active = True then sum(price_subtotal)
                else 0 end) as credit, 
                (case when ai.type = 'out_invoice' and ai.pos = True and ail.active = True then sum(price_subtotal)
                else 0 end) as pos, 
                (case when ai.type = 'out_refund' and ail.active = True then sum(price_subtotal*-1)
                else 0 end) as refund, 
                (case when ai.type = 'out_invoice' then sum(price_subtotal) else sum(price_subtotal*-1) end) as price_subtotal
                from account_invoice_line ail
                left join account_invoice ai on ai.id = ail.invoice_id
                left join sale_shop ss on ss.id = ai.shop_id
                where 
                ss.id = %s and 
                ai.date_invoice between '%s' and '%s' 
                and ai.type in ('out_invoice','out_refund')
                and ai.state in ('open','paid')
                group by ss.id, discount_total, ai.type, ai.credit, ai.pos, ail.active
                order by ss.id, discount_total) as total
                group by shop_id, discount
                order by shop_id, discount
                """            
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
                        sql = sql%(shop.id,from_date, to_date)
                        conect.execute(sql)
                        discount= 0.00
                        amount_cash= 0.00
                        amount_credit= 0.00
                        amount_untaxed= 0.00

                        il = conect.fetchall()
                        if il:
                            for tp in il:
                                shop_id = tp[5]
                                discount = tp[0]
                                amount_cash= tp[1]
                                amount_credit= tp[2]
                                amount_refund= tp[3]
                                amount_untaxed = tp[4]  
                                
                                cr.execute("""INSERT INTO reports_discounts_shop_line(
                                    shop_id, 
                                    discount,
                                    amount_cash,
                                    amount_credit,
                                    amount_refund,
                                    amount_untaxed,
                                    wizard_id,
                                    create_date,
                                    create_uid)
                                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                                                        (shop.id,
                                                                        discount,
                                                                        amount_cash,
                                                                        amount_credit,
                                                                        amount_refund,                                                                        
                                                                        amount_untaxed,
                                                                        ids[0],
                                                                        date,
                                                                        uid))
                except psycopg2.Error, e:
                    shop_obj.log(cr, uid, shop.id, "La tienda '%s' tiene problemas de conexión. Mensaje del Servidor: %s." % (shop.name, e))
                    pass                        
            return True
                                                                        
    def do_search_discounts(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        cr.execute("""delete from reports_discounts_shop_line where wizard_id = %s""",(ids[0],))
        for rp in self.browse(cr,uid,ids):
            if rp.report_type =='all':
                company_id = self.pool.get('res.company').browse(cr,uid,rp.company_id.id)
                shop_ids = shop_obj.search(cr,uid,[('company_id','=',company_id.id),('emision_point','=',True)])
                if shop_ids:
                    for shop in shop_ids:
                        self.do_shop_conection(cr,uid,ids,shop,rp.from_date, rp.to_date, context)
            elif rp.report_type =='this_shop':
                shop = shop_obj.browse(cr,uid,rp.shop_id.id)
                self.do_shop_conection(cr,uid,ids,shop.id,rp.from_date, rp.to_date, context)
        return True                
invoice_discounts_shops()
    
class invoice_discounts_shops_line(osv.osv):
    _name= 'reports.discounts.shop.line'
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Tienda', readonly=True),
                'discount': fields.float('Descuento'),
                'amount_cash': fields.float('Contado'),
                'amount_credit': fields.float('Crédito'),
                'amount_untaxed': fields.float('Total sin Impuestos'),
                'amount_refund': fields.float('Devoluciones'),
                'wizard_id': fields.many2one('reports.discounts.shop', 'Asistente'),                                
                }
invoice_discounts_shops_line()
    