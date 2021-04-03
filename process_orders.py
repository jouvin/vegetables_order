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

COMMENT_FIELD = "Commentaire"
DELIVERY_DAY_FIELD = "Livraison"
EMAIL_FIELD = 'E-mail'
NAME_FIELD = 'NOM - PRENOM'

DELIVERY_DAY_NO_PREFERENCE_VAL = "Peu importe"
DELIVERY_DAY_NO_PREFERENCE_STR = "Indifférent"

PRODUCT_PRICE_PATTERN = re.compile(r'\s*(?P<product>.+)\s*-\s*(?P<price>[0-9,]+)€\s*/\s*(?P<unit>\w+)\s*')

# Parameters related to PDF generation
PAGE_HEIGHT=defaultPageSize[1]
PAGE_WIDTH=defaultPageSize[0]
PAGE_MAX_PRODUCT_LINES = 35

# Singleton decorator definition
def singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class GlobalParams:
    def __init__(self):
        self.delivery_day = False
        self.verbose = False

@singleton
class PDFParams:
    def __init__(self):
        self.doc = None
        self.story = None
        self.email_style = None
        self.normal_style = None
        self.page_lines = 0
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
        return round(self.ordered_quantity,2)

    def get_price(self):
        return self.price

    def get_price_unit(self):
        return self.price_unit

    def increase_quantity(self, quantity):
        self.ordered_quantity += quantity


class ProductOrder():
    def __init__(self, name):
        self.name = name
        self.erroneous_quantity = None
        self.quantity = 0
        self.quantity_unit = None
        self.price = 0

    def get_name(self):
        return self.name

    def get_erroneous_quantity(self):
        return self.erroneous_quantity

    def get_quantity(self):
        return self.quantity

    def get_quantity_unit(self):
        return self.quantity_unit

    def set_quantity(self, quantity, product_params):
        self.quantity_unit = product_params.get_price_unit()
        # Sometimes clients mix grammes and kilos... attempt to detect it and fix it
        self.quantity = float(re.sub(',', '.', quantity))
        if self.quantity_unit == 'kg' and self.quantity >= 100:
            self.erroneous_quantity = self.quantity
            self.quantity = self.quantity / 1000.
        self.price = product_params.get_price() * self.quantity
        # Return the validated quantity
        return self.quantity

    def total_price(self):
        return self.price


class Client():
    def __init__(self):
        self.comment = None
        self.day = None
        self.email = None
        self.products = []
        self.total_price = None

    def add_product(self, product):
        self.products.append(product)

    def get_comment(self):
        return self.comment

    def get_day(self):
        return self.day

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

    def set_comment(self, comment):
        self.comment = comment

    def set_day(self, delivery_day):
        if len(delivery_day) == 0 or delivery_day == DELIVERY_DAY_NO_PREFERENCE_VAL:
            delivery_day = DELIVERY_DAY_NO_PREFERENCE_STR
        self.day = delivery_day

    def set_email(self, email):
        self.email = email


def debug(msg):
    global_params = GlobalParams()
    if global_params.logger:
        global_params.logger.debug(u'{}'.format(msg))
    elif global_params.verbose:
        print (msg)


def info(msg):
    global_params = GlobalParams()
    if global_params.logger:
        global_params.logger.info(u'{}'.format(msg))
    else:
        print (msg)


