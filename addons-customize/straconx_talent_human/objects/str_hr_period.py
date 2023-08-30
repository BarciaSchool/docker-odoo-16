# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2011-2012 STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
#
#    This program is private software.
#
##############################################################################
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import netsvc
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _

    
class hr_period_payment(osv.osv):
    _name = 'hr.period'
    _columns = {
                'name':fields.char('Name',size=256, required=True),
                'type': fields.selection([
                        ('ordinary', 'Ordinary'),
                        ('extra', 'Extraordinary')
                    ], 'Type', select=True, readonly=True, states={'draft': [('readonly', False)]}, required=True),
                'date_start': fields.date('Date From', readonly=True, states={'draft': [('readonly', False)]}, required=True),
                'date_stop': fields.date('Date To', readonly=True, states={'draft': [('readonly', False)]}, required=True),
                'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'draft': [('readonly', False)]}, select=True),
                'company_id': fields.related('fiscalyear_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
                'state': fields.selection([
                        ('draft', 'Open'),
                        ('verify', 'Waiting'),
                        ('done', 'Closed'),
                        ('cancel', 'Cancel'),
                    ], 'State', select=True, readonly=True),   
                'payment':fields.boolean('pagos', required=False) 
    }
                 
    _defaults = {
        'state': 'draft',
    }
    _order = "date_start"
     
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    ]
 
    def _check_duration(self,cr,uid,ids,context=None):
        obj_period = self.browse(cr, uid, ids[0], context=context)
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True
  
#     def _check_year_limit(self,cr,uid,ids,context=None):
#         for obj_period in self.browse(cr, uid, ids, context=context):
#               
#             if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
#                obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
#                obj_period.fiscalyear_id.date_start > obj_period.date_start or \
#                obj_period.fiscalyear_id.date_start > obj_period.date_stop:
#                 return False
#   
#             pids = self.search(cr, uid, [('date_stop','>=',obj_period.date_start),('date_start','<=',obj_period.date_stop),('id','<>',obj_period.id)])
#             for period in self.browse(cr, uid, pids):
#                 if period.fiscalyear_id.company_id.id==obj_period.fiscalyear_id.company_id.id:
#                     return False
#         return True
  
    _constraints = [
        (_check_duration, 'Error ! The duration of the Period(s) is/are invalid. ', ['date_stop']),
#        (_check_year_limit, 'Invalid period ! Some periods overlap or the date period is not in the scope of the fiscal year. ', ['date_stop'])
    ]
        
    def next(self, cr, uid, period, step, context=None):
        ids = self.search(cr, uid, [('date_start','>',period.date_start)])
        if len(ids)>=step:
            return ids[step-1]
        return False
 
    def find(self, cr, uid, dt=None, context=None):
        if context is None: context = {}
        if not dt:
            dt = fields.date.context_today(self,cr,uid,context=context)
#CHECKME: shouldn't we check the state of the period?
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            args.append(('company_id', '=', context['company_id']))
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            args.append(('company_id', '=', company_id))
        result = []
        if context.get('account_period_prefer_normal'):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(cr, uid, args , context=context)
        if not result:
            result = self.search(cr, uid, args, context=context)
        if not result:
            raise osv.except_osv(_('Error !'), _('No period defined for this date: %s !\nPlease create one.')%dt)
        return result
 
    def action_draft(self, cr, uid, ids, *args):
        mode = 'draft'
        for period in self.browse(cr, uid, ids):
            if period.fiscalyear_id.state == 'done':
                raise osv.except_osv(_('Warning !'), _('You can not re-open a period which belongs to closed fiscal year'))
        cr.execute('update account_journal_period set state=%s where period_id in %s', (mode, tuple(ids),))
        cr.execute('update account_period set state=%s where id in %s', (mode, tuple(ids),))
        return True
 
