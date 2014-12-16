#!/usr/bin/env python
import argparse
import sys
from subprocess import Popen, PIPE

switches = { 
            'bookshelf': { 'channel' : 4, 'button'  : 1 },
            'tank':      { 'channel' : 4, 'button'  : 2 },
            'sofa':      { 'channel' : 4, 'button'  : 3 },
            'outside':   { 'channel' : 4, 'button'  : 4 },
            'spareroom': { 'channel' : 3, 'button'  : 1 },
            'all' : True
           }

names = [ i for i in switches ]

def runcmd(channel, button, action):

    cmd = ["/usr/bin/sudo", "/usr/local/bin/strogonanoff_sender.py", "-c", str(channel), "-b", str(button), action]

    try:
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except Exception, e:
        print("Error:  %s" % e.strerror)
        print("Failed to run command: \"%s\"" % ' '.join(command))
        sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--switch', required=True, choices=names)
parser.add_argument('-a', '--action', required=True, choices=['on', 'off'])
args = parser.parse_args()

if args.switch == 'all':
    for key in switches:
        if key == 'all': continue
        print "Turning %s %s" % (key, args.action)
        runcmd(switches[key]['channel'], switches[key]['button'], args.action)
else:
    print "Turning %s %s" % (args.switch, args.action)
    runcmd(switches[args.switch]['channel'], switches[args.switch]['button'], args.action)
