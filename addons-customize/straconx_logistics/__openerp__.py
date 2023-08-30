# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved
#
#
##############################################################################

{
    'name': 'Customization for logistic process and inventory in Ecuador',
    'version': '1.0',
    'category': 'Ecuadorian Location/Logistics management',
    'author': "STRACONX S.A.",
    'website': 'http://openerp.straconx.com',
    'description': """
    This module customize the logistics management adapted in Ecuador.
    * Create structure of locations for each warehouse
    * generate accounts move for each move in or out
    * Permit create invoice in, out or liquidation puchase from picking order
    * Permit generate initial inventory of products for each ubication
    * Permit generate lost sales for products moves that can not delivery""",
    'depends': [
        'straconx_account',
        # 'straconx_invoice',
        'straconx_credit_notes',
        'straconx_products',
        'straconx_listprices',
        ],
    "init_xml": ["data/no_dashboard.xml",
                 "data/delete_data.xml"
                 ],
    'update_xml': [
        'data/inventory_sequence.xml',
        'data/carrier.xml',
        'report/straconx_logistic_report.xml',
        'views/straconx_shop.xml',
        'wizard/stock_move_scrap.xml',
        'wizard/report_shop_location.xml',
        'wizard/stock_invoice_incoming.xml',
        'wizard/stock_invoice_onshipping.xml',
        'wizard/straconx_delivery_note.xml',
        'wizard/stock_fill_inventory_view.xml',
        'wizard/make_procurement_view.xml',
        'views/partner_view.xml',
        'views/straconx_carrier_view.xml',
        'views/straconx_location.xml',
        'views/straconx_product.xml',
        'views/straconx_delivery_view.xml',
        'views/straconx_delivery_pos_view.xml',
        'views/straconx_delivery_view_wait.xml',
        'views/straconx_incoming_view.xml',
        'views/straconx_internal_view.xml',
        'views/straconx_company.xml',
#        'views/straconx_internal_report_view.xml',
        'views/straconx_consigment_view.xml',
        'views/straconx_inventory_view.xml',
        'views/stock_view_original.xml',
        'views/straconx_lost_sales.xml',
        'views/straconx_invoice.xml',
        'views/straconx_user.xml',
        "views/straconx_shop.xml",
        "views/straconx_stock_shop.xml",
        "views/straconx_delivery_guide.xml",
        "views/straconx_stock_by_shop.xml",
        "wizard/installer.xml",
        "edi/straconx_picking_internal.xml",
#         "edi/out_mail.xml",
#        'data/label_action.xml',
        'views/straconx_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'test':[],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
