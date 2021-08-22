from __future__ import annotations

import logging
from enum import Enum
from typing import Union, List
from xml.etree import ElementTree

import requests
from threescale_api import ThreeScaleClient


class AuthenticationType(Enum):
    APP_KEY = 1
    APP_ID_KEY = 2
    OAUTH = 'oauth'
    OIDC = 'oidc'

    @staticmethod
    def from_string(s: str) -> AuthenticationType:
        mapping = dict(
            app_key=AuthenticationType.APP_KEY,
            app_id_key=AuthenticationType.APP_ID_KEY,
            oauth=AuthenticationType.OAUTH,
            oidc=AuthenticationType.OIDC
        )
        if s not in mapping:
            raise KeyError('Invalid authentication type: {}'.format(s))
        return mapping.get(s)


class Proxy:
    logger = logging.getLogger('proxy')

    def __init__(
            self,
            service_id=None,
            endpoint=None,
            api_backend=None,
            credentials_location=None,
            auth_app_key=None,
            auth_app_id=None,
            auth_user_key=None,
            error_auth_failed=None,
            error_auth_missing=None,
            error_status_auth_failed=None,
            error_headers_auth_failed=None,
            error_status_auth_missing=None,
            error_headers_auth_missing=None,
            error_no_match=None,
            error_status_no_match=None,
            error_headers_no_match=None,
            error_limits_exceeded=None,
            error_status_limits_exceeded=None,
            error_headers_limits_exceeded=None,
            secret_token=None,
            hostname_rewrite=None,
            sandbox_endpoint=None,
            api_test_path=None,
            policies_config=None,
            created_at=None,
            updated_at=None,
            deployment_option=None,
            lock_version=None,
            oidc_issuer_endpoint=None,
            oidc_issuer_type=None,
            jwt_claim_with_client_id=None,
            jwt_claim_with_client_id_type=None):
        self.service_id = service_id
        self.endpoint = endpoint
        self.api_backend = api_backend
        self.credentials_location = credentials_location
        self.auth_app_key = auth_app_key
        self.auth_app_id = auth_app_id
        self.auth_user_key = auth_user_key
        self.error_auth_failed = error_auth_failed
        self.error_auth_missing = error_auth_missing
        self.error_status_auth_failed = error_status_auth_failed
        self.error_headers_auth_failed = error_headers_auth_failed
        self.error_status_auth_missing = error_status_auth_missing
        self.error_headers_auth_missing = error_headers_auth_missing
        self.error_no_match = error_no_match
        self.error_status_no_match = error_status_no_match
        self.error_headers_no_match = error_headers_no_match
        self.error_limits_exceeded = error_limits_exceeded
        self.error_status_limits_exceeded = error_status_limits_exceeded
        self.error_headers_limits_exceeded = error_headers_limits_exceeded
        self.secret_token = secret_token
        self.hostname_rewrite = hostname_rewrite
        self.sandbox_endpoint = sandbox_endpoint
        self.api_test_path = api_test_path
        self.policies_config = policies_config
        self.created_at = created_at
        self.updated_at = updated_at
        self.deployment_option = deployment_option
        self.lock_version = lock_version
        self.oidc_issuer_endpoint = oidc_issuer_endpoint
        self.oidc_issuer_type = oidc_issuer_type
        self.jwt_claim_with_client_id = jwt_claim_with_client_id
        self.jwt_claim_with_client_id_type = jwt_claim_with_client_id_type

    def fetch(self, client: ThreeScaleClient) -> Union[Proxy, None]:
        api_url = f"{client.admin_api_url}/services/{self.service_id}/proxy"
        proxy_response = requests.get(api_url, params={'access_token': client.token})
        proxy_xml = ElementTree.fromstring(proxy_response.text)
        kwargs = dict()
        for attrib in proxy_xml:
            kwargs[attrib.tag] = attrib.text
        return Proxy(**kwargs)

    def update(self, client: ThreeScaleClient, oidc_issuer_endpoint=None, oidc_issuer_type=None,
               credentials_location=None, auth_app_id=None, auth_app_key=None, auth_user_key=None,
               jwt_claim_with_client_id=None, jwt_claim_with_client_id_type=None,
               authentication_type: AuthenticationType = None, sandbox_endpoint=None, endpoint=None) -> Proxy:
        """
        Update configuration on a proxy (product). Note: this is different to proxy configuration.
        :param oidc_issuer_type: One of [keycloak | rest]
        :param credentials_location: One of [headers | query | authorization]
        :param authentication_type: Authentication type of the proxy.
        """
        api_url = f"{client.admin_api_url}/services/{self.service_id}/proxy.xml"
        # Set authentication type
        if authentication_type:
            self.logger.info("Updating authentication method.")
            service = client.services.fetch(self.service_id)
            if not service:
                raise ValueError('Could not find service id: {}'.format(self.service_id))
            client.services.update(self.service_id, dict(backend_version=authentication_type.value))
        self.logger.info("Updating proxy.")
        proxy_params = dict(
            oidc_issuer_endpoint=oidc_issuer_endpoint,
            oidc_issuer_type=oidc_issuer_type,
            credentials_location=credentials_location,
            auth_app_id=auth_app_id,
            auth_app_key=auth_app_key,
            auth_user_key=auth_user_key,
            jwt_claim_with_client_id=jwt_claim_with_client_id,
            jwt_claim_with_client_id_type=jwt_claim_with_client_id_type,
            sandbox_endpoint=sandbox_endpoint,
            endpoint=endpoint
        )
        self.logger.debug(proxy_params)
        proxy_response = requests.patch(api_url, params={'access_token': client.token}, data=proxy_params)
        self.logger.debug(proxy_response.text)
        if not proxy_response.ok:
            raise ValueError('Error updating proxy: code={}, error={}', proxy_response.status_code, proxy_response.text)
        return self.fetch(client)

    def fetch_latest_configuration(self, client: ThreeScaleClient, environment: str) -> dict:
        api_url = f"{client.admin_api_url}/services/{self.service_id}/proxy/configs/{environment}/latest.json"
        response = requests.get(api_url, params={'access_token': client.token})
        if not response.ok:
            raise ValueError(
                'Error fetching latest proxy version: service_id={}, environment={}, code={}, error={}'.format(
                    self.service_id, environment, response.status_code, response.text))
        # TODO: Create ProxyConfiguration class
        return response.json()

    def promote(self, client: ThreeScaleClient):
        """
        Promotes a APICast configuration for a product from staging to production.
        """
        # We need to perform a noop update in order to make the initial config go into staging. Otherwise there will be
        # no latest version to fetch.
        self.update(client, credentials_location=self.credentials_location)

        environment = 'production'
        latest = self.fetch_latest_configuration(client, 'sandbox')
        latest_version = latest['proxy_config']['version']
        api_url = f"{client.admin_api_url}/services/{self.service_id}/proxy/configs/staging/{latest_version}/promote.json"
        promote_args = dict(
            service_id=self.service_id,
            environment='sandbox',
            version=latest_version,
            to=environment
        )
        response = requests.post(api_url, params={'access_token': client.token}, data=promote_args)
        self.logger.debug(response.text)
        if not response.ok:
            if response.status_code == 422:
                self.logger.warning("Not promoting proxy configuration due to no updates. msg={}".format(response.text))
                return
            raise ValueError(
                'Error promoting proxy version: service_id={}, environment={}, version={}, code={}, error={}'.format(
                    self.service_id, environment, latest_version, response.status_code, response.text))


