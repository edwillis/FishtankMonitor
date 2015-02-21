import smtplib
import pygal
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from log import get_logger
import config

logger = get_logger(__name__)

time_last_warned = 0
time_last_informed = 0

def send_email(email):
    s = smtplib.SMTP(config.SMTP_host, config.SMTP_port)
    s.ehlo()
    if config.SMTP_use_ttls:
        s.starttls()
    s.ehlo()
    s.login(config.SMTP_user, config.SMTP_password)
    logger.info("sending emails")
    s.sendmail(config.email_to_address, [config.email_to_address], email.as_string())
    s.quit()

def warn_if_required(monitor):
    global time_last_warned
    ph_bad = False
    temp_bad = False
    msg = ''
    if monitor.ph and (monitor.ph < 6.0 or monitor.ph > 8.0):
        logger.warning("ph is bad: %r" %monitor.ph)
        ph_bad = True
    if monitor.temperature and (monitor.temperature < 20 or monitor.temperature > 28):
        logger.warning("temperature is bad: %r" %monitor.temperature)
        temp_bad = True
    if ph_bad:
        msg += 'Fishtank PH level is unsafe:  %r\n'%monitor.ph
        logger.warn("unsafe ph, will email")
    if temp_bad:
        msg += 'Fishtank temperature is unsafe:  %r\n'%monitor.temperature
        logger.warn("unsafe temperature, will email")
    if msg and time.time() - time_last_warned > config.send_warnings_interval:
        time_last_warned = time.time()
        logger.info("setting time_last_warned to %r" %time_last_warned)
        if config.send_warnings_interval > 0:
            logger.info("sending warning email")
            msg = MIMEText(msg)
            msg['Subject'] = 'Fishtank warning'
            msg['From'] = config.email_from_address
            msg['To'] = config.email_to_address
            send_email(msg)

def inform_if_required(conn):
    global time_last_informed
    if time.time() - time_last_informed > config.send_reports_interval:
        time_last_informed = time.time()
        logger.info("setting time_last_informed to %r" %time_last_informed)
        if config.send_reports_interval > 0:
            logger.info("sending daily report (time_last_informed is %r)"%time_last_informed)
            chart = pygal.DateY(title='Fishtank PH and Temperature over time', x_label_rotation=20)
            values = conn.execute('select ph, temp, time from measurements order by time desc limit 1000').fetchall()
            ph_values = [ i[0] for i in values ]
            temp_values = [ i[1] for i in values ]
            time_values = [ i[2] for i in values ]
            timespan = time_values[0] - time_values[-1]
            ph_values = list(zip(time_values, ph_values))
            temp_values = list(zip(time_values, temp_values))
            chart.add('PH', ph_values)
            logger.debug("PH:  %r" %ph_values)
            chart.add('Temperature', temp_values)
            logger.debug("Temperature:  %r" %temp_values)
            chart.x_label_format = "%Y-%m-%d"
            chart.render_to_file('chart.svg')
            msg = MIMEMultipart()
            msg.attach(MIMEText('Daily measurements from fishtank.'))
            msg['Subject'] = 'Fishtank status'
            msg['From'] = config.email_from_address
            msg['To'] = config.email_to_address
            with open('chart.svg', 'rb') as f:
                msg.attach(MIMEImage(f.read(), name='chart.svg', _subtype="svg"))
            send_email(msg)

