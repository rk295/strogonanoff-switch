# Maplins switch

Some of the code I've hacked together while playing with the [Maplin remote](http://www.maplin.co.uk/p/remote-controlled-mains-sockets-5-pack-n38hn)
switches and my [Raspberry Pi](http://www.raspberrypi.org/).

## maplin-mqtt.py

This is the main script, it is designed to connect to MQTT and wait for messages requesting a switch is turned on or off. It is designed to configure itself to know about all possible switches. It does this by connecting to a topic on MQTT, where it expects to find a JSON document which defines all switches. The format of that JSON document should be as shown below:

```
{
    "rooms": {
        "Tank": {
            "channel": 4,
            "button": 2
        },
        "Living Room": {
            "channel": 4,
            "button": 1
        }
}
```

It can contain as many switches as you like.

The format of messages it expects to receive is:

```
'{"action": "off", "switch": "spareroom"}'
```

The value of `switch` must match one of the rooms defined in the configuration JSON document.

The script is designed to be run as a daemon, from [supervisorD](http://supervisord.org/) or something similar, as a result it logs to standard out, expecting something else to rotate those logs.

### Configuration

Takes the following mandatory environment variables:

* `MQTT_HOST` Host to connect to
* `MQTT_TOPIC` MQTT the base topic to subscribe to, see note below.

And also takes the following optional variables

* `MQTT_USERNAME` MQTT Username for the connection
* `MQTT_PASSWORD` MQTT Password for the connection

#### MQTT Topic note

The script actually uses two topics on the broker, as a result, the topic defined in the `MQTT_TOPIC` environment variable is actually the `base` topic (which must end in a trailing forward slash). It then connects to two topics under that:

* `MQTT_TOPIC/switches` - This is the topic where it expects to find the configuration JSON.
* `MQTT_TOPIC/toggle` - This is the topic where it listens for requests to turn switches on or off.
