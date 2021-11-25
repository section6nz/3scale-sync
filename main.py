#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import time
from functools import reduce
from multiprocessing import Pool

import yaml
from threescale_api import ThreeScaleClient

from config import parse_config, Config, combine_configs
from sync import start_sync_for_one_config

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
    parser.add_argument('--config', dest='config', required=False, default=[], nargs='?', action='append',
                        help='Path to config file.')
    parser.add_argument('--config_dir', dest='config_dir', required=False, default=None,
                        help='Path to config directory.')
    parser.add_argument('--openapi_basedir', dest='openapi_basedir', required=False, default='.',
                        help='Directory root of OpenAPI specification files.')
    parser.add_argument('--policies_basedir', dest='policies_basedir', required=False, default='.',
                        help='Directory root of the policy configuration file.')
    parser.add_argument('--validation_basedir', dest='validation_basedir', required=False, default=None,
                        help='Directory root of config YAML files for validation.')
    parser.add_argument('--delete', dest='delete', required=False, default=False, help='Delete all products.',
                        action='store_true')
    parser.add_argument('--parallel', dest='parallel', required=False, default=1, type=int,
                        help='Parallel execution threads for product sync')
    parser.add_argument('--debug', dest='debug', required=False, default=False, help='Enable verbose logging.',
                        action='store_true')
    parser.add_argument('--no-ssl', dest='ssl_disabled', required=False, default=False,
                        help='Disable SSL verification.', action="store_true")
    args = parser.parse_args()
    Config.SSL_VERIFY = not args.ssl_disabled
    client = ThreeScaleClient(url=args.url, token=args.token, ssl_verify=Config.SSL_VERIFY)

    if not Config.SSL_VERIFY:
        logger.warning("SSL certificate verification disabled.")

    # Validation across all configuration files.
    if args.validation_basedir:
        configs_for_validation = []
        for file in os.listdir(args.validation_basedir):
            if file.endswith(".yml") or file.endswith(".yaml"):
                with open(os.path.join(args.validation_basedir, file), 'r') as f:
                    loaded_config = yaml.load(f.read(), Loader=yaml.FullLoader)
                    if not loaded_config:
                        raise ValueError('Invalid config for validation: {}'.format(file))
                    configs_for_validation.append(parse_config(loaded_config))

        # Combine configs.
        combined_config = reduce(combine_configs, configs_for_validation)
        combined_config.validate()

    # Find config files if config_dir is specified.
    if args.config_dir:
        for file in os.listdir(args.config_dir):
            if file.endswith(".yml") or file.endswith(".yaml"):
                args.config.append(os.path.join(args.validation_basedir, file))

    configs = []
    logger.info("Parsing configuration files: {}".format(args.config))
    for config_file in args.config:
        with open(config_file, 'r') as f:
            loaded_config = yaml.load(f.read(), Loader=yaml.FullLoader)
            if not loaded_config:
                raise ValueError('Invalid config: {}'.format(config_file))
            config = parse_config(loaded_config)
            config.validate()
            config.filename = config_file
            configs.append(config)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    with open(args.config, 'r') as f:
        loaded_config = yaml.load(f.read(), Loader=yaml.FullLoader)
        if not loaded_config:
            raise ValueError('Invalid config!')

    config = parse_config(loaded_config)
    config.validate()

    total_sync_start_time_ms = round(time.time() * 1000)
    if args.parallel > 1:
        arg_list = [(client, config, args) for config in configs]
        with Pool(args.parallel) as process_pool:
            process_pool.starmap(start_sync_for_one_config, arg_list)
    else:
        for config in configs:
            start_sync_for_one_config(client, config, args)

    total_sync_end_time_ms = round(time.time() * 1000)
    logger.info("Syncing {} configurations took {}s."
                .format(len(configs), (total_sync_end_time_ms - total_sync_start_time_ms) / 1000))
