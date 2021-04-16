from __future__ import annotations


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


def check_ip_overlap(network_group_ips: list[str], dia_ips: list[str]) -> bool:
    """Compare a set of IPs against a set of IPs from a network group to see if the existing group contains the IPs. Return True if there's an overlap. We'll use this to gate actually
    sending a put request to the FMC for changing the network group."""
    group_set = set(network_group_ips)
    dia_set = set(dia_ips)
    group_set.intersection_update(dia_set)
    return bool(group_set)


def validate_site_code(site_code: str) -> bool:
    """Check to see if the site code is exactly five letters, no other characters, and returns true if it validates."""
    if site_code.isalpha() and len(site_code) == 5:
        return True
    else:
        return False
