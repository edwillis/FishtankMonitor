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
x10_light_code = None
lights_on_times = []
lights_off_times = []
x10_retries = None

# set elsewhere
last_calibration = None

config_filename = './cfg/fishtank_monitor.cfg'

def read_config():
    global SMTP_host, SMTP_port, SMTP_user, SMTP_password, SMTP_use_ttls, send_reports_interval
    global send_warnings_interval, email_to_address, email_from_address, months_between_calibrations
    global last_calibration, serial_device, x10_retries, x10_light_code, lights_on_times, lights_off_times
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
        x10_retries = cfg.getint('lights', 'x10 retries')
        x10_light_code = cfg.get('lights', 'x10 light code')
        if cfg.get('lights', 'lights on times').strip():
            for t in cfg.get('lights', 'lights on times').split(','):
                lights_on_times.append(t.strip())
        if cfg.get('lights', 'lights off times').strip():
            for t in cfg.get('lights', 'lights off times').split(','):
                lights_off_times.append(t.strip())
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
        logger.info("x10_retries from config is %r" %x10_retries)
        logger.info("x10_light_code from config is %r" %x10_light_code)
        logger.info("lights_on_times from config is %r" %lights_on_times)
        logger.info("lights_off_times from config is %r" %lights_off_times)


    except Exception as e:
        logger.exception("exception encountered reading config file:  %r" %e)

