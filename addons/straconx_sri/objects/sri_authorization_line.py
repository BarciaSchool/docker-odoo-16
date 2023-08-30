# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-present STRACONX S.A 
#    (<http://openerp.straconx.com>). All Rights Reserved     
##############################################################################

from osv import fields,osv
from tools.translate import _

def _get_name(self, cr, uid, context={}):
    cr.execute("""select code, name from account_journal_type where sri_type_control in ('company','company_partner')""")
    return cr.fetchall()

class sri_authorization_line(osv.osv):
    
    def _verify_state(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.authorization_id.auto_printer:
                res[line.id] = (not line.expired)
            else:
                if line.name == 'withhold':
                    if line.counter < line.range:
                        res[line.id]=True
                    else:
                        res[line.id]=False
                else:
                    if line.counter < line.range:
                        res[line.id]=True
                    else:
                        res[line.id]=False
        return res
    
    def _get_range(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, args):
            result[line.id] = line.ending_number - line.starting_number
        return result
    
    def _check_sequences(self,cr,uid,ids):
        for line in self.browse(cr, uid, ids):
            if (line['ending_number'] < 0 or line['starting_number'] < 0):
                return False
            elif (line['ending_number'] - line['starting_number']) < 0:
                return False
            else:
                return True
            
    def _generate_document(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context):
            res[line.id]=False
            if line.counter >0:
                res[line.id]=True
        return res
            
    _name='sri.authorization.line'
    _columns = {
            'authorization_id':fields.many2one('sri.authorization', 'Authorization', required=True, ondelete="cascade"),
            'name':fields.selection(_get_name, 'Name', size=37, required=True),
            'pre_printer':fields.boolean('Pre printer', required=False),
            'auto_printer':fields.boolean('auto_printer', required=False),
            'generate_document': fields.function(_generate_document, method=True, type='boolean', string='Generate Document',),
            'expired':fields.boolean('Expired?'),
            'shop_id':fields.many2one('sale.shop', 'Shop', required=True),
            'printer_id':fields.many2one('printer.point', 'Printer Point', required=True),
            'prefix_shop': fields.related('shop_id', 'number_sri', string='Prefix Shop', type='char', size=3, readonly=True),
            'prefix_point': fields.related('printer_id', 'number_sri', string='Prefix Printer', type='char', size=3, readonly=True),
            'starting_number': fields.integer('Start'),
            'ending_number': fields.integer('End'),
            'counter': fields.integer('counter'),
            'number_next': fields.integer('number next'),
            'range': fields.function(_get_range, method=True, type='integer',string='range', 
                                     store={'sri.authorization.line': (lambda self, cr, uid, ids, c={}: ids, ['starting_number','ending_number'], 6)}),
            'state': fields.function(_verify_state, method=True, type='boolean', string='Active',
                                         store={'sri.authorization.line': (lambda self, cr, uid, ids, c={}: ids, ['counter','expired'], 8)}),
            'type_printer':fields.selection([('auto','auto-printer'),('pre','pre-printer'),('manual','manual'),('electronic','Electrónico')],'Type Printer', select=True,
                                help="defines how it will generate documents"),                
            'active': fields.boolean('active')
    }
    
    _defaults = {
        'counter': lambda *a: 0,
        'expired': lambda *a: False,
        'type_printer': 'pre',
        'active': True        
    }
    
    _constraints = [(_check_sequences,'La secuencia final debe ser mayo que la secuencia inicial de esta autorización',['ending_number','starting_number']),]
    
    _sql_constraints = [('line_name_uniq','unique(name,shop_id,printer_id,authorization_id)', 'Ya existe un documento con este mismo número en la tienda y el punto de emisión seleccionado, por favor revisar'),
                        ]
        
    def onchange_auto_printer(self, cr, uid, ids, shop=None,auto_printer=False, context={}):
        res={}
        if auto_printer:
            res['type_printer']='auto'
        return {'value':res}
        
    def on_change_shop(self, cr, uid, ids, shop=None,company=False, context={}):
        res={}
        if shop:
            res['printer_id']=None
        return {'value':res}
    
    def on_change_name(self, cr, uid, ids, name, shop=None, printer=None, automatic=False, company=False, context=None):
        result = {}
        if context is None:
            context={}
        if not (shop and printer and name):
            return result
        primera=0
        ultima=0
        range_default=99
        if automatic:
            auth_ant = self.search(cr, uid, [('name','=', name ),('state','=',False),('printer_id','=',printer),('shop_id','=',shop),('authorization_id.auto_printer','=',True)])
            if auth_ant:
                primera=self.browse(cr, uid, auth_ant[-1], context).ending_number + 1
            else:
                primera=1
            result['starting_number'] = primera
            result['ending_number'] = primera
        else:
            result['expired']=False
            auth_ant = self.search(cr, uid, [('name','=', name ),('printer_id','=',printer),('shop_id','=',shop),('authorization_id.auto_printer','!=',True)],order='starting_number')
            if not auth_ant:
                primera=1
            else:
                primera=self.browse(cr, uid, auth_ant[-1], context).ending_number + 1
            ultima=primera + range_default
            result['ending_number'] = ultima
        result['starting_number'] = primera
        return {'value':result}
        
    def onchange_number(self, cr, uid, ids, first_secuence, automatic, context=None):
        result = {}
        if automatic:
            result['ending_number'] = first_secuence
        value = {'value':result}
        return value
    
    def create(self, cr, uid, values,context=None):
        values['number_next'] = values['starting_number']
        authorization=self.pool.get('sri.authorization').browse(cr, uid, values['authorization_id'], context)
        line_act_ids = self.search(cr, uid, [('name','=',values['name']),('printer_id','=',values['printer_id']),('shop_id','=',values['shop_id']),('authorization_id','!=',values['authorization_id']),('state','=',True),('authorization_id.company_id','=',authorization.company_id.id)])
        for line in self.browse(cr, uid, line_act_ids , context=context):
#             if not authorization.auto_printer:
#                 raise osv.except_osv('Error!', _('You have activated automatic authorization in the company by this printer point and shop'))
            self.write(cr, uid, [line.id,], {'counter':line.range + 1}, context)
        return super(sri_authorization_line, self).create(cr, uid, values, context)
    
    def write(self, cr, uid, ids, values, context=None):
            if values.get('starting_number',False) and not values.get('counter',0)>0:
                values['number_next'] = values['starting_number']
            return super(sri_authorization_line, self).write(cr, uid, ids, values, context)
    
    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        for line in self.browse(cr, uid, ids, context):
            if line.counter > 0:
                raise osv.except_osv(_('Invalid action!'), _('You can delete authorization that have already generated documents'))
            unlink_ids.append(line.id)
        else:
            self.write(cr,uid,ids,{'active':False})
        return True           
#        return super(sri_authorization_line, self).unlink(cr, uid, unlink_ids, context)
    
    #metodos para el control de seccuencias y rangos de la autorizacion, teniendo en cuenta que formamos nuestras propias secuencias.
    
    def add_sequence(self,cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [line.id], {'number_next':line.number_next+1}, context )
        return True
    
    def rest_sequence(self,cr, uid, ids, context=None):
        number_next = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.number_next >=line.starting_number:
                if (line.number_next - 1)>0:
                    number_next = line.number_next
                elif (line.number_next - 1)<=0:
                    number_next = line.starting_number
                else:
                    number_next = 1
            if number_next:
                self.write(cr, uid, [line.id], {'number_next':number_next}, context )
        return True
    
    def add_document(self,cr, uid, line_ids, context=None):
        """ Add sequence of line by authorization"""
        for line in self.browse(cr, uid, line_ids, context=context):
            if line.authorization_id.auto_printer or line.type_printer=='auto':
                self.write(cr, uid, [line.id], {'ending_number': line.number_next}, context=context )
            self.write(cr, uid, [line.id], {'counter': line.counter+1,'number_next':line.number_next+1}, context=context)
        return True
            
    def rest_document(self,cr, uid, line_ids, context=None):
        """ Rest sequence of line by authorization"""
        for line in self.browse(cr, uid, line_ids, context=context):
            if line.authorization_id.auto_printer:
                if (line.number_next)>=0:
                    number_next = line.number_next
                    counter = line.number_next
                    range = line.number_next
                else:
                    number_next = 1 
                    counter = 1
                    range = 1
                self.write(cr, uid, [line.id], {'ending_number': number_next, 'counter':counter, 'range': range}, context=context )
            else:
                if (line.number_next -1 )>=0:
                    number_next = line.number_next 
                if line.counter - 1 >0:
                    counter = line.counter
                else:
                    counter = 1
                self.write(cr, uid, [line.id], {'number_next': number_next, 'counter':counter}, context=context )
#             self.write(cr, uid, [line.id], {'counter': counter}, context=context)
        return True
sri_authorization_line()