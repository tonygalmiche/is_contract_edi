# -*- coding: utf-8 -*-

{
    'name': 'Importation des commandes ouvertes',
    'version': '1.0',
    'category': 'InfoSaône',
    'description': """
Importation des commandes ouvertes via des fichiers xml et csv
    """,
    'author': 'Tony GALMICHE / Asma BOUSSELMI',
    'maintainer': 'InfoSaône',
    'website': 'http://www.infosaone.com',
    'depends': ['sale', 'is_automobile_contract'],
    'data': [
             'view/is_contract_menu.xml',
             'view/is_res_partner_view.xml',
             'wizard/is_import_contract_view.xml',
        ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
