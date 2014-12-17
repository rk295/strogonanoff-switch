#!/usr/bin/python -u
# -u to unbuffer stdout, plays nicer with supervisor

import sys
import json
import datetime
import paho.mqtt.client as paho
from subprocess import Popen, PIPE

""" hostname and topic of MQTT """
hostname = 'trin'
topic = 'foo/bar'

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

    cmd = ["/usr/bin/sudo", "/usr/local/bin/strogonanoff_sender.py", "-c", str(channel), "-b", str(button), action]
    try:
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except Exception, e:
        print("error:  %s" % e.strerror)
        print("failed to run command: \"%s\"" % ' '.join(command))
    


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

    if data['switch'] not in switches:
        print "%s switch (%s) not found" % (timestamp, data['switch'])
        return False

    action  = data['action']
    channel = switches[data['switch']]['channel']
    button  = switches[data['switch']]['button']
    print "%s switch=%s channel=%s button=%s action=%s" % (timestamp, data['switch'], channel, button, action)

    runcmd(channel, button, action)


if __name__ == "__main__":

    mqttc = paho.Client()
    mqttc.on_message = on_message
    mqttc.connect(hostname)
    mqttc.subscribe(topic)

    while mqttc.loop() == 0:
        pass
