# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2012-2013 STRACONX S.A.
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
from os.path import join
from osv import fields,osv
from xlwt import easyxf
from xlrd import open_workbook
from xlutils.copy import copy
from xlutils.styles import Styles
from osv import fields,osv,orm
from tools.translate import _
import time
from datetime import date
import base64
import httplib
import mimetypes
import urllib
import os,base64,urllib
from cStringIO import StringIO
#import requests
from xml.etree.ElementTree import Element, SubElement, tostring

black_list=[332,427]

list_tags_nationals=[302,303,304,307,308,309,310,312,319,320,322,323,325,327,328,332,340,341,342,343,344]

list_tags_internationals=[401,403,405,421,427]

class form_103(osv.osv_memory):
    periodo_list=[]
    
    def indent(self,elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def _get_period(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id)])
        return period_ids and period_ids[0] or None
    
    def _get_fiscalyear(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fiscalyear_ids = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d')), ('company_id', '=', user.company_id.id),('state', '=', 'draft')])
        return fiscalyear_ids and fiscalyear_ids[0] or None
    
    _name='form.103'
    
    _columns={
              'name':fields.char('name', size=20, readonly=True),
              'company_id':fields.many2one('res.company', 'Company', required=True),
              'fiscalyear_id':fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
              'period_id':fields.many2one('account.period', 'Period', required=True, domain="[('fiscalyear_id', '=', fiscalyear_id)]"),
              'legal_representative_id':fields.many2one('res.partner', 'Legal Representative (198)', required=True),
              'counter_id':fields.many2one('res.partner', 'Counter (199)', required=True),
              'currency_id':fields.many2one('res.currency', 'Currency', required=True),
              'cod_form':fields.char('Form code', size=64, required=False),
              #fields for forms replacement
              'replacement':fields.boolean('replacement', required=False),
              'pre_payment': fields.float('Pre Payment (890)', digits=(16, 2)),
              'pre_interest': fields.float('Pre Interest (897)', digits=(16, 2)),
              'pre_tax': fields.float('Pre Tax (898)', digits=(16, 2)),
              'pre_fine': fields.float('Pre Fine (899)', digits=(16, 2)),
              'interest': fields.float('interest (903)', digits=(16, 2)),
              'tax': fields.float('tax (904)', digits=(16, 2)),
              'cod_form_replace':fields.char('Form code Replacement (104)', size=64, required=False),
              'data':fields.binary('File', readonly=True),
              'state':fields.selection([
                    ('choose','Choose'),
                    ('get','Get'),
                ],'state', required=True, readonly=True),
              
              }
    
    _defaults = {
                 'state': lambda *a: 'choose',
                 'replacement': False,
                 "period_id": _get_period,
                 "fiscalyear_id": _get_fiscalyear,
                 'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'form.103', context=c),
                 }
    
    def onchange_company(self, cr, uid, ids, company_id, context={}):
        res={}
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id)
            res['currency_id']=company.currency_id.id or None
            res['legal_representative_id']=company.legal_representative_id.id or None
            res['counter_id']=company.counter_id.id or None
        return {'value':res}
    
    def agree_subelement_xml(self, root, tag, values={}):
        elements=values.keys()
        elements.sort()
        for k in elements:
            SubElement(root,tag, {'numero':str(k)}).text=values[k]
        return True
    
    def search_taxes(self, cr, uid, form, tax_description):
        try:
            cr.execute("""SELECT  int4(t.description), sum(wl.tax_base), sum(wl.retained_value)
                            FROM account_withhold_line wl, account_withhold w, account_tax t 
                            WHERE wl.withhold_id = w.id AND wl.tax_id = t.id AND 
                            w.state = 'approved' AND w.transaction_type = 'purchase' AND
                            w.period_id = %s AND t.description = %s
                            GROUP BY t.description""", (form.period_id.id, str(tax_description)))
            return cr.fetchall()
        except Exception, e:
            raise orm.except_orm(_('Unknown Error'), str(e))
            
    
    def generate_xml(self, cr, uid, ids, context=None):
        formulario = ''
        for form in self.browse(cr, uid, ids, context=context):
            periodo= form.period_id.name
            self.periodo_list= periodo.split('/')
            formulario = Element("formulario",{'version': '0.2'})
            cabecera = SubElement(formulario,"cabecera")
            SubElement(cabecera,"codigo_version_formulario").text=form.cod_form
            SubElement(cabecera,"ruc").text=form.company_id.partner_id.vat[2:]
            SubElement(cabecera,"codigo_moneda").text=form.currency_id.name == 'USD' and '1' or ''
            detalle = SubElement(formulario,"detalle")
            dict_information={31:'0',
                              101:self.periodo_list[0],
                              102:self.periodo_list[1],
                              104:form.cod_form_replace or ' ',
                              198:form.legal_representative_id.vat and form.legal_representative_id.vat[2:] or '',
                              199:form.counter_id.vat and form.counter_id.vat[2:] or '',
                              201:form.company_id.partner_id.vat[2:] or '',
                              202:"<![CDATA["+form.company_id.name+"]]>",
                              }
            self.agree_subelement_xml(detalle, "campo", dict_information)
            dict_tax={}
            dict_tax_calculate={}
            sum_base=0.00
            sum_tax=0.00
            sum_base_inter=0.00
            sum_tax_inter=0.00
            #CALCULO DE LOS IMPUESTOS DE RETENCIONES NACIONALES
            for tag in list_tags_nationals:
                res=self.search_taxes(cr, uid, form, tag)
                for r in res:
                    sum_base+=r[1]
                    dict_tax.update({r[0]:str(r[1])})
                    if tag not in black_list:
                        dict_tax_calculate.update({tag+50:str(r[2])})
                        sum_tax+=r[2]
                    continue
                dict_tax.update({tag:'0.00'})
                if tag not in black_list:
                    dict_tax_calculate.update({tag+50:'0.00'})
            dict_tax.update({349:str(sum_base)})
            dict_tax_calculate.update({399:str(sum_tax)})
            self.agree_subelement_xml(detalle, "campo", dict_tax)
            self.agree_subelement_xml(detalle, "campo", dict_tax_calculate)
            
            #CALCULO DE LOS IMPUESTOS DE RETENCIONES INTERNACIONALES
            dict_tax.clear()
            dict_tax_calculate.clear()
            for tag in list_tags_internationals:
                res=self.search_taxes(cr, uid, form, tag)
                for r in res:
                    sum_base_inter+=r[1]
                    dict_tax.update({r[0]:str(r[1])})
                    if tag not in black_list:
                        dict_tax_calculate.update({tag+50:str(r[2])})
                        sum_tax_inter+=r[2]
                    continue
                dict_tax.update({tag:'0.00'})
                if tag not in black_list:
                    dict_tax_calculate.update({tag+50:'0.00'})
            dict_tax.update({429:str(sum_base_inter)})
            dict_tax_calculate.update({498:str(sum_tax_inter)})
            self.agree_subelement_xml(detalle, "campo", dict_tax)
            self.agree_subelement_xml(detalle, "campo", dict_tax_calculate)
            
            dict_information.clear()
            dict_information={499:str(sum_tax+sum_tax_inter),
                              880:'0.00',
                              890:str(form.pre_payment) or '0.00',
                              897:str(form.pre_interest) or '0.00',
                              898:str(form.pre_tax) or '0.00',
                              899:str(form.pre_fine) or '0.00',
                              903:str(form.interest) or '0.00',
                              904:str(form.tax) or '0.00',
                              }
            total=sum_tax+sum_tax_inter-form.pre_tax
            dict_information.update({902:str(total) or '0.00',
                                     999:str(total+form.interest+form.tax) or '0.00',
                                     907:'0.00',
                                     908:'',
                                     910:'',
                                     912:'',
                                     909:'0.00',
                                     911:'0.00',
                                     913:'0.00',
                                     915:'0.00',
                                     })
            self.agree_subelement_xml(detalle, "campo", dict_information)
            self.indent(formulario)
        return tostring(formulario,encoding="UTF-8")
    
    def act_export(self, cr, uid, ids, context={}):
        formulario = self.generate_xml(cr,uid,ids)
        date_new=date(int(self.periodo_list[1]),int(self.periodo_list[0]),15)
        name = "103ORI_"+date_new.strftime('%B')[0:3].upper()+self.periodo_list[1]+".xml"
        out=base64.encodestring(formulario)
        return self.write(cr, uid, ids, {'data':out, 'name':name, 'state': 'get'}, context=context)
    
    def _getOutCell(self, outSheet, colIndex, rowIndex):
        row = outSheet._Worksheet__rows.get(rowIndex)
        if not row: return None
    
        cell = row._Row__cells.get(colIndex)
        return cell
    
