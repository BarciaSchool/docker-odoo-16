# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP Addons, Open Source Management Solution    
#    Copyright (C) 2013-2014 Jorge Valdiviezo (jorgito2006@gmail.com) All Rights Reserved     
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

from osv import fields,osv
from tools.translate import _
from sql_db_remote import get_connect_server
from orm import check_filestore,get_directory
import psycopg2
from tempfile import TemporaryFile

class base_synchro_server(osv.osv):
    '''Class to store the information regarding server'''
    _name = "base.synchro.server"
    _description = "Synchronized server"
    _columns = {
        'name': fields.char('Server name', size=64,required=True),
        'server_url': fields.char('Server URL', size=64,required=True),
        'server_port': fields.integer('Server Port', size=64,required=True),
        'server_db': fields.char('Server Database', size=64,required=True),
        'login': fields.char('User Name',size=50,required=True),
        'password': fields.char('Password',size=64,required=True),
        'active': fields.boolean('Active'),
        'obj_without_sync':fields.many2many('ir.model', 'rel_synchro_model', 'synchro_server_id', 'model_id', 'Objects without synchronize'),
    }
    _defaults = {
        'server_port': lambda *args: 5432,
        'active': True,
    }

    def connection(self, server, context=None):
        try:
            connection=get_connect_server(server).get_connect()
            return connection
        except psycopg2.Error, e:
            raise osv.except_osv('Error!', _("Could not establish the connection : %s" %e))
    
    def check_connection(self, cr, uid, ids, context=None):
        for server in self.browse(cr, uid, ids, context):
            self.connection(server, context)
        raise osv.except_osv(_("Message!"), _("Connection test succeeded!"))
    
    def write_sql_servers(self, cr, uid, context=None):
        full_path=get_directory(self ,cr, uid)
        check_filestore(self, full_path)
        fileobj = TemporaryFile('rw+')
        with open(full_path, 'r') as ofile:
            for linea in ofile.readlines():
                tup = linea.split(':$')
                try:
                    server = self.browse(cr, uid, int(tup[0]),context)
                    cr_remote=get_connect_server(server).get_cursor()
                    cr_remote.execute(tup[1],eval(tup[2]))
                    cr_remote.commit()
                    cr_remote.close()
                except psycopg2.Error, e:
                    osv._logger.warning("Error in operation %s",e)
                    fileobj.write(linea)
                except:
                    osv._logger.warning("Could not establish the connection to server %s",server.server_url)
        fileobj.seek(0)
        with open(full_path, 'w') as ofile:
            ofile.write(fileobj.read())
        fileobj.close()
        return True
base_synchro_server()

class base_synchro_object(osv.osv):
    _name = "base.synchro.object"
    _description = "objects that are not synchronized"
    _columns = {
        'model_id': fields.many2one('ir.model', 'Object not alter sequence',required=True),
    }
    _rec_name='model_id'
base_synchro_object()