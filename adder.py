#!/usr/bin/env python

from __future__ import annotations
import logging
import logging.config
import requests
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


def parse_arguments() -> argparse.Namespace:
    """Here we parse all our arguments, get the values and return them so we can pass into the main func"""
    parser = argparse.ArgumentParser(
        description="Adds DIA IP addresses from Netbox into the Cisco Firewalls and SROS routers"
    )
    deploy_rollback_group = parser.add_mutually_exclusive_group()
    group_get_ips = parser.add_mutually_exclusive_group()

    group_get_ips.add_argument(
        "--site",
        type=str,
        help="The five letter site code you are trying to deploy. Site must be built in netbox for this to work.",
    )
    group_get_ips.add_argument(
        "--ip",
        type=str,
        help="Use this to manually specify the IP addresses you are trying to apply to the firewalls. Separate with spaces. Doesn't mix with --site",
        nargs="+",
    )
    deploy_rollback_group.add_argument(
        "--deploy",
        help="Push pending changes from the FMC to the FTDs",
        action="store_true",
    )
    deploy_rollback_group.add_argument(
        "--rollback",
        help="Rolls back the most recent change made to the FTD's DIA object-group. Cannot mix with --deploy",
        action="store_true",
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Identify a specific object-group to modify. Default is Store-DIA-PROD",
        default="Store-DIA-PROD",
    )

    return parser.parse_args()


def populate_site(site_code: str, nb: AdderNetbox, fmc: AdderFMC) -> None:
    """Wrapping up all the logic to get from invocation of the entire app to adding a whole site to the firewalls"""
    # First we do some input validation. Make sure that the argument passed to the function is a five-letter WFM site code.
    try:
        logger.debug(f"Validating the site code: {site_code}")
        validate_site_code(site_code)
    except SiteCodeError as e:
        logger.error(f"Site code invalid: {e}")
        raise

    if site_code == "tests":
        dia_ips = [
            "169.254.100.201",
            "169.254.100.202",
            "169.254.100.203",
            "169.254.100.204",
        ]
        logger.debug(f"Using test list of IPs: {dia_ips}")
    else:
        dia_ips = nb.get_dia_ip_addrs(site_code)
        logger.debug(f"Retrieving Netbox DIA IP addrs: {dia_ips}")

    new_objects = fmc.create_host_objects(dia_ips)
    logger.debug(f"New host objects created: {new_objects}")

    if site_code == "tests":
        dia_prod_objgrp = fmc.get_netgroup_uuid("adder_test")
        logger.debug(f"UUID of object group {site_code}: {dia_prod_objgrp}")
    else:
        dia_prod_objgrp = fmc.get_netgroup_uuid("Store-DIA-PROD")
        logger.debug(f"UUID of object group {site_code}: {dia_prod_objgrp}")

    if dia_prod_objgrp is not None:
        fmc.update_object_group(dia_prod_objgrp, new_objects)
    else:
        raise SomethingBroke(
            dia_prod_objgrp, message="Cannot find Store-DIA-PROD object group."
        )


def deploy_fmc(fmc: AdderFMC) -> tuple[requests.Response, requests.Response]:
    dfw_response = fmc.deploy_to_device("CODFW-FTD")
    ord_response = fmc.deploy_to_device("COORD-FTD")
    return (dfw_response, ord_response)


def deploy_singles(fmc: AdderFMC) -> None:
    print("MOCK FUNC: deploy_singles()")


def rollback_fmc(fmc: AdderFMC) -> None:
    print("MOCK FUNC: rollback_fmc()")


def main(args):
    # Establish API connection object to FMC
    fmc = AdderFMC()
    logger.debug("Connection to FMC established")

    # Establish API connection object to Netbox
    nb = AdderNetbox()
    logger.debug("Connection to Netbox established")

    if args.site:
        populate_site(args.site, nb, fmc)
        if args.deploy:
            rdfw, rord = deploy_fmc(fmc)
            logger.debug(f"{rdfw}\n {rord}")
            return
    elif args.ip:
        deploy_singles(fmc)
        if args.deploy:
            # deploy_fmc(fmc)
            return
    elif args.deploy:
        # deploy_fmc(fmc)
        return
    elif args.rollback:
        # rollback_fmc(fmc)
        return


if __name__ == "__main__":
    args = parse_arguments()
    main(args)