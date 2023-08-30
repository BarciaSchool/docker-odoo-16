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

from functools import wraps
from tools.func import frame_codeinfo
from inspect import currentframe
import tools

from datetime import datetime as mdt
from datetime import timedelta

import psycopg2
from psycopg2.psycopg1 import cursor as psycopg1cursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ
import logging
_logger = logging.getLogger(__name__)

import re
re_from = re.compile('.* from "?([a-zA-Z_0-9]+)"? .*$');
re_into = re.compile('.* into "?([a-zA-Z_0-9]+)"? .*$');
sql_counter_remote = 0


# class Cursor_remote(object):
#      
#     IN_MAX = 1000 # decent limit on size of IN queries - guideline = Oracle limit
#      
#     def check(f):
#         @wraps(f)
#         def wrapper(self, *args, **kwargs):
#             if self.__closed:
#                 msg = 'Unable to use a closed cursor.'
#                 if self.__closer:
#                     msg += ' It was closed at %s, line %s' % self.__closer
#                 raise psycopg2.OperationalError(msg)
#             return f(self, *args, **kwargs)
#         return wrapper
#      
#     def __init__(self, connection, dbname, serialized=True):
#         self.sql_from_log = {}
#         self.sql_into_log = {}
#  
#         # default log level determined at cursor creation, could be
#         # overridden later for debugging purposes
#         self.sql_log = _logger.isEnabledFor(logging.DEBUG)
#  
#         self.sql_log_count = 0
#         self.__closed = True    # avoid the call of close() (by __del__) if an exception
#                                 # is raised by any of the following initialisations
#         self.dbname = dbname
#  
#         # Whether to enable snapshot isolation level for this cursor.
#         # see also the docstring of Cursor.  
#         self._serialized = serialized
#  
#         self._cnx = connection
#         self._obj = self._cnx.cursor(cursor_factory=psycopg1cursor)
#         if self.sql_log:
#             self.__caller = frame_codeinfo(currentframe(),2)
#         else:
#             self.__caller = False
#         self.__closed = False   # real initialisation value
#         self.autocommit(False)
#         self.__closer = False
#  
#         self._default_log_exceptions = True
#          
#     def __del__(self):
#         if not self.__closed and not self._cnx.closed:
#             # Oops. 'self' has not been closed explicitly.
#             # The cursor will be deleted by the garbage collector,
#             # but the database connection is not put back into the connection
#             # pool, preventing some operation on the database like dropping it.
#             # This can also lead to a server overload.
#             msg = "Cursor not closed explicitly\n"
#             if self.__caller:
#                 msg += "Cursor was created at %s:%s" % self.__caller
#             else:
#                 msg += "Please enable sql debugging to trace the caller."
#             _logger.warning(msg)
#             self._close(True)
#          
#     def execute(self, query, params=None, log_exceptions=None):
#         if '%d' in query or '%f' in query:
#             _logger.warning(query)
#             _logger.warning("SQL queries cannot contain %d or %f anymore. "
#                          "Use only %s")
#  
#         if self.sql_log:
#             now = mdt.now()
#  
#         try:
#             params = params or None
#             res = self._obj.execute(query, params)
#         except psycopg2.ProgrammingError, pe:
#             if (self._default_log_exceptions if log_exceptions is None else log_exceptions):
#                 _logger.error("Programming error: %s, in query %s", pe, query)
#             raise
#         except Exception:
#             if (self._default_log_exceptions if log_exceptions is None else log_exceptions):
#                 _logger.exception("bad query: %s", self._obj.query or query)
#             raise
#  
#         if self.sql_log:
#             delay = mdt.now() - now
#             delay = delay.seconds * 1E6 + delay.microseconds
#  
#             _logger.debug("query: %s", self._obj.query)
#             self.sql_log_count+=1
#             res_from = re_from.match(query.lower())
#             if res_from:
#                 self.sql_from_log.setdefault(res_from.group(1), [0, 0])
#                 self.sql_from_log[res_from.group(1)][0] += 1
#                 self.sql_from_log[res_from.group(1)][1] += delay
#             res_into = re_into.match(query.lower())
#             if res_into:
#                 self.sql_into_log.setdefault(res_into.group(1), [0, 0])
#                 self.sql_into_log[res_into.group(1)][0] += 1
#                 self.sql_into_log[res_into.group(1)][1] += delay
#         return res
#  
#  
#     def split_for_in_conditions(self, ids):
#         """Split a list of identifiers into one or more smaller tuples
#            safe for IN conditions, after uniquifying them."""
#         return tools.misc.split_every(self.IN_MAX, set(ids))
#  
#     def print_log(self):
#         global sql_counter_remote
#         sql_counter_remote += self.sql_log_count
#         if not self.sql_log:
#             return
#         def process(type):
#             sqllogs = {'from':self.sql_from_log, 'into':self.sql_into_log}
#             sum = 0
#             if sqllogs[type]:
#                 sqllogitems = sqllogs[type].items()
#                 sqllogitems.sort(key=lambda k: k[1][1])
#                 _logger.debug("SQL LOG %s:", type)
#                 sqllogitems.sort(lambda x,y: cmp(x[1][0], y[1][0]))
#                 for r in sqllogitems:
#                     delay = timedelta(microseconds=r[1][1])
#                     _logger.debug("table: %s: %s/%s",
#                                         r[0], delay, r[1][0])
#                     sum+= r[1][1]
#                 sqllogs[type].clear()
#             sum = timedelta(microseconds=sum)
#             _logger.debug("SUM %s:%s/%d [%d]",
#                                 type, sum, self.sql_log_count, sql_counter_remote)
#             sqllogs[type].clear()
#         process('from')
#         process('into')
#         self.sql_log_count = 0
#         self.sql_log = False
#  
#     @check
#     def close(self):
#         return self._close(False)
#  
#     def _close(self, leak=False):
#         if not self._obj:
#             return
#  
#         if self.sql_log:
#             self.__closer = frame_codeinfo(currentframe(),3)
#         self.print_log()
#  
#         self._obj.close()
#  
#         # This force the cursor to be freed, and thus, available again. It is
#         # important because otherwise we can overload the server very easily
#         # because of a cursor shortage (because cursors are not garbage
#         # collected as fast as they should). The problem is probably due in
#         # part because browse records keep a reference to the cursor.
#         del self._obj
#         self.__closed = True
#  
#         # Clean the underlying connection.
#         self._cnx.rollback()
#  
# #        if leak:
# #            self._cnx.leaked = True
# #        else:
# #            chosen_template = tools.config['db_template']
# #            templates_list = tuple(set(['template0', 'template1', 'postgres', chosen_template]))
# #            keep_in_pool = self.dbname not in templates_list
# #            self._pool.give_back(self._cnx, keep_in_pool=keep_in_pool)
#  
#     @check
#     def autocommit(self, on):
#         if on:
#             isolation_level = ISOLATION_LEVEL_AUTOCOMMIT
#         else:
#             # If a serializable cursor was requested, we
#             # use the appropriate PotsgreSQL isolation level
#             # that maps to snaphsot isolation.
#             # For all supported PostgreSQL versions (8.3-9.x),
#             # this is currently the ISOLATION_REPEATABLE_READ.
#             # See also the docstring of this class.
#             # NOTE: up to psycopg 2.4.2, repeatable read
#             #       is remapped to serializable before being
#             #       sent to the database, so it is in fact
#             #       unavailable for use with pg 9.1.
#             isolation_level = ISOLATION_LEVEL_REPEATABLE_READ \
#                                   if self._serialized \
#                                   else ISOLATION_LEVEL_READ_COMMITTED
#         self._cnx.set_isolation_level(isolation_level)
#  
#     @check
#     def commit(self):
#         """ Perform an SQL `COMMIT`
#         """
#         return self._cnx.commit()
#  
#     @check
#     def rollback(self):
#         """ Perform an SQL `ROLLBACK`
#         """
#         return self._cnx.rollback()
#  
#     @check
#     def __getattr__(self, name):
#         return getattr(self._obj, name)
#  
#         """ Set the mode of postgres operations for all cursors
#         """
#         """Obtain the mode of postgres operations for all cursors
#         """
#         
# class connect_host_remote(object):
#     def __init__(self, database, login, password, host, port):
#         self.database = database
#         self.login=login
#         self.password=password
#         self.host=host
#         self.port=port
#         self.con=None
#     def get_connect(self):
#         if not self.con:
#             self.con = psycopg2.connect(database=self.database, user=self.login, password=self.password, host=self.host, port=self.port)
#         return self.con
#     def get_cursor(self):
#         con=self.get_connect()
#         cur = Cursor_remote(con, self.database)
#         return cur
#     
# initializer={}

# def get_connect_server(server):
#     global initializer
#     if not initializer.get(server.server_url,False):
#         connection=connect_host_remote(server.server_db, server.login, server.password, server.server_url, server.server_port)
#         initializer.update({server.server_url:connection})
#     else:
#         con = initializer.get(server.server_url,False)
#         try:
#             cr=con.get_cursor()
#             cr.close()
#         except psycopg2.Error, e:
#             connection=connect_host_remote(server.server_db, server.login, server.password, server.server_url, server.server_port)
#             initializer.update({server.server_url:connection})
#     return initializer.get(server.server_url,None)

