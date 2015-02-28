import threading
import subprocess
import schedule
import config
from log import get_logger

logger = get_logger(__name__)

class LightFunctor():

    def __init__(self, on=True):
        self._on = on

    def __call__(self):
        try:
            logger.info("turning lights %r" %('on' if self._on else 'off'))
            for i in range(1 + config.x10_retries):
                logger.debug("light operation attempt %d" %i)
                args = ['sudo',
                        '/usr/local/bin/heyu',
                        'f' + ('on' if self._on else 'off'),
                        config.x10_light_code]
                subprocess.call(args)
        except Exception as e:
            logger.exception('encountered while calling heyu:  %r'%e)

class LightScheduler(threading.Thread):

    def __init__(self):
        super().__init__()
        self._scheduler = schedule.Scheduler()
        self._on = LightFunctor()
        self._off = LightFunctor(False)
        for t in config.lights_on_times:
            if not self._is_valid_time_string(t):
                raise ValueError('invalid time specification for on time:  %r' %t)
        for t in config.lights_off_times:
            if not self._is_valid_time_string(t):
                raise ValueError('invalid time specification for off time:  %r' %t)
        for t in config.lights_on_times:
            self._scheduler.every().day.at(t).do(self._on)
            logger.info("scheduling light on time %r"%t)
        for t in config.lights_off_times:
            self._scheduler.every().day.at(t).do(self._off)
            logger.info("scheduling light off time %r"%t)
        self.daemon = True

    @staticmethod
    def _is_valid_time_string(time_str):
        if len(time_str) not in [4, 5]:
            return False
        if time_str[-3] != ':':
            return False
        if not time_str.replace(':', '').isdigit():
            return False
        return True

    def run(self):
        logger.info("light scheduler starting up")
        while True:
            self._scheduler.run_pending()

