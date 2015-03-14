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
#  Currently bi-directional communications are limited to an initial message
#  to the alamode containing configration details followed by a series of
#  reads from the alamode containing sensor measurements and logs from the
#  alamode that terminates on when the fishtank_monitor is stopped.  All
#  communications are encoded in simple JSON strings.  Logs entries from the
#  alamode are prefixed to distinguish them from the fishtank_monitor logs
#  but are emitted to those logs also.  The SerialMonitor runs in its own
#  thread.
class SerialMonitor(threading.Thread):

    ## The constructor creates the SerialMonitor thread but does not start it
    #
    #  @param serial_device the serial device to read and write to
    def __init__(self, serial_device):
        super().__init__()
        self.ph = None
        self.temperature = None
        self.started = threading.Event()
        self.serial_device = serial_device
        self.ard = serial.Serial(self.serial_device)
        self.daemon = True

    ## Write a specified JSON object to the serial device
    #
    #  Although this class does not enforce this, it is nonetheless the case that
    #  writing to serial can only happen immediately upon startup, at which point
    #  the only communications supported are an endless series of reads from the
    #  alamode.
    #
    #  @todo  This class should ensure that the protocol (write first, then read
    #         forever) is enforced rather than leaving this responsibility to the
    #         client.
    #  @param json_message the JSON messsage to send to the alamode
    def write_to_serial(self, json_message):
        logger.info("writing to serial:  %r" %json.dumps(json_message))
        self.ard.writelines([json.dumps(json_message).encode('UTF8')])

    ## Given a string read from the alamode, construct a JSON object from it
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

    ## Endlessly read from serial and make measurements available to third parties
    #
    #  The run method reads messages from the serial device and sets the sensor
    #  measurements on itself in public members which parties interested in the
    #  most recent observations can read.
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
        except Exception as e:
            logger.exception("exception encountered in monitor_serial:  %r" %e)

    ## Create the SerialMonitor object using config data from the configuration file
    #
    #  @return the SerialMonitor object
    @classmethod
    def create_monitor(cls):
        monitor = SerialMonitor(config.serial_device)
        return monitor

    ## Start ourselves
    def start_monitor(self):
        logger.info("starting monitor")
        self.start()
        time.sleep(2)
        self.started.set()

