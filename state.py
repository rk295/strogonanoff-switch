#!/usr/bin/python -u
# -u to unbuffer stdout, plays nicer with supervisor

import sys
import json
import time
import os
import logging
import paho.mqtt.client as paho
import paho.mqtt.publish as publish
from subprocess import Popen, PIPE
from time import gmtime, strftime

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

logger = logging.getLogger(os.path.basename(__file__))

logger.debug('Starting...')

""" hostname and topic of MQTT """
hostname = os.getenv('MQTT_HOST')
topic_base = os.getenv('MQTT_TOPIC')
topic_wildcard = topic_base + "#"
topic_toggle = topic_base + 'toggle'
topic_switches = topic_base + 'switches'
""" Optional username and password for MQTT """
username = os.getenv('MQTT_USERNAME', None)
password = os.getenv('MQTT_PASSWORD', None)

mqtt_options = {'hostname': hostname}

if username is not None and password is not None:
    logging.debug("connected to MQTT with authentication")
    mqtt_options['auth'] = {'username': username, 'password': password}
else:
    logging.debug("connected to MQTT without authentication")


def on_message(client, userdata, message):

    if switches is None:
        logging.debug("not configured yet, ignoring request")
        return False

    try:
        data = json.loads(message.payload)
    except:
        logging.debug("failed to parse json. message=%s" % message.payload)
        return False

    if data['switch'] not in switches['rooms']:
        logging.debug("switch (%s) not found" % data['switch'])
        return False

    if data['action'] != "on" and data['action'] != "off":
        logging.debug("action (%s) is not valid" % data['action'])
        return False

    switch = data['switch']
    action = data['action']

    logging.debug("switch=%s action=%s" % (data['switch'], action))

    update_state(switch, action)


def on_config(client, userdata, message):

    global switches

    try:
        logging.debug("parsing json. message=%s" % message.payload)
        data = json.loads(message.payload)
    except:
        logging.debug("failed to parse json. message=%s" % message.payload)

        return False

    switches = data
    logging.debug("configured correctly")


def on_connect(client, userdata, rc):
    logging.debug("connected with result code=%s " % str(rc))


def update_state(switch, action):
    logging.debug("Updating state with %s turned %s" % (switch, action))

    switches['rooms'][switch]['state'] = action
    switches['updated']['by'] = 'state.py'
    time_stamp = strftime("%a %b %d %H:%M:%S %Z %Y", gmtime())
    switches['updated']['at'] = time_stamp

    new_config = dict()
    new_config = switches

    mqtt_options['retain'] = True

    mqtt_options['payload'] = json.dumps(new_config)
    # logger.debug("mqtt args=%s" % mqtt_options)
    # logger.debug("mqtt topic=%s" % topic_switches)
    publish.single(topic_switches, **mqtt_options)


if __name__ == "__main__":

    # Bit hacky, making this global. But you know ;)
    switches = None

    mqttc = paho.Client()
    mqttc.message_callback_add(topic_toggle, on_message)
    mqttc.message_callback_add(topic_switches, on_config)

    mqttc.on_connect = on_connect
    if username is not None and password is not None:
        logging.debug("connected to MQTT with authentication")
        mqttc.username_pw_set(username, password)
    else:
        logging.debug("connected to MQTT without authentication")

    try:
        mqttc.connect(hostname)
    except Exception as e:
        logging.debug("failed to connect: %s" % e)

    logging.debug("subscribing to topic: %s" % topic_wildcard)
    mqttc.subscribe(topic_wildcard)

    while mqttc.loop() == 0:
        pass
