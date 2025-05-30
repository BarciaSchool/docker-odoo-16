# -*- encoding: utf-8 -*-
########################################################################
#                                                                       
# @authors: STRACONX S.A                                                                          
# Copyright (C) 2012  Ecuadorenlinea.net                                  
#                                                                       
#This program is free software: you can redistribute it and/or modify   
#it under the terms of the GNU General Public License as published by   
#the Free Software Foundation, either version 3 of the License, or      
#(at your option) any later version.                                    
#
# This module is GPLv3 or newer and incompatible
# with OpenERP SA "AGPL + Private Use License"!
#                                                                       
#This program is distributed in the hope that it will be useful,        
#but WITHOUT ANY WARRANTY; without even the implied warranty of         
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          
#GNU General Public License for more details.                           
#                                                                       
#You should have received a copy of the GNU General Public License      
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  
########################################################################

from osv import fields,osv

class tipo_comprobante(osv.osv):
    
    _inherit = 'sri.document.type'
    
    _columns = {
                'sustent_ids':fields.many2many('sri.tax.sustent', 'document_support_rel', 'document_id', 'sustent_id', 'Tax Sustent'), 
                'usage_ids':fields.many2many('sri.transaction.type', 'document_transaction_rel', 'document_id', 'transaction_id', 'Transaction Types'), 
                }
    
tipo_comprobante()