# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
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
from tools.translate import _
import time
from datetime import date
from datetime import datetime
import base64
import StringIO
from time import strftime
from string import upper
from string import join
import decimal_precision as dp

class hr_provision(osv.osv):
    
    _name="hr.provision"
    _columns={
        'name': fields.selection([("XIII","XIII"),("XIV","XIV"),("VACACIONES","VACACIONES"),("UTITLIDADES","UTILIDADES")],"Nombre"),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'date_from_coast': fields.date('Date From Coast',readonly=False),
        'date_to_coast': fields.date('Date to Coast',readonly=False),
        'date_from_sie': fields.date('Date From Sierra',readonly=False),
        'date_to_sie': fields.date('Date to Sierra',readonly=False),
        'date_from': fields.date('Date From',readonly=False),
        'date_to': fields.date('Date to',readonly=False),
        'account_id':fields.many2one('account.account','Account'),
        'pay_prov': fields.boolean('Pay Provision', readonly = False),

    }  
    
    _defaults = {
                 'name': 'XIII',
                 'pay_prov': True
                 
                 } 
    def change_date (self, cr, uid, ids, prov=None,y_from =False,y_to=False,  context =None):              
        date = time.strftime('%Y-%m-%d')
        date = datetime.strptime(date[0:10],"%Y-%m-%d")
        prov_id = self.browse(cr,uid,prov)
        if prov_id:
            y_from += 1
            y_to += 1
            if prov_id.name == 'XIV':
                #COSTA
                date_f_c = prov_id.date_from_coast
                date_t_c = prov_id.date_to_coast
                date_from = str(y_from) +'-'+date_f_c[5:7]+'-'+date_f_c[8:10]                
                date_from_c = datetime.strptime(date_from[0:10],"%Y-%m-%d")                
                date_to = str(y_to) +'-'+date_t_c[5:7]+'-'+date_t_c[8:10]                
                date_to_c = datetime.strptime(date_to[0:10],"%Y-%m-%d")
                #SIERRA
                date_f_s = prov_id.date_from_sie                       
                date_t_s = prov_id.date_to_sie
#                 date_f_s = date_f_s.strftime("%Y-%m-%d")          
#                 date_t_s = date_t_s.strftime("%Y-%m-%d")
                date_from = str(y_from) +'-'+date_f_s[5:7]+'-'+date_f_s[8:10]                
                date_from_s = datetime.strptime(date_from[0:10],"%Y-%m-%d")                
                date_to = str(y_to) +'-'+date_t_s[5:7]+'-'+date_t_s[8:10]                
                date_to_s = datetime.strptime(date_to[0:10],"%Y-%m-%d")
                self.write(cr,uid,[prov_id.id],{'date_from_coast':date_from_c,
                                                'date_to_coast':date_to_c,
                                                'date_from_sie':date_from_s,
                                                'date_to_sie':date_to_s,
                                                })
            if prov_id.name == 'XIII':
                date_f = prov_id.date_from                  
                date_t = prov_id.date_to
                date_from = str(y_from) +'-'+date_f[5:7]+'-'+date_f[8:10]                
                date_from = datetime.strptime(date_from[0:10],"%Y-%m-%d")                
                date_to = str(y_to) +'-'+date_t[5:7]+'-'+date_t[8:10]                
                date_to = datetime.strptime(date_to[0:10],"%Y-%m-%d")
                self.write(cr,uid,[prov_id.id],{'date_from':date_from,
                                                'date_to':date_to
                                                })
            
        return True 
    
    def onchange_boolean (self, cr, uid, ids, name, context = None):
        
        res = {}
        if name == 'XIII' or name == 'XIV':
            res['pay_prov'] = True
        else:
            res['pay_prov'] = False    
        return {'values':res}
hr_provision()

