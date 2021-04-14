from configparser import ConfigParser

# Read in configuration data from config.ini
config = ConfigParser()
config.read("adder.conf")

# Set global variables from the config file
SROS_PASS: str = config["sros"]["password"]
SROS_USER: str = config["sros"]["username"]