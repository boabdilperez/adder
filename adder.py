from __future__ import annotations
import logging
import logging.config
import yaml
from utils import *
from fmc import AdderFMC
from netbox import AdderNetbox
from pprint import pprint
import argparse

# Logging config
with open("logging.yaml", "r") as f:
    try:
        contents = yaml.safe_load(f)
    except yaml.YAMLError:
        raise
    logging.config.dictConfig(contents)

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

# Establish API connection object to FMC
fmc = AdderFMC()
logger.debug("Connection to FMC established")
# Establish API connection object to Netbox
nb = AdderNetbox()
logger.debug("Connection to Netbox established")

# Validate input; raise an exception if the site code provided is anything other than five letters.
if validate_site_code(args.site):
    dia_ips = nb.get_dia_ip_addrs(site_code=args.site.lower())
    logger.debug(f"DIA IPs obtained: {dia_ips}")

    existing_netgrp_ips = fmc.get_netgrp_ips()
    logger.debug("Grabbed list of IPs from FMC")

    overlap = check_ip_overlap(existing_netgrp_ips, dia_ips)
    logger.debug("Checking IP overlap")
else:
    raise SiteCodeError(args.site)
