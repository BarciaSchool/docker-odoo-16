import netsvc
from procurement.procurement import procurement_order

def action_cancel(self, cr, uid, ids, context={}):
    """ Cancels procurement and writes move state to Assigned.
    @return: True
    """
    todo = []
    todo2 = []
    move_obj = self.pool.get('stock.move')
    for proc in self.browse(cr, uid, ids):
        if proc.close_move and proc.move_id:
            if proc.move_id.state not in ('done', 'cancel'):
                todo2.append(proc.move_id.id)
        else:
            if proc.move_id and proc.move_id.state == 'waiting':
                todo.append(proc.move_id.id)
    if len(todo2):
        move_obj.action_cancel(cr, uid, todo2)
    if len(todo):
        move_obj.write(cr, uid, todo, {'state': 'assigned'})
    self.write(cr, uid, ids, {'state': 'cancel'})
    wf_service = netsvc.LocalService("workflow")
    for id in ids:
        wf_service.trg_trigger(uid, 'procurement.order', id, cr)
    return True

procurement_order.action_cancel = action_cancel