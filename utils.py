from __future__ import annotations
import ipaddress
import logging

# Logging enable
logger = logging.getLogger(__name__)


class SomethingBroke(Exception):
    """Something doesn't work like I wanted! >:( """

    def __init__(self, broke_thing, message="Something Broke"):
        self.broke_thing = broke_thing
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.broke_thing} -> {self.message}"


class SiteCodeError(SomethingBroke):
    """Exception raised when site code validation fails."""

    def __init__(self, site_code, message="Site code is not valid."):
        self.site_code = site_code
        self.message = message
        super().__init__(self.site_code, self.message)


class StatusCodeError(SomethingBroke):
    """Exception to raise when an API returns an HTTP status code that indicates an error in the request"""

    def __init__(self, status_code, message="HTTP status code indicates API error"):
        self.status_code = status_code
        self.message = message
        super().__init__(self.status_code, self.message)


class FirewallNotDeployableWarning(SomethingBroke):
    """Exception raised when API is instructed to deploy to an FTD that is not in a status that can be deployed."""

    def __init__(self, device_name, message="FTD is not in deployable state"):
        self.device_name = device_name
        self.message = message
        super().__init__(self.device_name, self.message)


class HostAlreadyExistsWarning(SomethingBroke):
    """Exception raised when attempting to add a host object that clashes with the name of an already-existing host object"""

    def __init__(self, host, message="Host object with this name already exists"):
        self.host = host
        self.message = message
        super().__init__(self.host, self.message)


class HostNotFoundWarning(SomethingBroke):
    """Exception raised when attempting to add a host object that clashes with the name of an already-existing host object"""

    def __init__(self, host, message="Host object with this name cannot be found"):
        self.host = host
        self.message = message
        super().__init__(self.host, self.message)


class IPOverlapWarning(SomethingBroke):
    """Exception raised when the DIA IP addresses retrieved from Netbox already appear to exist in the DIA object-group of the FMC"""

    def __init__(
        self,
        dia_ips,
        message="DIA IPs retreived from Netbox overlap with an existing network object name in the firewall",
    ):
        self.dia_ips = dia_ips
        self.message = message
        super().__init__(self.dia_ips, self.message)


def check_ip_overlap(network_group_ips: list[str], dia_ips: list[str]):
    """Compare a set of IPs against a set of IPs from a network group to see if the existing group contains the IPs. Return True if there's an overlap. We'll use this to gate actually
    sending a put request to the FMC for changing the network group."""
    group_set = set(network_group_ips)
    dia_set = set(dia_ips)
    group_set.intersection_update(dia_set)
    if bool(group_set):
        raise IPOverlapWarning(dia_set)


def validate_site_code(site_code: str):
    """Check to see if the site code is exactly five letters, no other characters, and returns true if it validates."""
    logger.debug(f"Validating the site code: {site_code}")
    if site_code.isalpha() and len(site_code) == 5:
        logger.debug(f"Site code valid: {site_code}")
        return
    else:
        logger.error(f"Site code invalid: {site_code}")
        raise SiteCodeError(site_code, message="Provided site sode is not valid")


def validate_ip(ip: str) -> bool:
    """Input validation for IP addresses"""
    try:
        valid_addr = ipaddress.ip_address(ip)
    except ValueError:
        raise

    if valid_addr:
        return True
    else:
        return False