def exception_handler(exception_type, exception, traceback, debug_hook=sys.excepthook):
    global_params = GlobalParams()
    if global_params.verbose:
        debug_hook(exception_type, exception, traceback)
    else:
        print ("{}: {} (use --verbose for details)".format(exception_type.__name__, exception))


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

    for client_name,client in sorted(orders.items()):
        client_email = client.get_email()

        if client_email is None:
            client_email = "email non spécifié"

        suspect_quantities = []
        print('-----------------------------------------------------------', file=file_params.file)
        print("Commande pour {} ({})".format(client_name, client_email), file=file_params.file)
        for product in client.get_products():
            print('{}: {} {}\t({:.2f}€)'.format(product.get_name(),
                                                product.get_quantity(),
                                                product.get_quantity_unit(),
                                                product.total_price()), file=file_params.file)
            if product.get_erroneous_quantity() is not None:
                suspect_quantities.append((product))

        if client.get_comment():
            print("\nCommentaire de {} :".format(client_name), file=file_params.file)
            print(client.get_comment(), file=file_params.file)

        if len(suspect_quantities) > 0:
            print("\nQuantité suspecte corrigée pour les produits suivants :", file=file_params.file)
            for product in suspect_quantities:
                print("{} : {} {} au lieu de {} {}".format(product.get_name(),
                                                           product.get_quantity(), product.get_quantity_unit(),
                                                           product.get_erroneous_quantity(), product.get_quantity_unit()), file=file_params.file)

        print("\nPrix total = {:.2f}€".format(client.get_total_price()), file=file_params.file)
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
    global_params = GlobalParams()

    if pdf_params.doc is None:
        PDFInit(filename)
    else:
        pdf_params.story.append(PageBreak())

    first_client = True
    for client_name,client in sorted(orders.items()):
        client_email = client.get_email()
        if client_email is None:
            client_email = "non spécifié"

        # Decide if the client can fit on the current page. It is very empirical...
        # With the used character size, approximately 35 product lines can fit on one page.
        # Space used by header + total lines and the potential spacer is estimated in number of
        # product lines.
        if first_client:
            spacer_lines = 0
        else:
            spacer_lines = 3
        header_total_lines = 4
        cmd_lines = len(client.get_products()) + spacer_lines + header_total_lines
        if pdf_params.page_lines + cmd_lines > PAGE_MAX_PRODUCT_LINES:
            pdf_params.page_lines = 0
            pdf_params.story.append(PageBreak())
        elif not first_client:
            pdf_params.story.append(Spacer(1, 1 * inch))
        first_client = False
        pdf_params.page_lines += cmd_lines

        pdf_params.story.append(Paragraph("Commande de {}".format(client_name), pdf_params.title_style))
        pdf_params.story.append(Paragraph("Email : {}".format(client_email), pdf_params.email_style))
        if global_params.delivery_day:
            pdf_params.story.append(Paragraph("Jour de livraison : {}".format(client.get_day()), pdf_params.email_style))
        pdf_params.story.append(Spacer(1, 0.2 * inch))

        suspect_quantities = []
        product_table = [[[Paragraph("Produit", style=pdf_params.table_title_style)],
                          [Paragraph("Quantité", style=pdf_params.table_title_style)],
                          [Paragraph("Prix", style=pdf_params.table_title_style)]]]
        for product in client.get_products():
            product_table.append([product.get_name(),
                                  '{} {}'.format(product.get_quantity(), product.get_quantity_unit()),
                                  '{:.2f}€'.format(product.total_price())])
            if product.get_erroneous_quantity() is not None:
                suspect_quantities.append((product))
        pdf_params.story.append(Table(product_table, style=pdf_params.table_style))

        total_line = "\nPrix total pour {} = {:.2f}€".format(client_name, client.get_total_price())
        pdf_params.story.append(Spacer(1, 0.2 * inch))
        pdf_params.story.append(Paragraph(total_line, pdf_params.total_style))

        if client.get_comment():
            pdf_params.story.append(Spacer(1, 0.2 * inch))
            pdf_params.story.append(Paragraph("\nCommentaire de {} :".format(client_name), pdf_params.total_style))
            pdf_params.story.append(Spacer(1, 0.1 * inch))
            pdf_params.story.append(Paragraph(client.get_comment(), pdf_params.normal_style))

        if len(suspect_quantities) > 0:
            pdf_params.story.append(Spacer(1, 0.2 * inch))
            pdf_params.story.append(Paragraph("\nQuantité suspecte pour les produits suivants :", pdf_params.total_style))
            pdf_params.story.append(Spacer(1, 0.1 * inch))
            product_table = [[[Paragraph("Produit", style=pdf_params.table_title_style)],
                              [Paragraph("Quantité demandée", style=pdf_params.table_title_style)],
                              [Paragraph("Quantité corrigée", style=pdf_params.table_title_style)]]]
            for product in suspect_quantities:
                product_table.append([product.get_name(),
                                      '{} {}'.format(product.get_erroneous_quantity(), product.get_quantity_unit()),
                                      '{} {}'.format(product.get_quantity(), product.get_quantity_unit())])
            pdf_params.story.append(Table(product_table, style=pdf_params.table_style))
            # Update the number of lines used to ensure it is taken into account for the next client
            # It doesn't prevent the suspect product information to be split on next page
            pdf_params.page_lines += len(suspect_quantities) + 1


def harvest_quantity_pdf(filename, harvest_products, delivery_day):
    pdf_params = PDFParams()
    global_params = GlobalParams()

    if pdf_params.doc is None:
        PDFInit(filename)
    else:
        pdf_params.story.append(PageBreak())

    page_title = "Produits à récolter"
    if global_params.delivery_day:
        if delivery_day == DELIVERY_DAY_NO_PREFERENCE_STR:
            page_title += ' - jour de livraison indifférent'
        else:
            page_title += ' pour le {}'.format(delivery_day)
    pdf_params.story.append(Paragraph(page_title, pdf_params.title_style))

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
            product_table.append([product_name])
        pdf_params.story.append(Table(product_table, style=pdf_params.table_style))