#     def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
#         if args is None:
#             args = []
#         if context is None:
#             context = {}
#         ids = []
#         if name:
#             ids = self.search(cr, user, [('code','ilike',name)]+ args, limit=limit)
#         if not ids:
#             ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit)
#         return self.name_get(cr, user, ids, context=context)
 
    def build_ctx_periods(self, cr, uid, period_from_id, period_to_id):
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.browse(cr, uid, period_from_id)
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.browse(cr, uid, period_to_id)
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise osv.except_osv(_('Error'), _('You should have chosen periods that belongs to the same company'))
        if period_date_start > period_date_stop:
            raise osv.except_osv(_('Error'), _('Start period should be smaller then End period'))
        #for period from = january, we want to exclude the opening period (but it has same date_from, so we have to check if period_from is special or not to include that clause or not in the search).
        return self.search(cr, uid, [('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('company_id', '=', company1_id)])
 
hr_period_payment()

class account_fiscalyear(osv.osv):
    _inherit = "account.fiscalyear"
    _columns = {
        'hr_period_ids': fields.one2many('hr.period', 'fiscalyear_id', 'Periods'),
        #TODO: Hacer que el campo extra se encuentre invisible cuando se generan líneas y lo contrario cuando estas se borren.
        'extra': fields.boolean('Special Payments', help="Check this field if you company have extraordinary payments"),        
        }
        
    def hr_create_period2(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('hr.period')
        for fy in self.browse(cr, uid, ids, context=context):
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            year = ds.strftime('%Y-%m-%d')[0:4]
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                m = ds.strftime('%Y-%m-%d')[5:7]
                if m=='01':
                    month = "Enero"
                elif m=='02':
                    month = "Febrero"
                elif m=='03':
                    month = "Marzo"
                elif m=='04':
                    month = "Abril"
                elif m=='05':
                    month = "Mayo"
                elif m=='06':
                    month = "Junio"
                elif m=='07':
                    month = "Julio"
                elif m=='08':
                    month = "Agosto"
                elif m=='09':
                    month = "Septiembre"
                elif m=='10':
                    month = "Octubre"
                elif m=='11':
                    month = "Noviembre"
                elif m=='12':
                    month = "Diciembre"
                else:
                    raise osv.except_osv(_('Error!'),_("Incorrect month!"))
                
                last_day = ds + relativedelta(day=31) 
                day=ds.strftime('%Y-%m-%d')[8:10] 
                if day=='01':                                            
                    period_obj.create(cr, uid, {
                        'name': 'Primera Quincena de '+ month+'-'+year,
                        'date_start': ds.strftime('%Y-%m-01'),
                        'date_stop': ds.strftime('%Y-%m-15'),
                        'fiscalyear_id': fy.id,
                        'type':'ordinary',
                        'state':'draft',
                        'payment': True
                    })
                    de = ds + relativedelta(day=16)
                    ds = de                                         
                else:
                    period_obj.create(cr, uid, {
                        'name': 'Segunda Quincena de '+ month+'-'+year,
                        'date_start': ds.strftime('%Y-%m-16'),
                        'date_stop': last_day,
                        'fiscalyear_id': fy.id,
                        'type':'ordinary',
                        'state':'draft',
                        'payment': False
                    })
                    if fy.extra==True:
                        period_obj.create(cr, uid, {
                            'name': 'Ajuste Nómina de '+ month+'-'+year,
                            'date_start': last_day,
                            'date_stop': last_day,
                            'fiscalyear_id': fy.id,
                            'type':'extra',
                            'state':'draft'
                        })                    
                    de = last_day + relativedelta(days=1)
                    ds = de 
                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')
        return True

    def hr_create_period(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('hr.period')
        for fy in self.browse(cr, uid, ids, context=context):
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            year = ds.strftime('%Y-%m-%d')[0:4]
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                m = ds.strftime('%Y-%m-%d')[5:7]
                if m=='01':
                    month = "Enero"
                elif m=='02':
                    month = "Febrero"
                elif m=='03':
                    month = "Marzo"
                elif m=='04':
                    month = "Abril"
                elif m=='05':
                    month = "Mayo"
                elif m=='06':
                    month = "Junio"
                elif m=='07':
                    month = "Julio"
                elif m=='08':
                    month = "Agosto"
                elif m=='09':
                    month = "Septiembre"
                elif m=='10':
                    month = "Octubre"
                elif m=='11':
                    month = "Noviembre"
                elif m=='12':
                    month = "Diciembre"
                else:
                    raise osv.except_osv(_('Error!'),_("Incorrect month!"))
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')

                period_obj.create(cr, uid, {
                    'name': 'Nómina de '+ month+'-'+year,
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                    'type':'ordinary',
                    'state':'draft',
                    'payment':False
                })

                if fy.extra==True:
                    period_obj.create(cr, uid, {
                        'name': 'Ajuste Nómina de '+ month+'-'+year,
                        'date_start': de.strftime('%Y-%m-%d'),
                        'date_stop': de.strftime('%Y-%m-%d'),
                        'fiscalyear_id': fy.id,
                        'type':'extra',
                        'state':'draft',
                        'payment':False
                    })                                    
                ds = ds + relativedelta(months=interval)
        return True
account_fiscalyear()