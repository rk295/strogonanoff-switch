#!/usr/bin/python -u
# -u to unbuffer stdout, plays nicer with supervisor

import sys
import json
import time
import os
import datetime
import paho.mqtt.client as paho
from subprocess import Popen, PIPE

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

    sleep_time = 1
    loops = 2
    timestamp = datetime.datetime.now()

    cmd = ["/usr/bin/sudo", "/usr/local/bin/strogonanoff_sender.py",
           "-c", str(channel), "-b", str(button), action]
    try:
        for i in range(loops):
            print "%s running channel=%s button=%s action=%s" % (timestamp, str(channel), str(button), action)
            print "%s running cmd=%s" % (timestamp, cmd)
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            print "%s sleeping %d" % (timestamp, sleep_time)
            time.sleep(sleep_time)
    except Exception as e:
        print("%s error:  %s" % (timestamp, e.strerror))
        print("%s failed to run command: \"%s\"" %
              (timestamp, ' '.join(command)))


def on_message(client, userdata, message):
    """Called whenever a message is received. 

    Tries to parse the message as valid json and if successful will
    try to find the switch mentioned in the json in the global lookup
    table 'switches' (defined at the top). If the switch is found it
    will call runcmd to actually do the work of turning the switch 
    on or off.
    """

    timestamp = datetime.datetime.now()

    if switches is None:
        print "%s not configured yet, ignoring request" % (timestamp)
        return False

    try:
        data = json.loads(message.payload)
    except:
        print "%s failed to parse json. message=%s" % (timestamp, message.payload)
        return False

    # Check if either of the two valid strings are in the message
    # Changing this to only accept messages of the format:
    # '{ "switch": "Sofa","action": "off"}'

    if data['switch'] not in switches:
        print "%s switch (%s) not found" % (timestamp, data['switch'])
        return False

    if data['action'] != "on" and data['action'] != "off":
        print "%s action (%s) is not valid" % (timestamp, data['action'])
        return False

    action = data['action']
    channel = switches[data['switch']]['channel']
    button = switches[data['switch']]['button']

    print "%s switch=%s channel=%s button=%s action=%s" % (timestamp, data['switch'], channel, button, action)

    runcmd(channel, button, action)


def on_config(client, userdata, message):

    global switches

    timestamp = datetime.datetime.now()
    print "%s doing some config stuff...." % (timestamp)

    try:
        print "%s parsing json. message=%s" % (timestamp, message.payload)
        data = json.loads(message.payload)
    except:
        print "%s failed to parse json. message=%s" % (timestamp, message.payload)

        return False

    switches = data['rooms']
    print "%s configured correctly" % timestamp


def on_connect(client, userdata, rc):
    timestamp = datetime.datetime.now()
    print "%s connected with result code=%s " % (timestamp, str(rc))


if __name__ == "__main__":

    timestamp = datetime.datetime.now()

    # Bit hacky, making this global. But you know ;)
    switches = None

    mqttc = paho.Client()
    mqttc.message_callback_add(topic_toggle, on_message)
    mqttc.message_callback_add(topic_switches, on_config)

    mqttc.on_connect = on_connect
    if username is not None and password is not None:
        print "%s connected to MQTT with authentication" % timestamp
        mqttc.username_pw_set(username, password)
    else:
        print "%s connected to MQTT without authentication" % timestamp

    try:
        mqttc.connect(hostname)
    except Exception as e:
        print "%s failed to connect: %s" % (timestamp, e)

    print "%s subscribing to topic: %s" % (timestamp, topic_wildcard)
    mqttc.subscribe(topic_wildcard)

    while mqttc.loop() == 0:
        pass
