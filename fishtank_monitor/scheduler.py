import threading
import subprocess
import schedule
import config
from datetime import datetime
from dateutil import tz
from log import get_logger

logger = get_logger(__name__)

class LightFunctor():

    def __init__(self, on=True):
        self._on = on

    def __call__(self):
        try:
            logger.info("turning lights %r" %('on' if self._on else 'off'))
            for i in range(1 + config.x10_retries):
                logger.info("light operation attempt %d" %i)
                args = ['sudo',
                        '/usr/local/bin/heyu',
                        'f' + ('on' if self._on else 'off'),
                        config.x10_light_code]
                logger.debug("subprocess args are %r"%args)
                subprocess.call(args)
        except Exception as e:
            logger.exception('encountered while calling heyu:  %r'%e)

class LightScheduler(threading.Thread):

    def __init__(self):
        super().__init__()
        self._scheduler = schedule.Scheduler()
        for t in config.lights_on_times:
            if not self._is_valid_time_string(t):
                raise ValueError('invalid time specification for on time:  %r' %t)
        for t in config.lights_off_times:
            if not self._is_valid_time_string(t):
                raise ValueError('invalid time specification for off time:  %r' %t)
        for t in config.lights_on_times:
            self._scheduler.every().day.at(self._convert_to_utc_time_string(t)).do(LightFunctor())
        for t in config.lights_off_times:
            self._scheduler.every().day.at(self._convert_to_utc_time_string(t)).do(LightFunctor(False))
        self.daemon = True

    @staticmethod
    def _convert_to_utc_time_string(time_str):
        if not LightScheduler._is_valid_time_string(time_str):
            raise ValueError('invalid time specification in _convert_to_utc_time_string:  %r' %time_str)
        dt = datetime.strptime(time_str, '%H:%M')
        # arbitrary - avoid conversion underflow issues
        dt = dt.replace(year = 2015)
        dt = dt.replace(tzinfo = tz.tzlocal())
        dt = dt.astimezone(tz.tzutc())
        return dt.strftime("%H:%M")

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

