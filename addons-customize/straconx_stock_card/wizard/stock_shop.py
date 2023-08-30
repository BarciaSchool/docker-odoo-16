import wizard
import pooler

view="""<?xml version="1.0"?>
<form string="Stock card parameters">
    <field name="location_id"/>
    <field name="product_id"
        context="{'location': location_id}" />
    <field name="date_from"/>
    <field name="date_to"/>
</form>
"""

fields={
    "location_id": {
        "type": "many2one",
        "relation": "stock.location",
        "string": "Location",
        #"readonly":False,
        "required": True,
        "traslate":True,
    },
    "product_id": {
        "type": "many2one",
        "relation": "product.product",
        "string": "Product",
        "required": True,
    },

    "date_from": {
        "type": "datetime",
        "string": "From",
    },
    "date_to": {
        "type": "datetime",
        "string": "To",
    },
}

class wiz_stock_card(wizard.interface):
    states={
        "init": {
            "actions": [],
            "result": {
                "type": "form",
                "arch": view,
                "fields": fields,
                "state": [
                    ("end","Cancel"),
                    ("report","Print Stock Card"),
                ]
            }
        },
        "report": {
            "actions": [],
            "result": {
                "type": "print",
                "report": "stock.card",
                "state": "end",
            }
        }
    }
wiz_stock_card("stock.shop")
