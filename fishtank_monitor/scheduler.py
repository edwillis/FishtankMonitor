## @package scheduler
#  Classes collaborating to manage the fishtank lighting
#
#  @author  Ed Willis
#  @copyright Ed Willis, 2015, all rights reserved
#  @license  This software is released into the public domain

import threading
import subprocess
import schedule
import config
from log import get_logger

logger = get_logger(__name__)

## Function object used to turn the fishtank lights on or off via x10
#
#  On instantiation, the functor is configured to be either on or off.
#  When called, the functor uses the heyu binary to set the lights to
#  the indicated state and retries (necessary given the flakey nature
#  of the x10 protocol) the number of times indicated by the user in
#  the configuration file.
class LightFunctor():

    ## The contructor
    #  @param on true, if the function object will turn on the lights,
    #  off otherwise
    def __init__(self, on=True):
        self._on = on

    ## The functor method which turns the lights on or off
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

## The LightScheduler controls the fishtank lights
#
#  The LightScheduler arranges for the fishtank lights to be turned on
#  or off on the schedule specified by the user in the configuration file.
class LightScheduler(threading.Thread):

    ## The constructor builds the functors and calls them as the specified times
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

    ## Parses and validates the configuration file time specifications
    #  @param time_str a string like "18:45,20:15" etc.
    #  @return True, if the time_str was of valid form
    @staticmethod
    def _is_valid_time_string(time_str):
        if len(time_str) not in [4, 5]:
            return False
        if time_str[-3] != ':':
            return False
        if not time_str.replace(':', '').isdigit():
            return False
        return True

    ## The thread's run method - starts the scheduler
    def run(self):
        logger.info("light scheduler starting up")
        while True:
            self._scheduler.run_pending()

