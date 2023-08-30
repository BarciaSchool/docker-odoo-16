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
from tools.translate import _
import netsvc
import binascii
import os
import uuid
from string import upper


# TODO:
# Añadir en payments los pagos en diferidos.
# Añadir la penalidad para las Notas de Crédito.
# Añadir un reporte de Estado de Cliente.
# Añádir un reporte de Costo de Promoción.
# Cada vez que se genere el pago, debe indicar cuánto es. 
# Crear dos cron: a) Expira la promoción, b) Expira las líneas del cliente, c) Correo electrónico par el cliente.    

class sales_partner(osv.osv):

    def amount_bonus(self, cr, uid, ids, name, args, context=None):
        res = {}
        expired_bonus = 0.00
        received_bonus = 0.00
        redeem_bonus = 0.00
        saldo = 0.00
        actual_bonus = 0.00
        total_invoices = 0.00
        minimun_purchase = 0.00
        bonus_ids = False
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
        for datas in self.browse(cr, uid, ids, context=context):
            res[datas.id] = {
                'received_bonus':received_bonus,
                'redeem_bonus':redeem_bonus,
                'expired_bonus': expired_bonus,
                'actual_bonus': actual_bonus,
                'total_invoices': total_invoices
            }
            
            partner_id = datas.partner_id.id
            
            if partner_id:
                bon_ids = self.pool.get('sales.loyalty.partner.line').search(cr,uid,[('partner_id','=',partner_id),('active','=',True)])
                bonus_ids = self.pool.get('sales.loyalty.partner.line').browse(cr,uid,bon_ids)

            for line in bonus_ids:
                if line.state=='expired':                    
                    expired_bonus += round((line.bonus),di)
                if line.type=='add' and line.active and line.state=='pending':                
                    received_bonus += round((line.bonus),di)
                if line.type=='subtract' and line.active and line.state=='redimed':
                    redeem_bonus += round((line.bonus),di)  
                if line.amount_invoice:
                    total_invoices += round((line.amount_invoice),di)
                if line.type=='add' and line.active and line.state=='pending':                
                    saldo += round((line.pending),di)

                                     
            actual_bonus = received_bonus - expired_bonus -  redeem_bonus
            actual_bonus = saldo     
            if actual_bonus>0:
                minimun_purchase = round(actual_bonus/0.30,2)
                if minimun_purchase < 20.00:
                    minimun_purchase = 20.00
                       
            res[datas.id] = {
                'received_bonus':received_bonus,
                'redeem_bonus':redeem_bonus,
                'expired_bonus': expired_bonus,
                'actual_bonus': actual_bonus,
                'total_invoices': total_invoices,
                'minimun_purchase': minimun_purchase
            }        
        return res
        
    _name = "sales.loyalty.partner"
    _columns = {                
        'name': fields.char('Código', size=15, help='Un nombre indicativo de la promoción'),
        'vat': fields.related('partner_id','vat',type="char", relation="res.partner", string="Identificación", store=True),
        'active': fields.boolean('Activo'),
        'partner_id': fields.many2one('res.partner','Cliente'),        
        'date_from': fields.date('Desde',help='La fecha desde cuando quiere consultar'),
        'date_to': fields.date('Hasta',help='La fecha hasta donde quiere consultar'),
        'total_invoices': fields.function(amount_bonus, method=True, digits_compute=dp.get_precision('Account'), string='Total Documentos', multi='vat_amount', help='El bono que ha acumulado'),
        'received_bonus': fields.function(amount_bonus, method=True, digits_compute=dp.get_precision('Account'), string='Bono acumulado', multi='vat_amount', help='El bono que ha acumulado'),
        'redeem_bonus': fields.function(amount_bonus, method=True, digits_compute=dp.get_precision('Account'), string='Bono Redimindo', multi='vat_amount', help='El valor de bonos que ha redimido'),
        'expired_bonus': fields.function(amount_bonus, method=True, digits_compute=dp.get_precision('Account'), string='Bono Expirado', multi='vat_amount', help='El valor de bonos que ha expirado'),
        'actual_bonus': fields.function(amount_bonus, method=True, digits_compute=dp.get_precision('Account'), string='Saldo', multi='vat_amount', help='El saldo de bonos que puede utilizar', store=True),        
        'minimun_purchase': fields.function(amount_bonus, method=True, digits_compute=dp.get_precision('Account'), string='Compra Mínima', multi='vat_amount', help='El saldo de bonos que puede utilizar', store=True),
        'bonus_ids':fields.one2many('sales.loyalty.partner.line', 'partner_id', 'Lines'),
        'company_id': fields.many2one('res.company','Compañía'),       
        'email_send': fields.boolean('Email send?'),
        }
    
    _defaults = {
        'email_send': False,
        'active': True,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'sales.loyalty', context=c),
        'date_from': '2010-01-01 00:00:00',        
        'date_to':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 }
        
    def unlink(self, cr, uid, vals, context={}):
        raise osv.except_osv(_('¡Acción Inválida!'), _('NO se puede eliminar un cliente que tiene Bonos en cualquier estado.'))

    def create(self, cr, uid, vals, context={}):
        partner_id = vals.get('partner_id')
        if partner_id:
            confirm = self.search(cr,uid,[('partner_id','=',partner_id)])
            if confirm:
                #raise osv.except_osv(_('¡Acción Inválida!'), _('NO debe presionar GRABAR en clientes con códigos asignados. Solo tiene que CERRAR la ventana para continuar.'))
                return confirm[-1]        
        return super(sales_partner, self).create(cr, uid, vals, context)
    
