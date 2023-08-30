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
from osv import fields, osv
from tools.translate import _
import time

class stock_picking(osv.osv):
    
    def _verify_authorization(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        b=True
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.international:
                for move in picking.move_lines:
                    if not move.authorized:
                        b=False
            res[picking.id]=b
        return res
    
    _inherit = 'stock.picking'
    _columns = {
        'trade_id': fields.many2one('purchase.trade', 'Purchase Trade',
            ondelete='set null', select=True),
        'international':fields.boolean('International', required=False),
        'authorized':fields.boolean('Autorizado', required=False),        
#        'authorized': fields.function(_verify_authorization, method=True, type='boolean', string='Authorized'),
    }
    _defaults = {
        'trade_id': False,
        'international': False,
        'authorized': True,
    }
    
    def action_process(self, cr, uid, ids, context=None):
        result = {}
        warning = {}
        differences = 0.00
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.move_lines and picking.international and picking.type == 'in':
                for line in picking.move_lines: 
                    if not line.flag:
                        differences += line.qty_receive  - line.product_qty
            if differences <>0:
                cr.execute("""update stock_picking set write_date = now(), authorized=False where id =%s """,(ids[0],))
                cr.commit()
                picking.refresh()
                raise osv.except_osv(_('Error!'), _('You need authorization to process because the quantities received are different than expected'))
            else:
                return super(stock_picking, self).action_process(cr, uid, ids, context)
    
    def action_drafted(self, cr, uid, ids, context=None):
        debit_note_pool=self.pool.get('account.debit.note')
        debit_list = []
        debit_moves = []
        for pick in self.browse(cr, uid, ids, context=context):
            for move in pick.move_lines:
                if move.debit_note_id:
                    if move.debit_note_id.state !='draft':
                        if not move.debit_note_id.payment_ids or move.debit_note_id.residual <>0:
                            debit_moves.append(move.debit_note_id.id)
                        else:
                            debit_list.append(move.debit_note_id.number)                        
                    else:
                        debit_moves.append(move.debit_note_id.id)                                                
            if debit_list: 
                raise osv.except_osv(_('Invalid action!'), _('Existen la(s) siguiente(s) Nota(s) de Débito(s) PAGADAS %s en la presente importación y no puede ser cambiada a borrador')%(tuple(debit_list),))
            if debit_moves:
                debit_note_pool.action_cancel_draft(cr, uid,debit_moves, context)
                debit_note_pool.cancel_debit_note(cr, uid,debit_moves, context)
        return super(stock_picking, self).action_drafted(cr, uid, ids, context)
    
    def validate_authorized(self, cr, uid, ids, context=None):
        debit_note_pool=self.pool.get('account.debit.note')
        debit_note_line_pool=self.pool.get('account.debit.note.line')
        for picking in self.browse(cr, uid, ids, context=context):
            debit_note=[]
            todo=[]
            if picking.move_lines:
                for move in picking.move_lines:
                    todo.append(move.id)
                    if move.qty_receive<0:
                        raise osv.except_osv(_('¡Acción Inválida!'), _('No puede recibir cantidades negativas'))
                    if move.qty_receive < move.product_qty:
                        if not move.invoice_line_id:
                            continue
                        journal_ids=self.pool.get('account.journal').search(cr, uid, [('type','=','debit_note')])
                        if not journal_ids:
                            raise osv.except_osv(_("Error"),_("You must create a Debit Note Journal"))
                        debit_note_id = debit_note_pool.create(cr, uid, {
                                                             'partner_id':move.invoice_line_id.invoice_id.partner_id.id,
                                                             'account_id':move.invoice_line_id.account_id.id,
                                                             'user_id':uid,
                                                             'journal_id':journal_ids[0],
                                                             'date':time.strftime('%Y-%m-%d'),
                                                             'name': 'Nota de Débito por Producto Faltante '+move.product_id.name,
                                                             'reference': move.picking_id.name,
                                                             'type':'debit_supplier'
                                                            })
                        debit_note_line_pool.create(cr, 1,{
                                                             'account_id':move.invoice_line_id.invoice_id.account_id.id,
                                                             'name':str(move.product_qty-move.qty_receive) + str(move.product_uom.name) +' del '+move.product_id.default_code+'-'+move.product_id.name,
                                                             'amount':(move.product_qty-move.qty_receive)*move.invoice_line_id.price_unit,
                                                             'debit_note_id':debit_note_id,
                                                             })
                        debit_note.append(debit_note_id)
                        self.pool.get('stock.move').write(cr, uid, [move.id], {'product_qty':move.qty_receive,'debit_note_id':debit_note_id})
                if debit_note:
                    debit_note_pool.button_dummy(cr, uid,debit_note,context)
                    debit_note_pool.confirm_debit_note(cr, uid,debit_note,context)
                if todo:
                    self.pool.get('stock.move').write(cr, uid, todo, {'flag':True,'authorized':True})
            self.write(cr, uid, ids, {'authorized':True})    
        return True
    
stock_picking()