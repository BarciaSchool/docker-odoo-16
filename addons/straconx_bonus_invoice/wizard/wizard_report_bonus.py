 # -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import osv,fields

class wizard_report_bonus(osv.osv_memory):
    _name="wizard.report.bonus"
    
    _columns={
              "company_id":fields.many2one("res.company","Company"),
              "partner_id":fields.many2one("res.partner","Customer"),
              "product_id":fields.many2one("product.product","Product"),
              "initial_date":fields.date("Initial Date",help="indicates the initial date where the bonus products will be considered"),
              "end_date":fields.date("End Date",help="indicates the final date where the bonus products will be considered"),              
              }
    
wizard_report_bonus()