#     def write(self, cr, uid, ids, vals, context={}):
#         return True
                         
    def onchange_date(self, cr, uid, ids, date_from, date_to, partner_id=False, vat=None, loyalty_card = None, context=None):
        loyalty_obj = self.pool.get('sales.loyalty.partner.line')
        partner_obj = self.pool.get('res.partner')
        di = self.pool.get('decimal.precision').precision_get(cr, 1, 'Account')
        loyalty_ids = []
        expired_bonus = 0.00
        received_bonus = 0.00
        redeem_bonus = 0.00
        actual_bonus = 0.00
        saldo = 0.00
        total_invoices = 0.00
        minimun_purchase = 0.00
        res={}
        if context is None: 
            context = {}
        if not (date_from and date_to):
            return res
        if date_to < date_from:
            raise osv.except_osv(_("Error"),_("To data is greater to from date."))
        if vat and not partner_id:
            if vat[:2] not in ('EC','ec','PA','pa'):
                vat='EC'+vat
            else:
                vat = upper(vat)
            partner_ids = partner_obj.search(cr,uid,[('vat','=',vat)])
            if partner_ids:
                partner_id = partner_ids[0]
            else:
                raise osv.except_osv(_('¡Acción Inválida!'), _('El cliente no existe en nuestra base de datos.'))
        if loyalty_card and not partner_id:
            partner_ids = partner_obj.search(cr,uid,[('loyalty_card','=',loyalty_card)])
            if partner_ids:
                partner_id = partner_ids[0]
        if partner_id:
            partner_id = partner_obj.browse(cr,uid,partner_id)
            vat = partner_id.vat
            loyalty_card = partner_id.loyalty_card
            if not loyalty_card:
                raise osv.except_osv(_('¡Acción Inválida!'), _('El cliente no ha realizado movimientos en el período que generen una Tarjeta Promocional.')) 
            loyalty_ids = loyalty_obj.search(cr, uid,[('partner_id','=',partner_id.id),('date','>=',date_from),('date','<=',date_to),('active','=',True)])
            if loyalty_ids:
                lines = loyalty_obj.browse(cr,uid,loyalty_ids)
                for line in lines: 
                    if line.state=='expired':                    
                        expired_bonus += round((line.bonus),di)
                    if line.type=='add' and line.active and line.state=='pending':                
                        received_bonus += round((line.bonus),di)
                    if line.type=='subtract' and line.active and line.state=='redimed':
                        redeem_bonus += round((line.bonus),di)  
                    if line.amount_invoice:
                        total_invoices += round((line.amount_invoice),di)
                    if line.type=='add' and line.active and line.state=='pending':                
                        saldo += round((line.pending),di)
                                 
                actual_bonus = received_bonus - expired_bonus -  redeem_bonus        
                actual_bonus = saldo         
                minimun_purchase = round(saldo/0.3,2)
            res['bonus_ids']=loyalty_ids
            res['partner_id']=partner_id.id
            res['vat']=vat
            res['name']=loyalty_card
            res['received_bonus']=received_bonus
            res['redeem_bonus']=redeem_bonus
            res['expired_bonus']= expired_bonus
            res['actual_bonus']=actual_bonus
            res['total_invoices']=total_invoices
            res['minimun_purchase']=minimun_purchase
#             cr.update('update sales_loyalty_partner set write_date=now(), actual_bonus=%s,minimun_purchase=%s where id=%s',(actual_bonus,minimun_purchase,ids[0]))
            cr.commit()
        return {'value':res}        
sales_partner()


