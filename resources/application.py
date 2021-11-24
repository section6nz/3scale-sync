from __future__ import annotations

import logging
from typing import List, Union
from xml.etree import ElementTree

import requests
from threescale_api import ThreeScaleClient

from config import Config
from resources.resource import Resource


class Application(Resource):
    logger = logging.getLogger('application')

    def __init__(
            self,
            id=None,
            state=None,
            enabled=None,
            created_at=None,
            updated_at=None,
            service_id=None,
            service_name=None,
            plan_id=None,
            plan_name=None,
            account_id=None,
            org_name=None,
            first_traffic_at=None,
            first_daily_traffic_at=None,
            application_id=None,
            redirect_url=None,
            client_id=None,
            client_secret=None,
            oidc_configuration=None,
            links=None,
            name=None,
            description=None,
            user_key=None,
            provider_verification_key=None
    ):
        self.id = id
        self.state = state
        self.enabled = enabled
        self.created_at = created_at
        self.updated_at = updated_at
        self.service_id = service_id
        self.service_name = service_name
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.account_id = account_id
        self.org_name = org_name
        self.first_traffic_at = first_traffic_at
        self.first_daily_traffic_at = first_daily_traffic_at
        self.application_id = application_id
        self.redirect_url = redirect_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.oidc_configuration = oidc_configuration
        self.links = links
        self.name = name
        self.description = description
        self.user_key = user_key
        self.provider_verification_key = provider_verification_key

    def fetch(self, client: ThreeScaleClient, system_name: str) -> Union[Application, None]:
        applications = self.list(client)
        application: Application
        for application in applications:
            if application.name == system_name:
                return application
        return None

    def create(self, client: ThreeScaleClient, application_id=None, application_key=None, redirect_url=None,
               ignore_if_exists=True, delete_if_exists=False) -> Application:
        try:
            assert self.account_id is not None
            assert self.plan_id is not None
            assert self.name is not None
            assert self.description is not None
        except AssertionError as e:
            raise ValueError('Required creation parameter not provided: {}'.format(e))

        # Check for existing application
        existing_application = self.fetch(client, self.name)
        if existing_application:
            if delete_if_exists:
                self.logger.info("Application %s already exists, deleting.", self.name)
                existing_application.delete(client)
            elif ignore_if_exists:
                self.logger.info("Application %s already exists, not creating.", self.name)
                return existing_application
            else:
                raise ValueError("Application {} already exists!".format(self.name))

        api_url = f"{client.admin_api_url}/accounts/{self.account_id}/applications.json"
        params = dict(
            account_id=self.account_id,
            plan_id=self.plan_id,
            name=self.name,
            description=self.description,
            application_id=self.client_id,
            application_key=self.client_secret,
            redirect_url=redirect_url
        )
        response = requests.post(api_url, params={
            'access_token': client.token,
            **params
        }, verify=Config.SSL_VERIFY)
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError(
                'Error creating application: code={}, error={}'.format(response.status_code, response.text))
        return Application(**response.json()['application'])

    def delete(self, client: ThreeScaleClient):
        application = self.fetch(client, self.name)
        if not application:
            raise ValueError('Application {} does not exist for deletion'.format(self.name))
        api_url = f"{client.admin_api_url}/accounts/{self.account_id}/applications/{application.id}"
        response = requests.delete(api_url, params={'access_token': client.token}, verify=Config.SSL_VERIFY)
        if not response.ok:
            raise ValueError('Error deleting application: name={}, code={}, error={}'
                             .format(self.name, response.status_code, response.text))
        else:
            self.logger.info('Deleted application: {}'.format(self.name))

    @staticmethod
    def list(client: ThreeScaleClient, user: str = None) -> List[Application]:
        """
        Listing applications in 3Scale is not provided by `ThreeScaleClient`
        so we provide a custom implementation. If no user is specified, applications
        for across all users will be listed.
        """
        logger = logging.getLogger('application')
        logger.info("Fetching applications for user: {}".format(user if user else "ALL_USERS"))
        accounts = client.accounts.list()
        filtered_users = [a.entity_name for a in accounts]
        if user:
            if user not in [a.entity_name for a in accounts]:
                raise ValueError('Account for user {} not found.'.format(user))
            filtered_users = [a.entity_name for a in accounts if a.entity_name == user]

        parsed_applications = []
        for user_account in filtered_users:
            user_resource = list(filter(lambda u: u.entity_name == user_account, accounts))[0]
            applications_list_response = requests.get(
                user_resource.applications.url + '.json', params={'access_token': client.token},
                verify=Config.SSL_VERIFY)
            if not applications_list_response.ok:
                raise ValueError(
                    'Applications list request failed with {}, error={}, url={}'.format(
                        applications_list_response.status_code,
                        applications_list_response.text,
                        applications_list_response.url))
            applications = applications_list_response.json()['applications']
            for application in applications:
                app = Application(**application['application'])
                parsed_applications.append(app)
        return parsed_applications

    def update(self, client: ThreeScaleClient, **kwargs) -> Application:
        api_url = f"{client.admin_api_url}/accounts/{self.account_id}/applications/{self.id}.json"
        response = requests.put(api_url, params={'access_token': client.token}, data=kwargs, verify=Config.SSL_VERIFY)
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError(
                'Error updating application {}, code={}, error={}'
                    .format(self.name, response.status_code, response.text))
        return self.fetch(client, self.name)


