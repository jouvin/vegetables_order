#!/usr/bin/env python

import sys
import argparse
import csv

EMAIL_FIELD = 'E-mail'
NAME_FIELD = 'NOM - PRENOM'


def write_client_orders(output_file, orders):
    if output_file is None:
        output = sys.stdout
    else:
        output = open(output_file, 'w', encoding='utf-8')

    for name,entry in orders.items():
        print('-----------------------------------------------------------', file=output)
        print("Commande pour {}".format(name), file=output)
        for item,quantity in entry.items():
            print('{}: {}'.format(item, quantity), file=output)
        print('-----------------------------------------------------------', file=output)
        print(file=output)


def write_harvest_quantity(output_file, harvest_products):
    if output_file is None:
        output = sys.stdout
    else:
        output = open(output_file, 'w', encoding='utf-8')

    print('----------- Produits à récolter --------------------', file=output)
    for product, quantity in harvest_products.items():
        print("{}: {}".format(product, quantity), file=output)


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--clients', action='store_true', default=False, help='Commandes clients')
    action.add_argument('--harvest', '--recolte', action='store_true', default=False, help='Produits à récolter')
    parser.add_argument('--output', help='Nom de fichier de sortie')
    parser.add_argument('csv', help='Fichier des commandes Framaform')
    options = parser.parse_args()

    orders = dict()
    harvest_products = dict()

    try:
        with open(options.csv, 'r') as csvfile:
            rows = csv.DictReader(csvfile, delimiter=';')
            for row in rows:
                name = None
                entry = dict()
                for k,v in row.items():
                    if name is None:
                        if k == NAME_FIELD:
                            if v != '':
                                name = v
                            else:
                                raise Exception('Entrée invalide: le nom est vide')
                        continue
                    # If the field is a product, create an entry in the product list to keep the original order of products
                    if k != EMAIL_FIELD:
                        if k not in harvest_products:
                            harvest_products[k] = 0
                    if v != '':
                        entry[k] = v
                        if k != EMAIL_FIELD:
                            harvest_products[k] += float(v)
                    elif k == EMAIL_FIELD:
                        entry[EMAIL_FIELD] = 'non spécifié'
                orders[name] = entry
    except:
        print("Erreur lors de l'ouverture du fichier {}".format(options.csv))
        raise

    if options.clients:
        write_client_orders(options.output, orders)

    if options.harvest:
        write_harvest_quantity(options.output, harvest_products)


if __name__ == "__main__":
    exit(main())