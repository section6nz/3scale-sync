3scale Sync
===

Define your API in an OpenAPI specification. Define your 3scale configuration in a YAML file. Sync it to 3scale. Allows
you to manage in 3scale configuration as code.

## Configuration

An example configuration template is provided in config.yaml. General rules:

- Product names and short names should be unique.
- Application names and client IDs should be unique.
- Backend IDs should be unique.

## Mappings
API path mapping are defined in a separate OpenAPI specification file. The path to this file is referenced in the 
configuration file, using the `openAPIPath` key. Additional mapping patterns can be specified using the `mappings` 
key, this can be useful if advanced patterns are required (for example, inexact matching).

### Reference

```yaml
environment: dev # Name of environment this file refers to.
products:
  - name: Example API Display Name   # Product display name.
    shortName: example-api-display-name     # Short name. This will be used as the system name.
    description: Example API for automation # Description
    openAPIPath: openapi.yml  # Path to OpenAPI definition.
    version: 1  # Version of this product.
    stagingPublicURL: https://staging-url.com # Staging Public Base URL (optional)
    productionPublicURL: https://production-url.com # Production Public Base URL (optional)
    api:
      publicBasePath: /example/v1 # Base API path prefix for this product in the tenant.
      authentication:
        authType: oidc # One of [app_key | app_id_key | oauth | oidc].
        issuerURL: https://oidc-issuer.example.com # OIDC issuer URL.
        issuerType: keycloak  # OIDC issuer type.
        credentialsLocation: authorization # One of [headers | query | authorization].
        oidcFlows: # Enabled oidcFlows (optional).
          directAccessGrants: false
          implicitFlow: false
          serviceAccounts: true
          standardFlow: false
    mappings: # Additional patterns not specified in OpenAPI spec (optional)
      - method: GET
        pattern: /api/test/1
      - method: POST
        pattern: /api/test/2$
    backends:
      - id: example_api_backend_name  # Backend system name.
        privateBaseURL: http://backend-service:8080 # Backend URL.
        path: / # Backend API prefix.
    applications:
      - name: example_api_consumer_1  # Application system name.
        client_id: consumer_1 # Client ID used in authentication.
        client_secret: consumer_1_token # Client secret used in authentication.
        account: anonymous  # 3scale account that this application should be created under.
```

## Usage

```bash
main.py --3scale_url=${TENANT_URL} --access_token=${TOKEN} [--config=config.yml]
```
