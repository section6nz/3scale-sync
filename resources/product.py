from __future__ import annotations

import logging
from typing import Union

import requests
from threescale_api import ThreeScaleClient

from resources.backend import Backend, BackendUsage
from resources.resource import Resource


class Product(Resource):
    logger = logging.getLogger('product')

    def __init__(
            self,
            id=None,
            name=None,
            state=None,
            system_name=None,
            backend_version=None,
            deployment_option=None,
            support_email=None,
            description=None,
            intentions_required=None,
            buyers_manage_apps=None,
            buyers_manage_keys=None,
            referrer_filters_required=None,
            custom_keys_enabled=None,
            buyer_key_regenerate_enabled=None,
            mandatory_app_key=None,
            buyer_can_select_plan=None,
            buyer_plan_change_permission=None,
            created_at=None,
            updated_at=None,
            **kwargs):
        self.id = id
        self.name = name
        self.state = state
        self.system_name = system_name if system_name else name.replace('-', '_').replace(' ', '_')
        self.backend_version = backend_version
        self.deployment_option = deployment_option
        self.support_email = support_email
        self.description = description
        self.intentions_required = intentions_required
        self.buyers_manage_apps = buyers_manage_apps
        self.buyers_manage_keys = buyers_manage_keys
        self.referrer_filters_required = referrer_filters_required
        self.custom_keys_enabled = custom_keys_enabled
        self.buyer_key_regenerate_enabled = buyer_key_regenerate_enabled
        self.mandatory_app_key = mandatory_app_key
        self.buyer_can_select_plan = buyer_can_select_plan
        self.buyer_plan_change_permission = buyer_plan_change_permission
        self.created_at = created_at
        self.updated_at = updated_at
        self.kwargs = kwargs

    def fetch(self, client: ThreeScaleClient, system_name: str) -> Union[Product, None]:
        for service in client.services.list():
            if service.entity['system_name'] == system_name:
                return Product(**service.entity)
        return None

    def update(self, client: ThreeScaleClient, params: dict):
        client.services.update(self.id, params)
        return self.fetch(client, self.system_name)

    def create(self, client: ThreeScaleClient, ignore_if_exists=True) -> Product:
        existing_product = self.fetch(client, self.system_name)
        if existing_product:
            if ignore_if_exists:
                self.logger.info("Product %s already exists, not creating.", self.name)
                return existing_product
            if not ignore_if_exists:
                raise ValueError("Product {} already exists!".format(self.name))
        client.services.create(dict(
            name=self.name,
            system_name=self.system_name,
            description=self.description
        ))
        return self.fetch(client, self.system_name)

    def delete(self, client: ThreeScaleClient):
        if self.id is None:
            raise ValueError('Cannot delete product, entity ID has not yet been fetched.')
        client.services.delete(entity_id=self.id)

    def update_backends(self, client: ThreeScaleClient, backend_id: int, path: str):
        api_url = f"{client.admin_api_url}/services/{self.id}/backend_usages.json"
        backend = Backend.fetch_by_id(client, backend_id)
        if backend is None:
            raise ValueError('Backend not found: id={}'.format(backend_id))
        usages = BackendUsage(service_id=self.id).list(client)
        backend_args = dict(
            service_id=self.id,
            backend_api_id=backend_id,
            path=path
        )

        for usage in usages:
            if usage.backend_id == backend_id:
                self.logger.info('Backend usage already exists for path=\'{}\'. Updating'.format(path))
                usage.update(client, path=path)
                return

        self.logger.info('Backend usage does not exist for path=\'{}\'. Creating'.format(path))
        response = requests.post(api_url, params={'access_token': client.token}, data=backend_args)
        if not response.ok:
            raise ValueError(
                'Error updating backend usages: code={}, error={}'.format(response.status_code, response.text))

    def delete_backends(self, client: ThreeScaleClient, backend_id: int):
        usages = BackendUsage(service_id=self.id).list(client)
        for usage in usages:
            if usage.id == backend_id:
                usage.delete(client)