# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#
##############################################################################


{
    'name': 'Customization for Sale Management in Ecuador',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """Customization for Sale Management in Ecuador.
        Permit configure the shop by point of sale, wholesale, consignment and headquarter
        Create of view model invoice for point of sale shop.
        Permit the delivery of products partially automatically
        Configure supervisors that give users permission to discounts that exceed the value allowed by the company.""",
    'author': 'STRACONX S.A.',
    'website': 'http://openerp.straconx.com',
    'depends': [
                'crm',
                'sale_pricelist_recalculation',
                'straconx_account',
                'straconx_invoice',
                'straconx_payments',
                'straconx_products',
                'straconx_logistics',
                'straconx_withhold',
                'straconx_authorizations'
                ],
    'init_xml': [],
    'update_xml': [
                    'security/straconx_sales_security.xml',
                    'report/straconx_sale_report.xml',
                    #'workflow/sale_workflow.xml',
                    'wizard/authorization.xml',
                    'wizard/wizard_pay_invoice.xml',
                    'wizard/wizard_sale_pricelist_recalculation.xml',
#                    'views/straconx_shop.xml',
                    'views/straconx_partner_view.xml',
                    'views/straconx_payments_mode_view.xml',
                    'views/straconx_company_view.xml',
                    'views/straconx_invoice_pos_view.xml',
                    'views/straconx_view_sale.xml',
                    'views/straconx_view_sale_salesman.xml',
                    'views/straconx_view_sale_backorder.xml',
#                    'views/straconx_view_pos.xml',
                    'views/straconx_view_consignment.xml',
                    'views/straconx_withhold_invoice_view.xml',
                    'views/straconx_view_other.xml',
                    'views/straconx_payments_shop.xml',
                    'views/straconx_menu.xml',                    
                    'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

