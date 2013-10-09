#!/usr/bin/env python
import os
import csv
from datetime import datetime
from decimal import Decimal as D
import json
import unicodedata

import yaml

import requests

DATA_DIR = "data"
CONFIG_FILE = "product_ids.yaml"
URL_BASE = "http://lcboapi.com"
PRODUCT_SEGMENT = "products/%s"
STORE_SEGMENT = "stores/%s"
INVENTORY_SEGMENT = "inventory"
PRODUCT_ENDPOINT = "/".join([URL_BASE, PRODUCT_SEGMENT])
INVENTORY_ENDPOINT = "/".join([URL_BASE, STORE_SEGMENT, PRODUCT_SEGMENT, INVENTORY_SEGMENT])
NOW = datetime.now().strftime("%s")


def get_clean_product_name(product):
    """ Clean accents from product names, because CSV writer can't deal with them """
    return unicodedata.normalize(
        'NFKD',
        unicode(product.get('name', 'Not Found'))
    ).encode('ascii', 'ignore')


def get_quantity_at_store(store_id, product_id):
    url = INVENTORY_ENDPOINT % (store_id, product_id)
    response = requests.get(url)
    if response.status_code == 200:
        json_response = json.loads(response.content)
        store_product_info = json_response.get('result')
        return store_product_info.get('quantity')
    else:
        print '%s didn\'t return anything useful! You should probably check the IDs' % url
        return 0


def main():
    with open(CONFIG_FILE, 'r') as config_file:
        config = yaml.load(config_file)
        keep_backups = config.get('keep_backups', True)
        destination = os.path.join(DATA_DIR, config.get('destination', 'prices.csv'))
        csv_separator = str(config.get('csv_separator', ',')).strip()[0]
        csv_quote = config.get('csv_quote', '|')
        product_ids = config.get('product_ids', [])
        store_ids = config.get('store_ids', [])

    catalog = dict.fromkeys(product_ids, {})

    for product_id in product_ids:
        url = PRODUCT_ENDPOINT % product_id
        response = requests.get(url)
        if response.status_code == 200:
            json_response = json.loads(response.content)
            product = json_response.get('result')
            for store_id in store_ids:
                product['q%s' % store_id] = get_quantity_at_store(store_id, product_id)
            catalog[product_id] = product
        else:
            print '%s didn\'t return anything useful! You should probably check the IDs' % url

    if keep_backups and os.path.exists(destination):
        backup = os.path.join(DATA_DIR, "prices_backup_%s.csv" % NOW)
        os.rename(destination, backup)

    with open(destination, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=csv_separator, quotechar=csv_quote,
                            quoting=csv.QUOTE_NONNUMERIC)
        # This is the column name row in the CSV, the writerow in the loop should
        # match the order below.
        columns = [
            'ProductID',
            'ProductName',
            'Price',
            'RegularPrice',
            'PackageVolume',
            'PricePerLitre'
        ]
        columns += ['QuantityAt%s' % store_id for store_id in store_ids]
        writer.writerow(columns)
        for product_id in product_ids:
            product = catalog.get(product_id)
            product_name = get_clean_product_name(product)
            row = [
                product_id,
                product_name,
                D(product.get('price_in_cents', 0)) / D(100),
                D(product.get('regular_price_in_cents', 0)) / D(100),
                D(product.get('package_unit_volume_in_milliliters', 0)),
                D(product.get('price_per_liter_in_cents', 0)) / D(100),
            ]
            row += [product.get('q%s' % store_id, 0) for store_id in store_ids]
            writer.writerow(row)


if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)
    try:
        main()
        print "New data available!"
    except Exception, err:
        print "An error occurred. %s" % err
