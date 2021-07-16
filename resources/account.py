from __future__ import annotations

import logging
from typing import Union

from threescale_api import ThreeScaleClient

from resources.resource import Resource


class Account(Resource):
    logger = logging.getLogger('account')

    def __init__(
            self,
            id=None,
            username=None,
            created_at=None,
            updated_at=None,
            credit_card_stored=None,
            monthly_billing_enabled=None,
            monthly_charging_enabled=None,
            state=None,
            org_name=None,
            links=None):
        self.id = id
        self.username = username  # entity_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.credit_card_stored = credit_card_stored
        self.monthly_billing_enabled = monthly_billing_enabled
        self.monthly_charging_enabled = monthly_charging_enabled
        self.state = state  # one of [ 'pending' | 'approved' | 'rejected' ]
        self.org_name = org_name
        self.links = links

    def fetch(self, client: ThreeScaleClient, system_name: str) -> Union[Account, None]:
        accounts = client.accounts.list()
        for account in accounts:
            self.logger.debug(account.entity)
            if account.entity['org_name'] == system_name:
                return Account(**dict(username=account.entity_name, **account.entity))
        return None

    def create(self, client: ThreeScaleClient) -> Union[Account, None]:
        if self.username is None:
            raise ValueError('Account username must be specified for creation.')
        self.logger.info('Creating account: {}'.format(self.username))
        client.accounts.create(dict(
            credit_card_stored=self.credit_card_stored,
            monthly_billing_enabled=self.monthly_billing_enabled,
            monthly_charging_enabled=self.monthly_charging_enabled,
            state=self.state if self.state else 'approved',
            username=self.username,
            org_name=self.org_name if self.org_name else self.username,
        ))
        return self.fetch(client, self.username)

    def delete(self, client: ThreeScaleClient):
        if self.username is None:
            raise ValueError('Account username must be specified for deletion.')
        if self.id is None:
            account = self.fetch(client, self.username)
            if not account:
                raise ValueError('Account {} not found.'.format(self.username))
            self.id = account.id

        self.logger.info('Deleting account: {}'.format(self.username))
        client.accounts.delete(self.id)
