import json
import logging
import os.path
import time
from typing import List
from urllib.parse import urljoin

import yaml
from threescale_api import ThreeScaleClient

from config import ProductConfig, Config, ApplicationConfig
from resources.account import Account
from resources.application import Application, ApplicationPlan, ApplicationOIDCConfiguration
from resources.backend import BackendUsage, Backend
from resources.metric import Metric
from resources.product import Product
from resources.proxy import ProxyMapping, Proxy, AuthenticationType

logger = logging.getLogger('sync')


def sync_mappings(client: ThreeScaleClient, product: Product, product_config: ProductConfig,
                  proxy_mappings: List[ProxyMapping]):
    # Combine active OpenAPI mappings with config mappings.
    active_mappings = [(m.http_method, m.pattern) for m in proxy_mappings]
    if product_config.mappings:
        active_mappings += [(m.method, m.pattern) for m in product_config.mappings]
    # Delete extra mappings
    for mapping in ProxyMapping.list(client, product.id):
        should_be_active = True
        for active_mapping in active_mappings:
            if active_mapping == (mapping.http_method, mapping.pattern):
                continue
            should_be_active = False
        if not should_be_active:
            mapping.delete(client, product.id)

    existing_mappings = ProxyMapping.list(client, product.id)
    hits_metric = Metric.fetch_hits_metric(client, product.id)
    # Sync mappings defined in OpenAPI spec.
    for mappingConfig in proxy_mappings:
        mappingConfig.metric_id = hits_metric.id  # set metric id on mapping (required)
        mappingConfig.pattern = product_config.api.publicBasePath + mappingConfig.pattern
        mappingConfig.create(client, product.id, existing_mappings=existing_mappings)
    # Sync mappings defined in config yaml.
    if product_config.mappings:
        for mappingConfig in product_config.mappings:
            proxy_mapping = ProxyMapping(
                metric_id=hits_metric.id,
                http_method=mappingConfig.method,
                pattern=mappingConfig.pattern,
                delta=1)
            proxy_mapping.create(client, product.id, existing_mappings=existing_mappings)

    # Fetch the final list of mappings from the server. Used for logging
    ProxyMapping.list(client, product.id)


def start_sync_for_one_config(client: ThreeScaleClient, config: Config, args):
    # Class variable needs to be set once per process when using a multiprocessing pool.
    Config.SSL_VERIFY = not args.ssl_disabled
    if args.delete:
        response = input("WARNING --- Deleting all products in the configuration. Are you sure? y/N: ")
        if response.upper() == 'Y':
            logger.warning(
                "Deleting {} products: {}".format(len(config.products), [p.name for p in config.products]))
            for config_product in config.products:
                system_name = config_product.shortName.replace('-', '_').replace(' ', '_')
                p = Product().fetch(client, system_name)
                if not p:
                    logger.error(
                        'Could not find product: {}, system_name={}'.format(config_product.name, system_name))
                    exit(1)
                p.delete(client)
    else:
        total_product_sync_start_time_ms = round(time.time() * 1000)
        sync_config(client, config,
                    open_api_basedir=args.openapi_basedir,
                    policies_basedir=args.policies_basedir)
        total_product_sync_end_time_ms = round(time.time() * 1000)
        logger.info("Syncing configuration '{}' took {}s."
                    .format(config.filename, (total_product_sync_end_time_ms - total_product_sync_start_time_ms) /
                            1000))


def sync_config(c: ThreeScaleClient, config: Config, open_api_basedir='.', policies_basedir='.'):
    # TODO: Create user if not exists
    accounts = Account().list(c)
    for product_config in config.products:
        sync_product(config, accounts, c, open_api_basedir, policies_basedir, product_config)


