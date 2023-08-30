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



class shop_id_data(osv.osv):
    _inherit = 'sale.shop'
        
    _columns = {
                'server_url': fields.char('Server URL', size=64,required=True),
                'server_port': fields.integer('Server Port', size=64,required=True),
                'server_db': fields.char('Server Database', size=64,required=True),
                'login': fields.char('User Name',size=50,required=True),
                'password': fields.char('Password',size=64,required=True),
                'last_synchro': fields.datetime('Process Date'),
            }
    
shop_id_data()

class invoice_shops(osv.osv):
    _name= 'reports.invoice.shop'
    _rec_name ='from_date'
    _columns = {
                'report_type':fields.selection([('all', 'Todas las tiendas'), ('this_shop', 'Esta Tienda'), ], 'Seleccionar', select=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                'user_id': fields.many2one('res.users', 'Usuario'),
                'from_date': fields.date('Desde'),
                'to_date': fields.date('Hasta'),
                'lines_invoice_ids':fields.one2many('reports.invoice.shop.line','wizard_id','Facturas'),
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
#            sql = """select shop_id, count(id), sum(amount_untaxed_s), sum(amount_total_vat_s), sum(amount_total_s),sum(residual_s) from account_invoice where shop_id = %s and date_invoice >=%s and date_invoice <= %s and type in ('out_invoice','out_refund') and state in ('open','paid') group by shop_id"""
            sql="""select distinct shop_id, 
                (select count(id) from account_invoice where type in ('out_refund','out_invoice') 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as id, 
                (select coalesce(sum(amount_untaxed),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid')) - 
                (select coalesce(sum(amount_untaxed),0) from account_invoice where type='out_refund' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as amount_untaxed,
                (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid')) - 
                (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_refund' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as amount_total_vat,
                (select coalesce(sum(amount_total),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid')) - 
                (select coalesce(sum(amount_total),0) from account_invoice where type='out_refund' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as amount_total,
                (select coalesce(sum(residual),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid')) - 
                (select coalesce(sum(residual),0) from account_invoice where type='out_refund' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as residual
                from account_invoice where shop_id = %s"""
            
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
                        conect.execute(sql,(shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id))
                        il = conect.fetchall()
                        if il:
                            cr.execute("""INSERT INTO reports_invoice_shop_line(shop_id, quantity, amount_untaxed_s, amount_total_vat_s, amount_total_s, residual_s, wizard_id, create_date, create_uid)
                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(il[0][0],il[0][1],il[0][2],il[0][3],il[0][4],il[0][5],ids[0],date,uid))
                except psycopg2.Error, e:
                    pass                        
            return True
                                                                        
    def do_search_invoices(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        cr.execute("""delete from reports_invoice_shop_line where wizard_id = %s""",(ids[0],))
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
invoice_shops()
    
class reports_invoice_shop_line(osv.osv):
    _name= 'reports.invoice.shop.line'
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Tienda', readonly=True),
                'quantity': fields.integer('Cantidad'),
                'amount_untaxed_s': fields.float('Base Imponible'),
                'amount_total_vat_s': fields.float('Impuestos'),
                'amount_total_s': fields.float('Valor total'),
                'residual_s': fields.float('Pendiente'),
                'wizard_id': fields.many2one('reports.invoice.shop', 'Asistente'),                                
                }
reports_invoice_shop_line()
    




class invoice_shops_reports(osv.osv):
    _name= 'reports.invoice.shop.type'
    _rec_name ='from_date'
    _columns = {
                'report_type':fields.selection([('all', 'Todas las tiendas'), ('this_shop', 'Esta Tienda'), ], 'Seleccionar', select=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                'user_id': fields.many2one('res.users', 'Usuario'),
                'from_date': fields.date('Desde'),
                'to_date': fields.date('Hasta'),
                'lines_invoice_ids':fields.one2many('reports.invoice.shop.line.type','wizard_id','Facturas'),
                }

    _defaults={
        'user_id': lambda obj, cr, uid, context: uid,
        'from_date':lambda *a: time.strftime('%Y-%m-%d'),
        'to_date':lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        'report_type':'all'
    }

    def do_shop_conection(self, cr, uid, ids, shop_id,from_date, to_date,context=None):
            shop_obj = self.pool.get('sale.shop')
            shop = shop_obj.browse(cr,uid,shop_id)            
            types = ['pre_printer','automatic','electronic']
            if shop:          
                database = shop_obj.browse(cr,uid,shop.id).server_db
                port = shop_obj.browse(cr,uid,shop.id).server_port
                host = shop_obj.browse(cr,uid,shop.id).server_url
                user = shop_obj.browse(cr,uid,shop.id).login
                password= shop_obj.browse(cr,uid,shop.id).password
                date = time.strftime('%Y-%m-%d %H:%M:%S') 
#            sql = """select shop_id, count(id), sum(amount_untaxed_s), sum(amount_total_vat_s), sum(amount_total_s),sum(residual_s) from account_invoice where shop_id = %s and date_invoice >=%s and date_invoice <= %s and type in ('out_invoice','out_refund') and state in ('open','paid') group by shop_id"""
            for type in types:                
                if type == 'pre_printer':
                    sql="""select distinct shop_id, 
                    (select count(id) from account_invoice where type in ('out_refund','out_invoice') 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True)
                    as id,
                    (select coalesce(sum(amount_base_vat_00),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True) - 
                    (select coalesce(sum(amount_base_vat_00),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True)
                    as amount_base_vat_00,
                    (select coalesce(sum(amount_base_vat_12),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True) - 
                    (select coalesce(sum(amount_base_vat_12),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True)
                    as amount_base_vat_12,
                    (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and  pre_printer = True) - 
                    (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True)
                    as amount_total_vat,
                    (select coalesce(sum(amount_total),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True) - 
                    (select coalesce(sum(amount_total),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and pre_printer = True)
                    as amount_total
                    from account_invoice where shop_id = %s"""
                    tipo = "Preimpreso"
                elif type == 'automatic':
                    sql="""select distinct shop_id, 
                    (select count(id) from account_invoice where type in ('out_refund','out_invoice') 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True)
                    as id,
                    (select coalesce(sum(amount_base_vat_00),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True) - 
                    (select coalesce(sum(amount_base_vat_00),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True)
                    as amount_base_vat_00,
                    (select coalesce(sum(amount_base_vat_12),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True) - 
                    (select coalesce(sum(amount_base_vat_12),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True)
                    as amount_base_vat_12,
                    (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and  automatic = True) - 
                    (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True)
                    as amount_total_vat,
                    (select coalesce(sum(amount_total),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True) - 
                    (select coalesce(sum(amount_total),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and automatic = True)
                    as amount_total
                    from account_invoice where shop_id = %s"""
                    tipo = "Autoimpreso"
                else:
                    sql="""select distinct shop_id, 
                    (select count(id) from account_invoice where type in ('out_refund','out_invoice') 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True)
                    as id,
                    (select coalesce(sum(amount_base_vat_00),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True) - 
                    (select coalesce(sum(amount_base_vat_00),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True)
                    as amount_base_vat_00,
                    (select coalesce(sum(amount_base_vat_12),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True) - 
                    (select coalesce(sum(amount_base_vat_12),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True)
                    as amount_base_vat_12,
                    (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and  electronic = True) - 
                    (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True)
                    as amount_total_vat,
                    (select coalesce(sum(amount_total),0) from account_invoice where type='out_invoice' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True) - 
                    (select coalesce(sum(amount_total),0) from account_invoice where type='out_refund' 
                    and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                    and state in ('open','paid') and electronic = True)
                    as amount_total
                    from account_invoice where shop_id = %s"""
                    tipo = "Electrónico"  
                
                if not database or not port or not host or not user or not password:
                    raise osv.except_osv('Error!', _("La tienda %s no tiene configurada toda la información de conexión.")%(shop.name))
                try:
                    conection = psycopg2.connect(database=database, user=user, password=password, host=host, port=port, options='-c statement_timeout=15s')
                    if conection:
                        conect = conection.cursor()
                        conect.execute(sql,(shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id))
                        il = conect.fetchall()
                        if il:
                            cr.execute("""INSERT INTO reports_invoice_shop_line_type(shop_id,type, quantity, amount_base_vat_00,amount_base_vat_12, amount_total_vat_s, amount_total_s, wizard_id, create_date, create_uid)
                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(il[0][0],tipo,il[0][1],il[0][2],il[0][3],il[0][4],il[0][5],ids[0],date,uid))
                except psycopg2.Error, e:
                    print e
                    pass                        
            return True
                                                                        
    def do_search_invoices_report(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        cr.execute("""delete from reports_invoice_shop_line where wizard_id = %s""",(ids[0],))
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
invoice_shops_reports()


class reports_invoice_shop_line_type(osv.osv):
    _name= 'reports.invoice.shop.line.type'
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Tienda', readonly=True),
                'type': fields.char('Tipo',size=15),
                'quantity': fields.integer('Cantidad'),
                'amount_base_vat_00': fields.float('Base 0%'),
                'amount_base_vat_12': fields.float('Base 12%'),
                'amount_total_vat_s': fields.float('Impuestos'),
                'amount_total_s': fields.float('Valor total'),
                'wizard_id': fields.many2one('reports.invoice.shop.type', 'Asistente'),                                
                }
reports_invoice_shop_line_type()



class invoice_shop_resumen(osv.osv):
    _name= 'invoice.shop.resumen'
    _rec_name ='from_date'
    _columns = {
                'report_type':fields.selection([('all', 'Todas las tiendas'), ('this_shop', 'Esta Tienda'), ], 'Seleccionar', select=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                'user_id': fields.many2one('res.users', 'Usuario'),
                'from_date': fields.date('Desde'),
                'to_date': fields.date('Hasta'),
                'lines_ids':fields.one2many('invoice.shop.resumen.line','wizard_id','Facturas'),
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
#            sql = """select shop_id, count(id), sum(amount_untaxed_s), sum(amount_total_vat_s), sum(amount_total_s),sum(residual_s) from account_invoice where shop_id = %s and date_invoice >=%s and date_invoice <= %s and type in ('out_invoice','out_refund') and state in ('open','paid') group by shop_id"""
            sql="""select distinct shop_id, 
                (select count(id) from account_invoice where type in ('out_invoice') 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as id, 
                (select coalesce(sum(amount_untaxed),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as amount_untaxed,
                (select coalesce(sum(amount_total_vat),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as amount_total_vat,
                (select coalesce(sum(amount_total),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as amount_total,
                (select coalesce(sum(residual),0) from account_invoice where type='out_invoice' 
                and shop_id = %s and date_invoice >=%s and date_invoice <= %s 
                and state in ('open','paid'))
                as residual
                from account_invoice where shop_id = %s"""
            
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
                        conect.execute(sql,(shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id))
                        il = conect.fetchall()
                        if il:
                            cr.execute("""INSERT INTO invoice_shop_resumen_line(shop_id, quantity, amount_untaxed_s, amount_total_vat_s, amount_total_s, residual_s, wizard_id, create_date, create_uid)
                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(il[0][0],il[0][1],il[0][2],il[0][3],il[0][4],il[0][5],ids[0],date,uid))
                except psycopg2.Error, e:
                    pass                        
            return True
                                                                        
    def do_search_invoices(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        cr.execute("""delete from reports_invoice_shop_line where wizard_id = %s""",(ids[0],))
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
invoice_shop_resumen()
    
class invoice_shop_resumen_line(osv.osv):
    _name= 'invoice.shop.resumen.line'
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Tienda', readonly=True),
                'quantity': fields.integer('Cantidad'),
                'amount_untaxed_s': fields.float('Base Imponible'),
                'amount_total_vat_s': fields.float('Impuestos'),
                'amount_total_s': fields.float('Valor total'),
                'residual_s': fields.float('Pendiente'),
                'wizard_id': fields.many2one('invoice.shop.resumen', 'Asistente'),                                
                }
invoice_shop_resumen_line()
    