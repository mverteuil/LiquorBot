#!/usr/bin/env python
import os
import csv
from datetime import datetime
import json

import yaml

import requests

DATA_DIR = "data"
CONFIG_FILE = "product_ids.yaml"
URL_BASE = "http://lcboapi.com"
PRODUCT_ENDPOINT = "/".join([URL_BASE, "products/%s"])
NOW = datetime.now().strftime("%s")


def main():
    with open(CONFIG_FILE, 'r') as config_file:
        config = yaml.load(config_file)
        keep_backups = config.get('keep_backups', True)
        destination = os.path.join(DATA_DIR, config.get('destination', 'prices.csv'))
        csv_separator = str(config.get('csv_separator', ',')).strip()[0]
        csv_quote = config.get('csv_quote', '|')
        product_ids = config.get('product_ids', [])

    catalog = dict.fromkeys(product_ids, {})

    for product_id in product_ids:
        url = PRODUCT_ENDPOINT % product_id
        response = requests.get(url)
        if response.status_code == 200:
            response = json.loads(response.content)
            catalog[product_id] = response.get('result')

    if keep_backups and os.path.exists(destination):
        backup = os.path.join(DATA_DIR, "prices_backup_%s.csv" % NOW)
        os.rename(destination, backup)

    with open(destination, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=csv_separator, quotechar=csv_quote,
                            quoting=csv.QUOTE_NONNUMERIC)
        # This is the column name row in the CSV, the writerow in the loop should
        # match the order below.
        writer.writerow([
            'ProductID',
            'ProductName',
            'Price',
            'RegularPrice',
            'PackageVolume',
            'PricePerLitre'
        ])
        for product_id, product in catalog.items():
            writer.writerow([
                product_id,
                product.get('name', 'Not Found'),
                product.get('price_in_cents', 0) / 100,
                product.get('regular_price_in_cents', 0) / 100,
                product.get('package_unit_volume_in_milliliters', 0),
                product.get('price_per_liter_in_cents', 0) / 100,
            ])


if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)
    main()
