#!/usr/bin/env python

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
import ephem
import math
import paho.mqtt.publish as publish

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',  # noqa
                    datefmt='%m-%d %H:%M')

logger = logging.getLogger(os.path.basename(__file__))
logger.debug('Starting...')


def shSigInt(signal, frame):
    logger.info("CTRL+C detected, exiting.")
    sys.exit(0)


class Socket(object):

    """Class to represent a socket, storing the on/off times and the name"""

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


class sun(object):

    """Class to represent things like 'sunrise'"""
    TIME_FORMAT = '%H:%M:%S'

    def __init__(self):
        self.radians = lambda d: d * math.pi / 180
        self.local = lambda d: ephem.localtime(d)
        self.sun = ephem.Sun()
        self.obs = ephem.Observer()

        logger.debug("Creating sun object")
        pass

    def config(self, coords):
        self.obs.lat, self.obs.lon = map(self.radians, map(
            float, coords.split(',')))
        logger.debug("Setting coords to:%s" % coords)

    def configured(self):
        """Returns true if this object has been configured"""
        if self.coords is None:
            return False
        else:
            return True

    def _calculate(self, state, date, horizon='0'):
        obs = self.obs
        obs.date = date
        obs.horizon = horizon

        if state == 'rising':
            value = self.local(obs.next_rising(self.sun)).strftime(
                self.TIME_FORMAT)
        elif state == 'setting':
            value = self.local(obs.next_setting(self.sun)).strftime(
                self.TIME_FORMAT)
        else:
            return False

        return value

    def sunrise(self, date=date.today()):
        return self._calculate('rising', date)

    def sunset(self, date=date.today()):
        return self._calculate('setting', date)

    def dusk(self, date=date.today()):
        return self._calculate('setting', date, '-6')

    def dawn(self, date=date.today()):
        return self._calculate('rising', date, '-6')


def sendCommand(socket, action):
    """function to actually send a message off to MQTT"""

    logger.info("turning socket=%s %s" % (socket, action))
    payload = json.dumps({"switch": socket, "action": action})
    mqtt.send_message(payload)


def setSchedules(name, action, times):
    """For all the times defined in 'times' set a schedule"""

    today = date.today()

    for time in times:
        if time == "dawn":
            actual_time = sun_times.dawn(today)
        elif time == "sunrise":
            actual_time = sun_times.sunrise(today)
        elif time == "sunset":
            actual_time = sun_times.sunset(today)
        elif time == "dusk":
            actual_time = sun_times.dusk(today)
        else:
            actual_time = time

        logger.info("Setting job %s %s at %s" % (name, action, actual_time))
        # Slice the actual time here because schedule doesn't like seconds
        schedule.every().day.at(actual_time[:5]).do(sendCommand, name, action)


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

        logger.debug("Dawn: %s" % sun_times.dawn())
        logger.debug("Sunrise: %s" % sun_times.sunrise())
        logger.debug("Sunset: %s" % sun_times.sunset())
        logger.debug("Dusk: %s" % sun_times.dusk())

        logger.info("New day, clearing schedule")
        createSchedules(config.sockets)

    return day


if __name__ == '__main__':

    # Nicer handling of CTRL-C
    signal.signal(signal.SIGINT, shSigInt)

    ts_config = os.getenv('CONFIG')
    mqtt_host = os.getenv('MQTT_HOST')
    mqtt_topic = os.getenv('MQTT_TOPIC')
    """ Optional username and password for MQTT """
    mqtt_user = os.getenv('MQTT_USER', None)
    mqtt_password = os.getenv('MQTT_PASSWORD', None)

    # Optional coodinates, if you want to support 'sunrise' and the like
    # in time schedules.
    coords = os.getenv('COORDS', None)

    sun_times = sun()
    sun_times.config(coords)

    # Create a MQTT object to represet out connection to the broker
    mqtt = MQTT()
    mqtt.config(mqtt_topic,
                mqtt_host,
                mqtt_user,
                mqtt_password)

    today = date.today()
    lastDay = date.today().day
    logger.debug("Detected todays date as %d" % lastDay)

    config = Config()
    config.load(ts_config)

    createSchedules(config.sockets)

    # Main loop
    while True:
        lastDay = newDay(lastDay)
        schedule.run_pending()
        time.sleep(1)
