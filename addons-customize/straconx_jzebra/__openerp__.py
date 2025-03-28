# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (c) 2010 Juan Pizarro <jpizarrom@gmail.com> All Rights Reserved.
#
#    $Id$
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
    "name": "jZebra",
    'category': 'Printer',
    "description":
        """
        OpenERP Web example module.
        """,
    "version": "2.0",
    "depends": ['product','web'],
    "update_xml": ["wizard/printer_view.xml"],
    'js': ['static/js/jzebra.js'],
    'qweb': ['static/xml/jzebra.xml'],
    'installable': True,
    'active': False
}
