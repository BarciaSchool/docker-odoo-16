# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013 STRACONX S.A. <http://openerp.straconx.com>
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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from osv import fields, osv, orm
from edi import EDIMixin
from tools import DEFAULT_SERVER_DATE_FORMAT
from tools.translate import _

STOCK_PICKING_LINE_EDI_STRUCT = {
    'ref_product': True,
    'product_id': True,
    'product_qty': True,
    'product_uom': True,
    'ubication_id': True,    
}

STOCK_PICKING_EDI_STRUCT = {
    'company_id': True, # -> to be changed into partner
    'name': True,
    'digiter_id': True,
    'shop_id': True,
    'shop_id_dest': True,    
    'address_id': True,
    'carrier_id': True,
    'date': True,
    'min_date': True,
    'move_lines': STOCK_PICKING_LINE_EDI_STRUCT,
}

class stock_picking(osv.osv, EDIMixin):
    _inherit = 'stock.picking'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):

        edi_struct = dict(edi_struct or STOCK_PICKING_EDI_STRUCT)
        res_company = self.pool.get('res.company')
        res_partner_address = self.pool.get('res.partner.address')
        edi_doc_list = []
        for order in records:
            # generate the main report
            self._edi_generate_report_attachment(cr, uid, order, context=context)

            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(stock_picking,self).edi_export(cr, uid, [order], edi_struct, context)[0]
            edi_doc.update({
                    # force trans-typing to purchase.order upon import
                    '__import_model': 'sale.order',
                    '__import_module': 'sale',

                    'company_address': res_company.edi_export_address(cr, uid, order.company_id, context=context),
            })
            if edi_doc.get('move_lines'):
                for line in edi_doc['move_lines']:
                    line['__import_model'] = 'stock.move'
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def edi_import_company(self, cr, uid, edi_document, context=None):
        # TODO: for multi-company setups, we currently import the document in the
        #       user's current company, but we should perhaps foresee a way to select
        #       the desired company among the user's allowed companies

        self._edi_requires_attributes(('company_id','company_address'), edi_document)
        res_partner = self.pool.get('res.partner')

        # imported company = as a new partner
        src_company_id, src_company_name = edi_document.pop('company_id')
        partner_id = self.edi_import_relation(cr, uid, 'res.partner', src_company_name,
                                              src_company_id, context=context)
        partner_value = {'customer': True}
        res_partner.write(cr, uid, [partner_id], partner_value, context=context)

        # imported company_address = new partner address
        address_info = edi_document.pop('company_address')
        address_info['partner_id'] = (src_company_id, src_company_name)
        address_info['type'] = 'default'

        # modify edi_document to refer to new partner/address
        edi_document['partner_id'] = (src_company_id, src_company_name)

        return partner_id

    def edi_import(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('company_id','company_address','order_line','date_order','currency'), edi_document)
        #import company as a new partner
        partner_id = self.edi_import_company(cr, uid, edi_document, context=context)
        partner_ref = edi_document.pop('partner_ref', False)
        edi_document['partner_ref'] = edi_document['name']
        edi_document['name'] = partner_ref or edi_document['name']
        edi_document['location_id'] = self._edi_get_location(cr, uid, partner_id, context=context)
        
        for move_lines in edi_document['move_lines']:
            self._edi_requires_attributes(('ref_product','product_id','product_qty','product_uom','ubication_id',), move_lines)
        return super(stock_picking,self).edi_import(cr, uid, edi_document, context=context)

class stock_move(osv.osv, EDIMixin):
    _inherit='stock.move'
