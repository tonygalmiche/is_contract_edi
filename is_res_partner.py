# -*- coding: utf-8 -*-

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
