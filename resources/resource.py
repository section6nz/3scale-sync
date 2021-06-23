from abc import abstractmethod

from threescale_api import ThreeScaleClient


class Resource:
    @abstractmethod
    def fetch(self, client: ThreeScaleClient, system_name: str):
        pass

    @abstractmethod
    def create(self, client: ThreeScaleClient):
        pass

    @abstractmethod
    def delete(self, client: ThreeScaleClient):
        pass
