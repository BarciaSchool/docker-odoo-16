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



class invoice_payments_shops(osv.osv):
    _name= 'reports.payments.shop'
    _rec_name ='from_date'
    _columns = {
                'report_type':fields.selection([('all', 'Todas las tiendas'), ('this_shop', 'Esta Tienda'), ], 'Seleccionar', select=True),
                'shop_id': fields.many2one('sale.shop', 'Tienda'),
                'company_id': fields.many2one('res.company', 'Compañía'),
                'user_id': fields.many2one('res.users', 'Usuario'),
                'from_date': fields.date('Desde'),
                'to_date': fields.date('Hasta'),
                'lines_payments_ids':fields.one2many('reports.payments.shop.line','wizard_id','Cobros'),
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
                from_date = from_date +" 00:00:00"
                to_date = to_date  + " 23:59:59"
                
            sql=""" 
                select distinct on (pm.name)
                pm.name,
                coalesce((select sum(absl.amount) from account_bank_statement_line absl
                left join account_payments ap on absl.payment_id = ap.id
                left join account_bank_statement abs on abs.id = absl.statement_id
                left join payment_mode pmi on (pmi.id = ap.mode_id)
                where pm.id = pmi.id 
                and abs.shop_id = %s
                and absl.active = True
                and abs.date between '%s' and '%s'
                and absl.type='customer'
                ),0),
                coalesce((select sum(absl.amount) from account_bank_statement_line absl
                left join account_payments ap on absl.payment_id = ap.id
                left join account_bank_statement abs on abs.id = absl.statement_id
                left join payment_mode pmi on (pmi.id = ap.mode_id)
                left join printer_point pp on (pp.id = abs.printer_id)
                where pm.id = pmi.id 
                and abs.shop_id = %s
                and abs.date between '%s' and '%s'
                and absl.type='supplier'
                and absl.active = True
                and (pp.type = False or pp.type is Null)
                ),0),
                coalesce((select sum(absl.amount) from account_bank_statement_line absl
                left join account_payments ap on absl.payment_id = ap.id
                left join account_bank_statement abs on abs.id = absl.statement_id
                left join payment_mode pmi on (pmi.id = ap.mode_id)
                left join printer_point pp on (pp.id = abs.printer_id)
                where pm.id = pmi.id 
                and abs.shop_id = %s
                and abs.date between '%s' and '%s'
                and absl.active = True
                and absl.type='supplier'
                and pp.type = True
                ),0)

                from payment_mode pm
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
                        sql = sql%(shop.id,from_date, to_date,shop.id,from_date, to_date,shop.id,from_date, to_date)
                        conect.execute(sql)
                        cash=0.00
                        credit_card=0.00
                        day_check=0.00
                        date_check=0.00
                        bank_deposit=0.00                               
                        credit_notes=0.00
                        employee_discount=0.00
                        withholds=0.00                    
                        others=0.00
                        expenses=0.00
                        petty = 0.00
                        total_incomes=0.00
                        total_expenses=0.00
                        total=0.00

                        il = conect.fetchall()
                        if il:
                            for tp in il:
                                if re.search("(EFECTIVO.*)", tp[0]):
                                    cash += tp[1]
                                    expenses += tp[2]
                                elif tp[0] =='TARJETA DE CRÉDITO':
                                    credit_card+= tp[1]
                                elif tp[0] == 'CHEQUE AL DIA':
                                    day_check+= tp[1]
                                elif tp[0] == 'CHEQUE A FECHA':
                                    date_check+= tp[1]
                                elif re.search("(DEPOSITO.*)", tp[0]):
                                    bank_deposit+= tp[1]
                                elif tp[0] == 'NOTA DE CREDITO':                               
                                    credit_notes+= tp[1]
                                elif tp[0] == 'DESCUENTO COLABORADOR':
                                    employee_discount+= tp[1]
                                elif re.search("(RETENCI.*)", tp[0]):                                      
                                    withholds+= tp[1]     
                                else:               
                                    others+= tp[1]
                                    expenses += tp[3]
                                    petty += tp[2]
                                total_incomes += tp[1]
                                total_expenses += (tp[2]+tp[3]) 
                            total = total_incomes - total_expenses
                            cr.execute("""INSERT INTO reports_payments_shop_line(shop_id, 
                                cash,
                                credit_card,
                                day_check,
                                date_check,
                                bank_deposit,                                 
                                credit_notes, 
                                employee_discount,
                                withholds,                                
                                others, 
                                total_incomes,
                                petty,
                                expenses,
                                total_expenses,
                                total,
                                wizard_id,
                                create_date,
                                create_uid)
                                values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                                                    (shop.id,
                                                                    cash,
                                                                    credit_card,
                                                                    day_check,
                                                                    date_check,
                                                                    bank_deposit,                                 
                                                                    credit_notes, 
                                                                    employee_discount,
                                                                    withholds,                                
                                                                    others, 
                                                                    total_incomes,
                                                                    petty,
                                                                    expenses,
                                                                    total_expenses,
                                                                    total,
                                                                    ids[0],
                                                                    date,
                                                                    uid))
                except psycopg2.Error, e:
                    shop_obj.log(cr, uid, shop.id, "La tienda '%s' tiene problemas de conexión. Mensaje del Servidor: %s." % (shop.name, e))
                    pass                        
            return True
                                                                        
    def do_search_payments(self, cr, uid, ids, context=None):
        shop_obj = self.pool.get('sale.shop')
        cr.execute("""delete from reports_payments_shop_line where wizard_id = %s""",(ids[0],))
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
invoice_payments_shops()
    
class invoice_payments_shops_line(osv.osv):
    _name= 'reports.payments.shop.line'
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Tienda', readonly=True),
                'cash': fields.float('Efectivo'),
                'credit_card': fields.float('T/Crédito'),
                'day_check': fields.float('Cheque al día'),
                'date_check': fields.float('Cheque a fecha'),
                'employee_discount': fields.float('Desc. Empleados'),
                'credit_notes': fields.float('Nota de Crédito'),
                'bank_deposit': fields.float('Depósito Bancario'),
                'withholds': fields.float('Retenciones'),
                'others': fields.float('Otros'),
                'total_incomes': fields.float('Total Ingresos'),
                'petty': fields.float('(Caja Chica)'),
                'expenses': fields.float('(Egresos)'),
                'total_expenses': fields.float('Total Egresos'),
                'total': fields.float('Neto'),
                'wizard_id': fields.many2one('reports.payments.shop', 'Asistente'),                                
                }
invoice_payments_shops_line()
    