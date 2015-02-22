import time
import serial
import threading
import config
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
        while '\n' in input:
            split_point = input.find('\n')
            token = input[:split_point]
            if token[0] == 'T':
                self.temperature = float(token[2:])
                logger.debug("measured temperature:  %r"%self.temperature)
            if token[0] == 'P':
                self.ph = float(token[2:])
                logger.debug("measured ph:  %r"%self.ph)
            input = input[split_point + 1:]
        return input

    def run(self):
        try:
            input = ''
            stop = False
            while not stop:
                next = self.ard.readline().decode('UTF8')
                logger.debug("serial raw read %r"%next)
                input = input + next
                input = self._parse_input(input)
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

