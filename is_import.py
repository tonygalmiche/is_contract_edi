# -*- coding: utf-8 -*-

import csv
import numpy as np
import xlrd

from openerp.tools.translate import _
from openerp import netsvc
from openerp.osv import osv, fields
from lxml import etree
from tempfile import TemporaryFile
import base64
import os
import time
from datetime import date, datetime

class is_contract_automobile(osv.osv):
    _name = "is.contract.automobile.line"
    _columns = {
        'ref_partner': fields.char('Reference commande client', size=64),
        'ref_product': fields.char('Reference article client', size=64),
        'import_id': fields.many2one('is.import.contract', 'Import'),
    }
    
is_contract_automobile()


class is_import_contract(osv.osv):
    _name = "is.import.contract"
    _description = "Importer les commandes ouvertes"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Client', required=True),
        'import_function': fields.char("Fonction d'importation EDI", size=32, required=True),
        'name': fields.char('Nom de fichier', size=128),
        'file': fields.binary('Fichier', required=True),
        'create_uid': fields.many2one('res.users', 'Importe par', readonly=True),
        'create_date': fields.datetime("Date d'importation"),
        'notfound_contract': fields.boolean('Contrats non trouves'),
        'contract_ids': fields.one2many('is.contract.automobile.line', 'import_id', "Contrats non trouves dans le fichier d'import"),
    }
    
    _defaults = {
        'notfound_contract': False,
    }
    
    # Remplir le champ import_function à partir de champ partner_id
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not part:
            return {}

        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        val = {
            'import_function': part.import_function,
        }
        return {'value': val}
   
    def _create_message_log(self, cr, uid, id_import, msg_error, context=None):  
        msg_obj = self.pool.get('mail.message')       
        mail_values = {
                        'type' :'comment',
                        'model': 'casa_porta.import',
                        'body': '<p>' + msg_error + '<p>',
                        'res_id':id_import
                    }
        msg_obj.create(cr, uid, mail_values)
    
    # Retourner les contrats de la liste des informations extrait de fichier d'importation
    def get_contracts(self, cr, uid, data, context=None):
        res = []
        
        if data:
            for item in data:
                res.append((item['ref_product'], item['ref_partner']))
        return res
                  
    # Retourner la liste des contrats (couple(refcommandeclient, refproduitclient)) lié au client choisi
    def get_contracts_partner(self, cr, uid, partner_id, context=None):
        res = []
        contract_obj = self.pool.get('contract.automobile')
        
        contract_ids = contract_obj.search(cr, uid, [('partner_id', '=', partner_id)], context=context)
        if contract_ids:
            for contract in contract_obj.read(cr, uid, contract_ids, ['ref_product','ref_partner']):
                res.append((contract['ref_product'], contract['ref_partner']))
        return res
    
    # Comparer la liste des contrats de fichier d'importaion avec celle associée au client
    # Retourner les contrats non trouvés
    def compare_lst_contracts(self, cr, uid, lst_contracts_partner, lst_contracts, context=None):
        res = []
        for contract in lst_contracts:
            if not contract in lst_contracts_partner:
                res.append(contract)
            else:
                continue
        return res
    
    # Faire Afficher la liste des contrats non existants
    def contracts_notfound(self, cr, uid, id, lst_contracts_notfound, context=None):
        res = []
        print "lst_contracts_notfound*****", lst_contracts_notfound
        for contract in lst_contracts_notfound:
            newid = self.pool.get('is.contract.automobile.line').create(cr, uid, {'ref_partner': contract[0], 
                                                                                  'ref_product': contract[1], 
                                                                                  'import_id':id}, 
                                                                        context=context)
            res.append(newid)
        return res 
    
    # Retourner l'id de contrat associé au couple (refcommandeclient, refproduitclient)
    def get_contract_id(self, cr, uid, ref_partner, ref_product, context=None):
        contract_obj = self.pool.get('contract.automobile')
        contract_id = contract_obj.search(cr, uid, [('ref_partner','=',ref_partner),('ref_product','=',ref_product)], context=context)[0]
        return contract_id
    
    # Supprimer les devis associé au contrat courant et ayant une date supérieure à la date de jour
    def delete_quotations(self, cr, uid, contract_id, context=None):
        order_obj = self.pool.get('sale.order')
        today = time.strftime('%Y-%m-%d')
        order_ids = order_obj.search(cr, uid, [('contract_id','=',contract_id),('state','=','draft'),('date_livraison','>=',today)], context=context)
        res = order_obj.unlink(cr, uid, order_ids, context=context)
        return res
    
    # interpreter la date de livraison de fichier d'importation
    def convert_date(self, cr, uid, import_function, date_livraison, context=None):
        if import_function == 'xml1':
            date = time.strptime(date_livraison, '%Y%m%d%H%M%S')
            return time.strftime('%Y-%m-%d', date)
        elif import_function == 'csv1':
            date = time.strptime(date_livraison, '%d.%m.%Y')
            return time.strftime('%Y-%m-%d', date)
        
    # interpreter le type de contrat de fichier d'importation
    def convert_contract_type(self, cr, uid, import_function, contract_type, context=None):
        if import_function == 'xml1':
            if contract_type == '1':
                return 'ferme'
            elif contract_type == '4':
                return 'previsionnel'
            else:
                return ''
        if import_function == 'csv1':
            if contract_type == 'F':
                return 'ferme'
            elif contract_type == 'P':
                return 'previsionnel'
            else:
                return ''       
    
    # Creation de devis
    def create_quotation(self, cr, uid, ids, import_function, contract_id, partner_id, detail, context=None):
        order_obj = self.pool.get('sale.order')
        order_line_obj = self.pool.get('sale.order.line')
        contract_obj = self.pool.get('contract.automobile')
        
        contract = contract_obj.browse(cr, uid, contract_id, context=context)
        
        quotation_line = order_line_obj.product_id_change(cr, uid, ids, 1, contract.product_id.id, 0, False, 0, False, '', partner_id, False, True, False, False, False, False, context=context)['value']
        quotation_line.update({'product_id':contract.product_id.id, 'product_uom_qty': detail['qty_product']})
                    
        quotation = order_obj.onchange_partner_id(cr, uid, ids, partner_id, context=context)['value']

        date_livraison = self.convert_date(cr, uid, import_function, detail['date_livraison'], context=context)       
        date_expedition = order_obj.onchange_date_livraison(cr, uid, ids, date_livraison, partner_id, context=context)['value']['date_expedition']
        type = self.convert_contract_type(cr, uid, import_function, detail['type_contract'], context=context)
        
        if contract.ref_partner:
            origin = contract.ref_partner   + ', ' + contract.ref_product
        else:
            origin = contract.ref_product
            
        quotation_values = {
            'name': '/',
            'partner_id': partner_id,
            'client_order_ref': contract.ref_partner,
            'contract_id': contract.id,
            'type_contrat': type ,
            'date_livraison': date_livraison,
            'date_expedition': date_expedition,
            'origin': origin,
            'order_line': [[0,False,quotation_line]],
            'picking_policy': 'direct',
            'order_policy': 'manual',
            'invoice_quantity': 'order',
        }

        quotation.update(quotation_values)
        newid = order_obj.create(cr, uid, quotation, context=context)
        return newid

        
    def import_contract_orders(self, cr, uid, ids, context=None):          
        if context is None:
            context = {}
        
        xml1_obj = self.pool.get('is_import_xml1')
        csv1_obj = self.pool.get('is_import_csv1')
        result = []
        
        data = self.read(cr, uid, ids)[0]       
        if data:
            # Extraire les informations du fichier d'importation à utiliser dans la création des commandes ouvertes      
            if data['import_function'] == 'xml1':
                res = xml1_obj.get_data_xml(cr, uid, data, context=context)
            elif data['import_function'] == 'csv1':
                res = csv1_obj.get_data_csv(cr, uid, data, context=context)
            else:
                res = []
                
            print "res********", res
            lst_contracts = self.get_contracts(cr, uid, res, context=context)
            print "lst_contracts********", lst_contracts
            lst_contracts_partner = self.get_contracts_partner(cr, uid, data['partner_id'][0], context=context)
            print "lst_contracts_partner********", lst_contracts_partner
            lst_contracts_notfound = self.compare_lst_contracts(cr, uid, lst_contracts_partner, lst_contracts, context=context)
            if lst_contracts_notfound:
                print "lst_contracts_notfound********", lst_contracts_notfound
                self.write(cr, uid, ids[0], {'notfound_contract': True}, context=context)
                line_ids = self.contracts_notfound(cr, uid, ids[0], lst_contracts_notfound, context=context)
                return line_ids               
            else:
                for item in res:
                    # déterminer l'id de contrat associé au couple (refcommandeclient, refproduitclient)
                    contract_id = self.get_contract_id(cr, uid, item['ref_partner'], item['ref_product'], context=context)
                    # Suppression des devis ayant une date de livraison supérieure à la date de jour
                    self.delete_quotations(cr, uid, contract_id, context=context)
                    for detail in item['details']:
                        newid = self.create_quotation(cr, uid, ids, data['import_function'], contract_id, data['partner_id'][0], detail, context=context)
                        result.append(newid)
        
        result.sort()                
        action_model = False
        data_pool = self.pool.get('ir.model.data')
        action = {}
        action_model,action_id = data_pool.get_object_reference(cr, uid, 'sale', "action_quotations")
        
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,result))+"])]"
        return action
                
                
            
