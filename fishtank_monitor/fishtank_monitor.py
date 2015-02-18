import serial
import time
import sqlite3
import smtplib
import threading
import pygal
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import logging, logging.handlers

log_handler = logging.handlers.TimedRotatingFileHandler("fishtank_monitor.log",
                                                         backupCount=5,
                                                         when="midnight")
log_formatter = logging.Formatter('%(asctime)s | %(levelname)5s | %(message)s')
log_handler.setFormatter(log_formatter)
logger = logging.getLogger('fishtank_monitor')
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

SERIAL_DEV = '/dev/ttyS0'

conn = sqlite3.Connection('./fishtank.db')

conn.execute('create table if not exists measurements (time INT, temp REAL, ph REAL)')

ph = None
temperature = None

def parse_input(input):
    global temperature
    global ph
    while '\n' in input:
        split_point = input.find('\n')
        token = input[:split_point]
        if token[0] == 'T':
            temperature = float(token[2:])
            logger.debug("measured temperature:  %r"%temperature)
        if token[0] == 'P':
            ph = float(token[2:])
            logger.debug("measured ph:  %r"%ph)
        input = input[split_point + 1:]
    return input

ard = serial.Serial(SERIAL_DEV)

def monitor_serial():
    try:
        input = ''
        stop = False
        while not stop:
            next = ard.readline().decode('UTF8')
            logger.debug("serial raw read %r"%next)
            input = input + next
            input = parse_input(input)
    except Exception as e:
        logger.exception("exception encountered in monitor_serial:  %r" %e)

time_last_notified = 0
time_last_informed = 0

def send_email(email):
    s = smtplib.SMTP('mail.jesande.com', 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login('ewillis@jesande.com', 'password')
    logger.info("sending emails")
    s.sendmail("ewillis@jesande.com", ["ewillis@jesande.com"], email.as_string())
    s.quit()

def notify_if_required():
    global time_last_notified
    ph_bad = False
    temp_bad = False
    msg = ''
    if ph and (ph < 6.0 or ph > 8.0):
        logger.warning("ph is bad: %r" %ph)
        ph_bad = True
    if temperature and (temperature < 20 or temperature > 28):
        logger.warning("temperature is bad: %r" %temperature)
        temp_bad = True
    if ph_bad:
        msg += 'Fishtank PH level is unsafe:  %r\n'%ph
        logger.warn("unsafe ph, will email")
    if temp_bad:
        msg += 'Fishtank temperature is unsafe:  %r\n'%temperature
        logger.warn("unsafe temperature, will email")
    if msg and time.time() - time_last_notified > 4*60*60:
        time_last_notified = time.time()
        logger.info("setting time_last_notified to %r" %time_last_notified)
        msg = MIMEText(msg)
        msg['Subject'] = 'Fishtank warning'
        msg['From'] = "pi@jesande.com"
        msg['To'] =  "ewillis@jesande.com"
        send_email(msg)

def inform_if_required():
    global time_last_informed
    global conn
    global temperature
    global ph
    if time.time() - time_last_informed > 24*60*60:
        logger.info("sending daily report (time_last_informed is %r)"%time_last_informed)
        chart = pygal.DateY(title='Fishtank PH and Temperature over time')
        values = conn.execute('select ph, temp, time from measurements order by time desc limit 1000').fetchall()
        ph_values = [ i[0] for i in values ]
        temp_values = [ i[1] for i in values ]
        time_values = [ datetime.fromtimestamp(i[2]) for i in values ]
        timespan = time_values[0] - time_values[-1]
        chart.x_labels = [ 
                           time_values[0], 
                           time_values[0] - 1*(timespan / 4),
                           time_values[0] - 2*(timespan / 4),
                           time_values[0] - 3*(timespan / 4),
                           time_values[-1]
                         ]
        ph_values = list(zip(time_values, ph_values))
        temp_values = list(zip(time_values, temp_values))
        chart.add('PH', ph_values)
        chart.add('Temperature', temp_values, secondary=True)
        chart.x_label_format = "%b-%d %H:%M"
        chart.render_to_file('chart.svg')
        msg = MIMEMultipart()
        msg.attach(MIMEText('Daily measurements from fishtank.'))
        msg['Subject'] = 'Fishtank status'
        msg['From'] = "pi@jesande.com"
        msg['To'] =  "ewillis@jesande.com"
        with open('chart.svg', 'rb') as f:
            msg.attach(MIMEImage(f.read(), name='chart.svg', _subtype="svg"))
        send_email(msg)
        time_last_informed = time.time()
        logger.info("setting time_last_informed to %r" %time_last_informed)

def create_and_start_monitor():
    monitor = threading.Thread(target=monitor_serial)
    monitor.daemon = True
    logger.info("starting monitor")
    monitor.start()
    time.sleep(2)
    return monitor

def main_loop():
    monitor = create_and_start_monitor()
    while True:
        if temperature is not None and ph is not None:
            logger.info("writing measurements to database ph is %r, temperature is %r" %(ph, temperature))
            conn.execute('insert into measurements values(?, ?, ?)',(int(time.time()), temperature, ph))
            conn.commit()
            notify_if_required()
            inform_if_required()
            if not monitor.is_alive():
                logger.error("serial monitor died, restarting")
                monitor = threadingte_and_start_monitor()
        logger.info("sleeping until next check")
        time.sleep(60*60)

if __name__ == "__main__":
    while True:
        try:
            logger.info("calling main_loop")
            main_loop()
        except Exception as e:
            logger.exception("encountered exception in main_loop, retrying:  %r" %e)