#     def get_document_file(self,url):
#         if not os.path.isfile(url):
#             return False
#         file=False        
#         (filename, header) = urllib.urlretrieve(url)        
#         with open(filename, 'r') as f:
#             file = base64.b64encode(f.read())
#         return file
    
    def crear_formulario (self, cr, uid, ids, context={}):  
        res = {}
        i = 14
        s1 = 0.0
        sr1 = 0.0
        s2 = 0.0
        sr2 = 0.0
        range_list=range(14,85)
        #response = httplib.HTTPResponse(mimetype="application/vnd.ms-excel") 
        #response['Content-Disposition'] = 'attachment; filename=Formulario_103_2.xls' 
        excel = open_workbook('/opt/openerp/server/openerp/addons/straconx_anexos/wizard/Formulario_103.xls', formatting_info=True)
        sh = excel.sheet_by_index(0)
        wb = copy(excel)
        ws = wb.get_sheet(0) 
        
        period_id = self.browse(cr, uid, ids)[0].period_id.id
        year = self.browse(cr, uid, ids)[0].fiscalyear_id.name
        name_company = self.browse(cr, uid, ids)[0].company_id.name
        ruc_company = self.browse(cr, uid, ids)[0].company_id.vat
        r_legal = self.browse(cr, uid, ids)[0].legal_representative_id.name
        r_legal_vat = self.browse(cr, uid, ids)[0].legal_representative_id.vat
        counter = self.browse(cr, uid, ids)[0].counter_id.name
        counter_vat = self.browse(cr, uid, ids)[0].counter_id.vat
        
        for x in range(0,4):
            previousCell = self._getOutCell(ws,(18+x), 4)
            ws.write(4,(18+x), year[x])
            if previousCell:
                newCell = self._getOutCell(ws,(18+x), 4)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
        c=1            
        for x in range (2,15):
            previousCell = self._getOutCell(ws,c, 9)
            ws.write(9, c, ruc_company[x])
            if previousCell:
                newCell = self._getOutCell(ws,c, 9)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
            c+=1
            
        previousCell = self._getOutCell(ws,14, 9)    
        ws.write(9, 14, name_company)
        if previousCell:
            newCell = self._getOutCell(ws,14, 9)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx
                    
        sql_select = """SELECT atx.description, ai.period_id, sum(aw.tax_base) as base, sum(aw.retained_value) as ret 
                        FROM account_invoice ai 
                        JOIN account_withhold_line aw on aw.invoice_id = ai.id  
                        JOIN account_tax atx on atx.id = aw.tax_id 
                        WHERE ai.period_id=%s and aw.state = 'approved'
                        GROUP BY atx.description,ai.period_id"""                
        cr.execute(sql_select,(period_id,))
        
        for t in cr.dictfetchall():    
            for j in range_list:
                codigo = sh.cell_value(rowx=j, colx=21)  
                cod = int (t['description'])         
                if cod == codigo: 
                    previousCell = self._getOutCell(ws, 23, j)
                    ws.write(j,23, t['base'])
                    if previousCell:
                        newCell = self._getOutCell(ws, 23, j)
                        if newCell:
                            newCell.xf_idx = previousCell.xf_idx
                    if j < 52:
                        s1 += t['base']
                        sr1 += t['ret']
                    else:                        
                        s2 += t['base']
                        sr2 += t['ret']
                    if j != 35 and j != 36:
                        previousCell = self._getOutCell(ws, 30, j)
                        ws.write(j,30, t['ret'])
                        if previousCell:
                            newCell = self._getOutCell(ws, 30, j)
                            if newCell:
                                newCell.xf_idx = previousCell.xf_idx
        if s1 > 0:
            previousCell = self._getOutCell(ws, 23, 51)
            ws.write(51,23, s1)
            if previousCell:
                newCell = self._getOutCell(ws, 23, 51)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
            previousCell = self._getOutCell(ws, 30, 51)
            ws.write(51,30, sr1)
            if previousCell:
                newCell = self._getOutCell(ws, 30, 51)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
        if s2 >0:
            previousCell = self._getOutCell(ws, 23, 85)
            ws.write(85,23, s2)
            if previousCell:
                newCell = self._getOutCell(ws, 23, 85)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
            previousCell = self._getOutCell(ws, 30, 85)
            ws.write(85,30, sr2)
            if previousCell:
                newCell = self._getOutCell(ws, 30, 85)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
                    
        previousCell = self._getOutCell(ws, 30, 87)            
        ws.write(87,30, (sr2+sr1))
        if previousCell:
            newCell = self._getOutCell(ws, 30, 87)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx
