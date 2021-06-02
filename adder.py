#!/usr/bin/env python3
from __future__ import annotations
import logging
import requests
import yaml
import logging.config as log_config
from utils import *
from devices.fmc import AdderFMC
from devices.netbox import AdderNetbox
from pprint import pprint
import argparse

# Logging config
with open("./log/log.conf", "r") as f:
    try:
        contents = yaml.safe_load(f)
    except yaml.YAMLError:
        raise
    log_config.dictConfig(contents)

# Logging enable
logger = logging.getLogger(__name__)


def deploy_fmc(fmc: AdderFMC) -> tuple[requests.Response, requests.Response]:
    """If the --deploy flag is set, we will attempt to deploy changes to the ORD and DFW FTDs."""
    dfw_response = fmc.deploy_to_device(fmc.dfw_ftd)
    ord_response = fmc.deploy_to_device(fmc.ord_ftd)
    return (dfw_response, ord_response)


def parse_arguments() -> argparse.Namespace:
    """Here we parse all our arguments, get the values and return them so we can pass into the main func"""
    parser = argparse.ArgumentParser(
        description="Adds DIA IP addresses from Netbox into the Cisco Firewalls and SROS routers"
    )
    deploy_rollback_group = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "--target",
        type=str,
        help="The name of the object group you want to update. Defaults to 'Store-DIA-PROD'",
    )
    parser.add_argument(
        "--site",
        type=str,
        help="The five letter site code you are trying to deploy. Sites must be built in netbox for this to work. Can add multiple space-delimited site codes",
        nargs="+",
    )
    parser.add_argument(
        "--ip",
        type=str,
        help="Use this to manually specify the IP addresses you are trying to apply to the firewalls.",
        nargs="+",
    )
    deploy_rollback_group.add_argument(
        "--deploy",
        help="Push pending changes from the FMC to the FTDs",
        action="store_true",
    )
    deploy_rollback_group.add_argument(
        "--rollback",
        help="Rolls back the most recent change made to the FTD's DIA object-group. Cannot mix with --deploy. Not working.",
        action="store_true",
    )

    return parser.parse_args()


def populate_site(
    nb: AdderNetbox, fmc: AdderFMC, site_codes: list[str], target: str = None
) -> None:
    """Takes a list of site codes and adds the corresponding IP addresses to the firewall"""
    new_sites = []
    bad_sites = []
    new_ips = []
    existing_ips = []
    bad_ips = []

    if target == None:
        obj_group = fmc.get_netgroup_uuid("Store-DIA-PROD")
    else:
        obj_group = fmc.get_netgroup_uuid(target)

    for site_code in site_codes:
        try:
            validate_site_code(site_code)
        except SiteCodeError:
            logger.warning(f"Site Code Invalid: {site_code}")
            bad_sites.append(site_code)
        else:
            logger.debug(f"Site Code to be added: {site_code}")
            new_sites.append(site_code)

    for site_code in new_sites:
        dia_ips = nb.get_dia_ip_addrs(site_code)
        for ip in dia_ips:
            logger.debug(f"Validating IP {ip} from site {site_code}")
            try:
                validate_ip(ip)
            except InvalidIPArgumentError:
                bad_ips.append(ip)
                continue

            try:
                fmc.check_host_exists(ip)
            except HostAlreadyExistsWarning:
                existing_ips.append(ip)
            else:
                new_ips.append(ip)

    if len(existing_ips) >= 1:
        for ip in existing_ips:
            fmc.update_group_from_existing_host(obj_group, ip)

    if len(new_ips) >= 1:
        new_objects = fmc.create_host_objects(new_ips)
        fmc.update_object_group(obj_group, new_objects)
        logger.debug(
            f"\nNewly added sites: {site_codes}\nNewly Created IPs from sites: {new_ips}\nAlready Existing IPs from sites: {existing_ips}\nInvalid IPs: {bad_ips}. Check netbox!\n"
        )
    print(
        f"\nNewly added sites: {site_codes}\nNewly Created IPs from sites: {new_ips}\nAlready Existing IPs from sites: {existing_ips}\nInvalid IPs: {bad_ips}. Check netbox!\n"
    )


def populate_from_single(fmc: AdderFMC, arg_ips: list, target: str = None) -> None:
    """Skip the netbox! This lets you enter a list of IPs into adder and have them added to the FMC"""
    existing_ips = []
    new_ips = []
    bad_ips = []

    if target == None:
        obj_group = fmc.get_netgroup_uuid("Store-DIA-PROD")
    else:
        obj_group = fmc.get_netgroup_uuid(target)

    for ip in arg_ips:
        logger.debug(f"Validating IP passed to adder: {ip}")

        try:
            _ = validate_ip(ip)
        except InvalidIPArgumentError:
            bad_ips.append(ip)
            continue

        try:
            fmc.check_host_exists(ip)
        except HostAlreadyExistsWarning:
            existing_ips.append(ip)
        else:
            new_ips.append(ip)

    if len(existing_ips) >= 1:
        for ip in existing_ips:
            fmc.update_group_from_existing_host(obj_group, ip)

    if len(new_ips) >= 1:
        new_objects = fmc.create_host_objects(new_ips)
        fmc.update_object_group(obj_group, new_objects)
        logger.debug(
            f"Newly Created IPs: {new_ips}\nAlready Existing IPs: {existing_ips}\nInvalid IPs: {bad_ips}"
        )
    print(
        f"\nNewly Created IPs: {new_ips}\nAlready Existing IPs: {existing_ips}\nInvalid IPs: {bad_ips}\n"
    )


def rollback_fmc(fmc: AdderFMC) -> None:
    print("MOCK FUNC: rollback_fmc()")


def main(args) -> None:
    # Establish API connection object to FMC
    fmc = AdderFMC()

    # Establish API connection object to Netbox
    nb = AdderNetbox()

    deployable_devices = fmc.get_deployable_devices()
    for device in deployable_devices.json()["items"]:
        if device["name"] == fmc.ord_ftd:
            input(
                "The ORD FTD already has pending changes. ENTER to proceed, Ctrl-C to exit."
            )
            break

    for device in deployable_devices.json()["items"]:
        if device["name"] == fmc.dfw_ftd:
            input(
                "The DFW FTD already has pending changes. ENTER to proceed, Ctrl-C to exit."
            )
            break

    if args.site is not None:
        if args.target is not None:
            populate_site(nb, fmc, args.site, target=args.target)
        else:
            populate_site(nb, fmc, args.site)

    if args.ip is not None:
        populate_from_single(fmc, args.ip, target=args.target)
        if args.deploy:
            deploy_fmc(fmc)

    if args.deploy:
        deploy_fmc(fmc)
    elif args.rollback:
        rollback_fmc(fmc)


if __name__ == "__main__":
    args = parse_arguments()
    logger.debug(f"Arguments Passed: {args}")
    main(args)