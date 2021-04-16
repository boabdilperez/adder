from __future__ import annotations
from pprint import pprint
from utils import *
from typing import Any
from datetime import datetime, timedelta
from getpass import getpass
from configparser import ConfigParser
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
FMC_DIA_NETGRP_OBJ_UUID: str = config["fmc"]["dia_network_group_uuid"]
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
        self.dia_network_group_uuid = FMC_DIA_NETGRP_OBJ_UUID
        self.dfw_ftd: str = DFW_FTD
        self.ord_ftd: str = ORD_FTD

    def get_creds(self) -> tuple[str, str]:
        username: str = input("ADM User: ")
        password: str = getpass(prompt="Password: ")
        creds: tuple[str, str] = (username, password)
        return creds

    def get_tokens(self) -> dict[str, str]:
        r: requests.Response = requests.post(
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
            r: requests.Response = requests.get(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r
        else:
            r: requests.Response = requests.get(
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
            r: requests.Response = requests.post(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r
        else:
            r: requests.Response = requests.post(
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
            r: requests.Response = requests.put(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r
        else:
            r: requests.Response = requests.put(
                f"{self.host}{uri}",
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            return r

    def get_network_group(self, net_grp_id: str) -> requests.Response:
        """FMC API GET request to grab the representation of an object group. Needs the UUID of the object group and returns the http response if it's in the 200 range."""
        uri: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}/object/networkgroups/{net_grp_id}"
        r: requests.Response = self.get(uri)
        if 200 <= r.status_code <= 299:
            return self.get(uri)
        else:
            raise StatusCodeError(r.status_code, r.text)

    def get_netgrp_ips(self, network_group_object: requests.Response) -> list[str]:
        """This helper function parses out the individual objects and literals from the return of a GET on a network object group;
        returns a string of obj names and literal IPs"""
        ips_in_netgrp: list[str] = []

        for each_object in network_group_object.json()["objects"]:
            ips_in_netgrp.append(each_object["name"])

        for each_object in network_group_object.json()["literals"]:
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
            r: requests.Response = self.get(uri, payload, url)

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
            r: requests.Response = self.post(uri, multi_body, payload)
        else:
            logger.debug("CREAT_NET_OBJ: bulk flag not set")
            single_body: dict[str, str | bool] = {
                "name": ip_addrs[0],
                "value": ip_addrs[0],
                "description": "Added via REST API",
                "type": "Host",
            }
            r: requests.Response = self.post(uri, single_body)

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

    def update_dia_network_group(
        self, new_objects: list[dict[str, str]]
    ) -> requests.Response:
        """This function needs to take in a list of new objects to add into an object group,
        retrieve the existing object group, append the new data to it, and return it to the API via a PUT request."""
        uri = f"/api/fmc_config/v1/domain/{self.domain_uuid}/object/networkgroups/{self.dia_network_group_uuid}"

        original_network_grp = self.get_network_group(self.dia_network_group_uuid)
        modified_obj_group = original_network_grp.json()
        modified_obj_group.pop("metadata", None)
        modified_obj_group.pop("links", None)

        for object in new_objects:
            modified_obj_group["objects"].append(object)

        r: requests.Response = self.put(uri, modified_obj_group)
        if 200 <= r.status_code <= 299:
            return r
        else:
            raise StatusCodeError(
                r.status_code, message="API failure to update DIA object group"
            )

    def get_deployable_devices(self) -> requests.Response:
        """Get a list of devices with config changes ready to be deployed from the FMC API"""
        payload: dict[str, bool] = {"expanded": True}
        uri: str = (
            f"/api/fmc_config/v1/domain/{self.domain_uuid}/deployment/deployabledevices"
        )
        r: requests.Response = self.get(uri, payload)

        if 200 <= r.status_code <= 299:
            return r
        else:
            raise StatusCodeError(
                r.status_code, message="API Failure to get deployable devices"
            )

    # def deploy_to_devices(self):
    #     """Check to see if the two datacenter FTDs are in the list of devices with changes ready to go.
    #     If so, deploy the pending changes from the FMC to the FTD clusters."""
    #     uri: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}/deployment/deploymentrequests"
    #     deployable_devices = self.get_deployable_devices()
    #     dfw_response = None
    #     ord_response = None

    #     for device in deployable_devices:
    #         if device["name"] == self.dfw_ftd:
    #             dfw_body = {
    #                 "type": "DeploymentRequest",
    #                 "version": device["version"],
    #                 "forceDeploy": True,
    #                 "ignoreWarning": True,
    #                 "deviceList": [
    #                     device["id"],
    #                 ],
    #             }
    #             dfw_response = self.post(uri, dfw_body)
    #         if device["name"] == self.ord_ftd:
    #             ord_body = {
    #                 "type": "DeploymentRequest",
    #                 "version": device["version"],
    #                 "forceDeploy": True,
    #                 "ignoreWarning": True,
    #                 "deviceList": [
    #                     device["id"],
    #                 ],
    #             }
    #             ord_response = self.post(uri, ord_body)

    #     return dfw_response, ord_response