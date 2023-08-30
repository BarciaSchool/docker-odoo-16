# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2013-2014 STRACONX S.A (Jorge Valdiviezo) 
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

{
    "name": "Multi-DB Synchronization",
    "version": "1.0",
    "author" :  "Jorge Valdiviezo, Straconx S.A.",
    "category": "Tools",
    "description": """
Synchronization with all database.
=================================

Configure servers and trigger synchronization with its database objects.
Modify id of object for the synchronize.
This module is based in code of module base_synchro.
""",
    "depends": ["base"],
    "update_xml": [
        "data/data_cron.xml",
        "views/company_view.xml",
        "views/base_synchro_obj_view.xml",
        #"security/ir.model.access.csv",
        ],
    "installable": True,
}
