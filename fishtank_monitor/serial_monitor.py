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

    def _parse_input(self, input):
        if '{' in input and '}' in input and (input.index('{') < input.rfind('}')):
            logger.debug("input is %r" %input)
            message = json.loads(input[input.index('{') : input.rfind('}') + 1])
            logger.message("json is %r" %message)
            if 'temperature' in message and 'ph' in message:
                logger.info("measured temperature:  %r" %message['temperature'])
                logger.info("measured ph:  %r" %message['ph'])
            return message
        return None

    def run(self):
        try:
            stop = False
            # before we read anything, write the analog input pins for
            # ph and temp.  On the other side, read them on startup and
            # periodically check for readability and discard
            while not stop:
                next = self.ard.readline().decode('UTF8')
                if next:
                    logger.info("serial raw read %r"%next)
                    message = self._parse_input(next)
                    if message and 'temperature' in message and 'ph' in message:
                        self.temperature = message['temperature']
                        self.ph = message['ph']
        except Exception as e:
            logger.exception("exception encountered in monitor_serial:  %r" %e)

    @classmethod
    def create_and_start_monitor(cls):
        monitor = SerialMonitor(config.serial_device)
        logger.info("starting monitor")
        monitor.start()
        time.sleep(2)
        monitor.started.set()
        return monitor

