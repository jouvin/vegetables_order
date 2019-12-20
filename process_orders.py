#!/usr/bin/env python

import sys
import re
import argparse
import csv
from reportlab.platypus import SimpleDocTemplate, PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch
from reportlab.lib import colors


EMAIL_FIELD = 'E-mail'
NAME_FIELD = 'NOM - PRENOM'

PRODUCT_PRICE_PATTERN = re.compile(r'\s*(?P<product>.+)\s*-\s*(?P<price>[0-9,]+)€\s*/\s*(?P<unit>\w+)\s*')

PAGE_HEIGHT=defaultPageSize[1]
PAGE_WIDTH=defaultPageSize[0]

# Singleton decorator definition
def singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class PDFParams:
    def __init__(self):
        self.doc = None
        self.story = None
        self.email_style = None
        self.normal_style = None
        self.subtitle_style = None
        self.table_style = None
        self.table_title_style = None
        self.title_style = None
        self.total_style = None

@singleton
class TextFileParams:
    def __init__(self):
        self.file = None


class Product():
    def __init__(self, price, unit):
        self.price = float(re.sub(',', '.', price))
        self.price_unit = unit
        self.ordered_quantity = 0

    def get_ordered_quantity(self):
        return self.ordered_quantity

    def get_price(self):
        return self.price

    def get_price_unit(self):
        return self.price_unit

    def increase_quantity(self, quantity):
        self.ordered_quantity += float(re.sub(',', '.', quantity))


class ProductOrder():
    def __init__(self, name):
        self.name = name
        self.quantity = 0
        self.quantity_unit = None
        self.price = 0

    def get_name(self):
        return self.name

    def get_quantity(self):
        return self.quantity

    def get_quantity_unit(self):
        return self.quantity_unit

    def set_quantity(self, quantity, product_params):
        self.quantity = float(re.sub(',', '.', quantity))
        self.quantity_unit = product_params.get_price_unit()
        self.price = product_params.get_price() * self.quantity

    def total_price(self):
        return self.price


class Client():
    def __init__(self):
        self.email = None
        self.products = []
        self.total_price = None

    def add_product(self, product):
        self.products.append(product)

    def get_email(self):
        return self.email

    def get_products(self):
        return self.products

    def get_total_price(self):
        if self.total_price is None:
            self.total_price = 0
            for product in self.products:
                self.total_price += product.total_price()
        return self.total_price

    def set_email(self, email):
        self.email = email


def text_file_init(output_file):
    file_params = TextFileParams()
    if output_file is None:
        file_params.file = sys.stdout
    else:
        file_params.file = open(output_file, 'w', encoding='utf-8')

def write_client_orders(output_file, orders):
    file_params = TextFileParams()
    if file_params.file is None:
        text_file_init(output_file)

    for name,entry in orders.items():
        client_email = entry.get_email()

        if client_email is None:
            client_email = "email non spécifié"

        print('-----------------------------------------------------------', file=file_params.file)
        print("Commande pour {} ({})".format(name, client_email), file=file_params.file)
        for product in entry.get_products():
            print('{}: {} {}\t({:.2f}€)'.format(product.get_name(),
                                                product.get_quantity(),
                                                product.get_quantity_unit(),
                                                product.total_price()), file=file_params.file)
        print("\nPrix total = {:.2f}€".format(entry.get_total_price()), file=file_params.file)
        print('-----------------------------------------------------------', file=file_params.file)
        print(file=file_params.file)


def write_harvest_quantity(output_file, harvest_products):
    file_params = TextFileParams()
    if file_params.file is None:
        text_file_init(output_file)

    products_not_ordered = []
    print('----------- Produits à récolter --------------------', file=file_params.file)
    for name, product in harvest_products.items():
        if product.get_ordered_quantity() > 0:
            print("{}: {} {}\t({:.2f}€/{})".format(name,
                                                   product.get_ordered_quantity(),
                                                   product.get_price_unit(),
                                                   product.get_price(),
                                                   product.get_price_unit()), file=file_params.file)
        else:
            products_not_ordered.append(name)

    if len(products_not_ordered) > 0:
        print('\n----------- Produits sans commande --------------------', file=file_params.file)
        for product_name in products_not_ordered:
            print(product_name, file=file_params.file)


