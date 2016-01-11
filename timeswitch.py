#!/usr/bin/env python
"""Usage:
  test.py --config=<file> --mqtt-host=<host> --mqtt-topic=<topic> [--mqtt-password=<password>] [--mqtt-user=<user>]
  test.py -h | --help | --version
"""

from docopt import docopt

import time
from datetime import date
from pprint import pprint
import signal
import sys
import yaml
import os
import logging
import schedule
import json
import paho.mqtt.publish as publish

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

logger = logging.getLogger(os.path.basename(__file__))
logger.debug('Starting...')


def shSigInt(signal, frame):
    logger.info("CTRL+C detected, exiting.")
    sys.exit(0)


class Socket(object):
    """Class to represent a socket, storing the on and off times and the name"""

    def __init__(self, **socket):

        self.name = socket.get('name')
        self.onTimes = socket.get('on')
        self.offTimes = socket.get('off')

        logger.debug("new socket object for name=%s" % self.name)


class Config(object):
    """Class to represent the configuration file"""

    def __init__(self):

        self.sockets = []
        self.filePath = None
        self.file = None
        self.yaml = None

        logger.debug("Creating a new config object")

    def load(self, path):
        """Load and parse the YAML config file"""

        logger.debug("Config file path=%s" % path)

        self.filePath = path
        self._parseYaml()

        logger.info("Found %d sockets in config" % len(self.yaml))

        for socket in self.yaml:
            self.sockets.append(Socket(**socket))

    def _loadConfig(self):
        """Private method to actually handle the loading of the file"""

        logger.info("Loading config from %s" % self.filePath)
        self.file = open(self.filePath, 'r')

    def _parseYaml(self):
        """Private metod to parse the yaml"""

        self._loadConfig()

        logger.debug("Parsing YAML")

        try:
            self.yaml = yaml.load(self.file, Loader=yaml.BaseLoader)
        except yaml.YAMLError as e:
            logger.error("Invalid YAML")


class MQTT(object):
    """ Simple class to represent our connection to MQTT"""

    def __init__(self):
        """Intentionally simple constructor"""
        self.topic = None
        self.options = {}

    def config(self, topic, host, username=None, password=None):
        """Sets the configuration options for the MQTT connection,
           authetication is optional"""

        self.topic = topic

        self.options = {'hostname': host}

        if username is not None and password is not None:
            logging.debug("connected to MQTT with authentication")
            self.options['auth'] = {'username': username, 'password': password}
        else:
            logging.debug("connected to MQTT without authentication")

    def send_message(self, payload):
        """Actually send the message defined in payload to MQTT"""

        kwargs = self.options
        kwargs['payload'] = payload

        logger.debug("mqtt args=%s" % kwargs)
        logger.debug("mqtt topic=%s" % self.topic)

        publish.single(self.topic, **kwargs)


def sendCommand(socket, action):
    """function to actually send a message off to MQTT"""

    logger.info("turning socket=%s %s" % (socket, action))
    payload = json.dumps({"switch": socket, "action": action})
    mqtt.send_message(payload)


def setSchedules(name, action, times):
    """For all the times defined in 'times' set a schedule"""

    for time in times:
        logger.info("Setting job for %s %s at %s" % (name, action, time))
        schedule.every().day.at(time).do(sendCommand, name, action)


def createSchedules(sockets):
    """Create all of the on and off schedules for all the sockets"""

    # Clear the existing schedule, because in cases where a switch on or
    # off time is defined as sunset or similar, the time will change daily
    logger.debug("Clearing existing schedule")
    schedule.clear()

    logger.info("Creating schedule")
    for socket in sockets:
        setSchedules(socket.name, 'on', socket.onTimes)
        setSchedules(socket.name, 'off', socket.offTimes)


def newDay(day):
    """Check to see if we are in a new day"""

    newDay = date.today().day

    if day != newDay:
        logger.debug(
            "Detected date change, old date=%d new date=%d" % (day, newDay))
        day = newDay
        logger.info("New day, clearing schedule")
        createSchedules(config.sockets)

    return day


if __name__ == '__main__':

    # Nicer handling of CTRL-C
    signal.signal(signal.SIGINT, shSigInt)

    arguments = docopt(__doc__)

    # Create a MQTT object to represet out connection to the broker
    mqtt = MQTT()
    mqtt.config(arguments['--mqtt-topic'],
                arguments['--mqtt-host'],
                arguments.get('--mqtt-user'),
                arguments.get('--mqtt-password'))

    lastDay = date.today().day
    logger.debug("Detected todays date as %d" % lastDay)

    config = Config()
    config.load(arguments['--config'])

    createSchedules(config.sockets)

    # Main loop
    while True:
        lastDay = newDay(lastDay)
        schedule.run_pending()
        time.sleep(1)
