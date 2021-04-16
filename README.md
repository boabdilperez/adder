## Still to-do
* **SROS** Successfully connect to router. Config needed on box to enable netconf? Skip netconf and just use netmiko?
* **SM** Come up with SOME idea to modify salt master firewall gracefully.
* **FMC** Need to re-design fmc.update_network_group to send a correctly formatted PUT request. There is no way to simply append new objects to the ObjGrp, it must be completely defined in JSON with the necessary changes added to the entire list of existing objects and literals.
* **FMC** Extra error checking around the FMC POST/PUT calls to ensure the correct network objects have been created and added to network groups
* **FMC** Examine and simplify the code around deploying the FMC to the DFW and ORD FTDs. 
* **FMC** Implement rollback for FMC deploy, since native rollback functionality doesn't exist.