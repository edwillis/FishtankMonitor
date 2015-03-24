## @package fishtank_monitor
#  The main function for the Fishtank Monitor
#
#  This module implements the main entry point for the Fishtank Monitor as well
#  as the principle exception handling strategy, which is to log, discard and
#  reconstruct affected objects and carry on.
# 
#  In addition, all database interaction (such as it is) is handled here.
#
#  @author  Ed Willis
#  @copyright Ed Willis, 2015, all rights reserved
#  @license  This software is released into the public domain

## @mainpage
#
#  @section Introduction Introduction
#  The decomposition of the software can be seen in each of the module pages.
#  Here, we'll cover the dynamic behavior of the system and how it is initialized
#  and does its work.  But first we'll cover the basic responsibilities of the main
#  hardware components in the system.
#
#  @section HW The Raspberry Pi and the Alamode
#  At the coarsest level, the system breaks down into the two main hardware
#  components:  the Raspberry Pi and the Alamode (Arduino-compatible) board.
#
#  @subsection Alamode The Alamode
#  The Alamode is responsible for:
#  * receiving configuration parameters from the Raspberry Pi and applying them
#  * periodically taking temperature and ph measurements
#  * updating the LCD display with time/measurements et al
#  * communicating measurement data and logs to the Raspberry Pi
#
#  @subsection PI The Raspberry Pi
#  The Raspberry Pi is responsible for:
#  * reading configuration parameters frm the config file and making them available
#    to the software components in the system.
#  * managing serial communications, including sending config parameters to the
#    Alamode and subsequently reading measurements data and logs from it
#  * controlling the tank lights on a user-defined schedule
#  * managing the various email notifications, including informational (accompanied
#    by charts) and warnings when tank conditions become unsafe
#  * storing sensor measurement data and some configuration parameters in the sqlite
#    database
#
#  @section Initialization Initialization and steady state operation
#  In rough detail, the dynamic behavior of the system is presented below.
#
#  @subsection Alamode The Alamode
#  * The Alamode starts up and configures some aspects of the hardware and then
#    blocks, waiting on JSON-formatted configuration data for the remainder of the
#    hardware ::setup
#  * The Alamode then enters a ::loop where it periodically:
#      * updates the LCD with the current time and sensor measurements is ::display
#      * sends the Raspberry Pi JSON-formatted sensor measurements and logs
#
#  @subsection Pi The Raspberry Pi
#  * The Raspberry Pi reads the config file makes the configuration parameters available
#  * It creates the notifiers used to publish emailed reports and warnings
#    via ::notifications::get_notifiers
#  * It creates the ::serial_monitor::SerialMonitor and immediately uses it to send
#    the alamode configuration data
#  * It creates the ::scheduler::LightScheduler and starts it to manage the lights
#  * Thereafter, it enters a loop of writing measurement data to the sqlite database,
#    triggering the notifiers and detecting and recovering from certain errors

import time
import sqlite3
from serial_monitor import SerialMonitor
from notifications import get_notifiers
import config
import scheduler
from log import get_logger

logger = get_logger(__name__)

conn = sqlite3.Connection('./fishtank.db')

conn.execute('create table if not exists measurements (time INT, temp REAL, ph REAL)')
conn.execute('create table if not exists settings (last_calibration REAL)')

## The main functional loop of ithe fishtank monitor.
#
#  This function arranges for the following:
#  * Set up serial monitoring
#  * Configure the parameters to use on the alamode
#  * Set up and start the light scheduler
#  And then enter the main loop where we:
#  * Read temperature and PH readings from the alamode
#  * Log the readings to our database
#  * Trigger the notifiers to send out warnings or informational messages
#  This function is also responsible for monitoring the health of the serial
#  monitor thread and restarting it on failures.
#
#  @param notifiers the list of notifier functors to call each iteration
def main_loop(notifiers):
    logger.debug("starting serial monitor")
    monitor = SerialMonitor.create_monitor()
    alamode_cfg = { 
                    "thermistor_pin": config.temperature_pin, 
                    "ph_pin": config.ph_pin, 
                    "daylight": config.daylight_tz, 
                    "standard": config.standard_tz,
                    "ph_offset": config.ph_offset,
                    "ip_address": config.IP_address
                  }
    monitor.write_to_serial(alamode_cfg)
    monitor.start_monitor()
    monitor.started.wait()
    logger.debug("starting light scheduler")
    light_scheduler = scheduler.LightScheduler()
    light_scheduler.start()
    logger.info("prior to while loop in main_loop, temperature is %r, ph is %r" %(monitor.temperature, monitor.ph))
    while True:
        if monitor.temperature is not None and monitor.ph is not None:
            logger.info("writing measurements to database ph is %r, temperature is %r" %(monitor.ph, monitor.temperature))
            conn.execute('insert into measurements values(?, ?, ?)',(int(time.time()), monitor.temperature, monitor.ph))
            conn.commit()
            logger.info("checking notifications")
            for notifier in notifiers:
                notifier(conn, monitor)
            if not monitor.is_alive():
                logger.error("serial monitor died, restarting")
                monitor = SerialMonitor.create_and_start_monitor()
        logger.info("sleeping until next check")
        time.sleep(60*60)

if __name__ == "__main__":
    logger.info("getting parameters from config file")
    config.read_config()
    notifiers = get_notifiers()
    if config.months_between_calibrations:
        try:
            config.last_calibration = conn.execute('select last_calibration from settings').fetchall()[0][0]
        except:
            pass
        if not config.last_calibration:
            config.last_calibration = time.time()
            conn.execute('insert into settings values (%r)' %config.last_calibration)
    logger.info("last_calibration from database is %r" %config.last_calibration)
    while True:
        try:
            logger.info("calling main_loop")
            main_loop(notifiers)
        except Exception as e:
            logger.exception("encountered exception in main_loop, retrying:  %r" %e)
