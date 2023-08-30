# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class book_salesman(osv.osv):
    
    def _check_sequence(self,cr,uid,ids):
        for book in self.browse(cr, uid, ids):
            if (book.to_seq - book.from_seq < 0 or book.from_seq < 0 or book.padding<=0):
                return False
            else:
                return True
    
    _name="book.salesman"
    _columns={
        "receipt_ids":fields.one2many('receipt.salesman','book_id','Receipt Salesman'),
        'name':fields.char('Name', size=15, required=False, readonly=True, states={'draft':[('readonly',False)]}),
        "state": fields.selection([('draft','Draft'),('open','Open'),('process','Process'),('missing','Missing'), ('cancel','Canceled')],'State', readonly=True),
        "from_seq":fields.integer("From", readonly=True, states={'draft':[('readonly',False)]}),
        "to_seq":fields.integer("To", readonly=True, states={'draft':[('readonly',False)]}),
        "padding":fields.integer("padding", readonly=True, states={'draft':[('readonly',False)]}),
        "salesman_id":fields.many2one('salesman.salesman','Collector', readonly=True, states={'draft':[('readonly',False)]}),
        "credit_user_id":fields.many2one('res.users','Credit Official'),
        "delivery_date": fields.date("Delivery Date", readonly=True, states={'draft':[('readonly',False)]}),
        "return_date": fields.date("Return Date", readonly=True),
        'type':fields.selection([
            ('point_sale','Point Of Sale'),
            ('distribution','Distribution'),],'Type of Book', readonly=True, states={'draft':[('readonly',False)]}, help="Select the type of Book Salesman for what is to be used"),
    }
    
    _defaults={
        "state": lambda *a: "draft",
        "credit_user_id": lambda obj, cr, uid, context: uid,
        "delivery_date": lambda *a: time.strftime('%Y-%m-%d'),
        "padding": lambda *a: 9,
    }
    
    _constraints = [(_check_sequence,'the sequences information is incorrect',['from_seq', 'to_seq','padding'])]


    def get_id(self, book, number, padding):
        return book + '-'+'%%0%sd' % padding % number
    
    
    def on_change_salesman(self, cr, uid, ids, salesman=None, context=None):
        result = {}
        if salesman:
            primera=0
            ultima=0
            range_default=99
            book_ant = self.pool.get('book.salesman').search(cr, uid, [('salesman_id','=', salesman )])
            if not book_ant:
                primera=1
            else:
                for book in self.pool.get('book.salesman').browse(cr, uid, book_ant , context=context):
                    if primera < book.to_seq:
                        primera= book.to_seq+1
            ultima=primera + range_default
            result['to_seq'] = ultima
            result['from_seq'] = primera
        return {'value':result}

    def check_information(self, cr, uid, ids):
        book = self.browse(cr, uid, ids)[0]
        if not book.salesman_id:
            raise osv.except_osv(_('Error!'), _('You must select one collector to open the book salesman!'))
            return False
        if not book.credit_user_id:
            raise osv.except_osv(_('Error!'), _('You must select one Credit official to open the book salesman!'))
            return False
        if not book.delivery_date:
            self.write(cr, uid, book.id, {'delivery_date':time.strftime('%Y-%m-%d'),})
        return True
    
    def button_set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_delete(uid, 'book.salesman', id, cr)
            wf_service.trg_create(uid, 'book.salesman', id, cr)
        return True
    
    
    def action_open(self, cr, uid, ids):
        receipt_obj=self.pool.get('receipt.salesman')
        number=0
        sequence=0
        for book in self.browse(cr, uid, ids, context=None):
            if not book.from_seq or not book.to_seq or not book.padding:
                raise osv.except_osv(_('Error!'), _('The information of sequence is incorrect!'))
            book_act = self.pool.get('book.salesman').search(cr, uid, [('salesman_id','=', book.salesman_id.id),('state','=','open')])
            if book_act:
                raise osv.except_osv(_('Error!'), _('You can not give this book while there is another book salesman active!'))
            number=book.from_seq
            while number<= book.to_seq:
                sequence=self.get_id(book.name,number, book.padding)
                receipt_obj.create(cr, uid, {'name':sequence,
                                             'state':'open',
                                             'received_date':book.delivery_date,
                                             'book_id':book.id,
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
                        wf_service.trg_validate(uid, 'receipt.salesman', receipt.id, 'button_canceled', cr)
        self.write(cr, uid, ids, {'state':'process', 'return_date':time.strftime('%Y-%m-%d')})
        return True

    def action_missing(self, cr, uid, ids):
        wf_service = netsvc.LocalService("workflow")
        for book in self.browse(cr, uid, ids, context=None):
            if book.receipt_ids:
                for receipt in book.receipt_ids:
                    if receipt.state == 'open':
                        wf_service.trg_validate(uid, 'receipt.salesman', receipt.id, 'button_missing', cr)
        self.write(cr, uid, ids, {'state':'missing','return_date':time.strftime('%Y-%m-%d')})
        return True
    
    def action_canceled(self, cr, uid, ids):
        receipt_ids=[]
        for book in self.browse(cr, uid, ids, context=None):
            if book.receipt_ids:
                for receipt in book.receipt_ids:
                    if receipt.state != 'open':
                        raise osv.except_osv(_('Error!'), _('You can not cancel book salesman with receipts used!'))
                    receipt_ids.append(receipt.id)
        self.pool.get('receipt.salesman').unlink(cr, uid,receipt_ids, context=None)
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
book_salesman()

class receipt_salesman(osv.osv):
    _name="receipt.salesman"
    _columns={
        "voucher_id": fields.many2one("account.voucher","Payments"),
        "book_id":fields.many2one('book.salesman','Salesman Book', ondelete='cascade'),
        'name':fields.char('Number', size=60, required=True),
        "state": fields.selection([('open','Open'),('process','Process'),('cancel','Cancel'),('annulled','Annulled'),('missing','Missing')],'State', readonly=True),
        "salesman_id":fields.related('book_id','salesman_id',type='many2one', relation='salesman.salesman',string='Collector',store=True),
        "bank_statement": fields.many2one('account.bank.statement','Cash Box'),
        "received_date": fields.date("Received Date"),
        "process_date": fields.date("Proccess Date"),
        "partner_id": fields.many2one("res.partner","Partner"),
        'emission_date': fields.date('Emission Date'),
        'type': fields.related('book_id','type', type='selection', selection=[('point_sale','Point Of Sale'),('distribution','Distribution')], readonly=True, store=True, string='Type Receipt'),
    }
    
    _sql_constraints = [('name_receipt_uniq', 'unique (name)','The number of receipt must be unique!')]
    
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
            wf_service.trg_delete(uid, 'receipt.salesman', receip, cr)
            wf_service.trg_create(uid, 'receipt.salesman', receip, cr)
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        receipt = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for rec in receipt:
            if rec['state'] == 'open':
                unlink_ids.append(rec['id'])
            else:
                raise osv.except_osv(_('Invalid action!'), _('You can delete receipt in state Open'))
        return super(receipt_salesman, self).unlink(cr, uid, unlink_ids, context)
    
receipt_salesman()