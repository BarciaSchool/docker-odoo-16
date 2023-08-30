# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from osv import fields, osv
from tools.translate import _

class validate_account_move(osv.osv_memory):
    _inherit = "validate.account.move"

    _columns = {
        'company_id': fields.many2one('res.company', 'Compañía', required=True),
    }

    def validate_move(self, cr, uid, ids, context=None):
        obj_move = self.pool.get('account.move')
        obj_move_line = self.pool.get('account.move.line')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        move_review = []
        lines_review = []
        ids_move = obj_move.search(cr, uid, [('state','=','draft'),('journal_id','=',data.journal_id.id),('period_id','=',data.period_id.id)], order='id')
        contador = 0.00
        if not ids_move:
            raise osv.except_osv(_('Warning'), _('Specified Journal does not have any account move entries in draft state for this period'))
        for ids_m in ids_move:
            datas ={}
            contador += 1
            debit = 0
            credit = 0
            move_id = obj_move.browse(cr,uid,ids_m)
            if move_id.state == 'draft':
                iva_account = False
                if move_id.line_id:
                    for lines in move_id.line_id: 
                        if lines.account_id.id == 544:
                            lines_review = lines.id
                            lines_value = lines.debit + lines.credit
                        elif lines.account_id.id == 310:
                            iva_account = True
                        elif lines.account_id.id == 110:
                            iva_account  = True                            
                        debit += lines.debit
                        credit += lines.credit
                if not round(debit,2) == round(credit,2) and move_id.state == 'draft':
                    if lines_review and move_id.state=='draft' and iva_account:
                        move_review.append(move_id.id)
                        new_value = debit - credit - lines_value
                        cr.execute("""update account_move_line set write_date=now(), credit = 0.00, debit=0.00 where id =%s""",(lines_review,))
#                        obj_move_line.write(cr,uid,[lines_review],{'debit':0.00,'credit':0.00})
                        if new_value > 0 and new_value < 0.02:
                            n_debit = 0.00
                            n_credit = abs(new_value)
                        else:
                            n_debit = abs(new_value)
                            n_credit = 0.00
                        obj_move_line.write(cr,uid,[lines_review],{'debit':n_debit,'credit':n_credit})
                    else:
                        if iva_account:
                            last_line = obj_move_line.search(cr,uid,[('move_id','=',move_id.id)]) 
                            if last_line:
                                id_update = last_line[-1]
                                if id_update:
                                    if debit > credit:
                                        value_update = obj_move_line.browse(cr,uid,id_update).credit + (debit - credit)                                  
                                        cr.execute("""update account_move_line set write_date=now(), credit = %s, debit=%s where id =%s""",(value_update,0,id_update))
                                    else:
                                        value_update = obj_move_line.browse(cr,uid,id_update).credit - (credit - debit)
                                        cr.execute("""update account_move_line set write_date=now(), credit = %s, debit=%s where id =%s""",(value_update,0,id_update))
                        else:
                            if debit > credit and not iva_account:
                                amount1 = 0.00
                                amount2 = abs(debit-credit)
                                name = '601 - 12% IVA'
                                account_id = 310
                                reference = move_id.line_id[0].invoice.number or False
                            elif debit < credit and not iva_account:
                                amount1 = abs(debit-credit)
                                amount2 = 0.00
                                name = 'IVA PAGADO'
                                account_id = 110
                                reference = move_id.line_id[0].invoice.number or False
                                
                            datas = {
                                    'journal_id':move_id.journal_id.id, 
                                    'name':name, 
                                    'reference':reference, 
                                    'partner_id': move_id.partner_id.id, 
                                    'period_id':move_id.period_id.id, 
                                    'company_id':move_id.company_id.id, 
                                    'account_id':account_id, 
                                    'debit': amount1,
                                    'credit': amount2, 
                                    'date':move_id.date,
                                    'move_id': move_id.id,
                                    'analytic_account_id':move_id.line_id[0].analytic_account_id.id, 
                                    'currency_id':move_id.line_id[0].currency_id.id, 
                                    'amount_currency': amount1+amount2
                                    }
                            if datas:
                                obj_move_line.create(cr,uid,datas)
            cr.execute("""select sum(debit)-sum(credit) from account_move_line where move_id = %s""",(ids_m,))
            dato = cr.fetchone()
            if dato:
                try:
                    if round(dato[0],2)==0 and move_id.state == 'draft':
                        obj_move.post(cr, uid, [move_id.id], context=context)
                        cr.commit()
                except:
                    continue
        return {'type': 'ir.actions.act_window_close'}

validate_account_move()