class hr_pay_provision(osv.osv):
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal=self.pool.get('account.journal').search(cr, uid, [('type','=','salary_employee')])
        if not journal:
            return None
        return journal[0]
    
    def _total_amount(self, cr, uid, ids, name, args, context):
        result = {}
        for pay in self.browse(cr, uid, ids, context=context):
            result[pay.id] = {
                                'total_amount': 0.0,
                                'total_bank': 0.0,
                              }
            for line in pay.line_ids:
                if line.employee_id.bank_account_id:
                    result[pay.id]['total_bank'] += line.amount_total
                result[pay.id]['total_amount'] += line.amount_total
        return result
    
    _name="hr.pay.provision"
    _columns={
        'provision_id':fields.many2one('hr.provision', 'Name', readonly=True, states={'draft':[('readonly',False)]}),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=False, states={'draft':[('readonly',False)]}),
        'employee_id':fields.many2one('hr.employee', 'Employee', readonly=True, states={'draft':[('readonly',False)]}),
        'date_from': fields.date('Date From',readonly=False, states={'draft':[('readonly',False)]}),
        'date_to': fields.date('Date to',readonly=False, states={'draft':[('readonly',False)]}),
        "reference":fields.char('Reference', size=64, required=False,readonly=True, states={'draft':[('readonly',False)]}),
        "name":fields.char('Name', size=64, required=False,readonly=True, states={'draft':[('readonly',False)]}),
        "line_ids":fields.one2many('hr.pay.provision.line','pay_provision_id','Pay Provision Line',readonly=True, states={'draft':[('readonly',False)]}),
        "check_ids":fields.one2many('account.payments','provision_id','Checks Provision',readonly=True, states={'draft':[('readonly',False)]}),
        "period_id":fields.many2one('account.period','Period',readonly=True, states={'draft':[('readonly',False)]}),
        "company_id":fields.many2one('res.company','Company', required = True,states={'draft':[('readonly',False)]}),
        "journal_id":fields.many2one('account.journal','Journal',readonly=True, states={'draft':[('readonly',False)]}),
        'move_id':fields.many2one('account.move', 'Reference Account Move'),
        'debit_note_id':fields.many2one('account.debit.note', 'Reference Account Move'),
        "state": fields.selection([('draft','Draft'),('close','Close'),('paid','Paid')],'State', readonly=True),
        "total_amount": fields.function(_total_amount, method=True,type="float", string='Total Amount', multi="total_amount",),
        "total_bank": fields.function(_total_amount, method=True,type="float", string='Total Amount', multi="total_bank",),
        'data':fields.binary('File', readonly=True),
        'check':fields.boolean('check', required=False),
        'region_id':fields.many2one('res.region','Region', required = True,readonly = False, states={'draft':[('readonly',False)]}),
        'moves_ids':fields.one2many('account.move', 'pays_run_id', 'Movimientos', required=False),
        'debit_note_ids':fields.one2many('account.debit.note', 'payslip_run_id', 'Egresos', required=False),
        
    }
    
    _rec_name='provision_id'
    
    _defaults={
        "state": lambda *a: "draft",
        "company_id": lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        "partner_id": lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.partner_id.id,
        "region_id": lambda self, cr, uid, context: self.pool.get('res.region').browse(cr, uid, uid).id,
        "period_id": lambda self, cr, uid, context: self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d'))])[0] or False,
        'journal_id':_get_journal,
        'check':False,        
        'date_from': time.strftime('%Y-%m-%d'),
        'date_to' : time.strftime('%Y-%m-%d')
    }
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not len(ids):
            return []
        for pay in self.browse(cr, uid, ids, context):
            name=""
            if pay.provision_id:
                name=name+"%s"%(pay.provision_id.name)
            res.append((pay.id, name))
        return res
    
    def onchange_provision (self, cr, uid, ids, provision_id=False, context=None):
        res = {}
        provision = self.pool.get('hr.provision')
        prov_id = provision.browse(cr, uid, provision_id)
        name = _('Pago de %s') % (prov_id.name)  
        res['check']= prov_id.pay_prov
        res['reference']= name 
        return {'value':res}
        
    def onchange_date (self, cr, uid, ids,region_id=False,provision_id=False,company_id=False, date_from=False, date_to=False, partner_id=False, period_id = False, journal_id =False, context=None):
        res = {}  
        reg_ids = []      
        date = time.strftime('%Y-%m-%d')
        date = datetime.strptime(date[0:10],"%Y-%m-%d")
        date_to = time.strftime('%Y-%m-%d')
        provision = self.pool.get('hr.provision') 
        reg_obj = self.pool.get('res.region')
        shop_obj = self.pool.get('sale.shop')
        if not company_id:
            company_id =  self.pool.get('res.users').browse(cr, uid, uid).company_id.id       
        if not (provision.browse(cr, uid, provision_id)) and not (provision.search(cr, uid, [('company_id','=',company_id)])):
            raise osv.except_osv(_('Error'), _('Primero debe configurar la provisión'))    
        if not provision_id or provision.browse(cr, uid, provision_id).company_id.id != company_id:  
            prov = provision.search(cr, uid, [('company_id','=',company_id)])
            if not provision.search(cr, uid, [('company_id','=',company_id)]):
                raise osv.except_osv(_('Error'), _('No existe provisiones creadas para esta compañía'))   
            for pro_id in provision.browse(cr, uid, prov):
                prov_id = pro_id
                break
        else:
            prov_id = provision.browse(cr, uid, provision_id)    
        if not region_id: 
             shop_id = shop_obj.search(cr, uid, [('company_id','=',company_id)])
             if not shop_id:
                 raise osv.except_osv(_('Error'), _('Las tiendas de esta compañía no tienen asignada una región'))
             for shop in shop_obj.browse(cr, uid, shop_id):
                reg = shop.partner_address_id.region_id
                break
        else:
            reg =  reg_obj.browse(cr, uid,region_id)       
        if prov_id:
           if prov_id.name == 'XIV':
               if reg.name == 'SIERRA' or reg.name == 'ORIENTE':
                   date1 = datetime.strptime(prov_id.date_from_sie[0:10],"%Y-%m-%d")
                   date_1 = date1.strftime("%Y-%m-%d")
                   if date1.year == ((date.year)-1):
                       year1 = date1.year
                   else:
                       year1 = date.year - 1
                   date_f = str(year1) +'-'+date_1[5:7]+'-'+date_1[8:10]
                   date_from = datetime.strptime(date_f[0:10],"%Y-%m-%d")
                   date_from = date_from.strftime("%Y-%m-%d")
                   date2 = datetime.strptime(prov_id.date_to_sie[0:10],"%Y-%m-%d")
                   date_2 = date2.strftime("%Y-%m-%d")
                   year2 = date.year
                   date_t = str(year2) +'-'+date_2[5:7]+'-'+date_2[8:10]
                   date_to = datetime.strptime(date_t[0:10],"%Y-%m-%d")
                   date_to = date_to.strftime("%Y-%m-%d")
               else:
                   date1 = datetime.strptime(prov_id.date_from_coast[0:10],"%Y-%m-%d")
                   date_1 = date1.strftime("%Y-%m-%d")                   
                   if date1.year == ((date.year)-1):
                       year1 = date1.year
                   else:
                       year1 = date.year - 1
                   date_f = str(year1) +'-'+date_1[5:7]+'-'+date_1[8:10]
                   date_from = datetime.strptime(date_f[0:10],"%Y-%m-%d")
                   date_from = date_from.strftime("%Y-%m-%d")
                   date2 = datetime.strptime(prov_id.date_to_coast[0:10],"%Y-%m-%d")
                   date_2 = date2.strftime("%Y-%m-%d")
                   year2 = date.year
                   date_t = str(year2) +'-'+date_2[5:7]+'-'+date_2[8:10]
                   date_to = datetime.strptime(date_t[0:10],"%Y-%m-%d")
                   date_to = date_to.strftime("%Y-%m-%d")                     
           if prov_id.name == 'XIII':  
               date1 = datetime.strptime(prov_id.date_from[0:10],"%Y-%m-%d")
               date_1 = date1.strftime("%Y-%m-%d")
               if date1.year == ((date.year)-1):
                   year1 = date1.year
               else:
                   year1 = date.year - 1 
               date_f = str(year1) +'-'+date_1[5:7]+'-'+date_1[8:10]
               date_from = datetime.strptime(date_f[0:10],"%Y-%m-%d")
               date_from = date_from.strftime("%Y-%m-%d")
               date2 = datetime.strptime(prov_id.date_to[0:10],"%Y-%m-%d")
               date_2 = date2.strftime("%Y-%m-%d")
               year2 = date.year 
               date_t = str(year2) +'-'+date_2[5:7]+'-'+date_2[8:10]
               date_to = datetime.strptime(date_t[0:10],"%Y-%m-%d")
               date_to = date_to.strftime("%Y-%m-%d")   
        journal_obj = self.pool.get('account.journal')
        journal_id = journal_obj.search(cr, uid, [('company_id','=',company_id)])
        for journal in journal_obj.browse(cr, uid, journal_id):
            if company_id == 1 and journal.code == 'SEMP' or company_id == 2 and journal.code == 'SEQV':
                jour_id= journal.id         
        period_obj = self.pool.get('account.period')
        period_id = period_obj.search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')),('company_id','=',company_id)])
        for period in period_obj.browse(cr, uid, period_id):
            per_id= period.id 
        comp_obj = self.pool.get('res.company')
        comp_id =  comp_obj.browse(cr, uid, company_id)
        partner = comp_id.partner_id.id  
        name = _('Pago de %s') % (prov_id.name)  
        res['date_from']= date_from
        res['date_to']= date_to
        return {'value':res}
    
    def formato_numero(self, valor):
        tup = valor.split('.')
        valor = ''.join(tup)
        if len(tup[1])== 1:
            return valor+"0"
        return valor
    

    
    def draft_pay_provision_run(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        reconcile_pool = self.pool.get('account.move.reconcile')
        for pay in self.browse(cr, uid, ids, context):
            remove_reconcile = []
            for line in pay.line_ids:
                if line.move_line_id.reconcile_id:
                    remove_reconcile += [line.move_line_id.reconcile_id.id]
                if line.move_line_id.reconcile_partial_id:
                    remove_reconcile += [line.move_line_id.reconcile_partial_id.id]
            reconcile_pool.unlink(cr, uid, remove_reconcile)
            if pay.move_id:
                move_pool.button_cancel(cr, uid, [pay.move_id.id], context={})
                move_pool.unlink(cr, uid, [pay.move_id.id], context={})
            for line in pay.line_ids:
                if line.move_line_id2.reconcile_id:
                    remove_reconcile += [line.move_line_id2.reconcile_id.id]
                if line.move_line_id2.reconcile_partial_id:
                    remove_reconcile += [line.move_line_id2.reconcile_partial_id.id]
            reconcile_pool.unlink(cr, uid, remove_reconcile)
            for chk in pay.check_ids:
                if chk.state != 'draft':
                    raise osv.except_osv(_('Error'), _('You can not change to state pay provision in draft because there is a paid check'))
                else:
                    self.pool.get('account.payments').unlink(cr, uid, [chk.id], context)
                    self.pool.get('check.receipt').write(cr, uid, [chk.cheque_id.id], {'state':'open'},context=context)
#            if pay.check_id:
#                if pay.check_id.state != 'hold':
#                    raise osv.except_osv(_('Error'), _('You can not change to state pay provision in draft because there is a paid check'))
#                else:
#                    self.pool.get('account.payments').unlink(cr, uid, [pay.check_id.id], context)
        return self.write(cr, uid, ids, {'state': 'draft', 'check':False, 'data':None, 'name':None}, context=context)
    
    
    def get_employee_ids(self, cr, uid, ids, context=None): 
        pays_prov = self.browse(cr,uid,ids[0])
        contract_object = self.pool.get('hr.contract')
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        mode_obj = self.pool.get('payment.mode')
        pay_line_pool = self.pool.get('hr.pay.provision.line')
        if not pays_prov.provision_id.account_id:
            raise osv.except_osv(_("Warning !"), _("You must select account on the type of provision to pay"))
        company_id = pays_prov.company_id.id
        region= pays_prov.region_id.id
        if pays_prov.employee_id:
            employee_ids = emp_pool.search(cr,uid,[('company_id','=',company_id),('unemployee','=',False),('id','=',pays_prov.employee_id.id)])
        else:
            employee_ids = emp_pool.search(cr,uid,[('company_id','=',company_id),('unemployee','=',False)])
        if employee_ids:
            for empl_id in employee_ids:
                emp = emp_pool.browse(cr, uid, empl_id, context=context)
                if emp.shop_id.partner_address_id.region_id.id == region:
        #             line_ant_ids=pay_line_pool.search(cr, uid, [('pay_provision_id','=',pays_prov.id),('employee_id','=',empl_id.id)])
        #             if line_ant_ids:
        #                 continue
                    cont_active = contract_object.search(cr,uid,[('employee_id','=',emp.id),('contract_active','=',True)])
                    if cont_active:                    
                        if not emp.partner_id:
                            raise osv.except_osv(_('Error'), _(('the employee %s does not have a partner created')% (emp.name)))
                        contract_ids = slip_pool.get_contract(cr, uid, emp, pays_prov.date_from, pays_prov.date_to, context=context)
                        mode_id = mode_obj.search(cr, uid, [('company_id','=',company_id),('cash','=',True),('discount','=',False)])
                        mode = mode_obj.browse(cr, uid, mode_id[0])
                        sql='''SELECT am.id 
                        FROM account_move_line AS am, account_account AS a
                        WHERE am.account_id = a.id AND am.partner_id = %s 
                        AND ((am.credit > 0 AND am.reconcile_id is Null) or (am.debit >0 AND am.reconcile_id is Null)) 
                        AND a.type='other' AND am.state = 'valid' 
                        AND am.account_id=%s
                        '''
                        sql = sql + 'AND am.date >= %s AND am.date<= %s'
                        cr.execute(sql,(emp.partner_id.id,pays_prov.provision_id.account_id.id,pays_prov.date_from,pays_prov.date_to))                                        
                        atts = cr.fetchall()                
                        if atts:
                            res = {
                             'employee_id': emp.id,
                             'partner_id': emp.partner_id.id,
                             'mode_id': mode.id,
                             'contract_id':contract_ids and contract_ids[0] or cont_active[0] or False,
                             'pay_provision_id':pays_prov.id,
                             'move_line_ids':[[6, 0, [c[0] for c in atts]]]
                             }
                            pay_line_pool.create(cr, uid, res, context)
        return True     
    
    def close_pay_provision(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        lines_ids = []
        hce_obj = self.pool.get('hr.contract.expense')
        htt_obj = self.pool.get('hr.transaction.type')
        debit_note_pool = self.pool.get('account.debit.note')
        debit_note_line_pool = self.pool.get('account.debit.note.line')
        context['search_shop']=True
        date = time.strftime('%Y-%m-%d')
        value = 0.0
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        account_obj = self.pool.get('account.account')
        line_provision_obj = self.pool.get('hr.pay.provision.line')
        move_reconcile_ids = []
        for pay in self.browse(cr, uid, ids, context):
            if not pay.line_ids:
                raise osv.except_osv(_('Error'), _('You can not close a Pay-Provision without lines generated'))
            move_id = None
            amount=0.0
            move_id2=0
            move_id3=0
            move_line2=0
            move_line_iess=0
            account_id = account_obj.search(cr,uid,[('name','=','CUENTAS POR PAGAR – EMPLEADOS'),('company_id','=',pay.company_id.id)])
            for account in account_obj.browse(cr,uid,account_id):
                acc_id = account.id
            if not pay.journal_id:
                raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by pay provision'))
            name = self.pool.get('ir.sequence').next_by_id(cr, uid, pay.journal_id.sequence_id.id)
            if not pay.reference:
                ref = name
            else:
                ref = pay.reference
            move = {'name': name,
                    'journal_id': pay.journal_id.id,
                    'date': date,
                    'ref': ref,
                    'period_id': pay.period_id.id,
                    'company_id': pay.company_id.id
                    }
            move_id = move_pool.create(cr, uid, move,context=context)
            for line in pay.line_ids:
                if (not pay.provision_id.pay_prov and line.pay_aprove) or (pay.provision_id.pay_prov): 
                    if line.wk_years > 0:                                    
                        move= {'name': 'Pago Días Adicionales Vacaciones '+name,
                                'journal_id': pay.journal_id.id,
                                'date': date,
                                'ref': ref,
                                'period_id': pay.period_id.id,
                                'company_id': pay.company_id.id
                                }                        
                        move_id2 = move_pool.create(cr, uid, move,context=context)
                        
                        move_line2=move_line_pool.create(cr, uid, {
                        'name': 'Pago Días Adicionales VAC/'+ pay.period_id.name,
                        'debit': 0,
                        'credit':round(line.value_year,2),
                        'account_id': pay.provision_id.account_id.id,
                        'move_id': move_id2,
                        'journal_id': pay.journal_id.id,
                        'period_id': pay.period_id.id,
                        'partner_id': line.employee_id.partner_id.id,
                        'date': date,
                        'company_id': pay.company_id.id
                        },context=context)
                        
                        move_line_pool.create(cr, uid, {
                        'name': 'Pago Días Adicionales VAC/'+ pay.period_id.name,
                        'debit': round(line.value_year,2),
                        'credit': 0,
                        'account_id': acc_id,
                        'move_id': move_id2,
                        'journal_id': pay.journal_id.id,
                        'period_id': pay.period_id.id,
                        'partner_id': line.employee_id.partner_id.id,
                        'date': date,
                        'company_id': pay.company_id.id
                        },context=context) 
                        
                    move_line=move_line_pool.create(cr, uid, {
                        'name': ref or '/',
                        'debit': line.total_amount_provision,
                        'credit': 0,
                        'account_id': pay.provision_id.account_id.id,
                        'move_id': move_id,
                        'journal_id': pay.journal_id.id,
                        'period_id': pay.period_id.id,
                        'partner_id': line.employee_id.partner_id.id,
                        'date': date,
                        'company_id': pay.company_id.id
                        },context=context)
                    if not pay.provision_id.pay_prov:
                        account_iess_id = self.pool.get('hr.salary.rule').search(cr, uid, [('code','=','IESS')])
                        account_iess = self.pool.get('hr.salary.rule').browse(cr, uid, account_iess_id)[0].account_debit.id
                        move= {'name': 'Pago IESS Vacaciones '+name,
                                'journal_id': pay.journal_id.id,
                                'date': date,
                                'ref': ref,
                                'period_id': pay.period_id.id,
                                'company_id': pay.company_id.id
                                }                        
                        move_id3 = move_pool.create(cr, uid, move,context=context)
                        
                        move_line_iess=move_line_pool.create(cr, uid, {
                        'name': 'Pago de IESS VACACIONES',
                        'debit': round(line.iess_vac,2),
                        'credit': 0,
                        'account_id': pay.provision_id.account_id.id,
                        'move_id': move_id3,
                        'journal_id': pay.journal_id.id,
                        'period_id': pay.period_id.id,
                        'partner_id': line.employee_id.partner_id.id,
                        'date': date,
                        'company_id': pay.company_id.id
                        },context=context)
                        
                        move_line_pool.create(cr, uid, {
                        'name': 'Pago de IESS VACACIONES',
                        'debit': 0,
                        'credit': round(line.iess_vac,2),
                        'account_id': account_iess,
                        'move_id': move_id3,
                        'journal_id': pay.journal_id.id,
                        'period_id': pay.period_id.id,
                        'partner_id': line.employee_id.partner_id.id,
                        'date': date,
                        'company_id': pay.company_id.id
                        },context=context)
                        
                    rec_ids = [m.id for m in line.move_line_ids]                                                   
                    rec_ids.append(move_line)  
                    if move_line2:
                        rec_ids.append(move_line2) 
                    if move_line_iess:
                        rec_ids.append(move_line_iess)
                    move_reconcile_ids.append(rec_ids)
                    self.pool.get('hr.pay.provision.line').write(cr, uid, [line.id], {'move_line_id':move_line})
                    if line.amount_total:
                        amount+=line.amount_total
                        value = line.retention
                        hce_ids = hce_obj.search(cr, uid, [('contract_id','=',line.contract_id.id)])
                        if hce_ids:
                            for exp in hce_obj.browse(cr, uid, hce_ids):
                                htt = htt_obj.browse(cr, uid, exp.name.id)
                                if htt.code == 'RETJUD': 
                                    account_ret = htt.credit_account_id.id
                        if value > 0:    
                            move_line_pool.create(cr, uid, {
                                'name': ref or '/',
                                'debit': 0,
                                'credit': value,
                                'account_id': account_ret,
                                'move_id': move_id,
                                'journal_id': pay.journal_id.id,
                                'period_id': pay.period_id.id,
                                'partner_id': line.employee_id.partner_id.id,
                                'date':date,
                                'company_id': pay.company_id.id
                                },context=context)
                    else:                        
                        amount+=line.total_amount_provision
                else:
                    lines_ids.append(line.id)
            if amount>=0:
                move_line_pool.create(cr, uid, {
                    'name': ref or '/',
                    'debit': 0,
                    'credit': amount,
                    'account_id': acc_id,
                    'move_id': move_id,
                    'journal_id': pay.journal_id.id,
                    'period_id': pay.period_id.id,
                    'partner_id': pay.partner_id.id,
                    'date': date,
                    'company_id': pay.company_id.id
                    },context=context)
            if move_reconcile_ids:
                move_pool.post(cr, uid, [move_id], context=context)
                if move_id2:
                    move_pool.post(cr, uid, [move_id2], context=context)
                if move_id3:
                    move_pool.post(cr, uid, [move_id3], context=context)
                for rec_ids in move_reconcile_ids:
                    if len(rec_ids) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, rec_ids, context=context)
             
            self.write(cr, uid, [pay.id], {'move_id':move_id})
            line_provision_obj.unlink(cr, uid, lines_ids)
            debit_note_id = False
            if not pay.provision_id.pay_prov:
                debit_note_id = debit_note_pool.create(cr, uid, {
                                                                     'partner_id':pay.employee_id.partner_id.id,
                                                                     'beneficiary':pay.employee_id.partner_id.name,
                                                                     'account_id':account_id[0],
                                                                     'user_id':uid,
                                                                     'journal_id':pay.journal_id.id,
                                                                     'date':time.strftime('%Y-%m-%d'),
                                                                     'name': pay.reference+' - '+pay.employee_id.name,
                                                                     'reference': pay.reference+' - '+pay.employee_id.name,
                                                                     'type':'advance_supplier',
                                                                     'total_amount': line.amount_total
                                                                     
                                                                    })
                debit_note_line_pool.create(cr, uid,{
                                                                     'account_id':account_id[0],
                                                                     'name':pay.reference+' - '+pay.employee_id.name,
                                                                     'amount':line.amount_total,
                                                                     'debit_note_id':debit_note_id
                                                                     })
        return self.write(cr, uid, ids, {'state': 'close', 'debit_note_id':debit_note_id}, context=context)
    
    def pay_provision(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        value = 0.0
        lines_ids = []
        date = time.strftime('%Y-%m-%d')
        context['search_shop']=True
        move_pool = self.pool.get('account.move')
        bank_obj = self.pool.get('res.partner.bank')
        pay_pool = self.pool.get('account.payments')
        account_obj = self.pool.get('account.account')
        hce_obj = self.pool.get('hr.contract.expense')
        debit_note_pool=self.pool.get('account.debit.note')
        debit_note_line_pool=self.pool.get('account.debit.note.line')
        htt_obj = self.pool.get('hr.transaction.type')
        prov_line_obj = self.pool.get('hr.pay.provision.line')
        move_line_pool = self.pool.get('account.move.line')
        move_reconcile_ids = []
        debit_note=[]
        for pay in self.browse(cr, uid, ids, context):
            if not pay.line_ids:
                raise osv.except_osv(_('Error'), _('You can not close a Pay-Provision without lines generated'))
            move_id = None
            check_id = None
            slip_id = None
            inv_id = None
            amount=0.0
            account_id = account_obj.search(cr,uid,[('name','=','CUENTAS POR PAGAR – EMPLEADOS'),('company_id','=',pay.company_id.id)])
            for account in account_obj.browse(cr,uid,account_id):
                acc_id = account.id
            if not pay.journal_id:
                raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by pay provision'))
            name = self.pool.get('ir.sequence').next_by_id(cr, uid, pay.journal_id.sequence_id.id)
            if not pay.reference:
                ref = name
            else:
                ref = pay.reference                
#             move = {'name': name,
#                     'journal_id': pay.journal_id.id,
#                     'date': date,
#                     'ref': ref,
#                     'period_id': pay.period_id.id,
#                     'company_id': pay.company_id.id
#                     }
#             move_id = move_pool.create(cr, uid, move,context=context)
            for move_pay in pay.move_id.line_id:
                if not move_pay.reconcile_id and move_pay.account_id.id == acc_id:
                    move_reconcile_ids.append(move_pay.id)   
            for line in pay.line_ids:
                bank_id = bank_obj.search(cr, uid, [('partner_id', '=', line.employee_id.partner_id.id), ('default_bank', '=', True)])
                if not bank_id:
                    if line.employee_id:
                            debit_note_id = debit_note_pool.create(cr, uid, {
                                                                 'partner_id':line.employee_id.partner_id.id,
                                                                 'beneficiary':line.employee_id.partner_id.name,
                                                                 'account_id':account_id,
                                                                 'user_id':uid,
                                                                 'journal_id':line.journal_id.id,
                                                                 'date':time.strftime('%Y-%m-%d'),
                                                                 'name': pay.reference + line.employee_id.name1,
                                                                 'reference': pay.reference + line.employee_id.name1,
                                                                 'provision_id':pay.id,
                                                                 'type':'advance_supplier',
                                                                 'total_amount': line.amount_total
                                                                 
                                                                })
                            debit_note_line_pool.create(cr, uid,{
                                                                 'account_id':line.journal_id.default_credit_account_id.id,
                                                                 'name':pay.reference + line.employee_id.name1,
                                                                 'amount':line.amount_total,
                                                                 'debit_note_id':debit_note_id,
                                                                 })
                            debit_note.append(debit_note_id)
                else:
                    bank_id = bank_obj.search(cr, uid, [('partner_id', '=', pay.company_id.partner_id.id), ('default_bank', '=', True)])
                    if not bank_id:
                        raise osv.except_osv(_('Error'), _('Debe definir una cuenta bancaria por defecto.'))
                    account_credit = bank_obj.browse(cr, uid, bank_id[0], context).account_id.id or False
                    if not account_credit:
                        raise osv.except_osv(_('Error'), _('Debe definir una cuenta de nómina en la cuenta bancaria por defecto. '))
                    move = {'name': name,
                        'journal_id': pay.journal_id.id,
                        'date': time.strftime('%Y-%m-%d'),
                        'partner_id':pay.company.partner_id.id,
                        'ref': pay.reference + line.employee_id.name1,
                        'details':pay.reference + line.employee_id.name1,
                        'shop_id': pay.create_uid.shop_id.id,
                        'period_id': pay.period_id.id,
                        'provision_id':ids[0]
                        }
                    move_id = move_pool.create(cr, uid, move, context=context)
                    
                    move_line_pool.create(cr, uid, {
                    'name': pay.reference + line.employee_id.name1 or '/',
                    'debit': pay.total_amount,
                    'credit': 0,
                    'account_id': account_id,
                    'move_id': move_id,
                    'journal_id': pay.journal_id.id,
                    'period_id': pay.period_id.id,
                    'partner_id': pay.company_id.partner_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    }, context=context)
                move_line_pool.create(cr, uid, {
                    'name':  pay.reference + line.employee_id.name1 or '/',
                    'debit': 0,
                    'credit': pay.total_amount,
                    'account_id': account_credit,
                    'move_id': move_id,
                    'journal_id': pay.journal_id.id,
                    'period_id': pay.period_id.id,
                    'partner_id': pay.company_id.partner_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    }, context=context)
            #prov_line_obj.unlink(cr, uid, lines_ids)    
            return self.write(cr, uid, ids, {'state': 'paid'}, context=context)      
 
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        unlink_ids = []
        pay_obj = self.pool.get('hr.pay.provision')
        pay_prov_id = ids[0]
        if pay_prov_id:
            pay_id = pay_obj.search(cr,uid,[('id','=',pay_prov_id)])
        if pay_id:
            for p in pay_id:
                datas = pay_obj.browse(cr,uid,p)
                if datas.state == 'draft':
                    unlink_ids.append(datas.id)
                else:
                    raise osv.except_osv(_('Invalid action !'), _('Cannot delete payslip(s) that are close or paid state !'))
        osv.osv.unlink(self, cr, uid, ids, context=context)
        return True
        
hr_pay_provision()

class hr_provision_advance(osv.osv):
    
    _name="hr.provision.advance"
    _columns={
        "adv_provision_id": fields.many2one("hr.provision","Provision",ondelete='cascade',states={'draft':[('readonly',False)]}),
        "name":fields.char('Name', size=64, required=False,readonly=True, states={'draft':[('readonly',False)]}),        
        "ref":fields.char('Referencia', size=64, required=False,readonly=True, states={'draft':[('readonly',False)]}),
        'date_to': fields.date('Date To',readonly=False, states={'draft':[('readonly',False)]}),
        'date_from': fields.date('Date From',readonly=False),
        "period_id":fields.many2one('account.period','Period',readonly=True, states={'draft':[('readonly',False)]}),
        "company_id":fields.many2one('res.company','Company', states={'draft':[('readonly',False)]}),
        "journal_id":fields.many2one('account.journal','Journal',readonly=True, states={'draft':[('readonly',False)]}),
        "check_ids":fields.one2many('account.payments','provision_id','Checks Provision',readonly=True, states={'draft':[('readonly',False)]}),
        "state": fields.selection([('draft','Draft'),('close','Close'),('paid','Paid')],'State', readonly=True),
        "lines_ids":fields.one2many('hr.provision.advance.line','provision_advance_id','Lines', states={'draft':[('readonly',False)]}),
        'region_id':fields.many2one('res.region','Region', readonly = False, states={'draft':[('readonly',False)]}),
        'move_id':fields.many2one('account.move', 'Reference Account Move', states={'draft':[('readonly',False)]}),
        'move_id2':fields.many2one('account.move', 'Reference Account Move', states={'draft':[('readonly',False)]}),
        'partner_id':fields.many2one('res.partner', 'Partner', states={'draft':[('readonly',False)]}),
        'check_id':fields.many2one('account.payments', 'Check', readonly=True),
        'value':fields.integer('Valor'),
    }
    _defaults={
        "state": lambda *a: "draft",
        "company_id": lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        "period_id": lambda self, cr, uid, context: self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d'))])[0] or False,
        'date_to' : time.strftime('%Y-%m-%d'),
        'date_from' : time.strftime('%Y-%m-%d'),
    }
    
    _rec_name='adv_provision_id'
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not len(ids):
            return []
        for pay in self.browse(cr, uid, ids, context):
            name=""
            if pay.adv_provision_id:
                name=name+"%s"%(pay.adv_provision_id.name)
            res.append((pay.id, name))
        return res

    def onchange_date (self, cr, uid, ids, adv_provision_id=False,company_id=False,partner_id=False,region_id = False, period_id = False, journal_id =False, context=None):
        res = {}
        date_from = time.strftime('%Y-%m-%d')
        date_to = time.strftime('%Y-%m-%d')
        provision = self.pool.get('hr.provision')
        reg_obj = self.pool.get('res.region')        
        shop_obj = self.pool.get('sale.shop')
        if not company_id:
            company_id =  self.pool.get('res.users').browse(cr, uid, uid).company_id.id       
        if not (provision.browse(cr, uid, adv_provision_id)) and not (provision.search(cr, uid, [('company_id','=',company_id)])):
            raise osv.except_osv(_('Error'), _('Primero debe configurar la provisión'))    
        if not adv_provision_id or provision.browse(cr, uid, adv_provision_id).company_id.id != company_id:  
            prov = provision.search(cr, uid, [('company_id','=',company_id)])
            if not provision.search(cr, uid, [('company_id','=',company_id)]):
                raise osv.except_osv(_('Error'), _('No existe provisiones creadas para esta compañía'))   
            for pro_id in provision.browse(cr, uid, prov):
                prov_id = pro_id
                break
        else:
            prov_id = provision.browse(cr, uid, adv_provision_id)    
        if not region_id: 
            shop_id = shop_obj.search(cr, uid, [('company_id','=',company_id)])
            if not shop_id:
                raise osv.except_osv(_('Error'), _('Las tiendas de esta compañía no tienen asignada una región'))
            for shop in shop_obj.browse(cr, uid, shop_id):
                reg = shop.partner_address_id.region_id
                break
        else:
            reg =  reg_obj.browse(cr, uid,region_id)       
        if prov_id:
            if prov_id.name == 'XIV':
                if reg.name == 'SIERRA' or reg.name == 'ORIENTE':
                    date_from = prov_id.date_from_sie
                    date_to = prov_id.date_to_sie
                else:
                    date_from = prov_id.date_from_coast
                    date_to = prov_id.date_to_coast                     
            if prov_id.name == 'XIII':
                date_from = prov_id.date_from
                date_to = prov_id.date_to            
        journal_obj = self.pool.get('account.journal')
        journal_id = journal_obj.search(cr, uid, [('company_id','=',company_id)])
        for journal in journal_obj.browse(cr, uid, journal_id):
            if company_id == 1 and journal.code == 'SEMP' or company_id == 2 and journal.code == 'SEQV':
                jour_id= journal.id         
        period_obj = self.pool.get('account.period')
        period_id = period_obj.search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')),('company_id','=',company_id)])
        for period in period_obj.browse(cr, uid, period_id):
            per_id= period.id 
        comp_obj = self.pool.get('res.company')
        comp_id =  comp_obj.browse(cr, uid, company_id)
        partner = comp_id.partner_id.id
        name = _('Pago anticipado de %s') % (prov_id.name)  
        res['company_id']= company_id
        res['partner_id']= partner        
        res['date_from']= date_from
        res['date_to']= date_to
        res['period_id']= per_id 
        res['journal_id']= jour_id 
        res['region_id']= reg.id
        res['provision_id']= prov_id.id 
        res['ref']= name
        return {'value':res}
    
    def get_employee_ids(self, cr, uid, ids, context=None): 
        pays_prov = self.browse(cr,uid,ids[0])
        
        contract_object = self.pool.get('hr.contract')
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        mode_obj = self.pool.get('payment.mode')
        pay_line_pool = self.pool.get('hr.provision.advance.line')
        if not pays_prov.adv_provision_id.account_id:
            raise osv.except_osv(_("Warning !"), _("You must select account on the type of provision to pay"))
        company_id = pays_prov.company_id.id
        region= pays_prov.region_id.id
        employee_ids = emp_pool.search(cr,uid,[('company_id','=',company_id),('unemployee','=',False)])
        if employee_ids:
            for empl_id in employee_ids:
                emp = emp_pool.browse(cr, uid, empl_id, context=context)
                if emp.shop_id.partner_address_id.region_id.id == region:
                    cont_active = contract_object.search(cr,uid,[('employee_id','=',emp.id),('contract_active','=',True)])
                    if cont_active:                    
                        if not emp.partner_id:
                            raise osv.except_osv(_('Error'), _(('the employee %s does not have a partner created')% (emp.name)))
                        contract_ids = slip_pool.get_contract(cr, uid, emp, pays_prov.date_from, pays_prov.date_to, context=context)
                        mode_id = mode_obj.search(cr, uid, [('company_id','=',company_id),('cash','=',True),('discount','=',False)])
                        mode = mode_obj.browse(cr, uid, mode_id[0])
                        sql='''SELECT am.id 
                        FROM account_move_line AS am, account_account AS a
                        WHERE am.account_id = a.id AND am.partner_id = %s 
                        AND am.credit > 0 AND am.reconcile_id is Null 
                        AND a.type='other' AND am.state = 'valid' 
                        AND am.date >= %s AND am.date<= %s AND am.account_id=%s'''
                        cr.execute(sql,(emp.partner_id.id,pays_prov.date_from,pays_prov.date_to,pays_prov.adv_provision_id.account_id.id))
                        atts = cr.fetchall()
                        if atts:
                            res = {
                             'employee_id': emp.id,
                             'partner_id': emp.partner_id.id,
                             'mode_id': mode.id,
                             'contract_id':contract_ids and contract_ids[0] or False,
                             'provision_advance_id':pays_prov.id,
                             'move_line_ids':[[6, 0, [c[0] for c in atts]]]
                             }
                            pay_line_pool.create(cr, uid, res, context)
        return True     
    
    def close_pay_provision_advance(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        context['search_shop']=True
        move_pool = self.pool.get('account.move')
        account_obj = self.pool.get('account.account')
        move_line_pool = self.pool.get('account.move.line')
        context['search_shop']=True
        move_reconcile_ids = []
        for pay in self.browse(cr, uid, ids, context):
            if not pay.lines_ids:
                raise osv.except_osv(_('Error'), _('You can not close a Pay-Provision without lines generated'))
            move_id = None
            amount=0.0
            account_id = account_obj.search(cr,uid,[('name','=','CUENTAS POR PAGAR – EMPLEADOS'),('company_id','=',pay.company_id.id)])
            for account in account_obj.browse(cr,uid,account_id):
                acc_id = account.id
            if not pay.journal_id:
                raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by pay provision'))
            name = self.pool.get('ir.sequence').next_by_id(cr, uid, pay.journal_id.sequence_id.id)
            if not pay.ref:
                ref = name
            else:
                ref = pay.ref
            move = {'name': name,
                    'journal_id': pay.journal_id.id,
                    'date': pay.date_to,
                    'ref': ref,
                    'period_id': pay.period_id.id,
                    'company_id': pay.company_id.id
                    }
            move_id = move_pool.create(cr, uid, move,context=context)
            for line in pay.lines_ids:
                if line.value > line.total_amount:
                    raise osv.except_osv(_('Error'), _(('No puede anticipar más de $ %s')%(line.total_amount)))
                move_line=move_line_pool.create(cr, uid, {
                    'name': name or '/',
                    'debit': line.value,
                    'credit': 0,
                    'account_id': pay.adv_provision_id.account_id.id,
                    'move_id': move_id,
                    'journal_id': pay.journal_id.id,
                    'period_id': pay.period_id.id,
                    'partner_id': line.employee_id.partner_id.id,
                    'date': pay.date_to,
                    'company_id': pay.company_id.id
                    },context=context)
                rec_ids = [m.id for m in line.move_line_ids]
                rec_ids.append(move_line) 
                move_reconcile_ids.append(rec_ids)
                self.pool.get('hr.provision.advance.line').write(cr, uid, [line.id], {'move_line_id':move_line})
                amount+=line.value
            if amount>=0:
                move_line_pool.create(cr, uid, {
                    'name': name or '/',
                    'debit': 0,
                    'credit': amount,
                    'account_id': acc_id,
                    'move_id': move_id,
                    'journal_id': pay.journal_id.id,
                    'period_id': pay.period_id.id,
                    'partner_id': pay.partner_id.id,
                    'date': pay.date_to,
                    'company_id': pay.company_id.id
                    },context=context)
            if move_reconcile_ids:
                move_pool.post(cr, uid, [move_id], context={})
                for rec_ids in move_reconcile_ids:
                    if len(rec_ids) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, rec_ids, context=context)
                
            self.write(cr, uid, [pay.id], {'move_id':move_id})
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)    
    
    def pay_provision_advance(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        value = 0.0
        rec_ids = []
        date = time.strftime('%Y-%m-%d')
        context['search_shop']=True
        move_pool = self.pool.get('account.move')
        account_obj = self.pool.get('account.account')
        pay_pool = self.pool.get('account.payments')
        hce_obj = self.pool.get('hr.contract.expense')
        htt_obj = self.pool.get('hr.transaction.type')
        move_line_pool = self.pool.get('account.move.line')
        move_reconcile_ids = []
        for pay in self.browse(cr, uid, ids, context):
            if not pay.lines_ids:
                raise osv.except_osv(_('Error'), _('You can not close a Pay-Provision without lines generated'))
            move_id = None
            slip_id = None
            inv_id = None
            amount=0.0
            account_id = account_obj.search(cr,uid,[('name','=','CUENTAS POR PAGAR – EMPLEADOS'),('company_id','=',pay.company_id.id)])
            for account in account_obj.browse(cr,uid,account_id):
                acc_id = account.id
            if not pay.journal_id:
                raise osv.except_osv(_('Invalid action!'), _('you must defined a journal by pay provision'))
            name = self.pool.get('ir.sequence').next_by_id(cr, uid, pay.journal_id.sequence_id.id)
            if not pay.ref:
                ref = name
            else:
                ref = pay.ref                
            move = {'name': name,
                    'journal_id': pay.journal_id.id,
                    'date': date,
                    'ref': ref,
                    'period_id': pay.period_id.id,
                    'company_id': pay.company_id.id
                    }
            move_id = move_pool.create(cr, uid, move,context=context)
            for line in pay.lines_ids:
                move_line=move_line_pool.create(cr, uid, {
                        'name': ref or '/',
                        'debit': 0,
                        'credit': line.value,
                        'account_id': line.mode_id.credit_account_id.id,
                        'move_id': move_id,
                        'journal_id': pay.journal_id.id,
                        'period_id': pay.period_id.id,
                        'partner_id': line.employee_id.partner_id.id,
                        'date':date,
                        'company_id': pay.company_id.id
                        },context=context)
                move_reconcile_ids.append(move_line)
                self.pool.get('hr.provision.advance.line').write(cr, uid, [line.id], {'move_line_id2':move_line})
                amount+=line.value
                if line.mode_id.check: 
                        check_book = self.pool.get('check.receipt').search(cr, uid,[('state','=','open'),('bank','=',line.bank_account_id.bank.id)])[0]
                        cheque_id = self.pool.get('check.receipt').search(cr, uid,[('state','=','open'),('book_id','=',check_book)])[0] or False  
                        self.pool.get('check.receipt').write(cr, uid, [cheque_id],{'state':'paid'})
                        check_id = pay_pool.create_check(cr,uid, ids, line.mode_id.id, line.partner_id.name, pay.date_to, line.partner_id.id, line.amount_total, line.bank_account_id.id, line.bank_account_id.bank.id,pay.id,slip_id, inv_id, cheque_id, line.employee_id.shop_id.id)
                        self.pool.get('hr.provision.advance.line').write(cr, uid, [line.id], {'check_id':check_id})
            if amount>=0:
                move_line2=move_line_pool.create(cr, uid, {
                    'name': ref or '/',
                    'debit': amount,
                    'credit': 0,
                    'account_id': acc_id,
                    'move_id': move_id,
                    'journal_id': pay.journal_id.id,
                    'period_id': pay.period_id.id,
                    'partner_id': pay.partner_id.id,
                    'date': pay.date_to,                        
                    'company_id': pay.company_id.id
                    },context=context)
                move_reconcile_ids.append(move_line2)                
            if move_reconcile_ids:
                move_pool.post(cr, uid, [move_id], context=context)
                move_line_pool.reconcile_partial(cr, uid, move_reconcile_ids, context=context)
            
            self.write(cr, uid, [pay.id], {'move_id2':move_id})
        return self.write(cr, uid, ids, {'state': 'paid'}, context=context) 
    
   
    def draft_provision_advance_run(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        reconcile_pool = self.pool.get('account.move.reconcile')
        for pay in self.browse(cr, uid, ids, context):
            remove_reconcile = []
            for line in pay.lines_ids:
                if line.move_line_id.reconcile_id:
                    remove_reconcile += [line.move_line_id.reconcile_id.id]
                if line.move_line_id.reconcile_partial_id:
                    remove_reconcile += [line.move_line_id.reconcile_partial_id.id]
            reconcile_pool.unlink(cr, uid, remove_reconcile)
            if pay.move_id:
                move_pool.button_cancel(cr, uid, [pay.move_id.id], context={})
                move_pool.unlink(cr, uid, [pay.move_id.id], context={})
            for line in pay.lines_ids:
                if line.move_line_id2.reconcile_id:
                    remove_reconcile += [line.move_line_id2.reconcile_id.id]
                if line.move_line_id2.reconcile_partial_id:
                    remove_reconcile += [line.move_line_id2.reconcile_partial_id.id]
            reconcile_pool.unlink(cr, uid, remove_reconcile)
            if pay.move_id2:
                move_pool.button_cancel(cr, uid, [pay.move_id2.id], context={})
                move_pool.unlink(cr, uid, [pay.move_id2.id], context={})
            for chk in pay.check_ids:
                if chk.state != 'draft':
                    raise osv.except_osv(_('Error'), _('You can not change to state pay provision in draft because there is a paid check'))
                else:
                    self.pool.get('account.payments').unlink(cr, uid, [chk.id], context)
                    self.pool.get('check.receipt').write(cr, uid, [chk.cheque_id.id], {'state':'open'},context=context)
#            if pay.check_id:
#                if pay.check_id.state != 'hold':
#                    raise osv.except_osv(_('Error'), _('You can not change to state pay provision in draft because there is a paid check'))
#                else:
#                    self.pool.get('account.payments').unlink(cr, uid, [pay.check_id.id], context)
        return self.write(cr, uid, ids, {'state': 'draft', 'check':False, 'data':None, 'name':None}, context=context)
    
hr_provision_advance()


class hr_provision_advance_line(osv.osv):
    
    def _total_amount2(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0.0
        for move in line.move_line_ids:
            result[line.id]+= move.amount_to_pay
        return result
    
    _name= "hr.provision.advance.line"
    _columns={
        "provision_advance_id": fields.many2one("hr.provision.advance","Provision",ondelete='cascade'),        
        'employee_id':fields.many2one('hr.employee', 'Employee'),
        'contract_id':fields.many2one('hr.contract','Contract'),
        "move_line_ids":fields.one2many('account.move.line','provision_advance_line_id','Move Line',),
        'move_line_id':fields.many2one('account.move.line', 'Move Line', required=False, readonly=True),
        'move_line_id2':fields.many2one('account.move.line', 'Move Line', required=False, readonly=True),
        "total_amount": fields.function(_total_amount2, method=True,type="float", string='Valor Máximo de Anticipo', store=True,),
        'value':fields.float('Valor'),
        'mode_id':fields.many2one('payment.mode', 'Mode', readonly=False, required = True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=False, ), 
        'bank_account_id':fields.many2one('res.partner.bank', 'Bank Account', readonly=False, ),
        'check_id':fields.many2one('account.payments', 'Check', readonly=True),      
              }
    
    def bank_account_change2(self, cr, uid, ids, mode_id = False,employee_id=False, context = None):
        res = {}
        line = self.browse(cr,uid,ids[0])
        acc_bank_obj = self.pool.get('res.partner.bank')
        mode_obj = self.pool.get('payment.mode')
        empl_obj = self.pool.get('hr.employee')
        comp_obj = self.pool.get('res.company')
        if mode_id:
            mode= mode_obj.browse(cr, uid, mode_id)
            if mode.required_bank == True :
                empl = empl_obj.browse(cr, uid, employee_id, context)
                partner_id = empl.partner_id.id
                acc_bank_id = acc_bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
                if not acc_bank_id and mode.check == True:
                    company_id = line.pay_provision_id.company_id.id
                    comp = comp_obj.browse(cr, uid, company_id, context)                
                    partner_id = comp.partner_id.id
                    acc_bank_id = acc_bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
                if not acc_bank_id and mode.check == False:            
                    raise osv.except_osv(_('Error'), _('Debe configurar un N° d cuenta para el empleado'))
                if acc_bank_id:
                    for acc_bank in acc_bank_obj.browse(cr, uid,acc_bank_id):
                            acc = acc_bank.id
                            break 
                res['bank_account_id'] = acc        
            else:
                if mode.check == True : 
                    company_id = line.pay_provision_id.company_id.id
                    comp = comp_obj.browse(cr, uid, company_id, context)                
                    partner_id = comp.partner_id.id
                    acc_bank_id = acc_bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
                    for acc_bank in acc_bank_obj.browse(cr, uid,acc_bank_id):
                            acc = acc_bank.id
                            break            
                    res['bank_account_id'] = acc                                         
        return {'value':res}

hr_provision_advance_line()

class hr_pay_provision_line(osv.osv):
    
    def _total_provision(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0.0
            for move in line.move_line_ids:
                if move.amount_to_pay >0:
                    result[line.id]+= move.amount_to_pay
                else:
                    result[line.id]+= move.credit 
        return result
    
    def _wk_days(self, cr, uid, ids, name, args, context):
        result = {}
        days = 0
        c = 0
        date = time.strftime('%Y-%m-%d')
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0
            date_from = line.pay_provision_id.date_from
            date_to = line.pay_provision_id.date_to
            date_init = line.contract_id.date_start
            if date_init < date_from:
                days = 360
            else:
                date_to = datetime.strptime(date_to[0:10],"%Y-%m-%d")
                date_init = datetime.strptime(date_init[0:10],"%Y-%m-%d")
                for month in range(date_init.month, 12):
                    if month == 1 or month ==2  or month == 3 or month == 5 or month == 7 or month == 8 or month == 10 or month == 12:   
                        c = c + 1
                    else:  
                        c += 0
                if c > 0:
                    c -= 1
                days = ((date_to - date_init ).days) - c 
            result[line.id]+= days     
        return result
    
    def _wk_years(self, cr, uid, ids, field_names, arg, context=None):
        return self.pool.get('hr.pay.provision.line')._amount_total(cr, uid, ids, field_names, arg, context)

        
    def _total_advance(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0.0
            for move in line.move_line_ids:
                result[line.id]+= move.debit
        return result
    
    def _amount_total(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        value = 0.00
        total = 0.00
        amount = 0.00
        provision = 0.00
        days = 0.00
        expense = self.pool.get('hr.contract.expense')
        htt_obj = self.pool.get('hr.transaction.type')
        date = time.strftime('%Y-%m-%d')
        for line in self.browse(cr, uid, ids, context=context):
            date = time.strftime('%Y-%m-%d')
            date_init = line.contract_id.date_start
            if date_init < date:
                date = datetime.strptime(date[0:10],"%Y-%m-%d")
                date_init = datetime.strptime(date_init[0:10],"%Y-%m-%d")
                year = date.year - date_init.year
                if year >= 20:
                    days = 15
                elif year > 5:
                    days = year - 5                    
            ##VALORES
            for move in line.move_line_ids:
                if move.amount_to_pay >0:
                    amount += (move.amount_to_pay - move.debit)
                    provision += move.amount_to_pay
                else:
                    amount += (move.credit - move.debit)
                    provision += move.credit
            exp_id =  expense.search(cr,uid,[('contract_id','=',line.contract_id.id)])
            if exp_id:
                for exp in expense.browse(cr, uid, exp_id):
                    htt = htt_obj.browse(cr, uid, exp.name.id)
                    if htt.code == 'RETJUD':
                        value += exp.amount
            total = amount - value  
            total2 = provision / 15 * days   
            iess = ((provision + total2)*9.45)/100
            if not line.pay_provision_id.provision_id.pay_prov:    
                res[line.id]['wk_years'] = days
                res[line.id]['value_year'] = total2
                res[line.id]['total_amount_provision'] = amount + total2 - iess
                res[line.id]['iess_vac'] = iess
                res[line.id]['amount_total'] = total + total2 - iess                
            else: 
                res[line.id]['wk_years'] = 0.00
                res[line.id]['value_year'] = 0.00
                res[line.id]['amount_total'] = total
                res[line.id]['total_amount_provision'] = amount
                res[line.id]['iess_vac'] = 0.00   
        return res
    
    def _retention(self, cr, uid, ids, name, args, context):
        result = {}
        expense = self.pool.get('hr.contract.expense')
        htt_obj = self.pool.get('hr.transaction.type')
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0.0
            exp_id =  expense.search(cr,uid,[('contract_id','=',line.contract_id.id)])
            if exp_id:
                for exp in expense.browse(cr, uid, exp_id):
                    htt = htt_obj.browse(cr, uid, exp.name.id)
                    if htt.code == 'RETJUD':   
                        result[line.id] = exp.amount
        return result
      
    _name="hr.pay.provision.line"
    _columns={
        "pay_provision_id": fields.many2one("hr.pay.provision","Provision",ondelete='cascade'),
        "employee_id":fields.many2one('hr.employee','Employee'),
        "contract_id":fields.many2one('hr.contract','Contract'),
        'type':fields.selection([
            ('P','Direct Payment'),
            ('A','Bank Statement'),
            ('RP','Direct Payment Retention'),
            ('RA','Bank Statement Retention'),
            ],'Type Payment', select=True, ),
        "move_line_ids":fields.one2many('account.move.line','pay_provision_line_id','Move Line',),
        'move_line_id':fields.many2one('account.move.line', 'Move Line', required=False, readonly=True),
        'move_line_id2':fields.many2one('account.move.line', 'Move Line', required=False, readonly=True),
        "total_provision": fields.function(_total_provision, method=True,type="float", string='Amount Provision', store=True,),
        "amount_total": fields.function(_wk_years, string='Receiving Total', multi='hr_provision_line_amount', store=True),
        "total_amount_provision": fields.function(_wk_years, string='Total de Provisión', multi='hr_provision_line_amount', store=True),
        "retention": fields.function(_retention, method=True,type="float", string='(-)Valor Retención', store=True,),
        "advance": fields.function(_total_advance, method=True,type="float", string='(-)Valor Anticipo', store=True,),
        'mode_id':fields.many2one('payment.mode', 'Mode', readonly=False, required = True),
        'check_id':fields.many2one('account.payments', 'Check', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=False, ), 
        'bank_account_id':fields.many2one('res.partner.bank', 'Bank Account', readonly=False, ),
        "wk_days": fields.function(_wk_days, method=True,type="integer", string='Días de trabajo', store=True,),
        "wk_years": fields.function(_wk_years, string='Días Adicionales', multi='hr_provision_line_amount', store=True),   
        'value_year': fields.function(_wk_years, string='(+)Valor días', multi='hr_provision_line_amount', store=True),
        'iess_vac': fields.function(_wk_years, string='(-)9.45% IESS', multi='hr_provision_line_amount', store=True),
        'pay_aprove': fields.boolean('Pago Aprobado', readonly = False), 
    }
    
    def bank_account_change(self, cr, uid, ids, mode_id = False,employee_id=False,context = None):
        res = {}
        if not ids:
            return res
        line = self.browse(cr,uid,ids[0])
        acc_bank_obj = self.pool.get('res.partner.bank')
        mode_obj = self.pool.get('payment.mode')
        empl_obj = self.pool.get('hr.employee')
        comp_obj = self.pool.get('res.company')
        if mode_id:
            mode= mode_obj.browse(cr, uid, mode_id)
            if mode.required_bank == True :
                empl = empl_obj.browse(cr, uid, employee_id, context)
                partner_id = empl.partner_id.id
                acc_bank_id = acc_bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
                if not acc_bank_id and mode.check == True:
                    company_id = line.pay_provision_id.company_id.id
                    comp = comp_obj.browse(cr, uid, company_id, context)                
                    partner_id = comp.partner_id.id
                    acc_bank_id = acc_bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
                if not acc_bank_id and mode.check == False:            
                    raise osv.except_osv(_('Error'), _('Debe configurar un N° d cuenta para el empleado'))
                if acc_bank_id:
                    for acc_bank in acc_bank_obj.browse(cr, uid,acc_bank_id):
                            acc = acc_bank.id
                            break 
                res['bank_account_id'] = acc        
            else:
                if mode.check == True : 
                    company_id = line.pay_provision_id.company_id.id
                    comp = comp_obj.browse(cr, uid, company_id, context)                
                    partner_id = comp.partner_id.id
                    acc_bank_id = acc_bank_obj.search(cr,uid,[('partner_id','=',partner_id)])
                    for acc_bank in acc_bank_obj.browse(cr, uid,acc_bank_id):
                            acc = acc_bank.id
                            break            
                    res['bank_account_id'] = acc                                 
        if (mode.cash == True or mode.check== True):
            if line.retention == 0:
                type = 'P'
            else :
                type = 'RP'       
        else:
            if line.retention == 0:
                type = 'A'
            else:
                type ='RA'     
        res['type'] = type        
        return {'value':res}
    


hr_pay_provision_line()



class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _columns = {
        'pay_provision_line_id':fields.many2one('hr.pay.provision.line', 'Provision Line', required=False),
        'provision_advance_line_id':fields.many2one('hr.provision.advance.line', 'Provision Advance Line', required=False),
    }
account_move_line()

class account_move(osv.osv):
    _inherit = 'account.move'
    _columns = {
                'provision_id':fields.many2one('hr.pay.provision', 'Provision', required=False) 
                    }     
account_move()

class account_debit_note(osv.osv):
    _inherit = 'account.debit.note'
    _columns = {
                'comments':fields.char('Reference', size=256),
                'provision_id':fields.many2one('hr.pay.provision', 'Provision', required=False) 
                    } 
    def create_move(self, cr, uid, note, name, ref, context=None):
        res = super(account_debit_note, self).create_move(cr, uid, note, name, ref, context=context)
        if note.provision_id:
            self.pool.get('account.move').write(cr, uid, [res], {'provision_id': note.provision_id.id or False})
        return res
account_debit_note()