#===============================================================================
#     def import_csv(self, cr, uid, ids, context=None):
#         if context is None:
#             context = {}
#             
#         data = self.read(cr, uid, ids)[0]
#         print "data *******", data
#         
#         result = []
# 
#         if data:   
#             quotechar='"'
#             delimiter=','
#             
#             name = str(datetime.now()).replace(':', '').replace('.', '').replace(' ', '')
#             filename = '/tmp/%s.xls' % name
#             temp = open(filename, 'w+b')
#             temp.write((base64.decodestring(data['file']))) 
#             temp.close()
#                     
#             csv_file = self.csv_from_excel(cr, uid, filename, name, context=context)
#             file_obj = open(csv_file, 'rb')
#             reader = csv.reader(file_obj, quotechar=str(quotechar), delimiter=str(delimiter))
#             
#             # Extraire les informations à utiliser dans la création des commandes ouvertes          
#             res = self.get_data_csv(cr, uid, reader, context=context)
#             print "get_data ********", res
#             lst_contracts_csv = self.get_contracts_xml(cr, uid, res, context=context)
#             print "lst_contracts_xml**********", lst_contracts_csv
#             lst_contracts_partner = self.get_contracts_partner(cr, uid, data['partner_id'][0], context=context)
#             print "lst_contracts_partner********", lst_contracts_partner
#             lst_contracts_notfound = self.compare_lst_contracts(cr, uid, lst_contracts_partner, lst_contracts_csv, context=context)
#             print "lst_contracts_notfound*******", lst_contracts_notfound
#             if lst_contracts_notfound:
#                 raise osv.except_osv(_("Warning"), _("Le fichier d'import ne contient pas tous les contrats du client"))
#             else:
#                 for item in res:
#                     # déterminer l'id de contrat associé au couple (refcommandeclient, refproduitclient)
#                     contract_id = self.get_contract_id(cr, uid, item['ref_partner'], item['ref_product'], context=context)
#                     # Suppression des devis ayant une date de livraison supérieure à la date de jour
#                     self.delete_quotations(cr, uid, contract_id, context=context)
#                     for detail in item['details']:
#                         newid = self.create_quotation(cr, uid, ids, data['import_function'], contract_id, data['partner_id'][0], detail, context=context)
#                         result.append(newid)
#                         
#         action_model = False
#         data_pool = self.pool.get('ir.model.data')
#         action = {}
#         action_model,action_id = data_pool.get_object_reference(cr, uid, 'sale', "action_quotations")
#         
#         if action_model:
#             action_pool = self.pool.get(action_model)
#             action = action_pool.read(cr, uid, action_id, context=context)
#             action['domain'] = "[('id','in', ["+','.join(map(str,result))+"])]"
#         return action   
#===============================================================================
    
is_import_contract()
