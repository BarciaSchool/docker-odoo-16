# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2009 Almacom (Thailand) Ltd.
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################


from osv import fields, osv
import time
from tools.translate import _
import decimal_precision as dp
class landed_cost(osv.osv):
    _name="landed.cost"
    _columns={
        "name": fields.char('Name', size=30, required=True),
        "date": fields.date("Date",required=True,readonly=True, states={'draft':[('readonly',False)]}),
        "method": fields.selection([("qty","Quantity"),("amount","Amount"),("weight","Weight"),("volume","Volume")],"Allocation Method", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        "amount": fields.float("Amount",readonly=True, states={'draft':[('readonly',False)]},digits_compute=dp.get_precision('Trade')),
        "other": fields.float("Other",readonly=True, states={'draft':[('readonly',False)]},digits_compute=dp.get_precision('Trade')),
#        "other_invoice": fields.float("Other Invoice",required=True,readonly=True, states={'draft':[('readonly',False)]},digits_compute=dp.get_precision('Trade')),
        "currency_id": fields.many2one("res.currency","Currency",required=True,readonly=True, states={'draft':[('readonly',False)]}),
        "lines": fields.one2many("landed.cost.line","cost_id","Items",readonly=True, states={'draft':[('readonly',False)]}),
        "state": fields.selection([("draft","Draft"),("posted","Posted"),("canceled","Canceled")],"Status",required=True,readonly=True),
    }
    
    _rec_name="method"
    
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "state": lambda *a: "draft",
        "currency_id": lambda self,cr,uid,context: self.pool.get('res.users').browse(cr,uid,uid).company_id.currency_id.id,
    }

    def btn_compute(self,cr,uid,ids,context={}):
        for ac in self.browse(cr,uid,ids):
            total_qty=0.0
            total_amount=0.0
            total_volume=0.0
            total_weight=0.0
            for line in ac.lines:
                total_qty+=line.product_qty
                total_amount+=line.amount
                total_volume+=line.total_volume
                total_weight+=line.total_weight
            for line in ac.lines:
                if ac.method=="qty":
#                    line.write({"cost":ac.amount*line.product_qty/total_qty,"other":ac.other*line.product_qty/total_qty,"other_invoice":ac.other_invoice*line.product_qty/total_qty})
                    line.write({"cost":ac.amount*line.product_qty/total_qty,"other":ac.other*line.product_qty/total_qty})
                elif ac.method=="amount":
#                    line.write({"cost":ac.amount*line.amount/total_amount,"other":ac.other*line.amount/total_amount,"other_invoice":ac.other_invoice*line.amount/total_amount})
                    if total_amount >0:
                        line.write({"cost":ac.amount*line.amount/total_amount,"other":ac.other*line.amount/total_amount})
                    else:
                        raise osv.except_osv(_("Error"),_("Verifique las facturas. Las líneas del costo no pueden ser 0"))
                elif ac.method=="weight":
#                    line.write({"cost":ac.amount*line.total_weight/total_weight,"other":ac.other*line.total_weight/total_weight,"other_invoice":ac.other_invoice*line.total_weight/total_weight})
                    line.write({"cost":ac.amount*line.total_weight/total_weight,"other":ac.other*line.total_weight/total_weight})
                elif ac.method=="volume":
#                    line.write({"cost":ac.amount*line.total_volume/total_volume,"other":ac.other*line.total_volume/total_volume,"other_invoice":ac.other_invoice*line.total_volume/total_volume})
                    line.write({"cost":ac.amount*line.total_volume/total_volume,"other":ac.other*line.total_volume/total_volume})
        return True

    def btn_post(self,cr,uid,ids,context={}):
        self.btn_compute(cr, uid, ids, context)
        self.write(cr,uid,ids,{"state": "posted"})
        count=0
        for ac in self.browse(cr,uid,ids):
            for line in ac.lines:
                count+=1
                if not line.invoice_line_id:
                    raise osv.except_osv(_("Error"),_("Does not exist reference to the line %s") % str(count))
                else:
                    cost_expense=line.cost_unit+line.other_unit
                self.pool.get('account.invoice.line').write(cr, uid, [line.invoice_line_id.id], {'cost_expense_unit':cost_expense}, context)
        return True

    def btn_cancel(self,cr,uid,ids,context={}):
        self.write(cr,uid,ids,{"state": "canceled"})
        for ac in self.browse(cr,uid,ids):
            for line in ac.lines:
                line_id = self.pool.get('account.invoice.line').browse(cr,uid,[line.invoice_line_id.id])
                if line_id:                    
                    self.pool.get('account.invoice.line').write(cr, uid, [line.invoice_line_id.id], {'cost_expense_unit':0.0}, context)
        return True

    def btn_draft(self,cr,uid,ids,context={}):
        self.write(cr,uid,ids,{"state": "draft"})
        return True
