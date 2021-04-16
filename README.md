## Still to-do
* **SROS** Successfully connect to router. Config needed on box to enable netconf? Skip netconf and just use netmiko?
* **SM** Come up with SOME idea to modify salt master firewall gracefully.
* **FMC** All the necessary API calls are built into the AdderFMC class now, we just need to wrap it up into some application niceties and test.
* **FMC** Extra error checking around the FMC POST/PUT calls to ensure the correct network objects have been created and added to network groups