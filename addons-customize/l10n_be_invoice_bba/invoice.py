# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
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

import re, time, random
from osv import fields, osv
from tools.translate import _
import netsvc
logger=netsvc.Logger()

"""
account.invoice object:
    - Add support for Belgian structured communication
    - Rename 'reference' field labels to 'Communication'
"""

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def _get_reference_type(self, cursor, user, context=None):
        """Add BBA Structured Communication Type and change labels from 'reference' into 'communication' """  
        res = super(account_invoice, self)._get_reference_type(cursor, user,
                context=context)
        res[[i for i,x in enumerate(res) if x[0] == 'none'][0]] = ('none', 'Free Communication')
        res.append(('bba', 'BBA Structured Communication'))
        #logger.notifyChannel('addons.'+self._name, netsvc.LOG_WARNING, 'reference_type =  %s' %res ) 
        return res

    def check_bbacomm(self, val):
        supported_chars = '0-9+*/ '
        pattern = re.compile('[^' + supported_chars + ']')
        if pattern.findall(val or ''):
            return False                
        bbacomm = re.sub('\D', '', val or '')
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97      
            if mod == int(bbacomm[-2:]):
                return True
        return False

    def _check_communication(self, cr, uid, ids):
        for inv in self.browse(cr, uid, ids):
            if inv.reference_type == 'bba':
                return self.check_bbacomm(inv.reference)
        return True

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):       
        result = super(account_invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id,
            date_invoice, payment_term, partner_bank_id, company_id)