class ApplicationPlan:
    logger = logging.getLogger('application_plan')

    def __init__(
            self,
            id=None,
            name=None,
            state=None,
            setup_fee=None,
            cost_per_month=None,
            trial_period_days=None,
            cancellation_period=None,
            approval_required=None,
            default=None,
            created_at=None,
            updated_at=None,
            custom=None,
            system_name=None,
            links=None
    ):
        self.id = id
        self.name = name
        self.state = state
        self.setup_fee = setup_fee
        self.cost_per_month = cost_per_month
        self.trial_period_days = trial_period_days
        self.cancellation_period = cancellation_period
        self.approval_required = approval_required
        self.default = default
        self.created_at = created_at
        self.updated_at = updated_at
        self.custom = custom
        self.system_name = system_name if system_name else name.replace('-', '_').replace(' ', '_')
        self.links = links

    @staticmethod
    def fetch(client: ThreeScaleClient, service_id: int, system_name: str) -> Union[ApplicationPlan, None]:
        plans = ApplicationPlan.list(client, service_id)
        for plan in plans:
            if plan.system_name == system_name:
                return plan
        return None

    @staticmethod
    def list(client: ThreeScaleClient, service_id: int) -> List[ApplicationPlan]:
        logger = logging.getLogger('application_plan')
        api_url = f"{client.admin_api_url}/services/{service_id}/application_plans.json"
        service = client.services.fetch(service_id)
        if not service:
            raise ValueError('Unable to find service id: {}'.format(service_id))
        application_plans_response = requests.get(api_url, params={'access_token': client.token},
                                                  verify=Config.SSL_VERIFY)
        logger.debug(application_plans_response.text)
        if not application_plans_response.ok:
            raise ValueError('Error retrieving application plans, code={}, error={}'.format(
                application_plans_response.status_code, application_plans_response.text))
        parsed_plans = []
        for plan in application_plans_response.json()['plans']:
            parsed_plan = ApplicationPlan(**plan['application_plan'])
            parsed_plans.append(parsed_plan)
        return parsed_plans

    def create(self, client: ThreeScaleClient, service_id: int, ignore_if_exists=True) -> ApplicationPlan:
        try:
            assert service_id is not None
        except AssertionError as e:
            raise ValueError('Creating application plan failed! service_id is required, got={}'.format(service_id))

        existing_plan = self.fetch(client, service_id, self.system_name)
        if existing_plan:
            if ignore_if_exists:
                self.logger.info("Application plan %s already exists, not creating.", self.name)
                return existing_plan
            if not ignore_if_exists:
                raise ValueError("Application plan {} already exists!".format(self.name))

        api_url = f"{client.admin_api_url}/services/{service_id}/application_plans.json"
        service = client.services.fetch(service_id)
        if not service:
            raise ValueError('Unable to find service id: {}'.format(service_id))
        plan_args = dict(
            service_id=service_id,
            name=self.name,
            system_name=self.system_name
        )
        response = requests.post(api_url, params={'access_token': client.token}, data=plan_args,
                                 verify=Config.SSL_VERIFY)
        self.logger.debug(response.text)
        if not response.ok:
            raise ValueError(
                'Could not create application plan: code={}, error={}'.format(response.status_code, response.text))
        application_plan_json = response.json()['application_plan']
        return ApplicationPlan(**application_plan_json)

    def delete(self, client: ThreeScaleClient, service_id: int):
        api_url = f"{client.admin_api_url}/services/{service_id}/application_plans/{self.id}"
        response = requests.delete(api_url, params={'access_token': client.token}, verify=Config.SSL_VERIFY)
        if not response.ok:
            raise ValueError('Error deleting application plan with service={}, id={}, code={}, error={}'
                             .format(service_id, self.id, response.status_code, response.text))


class ApplicationOIDCConfiguration:
    logger = logging.getLogger('application_oidc_configuration')

    def __init__(
            self,
            id=None,
            standard_flow_enabled=None,
            implicit_flow_enabled=None,
            service_accounts_enabled=None,
            direct_access_grants_enabled=None
    ):
        self.id = id
        self.standard_flow_enabled = standard_flow_enabled
        self.implicit_flow_enabled = implicit_flow_enabled
        self.service_accounts_enabled = service_accounts_enabled
        self.direct_access_grants_enabled = direct_access_grants_enabled

    @staticmethod
    def fetch(client: ThreeScaleClient, service_id: int) -> Union[ApplicationOIDCConfiguration, None]:
        api_url = f"{client.admin_api_url}/services/{service_id}/proxy/oidc_configuration"
        oidc_configuration_response = requests.get(api_url, params={'access_token': client.token}, verify=Config.SSL_VERIFY)
        if not oidc_configuration_response.ok:
            raise ValueError(
                'Applications list request failed with {}, error={}, url={}'.format(
                    oidc_configuration_response.status_code,
                    oidc_configuration_response.text,
                    oidc_configuration_response.url))

        oidc_xml = ElementTree.fromstring(oidc_configuration_response.text)
        kwargs = dict()
        for attrib in oidc_xml:
            kwargs[attrib.tag] = attrib.text
        return ApplicationOIDCConfiguration(**kwargs)

    def update(self, client: ThreeScaleClient, service_id: int):
        self.logger.info("Updating OIDC flows.")
        api_url = f"{client.admin_api_url}/services/{service_id}/proxy/oidc_configuration"
        oidc_params = dict(
            standard_flow_enabled=str(self.standard_flow_enabled).lower(),
            implicit_flow_enabled=str(self.implicit_flow_enabled).lower(),
            service_accounts_enabled=str(self.service_accounts_enabled).lower(),
            direct_access_grants_enabled=str(self.direct_access_grants_enabled).lower()
        )
        oidc_response = requests.patch(api_url, params={'access_token': client.token}, data=oidc_params, verify=Config.SSL_VERIFY)
        self.logger.debug(oidc_response.text)
        if not oidc_response.ok:
            raise ValueError('Error updating proxy: code={}, error={}', oidc_response.status_code, oidc_response.text)
