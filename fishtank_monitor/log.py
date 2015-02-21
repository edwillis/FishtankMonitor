import logging, logging.handlers

log_handler = logging.handlers.TimedRotatingFileHandler("fishtank_monitor.log",
                                                         backupCount=5,
                                                         when="midnight")
log_formatter = logging.Formatter('%(asctime)s | %(module)16s | %(levelname)5s | %(message)s')
log_handler.setFormatter(log_formatter)

def get_logger(name):
    l = logging.getLogger(name)
    l.addHandler(log_handler)
    l.setLevel(logging.DEBUG)
    return l

