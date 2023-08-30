# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2008-2009 B2CK, Cedric Krier, Bertrand Chenal (the methods "check_vat_[a-z]{2}"    
#    Copyright (C) 2010  (Christopher Ormaza,Jorge Valdiviezo) Ecuadorenlinea.net     
#    Copyright (C) 2010-present STRACONX S.A. All Rights Reserved     
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


from osv import osv, fields
from base_vat import base_vat
from tools.translate import _
from psycopg2 import IntegrityError
import re
import string

_re_ar_vat = re.compile('ar(\d\d)(\d*)(\d)', re.IGNORECASE)


_ref_vat = {
    'at': 'ATU12345675',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'ch': 'CHE-123.456.788 TVA or CH TVA 123456',  # Swiss by Yannick Vaucher @ Camptocamp
    'cy': 'CY12345678F',
    'cz': 'CZ12345679',
    'de': 'DE123456788',
    'dk': 'DK12345674',
    'ee': 'EE123456780',
    'el': 'EL12345670',
    'es': 'ESA12345674',
    'fi': 'FI12345671',
    'fr': 'FR32123456789',
    'gb': 'GB123456782',
    'gr': 'GR12345670',
    'hu': 'HU12345676',
    'hr': 'HR01234567896',  # Croatia, contributed by Milan Tribuson
    'ie': 'IE1234567T',
    'it': 'IT12345670017',
    'lt': 'LT123456715',
    'lu': 'LU12345613',
    'lv': 'LV41234567891',
    'mt': 'MT12345634',
    'mx': 'MXABC123456T1B',
    'nl': 'NL123456782B90',
    'no': 'NO123456785',
    'pl': 'PL1234567883',
    'pt': 'PT123456789',
    'ro': 'RO1234567897',
    'se': 'SE123456789701',
    'si': 'SI12345679',
    'sk': 'SK0012345675',
}