def PDFPageLayout(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman',9)
    canvas.drawString(inch, 0.75 * inch, "Page {}".format(doc.page))
    canvas.restoreState()


def PDFInit(filename):
    pdf_params = PDFParams()
    pdf_params.doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()
    pdf_params.normal_style = styles["Normal"]
    pdf_params.title_style = styles["Heading1"]
    pdf_params.title_style.alignment = 1
    pdf_params.subtitle_style = styles["Heading3"]
    pdf_params.subtitle_style.alignment = 1
    pdf_params.email_style = ParagraphStyle(pdf_params.normal_style)
    pdf_params.email_style.alignment = 1
    pdf_params.total_style = ParagraphStyle(pdf_params.normal_style)
    pdf_params.total_style.fontName = pdf_params.title_style.fontName

    pdf_params.table_style = TableStyle([('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                                         ('BOX', (0,0), (-1,-1), 0.25, colors.black),])
    pdf_params.table_title_style = ParagraphStyle(pdf_params.normal_style)
    pdf_params.table_title_style.fontName = pdf_params.title_style.fontName

    pdf_params.story = []


def client_orders_pdf(filename, orders):
    pdf_params = PDFParams()
    if pdf_params.doc is None:
        PDFInit(filename)

    for name,entry in orders.items():
        client_email = entry.get_email()
        if client_email is None:
            client_email = "non spécifié"

        pdf_params.story.append(Paragraph("Commande de {}".format(name), pdf_params.title_style))
        pdf_params.story.append(Paragraph("Email : {}".format(client_email), pdf_params.email_style))
        pdf_params.story.append(Spacer(1, 0.2 * inch))

        product_table = [[[Paragraph("Produit", style=pdf_params.table_title_style)],
                          [Paragraph("Quantité", style=pdf_params.table_title_style)],
                          [Paragraph("Prix", style=pdf_params.table_title_style)]]]
        for product in entry.get_products():
            product_table.append([product.get_name(),
                                  '{} {}'.format(product.get_quantity(), product.get_quantity_unit()),
                                  '{:.2f}€'.format(product.total_price())])
        pdf_params.story.append(Table(product_table, style=pdf_params.table_style))

        total_line = "\nPrix total pour {} = {:.2f}€".format(name, entry.get_total_price())
        pdf_params.story.append(Spacer(1, 0.2 * inch))
        pdf_params.story.append(Paragraph(total_line, pdf_params.total_style))
        pdf_params.story.append(Spacer(1, 1 * inch))
        #pdf_params.story.append(PageBreak())


def harvest_quantity_pdf(filename, harvest_products):
    pdf_params = PDFParams()
    if pdf_params.doc is None:
        PDFInit(filename)
    else:
        pdf_params.story.append(PageBreak())

    pdf_params.story.append(Paragraph("Produits à récolter", pdf_params.title_style))

    products_not_ordered = []
    product_table = [[[Paragraph("Produit", style=pdf_params.table_title_style)],
                      [Paragraph("Quantité", style=pdf_params.table_title_style)],
                      [Paragraph("Prix unitaire", style=pdf_params.table_title_style)]]]
    for name, product in harvest_products.items():
        if product.get_ordered_quantity() > 0:
            product_table.append([name,
                                  '{} {}'.format(product.get_ordered_quantity(), product.get_price_unit()),
                                  '{}€/{}'.format(product.get_price(), product.get_price_unit())])
        else:
            products_not_ordered.append(name)
    pdf_params.story.append(Table(product_table, style=pdf_params.table_style))

    product_table = [[Paragraph("Produit", style=pdf_params.table_title_style)]]
    if len(products_not_ordered) > 0:
        pdf_params.story.append(Paragraph("Produits sans commande ", pdf_params.subtitle_style))
        for product_name in products_not_ordered:
            product_table.append([name])
        pdf_params.story.append(Table(product_table, style=pdf_params.table_style))


# Must no be called before client_orders_pdf() or the price will be wrong
def clients_summary_pdf(filename, orders):
    pdf_params = PDFParams()
    if pdf_params.doc is None:
        PDFInit(filename)
    else:
        pdf_params.story.append(PageBreak())

    pdf_params.story.append(Paragraph("Somme Dûe par Client", pdf_params.title_style))

    clients_table = [[[Paragraph("Nom", style=pdf_params.table_title_style)],
                      [Paragraph("Somme Dûe", style=pdf_params.table_title_style)]]]
    for name,entry in orders.items():
        clients_table.append([name,
                              '{:.2f}€'.format(entry.get_total_price())])
    pdf_params.story.append(Table(clients_table, style=pdf_params.table_style))


def write_pdf_file():
    pdf_params = PDFParams()
    pdf_params.doc.build(pdf_params.story, onFirstPage=PDFPageLayout, onLaterPages=PDFPageLayout)


def main():
    parser = argparse.ArgumentParser()
    clients = parser.add_mutually_exclusive_group()
    clients.add_argument('--clients', action='store_true', default=True, help='Commandes clients')
    clients.add_argument('--no-clients', action='store_false', dest='clients', help='Ne pas produire les commandes clients')
    harvest = parser.add_mutually_exclusive_group()
    harvest.add_argument('--harvest', '--recolte', action='store_true', default=True, help='Produits à récolter')
    harvest.add_argument('--no-harvest', '--no-recolte', action='store_false', dest='harvest', help='Produits à récolter')
    parser.add_argument('--output', help='Nom de fichier de sortie')
    parser.add_argument('--format', choices=['pdf', 'text'], default='pdf', help='Ecrire un fichier PDF au lieu de texte')
    parser.add_argument('csv', help='Fichier des commandes Framaform')
    options = parser.parse_args()
    if options.format == 'pdf':
        pdf_output = True
    else:
        pdf_output = False

    orders = dict()
    harvest_products = dict()

    try:
        with open(options.csv, 'r') as csvfile:
            rows = csv.DictReader(csvfile, delimiter=';')
            while NAME_FIELD not in rows.fieldnames:
                rows = csv.DictReader(csvfile, delimiter=';')
            for row in rows:
                name = None
                client = Client()
                for k,v in row.items():
                    if name is None:
                        if k == NAME_FIELD:
                            if v != '':
                                name = v
                            else:
                                raise Exception('Entrée invalide: le nom est vide')
                        continue
                    elif k == EMAIL_FIELD:
                        if v != "":
                            client.set_email(v)
                        continue

                    # If the field is a product, create an entry in the product list to keep the original order of products
                    m = PRODUCT_PRICE_PATTERN.match(k)
                    if m:
                        product_name = m.group('product')
                        product_order = ProductOrder(product_name)
                    else:
                        raise Exception('Format produit invalide ({})'.format(k))

                    if product_name not in harvest_products:
                        harvest_products[product_name] = Product(m.group('price'), m.group('unit'))
                    if v != '':
                        product_order.set_quantity(v, harvest_products[product_name])
                        harvest_products[product_name].increase_quantity(v)
                        client.add_product(product_order)
                orders[name] = client
    except:
        print("Erreur lors du traitement du fichier {}".format(options.csv))
        raise

    if pdf_output:
        if options.clients:
            client_orders_pdf(options.output, orders)
            clients_summary_pdf(options.output, orders)
        if options.harvest:
            harvest_quantity_pdf(options.output, harvest_products)
        write_pdf_file()
    else:
        if options.clients:
            write_client_orders(options.output, orders)
        if options.harvest:
            write_harvest_quantity(options.output, harvest_products)


if __name__ == "__main__":
    exit(main())