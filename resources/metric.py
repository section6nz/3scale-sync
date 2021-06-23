from __future__ import annotations

import logging
from typing import List

import requests
from threescale_api import ThreeScaleClient


class Metric:
    def __init__(self,
                 id=None,
                 name=None,
                 system_name=None,
                 friendly_name=None,
                 description=None,
                 unit=None,
                 created_at=None,
                 updated_at=None,
                 links=None):
        self.id = id
        self.name = name
        self.system_name = system_name
        self.friendly_name = friendly_name
        self.description = description
        self.unit = unit
        self.created_at = created_at
        self.updated_at = updated_at
        self.links = links

    @staticmethod
    def list(client: ThreeScaleClient, service_id: int) -> List[Metric]:
        logger = logging.getLogger('metric')
        api_url = f"{client.admin_api_url}/services/{service_id}/metrics.json"
        response = requests.get(api_url, params={'access_token': client.token})
        logger.debug(response.text)
        metrics_json = response.json()['metrics']
        return [Metric(**m['metric']) for m in metrics_json]

    @staticmethod
    def fetch_hits_metric(client: ThreeScaleClient, service_id: int) -> Metric:
        return [m for m in Metric.list(client, service_id) if m.system_name == 'hits'][0]
