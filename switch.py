#!/usr/bin/env python
import argparse
import sys
from subprocess import Popen, PIPE

switches = { 
            'bookshelf': { 'channel' : 4, 'button'  : 1 },
            'tank':      { 'channel' : 4, 'button'  : 2 },
            'sofa':      { 'channel' : 4, 'button'  : 3 },
            'outside':   { 'channel' : 4, 'button'  : 4 },
            'spareroom': { 'channel' : 3, 'button'  : 1 }
           }

names = [ i for i in switches ]

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--switch', required=True, choices=names)
parser.add_argument('-a', '--action', required=True, choices=['on', 'off'])
args = parser.parse_args()

cmd = ["/usr/bin/sudo", "/usr/local/bin/strogonanoff_sender.py"]
cmd.extend(["-c", str(switches[args.switch]['channel'] ) ] )
cmd.extend(["-b", str(switches[args.switch]['button'] ) ] )
cmd.extend([args.action])

try:
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
except Exception, e:
    print("Error:  %s" % e.strerror)
    print("Failed to run command: \"%s\"" % ' '.join(command))
    sys.exit(1)
