#!/usr/bin/env python

import sys
import re
import argparse
import csv

EMAIL_FIELD = 'E-mail'
NAME_FIELD = 'NOM - PRENOM'

PRODUCT_PRICE_PATTERN = re.compile(r'\s*(?P<product>.+)\s*-\s*(?P<price>[0-9,]+€)\s*/\s*(?P<unit>\w+)\s*')


class Product():
    def __init__(self, quantity, price, unit):
        self.quantity = quantity
        self.price = price
        self.unit = unit

    def total_price(self):
        return self.price * self.quantity


class Client():
    def __init__(self,email):
        self.email = email
        self.products = []

    def add_product(self, product):
        self.products.append(product)

    def get_products(self):
        return(self.products)


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

    products_not_ordered = []
    print('----------- Produits à récolter --------------------', file=output)
    for product, quantity in harvest_products.items():
        if quantity > 0:
            print("{}: {}".format(product, quantity), file=output)
        else:
            products_not_ordered.append(product)

    if len(products_not_ordered) > 0:
        print('\n----------- Produits sans commande --------------------', file=output)
        for product in products_not_ordered:
            print(product)

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
                    m = PRODUCT_PRICE_PATTERN.match(k)
                    if m:
                        product = m.group('product')
                    elif k == EMAIL_FIELD:
                        product = k
                    else:
                        raise Exception('Format produit invalide ({}).format(k)')
                    if product != EMAIL_FIELD:
                        if product not in harvest_products:
                            harvest_products[product] = 0
                    if v != '':
                        entry[product] = v
                        if product != EMAIL_FIELD:
                            harvest_products[product] += float(v)
                    elif product == EMAIL_FIELD:
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