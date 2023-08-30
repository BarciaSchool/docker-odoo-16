##############################################################################
#
# Copyright (c) 2008-2011 Alistek Ltd (http://www.alistek.com) All Rights Reserved.
#                    General contacts <info@alistek.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This module is GPLv3 or newer and incompatible
# with OpenERP SA "AGPL + Private Use License"!
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from report import report_sxw
from report.report_sxw import rml_parse
import time
from tools.translate import _
import conversor

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        ret = super(Parser, self).__init__(cr, uid, name, context)
        
        try:
            report_conf_id = int(name)
        except:
            title = _('Incorrect Configuration name')
            message = _('A number was expected for the report name but instead it was "%s".', name)
            raise osv.except_osv(title, message)
        
        report_conf_obj = self.pool.get('report_aeroo_generator.report_configuration')
        report_conf = report_conf_obj.browse(cr, uid, report_conf_id, context=context)
        if isinstance(report_conf, list):
            report_conf = report_conf[0]
        
        if not report_conf:
            title = _('No configuration object')
            message = _('There is no report defined for Invoices with this parameters of in general.')
            raise osv.except_osv(title, message)
        
        # We add all the key-value pairs of the report configuration
        for report_conf_line in report_conf.line_ids:
            if report_conf_line.value_type == 'text':
                self.localcontext.update({report_conf_line.name: report_conf_line.value_text})
            elif report_conf_line.value_type == 'boolean':
                self.localcontext.update({report_conf_line.name: report_conf_line.value_boolean})
        
        # We add the report configuration
        self.localcontext.update({'report_configuration': report_conf})
        
        # We add the company of the active object
        company_id = False
        if 'active_model' in context and 'active_id' in context:
            active_model_obj = self.pool.get(context['active_model'])
            active_object = active_model_obj.browse(cr, uid, context['active_id'], context=context)
            if hasattr(active_object, 'company_id') and active_object.company_id:
                self.localcontext.update({'company': active_object.company_id})
        
        # We add logo
        if report_conf.print_logo == 'specified_logo':
            self.localcontext.update({'logo': report_conf.logo})
        elif report_conf.print_logo == 'company_logo':
            if company_id and company_id.logo:
                self.localcontext.update({'logo': company_id.logo})
        else:
            self.localcontext.update({'logo': False})
        
        # We add background_image
        self.localcontext.update({'use_background_image': report_conf.use_background_image})
        if report_conf.use_background_image:
            self.localcontext.update({'background_image': report_conf.background_image})
        else:
            self.localcontext.update({'background_image': False})
        
        self.localcontext.update({
            'format_vat': self.format_vat,
            'address_from_partner': self.address_from_partner,
            'minus': self.minus,
            'number_to_string': self.number_to_string,
            'net_price': self.net_price,
        })


    def format_vat(self, vat):
        formated_vat = False
        if vat and len(vat) > 2 and vat[0:2].lower() == "ar":
            vat_len = len(vat)
            formated_vat = '%s-%s-%s' % (vat[2:4], vat[4:vat_len-1], vat[vat_len-1:vat_len])
        return formated_vat
    
    def address_from_partner(self, partner):
        default_addr = False
        first_addr = False
        for address in partner.address:
            if address.type == 'invoice':
                return address
            elif address.type == 'default' and not default_addr:
                default_addr = address
        if default_addr:
            return default_addr
        else:
            return partner.address[0]
    
    def minus(self, val1, val2):
        return val1 - val2
    
    def number_to_string(self, val):
        return conversor.to_word(val)
    
    def net_price(self, gross_price, discount):
        return gross_price * (1-(discount / 100))





