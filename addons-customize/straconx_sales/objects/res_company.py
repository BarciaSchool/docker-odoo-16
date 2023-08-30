from openerp.osv import osv,fields
from openerp.tools.translate import _

class res_company(osv.osv):
    _inherit="res.company"
    _columns={
              "authorize_sales_order":fields.boolean("Requires a supervisor",help="Authorize sale by supervisor."),
              "number_days_validate":fields.integer("Number days to Validate",help="Days are needed to expire the sales order."),
              }
    
    _defaults={
               "authorize_sales_order":True,
               "number_days_validate":5,
               }
    
    def onchange_number_days_validate(self,cr,uid,ids,number_days_validate,context=None):
        if(number_days_validate):
            if(number_days_validate<0):
                return {"value":{"number_days_validate":number_days_validate*-1},"warning":{"title":_("Validation Error!"),"message":_("Number of days can not be negative.")}}
        return {}
        
res_company()