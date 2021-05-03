# Welcome to ADDER!

This is an application for automating the addition of firewall rules to the Cisco FMC in preparation for a Gemini deployment.

Details are fed to adder via command-line flags, and the app parses the arguments given, or searches our Netbox SOT, in order to automatically insert the correct IP addresses into the correct access-list entries.

## Usage:

* --site expects an argument of a single five-letter WFM store code. Adder will search netbox for the matching site and add the DIA IP addresses to the firewalls for you. The site must be built in netbox for this to work, since the app is looking for specific interfaces on the WR-1 and WR-2 devices.

* --ip takes one or more host IP addresses, without subnet masks, and attempts to add them to the firewalls. You cannot mix and match this option with the --site option, one or the other must be used.

* --deploy takes no arguments, but when passed to adder will trigger an attempt for the FMC to deploy the updated rules to the ORD and DFW firewalls. If passed in conjunction with IPs or a site name, it will add the new IPs first. If passed to adder with no other arguments, it will simply attempt to deploy whatever pending changes are on the FMC to DFW/ORD.

* --rollback is a special flag for undoing changes to the FMC. It should be mixed with any other options. When passed to adder with no arguments, all available backup files will be presented to the user, marked with timestamps and UUIDs. If a UUID is passed as an argument to the --rollback flag, then the object group identified by that backup file will be completely overwritten by the data in the backup file.

* --target overrides the destination object group for the automated update. By default the "Store-DIA-PROD" object group is the one updated on the FMC. If a string is fed as an argument to --target the app will attempt to find that object group and update it instead.

## Upcoming Capabilities:
* Automatic update of SROS routers
* Automatic update of Salt-Master firewalls