from typing import List


class APIConfig:
    def __init__(self, publicBasePath: str, authType: str, issuerURL: str, issuerType: str, credentialsLocation: str,
                 oidcFlows: dict):
        self.publicBasePath = publicBasePath
        self.authType = authType
        self.issuerURL = issuerURL
        self.issuerType = issuerType
        self.issuerType = issuerType
        self.credentialsLocation = credentialsLocation
        self.oidcFlows = oidcFlows


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
    def __init__(self, name: str, shortName: str, description: str, openAPIPath: str, version: int, api: APIConfig,
                 backends: List[BackendConfig], applications: List[ApplicationConfig]):
        self.name = name
        self.shortName = shortName
        self.description = description
        self.openAPIPath = openAPIPath
        self.version = version
        self.api = api
        self.backends = backends
        self.applications = applications


class Config:
    def __init__(self, environment, products: List[ProductConfig]):
        self.environment = environment
        self.products = products


def parse_config(c: dict) -> Config:
    products = []
    for product in c['products']:
        p = ProductConfig(
            name=product['name'],
            shortName=product['shortName'],
            description=product['description'],
            openAPIPath=product['openAPIPath'],
            version=product['version'],
            api=APIConfig(publicBasePath=product['api']['publicBasePath'],
                          authType=product['api']['authentication']['authType'],
                          issuerURL=product['api']['authentication']['issuerURL'],
                          issuerType=product['api']['authentication']['issuerType'],
                          credentialsLocation=product['api']['authentication']['credentialsLocation'],
                          oidcFlows=product['api']['authentication']['oidcFlows']
                          if 'oidcFlows' in product['api']['authentication'] else None),
            backends=[BackendConfig(**b) for b in product['backends']],
            applications=[ApplicationConfig(**a) for a in product['applications']]
        )
        products.append(p)
    return Config(c['environment'], products)