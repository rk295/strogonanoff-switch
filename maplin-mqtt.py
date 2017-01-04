#!/usr/bin/python -u
# -u to unbuffer stdout, plays nicer with supervisor

import sys
import json
import time
import os
import logging
import paho.mqtt.client as paho
from subprocess import Popen, PIPE

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


def runcmd(channel, button, action):
    """Does the grunt work of calling strogonanoff_sender.py

    Builds an array of strings to pass to Popen. Currently needs NOPASSWD sudo
    access to interact with /dev/mem.
    """

    sleep_time = 2
    loops = 2

    cmd = ["/usr/bin/sudo", "/usr/local/bin/strogonanoff_sender.py",
           "-c", str(channel), "-b", str(button), action]
    try:
        for i in range(loops):
            logging.debug("running channel=%s button=%s action=%s" %
                          (str(channel), str(button), action))
            logging.debug("running cmd=%s" % cmd)
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            logging.debug("sleeping %d" % sleep_time)
            time.sleep(sleep_time)
    except Exception as e:
        logging.error("error:  %s" % e.strerror)
        logging.error("failed to run command: \"%s\"" % ' '.join(command))


def on_message(client, userdata, message):
    """Called whenever a message is received.

    Tries to parse the message as valid json and if successful will
    try to find the switch mentioned in the json in the global lookup
    table 'switches' (defined at the top). If the switch is found it
    will call runcmd to actually do the work of turning the switch
    on or off.
    """

    if switches is None:
        logging.debug("not configured yet, ignoring request")
        return False

    try:
        data = json.loads(message.payload)
    except:
        logging.debug("failed to parse json. message=%s" % message.payload)
        return False

    name = data.get('switch')
    action = data.get('action')
    source = data.get('source')

    # Only 'on' and 'off' are supported
    if action != "on" and action != "off":
        logging.debug("action (%s) is not valid" % action)
        return False

    if name in switches['rooms']:
        channel = switches['rooms'][name]['channel']
        button = switches['rooms'][name]['button']

        logging.debug("switch=%s channel=%s button=%s action=%s source=%s" %
                      (name, channel, button, action, source))

        runcmd(channel, button, action)

    elif name in switches['scenes']:
        logging.debug("Handling scene=%s" % name)
        switch_list = switches['scenes'][name]

        for switch in switch_list:

            channel = switches['rooms'][switch]['channel']
            button = switches['rooms'][switch]['button']

            logging.debug("switch=%s channel=%s button=%s action=%s source=%s scene=%s" %
                          (switch, channel, button, action, source, name))
            runcmd(channel, button, action)
    else:
        # if it isn't in rooms or scenes it isn't valid, so return
        logging.debug("%s not found in switches or scenes" % switch_name)
        return False


def on_config(client, userdata, message):

    global switches

    try:
        logging.debug("parsing json. message=%s" % message.payload)
        switches = json.loads(message.payload)
    except:
        logging.debug("failed to parse json. message=%s" % message.payload)

        return False

    logging.debug("configured correctly")


def on_connect(client, userdata, rc):
    logging.debug("connected with result code=%s " % str(rc))


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