def sync_product(config, accounts, client, open_api_basedir, policies_basedir, product_config):
    environment = config.environment
    valid_methods = ['get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace']
    # Performance timers
    product_sync_start_time_ms = round(time.time() * 1000)
    product_name = product_config.name
    description = product_config.description
    version = product_config.version
    product_system_name = product_config.shortName.replace('-', '_').replace(' ', '_')
    # Parse OpenAPI spec for product.
    logger.info("Loading mapping paths from OpenAPI config.")
    openapi_specs = []
    if product_config.openAPIPath:
        if type(product_config.openAPIPath) is str:
            openapi = parse_openapi_file(open_api_basedir, product_config.openAPIPath)
            openapi_specs.append(openapi)
        else:
            for oas_file in product_config.openAPIPath:
                openapi = parse_openapi_file(open_api_basedir, oas_file)
                openapi_specs.append(openapi)
    proxy_mappings = []
    for openapi in openapi_specs:
        openapi_version: str = openapi['swagger'] if 'swagger' in openapi else openapi['openapi']
        api_base_path = '/'
        if openapi_version.startswith('2.') and 'basePath' in openapi:
            api_base_path = openapi['basePath']
        # TODO: OpenAPI 3.0 specifies basePath in the server object.
        if not api_base_path.endswith('/'):
            api_base_path += '/'

        for path in openapi['paths']:
            definition = openapi['paths'][path]
            for method in [m for m in definition if m in valid_methods]:
                logger.info("Found mapping in spec: {} {}".format(method, urljoin(api_base_path, path[1:])))
                proxy_mappings.append(
                    ProxyMapping(http_method=method.upper(), pattern=urljoin(api_base_path, path[1:]) + '$',
                                 delta=1))
    # Create product
    product = Product(name=product_name, description=description, system_name=product_system_name)
    existing_product = product.fetch(client, product_system_name)
    # Update product name and description if it has changed.
    if existing_product:
        has_product_metadata_changed = product.name != existing_product.name \
                                       or product.description != existing_product.description
        if has_product_metadata_changed:
            logger.info("Updating product name and description. Was name={}, desc={}, now name={}, desc={}"
                        .format(existing_product.name, existing_product.description,
                                product.name, product.description))
            existing_product.update(client, dict(name=product.name, description=product.description))
    product = product.create(client)
    sync_applications(client, description, environment, product, product_config, product_system_name, version,
                      accounts=accounts)
    # Configure authentication
    proxy = Proxy(service_id=product.id).fetch(client)
    _ = proxy.update(client, oidc_issuer_endpoint=product_config.api.issuerURL,
                     oidc_issuer_type=product_config.api.issuerType,
                     credentials_location=product_config.api.credentialsLocation,
                     authentication_type=AuthenticationType.from_string(product_config.api.authType),
                     sandbox_endpoint=product_config.stagingPublicURL,
                     endpoint=product_config.productionPublicURL)
    if product_config.api.oidcFlows:
        sync_oidc_flows(client, product, product_config)
    sync_policies(client, product, policies_basedir, product_config.policiesPath)
    sync_backends(client, environment, description, product, product_config)
    sync_mappings(client, product, product_config, proxy_mappings)
    # Promote configuration
    proxy = Proxy(service_id=product.id).fetch(client)
    proxy.promote(client)
    product_sync_end_time_ms = round(time.time() * 1000)
    logger.info("Syncing product took {}s. product={}"
                .format((product_sync_end_time_ms - product_sync_start_time_ms) / 1000, product.name))


def parse_openapi_file(basedir: str, filepath: str):
    with open(os.path.join(basedir, filepath), 'r') as oas:
        if filepath.endswith('.yml') or filepath.endswith('.yaml'):
            openapi = yaml.load(oas.read(), Loader=yaml.FullLoader)
        elif filepath.endswith('.json'):
            openapi = json.loads(oas.read())
        else:
            raise ValueError("Invalid file extension for OpenAPI spec, requires YAML or JSON. file={}".format(filepath))
    return openapi


