from __future__ import annotations

import logging
from typing import Union, List

import requests
from threescale_api import ThreeScaleClient

from resources.resource import Resource


class Backend(Resource):
    logger = logging.getLogger('backend')

    def __init__(
            self,
            id=None,
            name=None,
            system_name=None,
            description=None,
            private_endpoint=None,
            account_id=None,
            created_at=None,
            updated_at=None,
            links=None):
        self.id = id
        self.name = name
        self.description = description
        self.private_endpoint = private_endpoint
        self.account_id = account_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.links = links
        if not system_name and name:
            self.system_name = name.replace('-', '_').replace(' ', '_')
        else:
            self.system_name = system_name

    def fetch(self, client: ThreeScaleClient, system_name: str) -> Union[Backend, None]:
        for backend in client.backends.list():
            if backend.entity['system_name'] == system_name:
                return Backend(**backend.entity)
        return None

    @staticmethod
    def fetch_by_id(client: ThreeScaleClient, backend_id: int) -> Union[Backend, None]:
        for backend in client.backends.list():
            if backend.entity['id'] == backend_id:
                return Backend(**backend.entity)
        return None

    def create(self, client: ThreeScaleClient, ignore_if_exists=True) -> Backend:
        existing_backend = self.fetch(client, self.system_name)
        if existing_backend:
            if ignore_if_exists:
                self.logger.info("Backend %s already exists, not creating.", self.system_name)
                return existing_backend
            if not ignore_if_exists:
                raise ValueError("Backend {} already exists!".format(self.system_name))

        result = client.backends.create(dict(
            name=self.name,
            system_name=self.system_name,
            description=self.description,
            private_endpoint=self.private_endpoint
        ))

        return Backend(**result.entity)

    def update(self, client: ThreeScaleClient) -> Backend:
        result = client.backends.update(**dict(
            name=self.name,
            description=self.description,
            private_endpoint=self.private_endpoint
        ))

        return Backend(**result.entity)

    def delete(self, client: ThreeScaleClient):
        if self.id is None:
            raise ValueError('Cannot delete backend, entity ID has not yet been fetched.')
        client.backends.delete(entity_id=self.id)


class BackendUsage:
    logger = logging.getLogger('backend_usage')

    def __init__(
            self,
            id=None,
            path=None,
            service_id=None,
            backend_id=None,
            links=None):
        self.id = id
        self.path = path
        self.service_id = service_id
        self.backend_id = backend_id
        self.links = links

    def list(self, client: ThreeScaleClient) -> List[BackendUsage]:
        api_url = f"{client.admin_api_url}/services/{self.service_id}/backend_usages.json"
        response = requests.get(api_url, params={'access_token': client.token})
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError(
                'Error fetching backend usages: code={}, error={}'.format(response.status_code, response.text))
        return [BackendUsage(**b['backend_usage']) for b in response.json()]

    def delete(self, client: ThreeScaleClient):
        self.logger.info('Deleting backend usage for backend_id={}'.format(self.id))
        api_url = f"{client.admin_api_url}/services/{self.service_id}/backend_usages/{self.id}.json"
        response = requests.delete(api_url, params={'access_token': client.token})
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError(
                'Error deleting backend usage: code={}, error={}'.format(response.status_code, response.text))

    def update(self, client: ThreeScaleClient, **kwargs):
        api_url = f"{client.admin_api_url}/services/{self.service_id}/backend_usages/{self.id}.json"
        response = requests.put(api_url, params={'access_token': client.token}, data=kwargs)
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError(
                'Error updating backend usage: code={}, error={}'.format(response.status_code, response.text))