class ProxyMapping:
    logger = logging.getLogger('proxy_mapping')

    def __init__(
            self,
            id=None,
            metric_id=None,
            pattern=None,
            http_method=None,
            delta=None,
            position=None,
            last=None,
            created_at=None,
            updated_at=None,
            links=None):
        self.id = id
        self.metric_id = metric_id
        self.pattern = pattern
        self.http_method = http_method
        self.delta = delta
        self.position = position
        self.last = last
        self.created_at = created_at
        self.updated_at = updated_at
        self.links = links

    @staticmethod
    def list(client: ThreeScaleClient, service_id: int) -> List[ProxyMapping]:
        logger = logging.getLogger('proxy_mapping')
        api_url = f"{client.admin_api_url}/services/{service_id}/proxy/mapping_rules.json"
        response = requests.get(api_url, params={'access_token': client.token})
        logger.debug(response.text)
        mapping_rules_json = response.json()['mapping_rules']
        logger.info("Found {} proxy mappings.".format(len(mapping_rules_json)))
        return [ProxyMapping(**m['mapping_rule']) for m in mapping_rules_json]

    def fetch_existing(self, client: ThreeScaleClient, service_id: int,
                       http_method=None, pattern=None) -> Union[ProxyMapping, None]:
        mappings = self.list(client, service_id)
        for mapping in mappings:
            if mapping.http_method == http_method and mapping.pattern == pattern:
                return mapping
        return None

    def create(self, client: ThreeScaleClient, service_id: int,
               existing_mappings: List[ProxyMapping] = None) -> ProxyMapping:

        # Previously retrieved existing_mappings can be passed in to prevent re-fetching.
        if existing_mappings is None:
            existing_mapping = self.fetch_existing(client, service_id, http_method=self.http_method,
                                                   pattern=self.pattern)
        else:
            self.logger.debug("Using cached mapping list.")
            has_existing_mapping = len([m for m in existing_mappings
                                        if m.http_method == self.http_method and m.pattern == self.pattern]) > 0
            if has_existing_mapping:
                existing_mapping = self.fetch_existing(client, service_id, http_method=self.http_method,
                                                       pattern=self.pattern)
            else:
                existing_mapping = None

        if existing_mapping:
            self.logger.info(
                "Not creating existing mapping: {} {}".format(existing_mapping.http_method, existing_mapping.pattern))
            return existing_mapping

        api_url = f"{client.admin_api_url}/services/{service_id}/proxy/mapping_rules.json"
        mapping_params = dict(
            http_method=self.http_method,
            pattern=self.pattern,
            delta=self.delta,
            metric_id=self.metric_id,
        )
        response = requests.post(api_url, params={'access_token': client.token}, data=mapping_params)
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError('Error creating proxy mapping: service={}, args={}, code={}, error={}'
                             .format(service_id, mapping_params, response.status_code, response.text))
        mapping_rule_json = response.json()['mapping_rule']
        return ProxyMapping(**mapping_rule_json)

    def delete(self, client: ThreeScaleClient, service_id: int):
        api_url = f"{client.admin_api_url}/services/{service_id}/proxy/mapping_rules/{self.id}.json"
        response = requests.delete(api_url, params={'access_token': client.token})
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError('Error deleting proxy mapping: service={}, id={}, code={}, error={}'
                             .format(service_id, self.id, response.status_code, response.text))
