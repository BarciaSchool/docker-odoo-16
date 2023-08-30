# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2010-present STRACONX S.A (<http://openerp.straconx.com>). All Rights Reserved       
#
#    This program is private software.
#
##############################################################################

from osv import osv, fields
from tools.translate import _
import psycopg2
import time
import decimal_precision as dp

class migration_database(osv.osv):
    _name = "migration.database"
                
    _columns = {
        'name': fields.char('Database', size=60, required=True),
        'user': fields.char('User', size=20, required=True),
        'password': fields.char('Password', size=15,required=True),
        'host':fields.char('host', size=60,required=True),
        'port':fields.char('port', size=10,required=True),
    }
    
migration_database()
    
class migration(osv.osv):
    _name = "migration.products"
    _rec_name = 'date_process'

    def _get_database(self, cr, uid, ids, context=None):
        name = cr.dbname
#        cr.execute("""TRUNCATE migration_database""")
        cr.execute("select datname from pg_database where datdba in (select usesysid from pg_user where usename<>'postgres') and datname <> '%s'"%(name,))
        bases = cr.fetchall()
        if bases:
            for b in bases:                
                cr.execute("""select name from migration_database where name = '%s'"""%b)
                confirm = cr.fetchall()
                if not confirm:                    
                    cr.execute("""insert into migration_database (name) values ('%s')"""%b)
        cr.commit()
        cr.execute("select id from migration_database")
        base_first = cr.fetchall()
        if base_first:
            base_first = base_first[0] 
        return base_first

    _columns = {
        'company_id': fields.many2one('res.company','Company', required=True,readonly=True),
        'product_ids': fields.many2many('product.product', 'migration_product_wizard_rel', 'wizard_id', 'product_id', 'Products',required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'base_dest': fields.many2one('migration.database','Database',required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'date_proccess': fields.datetime('Process Date', readonly=True, states={'draft':[('readonly',False)]}, select=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('done','Done'),
            ],'State', select=True, readonly=True,),     
                }
    
    _defaults = {
        'base_dest': _get_database,
        'state': 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'migration.products', context=c),
        'user_id': lambda s, cr, u, c: u,
        'date_proccess':lambda *a:time.strftime('%Y-%m-%d %H:%M:%S') 
    }

    def start_migrate(self, cr, uid, ids, context=None):
        pool = cr.dbname
        db = self.browse(cr,uid,ids[0])
        database = db.base_dest.name
        if not database:
            raise osv.except_osv('Error!', _("Please, select a database."))
        user = db.base_dest.user
        password = db.base_dest.password
        host=db.base_dest.host
        port=db.base_dest.port        
        try:
            source_or= psycopg2.connect(database=pool, user=user, password=password, host='localhost', port=port, options='-c statement_timeout=15s')
            conection = psycopg2.connect(database=database, user=user, password=password, host=host, port=port, options='-c statement_timeout=15s')
            create_date = time.strftime('%Y-%m-%d %H:%M:%S')
            if conection:
                if db.product_ids:
                    for product in db.product_ids:
                        source = source_or.cursor()
                        conect = conection.cursor()
                        conect.execute("""select id from product_product where id=%s"""%(product.id,)) 
                        test = conect.fetchall()
                        if not test:
                            source.execute("""select id, supply_method,standard_price,mes_type,uom_id,uom_po_id,type,procure_method,cost_method,name,categ_id,sale_ok,description,purchase_ok from product_template where id = %s"""%(product.product_tmpl_id.id,))
                            prt = source.fetchall()
                            for pt in prt:
                                prt = self.pool.get('product.template').browse(cr,uid,pt[0])
                                categ_id = prt.categ_id.id
                                if categ_id:
                                    conect.execute("""select id from product_category where id = %s"""%(categ_id,))
                                    ct = conect.fetchall()
                                    if ct:
                                        categ_id = categ_id
                                    else:
                                        categ_id = self.pool.get('product.category').browse(cr,uid,categ_id)
                                        conect.execute("""INSERT INTO product_category(id,create_date, parent_left, parent_right, name, sequence, parent_id, type, is_comercial, permit_refund)VALUES(%s,'%s',%s,%s,'%s',%s,%s,'%s',%s,%s)"""%(categ_id.id, create_date, categ_id.parent_left, categ_id.parent_right, categ_id.name,categ_id.sequence,(categ_id.parent_id or "Null"),categ_id.type,categ_id.is_comercial,categ_id.permit_refund))
                                        categ_id = categ_id.id
                                conect.execute("""INSERT INTO PRODUCT_TEMPLATE(id,create_date, supply_method,standard_price,mes_type,uom_id,uom_po_id,type,procure_method,cost_method,name,categ_id,sale_ok,description,purchase_ok,list_price,uos_id,uos_coeff)values(%s,'%s','%s',%s,'%s',%s,%s,'%s','%s','%s','%s',%s,%s,'%s',%s,%s,%s,%s)"""%(prt.id,create_date,prt.supply_method,prt.standard_price,prt.mes_type,prt.uom_id.id,prt.uom_po_id.id,prt.type,prt.procure_method,prt.cost_method,prt.name,prt.categ_id.id,prt.sale_ok,prt.description,prt.purchase_ok,prt.list_price,prt.uos_id.id or prt.uom_id.id ,prt.uos_coeff))                        
                            source.execute("""SELECT id from product_product where id = %s"""%(product.id))
                            prd = source.fetchall()
                            for p in prd:
                                prod = self.pool.get('product.product').browse(cr,uid,p[0])
                                clasification_cat = prod.clasification_cat.id
                                if clasification_cat:
                                    conect.execute("""select id from product_clasification where id = %s"""%(clasification_cat,))
                                    clas =conect.fetchall()
                                    if clas:
                                        clasification_cat = clasification_cat
                                    else:
                                        clasification_cat = self.pool.get('product.clasification').browse(cr,uid,clasification_cat)
                                        conect.execute("""INSERT INTO product_clasification(id, create_date, parent_id, code, name, seq_1, seq_2, sequence_structure, padding_sufix,padding_prefix)values(%s,'%s',%s,'%s','%s',%s,%s,'%s','%s','%s')"""%(clasification_cat.id, create_date, (clasification_cat.parent_id.id or "Null"), (clasification_cat.code or "Null"), clasification_cat.name, clasification_cat.seq_1, clasification_cat.seq_2, clasification_cat.sequence_structure, clasification_cat.padding_sufix,clasification_cat.padding_prefix))
                                        clasification_cat = clasification_cat.id                                        
                                conect.execute("""INSERT INTO PRODUCT_PRODUCT(id,create_date,name_template,packing_p,ean13,product_tmpl_id,valuation,default_code,active,clasification_cat)values(%s,'%s','%s',%s,%s,%s,'%s','%s',%s,%s)"""%(prod.id,create_date,prod.name_template,prod.packing_p,(prod.ean13 or "NUll"),prod.product_tmpl_id.id,prod.valuation,prod.default_code,prod.active,prod.clasification_cat.id))
                                conect.execute("""update product_template set standard_price=%s where id=%s"""%(prod.p_net,prod.product_tmpl_id.id))
                                conect.execute("""select tax_id from product_taxes_rel where prod_id = %s"""%(prod.id,))
                                tax_sale = conect.fetchall()
                                if not tax_sale:
                                    source.execute("""select tax_id from product_taxes_rel where prod_id = %s"""%(prod.product_tmpl_id.id,))
                                    taxes = source.fetchall()
                                    for t in taxes:
                                        conect.execute("""insert into product_taxes_rel (prod_id, tax_id) values (%s,%s)"""%(prod.product_tmpl_id.id,t[0]))
                                conect.execute("""select tax_id from product_supplier_taxes_rel where prod_id =  %s"""%(prod.product_tmpl_id.id,))
                                tax_purc = conect.fetchall()
                                if not tax_purc:
                                    source.execute("""select tax_id from product_supplier_taxes_rel where prod_id = %s"""%(prod.product_tmpl_id.id,))
                                    taxes = source.fetchall()
                                    for t in taxes:
                                        tax_purchase = """insert into product_supplier_taxes_rel (prod_id, tax_id) values (%s,%s)"""%(prod.product_tmpl_id.id,t[0])
                                        conect.execute(tax_purchase)
                                conect.execute("""SELECT product_id FROM product_images where product_id = %s"""%(prod.id))                                
                                images = conect.fetchall()
                                if not images:
                                    source.execute("""SELECT id FROM product_images where product_id = %s"""%(prod.id))
                                    images_link = source.fetchall()
                                    images_pool = self.pool.get('product.images')
                                    for i in images_link:                        
                                        images = images_pool.browse(cr,uid,i[0])
                                        if images.file_db_store:                                            
                                            picture = psycopg2.Binary(images.file_db_store)
                                        else:
                                            picture = "Null"                
                                        conect.execute("""INSERT INTO PRODUCT_IMAGES(id, file_db_store,name, url, extention, comments, link, product_id, main) VALUES(%s,%s,'%s','%s','%s','%s',%s,%s,%s )"""%(images.id, picture,images.name, images.url, images.extention, images.comments, images.link, images.product_id.id, images.main))                                     
                    conection.commit()
                    self.write(cr,uid,ids,{'state':'done'})
                    return True                            
        except psycopg2.Error, e:
            raise osv.except_osv('Error!', _("Could not establish the connection : %s" %e))
        
migration()
