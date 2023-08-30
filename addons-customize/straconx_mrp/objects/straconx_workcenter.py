# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP es una marca registrada de OpenERP S.A.
#
#    OpenERP Addon - Módulo que amplia funcionalidades de OpenERP©
#    Copyright (C) 2010 - present STRACONX S.A. (<http://openerp.straconx.com>).
#
#    Este software es propiedad de STRACONX S.A. y su uso se encuentra restringido. 
#    Su uso fuera de un contrato de soporte de STRACONX es prohibido.
#    Para mayores detalle revisar el archivo LICENCIA.TXT contenido en el directorio
#    de este módulo.
# 
##############################################################################

from datetime import datetime
from osv import osv, fields
import decimal_precision as dp
from tools import float_compare
from tools.translate import _
import netsvc
import time
import tools
from operator import attrgetter


class mrp_workcenter(osv.osv):
    _inherit = 'mrp.workcenter'
    
    def cost_mrp_cycle(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cost_hour = 0.00
        capacity_per_cycle = 0.00
        costs_cycle = 0.00
        for production in self.browse(cr, uid, ids, context=context):
            if production.member_ids:
                for hr_employee in production.member_ids:
                    cost_hour += hr_employee.salary_hour
                    capacity_per_cycle += 1
                    costs_cycle += production.time_cycle*hr_employee.salary_hour 
        
        res[production.id]={'capacity_per_cycle':capacity_per_cycle,
                            'costs_hour':cost_hour,
                            'costs_cycle': costs_cycle
                            }        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        time_cycle = vals.get('time_cycle','00:00')
        if time_cycle <= 0.00:
            raise osv.except_osv(_('Error!'), _(('Necesita definir las horas del ciclo del trabajo!')))
        return super(mrp_workcenter, self).write(cr, uid, ids, vals, context)
        
    
    _columns = {
        'member_ids':fields.many2many('hr.employee', 'hr_workcenter_rel', 'workcenter_id', 'employee_id', 'Team Members'),
        'capacity_per_cycle': fields.function(cost_mrp_cycle, string='Capacidad por Ciclo', method=True,type="float", multi="Cycle"),
        'costs_hour': fields.function(cost_mrp_cycle, string='Costo por Hora', method=True,type="float", multi="Cycle"),
        'costs_cycle': fields.function(cost_mrp_cycle, string='Costo por Ciclo', method=True,type="float", multi="Cycle"),        
    }

    _defaults = {
        'time_cycle': 8.00,
        'resource_type': 'user'                                    
                }
    
    
mrp_workcenter()


class mrp_production_workcenter_line(osv.osv):
    _inherit = 'mrp.production.workcenter.line'

    def cost_mrp_hour(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        required_hour = 0.00
        for production in self.browse(cr, uid, ids, context=context):
            if production.workcenter_id.capacity_per_cycle:
                required_hour = production.workcenter_id.time_cycle * production.cycle
                res[production.id]= required_hour        
        return res

    _columns = {
        'hour': fields.function(cost_mrp_hour, string='Horas requeridas', method=True, type="float"),        
    }
    
mrp_production_workcenter_line()


class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    def salary_hour(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for employee in self.browse(cr, uid, ids, context=context):
            res[employee.id]={'salary':0.00,
                              'salary_hour':0.00}
            contract_active = self.pool.get('hr.contract').search(cr, uid, [('employee_id','=',employee.id),('contract_active','=',True)], limit=1)
            if contract_active:
                contract= self.pool.get('hr.contract').browse(cr, uid, contract_active[0], context)
                salary=contract.wage
                salary_hour=salary/240
                res[employee.id]={'salary':salary,
                                  'salary_hour':salary_hour}
        return res

    _columns = {
        'salary': fields.function(salary_hour, string='Salario', method=True,type="float", multi="Sum"), 
        'salary_hour': fields.function(salary_hour, string='Costo Hora / Colaborador', method=True,type="float", multi="Sum"),
        }
    
    _defaults = {
        'salary': 0.00,          
        'salary_hour': 0.00,                             
                }    
hr_employee()

