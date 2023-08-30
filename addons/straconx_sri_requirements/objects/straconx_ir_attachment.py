# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
##############################################################################

import itertools

from osv import fields,osv
from osv.orm import except_orm
import tools

class ir_attachment(osv.osv):

    def unlink(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'active':False})
        return True


    _inherit = 'ir.attachment'
    _columns = {
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }

ir_attachment()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

