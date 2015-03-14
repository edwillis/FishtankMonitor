## @package config
#  Read the user's choices from the config file and make them available to interested parties
#
#  See the config file cfg/fishtank_monitor.cfg.example for details but the heart of
#  this function is to read the config file (cfg/fishtank_monitor.cfg) and set these
#  values into global variables the rest of the code can use to respect the user's
#  choices.
#
#  @author  Ed Willis
#  @copyright Ed Willis, 2015, all rights reserved
#  @license  This software is released into the public domain

import configparser
from log import get_logger

logger = get_logger(__name__)

## The serialdevice to use for communicating with the alamode (e.g. /dev/ttyS0)
serial_device = None
SMTP_host = None
SMTP_port = None
SMTP_user = None
## The user's email password
#  @todo find a way to secure the user's email password
SMTP_password = None
SMTP_use_ttls = None
## How often to email the user informational reports and graphics
send_reports_interval = None
## How often to email warnings to the user when tank conditions are unsafe
send_warnings_interval = None
email_to_address = None
email_from_address = None
## How often the user wishes to recalibrate their ph sensor
months_between_calibrations = None
## The X10 house and device code for controlling the lights (for example I8)
x10_light_code = None
## A list of times in 24 hour format when we should turn on the lights
lights_on_times = []
## A list of times in 24 hour format when we should turn off the lights
lights_off_times = []
## X10 isn't the most reliable protocol - how often should we retry each command
x10_retries = None
## The local daylight savings time offset from GMT in minutes
daylight_tz = None
## The local standard time offset from GMT in minutes
standard_tz = None
## The analog pin the PH monitor is connected to
ph_pin = None
## The analog pin the temperature sensor is connected to
temperature_pin = None
## The linear PH calibration offset to use on PH measurements
ph_offset = None

## The last time we calibrated the ph sensor
last_calibration = None

## The path to the configuration file itself
config_filename = './cfg/fishtank_monitor.cfg'

## Read the config file and parse its contents into a series of global variables
def read_config():
    global SMTP_host, SMTP_port, SMTP_user, SMTP_password, SMTP_use_ttls, send_reports_interval
    global send_warnings_interval, email_to_address, email_from_address, months_between_calibrations
    global last_calibration, serial_device, x10_retries, x10_light_code, lights_on_times, lights_off_times
    global daylight_tz, standard_tz, ph_pin, temperature_pin, ph_offset
    try:
        cfg = configparser.ConfigParser()
        cfg.read(config_filename)
        serial_device = cfg.get('hardware', 'serial device')
        ph_pin = cfg.get('hardware', 'ph pin')
        temperature_pin = cfg.get('hardware', 'temperature pin')
        ph_offset = cfg.getfloat('hardware', 'ph calibration offset')
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
        daylight_tz = cfg.getint('time', 'daylight timezone offset')
        standard_tz = cfg.getint('time', 'standard timezone offset')
        if cfg.get('lights', 'lights on times').strip():
            for t in cfg.get('lights', 'lights on times').split(','):
                lights_on_times.append(t.strip())
        if cfg.get('lights', 'lights off times').strip():
            for t in cfg.get('lights', 'lights off times').split(','):
                lights_off_times.append(t.strip())
        logger.info("serial device from config is %r" %serial_device)
        logger.info("ph pin from config is %r" %ph_pin)
        logger.info("temperature pin from config is %r" %temperature_pin)
        logger.info("ph calibration offset from config is %r" %ph_offset)
        logger.info("standard timezone offset from config is %r" %daylight_tz)
        logger.info("daylight timezone offset from config is %r" %standard_tz)
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

