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
topic = os.getenv('MQTT_TOPIC')
""" Optional username and password for MQTT """
username = os.getenv('MQTT_USERNAME', None)
password = os.getenv('MQTT_PASSWORD', None)

""" Master lookup table of friendly names to channel/button"""
switches = { 
            'bookshelf': { 'channel' : 4, 'button'  : 1 },
            'tank':      { 'channel' : 4, 'button'  : 2 },
            'sofa':      { 'channel' : 4, 'button'  : 3 },
            'outside':   { 'channel' : 4, 'button'  : 4 },
            'spareroom': { 'channel' : 3, 'button'  : 1 },
            'all' : True
           }


def runcmd(channel, button, action):

    """Does the grunt work of calling strogonanoff_sender.py

    Builds an array of strings to pass to Popen. Currently needs NOPASSWD sudo 
    access to interact with /dev/mem.
    """

    # TODO: Figure out if a user can be given privs to access /dev/mem

    timestamp = datetime.datetime.now()

    cmd = ["/usr/bin/sudo", "/usr/local/bin/strogonanoff_sender.py", "-c", str(channel), "-b", str(button), action]
    try:
        print "%s running channel=%s button=%s action=%s" % (timestamp, str(channel), str(button), action)
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        print "%s sleeping 2" % timestamp
        time.sleep(2)
        print "%s running channel=%s button=%s action=%s" % (timestamp, str(channel), str(button), action)
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except Exception as e:
        print("%s error:  %s" % (timestamp, e.strerror))
        print("%s failed to run command: \"%s\"" % (timestamp, ' '.join(command)))
    


def on_message(client, userdata, message):
    """Called whenever a message is received. 

    Tries to parse the message as valid json and if successful will
    try to find the switch mentioned in the json in the global lookup
    table 'switches' (defined at the top). If the switch is found it
    will call runcmd to actually do the work of turning the switch 
    on or off.
    """

    timestamp = datetime.datetime.now()

    try:
        data = json.loads(message.payload)
    except:
        print "%s failed to parse json. message=%s" % (timestamp, message.payload)
        return False

    # Check if either of the two valid strings are in the message
    if data.get('switch') and data.get('action'):

        if data['switch'] not in switches:
            print "%s switch (%s) not found" % (timestamp, data['switch'])
            return False

        if data['action'] != "on" and data['action'] != "off":
            print "%s action (%s) is not valid" % (timestamp, data['action'])
            return False

        action  = data['action']
        channel = switches[data['switch']]['channel']
        button  = switches[data['switch']]['button']

        print "%s switch=%s channel=%s button=%s action=%s" % (timestamp, data['switch'], channel, button, action)

    elif data.get('channel') and data.get('button'):

        if data['action'] != "on" and data['action'] != "off":
            print "%s action (%s) is not valid" % (timestamp, data['action'])
            return False

        action  = data['action']
        channel = data['channel']
        button  = data['button']

        print "%s channel=%s button=%s action=%s" % (timestamp, channel, button, action)

    else:
        print "%s failed to parse message=%s" % (timestamp, data)
        
    runcmd(channel, button, action)

    
def on_connect(client, userdata, rc):
    timestamp = datetime.datetime.now()
    print "%s connected with result code=%s " % (timestamp, str(rc))


if __name__ == "__main__":

    timestamp = datetime.datetime.now()

    mqttc = paho.Client()
    mqttc.on_message = on_message
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

    mqttc.subscribe(topic)

    while mqttc.loop() == 0:
        pass
