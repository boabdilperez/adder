from __future__ import annotations
from utils import *
from typing import Any
from datetime import datetime, timedelta
from getpass import getpass
from configparser import ConfigParser
from pprint import pprint
import json
import requests
import logging
import uuid


# Logging enable
logger = logging.getLogger(__name__)

# Read in configuration data from config.ini
config = ConfigParser()
config.read("adder.conf")

# Define Constants
FMC_HOST: str = config["fmc"]["host"]
DFW_FTD: str = config["fmc"]["dfw_ftd"]
ORD_FTD: str = config["fmc"]["ord_ftd"]
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
        self.dfw_ftd: str = DFW_FTD
        self.ord_ftd: str = ORD_FTD
        self.uri_base: str = f"/api/fmc_config/v1/domain/{self.domain_uuid}"
        logger.debug("Connection to FMC established")

    def get(
        self,
        uri: str,
        payload: dict[str, Any] | None = None,
        url: str | None = None,
        body: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> requests.Response:
        """Wraps a requests.get method call in the formatting necessary to talk to FMC API"""

        if url is not None:
            logger.debug(f"GET decision: overriding GET request with {url}")
            r: requests.Response = requests.get(
                url,
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            logger.debug(f"Making get request to {url}")
            if 200 <= r.status_code <= 299:
                return r
            else:
                raise StatusCodeError(r.status_code, r.text)
        else:
            logger.debug(f"GET decision: no override URL provided")
            r: requests.Response = requests.get(
                f"{self.host}{uri}",
                params=payload,
                headers=self.get_auth_header(),
                json=body,
                verify=False,
            )
            logger.debug(f"Making get request to {uri}")
            if 200 <= r.status_code <= 299:
                return r
            else:
                raise StatusCodeError(r.status_code, r.text)

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
            logger.debug(f"Making post request: {r.request.body}")
            if 200 <= r.status_code <= 299:
                return r
            else:
                raise StatusCodeError(r.status_code, r.text)
        else:
            r: requests.Response = requests.post(
                f"{self.host}{uri}",
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            logger.debug(f"Making post request: {r.request.body}")
            if 200 <= r.status_code <= 299:
                return r
            else:
                raise StatusCodeError(r.status_code, r.text)

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
            logger.debug(f"Making put request: {r.request.body}")
            if 200 <= r.status_code <= 299:
                return r
            else:
                raise StatusCodeError(r.status_code, r.text)
        else:
            r: requests.Response = requests.put(
                f"{self.host}{uri}",
                headers=self.get_auth_header(),
                params=payload,
                json=body,
                verify=False,
            )
            logger.debug(f"Making put request: {r.request.body}")
            if 200 <= r.status_code <= 299:
                return r
            else:
                raise StatusCodeError(r.status_code, r.text)

    def get_all_hosts(self) -> dict[str, str]:
        """Returns a dictionary with object names as keys, and their UUIDs as values"""
        all_hosts: dict[str, str] = {}
        url: str | None = None
        uri: str = f"{self.uri_base}/object/networkaddresses"
        payload: dict[str, int] | None = {"limit": 1000}

        while True:
            try:
                r: requests.Response = self.get(uri, payload, url)
            except StatusCodeError as e:
                logger.error(f"Error retrieving list of network addresses: {e}")
                raise

            for item in r.json()["items"]:
                all_hosts[item["name"]] = item["id"]

            if "next" in r.json()["paging"].keys():
                url = r.json()["paging"]["next"][0]
                payload = None
            else:
                break

        return all_hosts

    def get_auth_header(self) -> dict[str, str]:
        """Checks the current time against the predicted expiry of the auth token.
        Returns a dict with the correct formatted authentication header for a Requests API call against the FMC"""
        if self.token_expire < datetime.now():
            self.token_expire = datetime.now() + timedelta(minutes=30)
            return {
                "X-auth-access-token": self.auth_token,
                "X-auth-refresh-token": self.refresh_token,
            }
        else:
            return {"X-auth-access-token": self.auth_token}

    def get_creds(self) -> tuple[str, str]:
        """Retrieve ADM username and password from the user"""
        username: str = input("ADM User: ")
        password: str = getpass(prompt="Password: ")
        creds: tuple[str, str] = (username, password)
        return creds

    def get_deployable_devices(self) -> requests.Response:
        """Get a list of devices with config changes ready to be deployed from the FMC API"""
        payload: dict[str, bool | int] = {"expanded": True, "limit": 100}
        uri: str = f"{self.uri_base}/deployment/deployabledevices"
        try:
            r: requests.Response = self.get(uri, payload)
        except StatusCodeError as e:
            logger.error(f"Error retrieving list of deployable devices: {e}")
            raise

        return r

    def get_host_by_name(self, name: str) -> requests.Response:
        uri: str = f"{self.uri_base}/object/networkaddresses"
        url: str | None = None
        payload: dict[str, int] | None = {"limit": 1000}
        r: requests.Response = self.get(uri, payload)

        while True:
            try:
                r: requests.Response = self.get(uri, payload, url)
            except StatusCodeError as e:
                logger.error(f"Error retreiving info for specific host: {name}")
                raise

            for item in r.json()["items"]:
                if item["name"] == name:
                    return self.get_host_by_uuid(item["id"])
            else:
                if "next" in r.json()["paging"].keys():
                    url = r.json()["paging"]["next"][0]
                    payload = None
                else:
                    raise HostNotFoundWarning(name)

    def get_host_by_uuid(self, uuid: str) -> requests.Response:
        uri = f"{self.uri_base}/object/hosts/{uuid}"
        return self.get(uri)

    def get_netgrp_ips(self, network_group_object: requests.Response) -> list[str]:
        """This helper function parses out the individual objects and literals from the return of a GET on a network object group;
        returns a string of obj names and literal IPs"""
        ips_in_netgrp: list[str] = []

        for each_object in network_group_object.json()["objects"]:
            ips_in_netgrp.append(each_object["name"])

        for each_object in network_group_object.json()["literals"]:
            ips_in_netgrp.append(each_object["value"])

        return ips_in_netgrp

    def get_netgroup_by_name(self, name: str) -> requests.Response | None:
        """Searches for the network object group named in the args, returns the HTTP response if it's in the 200-299 range."""
        uri: str = f"{self.uri_base}/object/networkgroups"
        r: requests.Response = self.get(uri)

        found = False
        while not found:
            for item in r.json()["items"]:
                if item["name"] == name:
                    found = True
                    logger.debug(f"Item with matching name found: {item['id']}")
                    return self.get_netgroup_by_uuid(item["id"])
            else:
                if "next" in r.json()["paging"]:
                    url = r.json()["paging"]["next"][0]
                    logger.debug(f"URL for request built: {url}")
                    r: requests.Response = self.get(uri, url=url)
                else:
                    return None

    def get_netgroup_by_uuid(self, net_grp_id: str) -> requests.Response:
        """FMC API GET request to grab the representation of an object group. Needs the UUID of the object group and returns the http response if it's in the 200 range."""
        uri: str = f"{self.uri_base}/object/networkgroups/{net_grp_id}"
        try:
            r: requests.Response = self.get(uri)
        except StatusCodeError as e:
            logger.error(f"Error retreiving network group: {e}")
            raise

        # if "next" not in r.json()["paging"].keys():
        return r
        # else:
        #     raise SomethingBroke(
        #         r.text,
        #         message="Size of HTTP response is too big. Implement pagination.",
        #     )

    def get_netgroup_uuid(self, name: str) -> str | None:
        """Searches for the network object group named in the args, returns object's UUID if it's in the 200-299 range."""
        uri: str = f"{self.uri_base}/object/networkgroups"
        r: requests.Response = self.get(uri)

        found = False
        while not found:
            for item in r.json()["items"]:
                if item["name"] == name:
                    found = True
                    logger.debug(f"UUID of object group {name}: {item['id']}")
                    return item["id"]
            else:
                if "next" in r.json()["paging"]:
                    url = r.json()["paging"]["next"][0]
                    r: requests.Response = self.get(uri, url=url)
                else:
                    return None

    def get_tokens(self) -> dict[str, str]:
        """API request to the FMC API to authenticate user and return the tokens necessary for further, authenticated, API calls."""
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
        """Use the FMC API to create a new host object; returns the json representation of
        the created objects."""
        uri: str = f"{self.uri_base}/object/hosts"
        new_objects: list[dict[str, str]] = []
        flag = len(ip_addrs)

        try:
            for addr in ip_addrs:
                self.check_host_exists(addr)
        except HostAlreadyExistsWarning:
            logger.warning(f"Host already exists on FMC")
            raise

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
            try:
                r: requests.Response = self.post(uri, multi_body, payload)
            except StatusCodeError as e:
                logger.error(f"Error creating host object: {e}")
                raise
        else:
            logger.debug("CREAT_NET_OBJ: bulk flag not set")
            single_body: dict[str, str | bool] = {
                "name": ip_addrs[0],
                "value": ip_addrs[0],
                "description": "Added via REST API",
                "type": "Host",
            }
            try:
                r: requests.Response = self.post(uri, single_body)
                logger.debug(f"Create new object post response: {r.json()}")
            except StatusCodeError as e:
                logger.error(f"Error creating host object: {e}")
                raise

        if flag > 1:
            for item in r.json()["items"]:
                new_objects.append(
                    {"name": item["name"], "id": item["id"], "type": item["type"]}
                )
        elif flag == 1:
            new_objects.append(
                {
                    "name": r.json()["name"],
                    "id": r.json()["id"],
                    "type": r.json()["type"],
                }
            )

        logger.debug(f"New host objects created: {new_objects}")
        return new_objects

    def update_group_from_existing_host(
        self, group_uuid: str, host_name: str
    ) -> requests.Response:
        new_obj = []
        existing_host = self.get_host_by_name(host_name).json()
        existing_host.pop("links")
        existing_host.pop("metadata")
        existing_host.pop("value")

        new_obj.append(existing_host)
        return self.update_object_group(group_uuid, new_obj)

    def update_object_group(
        self, group_uuid: str, new_objects: list[dict[str, str]]
    ) -> requests.Response:
        """This function needs to take in a list of new objects to add into an object group,
        retrieve the existing object group, append the new data to it, and return it to the API via a PUT request.
        We also grab a backup of the object-group being modified and dump it into a file for use by a rollback method."""
        uri = f"{self.uri_base}/object/networkgroups/{group_uuid}"

        obj_group = self.get_netgroup_by_uuid(group_uuid).json()
        obj_group.update({"backup_timestamp": str(datetime.now())})
        obj_group.update({"backup_uuid": str(uuid.uuid1())})
        try:
            with open(f"./backups/{obj_group['backup_uuid']}.json", "w") as backup:
                json.dump(obj_group, backup)
        except:
            logger.error(f"Error creating backup of {obj_group}")
        obj_group.pop("metadata")
        obj_group.pop("links")
        obj_group.pop("backup_timestamp")
        obj_group.pop("backup_uuid")

        for object in new_objects:
            obj_group["objects"].append(object)

        try:
            r: requests.Response = self.put(uri, obj_group)
        except StatusCodeError as e:
            logger.error(f"Error writing data to object group: {e}")
            raise

        return r

    def deploy_to_device(self, device_name: str):
        """API request to FMC. Takes in a device name as an argument and pushes the changes pending for that device."""
        uri: str = f"{self.uri_base}/deployment/deploymentrequests"
        body = {
            "type": "DeploymentRequest",
            "version": None,
            "forceDeploy": True,
            "ignoreWarning": True,
            "description": "Deployment initiated by API with Adder",
            "deviceList": [],
        }

        found = False
        deployable_devices = self.get_deployable_devices()
        for device in deployable_devices.json()["items"]:
            if device["name"] == device_name:
                body["version"] = device["version"]
                body["deviceList"].append(device["device"]["id"])
                found = True
                break

        if found == False:
            raise FirewallNotDeployableWarning(
                device_name, message=f"FTD {device_name} is not in a deployable state."
            )

        try:
            r: requests.Response = self.post(uri, body)
        except StatusCodeError as e:
            logger.error(
                f"Error making API request to deploy pending changes to the FTD: {e}"
            )
            raise

        logger.debug(f"Deployment Response: {r.text}")
        return r

    def check_host_exists(self, host: str) -> bool:
        """Match names of proposed object against the list of all net object names in the fmc"""
        all_hosts = self.get_all_hosts()
        for name in all_hosts:
            if name == host:
                logger.warning(
                    f"The name of the host object {host} already exists on the FMC"
                )
                raise HostAlreadyExistsWarning(host)
        return True