#Representante Legal                
        c=7            
        for x in range (2,12):
            previousCell = self._getOutCell(ws,c, 111)
            ws.write(111, c, r_legal_vat[x])
            if previousCell:
                newCell = self._getOutCell(ws,c, 111)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
            c+=1        
                
        previousCell = self._getOutCell(ws,2, 110)    
        ws.write(110, 2, r_legal)
        if previousCell:
            newCell = self._getOutCell(ws,2, 110)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx      
                
#Contador
        c=22            
        for x in range (2,15):
            previousCell = self._getOutCell(ws,c, 111)
            ws.write(111, c, counter_vat[x])
            if previousCell:
                newCell = self._getOutCell(ws,c, 111)
                if newCell:
                    newCell.xf_idx = previousCell.xf_idx
            c+=1        
                
        previousCell = self._getOutCell(ws,22, 110)    
        ws.write(110, 22, counter)
        if previousCell:
            newCell = self._getOutCell(ws,22, 110)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx   
                
        wb.save('/opt/openerp/server/openerp/addons/straconx_anexos/wizard/Formulario_103_2.xls')
#         files_path = 'file:/opt/openerp/server/openerp/addons/straconx_anexos/wizard'
#         name = 'Formulario_103_2'
#         ext = '.xls'
#         url = files_path+'/'+name+ext
#          fl=self.get_document_file(url)
#         local_filename = url.split('/')[-1]
#         r = requests.get(url, stream=True)
#         with open(local_filename, 'wb') as f:
#             for chunk in r.iter_content(chunk_size=1024): 
#                 if chunk:
#                     f.write(chunk)
#                     f.flush()
        return True
    
form_103()