#        reference_type = self.default_get(cr, uid, ['reference_type'])['reference_type']
#        logger.notifyChannel('addons.'+self._name, netsvc.LOG_WARNING, 'partner_id %s' % partner_id)
        reference = False
        reference_type = 'none'
        if partner_id:        
            if (type == 'out_invoice'):
                reference_type = self.pool.get('res.partner').browse(cr, uid, partner_id).out_inv_comm_type
                if reference_type:
                    algorithm = self.pool.get('res.partner').browse(cr, uid, partner_id).out_inv_comm_algorithm
                    if not algorithm:
                        algorithm = 'random' 
                    reference = self.generate_bbacomm(cr, uid, ids, type, reference_type, algorithm, partner_id, '')['value']['reference']
        res_update = {       
            'reference_type': reference_type or 'none',
            'reference': reference,
        }
        result['value'].update(res_update)
        return result                    

    def generate_bbacomm(self, cr, uid, ids, type, reference_type, algorithm, partner_id, reference):
        partner_obj =  self.pool.get('res.partner')
        reference = reference or ''  
        if (type == 'out_invoice'):
            if reference_type == 'bba':
                if not algorithm:
                    if partner_id:
                        algorithm = partner_obj.browse(cr, uid, partner_id).out_inv_comm_algorithm
                    if not algorithm:
                        if not algorithm:   
                            algorithm = 'random'
                if algorithm == 'date':
                    if not self.check_bbacomm(reference):
                        doy = time.strftime('%j')
                        year = time.strftime('%Y')
                        seq = '001'
                        seq_ids = self.search(cr, uid, 
                            [('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                             ('reference', 'like', '+++%s/%s/%%' % (doy, year))], order='reference')
                        if seq_ids:
                            prev_seq = int(self.browse(cr, uid, seq_ids[-1]).reference[12:15])
                            if prev_seq < 999:
                                seq = '%03d' % (prev_seq + 1)
                            else:
                                raise osv.except_osv(_('Warning!'),
                                    _('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!' \
                                      '\nPlease create manually a unique BBA Structured Communication.'))
                        bbacomm = doy + year + seq
                        base = int(bbacomm)
                        mod = base % 97 or 97   
                        reference = '+++%s/%s/%s%02d+++' % (doy, year, seq, mod)
                elif algorithm == 'partner_ref':
                    if not self.check_bbacomm(reference):
                        partner_ref = self.pool.get('res.partner').browse(cr, uid, partner_id).ref
                        partner_ref_nr = re.sub('\D', '', partner_ref or '')
                        if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
                            raise osv.except_osv(_('Warning!'),
                                _('The Partner should have a 3-7 digit Reference Number for the generation of BBA Structured Communications!' \
                                  '\nPlease correct the Partner record.'))                            
                        else:
                            partner_ref_nr = partner_ref_nr.ljust(7, '0')
                            seq = '001'
                            seq_ids = self.search(cr, uid, 
                                [('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                                 ('reference', 'like', '+++%s/%s/%%' % (partner_ref_nr[:3], partner_ref_nr[3:]))], order='reference')                            
                            if seq_ids:
                                prev_seq = int(self.browse(cr, uid, seq_ids[-1]).reference[12:15])
                                if prev_seq < 999:
                                    seq = '%03d' % (prev_seq + 1)
                                else:
                                    raise osv.except_osv(_('Warning!'),
                                        _('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!' \
                                          '\nPlease create manually a unique BBA Structured Communication.'))                            
                        bbacomm = partner_ref_nr + seq
                        base = int(bbacomm)
                        mod = base % 97 or 97                           
                        reference = '+++%s/%s/%s%02d+++' % (partner_ref_nr[:3], partner_ref_nr[3:], seq, mod)
                elif algorithm == 'random':
                    if not self.check_bbacomm(reference):
                        base = random.randint(1, 9999999999)
                        bbacomm = str(base).rjust(7, '0')
                        base = int(bbacomm)
                        mod = base % 97 or 97
                        mod = str(mod).rjust(2, '0')               
                        reference = '+++%s/%s/%s%s+++' % (bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
                else:
                    raise osv.except_osv(_('Error!'),
                        _("Unsupported Structured Communication Type Algorithm '%s' !" \
                          "\nPlease contact your OpenERP support channel.") % algorithm)   
        return {'value': {'reference': reference}}    
    
    def create(self, cr, uid, vals, context=None):
        if vals.has_key('reference_type'):
            reference_type = vals['reference_type']
            if reference_type == 'bba':               
                if vals.has_key('reference'):
                    bbacomm = vals['reference']
                else:
                    raise osv.except_osv(_('Warning!'),
                        _('Empty BBA Structured Communication!' \
                          '\nPlease fill in a unique BBA Structured Communication.'))       
                if self.check_bbacomm(bbacomm):
                    reference = re.sub('\D', '', bbacomm)
                    vals['reference'] = '+++' + reference[0:3] + '/' + reference[3:7] + '/' + reference[7:] + '+++'     
                    same_ids = self.search(cr, uid, 
                        [('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                         ('reference', '=', vals['reference'])])
                    if same_ids:
                        raise osv.except_osv(_('Warning!'),
                            _('The BBA Structured Communication has already been used!' \
                              '\nPlease create manually a unique BBA Structured Communication.'))                 
        return super(account_invoice, self).create(cr, uid, vals, context=context)     

    def write(self, cr, uid, ids, vals, context={}):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for inv in self.browse(cr, uid, ids, context):    
            if vals.has_key('reference_type'):
                reference_type = vals['reference_type']
            else:    
                reference_type = inv.reference_type or ''
            if reference_type == 'bba':               
                if vals.has_key('reference'):
                    bbacomm = vals['reference']
                else:
                    bbacomm = inv.reference or ''
                if self.check_bbacomm(bbacomm):
                    reference = re.sub('\D', '', bbacomm)
                    vals['reference'] = '+++' + reference[0:3] + '/' + reference[3:7] + '/' + reference[7:] + '+++'     
                    same_ids = self.search(cr, uid, 
                        [('id', '!=', inv.id), ('type', '=', 'out_invoice'), 
                         ('reference_type', '=', 'bba'), ('reference', '=', vals['reference'])])
                    if same_ids:
                        raise osv.except_osv(_('Warning!'),
                            _('The BBA Structured Communication has already been used!' \
                              '\nPlease create manually a unique BBA Structured Communication.'))                 
        return super(account_invoice, self).write(cr, uid, ids, vals, context)    

    _columns = {
        'reference': fields.char('Communication', size=64, help="The partner reference of this invoice."),
        'reference_type': fields.selection(_get_reference_type, 'Communication Type',
            required=True),
    }
    
    _constraints = [
        (_check_communication, 'Invalid BBA Structured Communication !', ['Communication']),
        ]

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
