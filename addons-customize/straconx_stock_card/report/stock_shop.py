from report import report_sxw
import time

class stock_card(report_sxw.rml_parse):
    def __init__(self,cr,uid,name,context):
        #print "stock_card __init__",name,context
        super(stock_card,self).__init__(cr,uid,name,context=context)
        self.localcontext.update({
            "param": self.param,
            "lines": self.lines,
        })

    def param(self,form,name):
        #print "stock_card param",form,name
        cr=self.cr
        uid=self.uid
        if name=="product":
            prod=self.pool.get("product.product").browse(cr,uid,form["product_id"])
            return prod.name
        elif name == "category":
            product_temp = self.pool.get('product.template').browse(cr, uid, form["product_id"])
            return product_temp.categ_id.name
        elif name=="location":
            loc=self.pool.get("stock.location").browse(cr,uid,form["location_id"])
            return loc.name
        elif name=="uom":
            prod=self.pool.get("product.product").browse(cr,uid,form["product_id"])
            return prod.uom_id.name


    def lines(self,form):
#        print "stock_card lines",form
        cr=self.cr
        uid=self.uid
        product_id=form["product_id"]
        categ_id=self.pool.get('product.template').browse(cr, uid, form["product_id"]).categ_id.name
        location_id=form["location_id"]
        date_from=form["date_from"] or "1970-01-01 00:00:00"
#        date_to=form["date_to"] or time.strftime("%Y-%m-%d")
        date_to=form["date_to"] or time.strftime("%Y-%m-%d %H:%M:%S")
#        category=form["product_id.categ_id.name"]
        
        moves={}
        # find all moves coming to location
        move_in_ids=self.pool.get("stock.move").search(cr,uid,[("product_id","=",product_id),("location_dest_id","child_of",[location_id]),("date",">=",date_from),("date","<=",date_to),("state","=","done")])
        for move in self.pool.get("stock.move").browse(cr,uid,move_in_ids):
            moves[move.id]=move
        # find all moves leaving from location
        move_out_ids=self.pool.get("stock.move").search(cr,uid,[("product_id","=",product_id),("location_id","child_of",[location_id]),("date",">=",date_from),("date","<=",date_to),("state","=","done")])
        for move in self.pool.get("stock.move").browse(cr,uid,move_out_ids):
            moves[move.id]=move
        move_in_ids=set(move_in_ids)
        move_out_ids=set(move_out_ids)
        # order moves by date
        order_moves=moves.values()
        order_moves.sort(lambda a,b: cmp(a.date, b.date))
        lines=[]
        # add opening line of report
        start_qty_in=self.pool.get("product.product").get_product_available(cr,uid,[product_id],context={"location": location_id, "compute_child": True, "what": ["in"], "to_date": date_from, "states": ["done"]})[product_id]
        start_qty_out=self.pool.get("product.product").get_product_available(cr,uid,[product_id],context={"location": location_id, "compute_child": True, "what": ["out"], "to_date": date_from, "states": ["done"]})[product_id]
        lines.append({
            "date": form["date_from"] or "",
            "src": "",
            "dest": "",
            "ref": "Saldo Inicial",
            "price_unit": "",
            "amount": "",
            "type": "",
            "partner": "",
            "qty_in": start_qty_in,
            "qty_out": start_qty_out,
            "balance": start_qty_in-start_qty_out,
        })
        # add move lines of report
        total_qty_in=start_qty_in
        total_qty_out=start_qty_out
        for move in order_moves:
            qty_in=move.id in move_in_ids and move.product_qty or 0.0
            qty_out=move.id in move_out_ids and move.product_qty or 0.0
            total_qty_in+=qty_in
            total_qty_out+=qty_out
            
            if move.picking_id.type=='out':
                type='salida'
            elif move.picking_id.type=='in':
                type='entrada'
            else:
                type='transferencia'
            
            invoice=[]
            if move.picking_id.invoice_ids:
                for p in move.picking_id.invoice_ids:
                    invoice = p.number
                
            lines.append({
                "date": move.date_expected,
                "src": move.location_id.name,
                "dest": move.location_dest_id.name,
                "ref": invoice or move.picking_id.name,
                "price_unit": move.price_unit,
                "amount": move.price_unit*move.product_qty,
                "type":type,
                "partner": move.picking_id and move.picking_id.address_id \
                    and move.picking_id.address_id.name or '',
                "qty_in": qty_in,
                "qty_out": qty_out,
                "balance": total_qty_in-total_qty_out,
            })
        # add closing line of report
        lines.append({
            "date": date_to,
            "src": "",
            "dest": "",
            "ref": "Saldo Final",
            "price_unit": "",
            "amount": "",
            "type": "",
            "partner": "",
            "qty_in": total_qty_in-start_qty_in,
            "qty_out": total_qty_out-start_qty_out,
            "balance": total_qty_in-total_qty_out,
        })
        return lines

report_sxw.report_sxw("report.stock.card","stock.location","addons/straconx_stock_card/report/stock_card.rml",parser=stock_card,header=False)
