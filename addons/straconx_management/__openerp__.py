##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 STRACONX S.A. (<http://openerp.straconx.com>). 
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Purchase - Management Purchase Requisition",
    "version" : "0.1",
    "author" : "STRACONX S.A.",
    "category" : "Generic Modules/Sales & Purchases",
    "website" : "http://openerp.straconx.com",
    "description":  """
    This module allows you to manage your Management Purchase Requisition.
                    """,
    "depends" : [
                    "purchase", 
                    "purchase_requisition",
                    "straconx_purchase",
                    ],
    "init_xml" : [],
    "update_xml" : [
                    "security/straconx_groups_management.xml",
                    #"security/ir.model.access.csv",
                    "views/straconx_purchase_requisition_view.xml",
                    "views/straconx_menu.xml",
                    ],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

