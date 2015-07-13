## @package serial_monitor
#  Module responsible for communications between the raspberry pi and the alamode
#
#  @author  Ed Willis
#  @copyright Ed Willis, 2015, all rights reserved
#  @license  This software is released into the public domain

import time
import serial
import threading
import config
import json
from log import get_logger

logger = get_logger(__name__)

## The SerialMonitor manages JSON encoded communications with the alamode
#
#  The communications protocol between the Alamode and the Pi starts with the
#  Pi sending the Alamode configuration data (IP address to display, sensor
#  configuration and offsets etc) to the Alamode after which communications
#  are symmetric, with the Alamode sending data of some form (e.g. sensor
#  readings, log entries etc) and the Pi immediately responding with the
#  (possibly updated) configuration data.  This cycle only terminatesc when
#  the fishtank_monitor is stopped.  All communications are encoded in simple
#  JSON strings.  Logs entries from the alamode are prefixed to distinguish
#  them from the fishtank_monitor logs but are emitted to those logs also.
#  The SerialMonitor runs in its own thread.
class SerialMonitor(threading.Thread):

    ## The constructor creates the SerialMonitor thread but does not start it
    #
    #  @param serial_device the serial device to read and write to
    #  @param configuration the arduino configuration json object to send
    def __init__(self, serial_device, configuration):
        super().__init__()
        self.ph = None
        self.temperature = None
        self.started = threading.Event()
        self.serial_device = serial_device
        self.ard = serial.Serial(self.serial_device)
        self.daemon = True
        self.configuration = configuration
        self._write_to_serial(self.configuration)

    ## Set the Alamode configuration object
    #
    #  The Alamode configuration is mutable - the user might have changed
    #  some parameters in the config file and things like the Pi's IP address
    #  are inherently dynamic.  The Pi to Alamode communications is a
    #  bi-directional affair of symmetric messages - one first from the Alamode
    #  followed immediately by a message from the Pi. The message from the Pi
    #  is always simply this configuration.  The only variance from this pattern
    #  of messages is on start-up, when the Pi starts off communications be sending
    #  the configuration, after which the bi-directional messaging proceeds as
    #  described earlier.
    def set_alamode_configuration(self, configuration):
        self.configuration = configuration

    ## Write a specified JSON object to the serial device
    #
    #  @param json_message the JSON messsage to send to the alamode
    def _write_to_serial(self, json_message):
        logger.info("writing to serial:  %r" %json.dumps(json_message))
        self.ard.writelines([json.dumps(json_message).encode('UTF8')])

    ## Given a string read from the Alamode, construct a JSON object from it
    #
    #  The input is parsed and any extraneous characters (prefixes or unexpected
    #  appendices) are discarded.  Sensor readings are assumed to be complete -
    #  that is, when one appears, all sensor readings will appear - but log and
    #  sensor entries can appear together in a message.  Log entries are
    #  immediately send to the fishtank_monitor log with a prefix making them
    #  easily distinguishable.
    #
    #  @input the string read from the serial sevice
    #  @return a JSON object representing the message from the alamode
    def _parse_input(self, input):
        if '{' in input and '}' in input and (input.index('{') < input.rfind('}')):
            logger.debug("input is %r" %input)
            message = json.loads(input[input.index('{') : input.rfind('}') + 1])
            logger.debug("received from alamode json is %r" %message)
            if 'temperature' in message and 'ph' in message:
                logger.info("measured temperature:  %r" %message['temperature'])
                logger.info("measured ph:  %r" %message['ph'])
            if 'log' in message:
                logger.info("ALAMODE:  %s" %message.pop("log"))
            return message
        return None

    ## Manage the Pi to Alamode communications protocol
    #
    #  The run method reads messages from the serial device and sets the sensor
    #  measurements on itself in public members which parties interested in the
    #  most recent observations can read.  Each received message trigger the send
    #  of configuration data back to the Alamode.
    def run(self):
        try:
            stop = False
            while not stop:
                next = self.ard.readline().decode('UTF8')
                if next:
                    logger.debug("serial raw read %r"%next)
                    message = self._parse_input(next)
                    if message and 'temperature' in message and 'ph' in message:
                        self.temperature = message['temperature']
                        self.ph = message['ph']
                        if not self.started.is_set():
                            self.started.set()
                    self._write_to_serial(self.configuration)

        except Exception as e:
            logger.exception("exception encountered in monitor_serial:  %r" %e)

    ## Create the SerialMonitor object using config data from the configuration file
    #
    #  @return the SerialMonitor object
    @classmethod
    def create_monitor(cls, configuration):
        monitor = SerialMonitor(config.serial_device, configuration)
        return monitor

    ## Start ourselves
    def start_monitor(self):
        logger.info("starting monitor")
        self.start()