class sales_partner_line(osv.osv):

    _name = "sales.loyalty.partner.line"
    _columns = {                
        'type': fields.selection([
            ('add','+'),
            ('subtract','-'),
            ],'Tipo'),
        'mode_id': fields.selection([
            ('input','Entrada'),
            ('output','Salida'),
            ],'Modo', select=True, change_default=True),
        'invoice_id': fields.many2one('account.invoice','Documento'),
        'amount_invoice': fields.float('Valor Documento',help='El valor del documento'),
        'date': fields.date('Fecha',help='La fecha de la transacción'),
        'percent': fields.float('% Bono/Documento', help="La división del bono obtenido sobre el valor del documento"),
        'campaing_id': fields.many2one('sales.loyalty','Campaña'),
        'bonus': fields.float('Bono acumulado',help='El bono que ha acumulado'),
        'pending': fields.float('Bono Pendiente',help='El bono que ha acumulado'),
        'period_id': fields.many2one('account.period','Período'),
        'state': fields.selection([
            ('expired','Expirado'),
            ('redimed','Redimido'),
            ('pending','Pendiente'),
            ('cancel','Anulado')
            ],'Estado'),
        'date_start': fields.date('Válido desde',help='El inicio de la fecha'),
        'date_expired': fields.date('Válido hasta',help='La finalización de la fecha'),
        'active': fields.boolean('Activo'),
        'name': fields.many2one('sales.loyalty.partner','Código Cliente'),
        'partner_id':fields.many2one('res.partner','Cliente')
        }
    
    _defaults = {
        'active': True,
                 }
    
    def unlink(self, cr, uid, vals, context={}):
        raise osv.except_osv(_('¡Acción Inválida!'), _('NO se puede eliminar un cliente que tiene Bonos en cualquier estado.'))

    def expired_process_lines(self, cr, uid, context=None):
        camp_obj = self.pool.get('sales.loyalty.partner.line')
        review_date = time.strftime('%Y-%m-%d')
        camp_ids = camp_obj.search(cr, uid, [('active','=',True),('state','=','expired')], context=context)
        for camp in camp_obj.browse(cr, uid, camp_ids, context=context):
            if camp.date_expired < review_date:
                camp.write({'active':False,'state':'expired'})
        return True

        
sales_partner_line()


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    _columns = {
            'loyalty_card': fields.char('Código', size=15, help='El código del cliente para aplicar su bono'),  
            'loyalty_email':fields.boolean('Enviado Correo')              
                }
    
    _defaults = {
            'loyalty_email': False,
                 }
    
    def create(self, cr, uid, vals, context={}):                
        loyalty_card = ''
        valor = 0
        seg = False
        if (vals.get('segmento_id',False)):
            id_seg = (vals.get('segmento_id',False))
            seg = self.pool.get('res.partner.segmento').browse(cr, uid, id_seg)
        if seg:
            if vals.get('vat',False):
                for x in range(1,len(vals.get('vat',False))):
                    if vals.get('vat',False):
                        tv = vals.get('vat',False)
                        if tv[:2]!='PA':
                            if x == 4:
                                valor = int(vals.get('vat',False)[x])
                            if valor <= 5 and seg.name == 'TIENDAS':
                                loyalty_card = str(uuid.uuid4().get_hex().upper()[0:15]) 
                            if loyalty_card:    
                                vals['loyalty_card']=loyalty_card
        return super(res_partner, self).create(cr, uid, vals, context)              

    def write(self, cr, uid, ids, vals, context={}):    
        loyalty_card = ''
        valor = 0                    
        for partner in self.browse(cr,uid,ids):
            if not partner.loyalty_card:
                for x in range(1,len(partner.vat)):
                    if x == 4:
                        valor = int(partner.vat[x])
                if valor <= 5 and partner.segmento_id.name == "TIENDAS":
                    loyalty_card = str(uuid.uuid4().get_hex().upper()[0:15])
                if loyalty_card:
                    vals['loyalty_card']=loyalty_card
                    self.pool.get('sales.loyalty.partner').create(cr,uid,{'name':loyalty_card, 'partner_id':partner.id,'vat':partner.vat})        
            else:
                loyalty_id= self.pool.get('sales.loyalty.partner').search(cr,uid,[('name','=',loyalty_card)])
                if not loyalty_id:
                    self.pool.get('sales.loyalty.partner').create(cr,uid,{'name':partner.loyalty_card, 'partner_id':partner.id,'vat':partner.vat})
        return super(res_partner, self).write(cr, uid, ids, vals, context)                     

res_partner()

