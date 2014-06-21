# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Asma BOUSSELMI - CONSULTANT OPENERP CONFIRME
#
##############################################################################

from datetime import datetime, timedelta
import time
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _


class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'import_function': fields.selection([('xml1','Fonction XML1'),('csv1','Fonction CSV1')], "Fonction d'importation EDI"),
    }
    

res_partner()
