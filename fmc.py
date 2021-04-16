from __future__ import annotations
from pprint import pprint
from utils import *
from typing import Any
from datetime import datetime, timedelta
from getpass import getpass
from configparser import ConfigParser
from requests.models import Response
import requests
import logging

# Logging enable
logger = logging.getLogger(__name__)

# Read in configuration data from config.ini
config = ConfigParser()
config.read("adder.conf")

# Define Constants
FMC_HOST: str = config["fmc"]["host"]
DFW_FTD: str = config["fmc"]["dfw_ftd"]
ORD_FTD: str = config["fmc"]["ord_ftd"]
FMC_NETGRP_OBJ_UUID: str = config["fmc"]["network_group_uuid"]
REQUESTS_EXCEPTIONS = (
    requests.RequestException,
    requests.ConnectionError,
    requests.HTTPError,
    requests.URLRequired,
    requests.TooManyRedirects,
    requests.Timeout,
)


class AdderFMC:
    def __init__(self):
        self.host: str = FMC_HOST
        self._creds: tuple[str, str] = self.get_creds()

        try:
            _tokens: dict[str, str] = self.get_tokens()
        except REQUESTS_EXCEPTIONS as e:
            logger.error(f"FMC_CONSTRUCTOR: Failed to connect to FMC: {e}")
            raise

        self.auth_token: str = _tokens["auth"]
        self.refresh_token: str = _tokens["refresh"]
        self.domain_uuid: str = _tokens["domain_uuid"]
        self.token_expire: datetime = datetime.now() + timedelta(minutes=30)
        self.network_group_id = FMC_NETGRP_OBJ_UUID
        self.dfw_ftd: str = DFW_FTD
        self.ord_ftd: str = ORD_FTD

    def get_creds(self) -> tuple[str, str]:
        username: str = input("ADM User: ")
        password: str = getpass(prompt="Password: ")
        creds: tuple[str, str] = (username, password)
        return creds

    def get_tokens(self) -> dict[str, str]:
        r: Response = requests.post(
            f"{self.host}/api/fmc_platform/v1/auth/generatetoken",
            auth=self._creds,
            verify=False,
        )
        tokens: dict[str, str] = {
            "auth": r.headers["X-auth-access-token"],
            "refresh": r.headers["X-auth-refresh-token"],
            "domain_uuid": r.headers["DOMAIN_UUID"],
        }
        return tokens

    def get_auth_header(self) -> dict[str, str]:
        if self.token_expire < datetime.now():
            self.token_expire = datetime.now() + timedelta(minutes=30)
            return {
                "X-auth-access-token": self.auth_token,
                "X-auth-refresh-token": self.refresh_token,
            }
        else:
            return {"X-auth-access-token": self.auth_token}

    def get(
        self,
        uri: str,
        payload: dict[str, Any] | None = None,
        url: str | None = None,
        body: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> requests.Response:
        """Wraps a requests.get method call in the formatting necessary to talk to FMC API"""

        if url is not None:
            r: Response = requests.get(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r
        else:
            r: Response = requests.get(
                f"{self.host}{uri}",
                params=payload,
                headers=self.get_auth_header(),
                json=body,
                verify=False,
            )
            return r

    def post(
        self,
        uri: str,
        body: dict[str, Any] | list[dict[str, Any]],
        payload: dict[str, Any] | None = None,
        url: str | None = None,
    ) -> requests.Response:
        """Wraps a requests.post method call in the formatting necessary to talk to FMC API"""

        if url is not None:
            r: Response = requests.post(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r
        else:
            r: Response = requests.post(
                f"{self.host}{uri}",
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r

    def put(
        self,
        uri: str,
        body: dict[str, Any] | list[dict[str, Any]],
        payload: dict[str, Any] | None = None,
        url: str | None = None,
    ) -> requests.Response:
        """Wraps a requests.put method call in the formatting necessary to talk to FMC API"""

        if url is not None:
            r: Response = requests.put(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r
        else:
            r: Response = requests.put(
                f"{self.host}{uri}",
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r

    def get_netgrp_ips(self) -> list[str]:
        """API request to the FMC API to grab all of the objects in the DIA IP PROD network group,
        parse out the names, return as list."""
        uri: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}/object/networkgroups/{self.network_group_id}"
        r: Response = self.get(uri)
        ips_in_netgrp: list[str] = []

        for each_object in r.json()["objects"]:
            ips_in_netgrp.append(each_object["name"])

        for each_object in r.json()["literals"]:
            ips_in_netgrp.append(each_object["value"])

        return ips_in_netgrp

    def get_all_hosts(self) -> dict[str, str]:
        """Returns a dictionary with object names as keys, and their resource URLs as values"""
        all_hosts: dict[str, str] = {}
        url: str | None = None
        uri: str = (
            f"/api/fmc_config/v1/domain/{self.domain_uuid}/object/networkaddresses"
        )
        payload: dict[str, int] | None = {"limit": 1000}

        while True:
            r: Response = self.get(uri, payload, url)

            for item in r.json()["items"]:
                all_hosts[item["name"]] = item["links"]["self"]

            if "next" in r.json()["paging"].keys():
                url = r.json()["paging"]["next"][0]
                payload = None
            else:
                break

        return all_hosts

    def create_bulk_request_body(
        self, ip_addrs: list[str]
    ) -> list[dict[str, str | bool]]:
        """Takes in a list of IP addresses and builds a json-serializable list of dictionaries out of the contents. This forms the request body to create new host objects."""
        request_body: list[dict[str, str | bool]] = []
        for addr in ip_addrs:
            request_body.append(
                {
                    "name": addr,
                    "value": addr,
                    "description": "Added via REST API",
                    "type": "Host",
                }
            )

        return request_body

    def create_host_objects(self, ip_addrs: list[str]) -> list[dict[str, str]]:
        """Use the FMC API to create a new host object; returns the UUIDs of
        the created objects."""
        uri: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}/object/hosts"
        new_objects: list[dict[str, str]] = []

        if len(ip_addrs) > 1:
            logger.debug(
                "CREATE_NET_OBJ: bulk flag true; multiple objects being created"
            )
            multi_body: list[dict[str, str | bool]] = self.create_bulk_request_body(
                ip_addrs
            )
            payload: dict[str, bool] = {"bulk": True}
            logger.debug(
                f"CREATE_NET_OBJ: URI: {uri}\n Body: {multi_body}\n Payload: {payload}"
            )
            r: Response = self.post(uri, multi_body, payload)
        else:
            logger.debug("CREAT_NET_OBJ: bulk flag not set")
            single_body: dict[str, str | bool] = {
                "name": ip_addrs[0],
                "value": ip_addrs[0],
                "description": "Added via REST API",
                "type": "Host",
            }
            r: Response = self.post(uri, single_body)

        if 200 <= r.status_code <= 299:
            for item in r.json()["items"]:
                new_objects.append(
                    {"name": item["name"], "id": item["id"], "type": item["type"]}
                )
        else:
            logger.error("CREAT_NET_OBJ: Error creating objects.")
            pprint(r.json())
            raise SomethingBroke(broke_thing=r, message="Failure to create objects")

        return new_objects

    # def update_network_group(
    #     self, new_objects: list[dict[str, str]]
    # ) -> requests.Response:
    #     """This method takes directly takes in the results of the create_host_objects function
    #     and adds those new objects to the PROD DIA network group with the FMC API"""
    #     uri: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}/object/networkgroups/{self.network_group_id}"
    #     request_body: dict[str, Any] = {}
    #     request_body["id"] = self.network_group_id
    #     request_body["type"] = "NetworkGroup"
    #     request_body["name"] = "Store-DIA-PROD"
    #     request_body["objects"] = []
    #     request_body["literals"] = []
    #     logger.debug(f"UPDATE_NET_GRP: URI: {uri}\n BODY: {request_body}")
    #     r: Response = self.put(uri, request_body)
    #     if r.status_code >= 200 and r.status_code <= 299:
    #         return r
    #     else:
    #         logger.error(f"UPDATE_NET_GRP: {r.text}")
    #         raise SomethingBroke(r.status_code, message="Failed to update OBJ_GRP")

    def get_deployable_devices(self) -> list[dict[str, str]]:
        """Get a list of devices with config changes ready to be deployed from the FMC API"""
        payload: dict[str, bool] = {"expanded": True}
        response_data: list[dict[str, str]] = []
        uri: str = (
            f"/api/fmc_config/v1/domain/{self.domain_uuid}/deployment/deployabledevices"
        )
        r: Response = self.get(uri, payload)
        for item in r.json()["items"]:
            response_data.append(
                {
                    "name": item["name"],
                    "id": item["device"]["id"],
                    "version": item["version"],
                }
            )
        return response_data

    def deploy_to_devices(self):
        """Check to see if the two datacenter FTDs are in the list of devices with changes ready to go.
        If so, deploy the pending changes from the FMC to the FTD clusters."""
        uri: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}/deployment/deploymentrequests"
        deployable_devices = self.get_deployable_devices()
        dfw_response = None
        ord_response = None

        for device in deployable_devices:
            if device["name"] == self.dfw_ftd:
                dfw_body = {
                    "type": "DeploymentRequest",
                    "version": device["version"],
                    "forceDeploy": True,
                    "ignoreWarning": True,
                    "deviceList": [
                        device["id"],
                    ],
                }
                dfw_response = self.post(uri, dfw_body)
            if device["name"] == self.ord_ftd:
                ord_body = {
                    "type": "DeploymentRequest",
                    "version": device["version"],
                    "forceDeploy": True,
                    "ignoreWarning": True,
                    "deviceList": [
                        device["id"],
                    ],
                }
                ord_response = self.post(uri, ord_body)

        return dfw_response, ord_response