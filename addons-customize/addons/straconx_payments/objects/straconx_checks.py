# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-2011 STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
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

from osv import fields, osv
import netsvc
import time
from tools.translate import _

class check_book(osv.osv):
    
    def _check_sequence(self,cr,uid,ids):
        for book in self.browse(cr, uid, ids):
            if (book.to_seq - book.from_seq < 0 or book.from_seq < 0 or book.padding<=0):
                return False
            else:
                return True
    
    def _get_salesman(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('salesman.salesman').search(cr, uid, [('user_id','=', uid)])[0]    
        user = self.pool.get('salesman.salesman').browse(cr, uid, user, context)
        if user:
            return user.id
        return None
    
    _name="check.book"
    _columns={
        "receipt_ids":fields.one2many('check.receipt','book_id','Documents',states={'draft':[('readonly',False)]}),
        "mode_id":fields.many2one('payment.mode','Modo de pago', ondelete='cascade'),
#        'name':fields.char('Name', size=15, required=False, readonly=True, states={'draft':[('readonly',False)]}),
        "name": fields.many2one("res.partner.bank","Account Bank", readonly=True, states={'draft':[('readonly',False)]}),
        "bank": fields.many2one("res.bank","Bank", readonly=True, states={'draft':[('readonly',False)]}),
        "state": fields.selection([('draft','Draft'),('open','Open'),('process','Process'),('missing','Missing'), ('cancel','Canceled')],'State', readonly=True),
        "from_seq":fields.integer("From", readonly=True, states={'draft':[('readonly',False)]}),
        "to_seq":fields.integer("To", readonly=True, states={'draft':[('readonly',False)]}),
        "padding":fields.integer("padding", readonly=True, states={'draft':[('readonly',False)]}),
        "salesman_id":fields.many2one('salesman.salesman','Treasurer', readonly=True, states={'draft':[('readonly',False)]}),
        "delivery_date": fields.date("Open Date", readonly=True, states={'draft':[('readonly',False)]}),
        "return_date": fields.date("End Date", readonly=True),
        'company_id': fields.many2one('res.company', 'Company', required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
        'automatic':fields.boolean('automatic'),
        's_sequence':fields.boolean('Salto de Secuencia'),
        'type':fields.selection([
             ('cheque','Cheque'),
             ('debit','debit')],'Type of Book', readonly=True, states={'draft':[('readonly',False)]}, help="Select the type of Cheque Book for what is to be used"),
    }
    
    _defaults={
        "state": lambda *a: "draft",
        'salesman_id': _get_salesman,
        "delivery_date": lambda *a: time.strftime('%Y-%m-%d'),
        "padding": lambda *a: 3,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'check.book', context=c),
    }
    
    _constraints = [(_check_sequence,'the sequences information is incorrect',['from_seq', 'to_seq','padding'])]


    def get_id(self, book, number, padding):
        return '%%0%sd' % padding % number
    
    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        bank_type_obj = self.pool.get('check.book').browse(cr,uid,ids[0],context)
        res = []
        if bank_type_obj:
            try:
                if bank_type_obj.name:
                    val = ids[0]
                    account = bank_type_obj.name.acc_number or None
                    bank =  bank_type_obj.bank.name or None
                    result = bank +': cta.' + ' - ' +account
                else:
                    val = False
                    result = None                 
                res.append((val, result))                
                return res
            except:
                raise osv.except_osv(_('Error!'), _('Review your checks books!'))
                    

    def onchange_name(self, cr, uid, ids, name=False, company_id=False, context=None):
        result = {}
        warning = {}
        if company_id:
            comp = self.pool.get('res.company').browse(cr,uid,company_id,context).partner_id.id
        else:
            raise osv.except_osv(_('Error!'), _('You need a select a company for continue!'))
        if name:
            bank_search = self.pool.get('res.partner.bank').browse(cr,uid,name,context)
            bank_account = bank_search.bank.id
            bank_partner = bank_search.partner_id.id
            if  bank_partner:
                if bank_partner <> comp:
                    warning = {'title': _('Partner different!'),'message': _(('Partner of bank account is different to Partner Company.'))}
            result['bank'] = bank_account 
        return {'value':result,'warning':warning}
            
    def on_change_salesman(self, cr, uid, ids, salesman=None, context=None):
        result = {}
        if salesman:
            primera=0
            ultima=0
            range_default=99
            book_ant = self.pool.get('check.book').search(cr, uid, [('salesman_id','=', salesman )])
            if not book_ant:
                primera=1
            else:
                for book in self.pool.get('check.book').browse(cr, uid, book_ant , context=context):
                    if primera < book.to_seq:
                        primera= book.to_seq+1
            ultima=primera + range_default
            result['to_seq'] = ultima
            result['from_seq'] = primera
        return {'value':result}

    def check_information(self, cr, uid, ids):
        book = self.browse(cr, uid, ids)[0]
        if not book.salesman_id:
            raise osv.except_osv(_('Error!'), _('You must select one Treasurer to open the cheque book!'))
            return False
#        if not book.credit_user_id:
#            raise osv.except_osv(_('Error!'), _('You must select one Credit official to open the book salesman!'))
#            return False
        if not book.delivery_date:
            self.write(cr, uid, book.id, {'delivery_date':time.strftime('%Y-%m-%d'),})
        return True
    
    def button_set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_delete(uid, 'check.book', id, cr)
            wf_service.trg_create(uid, 'check.book', id, cr)
        return True
    
    
    def action_open(self, cr, uid, ids):
        receipt_obj=self.pool.get('check.receipt')
        number=0
        sequence=0
        for book in self.browse(cr, uid, ids, context=None):
            if not book.from_seq or not book.to_seq or not book.padding:
                raise osv.except_osv(_('Error!'), _('The information of sequence is incorrect!'))
            book_act = self.pool.get('check.book').search(cr, uid, [('name','=',book.name.id),('salesman_id','=', book.salesman_id.id),('state','=','open')])
            if book_act:
                raise osv.except_osv(_('Error!'), _('You can not give this cheque book while there is another cheque book active!'))
            number=book.from_seq
            while number<= book.to_seq:
                sequence=self.get_id(book.name,number, book.padding)
                receipt_obj.create(cr, uid, {'name':sequence,
                                             'state':'open',
                                             'received_date':book.delivery_date,
                                             'book_id':book.id,
                                             'partner_id':book.name.id,
                                             'beneficiary_id':''
                                             })
                number+=1
        self.write(cr, uid, ids, {'state':'open'})
        return True
    
    def action_process(self, cr, uid, ids):
        wf_service = netsvc.LocalService("workflow")
        for book in self.browse(cr, uid, ids, context=None):
            if book.receipt_ids:
                for receipt in book.receipt_ids:
                    if receipt.state == 'open':
                        wf_service.trg_validate(uid, 'check.receipt', receipt.id, 'button_canceled', cr)
        self.write(cr, uid, ids, {'state':'process', 'return_date':time.strftime('%Y-%m-%d')})
        return True

    def action_missing(self, cr, uid, ids):
        wf_service = netsvc.LocalService("workflow")
        for book in self.browse(cr, uid, ids, context=None):
            if book.receipt_ids:
                for receipt in book.receipt_ids:
                    if receipt.state == 'open':
                        wf_service.trg_validate(uid, 'check.receipt', receipt.id, 'button_missing', cr)
        self.write(cr, uid, ids, {'state':'missing','return_date':time.strftime('%Y-%m-%d')})
        return True
    
    def action_canceled(self, cr, uid, ids):
        receipt_ids=[]
        for book in self.browse(cr, uid, ids, context=None):
            if book.receipt_ids:
                for receipt in book.receipt_ids:
                    if receipt.state != 'open':
                        raise osv.except_osv(_('Error!'), _('You can not cancel cheque book with cheques used!'))
                    receipt_ids.append(receipt.id)
        self.pool.get('check.receipt').unlink(cr, uid,receipt_ids, context=None)
        self.write(cr, uid, ids, {'state':'cancel'})
        return True

    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        payment = self.pool.get('payment.mode').search(cr,uid,[('bank_id','=',ids)])
        for book in self.browse(cr, uid, ids, context=context):            
            if book.state == 'draft':
                unlink_ids.append(book['id'])
                if payment:
                    self.pool.get('payment.mode').write(cr,uid,payment[0],{'bank_id':None})
            else:
                raise osv.except_osv(_('Invalid action !'), _('Only Can delete Cheques Book(s) in state draft !'))
        return super(check_book,self).unlink(cr, uid, unlink_ids, context=context)

check_book()

class check_receipt(osv.osv):
    _name="check.receipt"
    _columns={
        "voucher_id": fields.many2one("account.voucher","Payments"),
        "book_id":fields.many2one('check.book','Cheque Book', ondelete='cascade'),
        'name':fields.char('Number', size=60, required=True),
        "state": fields.selection([('open','Open'),('process','Process'),('paid','Paid'),('cancel','Cancel'),('annulled','Annulled'),('missing','Missing')],'State', readonly=True),
        "salesman_id":fields.related('book_id','salesman_id',type='many2one', relation='salesman.salesman',string='Treasure',store=True),
        "bank_statement": fields.many2one('account.bank.statement','Cash Box'),
        "amount":fields.float('Amount', readonly=True, states={'draft':[('readonly',False)]}),        
        "received_date": fields.date("Received Date"),
        "process_date": fields.date("Proccess Date"),
        "anulled_date": fields.date("Anulled Date"),
        "partner_id": fields.many2one("res.partner.bank","Account Bank"),
        "beneficiary_id": fields.char('Beneficiario', size=240, required=True),
        'emission_date': fields.date('Emission Date'),
        'type': fields.related('book_id','type', type='selection', selection=[('cheque','Cheque'),('debit','debit')], readonly=True, store=True, string='Type Book'),
    }
    
    _sql_constraints = [('name_receipt_uniq', 'unique (name, partner_id)','The number of cheque must be unique for each Bank!')]
    
    def action_process(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'process'})
        return True
    
    def action_annulled(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'annulled'})
        return True
    
    def action_missing(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'missing'})
        return True
    
    def action_canceled(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
    def set_to_open(self, cr, uid, ids, context):
        self.write(cr, uid, ids, {'state':'open'})
        wf_service = netsvc.LocalService("workflow")
        for receip in ids:
            wf_service.trg_delete(uid, 'check.receipt', receip, cr)
            wf_service.trg_create(uid, 'check.receipt', receip, cr)
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        receipt = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for rec in receipt:
            if rec['state'] == 'open':
                unlink_ids.append(rec['id'])
            else:
                raise osv.except_osv(_('Invalid action!'), _('You can delete receipt in state Open'))
        return super(check_receipt, self).unlink(cr, uid, unlink_ids, context)
    
check_receipt()