landed_cost()

class landed_cost_line(osv.osv):
    _name="landed.cost.line"
    
    def _cost_unit(self,cr,uid,ids,name,arg,context={}):
        vals={}
        rdc = self.pool.get('decimal.precision').search(cr,uid,[('name','=','Trade')]) 
        decimal = rdc and self.pool.get('decimal.precision').browse(cr,uid,rdc[0]).digits or 3
        for ac in self.browse(cr,uid,ids):
            if ac.product_qty:
                vals[ac.id]=round(ac.cost/ac.product_qty,decimal)
            else:
                vals[ac.id]=0.0
        return vals

    def _other_unit(self,cr,uid,ids,name,arg,context={}):
        vals={}
        rdc = self.pool.get('decimal.precision').search(cr,uid,[('name','=','Trade')]) 
        decimal = rdc and self.pool.get('decimal.precision').browse(cr,uid,rdc[0]).digits or 3
        for ac in self.browse(cr,uid,ids):
            if ac.product_qty:
                vals[ac.id]=round(ac.other/ac.product_qty,decimal)
            else:
                vals[ac.id]=0.0
        return vals
        
    def _cost_amount(self,cr,uid,ids,name,arg,context={}):
        vals={}
        rdc = self.pool.get('decimal.precision').search(cr,uid,[('name','=','Trade')]) 
        decimal = rdc and self.pool.get('decimal.precision').browse(cr,uid,rdc[0]).digits or 3
        for ac in self.browse(cr,uid,ids):
            vals[ac.id]=round(ac.price_unit*ac.product_qty,decimal)
        return vals
    
    def _total_volume(self,cr,uid,ids,name,arg,context={}):
        vals={}
        rdc = self.pool.get('decimal.precision').search(cr,uid,[('name','=','Trade')]) 
        decimal = rdc and self.pool.get('decimal.precision').browse(cr,uid,rdc[0]).digits or 3
        for ac in self.browse(cr,uid,ids):
            vals[ac.id]=0.0
            if ac.invoice_line_id:
                vals[ac.id]=round(ac.invoice_line_id.product_id.volume*ac.product_qty,decimal)
        return vals
    
    def _total_weight(self,cr,uid,ids,name,arg,context={}):
        vals={}
        rdc = self.pool.get('decimal.precision').search(cr,uid,[('name','=','Trade')]) 
        decimal = rdc and self.pool.get('decimal.precision').browse(cr,uid,rdc[0]).digits or 3
        for ac in self.browse(cr,uid,ids):
            vals[ac.id]=0.0
            if ac.invoice_line_id:
                vals[ac.id]=round(ac.invoice_line_id.product_id.weight*ac.product_qty,decimal)
        return vals

    _columns={
        "cost_id": fields.many2one("landed.cost","Landed Costs",required=True,ondelete="cascade"),
        "invoice_line_id": fields.many2one("account.invoice.line","Invoice Line Reference",required=False),
        "product_id": fields.related("invoice_line_id","product_id",type="many2one",relation="product.product",string="Product",readonly=True),
        "product_qty": fields.related("invoice_line_id","quantity",type="float",string="Quantity",readonly=True),
        "price_unit": fields.related("invoice_line_id","price_unit",type="float",string="Unit Price",readonly=True),
        "amount": fields.function(_cost_amount,method=True,digits_compute=dp.get_precision('Trade'),type="float",string="Amount",store=True),
        "total_volume": fields.function(_total_volume,method=True,type="float",string="Total Volume",store=True),
        "total_weight": fields.function(_total_weight,method=True,type="float",string="Total weight",store=True),
        "cost": fields.float("Allocated Cost",readonly=True, digits_compute=dp.get_precision('Trade')),
        "cost_unit": fields.function(_cost_unit,method=True,type="float",string="Cost Per Unit",digits_compute=dp.get_precision('Trade'),store=True),
        "other": fields.float("Other Cost", readonly=True,digits_compute=dp.get_precision('Trade')),
        "other_unit": fields.function(_other_unit,method=True,type="float",string="Other Cost",digits_compute=dp.get_precision('Trade'),store=True),
    }
landed_cost_line()