def sync_applications(c: ThreeScaleClient, description: str, environment: str, product: Product,
                      product_config: ProductConfig, product_system_name: str, version: int,
                      accounts: List[Account] = None):
    # Delete extra applications
    active_applications = [a.name for a in product_config.applications]
    for application in Application.list(c):
        if application.service_id == product.id and application.name not in active_applications:
            application.delete(c)
    for application_config in product_config.applications:
        # Create the application user if it does not exist. User account synchronization is append-only.
        # Previously retrieved accounts can be passed in to prevent re-fetch.
        if accounts is None:
            account = Account().fetch(c, application_config.account)
        else:
            account_list = [a for a in accounts if a.username == application_config.account]
            account = account_list[0] if len(account_list) == 1 else None

        if not account:
            logger.info("Creating new account: {}".format(application_config.account))
            Account(username=application_config.account).create(c)

        user_id = fetch_user_id(c, application_config, accounts=accounts)

        # Generate names
        application_name = application_config.name \
            if application_config.name else f"{environment}_{product_system_name}_v{version}_Application"
        application_plan_name = f"{environment}_{product_system_name}_v{version}_AppPlan"
        # Create application plans
        application_plan = ApplicationPlan(name=application_plan_name)
        application_plan = application_plan.create(c, service_id=product.id)
        # Create application
        logger.info("Creating application: {}".format(application_name))
        application = Application(name=application_name, client_id=application_config.client_id,
                                  client_secret=application_config.client_secret,
                                  description=description, account_id=user_id, plan_id=application_plan.id)
        _ = application.create(c, delete_if_exists=True)


def fetch_user_id(c: ThreeScaleClient, application_config: ApplicationConfig, accounts=None):
    accounts_list = Account().list(c) if accounts is None else accounts
    # Verify user exists.
    users = [u.id for u in accounts_list if u.username == application_config.account]
    if not users:
        raise ValueError('User {} not found.'.format(application_config.account))
    user_id = users[0]
    return user_id


def sync_policies(c: ThreeScaleClient, product: Product, basedir: str, filepath: str):
    logger.info("Updating policies.")
    if filepath is None:
        product.update_policies(c, '[]')
        return

    with open(os.path.join(basedir, filepath), 'r') as policesFile:
        try:
            policies = json.loads(policesFile.read())
        except ValueError as e:
            logger.error("Decoding policies from {} has failed, please fix this".format(filepath))
            raise e

    product.update_policies(c, json.dumps(policies))


def sync_backends(c: ThreeScaleClient, environment: str, description: str, product: Product,
                  product_config: ProductConfig):
    backend_usages = BackendUsage(service_id=product.id).list(c)
    # Create backend
    for backend_config in product_config.backends:
        backend_name = f"{environment}_{backend_config.id}_backend"
        backend = Backend(name=backend_name, description=description,
                          private_endpoint=backend_config.privateBaseURL)
        try:
            backend = backend.create(c, ignore_if_exists=False)
        except ValueError:
            logger.info("Backend {} exists, updating.".format(backend_name))
            existing_backend = backend.fetch(c, backend.system_name)
            backend = existing_backend.update(c, **dict(name=backend.name, description=backend.description,
                                                        private_endpoint=backend.private_endpoint))
        # Update backend usages
        product.update_backends(c, backend_id=backend.id, path=backend_config.path, backend_usages=backend_usages)
        # backend.delete(c)


def sync_oidc_flows(c: ThreeScaleClient, product: Product, product_config: ProductConfig):
    oidc_config = ApplicationOIDCConfiguration.fetch(c, product.id)
    oidc_flows = product_config.api.oidcFlows
    oidc_config.direct_access_grants_enabled = \
        oidc_flows['directAccessGrants'] if 'directAccessGrants' in oidc_flows else False
    oidc_config.implicit_flow_enabled = oidc_flows['implicitFlow'] if 'implicitFlow' in oidc_flows else False
    oidc_config.service_accounts_enabled = oidc_flows['serviceAccounts'] if 'serviceAccounts' in oidc_flows else False
    oidc_config.standard_flow_enabled = oidc_flows['standardFlow'] if 'standardFlow' in oidc_flows else False
    oidc_config.update(c, product.id)
