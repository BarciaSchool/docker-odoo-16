from osv import osv,fields
from tools.translate import _
import netsvc
from datetime import datetime

class create_ubication(osv.osv_memory):
    _name="create.ubication"
    _inherit = "res.config.installer"
    _columns={
              'company_id': fields.many2one('res.company', 'Company', required=True),
              }
    
    def execute(self, cr, uid, ids, context=None):
        if(context is None):
            context={}
        ubicat = self.pool.get('ubication').search(cr,uid,[])
        for u in ubicat:
            ubication = self.pool.get('ubication').browse(cr,uid,u)
            cr.execute("SELECT product_id FROM product_ubication WHERE ubication_id = %s and product_id is not null",(u,))
            product_ids= [r[0] for r in cr.fetchall()]
            sql="""INSERT INTO product_ubication 
                   (ubication_id,location_ubication_id,shop_ubication_id,qty,product_id,categ_id)
                   SELECT %s, %s, %s, 0, pp.id, pt.categ_id FROM product_product pp, product_template pt WHERE pp.product_tmpl_id = pt.id"""
            if product_ids:
                if len(product_ids) > 1:
                    sql += """ AND pp.id not in """+ str(tuple(product_ids))
                else:
                    sql += """ AND pp.id != """+ str(product_ids[0])
            cr.execute(sql,(u,ubication.location_id.id,ubication.location_id.location_id and ubication.location_id.location_id.id))
create_ubication()