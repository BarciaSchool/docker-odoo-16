# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from osv import fields, osv


class country_state(osv.osv):
        _inherit = 'res.country.state'
        afip_code = fields.char(
            'AFIP code', size=64, help='Codigo oficial del AFIP.')
