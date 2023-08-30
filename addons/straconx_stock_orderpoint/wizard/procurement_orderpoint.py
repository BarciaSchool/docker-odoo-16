# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A (Lajonner Crespín Moran) 
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
from osv import osv, fields
import threading
import pooler
from tools.translate import _
import traceback

class procurement_orderpoint(osv.osv_memory):
    
    _name = 'procurement.orderpoint'
    _columns = {
              "automatic":fields.boolean("Automatic", help="if true approves generated purchase order"),
              "company_id":fields.many2one("res.company", "Company", required="True")
              }

    def create_procurement(self, cr, uid, ids, company_id, origin_sale_shop_ids, automatic, context=None):
        name=cr.dbname
        new_con = pooler.get_db(name)
        new_cr = new_con.cursor()
        make_commit = self.pool.get("stock.warehouse.orderpoint").create_internal_procurement(new_cr, uid, company_id, origin_sale_shop_ids, automatic, context=None)
        try:
            try:     
                if(make_commit):
                    osv._logger.info("%s wizard supplies finalized ok",name)
                    new_cr.commit()
                else:
                    osv._logger.warning("%s wizard supplies failed",name)                
                    new_cr.rollback()
            except:
                pass
            finally:
                new_cr.close()
        except:
            osv._logger.error("%s error executing automated wizard supplies",name)
            osv._logger.error("%s %s",name,traceback.format_exc())
            raise
        return {}
    
    def procure_stock(self, cr, uid, ids, context=None):
        automatic = False
        company_id = False
        for browse_procurement in self.browse(cr, uid, ids, context):
            automatic = browse_procurement.automatic
            company_id = browse_procurement.company_id.id
        origin_sale_shop_ids = self.pool.get("sale.shop").search(cr, uid, [('company_id', '=', company_id), ('central_warehouse', '=', True)])##tienda que es bodega central
        if(not origin_sale_shop_ids):##no hay 1 bodega central
            raise osv.except_osv(_('Validation Error!'), _("There is no central warehouse."))
        if(not self.pool.get("salesman.salesman").search(cr, uid, [('is_buyer', '=', True), ('user_id', '=', uid)])):##debe ser un comprador
            raise osv.except_osv(_('Validation Error!'), _("The user should be a buyer."))
        threaded_calculation = threading.Thread(target=self.create_procurement, args=(cr, uid, ids, company_id, origin_sale_shop_ids, automatic, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
    
procurement_orderpoint()
