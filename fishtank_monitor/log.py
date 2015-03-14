## @package log
#  Log utilities ensuring a common formatting for logging
#
#  @author  Ed Willis
#  @copyright Ed Willis, 2015, all rights reserved
#  @license  This software is released into the public domain

import logging, logging.handlers

log_handler = logging.handlers.TimedRotatingFileHandler("log/fishtank_monitor.log",
                                                         backupCount=5,
                                                         when="midnight")

## the log format tracks time and module in addition to the message
log_formatter = logging.Formatter('%(asctime)s | %(module)16s | %(levelname)5s | %(message)s')
log_handler.setFormatter(log_formatter)

## get a logger object specific to the calling module
#
#  @param name the module to build a logger for
#  @return the logger object
def get_logger(name):
    l = logging.getLogger(name)
    l.addHandler(log_handler)
    l.setLevel(logging.INFO)
    return l