class report_loyalty(osv.osv):
        
    _name = "reports.loyalty.partner"
    _columns = {                
        'name': fields.char('Código', size=15, help='Un nombre indicativo de la promoción'),
        'vat': fields.related('partner_id','vat',type="char", relation="res.partner", string="Identificación", store=True),
        'partner_id': fields.many2one('res.partner','Cliente'),        
        'date_from': fields.date('Desde',help='La fecha desde cuando quiere consultar'),
        'date_to': fields.date('Hasta',help='La fecha hasta donde quiere consultar'),       
        'bonus_ids':fields.one2many('reports.loyalty.partner.line', 'wizard_id', 'Lines'),
        'company_id': fields.many2one('res.company','Compañía'),
        }
    
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'sales.loyalty', context=c),
        'date_from': '2010-01-01 00:00:00',        
        'date_to':datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                 }
 
 
    def onchange_date(self, cr, uid, ids, date_from, date_to, partner_id=False, vat=None, loyalty_card = None, context=None):
        res = {}
        res = self.pool.get('sales.loyalty.partner').onchange_date(cr,uid,ids,date_from,date_to,partner_id,vat,loyalty_card, context)
        res = res['value']
        return res   
 
    def do_search_loyalty_report(self, cr, uid, ids, context=None):
        cr.execute("""delete from reports_loyalty_partner_line where wizard_id = %s""",(ids[0],))
        for rp in self.browse(cr,uid,ids):
            partner_id = self.pool.get('res.partner').browse(cr,uid,rp.partner_id.id)
            if partner_id:
                self.do_shop_conection(cr,uid,ids,partner_id.id,rp.date_from, rp.date_to, context)
        return True 
    
    
    def do_shop_conection(self, cr, uid, ids, partner_id,from_date, to_date, context=None):
#           
            date = time.strftime('%Y-%m-%d %H:%M:%S')  
            cr.execute("""select pl.id, pl.partner_id, pl.name,pl.date, l.name as camp,
                   pl.type as tipo, pl.mode_id as modo, pl.invoice_id as fact,
                   pl.amount_invoice as valor_fact, pl.bonus as acum, pl.pending as pendiente,
                   pl.percent as porcentaje, pl.date_start, pl.date_expired, pl.state
                   from sales_loyalty_partner_line pl
                   left join sales_loyalty l on l.id = pl.campaing_id
                   where pl.partner_id = %s and pl.date >= %s and pl.date <= %s""",(partner_id,from_date,to_date))  
            il = cr.fetchall() 
            if il:  
                for i in il:
                    if i[5]=='add': type='+'    
                    else: type='-'
                    if i[6]=='input': mode ='Entrada'
                    else:  mode ='Salida'
                    if i[14]== 'expired': estado='Expirado'
                    elif i[14]== 'redimed': estado='Redimido'
                    elif i[14]== 'pending': estado='Pendiente'
                    else: estado='Anulado'
                    cr.execute("""INSERT INTO reports_loyalty_partner_line(type, mode_id, invoice_id, amount_invoice, date, percent, campaing, bonus, pending,state,date_start,date_expired,partner_id,name,wizard_id, create_date, create_uid)
                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(type,mode,i[7],i[8],i[3],i[11],i[4],i[9],i[10],estado,i[12],i[13],i[1],i[2],ids[0],date,uid))
             
            return True
    
report_loyalty()

class report_loyalty_line(osv.osv):
    
    _name = "reports.loyalty.partner.line"
    _columns = {                
        'type': fields.char('Tipo',size=5),
        'mode_id': fields.char('Modo',size=15),
        'invoice_id': fields.many2one('account.invoice','Documento'),
        'amount_invoice': fields.float('Valor Documento',help='El valor del documento'),
        'date': fields.date('Fecha',help='La fecha de la transacción'),
        'percent': fields.float('% Bono/Documento', help="La división del bono obtenido sobre el valor del documento"),
        'campaing': fields.char('Campaña',size=256),
        'bonus': fields.float('Bono acumulado',help='El bono que ha acumulado'),
        'pending': fields.float('Bono Pendiente',help='El bono que ha acumulado'),
        'state': fields.char('Estado',size=20),
        'date_start': fields.date('Válido desde',help='El inicio de la fecha'),
        'date_expired': fields.date('Válido hasta',help='La finalización de la fecha'),
        'partner_id':fields.many2one('res.partner','Cliente'),
        'name': fields.many2one('sales.loyalty.partner','Código Cliente'),
        'wizard_id':fields.many2one('reports.loyalty.partner','Asistente'),
        }
    
report_loyalty_line()