vatnumber = base_vat.vatnumber


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        if not re.match("^[A-Za-z]*$", country_code):
            return False
        check_func_name = 'check_vat_' + country_code
        check_func = getattr(self, check_func_name, None) or getattr(vatnumber, check_func_name, None)
        if not check_func:
            # No VAT validation available, default to check that the country code exists
            res_country = self.pool.get('res.country')
            return bool(res_country.search(cr, uid, [('code', '=ilike', country_code)], context=context))
        return check_func(vat_number)

    def _check_vat_repeat(self, cr, uid, ids, context=None):
        b = True
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat)
            vat = vat_country.upper() + vat_number
            part_ids = self.search(cr, uid, [('vat', '=', vat), ('id', 'not in', tuple(ids))])
            if part_ids:
                b = False
        return b

    def check_vat(self, cr, uid, ids, context=None):
        user_company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if user_company.vat_check_vies:
            # force full VIES online check
            check_func = self.vies_vat_check
        else:
            # quick and partial off-line checksum validation
            check_func = self.simple_vat_check
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat.replace('-', ''))
            if not check_func(cr, uid, vat_country, vat_number, context=context):
                return False
        return True

    def _construct_constraint_msg(self, cr, uid, ids, context=None):
        def default_vat_check(cn, vn):
            return cn[0] in string.ascii_lowercase and cn[1] in string.ascii_lowercase
        vat_country, vat_number = self._split_vat(self.browse(cr, uid, ids)[0].vat.replace('-', ''))
        vat_no = "'CC + ## país' (EC + cédula de identidad o el RUC o PA + el número de pasaporte para los extranjeros.)"
        if default_vat_check(vat_country, vat_number):
            vat_no = _ref_vat[vat_country] if vat_country in _ref_vat else vat_no
        return '\n' + _('La identificación ingresada no es válida.\nNota: Se espera una identificación similar a %s') % vat_no

    _columns = {
        'vat': fields.char('VAT', size=32,
                           help="CI, RUC or passport of the company. Please enter the number with the 2 first letters of your country."),
        'type_vat': fields.selection([('ruc', 'RUC'),
                                      ('ci', 'Cedula'),
                                      ('passport', 'Pasaporte'),
                                      ('consumidor', 'Consumidor')],
                                     'Identification Type'),
        'origin': fields.selection([('local', 'Local'), ('international', 'International')], 'Origin')
    }

    _constraints = [(_check_vat_repeat, 'This partner already exist', ['vat']),
                    (check_vat, _construct_constraint_msg, ["vat"])]

    _sql_constraints = [
        ('vat_uniq', 'unique (vat)', 'Error! Specified VAT Number already exists for any other registered partner.')
    ]

    def create(self, cr, uid, values, context=None):
        if values.get('vat', False):
            try:
                vat_country, vat_number = self._split_vat(values['vat'])
                values['vat'] = vat_country.upper() + vat_number
                return super(res_partner, self).create(cr, uid, values, context)
            except IntegrityError:
                raise osv.except_osv(_('Invalid action !'), _('The vat exists'))
        else:
            return super(res_partner, self).create(cr, uid, values, context)

    def write(self, cr, uid, ids, values, context=None):
        if values.get('vat', False):
            try:
                vat_country, vat_number = self._split_vat(values['vat'])
                values['vat'] = vat_country.upper() + vat_number
                return super(res_partner, self).write(cr, uid, ids, values, context)
            except IntegrityError:
                raise osv.except_osv(_('Invalid action !'), _('The vat exists'))
        else:
            return super(res_partner, self).write(cr, uid, ids, values, context)

    def check_vat_ch(self, vat):
        return True

    def check_vat_pa(self, vat):
        return True

    def check_vat_ar(self, vat):
        """
        Check VAT (CUIT) for Argentina
        """
        cstr = str(vat)
        salt = str(5432765432)
        n = 0
        suma = 0

        if not vat.isdigit:
            return False

        if (len(vat) != 11):
            return False

        while (n < 10):
            suma = suma + int(salt[n]) * int(cstr[n])
            n = n + 1

        op1 = suma % 11
        op2 = 11 - op1

        code_verifier = op2

        if (op2 == 11 or op2 == 10):
            if (op2 == 11):
                code_verifier = 0
            else:
                code_verifier = 9

        if (code_verifier == int(cstr[10])):
            return True
        else:
            return False

    def check_vat_ec(self, vat):
        '''
        Check Ecuadorian VAT number.
        '''
        b = False
        checker = 999999

        if len(vat) not in (10, 13):
            return b
        if not vat.isdigit():
            return b
        if vat == '9999999999999':
            b = True
        result = 0
        residue = 0
        # Natural Person CI
        if len(vat) == 10:
            value = [int(vat[x]) * (2 - x % 2) for x in range(9)]
            total = sum(map(lambda x: x > 9 and x - 9 or x, value))
            if int(int(vat[9] if int(vat[9]) != 0 else 10)) == (10 - int(str(total)[-1:])):
                b = True
        elif len(vat) == 13:
            # Public Companies vat
            if int(vat[2]) == 6 and vat[12] == '1':
                coefficient = "32765432"
                checker = int(vat[8])
                for i in range(8):
                    result += (int(vat[i]) * int(coefficient[i]))
                    residue = result % 11
                if residue == 0:
                    result = residue
                else:
                    result = 11 - residue
            # Private Companies Vat
            elif int(vat[2]) == 9 and vat[12] == '1':
                coefficient = "432765432"
                checker = int(vat[9])
                for i in range(9):
                    result += (int(vat[i]) * int(coefficient[i]))
                    residue = result % 11
                if residue == 0:
                    result = residue
                else:
                    result = 11 - residue
            # Natural Person vat
            elif int(vat[2]) < 6 and vat[12] == '1':
                coefficient = "212121212"
                checker = int(vat[9])
                for i in range(9):
                    sum_data = (int(vat[i]) * int(coefficient[i]))
                    if sum_data > 9:
                        str_sum = str(sum_data)
                        sum_data = int(str_sum[0]) + int(str_sum[1])
                    result += sum_data
                residue = result % 10
                if residue == 0:
                    result = residue
                else:
                    result = 10 - residue
            if result == checker:
                b = True
        return b

    def vat_change(self, cr, uid, ids, vat=None, context=None):
        result = super(res_partner, self).vat_change(cr, uid, ids, vat, context)
        country_company = ''
        type_ref = None
        origin = None
        company_obj = self.pool.get('res.users')
        country_company = company_obj.browse(cr, uid, uid).company_id.partner_id.vat[:2]
        if vat and len(vat) > 2:
            vat_country = vat[:2].upper()
            if country_company == vat_country and vat_country == 'EC':
                verify = self.check_vat_ec(vat[2:])
                if not verify:
                    raise osv.except_osv(_('Invalid action !'), _('The vat is wrong'))
                origin = "local"
                if len(vat[2:]) == 10:
                    type_ref = 'ci'
                elif len(vat[2:]) == 13:
                    if vat[2:] == '9999999999999':
                        type_ref = 'consumidor'
                    else:
                        type_ref = 'ruc'
            elif country_company == vat_country and vat_country == 'AR':
                verify = self.check_vat_ar(vat[2:].replace('-', ''))
                if not verify:
                    raise osv.except_osv(_('Invalid action !'), _('The vat is wrong'))
                origin = "local"
                if vat[2:4] in ('20', '27', '30'):
                    type_ref = 'ruc'
                cuit_parse = _re_ar_vat.match(vat) if vat else None
                cuit_string = 'AR{0}-{1}-{2}'.format(*cuit_parse.groups()) if cuit_parse is not None else vat
                result['value']['vat'] = cuit_string
            else:
                type_ref = 'passport'
                origin = 'international'

        result['value']['type_vat'] = type_ref
        result['value']['origin'] = origin
        return result

res_partner()