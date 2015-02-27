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

def main_loop(notifiers):
    logger.debug("starting serial monitor")
    monitor = SerialMonitor.create_and_start_monitor()
    monitor.started.wait()
    logger.debug("starting light scheduler")
    light_scheduler = scheduler.LightScheduler()
    light_scheduler.start()
    logger.debug("prior to while loop in main_loop, temperature is %r, ph is %r" %(monitor.temperature, monitor.ph))
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
