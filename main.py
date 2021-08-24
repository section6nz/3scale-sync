#!/usr/bin/env python3
import argparse
import logging
import sys
import time

import yaml
from threescale_api import ThreeScaleClient

from config import parse_config
from resources.product import Product
from sync import sync

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sync a 3scale API with OpenAPI mappings.')
    parser.add_argument('--3scale_url', dest='url', required=True, help='URL to the 3scale tenant admin.')
    parser.add_argument('--access_token', dest='token', required=True, help='Access token for the 3scale API.')
    parser.add_argument('--config', dest='config', required=False, default='config.yml', help='Path to config file.')
    parser.add_argument('--openapi_basedir', dest='openapi_basedir', required=False, default='.',
                        help='Directory root of OpenAPI specification files.')
    parser.add_argument('--delete', dest='delete', required=False, default=False, help='Delete all products.',
                        action='store_true')
    parser.add_argument('--parallel', dest='parallel', required=False, default=1, type=int,
                        help='Parallel execution threads for product sync')
    args = parser.parse_args()
    client = ThreeScaleClient(url=args.url, token=args.token, ssl_verify=True)

    with open(args.config, 'r') as f:
        loaded_config = yaml.load(f.read(), Loader=yaml.FullLoader)
        if not loaded_config:
            raise ValueError('Invalid config!')

    config = parse_config(loaded_config)
    config.validate()

    if args.delete:
        response = input("WARNING --- Deleting all products in the configuration. Are you sure? y/N: ")
        if response.upper() == 'Y':
            logger.warning("Deleting {} products: {}".format(len(config.products), [p.name for p in config.products]))
            for config_product in config.products:
                system_name = config_product.shortName.replace('-', '_').replace(' ', '_')
                p = Product().fetch(client, system_name)
                if not p:
                    logger.error('Could not find product: {}, system_name={}'.format(config_product.name, system_name))
                    exit(1)
                p.delete(client)
    else:
        total_product_sync_start_time_ms = round(time.time() * 1000)
        sync(client, config, open_api_basedir=args.openapi_basedir, parallel=args.parallel)
        total_product_sync_end_time_ms = round(time.time() * 1000)
        logger.info("Syncing configuration took {}s."
                    .format((total_product_sync_end_time_ms - total_product_sync_start_time_ms) / 1000))
