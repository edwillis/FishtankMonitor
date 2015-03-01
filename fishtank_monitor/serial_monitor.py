import time
import serial
import threading
import config
import json
from log import get_logger

logger = get_logger(__name__)


class SerialMonitor(threading.Thread):

    def __init__(self, serial_device):
        super().__init__()
        self.ph = None
        self.temperature = None
        self.started = threading.Event()
        self.serial_device = serial_device
        self.ard = serial.Serial(self.serial_device)
        self.daemon = True

    def write_to_serial(self, json_message):
        logger.info("writing to serial:  %r" %json.dumps(json_message))
        self.ard.writelines([json.dumps(json_message).encode('UTF8')])

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

    @classmethod
    def create_monitor(cls):
        monitor = SerialMonitor(config.serial_device)
        return monitor

    def start_monitor(self):
        logger.info("starting monitor")
        self.start()
        time.sleep(2)
        self.started.set()

