##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A. (<http://openerp.straconx.com>). All Rights Reserved
#    
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
  'name' : 'Contact of partner of Ecuador',
  'version' : '0.1',
  'author' : 'STRACONX S.A. based in module base_contact',
  'website' : 'http://openerp.straconx.com',
  'category' : 'Ecuadorian Location/Contacts',
  'description' : """This Module create structure contacts by address based in module base_contact
  version openerp 6.0.4 author Tiny SPRL """,
  'depends' : ['straconx_states'],
  'init_xml' : [],
  'demo_xml' : [],
  'update_xml' : ['views/base_contact_view.xml',
                  'views/res_partner_address.xml',
                  'views/straconx_menu.xml',
                ],
  'installable' : True,
  'active' : False,
}

