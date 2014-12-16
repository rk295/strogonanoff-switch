# Maplins switch

Some of the code I've hacked together while playing with the [Maplin remote](http://www.maplin.co.uk/p/remote-controlled-mains-sockets-5-pack-n38hn) 
switches and my [Raspberry Pi](http://www.raspberrypi.org/).

## switch.py

This is a simple wrapper script to [Raspberry Strogonanoff](https://github.com/dmcg/raspberry-strogonanoff) it allows me to (for example) say things like:

```
% switch.py -s tank -a on
```

Which is nicer than having to remember the channel and button numbers. It also runs the sudo for you.

## maplin-mqtt.py

Another simple wrapper which connects to a mqtt broker and subscribes to a specific topic. Then it sits there looking for messages of the format:

```
'{"action": "off", "switch": "spareroom"}'
```

This is intended to make it easier to communicate with the Pi from remote machines. To test this you can use mosquitto_sub:

```
% mosquitto_pub -h trin -t foo/bar -m '{"action": "off", "switch": "spareroom"}'
```

Which should result in something like the following being printed on stdout of the maplin-mqtt.py script:

```
2014-12-16 22:22:10.149430 action=off channel=3 button=1
```

And you never know, channel 3, button 1 ***might*** have just turned off :)
