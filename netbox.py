from __future__ import annotations
from utils import *
from pynetbox.core.api import Api
from pynetbox.models.ipam import Record
from configparser import ConfigParser
from typing import Any
import logging

# Logging enable
logger = logging.getLogger(__name__)

# Read in configuration data from config.ini
config = ConfigParser()
config.read("adder.conf")

# Set global variables from the config file
API_TOKEN: str = config["netbox"]["token"]
NB_URL: str = config["netbox"]["url"]


class AdderNetbox(Api):
    def __init__(self):
        Api.__init__(self, NB_URL, API_TOKEN)
        self.http_session.verify = False

    def get_dia_ip_addrs(self, site_code: str) -> list[str]:
        """Use Netbox API to grab all DIA IP addresses from site wanrouters.
        Also parse and remove subnet masks. Returns a list."""

        devices: list = [f"{site_code}-wr-1", f"{site_code}-wr-2"]
        dia_ips_masked: list = []

        for device in devices:
            dia_ips_masked.append(self.ipam.ip_addresses.get(device=device, interface="dia1").address)  # type: ignore
            dia_ips_masked.append(self.ipam.ip_addresses.get(device=device, interface="dia2").address)  # type: ignore

        dia_ips: list = [x[0:-3] for x in dia_ips_masked]
        return dia_ips

    def get_vlan_3(self, site_code: str) -> str | None:
        """Use Netbox API to grab the subnet value of vlan 3 at a site"""

        site_prefixes: list[Any | Record] | Any | Record = self.ipam.prefixes.filter(
            site=f"{site_code}"
        )

        if f"{site_code}" in site_prefixes[3].description.lower() and "vlan3" in site_prefixes[3].description.lower():  # type: ignore
            return str(site_prefixes[3].prefix)  # type: ignore
        else:
            return None