# Must no be called before client_orders_pdf() or the price will be wrong
def clients_summary_pdf(filename, orders, delivery_day):
    pdf_params = PDFParams()
    global_params = GlobalParams()

    if pdf_params.doc is None:
        PDFInit(filename)
    else:
        pdf_params.story.append(PageBreak())

    page_title = "Somme Dûe par Client"
    if global_params.delivery_day:
        if delivery_day == DELIVERY_DAY_NO_PREFERENCE_STR:
            page_title += ' - jour de livraison indifférent'
        else:
            page_title += ' - {}'.format(delivery_day)
    pdf_params.story.append(Paragraph(page_title, pdf_params.title_style))

    total_price = 0
    clients_table = [[[Paragraph("Nom", style=pdf_params.table_title_style)],
                      [Paragraph("Somme Dûe", style=pdf_params.table_title_style)]]]
    for client_name,client in sorted(orders.items()):
        clients_table.append([client_name,
                              '{:.2f}€'.format(client.get_total_price())])
        total_price += client.get_total_price()
    pdf_params.story.append(Table(clients_table, style=pdf_params.table_style))

    total_line = "\nMontant total des commandes = {:.2f}€".format(total_price)
    pdf_params.story.append(Spacer(1, 0.2 * inch))
    pdf_params.story.append(Paragraph(total_line, pdf_params.total_style))


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
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help="Messages pour le diagnostic de problèmes")
    parser.add_argument('csv', help='Fichier des commandes Framaform')
    options = parser.parse_args()

    global_params = GlobalParams()
    global_params.verbose = options.verbose

    if options.format == 'pdf':
        pdf_output = True
    else:
        pdf_output = False

    # orders and harvest_products are dict of dict
    #   - First dict key is the delivery day (or '' if the delivery day is not part of the CSV)
    #   - Second dict key is the client name
    orders = dict()
    harvest_products = dict()
    client_list = set()

    try:
        with open(options.csv, 'r', encoding='utf-8') as csvfile:
            rows = csv.DictReader(csvfile, delimiter=';')
            while NAME_FIELD not in rows.fieldnames:
                rows = csv.DictReader(csvfile, delimiter=';')
            if DELIVERY_DAY_FIELD in rows.fieldnames:
                global_params.delivery_day = True
            for row in rows:
                name = None
                client = Client()
                for k,v in row.items():
                    if name is None:
                        if k == NAME_FIELD:
                            if v == '':
                                raise Exception('Entrée invalide: le nom est vide')
                            name = v.capitalize()
                            if name in client_list:
                                i = 1
                                while True:
                                    i += 1
                                    new_name = f'{name} ({i})'
                                    if new_name not in client_list:
                                        break
                                print(f'Commande déjà existante pour {name}: nouvelle commande au nom de {new_name}')
                                name = new_name
                            client_list.add(name)
                        continue
                    elif k == EMAIL_FIELD:
                        if v != "":
                            client.set_email(v)
                        continue
                    elif k == COMMENT_FIELD:
                        if v != "":
                            client.set_comment(v)
                        continue
                    elif k == DELIVERY_DAY_FIELD:
                        client.set_day(v)
                        continue

                    if global_params.delivery_day:
                        day_key = client.get_day()
                    else:
                        day_key = ''

                    # If the field is a product, create an entry in the product list to keep the original order of products
                    m = PRODUCT_PRICE_PATTERN.match(k)
                    if m:
                        product_name = m.group('product')
                        product_order = ProductOrder(product_name)
                    else:
                        raise Exception('Format produit invalide ({})'.format(k))

                    if day_key not in harvest_products:
                        harvest_products[day_key] = {}
                    if product_name not in harvest_products[day_key]:
                        harvest_products[day_key][product_name] = Product(m.group('price'), m.group('unit'))
                    if v != '':
                        validated_quantity = product_order.set_quantity(v, harvest_products[day_key][product_name])
                        harvest_products[day_key][product_name].increase_quantity(validated_quantity)
                        client.add_product(product_order)
                if day_key not in orders:
                    orders[day_key] = {}
                orders[day_key][name] = client
    except:
        print("Erreur lors du traitement du fichier {}".format(options.csv))
        raise

    if pdf_output:
        if options.clients:
            for delivery_day in orders:
                client_orders_pdf(options.output, orders[delivery_day])
                clients_summary_pdf(options.output, orders[delivery_day], delivery_day)
        if options.harvest:
            for delivery_day in orders:
                harvest_quantity_pdf(options.output, harvest_products[delivery_day], delivery_day)
        write_pdf_file()
    else:
        if options.clients:
            for delivery_day in orders:
                write_client_orders(options.output, orders[delivery_day])
        if options.harvest:
            for delivery_day in orders:
                write_harvest_quantity(options.output, harvest_products[delivery_day])


if __name__ == "__main__":
    sys.excepthook = exception_handler
    exit(main())