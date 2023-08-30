# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#                  2012-2013 STRACONX S.A 
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

from osv import fields,osv

class res_partner_function(osv.osv):
    _name = 'res.partner.function'
    _columns = {
    'name': fields.char('Function', size=128),
    }
res_partner_function()

class res_partner_title(osv.osv):
    _inherit = 'res.partner.title'
    _columns = {
        'name': fields.char('Title', size=46, translate=True),
        'shortcut':fields.char('shortcut', size=16, required=False, readonly=False),
        'domain': fields.selection([('partner','Partner'),('origin','Origin'),('agency','Agency'),('contact','Contact'), ('function','Function')], 'Domain', required=True, size=24),
        'active': fields.boolean('Active'),
        }
    _defaults= {
        'active': True    
    }
res_partner_title()


class res_partner_contact(osv.osv):
    """ Partner Contact """

    _name = "res.partner.contact"
    _description = "Contact"

    _columns = {
        'address_id':fields.many2one('res.partner.address', 'Address Partner', required=False),
        'name': fields.char('Last Name', size=64, required=True),
        'first_name': fields.char('First Name', size=64),
        'vat': fields.char('VAT code',size=20),
        'sex': fields.selection([('men','Men'),('woman','Woman')],'Sex'),
        'mobile': fields.char('Mobile', size=64),
        'website': fields.char('Website', size=120),
        'email': fields.char('E-Mail', size=240),
        'comment': fields.text('Notes', translate=True),
        'photo': fields.binary('Image'),
        'birthdate': fields.date('Birth Date'),
        'title': fields.many2one('res.partner.title','Title'),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'job_ids': fields.one2many('res.partner.job', 'contact_id', 'Functions Jobs'),
        'country_id': fields.many2one('res.country','Nationality'),
        'active': fields.boolean('Active', help="If the active field is set to False,\
                 it will allow you to hide the partner contact without removing it."),
        'function': fields.many2one('res.partner.function','Function', help="Function of this contact with this partner"),                
        'partner_id': fields.related('address_id', 'partner_id', type='many2one',relation='res.partner', string='Main Employer'),

    }
    _defaults = {
        'active' : lambda *a: True,
    }

    _order = "name,first_name"

    def name_get(self, cr, user, ids, context=None):

        """ will return name and first_name.......
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param user: the current user’s ID for security checks,
            @param ids: List of create menu’s IDs
            @return: name and first_name
            @param context: A standard dictionary for contextual values
        """

        if not len(ids):
            return []
        res = []
        for contact in self.browse(cr, user, ids, context=context):
            _contact = ""
            if contact.title:
                _contact += "%s "%(contact.title.name)
            _contact += contact.name or ""
            if contact.name and contact.first_name:
                _contact += " "
            _contact += contact.first_name or ""
            res.append((contact.id, _contact))
        return res
    
    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=None):
        if not args:
            args = []
        if context is None:
            context = {}
        if name:
            ids = self.search(cr, uid, ['|',('name', operator, name),('first_name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context=context)
    
res_partner_contact()

class res_partner_job(osv.osv):
    def name_get(self, cr, uid, ids, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param user: the current user,
            @param ids: List of partner address’s IDs
            @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}

        if not ids:
            return []
        res = []

        jobs = self.browse(cr, uid, ids, context=context)

        contact_ids = [rec.contact_id.id for rec in jobs]
        contact_names = dict(self.pool.get('res.partner.contact').name_get(cr, uid, contact_ids, context=context))

        for r in jobs:
            function_name = r.function
            funct = function_name and (", " + function_name) or ""
            res.append((r.id, contact_names.get(r.contact_id.id, '') + funct))
        return res

    _name = 'res.partner.job'
    _description ='Contact Partner Function'
    _order = 'sequence_contact'

    _columns = {
        'contact_id': fields.many2one('res.partner.contact','Contact', required=False, ondelete='cascade'),
        'name': fields.related('contact_id','address_id','partner_id', type='many2one',relation='res.partner', string='Partner', help="You may enter Address first,Partner will be linked automatically if any."),
        'address_id': fields.related('contact_id','address_id','partner_id', type='many2one',relation='res.partner.address', string='Partner Address', help='Address which is linked to the Partner'),
        'function': fields.many2one('res.partner.function','Function', help="Function of this contact with this partner"),
        'sequence_contact': fields.integer('Contact Seq.',help='Order of importance of this address in the list of addresses of the linked contact'),
        'email': fields.char('E-Mail', size=240, help="Job E-Mail"),
        'phone': fields.char('Phone', size=64, help="Job Phone no."),
        'fax': fields.char('Fax', size=64, help="Job FAX no."),
        'extension': fields.char('Extension', size=64, help='Internal/External extension phone number'),
        'other': fields.char('Other', size=64, help='Additional phone field'),
        'date_start': fields.date('Date Start',help="Start date of job(Joining Date)"),
        'date_stop': fields.date('Date Stop', help="Last date of job"),
        'active': fields.boolean('Active', help="If the active field is set to False,\
         it will allow you to hide the partner contact without removing it."),
        'state': fields.selection([('past', 'Past'),('current', 'Current')], \
                                'State', required=True, help="Status of Address"),
    }

    _defaults = {
        'sequence_contact' : lambda *a: 0,
        'state': lambda *a: 'current',
        'active':lambda *a:True,
    }

res_partner_job()