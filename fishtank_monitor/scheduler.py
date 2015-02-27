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
        # TODO convert to utc time
        for t in config.lights_on_times:
            self._scheduler.every().day.at(t).do(LightFunctor())
        for t in config.lights_off_times:
            self._scheduler.every().day.at(t).do(LightFunctor(False))
        self.daemon = True

    def run(self):
        logger.info("light scheduler starting up")
        while True:
            self._scheduler.run_pending()

