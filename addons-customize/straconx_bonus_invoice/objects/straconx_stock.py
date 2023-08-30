from osv import osv,fields
import decimal_precision as dp
from tools.translate import _

class stock_picking(osv.osv):
    
    _name="stock.picking"
    _inherit="stock.picking"
    
    def get_prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
        invoice_vals, context=None):
        if group:
            name = (picking.name or '') + '-' + move_line.name
        else:
            name = move_line.name
        origin = move_line.picking_id.name or ''
        if move_line.picking_id.origin:
            origin += ':' + move_line.picking_id.origin

        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            account_id = move_line.product_id.product_tmpl_id.\
                    property_account_income.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_income_categ.id
        else:
            account_id = move_line.product_id.product_tmpl_id.\
                    property_account_expense.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_expense_categ.id
        if invoice_vals['fiscal_position']:
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = move_line.product_uos and move_line.product_uos.id or False
        if not uos_id and invoice_vals['type'] in ('out_invoice', 'out_refund'):
            uos_id = move_line.product_uom.id

        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'uos_id': uos_id,
            'product_id': move_line.product_id.id,
            'account_id': account_id,
            'price_product':self._get_price_original(cr, uid, move_line),
            'price_unit': self._get_price_unit_invoice(cr, uid, move_line, invoice_vals['type']),
            'discount': self._get_discount_invoice(cr, uid, move_line),
            'offer':self._get_offer_invoice(cr, uid, move_line),
            'qty':move_line.qty,
            'bonus_qty':move_line.bonus_qty,
            'quantity': move_line.qty+move_line.bonus_qty,
            'price_subtotal':self._get_subtotal_invoice(cr, uid, move_line),
            'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type']))],
            'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),
        }
    
stock_picking()

class stock_move(osv.osv):
    
    _inherit="stock.move"
    _columns = {
               'product_qty': fields.float('Total Quantity', digits_compute=dp.get_precision('Product UoM'), states={'done': [('readonly', True)]}),
               "bonus_qty":fields.float("Bonus", digits=(12, 3), help="Quantity awarded as bonus.Bonus must be greater than or equal to 0."),
               "qty":fields.float("Quantity", digits=(12, 3)),
                }
    _defaults = {
               "bonus_qty":0,
               } 
    
    def onchange_quantity(self,cr,uid, ids, product_id, product_qty,product_uom, product_uos):
        return self.onchange_qty(cr, uid, ids,product_qty, 0, product_id, product_qty, product_uom, product_uos)
    
    def onchange_qty(self, cr,uid, ids,qty,bonus_qty, product_id, product_qty,product_uom, product_uos):
        repaired = False
        if(qty):
            if(qty < 0):
                qty = qty * -1
        if(bonus_qty):
            if(bonus_qty < 0):
                repaired = -1
                bonus_qty = 0
            if(bonus_qty > qty):
                repaired = -2
                bonus_qty = 0    
        total_quantity = qty + bonus_qty
        values = super(stock_move, self).onchange_quantity(cr,uid, ids, product_id, product_qty,product_uom, product_uos)
        value = values["value"]
        value["qty"] = qty
        value["product_qty"] = total_quantity
        value["bonus_qty"] = bonus_qty
        values["value"] = value
        if(repaired):
            if(repaired == -1):
                values["warning"] = {"title":_("Validation Error!"), "message":_("BONUS must be greater than or equal to 0.PLEASE CHECK!.The amount has been adjusted.")}
            if(repaired == -2):
                values["warning"] = {"title":_("Validation Error!"), "message":_("BONUS not be greater than QUANTITY.PLEASE CHECK!.")}        
        return values
    
stock_move()