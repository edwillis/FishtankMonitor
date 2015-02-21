import time
import sqlite3
from serial_monitor import SerialMonitor
from notifications import warn_if_required, inform_if_required
import config
from log import get_logger

logger = get_logger(__name__)

conn = sqlite3.Connection('./fishtank.db')

conn.execute('create table if not exists measurements (time INT, temp REAL, ph REAL)')

def main_loop():
    monitor = SerialMonitor.create_and_start_monitor()
    monitor.started.wait()
    logger.debug("prior to while loop in main_loop, temperature is %r, ph is %r" %(monitor.temperature, monitor.ph))
    while True:
        if monitor.temperature is not None and monitor.ph is not None:
            logger.info("writing measurements to database ph is %r, temperature is %r" %(monitor.ph, monitor.temperature))
            conn.execute('insert into measurements values(?, ?, ?)',(int(time.time()), monitor.temperature, monitor.ph))
            conn.commit()
            logger.debug("checking notifications")
            warn_if_required(monitor)
            inform_if_required(conn)
            if not monitor.is_alive():
                logger.error("serial monitor died, restarting")
                monitor = SerialMonitor.create_and_start_monitor()
        logger.info("sleeping until next check")
        time.sleep(60*60)

if __name__ == "__main__":
    logger.info("getting parameters from config file")
    config.read_config()
    while True:
        try:
            logger.info("calling main_loop")
            main_loop()
        except Exception as e:
            logger.exception("encountered exception in main_loop, retrying:  %r" %e)
