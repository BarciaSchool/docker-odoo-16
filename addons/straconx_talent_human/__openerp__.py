##############################################################################
#
#    OpenERP Ecuadorian Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A.
#    All Rights Reserved
#    
#    This program is private software.
#
#
##############################################################################

{
        "name" : "Ecuadorian Human Resources",
        "version" : "1.0.106",
        "author" : "STRACONX S.A.",
        "website" : "http://openerp.straconx.com",
        "category" : "Base",
        "description": """Human Resources for Ecuadorian localisation. Please, replace file tools/safe_eval.py in your openerp-server/tools. Based in a Christopher Ormaza / Ecuadorenlinea.net work""",
        "depends" : [
                     'straconx_account',
                     'straconx_cash_voucher',                     
#                     'straconx_states',
                     'straconx_payments',
                     'straconx_sales',
                     'hr',
                     'hr_contract',
                     'hr_payroll',
                     'hr_payroll_account',
                     'hr_holidays',
                     'hr_evaluation',
                     'hr_attendance',
                     'pentaho_reports'
                     ],
        "init_xml" : [
                      'data/str_hr_delete_info.xml',
                      'data/no_dashboard.xml',                                            
                      ],
        "demo_xml" : [],
        "update_xml" : [
                        'security/ir.model.access.csv',
                        'report/str_hr_reports.xml',                        
                        'wizards/str_hr_wizard_invoice_pay.xml',
                        'wizards/str_hr_payroll_statement_view.xml',
                        'wizards/str_hr_create_partner_from_user.xml',
                        'wizards/str_hr_discount_employee.xml',
                        'wizards/str_hr_pay_provision_by_employees.xml',
                        'wizards/str_hr_reopen_discount.xml',
                        'views/str_hr_account_view.xml',
                        'views/str_hr_pay_provision_view.xml',
                        'views/str_hr_res_partner.xml',
                        'views/str_hr_res_partner_bank.xml',
                        'views/str_hr_user_view.xml',
                        'views/str_hr_check_for_employee.xml',
                        'views/str_hr_transaction_type.xml',
                        'views/str_hr_discount.xml',
                        'views/str_hr_incomes.xml',
                        'views/str_hr_period_view.xml',
                        'views/str_hr_salary_rule_view.xml',
                        'views/str_hr_job.xml',
                        'views/str_hr_department.xml',
                        'views/str_hr_company.xml',
                        'views/str_hr_payslip_view.xml',
                        'views/str_hr_payslip_run_view.xml',
                        'views/str_hr_employee.xml',
                        'views/str_hr_contract.xml',
                        'views/str_hr_sectorial_tables.xml',
                        'views/str_hr_family_burden_view.xml',
                        'views/str_hr_education_level_view.xml',
                        'views/str_hr_holidays.xml',
                        'views/str_hr_payment_mode_view.xml',
                        'views/str_hr_voucher_view.xml',
                        'views/str_hr_invoice_line.xml',
                        'views/str_hr_invoice_pos_view.xml',
                        'views/str_hr_menu.xml',
                        'data/str_hr_education_area.xml',
                        'data/str_hr_contract_type_data.xml',
                        'data/str_hr_diarios_contables.xml',
                        'data/str_hr_payroll_data.xml',
                        'data/str_hr_ir_sequence.xml',
                        'data/str_hr_payment_mode.xml',                   
                        ],
        "installable": True,
        'active': False,
}
