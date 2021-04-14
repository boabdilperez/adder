from __future__ import annotations
from utils import *
from fmc import AdderFMC
from netbox import AdderNetbox
from pprint import pprint
import argparse
import logging


# Logging enable
logger = logging.getLogger(__name__)

# Parser config
parser = argparse.ArgumentParser(
    description="Adds DIA IP addresses from Netbox into the Cisco Firewalls and SROS routers"
)
parser.add_argument("site", help="The five letter site code you are trying to deploy")
parser.add_argument(
    "-d",
    "--deploy",
    help="Push pending changes from the FMC to the FTDs",
    action="store_true",
)
args = parser.parse_args()


# Some default values
dia_ips = []
existing_netgrp_ips = []
overlap = True
r = None

# Establish API connection objects to FMC and Netbox
fmc = AdderFMC()
logging.debug("Connection to FMC established")
nb = AdderNetbox()
logging.debug("Connection to Netbox established")

# Validate input; raise an exception if the site code provided is anything other than five letters.
if validate_site_code(args.site):
    dia_ips = nb.get_dia_ip_addrs(site_code=args.site.lower())
    existing_netgrp_ips = fmc.get_netgrp_ips()
    overlap = check_ip_overlap(existing_netgrp_ips, dia_ips)
else:
    raise SiteCodeError(args.site)

# If the input validates, go ahead and create the network objects, then push them into the DIA object group.
if not overlap:
    new_objects = fmc.create_network_objects(dia_ips)
    r = fmc.update_network_group(new_objects)

# This block is kinda just for testing and debugging for now.
if r.status_code >= 200 and r.status_code <= 299:
    print("Object Group is updated with new site DIA IPs")
    pprint(r.json()["items"])
# If the FMC comes back with an HTTP status code that indicates anything other than success, we raise an error so the tech can investigate.
else:
    raise SomethingBroke(
        r.status_code,
        message="Received Non-200 status code from FMC when attempting to update DIA object group",
    )
