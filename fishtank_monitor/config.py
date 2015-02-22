import configparser
from log import get_logger

logger = get_logger(__name__)

serial_device = None
SMTP_host = None
SMTP_port = None
SMTP_user = None
SMTP_password = None
SMTP_use_ttls = None
send_reports_interval = None
send_warnings_interval = None
email_to_address = None
email_from_address = None
months_between_calibrations = None
# set elsewhere
last_calibration = None

config_filename = './cfg/fishtank_monitor.cfg'

def read_config():
    global SMTP_host, SMTP_port, SMTP_user, SMTP_password, SMTP_use_ttls, send_reports_interval
    global send_warnings_interval, email_to_address, email_from_address, months_between_calibrations
    global last_calibration, serial_device
    try:
        cfg = configparser.ConfigParser()
        cfg.read(config_filename)
        serial_device = cfg.get('hardware', 'serial device')
        SMTP_host = cfg.get('SMTP', 'host')
        SMTP_port = cfg.getint('SMTP', 'port')
        SMTP_user = cfg.get('SMTP', 'user')
        SMTP_password = cfg.get('SMTP', 'password')
        SMTP_use_ttls = cfg.getboolean('SMTP', 'use ttls')
        send_reports_interval = cfg.getint('email', 'send reports interval')
        send_warnings_interval = cfg.getint('email', 'send warnings interval')
        email_to_address = cfg.get('email', 'email to address')
        email_from_address = cfg.get('email', 'email from address')
        months_between_calibrations = cfg.getint('calibration', 'months_between_calibrations')
        logger.info("serial device from config is %r" %serial_device)
        logger.info("smtp host from config is %r" %SMTP_host)
        logger.info("smtp port from config is %r" %SMTP_port)
        logger.info("smtp user from config is %r" %SMTP_user)
        logger.info("smtp use ttls from config is %r" %SMTP_use_ttls)
        logger.info("send_reports_interval from config is %r" %send_reports_interval)
        logger.info("send_warnings_interval from config is %r" %send_warnings_interval)
        logger.info("email_to_address from config is %r" %email_to_address)
        logger.info("email_from_address from config is %r" %email_from_address)
        logger.info("months_between_calibrations from config is %r" %months_between_calibrations)

    except Exception as e:
        logger.exception("exception encountered reading config file:  %r" %e)

