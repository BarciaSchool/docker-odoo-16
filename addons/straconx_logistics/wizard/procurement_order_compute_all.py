from osv import osv
import threading
import pooler

class procurement_order_compute_all(osv.osv_memory):
    _inherit='procurement.order.compute.all'
    
    def create_procurement(self, cr, uid, ids,procurement_object,automatic,context=None):
        new_cr = pooler.get_db(cr.dbname).cursor()
        make_commit=procurement_object.create_internal_procurement(new_cr, uid,automatic,context=None)
        try:
            if(make_commit):
                new_cr.commit()
            else:
                new_cr.rollback()
        except:
            pass
        finally:
            try:
                new_cr.close()
            except Exception:
                pass
        return {}
    
    def procure_stock(self, cr, uid, ids, context=None):
        automatic=False
        for browse_procurement in self.browse(cr, uid, ids, context):
            automatic=browse_procurement.automatic
        procurement_object=self.pool.get("procurement.order")         
        threaded_calculation = threading.Thread(target=self.create_procurement, args=(cr, uid, ids,procurement_object,automatic,context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
    
procurement_order_compute_all()