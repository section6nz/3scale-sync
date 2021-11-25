import collections
import logging
import re
from typing import List, Union

import urllib3.util


class APIConfig:
    def __init__(self, publicBasePath: str, authType: str, issuerURL: str, issuerType: str, credentialsLocation: str,
                 oidcFlows: dict):
        self.publicBasePath = publicBasePath
        self.authType = authType
        self.issuerURL = issuerURL
        self.issuerType = issuerType
        self.credentialsLocation = credentialsLocation
        self.oidcFlows = oidcFlows


class PolicyConfig:
    def __init__(self, name: str, configuration: str, version: str, enabled: bool):
        self.name = name
        self.configuration = configuration
        self.version = version
        self.enabled = enabled


class BackendConfig:
    def __init__(self, id: str, privateBaseURL: str, path: str):
        self.id = id
        self.privateBaseURL = privateBaseURL
        self.path = path


class ApplicationConfig:
    def __init__(self, account: str, name: str = None, client_id: str = None, client_secret: str = None):
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.account = account


class MappingConfig:
    def __init__(self, method, pattern):
        self.method = method
        self.pattern = pattern


class ProductConfig:
    def __init__(self, name: str, shortName: str, description: str, openAPIPath: Union[str, List[str]], version: int,
                 api: APIConfig,
                 policiesPath: str,
                 backends: List[BackendConfig], applications: List[ApplicationConfig], stagingPublicURL=None,
                 productionPublicURL=None, mappings: List[MappingConfig] = None):
        self.name = name
        self.shortName = shortName
        self.description = description
        self.openAPIPath = openAPIPath
        self.policiesPath = policiesPath
        self.version = version
        self.api = api
        self.backends = backends
        self.applications = applications
        self.stagingPublicURL = stagingPublicURL
        self.productionPublicURL = productionPublicURL
        self.mappings = mappings


class Config:
    logger = logging.getLogger(__name__)

    def __init__(self, environment, products: List[ProductConfig]):
        self.environment = environment
        self.products = products

    def validate(self):
        self.logger.info("Validating sync configuration.")

        err_reason = "This will lead to system name conflicts. Please resolve this before continuing."
        # Ensure product system names are unique.
        system_names = [p.shortName for p in self.products]
        if len(system_names) > 1 and len(system_names) != len(set(system_names)):
            duplicates = [x for x, n in collections.Counter(system_names).items() if n > 1]
            self.logger.error("Duplicated: {}".format(duplicates))
            raise AssertionError("ABORT: Product short names are not unique. " + err_reason)

        backend_names = []
        application_names = []
        for product in self.products:
            backend_names.extend([b.id for b in product.backends])
            application_names.extend([a.name for a in product.applications])

        # Ensure backend names are unique.
        if len(backend_names) > 1 and len(backend_names) != len(set(backend_names)):
            duplicates = [x for x, n in collections.Counter(backend_names).items() if n > 1]
            self.logger.error("Duplicated: {}".format(duplicates))
            raise AssertionError("ABORT: Backend ids are not unique. " + err_reason)

        # Ensure application names are unique.
        if len(application_names) > 1 and len(application_names) != len(set(application_names)):
            duplicates = [x for x, n in collections.Counter(application_names).items() if n > 1]
            self.logger.error("Duplicated: {}".format(duplicates))
            raise AssertionError("ABORT: Application names are not unique. " + err_reason)

        # Ensure backend paths are not duplicated.
        for product in self.products:
            paths = [b.path for b in product.backends]
            if len(paths) > 1 and len(paths) != len(set(paths)):
                duplicates = [x for x, n in collections.Counter(paths).items() if n > 1]
                self.logger.error("Duplicated: {}".format(duplicates))
                raise AssertionError("ABORT: Backend paths are not unique. "
                                     "Please resolve before continuing. product={}".format(product.name))

        # Ensure backend hostnames are valid.
        for product in self.products:
            for backend in product.backends:
                # Validate privateBaseURL hostname.
                url = urllib3.util.parse_url(backend.privateBaseURL)
                hostname = url.netloc.split(':')[0]
                if not self._is_fqdn(hostname):
                    raise AssertionError(
                        "ABORT: Backend privateBaseURL does not contain a valid hostname. hostname={}", hostname)

    # Validate hostname
    @staticmethod
    def _is_fqdn(hostname):
        return re.match("^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9]["
                        "A-Za-z0-9\-]*[A-Za-z0-9])$", hostname)


def _parse_applications(product_config: dict) -> List[ApplicationConfig]:
    if 'applications' in product_config:
        if product_config['applications']:
            return [ApplicationConfig(**a) for a in product_config['applications']]
    return []


def _parse_backends(product_config: dict) -> List[BackendConfig]:
    if 'backends' in product_config:
        if product_config['backends']:
            return [BackendConfig(**b) for b in product_config['backends']]
    return []


def parse_config(c: dict) -> Config:
    products = []
    for product in c['products']:
        staging_public_url = product['stagingPublicURL'] if 'stagingPublicURL' in product else ''
        p = ProductConfig(
            name=product['name'],
            shortName=product['shortName'],
            description=product['description'],
            openAPIPath=product['openAPIPath'] if 'openAPIPath' in product else None,
            policiesPath=product['policiesPath'] if 'policiesPath' in product else None,
            version=product['version'],
            stagingPublicURL=staging_public_url,
            productionPublicURL=product[
                'productionPublicURL'] if 'productionPublicURL' in product else staging_public_url,
            api=APIConfig(publicBasePath=product['api']['publicBasePath'],
                          authType=product['api']['authentication']['authType'],
                          issuerURL=product['api']['authentication']['issuerURL'] if 'issuerURL' in product['api'][
                              'authentication'] else None,
                          issuerType=product['api']['authentication']['issuerType'] if 'issuerType' in product['api'][
                              'authentication'] else None,
                          credentialsLocation=product['api']['authentication']['credentialsLocation'],
                          oidcFlows=product['api']['authentication']['oidcFlows']
                          if 'oidcFlows' in product['api']['authentication'] else None),
            backends=_parse_backends(product),
            applications=_parse_applications(product),
            mappings=[MappingConfig(**m) for m in product['mappings']] if 'mappings' in product else []
        )
        products.append(p)
    return Config(c['environment'], products)
